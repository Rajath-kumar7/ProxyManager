from abc import ABC, abstractmethod
from typing import List
from ..db.models import Proxy


class BaseExporter(ABC):
    """Abstract base class for all exporters."""

    @abstractmethod
    async def export(self, proxies: List[Proxy]):
        pass
