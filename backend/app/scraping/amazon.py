"""Amazon India scraper using Playwright (reliable, anti-bot resistant)."""

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
    """Scrapes product data from Amazon India using Playwright."""

    BASE_URL = "https://www.amazon.in"

    async def search(self, query: str, max_results: int = 10) -> list[Product]:
        """Search Amazon India for products."""
        search_url = f"{self.BASE_URL}/s?k={query.replace(' ', '+')}&ref=nb_sb_noss"

        try:
            page, context = await browser_manager.get_page(search_url)
        except Exception as e:
            logger.error("amazon_search_failed", query=query, error=str(e))
            return []

        products = []
        try:
            items = await page.query_selector_all('[data-component-type="s-search-result"]')
            logger.info("amazon_items_found", count=len(items), query=query)

            for item in items[:max_results]:
                try:
                    product = await self._parse_search_result(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning("amazon_parse_item_failed", error=str(e))
                    continue

            await asyncio.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            logger.error("amazon_search_parse_failed", query=query, error=str(e))
        finally:
            await context.close()

        logger.info("amazon_search_complete", query=query, results=len(products))
        return products

    async def _parse_search_result(self, element) -> Product | None:
        """Parse a single Amazon search result element."""
        # Title — use h2 which always contains the product name
        title_el = await element.query_selector("h2")
        title = await title_el.inner_text() if title_el else None
        if not title:
            return None

        # URL
        link_el = await element.query_selector("h2 a")
        href = await link_el.get_attribute("href") if link_el else None
        url = f"{self.BASE_URL}{href}" if href else ""

        # Current price
        current_price = 0
        price_whole = await element.query_selector(".a-price-whole")
        if price_whole:
            price_text = await price_whole.inner_text()
            price_text = price_text.replace(",", "").replace(".", "").strip()
            try:
                current_price = float(price_text)
            except ValueError:
                pass

        # Original price
        original_price = None
        orig_el = await element.query_selector(".a-price.a-text-price .a-offscreen")
        if orig_el:
            orig_text = (await orig_el.inner_text()).replace("₹", "").replace(",", "").strip()
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating = None
        rating_el = await element.query_selector(".a-icon-alt")
        if rating_el:
            try:
                rating_text = await rating_el.inner_text()
                rating = float(rating_text.split(" ")[0])
            except (ValueError, IndexError):
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
            title=title.strip(),
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

            price_el = await page.query_selector(".a-price-whole")
            price_text = (await price_el.inner_text()).replace(",", "").replace(".", "").strip() if price_el else "0"
            try:
                price = float(price_text)
            except ValueError:
                price = 0

            specs = {}
            spec_rows = await page.query_selector_all("#productOverview_feature_div tr")
            for row in spec_rows[:15]:
                cells = await row.query_selector_all("td")
                if len(cells) >= 2:
                    key = (await cells[0].inner_text()).strip()
                    val = (await cells[1].inner_text()).strip()
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
