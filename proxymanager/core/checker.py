import asyncio
import time
from typing import Dict, Optional
import aiohttp
from aiohttp_socks import ProxyConnector
from loguru import logger
from .config import config

TCP_TIMEOUT = config.get("tester.tcp_connect_timeout")
HTTP_TIMEOUT = config.get("tester.http_request_timeout")
SPEED_URL = config.get("tester.speed_test_url")
SPEED_BYTES_LIMIT = config.get("tester.speed_test_bytes_limit")
IP_CHECK_URL = config.get("tester.ip_check_url")


async def check_proxy(proxy: Dict, check_url: Optional[str] = None) -> Dict:
    """
    Performs a proxy check.
    If check_url is provided -> do a faster connectivity/latency-only check against that URL.
    Otherwise -> perform full check (latency + speed) using configured URLs.
    Returns a dict with is_working, latency_ms, download_mbps, and original proxy fields.
    """
    proxy_url = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
    result = {**proxy, "is_working": False, "latency_ms": 9999, "download_mbps": 0.0}

    try:
        connector = ProxyConnector.from_url(proxy_url)
    except Exception as e:
        logger.debug(f"Failed to create connector for {proxy_url}: {e}")
        return result

    async with aiohttp.ClientSession(connector=connector) as session:
        # 1) Latency / basic connectivity (use check_url if provided, else IP_CHECK_URL)
        latency = await test_latency(session, check_url or IP_CHECK_URL)
        if latency is None:
            return result
        result["latency_ms"] = latency

        # If only a quick recheck (target URL provided), skip speed test
        if check_url:
            result["is_working"] = True
            return result

        # 2) Full speed test using configured SPEED_URL
        speed = await test_speed(session, SPEED_URL)
        if speed is None:
            return result
        result["download_mbps"] = speed
        result["is_working"] = True

    return result


async def test_latency(session: aiohttp.ClientSession, url: str) -> Optional[int]:
    """Make a small GET to url and measure latency in ms. Returns None on failure."""
    start_time = time.monotonic()
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as response:
            # Accept 200 and also 204 (e.g., generate_204) as success
            if response.status in (200, 204):
                end_time = time.monotonic()
                return int((end_time - start_time) * 1000)
    except Exception:
        # silent failure — caller will handle
        return None
    return None


async def test_speed(session: aiohttp.ClientSession, url: str) -> Optional[float]:
    """Download up to SPEED_BYTES_LIMIT bytes and return Mbps. None on failure."""
    start_time = time.monotonic()
    bytes_downloaded = 0
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as response:
            if response.status != 200:
                return None
            async for chunk in response.content.iter_chunked(1024):
                bytes_downloaded += len(chunk)
                if bytes_downloaded >= SPEED_BYTES_LIMIT:
                    break
        end_time = time.monotonic()
        duration = end_time - start_time
        if duration > 0:
            mbps = (bytes_downloaded * 8) / (duration * 1_000_000)
            return round(mbps, 2)
    except Exception:
        return None
    return 0.0
