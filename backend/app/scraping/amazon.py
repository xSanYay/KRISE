"""Amazon India scraper using Playwright."""

from __future__ import annotations
import asyncio
import random
import uuid
import structlog

from app.scraping.base import BaseScraper
from app.scraping.browser import browser_manager
from app.models.product import Product, PriceInfo

logger = structlog.get_logger()


class AmazonScraper(BaseScraper):
    """Scrapes product data from Amazon India."""

    BASE_URL = "https://www.amazon.in"

    async def search(self, query: str, max_results: int = 10) -> list[Product]:
        """Search Amazon India for products."""
        search_url = f"{self.BASE_URL}/s?k={query.replace(' ', '+')}"

        try:
            page, context = await browser_manager.get_page(search_url)
        except Exception as e:
            logger.error("amazon_search_failed", query=query, error=str(e))
            return []

        products = []
        try:
            # Wait for search results
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)

            items = await page.query_selector_all('[data-component-type="s-search-result"]')

            for item in items[:max_results]:
                try:
                    product = await self._parse_search_result(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning("amazon_parse_item_failed", error=str(e))
                    continue

            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            logger.error("amazon_search_parse_failed", query=query, error=str(e))
        finally:
            await context.close()

        logger.info("amazon_search_complete", query=query, results=len(products))
        return products

    async def _parse_search_result(self, element) -> Product | None:
        """Parse a single Amazon search result element."""
        # Title
        title_el = await element.query_selector("h2 a span")
        title = await title_el.inner_text() if title_el else None
        if not title:
            return None

        # URL
        link_el = await element.query_selector("h2 a")
        href = await link_el.get_attribute("href") if link_el else ""
        url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href

        # Price
        price_whole = await element.query_selector(".a-price-whole")
        price_text = await price_whole.inner_text() if price_whole else "0"
        price_text = price_text.replace(",", "").replace(".", "").strip()
        try:
            current_price = float(price_text) if price_text else 0
        except ValueError:
            current_price = 0

        # Original price
        original_el = await element.query_selector(".a-price.a-text-price .a-offscreen")
        original_price = None
        if original_el:
            orig_text = await original_el.inner_text()
            orig_text = orig_text.replace("₹", "").replace(",", "").strip()
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating_el = await element.query_selector(".a-icon-alt")
        rating = None
        if rating_el:
            rating_text = await rating_el.inner_text()
            try:
                rating = float(rating_text.split(" ")[0])
            except (ValueError, IndexError):
                pass

        # Review count
        review_el = await element.query_selector('[aria-label*="ratings"]')
        review_count = None
        if review_el:
            rc_text = await review_el.inner_text()
            rc_text = rc_text.replace(",", "").strip()
            try:
                review_count = int(rc_text)
            except ValueError:
                pass

        # Image
        img_el = await element.query_selector("img.s-image")
        image = await img_el.get_attribute("src") if img_el else ""

        if current_price == 0:
            return None

        discount = None
        if original_price and original_price > current_price:
            discount = round((1 - current_price / original_price) * 100, 1)

        return Product(
            id=str(uuid.uuid4()),
            title=title,
            brand=title.split(" ")[0] if title else "",
            price=PriceInfo(
                current=current_price,
                original=original_price,
                discount_percent=discount,
            ),
            url=url,
            source="amazon",
            availability="in_stock",
            rating=rating,
            review_count=review_count,
            images=[image] if image else [],
        )

    async def get_product_details(self, url: str) -> Product | None:
        """Get detailed product info from Amazon product page."""
        try:
            page, context = await browser_manager.get_page(url)
        except Exception as e:
            logger.error("amazon_detail_failed", url=url, error=str(e))
            return None

        try:
            title_el = await page.query_selector("#productTitle")
            title = (await title_el.inner_text()).strip() if title_el else "Unknown"

            # Price
            price_el = await page.query_selector(".a-price-whole")
            price_text = (await price_el.inner_text()).replace(",", "").replace(".", "").strip() if price_el else "0"
            try:
                price = float(price_text)
            except ValueError:
                price = 0

            # Specs table
            specs = {}
            spec_rows = await page.query_selector_all("#productOverview_feature_div tr, #detailBullets_feature_div li")
            for row in spec_rows[:15]:
                cells = await row.query_selector_all("td, span")
                texts = [await c.inner_text() for c in cells]
                if len(texts) >= 2:
                    key = texts[0].strip().rstrip(":")
                    val = texts[1].strip()
                    if key and val:
                        specs[key] = val

            return Product(
                id=str(uuid.uuid4()),
                title=title,
                brand=title.split(" ")[0],
                price=PriceInfo(current=price),
                specifications=specs,
                url=url,
                source="amazon",
                availability="in_stock",
            )
        except Exception as e:
            logger.error("amazon_detail_parse_failed", error=str(e))
            return None
        finally:
            await context.close()
