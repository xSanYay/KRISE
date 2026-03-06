"""Scraper Agent — coordinates product fetching from multiple sources."""

from __future__ import annotations
import asyncio
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import (
    PRODUCT_SEARCH_QUERY_PROMPT,
    SENTIMENT_SUMMARY_SYSTEM,
    SENTIMENT_SUMMARY_PROMPT,
)
from app.models.intent import IntentProfile
from app.models.product import Product, SentimentData
from app.scraping.amazon import AmazonScraper
from app.scraping.flipkart import FlipkartScraper
from app.websearch.search import WebSearcher

logger = structlog.get_logger()


class ScraperAgent:
    """Coordinates parallel scraping from multiple sources."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._amazon = AmazonScraper()
        self._flipkart = FlipkartScraper()
        self._web_search = WebSearcher()

    async def fetch_products(self, intent_profile: IntentProfile) -> list[Product]:
        """Fetch products from all sources based on intent profile."""
        # Generate search queries using LLM
        queries = await self._generate_search_queries(intent_profile)

        if not queries:
            queries = [f"{intent_profile.primary_use_case} {intent_profile.product_category}"]

        logger.info("scraping_started", queries=queries)

        # Scrape from multiple sources in parallel
        all_products: list[Product] = []

        for query in queries[:2]:  # Limit to 2 queries for speed
            tasks = [
                self._amazon.search(query, max_results=8),
                self._flipkart.search(query, max_results=8),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_products.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("scrape_source_failed", error=str(result))

        # Deduplicate by title similarity
        unique_products = self._deduplicate(all_products)

        # Fetch sentiment for top products (limit to 5 for an optimized, curated list)
        sentiment_tasks = [
            self._fetch_sentiment(p, intent_profile) for p in unique_products[:5]
        ]
        products_with_sentiment = await asyncio.gather(*sentiment_tasks, return_exceptions=True)

        final_products = []
        for result in products_with_sentiment:
            if isinstance(result, Product):
                final_products.append(result)

        logger.info("scraping_complete", total_products=len(final_products))
        return final_products

    async def _generate_search_queries(self, profile: IntentProfile) -> list[str]:
        """Use LLM to generate optimal search queries."""
        reqs = ", ".join(r.name for r in profile.technical_requirements[:5])
        budget = str(int(profile.constraints.budget_max)) if profile.constraints.budget_max else "any"
        brands = ", ".join(profile.constraints.brand_preferences) if profile.constraints.brand_preferences else "any"

        prompt = PRODUCT_SEARCH_QUERY_PROMPT.format(
            primary_use_case=profile.primary_use_case,
            product_category=profile.product_category,
            budget_max=budget,
            requirements=reqs or "general purpose",
            brand_preferences=brands,
        )

        result = await self._llm.generate_json(prompt, max_tokens=200)

        if isinstance(result, list):
            return [str(q) for q in result[:3]]
        elif isinstance(result, dict) and "error" not in result:
            # Try to extract list from dict
            for v in result.values():
                if isinstance(v, list):
                    return [str(q) for q in v[:3]]
        return []

    async def _fetch_sentiment(self, product: Product, profile: IntentProfile) -> Product:
        """Fetch and analyze sentiment for a product."""
        try:
            search_results = await self._web_search.search_reviews(product.title, max_results=5)

            if not search_results:
                return product

            snippets = "\n".join(
                f"[{r['source']}] {r['title']}: {r['snippet']}" for r in search_results[:8]
            )

            priorities = ", ".join(
                [profile.primary_use_case] + profile.secondary_use_cases[:2]
            )

            prompt = SENTIMENT_SUMMARY_PROMPT.format(
                product_name=product.title,
                snippets=snippets,
                user_priorities=priorities or "general use",
            )

            result = await self._llm.generate_json(prompt, system=SENTIMENT_SUMMARY_SYSTEM, max_tokens=500)

            if "error" not in result:
                product.sentiment = SentimentData(
                    overall_score=float(result.get("overall_score", 0.5)),
                    pros=result.get("pros", []),
                    cons=result.get("cons", []),
                    hidden_issues=result.get("hidden_issues", []),
                    summary=result.get("summary", ""),
                    sample_size=int(result.get("sample_size", 0)),
                )
        except Exception as e:
            logger.warning("sentiment_fetch_failed", product=product.title, error=str(e))

        return product

    @staticmethod
    def _deduplicate(products: list[Product]) -> list[Product]:
        """Remove duplicate products based on title similarity."""
        seen_titles: set[str] = set()
        unique: list[Product] = []

        for p in products:
            # Simple dedup: normalize and check first 50 chars
            normalized = p.title.lower().strip()[:50]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(p)

        return unique
