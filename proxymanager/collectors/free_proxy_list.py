import asyncio
from typing import List
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseCollector


class FreeProxyListCollector(BaseCollector):
    """Collector for free-proxy-list.net."""

    URL = "https://free-proxy-list.net/"

    async def fetch(self) -> List[dict]:
        proxies = []
        try:
            async with self.session.get(self.URL, headers=self.headers, timeout=15) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch from {self.URL}. Status: {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                table = soup.find('table', class_='table-striped')

                for row in table.tbody.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 6:
                        host = cells[0].text.strip()
                        port = int(cells[1].text.strip())
                        protocol = 'https' if cells[6].text.strip() == 'yes' else 'http'

                        proxies.append({
                            "protocol": protocol,
                            "host": host,
                            "port": port,
                            "source": "free-proxy-list.net"
                        })
            logger.info(f"Collected {len(proxies)} proxies from {self.URL}")
            return proxies
        except Exception as e:
            logger.error(f"Error collecting from {self.URL}: {e}")
            return []
