from abc import ABC, abstractmethod
from typing import List
import aiohttp
from ..core.config import config


class BaseCollector(ABC):
    """Abstract base class for all proxy collectors."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = config.get("scraper_headers")

    @abstractmethod
    async def fetch(self) -> List[dict]:
        """
        Fetches proxies from the source.
        Should return a list of dictionaries, each with 'protocol', 'host', and 'port'.
        """
        pass
