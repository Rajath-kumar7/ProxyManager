from pathlib import Path
from typing import List, Dict
import aiofiles
from collections import defaultdict
from loguru import logger
from .base import BaseExporter
from ..db.models import Proxy
from ..core.config import config


class TextExporter(BaseExporter):
    """Exports working proxies to protocol-specific text files."""

    async def export(self, proxies: List[Proxy]):
        output_dir = Path(config.get("output_dir"))
        output_dir.mkdir(exist_ok=True)

        # Group proxies by protocol
        grouped_proxies: Dict[str, List[str]] = defaultdict(list)
        for p in proxies:
            grouped_proxies[p.protocol].append(f"{p.host}:{p.port}")

        for protocol, addresses in grouped_proxies.items():
            file_path = output_dir / f"{protocol}.txt"
            try:
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write("\n".join(addresses))
                logger.success(f"Exported {len(addresses)} proxies to {file_path}")
            except Exception as e:
                logger.error(f"Failed to export to {file_path}: {e}")
