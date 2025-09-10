import json
from pathlib import Path
from typing import List
import aiofiles
from loguru import logger
from .base import BaseExporter
from ..db.models import Proxy
from ..core.config import config


class JSONExporter(BaseExporter):
    """Exports working proxies to a structured JSON file."""

    async def export(self, proxies: List[Proxy]):
        output_dir = Path(config.get("output_dir"))
        output_dir.mkdir(exist_ok=True)
        file_path = output_dir / "proxies.json"

        proxies_list = [
            {
                "url": p.url,
                "protocol": p.protocol,
                "host": p.host,
                "port": p.port,
                "latency_ms": p.latency_ms,
                "download_mbps": p.download_mbps,
                "score": p.score,
                "source": p.source,
                "last_tested": p.last_tested.isoformat() if p.last_tested else None
            }
            for p in proxies
        ]

        try:
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(proxies_list, indent=2))
            logger.success(f"Exported {len(proxies_list)} proxies to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export to {file_path}: {e}")

