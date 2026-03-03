"""Flipkart scraper using Playwright."""

from __future__ import annotations
import asyncio
import random
import uuid
import structlog

from app.scraping.base import BaseScraper
from app.scraping.browser import browser_manager
from app.models.product import Product, PriceInfo

logger = structlog.get_logger()


class FlipkartScraper(BaseScraper):
    """Scrapes product data from Flipkart."""

    BASE_URL = "https://www.flipkart.com"

    async def search(self, query: str, max_results: int = 10) -> list[Product]:
        """Search Flipkart for products."""
        search_url = f"{self.BASE_URL}/search?q={query.replace(' ', '+')}"

        try:
            page, context = await browser_manager.get_page(search_url)
        except Exception as e:
            logger.error("flipkart_search_failed", query=query, error=str(e))
            return []

        products = []
        try:
            # Close login popup if present
            close_btn = await page.query_selector('button._2KpZ6l._2doB4z')
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)

            # Find product cards — Flipkart uses dynamic class names, use multiple selectors
            items = await page.query_selector_all('[data-id]')
            if not items:
                items = await page.query_selector_all('div._1AtVbE')

            for item in items[:max_results]:
                try:
                    product = await self._parse_search_result(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning("flipkart_parse_item_failed", error=str(e))
                    continue

            await asyncio.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            logger.error("flipkart_search_parse_failed", query=query, error=str(e))
        finally:
            await context.close()

        logger.info("flipkart_search_complete", query=query, results=len(products))
        return products

    async def _parse_search_result(self, element) -> Product | None:
        """Parse a single Flipkart search result."""
        # Try multiple selector patterns for title
        title = None
        for selector in ["a.IRpwTa", "a.s1Q9rs", "div._4rR01T", "a.WKTcLC"]:
            title_el = await element.query_selector(selector)
            if title_el:
                title = (await title_el.inner_text()).strip()
                break

        if not title:
            return None

        # URL
        link = None
        for selector in ["a.IRpwTa", "a.s1Q9rs", "a._1fQZEK", "a.CGtC98", "a.WKTcLC"]:
            link_el = await element.query_selector(selector)
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    link = f"{self.BASE_URL}{href}" if not href.startswith("http") else href
                    break

        # Price
        price = 0
        for selector in ["div._30jeq3", "div._25b18c"]:
            price_el = await element.query_selector(selector)
            if price_el:
                price_text = (await price_el.inner_text()).replace("₹", "").replace(",", "").strip()
                try:
                    price = float(price_text)
                    break
                except ValueError:
                    continue

        if price == 0:
            return None

        # Original price
        original_price = None
        orig_el = await element.query_selector("div._3I9_wc")
        if orig_el:
            orig_text = (await orig_el.inner_text()).replace("₹", "").replace(",", "").strip()
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating = None
        rating_el = await element.query_selector("div._3LWZlK")
        if rating_el:
            try:
                rating = float((await rating_el.inner_text()).strip())
            except ValueError:
                pass

        # Image
        img_el = await element.query_selector("img._396cs4, img._2r_T1I")
        image = await img_el.get_attribute("src") if img_el else ""

        discount = None
        if original_price and original_price > price:
            discount = round((1 - price / original_price) * 100, 1)

        return Product(
            id=str(uuid.uuid4()),
            title=title,
            brand=title.split(" ")[0] if title else "",
            price=PriceInfo(
                current=price,
                original=original_price,
                discount_percent=discount,
            ),
            url=link or "",
            source="flipkart",
            availability="in_stock",
            rating=rating,
            images=[image] if image else [],
        )

    async def get_product_details(self, url: str) -> Product | None:
        """Get detailed info from Flipkart product page."""
        try:
            page, context = await browser_manager.get_page(url)
        except Exception as e:
            logger.error("flipkart_detail_failed", url=url, error=str(e))
            return None

        try:
            # Close popup
            close_btn = await page.query_selector('button._2KpZ6l._2doB4z')
            if close_btn:
                await close_btn.click()

            title_el = await page.query_selector("span.B_NuCI, h1._9E25nV")
            title = (await title_el.inner_text()).strip() if title_el else "Unknown"

            price_el = await page.query_selector("div._30jeq3")
            price_text = (await price_el.inner_text()).replace("₹", "").replace(",", "").strip() if price_el else "0"
            try:
                price = float(price_text)
            except ValueError:
                price = 0

            # Specs
            specs = {}
            spec_rows = await page.query_selector_all("div._1UhVsV tr, div.X3BRps tr")
            for row in spec_rows[:20]:
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
                source="flipkart",
                availability="in_stock",
            )
        except Exception as e:
            logger.error("flipkart_detail_parse_failed", error=str(e))
            return None
        finally:
            await context.close()
