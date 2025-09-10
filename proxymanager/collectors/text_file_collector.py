import asyncio
from typing import List
from loguru import logger
from .base import BaseCollector


class TextFileCollector(BaseCollector):
    """
    Collector for raw text URLs that list proxies in 'host:port' format.
    Each URL is a separate source.
    """

    def __init__(self, session, protocol: str, url: str):
        """
        Initializes the collector with a specific protocol and URL.
        """
        super().__init__(session)
        self.protocol = protocol
        self.url = url
        # Overwrite source for better logging
        self.source_name = url.split('/')[-2] + '/' + url.split('/')[-1]

    async def fetch(self) -> List[dict]:
        """
        Fetches proxies from the given text-based URL.
        """
        proxies = []
        try:
            logger.debug(f"Attempting to collect from {self.url}")
            async with self.session.get(self.url, headers=self.headers, timeout=20) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch from {self.url}. Status: {response.status}")
                    return []

                text_content = await response.text()
                lines = text_content.strip().splitlines()

                for line in lines:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue

                    try:
                        # Split from the RIGHT side, only once. Handles both formats!
                        host_part, port_str = line.rsplit(':', 1)

                        # Clean up the host if it contains a protocol prefix
                        if '//' in host_part:
                            host = host_part.split('//')[-1]
                        else:
                            host = host_part

                        port = int(port_str)
                        proxies.append({
                            "protocol": self.protocol,
                            "host": host.strip(),
                            "port": port,
                            "source": self.source_name
                        })
                    except ValueError as e:
                        logger.warning(f"Skipping malformed line '{line}' from {self.url}: {e}")

            logger.info(f"Collected {len(proxies)} proxies from {self.source_name}")
            return proxies
        except Exception as e:
            logger.error(f"Error collecting from {self.url}: {e}")
            return []
