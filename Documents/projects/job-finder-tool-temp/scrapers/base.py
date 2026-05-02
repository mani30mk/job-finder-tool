"""Base scraper interface."""
from abc import ABC, abstractmethod
from typing import List, Dict


class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """Return list of normalized job dicts."""
        pass
