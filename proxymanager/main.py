import asyncio
from typing import List, Dict
from pathlib import Path
from collections import defaultdict
import aiohttp
import aiofiles
from loguru import logger
from sqlalchemy import select, delete, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from aiohttp_socks import ProxyConnector

from .core.checker import check_proxy
from .core.scoring import calculate_score
from .core.config import config
from .db.database import AsyncSessionLocal
from .db.models import Proxy

# Global concurrency limit for checking proxies
CONCURRENCY = config.get("concurrency_limit")

# Main workflow function
async def run_workflow():
    collector_proxy_url = config.get("collector_proxy")
    connector = None
    if collector_proxy_url:
        logger.info(f"Using collector proxy for initial fetch: {collector_proxy_url}")
        connector = ProxyConnector.from_url(collector_proxy_url)
    else:
        logger.info("Connecting directly to collect proxies (no collector proxy set).")
    logger.info("Starting proxy collection...")
    from .collectors import ALL_COLLECTORS_STATIC, TextFileCollector, TEXT_SOURCES
    async with aiohttp.ClientSession(connector=connector) as session:
        collect_tasks = []
        for collector_cls in ALL_COLLECTORS_STATIC:
            collect_tasks.append(collector_cls(session).fetch())
        for protocol, urls in TEXT_SOURCES.items():
            for url in urls:
                collect_tasks.append(TextFileCollector(session, protocol, url).fetch())
        results = await asyncio.gather(*collect_tasks, return_exceptions=True)
    raw_proxies: List[Dict] = []
    for res in results:
        if isinstance(res, list):
            raw_proxies.extend(res)
        elif isinstance(res, Exception):
            logger.warning(f"A collector failed: {res}")
    unique_proxies_map = {f"{p['host']}:{p['port']}": p for p in raw_proxies}
    unique_proxies = list(unique_proxies_map.values())
    for p in unique_proxies:
        if p['protocol'].lower() == 'https':
            p['protocol'] = 'http'
    logger.success(f"Collected {len(unique_proxies)} unique proxies.")
    if not unique_proxies:
        logger.warning("No proxies were collected. Exiting workflow as there is nothing to check.")
        return
    logger.info(f"Checking {len(unique_proxies)} proxies with concurrency={CONCURRENCY}...")
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def throttled_check(proxy):
        async with semaphore:
            return await check_proxy(proxy)

    check_tasks = [throttled_check(proxy) for proxy in unique_proxies]
    checked_results = await asyncio.gather(*check_tasks, return_exceptions=True)
    proxies_to_save = []
    working_count = 0
    for res in checked_results:
        if isinstance(res, dict):
            res['score'] = calculate_score(res['latency_ms'], res['download_mbps'], res['is_working'])
            if res['is_working']:
                working_count += 1
            proxies_to_save.append(res)
        elif isinstance(res, Exception):
            logger.error(f"A check task failed unexpectedly: {res}")
    logger.success(f"Finished checking. Found {working_count} working proxies.")
    if proxies_to_save:
        BATCH_SIZE = 50
        total_proxies = len(proxies_to_save)
        logger.info(f"Saving {total_proxies} results to the database in batches of {BATCH_SIZE}...")
        async with AsyncSessionLocal() as session:
            for i in range(0, total_proxies, BATCH_SIZE):
                batch = proxies_to_save[i:i + BATCH_SIZE]
                if not batch: continue
                if (i // BATCH_SIZE) % 10 == 0:
                    logger.info(f"Saving batch starting at index {i}...")
                stmt = sqlite_insert(Proxy).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['host', 'port'],
                    set_={
                        'protocol': stmt.excluded.protocol,
                        'is_working': stmt.excluded.is_working,
                        'latency_ms': stmt.excluded.latency_ms,
                        'download_mbps': stmt.excluded.download_mbps,
                        'score': stmt.excluded.score,
                        'source': stmt.excluded.source,
                        'last_tested': stmt.excluded.last_tested
                    }
                )
                await session.execute(stmt)
            await session.commit()
        logger.success("Database updated.")
    logger.info("Exporting working proxies...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Proxy).where(Proxy.is_working == True).order_by(Proxy.score.desc())
        )
        working_proxies = result.scalars().all()
    if working_proxies:
        from .exporters import ALL_EXPORTERS
        export_tasks = [exporter_cls().export(working_proxies) for exporter_cls in ALL_EXPORTERS]
        await asyncio.gather(*export_tasks)
    else:
        logger.warning("No working proxies to export.")
    logger.info("Workflow finished successfully!")

# A simplified workflow that only collects and saves proxies without checking
async def collect_only_workflow():
    logger.info("🚀 Starting proxy collection process...")
    collector_proxy_url = config.get("collector_proxy")
    connector = ProxyConnector.from_url(collector_proxy_url) if collector_proxy_url else None

    from .collectors import ALL_COLLECTORS_STATIC, TextFileCollector, TEXT_SOURCES
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [cls(session).fetch() for cls in ALL_COLLECTORS_STATIC]
        for proto, urls in TEXT_SOURCES.items():
            for url in urls:
                tasks.append(TextFileCollector(session, proto, url).fetch())
        results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_proxies = [p for res in results if isinstance(res, list) for p in res]
    unique_proxies_map = {f"{p['host']}:{p['port']}": p for p in raw_proxies}
    unique_proxies = list(unique_proxies_map.values())

    if not unique_proxies:
        logger.warning("No proxies were collected.")
        return

    logger.success(f"Collected {len(unique_proxies)} unique proxies. Saving to database...")
    BATCH_SIZE = 50
    total = len(unique_proxies)
    async with AsyncSessionLocal() as session:
        for i in range(0, total, BATCH_SIZE):
            batch = unique_proxies[i:i + BATCH_SIZE]
            if not batch: continue
            try:
                stmt = sqlite_insert(Proxy).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=['host', 'port'])
                await session.execute(stmt)
            except Exception as e:
                logger.error(f"Failed to insert batch starting at {i}: {e}")
        await session.commit()
    logger.success("✅ New proxies have been saved to the database.")

# Workflow to export all proxies from the database to text files
async def export_all_workflow():
    logger.info("📂 Exporting all proxies from database to text files...")
    proxies_from_db = await get_all_proxies_from_db()
    if not proxies_from_db:
        logger.warning("Database is empty. Nothing to export.")
        return
    proxy_dicts = [{"protocol": p.protocol, "host": p.host, "port": p.port} for p in proxies_from_db]
    await export_to_text_files(proxy_dicts)
    logger.success("✅ All proxies exported successfully.")

# Workflow to delete all proxies from the database and vacuum
async def delete_all_proxies_workflow():
    logger.warning("🔥 Deleting all proxies from the database...")
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(delete(Proxy))
            logger.info("All proxy records have been deleted.")
            logger.info("Vacuuming the database to reclaim disk space. This may take a moment...")
            await session.commit()
            await session.execute(text("VACUUM"))
            await session.commit()
            logger.success("✅ Database has been cleared and vacuumed successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"An error occurred during database clearing: {e}")

# Helper function to get all proxies from the database
async def get_all_proxies_from_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Proxy))
        proxies = result.scalars().all()
        logger.info(f"Loaded {len(proxies)} proxies from the database.")
        return proxies

# Helper function to export proxies to text files
async def export_to_text_files(proxies: List[Dict], out_dir: str = None):
    output_dir = Path(out_dir or config.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = defaultdict(list)
    for p in proxies:
        proto = p.get("protocol", "http").lower()
        grouped[proto].append(f"{p['host']}:{p['port']}")
    for proto, addrs in grouped.items():
        path = output_dir / f"{proto}.txt"
        try:
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write("\n".join(addrs))
            logger.success(f"Wrote {len(addrs)} {proto} proxies -> {path}")
        except Exception as e:
            logger.error(f"Failed writing {path}: {e}")

# Workflow to recheck all proxies in the database against a target URL
async def recheck_workflow(target_url: str):
    proxies = await get_all_proxies_from_db()
    if not proxies:
        logger.warning("Database empty — nothing to recheck.")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY)
    total_proxies = len(proxies)
    checked_count = 0
    working_count = 0
    working_proxies = []

    def model_to_dict(m: Proxy) -> Dict:
        d = {"protocol": m.protocol.lower(), "host": m.host, "port": m.port, "source": m.source}
        if d["protocol"] == "https": d["protocol"] = "http"
        return d

    async def throttled(proxy_dict):
        async with semaphore:
            return await check_proxy(proxy_dict, check_url=target_url)

    tasks = [asyncio.create_task(throttled(model_to_dict(p))) for p in proxies]
    logger.info(f"Starting recheck of {total_proxies} proxies against {target_url}...")

    interrupted = False
    try:
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                checked_count += 1
                if isinstance(result, dict) and result.get("is_working"):
                    working_count += 1
                    working_proxies.append(result)

            except Exception as e:
                checked_count += 1
                logger.debug(f"Recheck task error: {e}")

            if checked_count % 200 == 0 or checked_count == total_proxies:
                logger.info(f"Progress: {checked_count}/{total_proxies} checked | {working_count} working.")

    except asyncio.CancelledError:
        logger.warning("Interruption detected! Proceeding to save working proxies...")
        interrupted = True

    finally:
        logger.info("Recheck process finishing up...")

        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        if working_proxies:
            await export_to_text_files(working_proxies)
        else:
            logger.warning("No working proxies were found to export.")

    if interrupted:
        logger.success(f"Graceful shutdown complete. Found and saved {len(working_proxies)} proxies.")
    else:
        logger.success(f"Recheck finished: found {len(working_proxies)} working proxies for {target_url}")
