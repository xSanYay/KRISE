"""Scraper Agent — coordinates product fetching from multiple sources."""

from __future__ import annotations
import asyncio
import uuid
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import (
    PRODUCT_SEARCH_QUERY_PROMPT,
    SENTIMENT_SUMMARY_SYSTEM,
    SENTIMENT_SUMMARY_PROMPT,
    DDG_PRODUCT_EXTRACTION_SYSTEM,
    DDG_PRODUCT_EXTRACTION_PROMPT,
    LLM_PRODUCT_GENERATION_SYSTEM,
    LLM_PRODUCT_GENERATION_PROMPT,
)
from app.models.intent import IntentProfile
from app.models.product import Product, PriceInfo, SentimentData
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

        # Scrape from multiple sources in parallel — all queries at once
        all_products: list[Product] = []

        async def _scrape_query(query: str) -> list[Product]:
            tasks = [
                self._amazon.search(query, max_results=8),
                self._flipkart.search(query, max_results=8),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            products: list[Product] = []
            for result in results:
                if isinstance(result, list):
                    products.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("scrape_source_failed", error=str(result))
            return products

        try:
            query_tasks = [_scrape_query(q) for q in queries[:2]]
            gathered = await asyncio.wait_for(
                asyncio.gather(*query_tasks, return_exceptions=True),
                timeout=45,
            )
            for result in gathered:
                if isinstance(result, list):
                    all_products.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("scrape_source_failed", error=str(result))
        except asyncio.TimeoutError:
            logger.warning("scraping_timeout", elapsed_s=25)

        # Layer 2: If Playwright scraping returned nothing, try DuckDuckGo + LLM extraction
        if not all_products:
            logger.info("playwright_empty_using_ddg_fallback")
            all_products = await self._search_products_via_ddg(queries, intent_profile)

        # Layer 3: If DDG also returns nothing (rate-limited / blocked), use LLM knowledge
        if not all_products:
            logger.info("ddg_empty_using_llm_fallback")
            all_products = await self._generate_products_from_llm(intent_profile)

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

    async def _generate_products_from_llm(self, profile: IntentProfile) -> list[Product]:
        """Last-resort fallback: ask the LLM to generate real product suggestions from its training knowledge."""
        reqs = ", ".join(r.name for r in profile.technical_requirements[:6]) or "general purpose"
        budget = str(int(profile.constraints.budget_max)) if profile.constraints.budget_max else "50000"
        brands = ", ".join(profile.constraints.brand_preferences) if profile.constraints.brand_preferences else "no preference"
        secondary = ", ".join(profile.secondary_use_cases[:3]) if profile.secondary_use_cases else "none"

        prompt = LLM_PRODUCT_GENERATION_PROMPT.format(
            primary_use_case=profile.primary_use_case or "everyday use",
            product_category=profile.product_category or "phone",
            budget_max=budget,
            requirements=reqs,
            brand_preferences=brands,
            secondary_uses=secondary,
        )

        raw = await self._llm.generate_json(prompt, system=LLM_PRODUCT_GENERATION_SYSTEM, max_tokens=2000)
        items: list = raw if isinstance(raw, list) else raw.get("products", []) if isinstance(raw, dict) else []

        products: list[Product] = []
        for item in items:
            try:
                price = float(item.get("price") or 0)
                if price <= 0:
                    continue
                original = item.get("original_price")
                orig_float = float(original) if original else None
                discount = None
                if orig_float and orig_float > price:
                    discount = round((1 - price / orig_float) * 100, 1)

                specs: dict = item.get("specs", {})

                products.append(Product(
                    id=str(uuid.uuid4()),
                    title=str(item.get("title", "Unknown")),
                    brand=str(item.get("brand", item.get("title", "").split()[0] if item.get("title") else "")),
                    price=PriceInfo(
                        current=price,
                        original=orig_float,
                        discount_percent=discount,
                    ),
                    url=str(item.get("url", "")),
                    source="ai_suggested",
                    availability="in_stock",
                    rating=float(item["rating"]) if item.get("rating") else None,
                    specifications=specs if isinstance(specs, dict) else {},
                ))
            except Exception as exc:
                logger.warning("llm_product_parse_failed", error=str(exc))

        logger.info("llm_products_generated", count=len(products))
        return products

    async def _search_products_via_ddg(self, queries: list[str], profile: IntentProfile) -> list[Product]:
        """Fallback: search DuckDuckGo and use LLM to extract structured product data."""
        all_snippets: list[str] = []

        search_tasks = [self._web_search.search_products(q, max_results=8) for q in queries[:2]]
        results_list = await asyncio.gather(*search_tasks, return_exceptions=True)

        for results in results_list:
            if isinstance(results, list):
                for r in results:
                    snippet = f"[{r.get('url', '')}] {r.get('title', '')}: {r.get('snippet', '')}"
                    all_snippets.append(snippet)

        if not all_snippets:
            return []

        budget = int(profile.constraints.budget_max) if profile.constraints.budget_max else 50000
        query_context = f"{profile.product_category} under ₹{budget} India"
        snippets_text = "\n".join(all_snippets[:16])

        prompt = DDG_PRODUCT_EXTRACTION_PROMPT.format(
            query=query_context,
            snippets=snippets_text,
        )

        raw = await self._llm.generate_json(prompt, system=DDG_PRODUCT_EXTRACTION_SYSTEM, max_tokens=1500)

        items: list = raw if isinstance(raw, list) else raw.get("products", []) if isinstance(raw, dict) else []

        products: list[Product] = []
        for item in items:
            try:
                price = float(item.get("price") or 0)
                if price <= 0:
                    continue

                original = item.get("original_price")
                orig_float = float(original) if original else None
                discount = None
                if orig_float and orig_float > price:
                    discount = round((1 - price / orig_float) * 100, 1)

                products.append(Product(
                    id=str(uuid.uuid4()),
                    title=str(item.get("title", "Unknown")),
                    brand=str(item.get("brand", item.get("title", "").split()[0] if item.get("title") else "")),
                    price=PriceInfo(
                        current=price,
                        original=orig_float,
                        discount_percent=discount,
                    ),
                    url=str(item.get("url", "")),
                    source=str(item.get("source", "web")),
                    availability=str(item.get("availability", "in_stock")),
                    rating=float(item["rating"]) if item.get("rating") else None,
                    specifications=item.get("specs", {}),
                ))
            except Exception as exc:
                logger.warning("ddg_product_parse_failed", error=str(exc))

        logger.info("ddg_products_extracted", count=len(products))
        return products

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
