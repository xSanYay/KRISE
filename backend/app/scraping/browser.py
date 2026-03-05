"""Playwright browser pool manager."""

from __future__ import annotations
import asyncio
import random
import structlog
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = structlog.get_logger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]


class BrowserManager:
    """Manages a Playwright browser instance with anti-detection."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Initialize playwright and launch browser."""
        if self._browser is not None:
            return

        async with self._lock:
            if self._browser is not None:
                return
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            logger.info("browser_started")

    async def stop(self):
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("browser_stopped")

    async def new_context(self) -> BrowserContext:
        """Create a new browser context with random user agent."""
        if not self._browser:
            await self.start()

        ua = random.choice(USER_AGENTS)
        context = await self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        return context

    async def get_page(self, url: str) -> tuple[Page, BrowserContext]:
        """Open a page with anti-detection and return page + context."""
        context = await self.new_context()
        page = await context.new_page()

        # Block unnecessary resources to speed up scraping
        excluded_resource_types = ["image", "stylesheet", "font", "media", "other"]
        await page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in excluded_resource_types
            else route.continue_()
        )

        # Anti-detection script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            # wait_until="domcontentloaded" is faster than networkidle
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait a small bit for dynamic JS content to render
            await page.wait_for_timeout(500)
        except Exception as e:
            logger.warning("page_load_warning", url=url, error=str(e))

        return page, context


# Singleton instance
browser_manager = BrowserManager()
