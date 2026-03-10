"""Web search using DuckDuckGo for sentiment gathering."""

from __future__ import annotations
import asyncio
import structlog
from typing import Any

from duckduckgo_search import DDGS

logger = structlog.get_logger()


class WebSearcher:
    """Searches the web for product reviews and sentiment data."""

    def _new_ddgs(self) -> DDGS:
        """Create a fresh DDGS instance each call to avoid reusing rate-limited sessions."""
        return DDGS()

    async def search_reviews(self, product_name: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search for product reviews on Reddit, YouTube, and forums."""
        queries = [
            f"{product_name} review reddit India",
            f"{product_name} review YouTube",
            f"{product_name} problems issues reddit",
        ]

        all_results = []
        for query in queries:
            try:
                ddgs = self._new_ddgs()
                raw_results = await asyncio.wait_for(
                    asyncio.to_thread(ddgs.text, query, region="in-en", max_results=max_results),
                    timeout=4.0
                )
                results = list(raw_results)
                for r in results:
                    all_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                        "source": self._classify_source(r.get("href", "")),
                    })
            except Exception as e:
                logger.warning("web_search_failed", query=query, error=str(e))
                continue

        logger.info("web_search_complete", product=product_name, results=len(all_results))
        return all_results

    async def fact_check(self, subject: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search for real-world facts, reviews, and issues about a product or claim."""
        query = f"{subject} review problems real world India 2025"
        try:
            ddgs = self._new_ddgs()
            raw_results = await asyncio.wait_for(
                asyncio.to_thread(ddgs.text, query, region="in-en", max_results=max_results),
                timeout=4.0,
            )
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:200],
                    "url": r.get("href", ""),
                    "source": self._classify_source(r.get("href", "")),
                }
                for r in list(raw_results)
            ]
        except Exception as e:
            logger.warning("fact_check_failed", subject=subject, error=str(e))
            return []

    async def search_products(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search for product listings."""
        try:
            ddgs = self._new_ddgs()
            raw_results = await asyncio.wait_for(
                asyncio.to_thread(ddgs.text, f"{query} buy India price", region="in-en", max_results=max_results),
                timeout=4.0
            )
            results = list(raw_results)
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.error("product_search_failed", query=query, error=str(e))
            return []

    @staticmethod
    def _classify_source(url: str) -> str:
        """Classify URL source."""
        url_lower = url.lower()
        if "reddit.com" in url_lower:
            return "reddit"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "amazon" in url_lower:
            return "amazon"
        elif "flipkart" in url_lower:
            return "flipkart"
        else:
            return "web"
