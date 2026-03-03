"""Base scraper interface."""

from __future__ import annotations
from abc import ABC, abstractmethod

from app.models.product import Product


class BaseScraper(ABC):
    """Abstract base for marketplace scrapers."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[Product]:
        """Search for products and return structured list."""
        ...

    @abstractmethod
    async def get_product_details(self, url: str) -> Product | None:
        """Get detailed product info from a product page URL."""
        ...
