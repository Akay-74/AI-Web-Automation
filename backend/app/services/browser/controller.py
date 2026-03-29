"""Browser Controller — Playwright wrapper with retry logic.

Provides navigate, click, type, scroll, extract, screenshot actions
with configurable timeouts and exponential‑backoff retries.
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class BrowserController:
    """Manages the Playwright browser lifecycle and actions."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._settings = get_settings()

    @property
    def page(self) -> Page:
        return self._page

    async def launch(self):
        """Launch a Chromium browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info("Browser launched")

    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    # ------ retry helper ------

    async def _retry(self, coro_factory, retries: int = 2, base_delay: float = 1.0, label: str = "operation"):
        """Retry a coroutine with exponential backoff.

        `coro_factory` is a callable that returns a new awaitable each time.
        """
        last_error = None
        for attempt in range(1 + retries):
            try:
                return await coro_factory()
            except Exception as e:
                last_error = e
                if attempt < retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Retrying {label}", attempt=attempt + 1, delay=delay, error=str(e)[:200])
                    await asyncio.sleep(delay)
        raise last_error

    # ------ actions ------

    async def execute(self, step: dict) -> dict:
        """Execute a single browser action from a plan step."""
        action = step.get("action", "unknown")
        params = step.get("params", {})

        try:
            if action == "navigate":
                return await self._navigate(params.get("url", "https://www.google.com"))
            elif action == "click":
                return await self._click(params.get("selector", ""))
            elif action == "type":
                return await self._type(params.get("selector", ""), params.get("text", ""))
            elif action == "scroll":
                return await self._scroll(params.get("direction", "down"), params.get("amount", 500))
            elif action == "extract":
                return await self._extract()
            elif action == "wait":
                await asyncio.sleep(params.get("seconds", 2))
                return {"success": True}
            elif action == "evaluate":
                # Handled by agent loop, not the browser
                return {"success": True}
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Action failed: {action}", error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _navigate(self, url: str) -> dict:
        """Navigate with retry and networkidle."""
        timeout = self._settings.browser_timeout_ms

        async def _do_nav():
            await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        try:
            await self._retry(_do_nav, retries=2, label=f"navigate {url[:60]}")
            logger.info("Navigated", url=url[:120])
            return {"success": True, "url": self._page.url}
        except Exception as e:
            logger.error("Navigation failed", url=url[:120], error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _click(self, selector: str) -> dict:
        """Click with retry."""
        timeout = self._settings.browser_timeout_ms

        async def _do_click():
            await self._page.click(selector, timeout=timeout)

        try:
            await self._retry(_do_click, retries=1, label=f"click {selector[:40]}")
            logger.info("Clicked", selector=selector[:60])
            await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            return {"success": True}
        except Exception as e:
            logger.error("Click failed", selector=selector[:60], error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _type(self, selector: str, text: str) -> dict:
        """Type text into an element."""
        try:
            await self._page.fill(selector, text, timeout=self._settings.browser_timeout_ms)
            logger.info("Typed text", selector=selector[:60], text=text[:40])
            return {"success": True}
        except Exception as e:
            logger.error("Type failed", selector=selector[:60], error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page."""
        try:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)
            await asyncio.sleep(1)
            logger.info("Scrolled", direction=direction, amount=amount)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _extract(self) -> dict:
        """Extract page content for LLM processing."""
        try:
            # Get visible text instead of raw HTML (to avoid <head> boilerplate)
            content = await self._page.locator("body").inner_text()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_html(self) -> str:
        """Return raw HTML of the current page."""
        return await self._page.content()

    async def screenshot(self) -> bytes:
        """Capture a PNG screenshot of the current page."""
        return await self._page.screenshot(type="png")
