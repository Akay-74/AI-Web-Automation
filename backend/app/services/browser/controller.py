"""Browser controller — Playwright wrapper with a CDP screencast, light
anti-detection, multi-tab handling, and CAPTCHA detection.

Actions arrive as ``{"action": ..., "params": {...}}`` and target elements by
the ``element_id`` the perception layer assigned, which this class resolves to
a selector just before executing.
"""

import asyncio
import random
from typing import Awaitable, Callable, Optional

import structlog
from playwright.async_api import (
    Browser,
    BrowserContext,
    CDPSession,
    Page,
    async_playwright,
)

from app.config import get_settings
from app.services.browser.state import BrowserState, InteractiveElement, TabInfo
from app.services.perception.element_mapper import ElementMapper
from app.services.perception.page_observer import extract_page_outline

logger = structlog.get_logger()

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Masks the automation flags that the cheapest bot checks read.
_STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
"""


# ---------------------------------------------------------------------------
# CAPTCHA detection (solving is left to the human)
# ---------------------------------------------------------------------------

_CAPTCHA_DOM_JS = """() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        const style = getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden';
    };

    if (visible(document.querySelector('#challenge-running, #challenge-form'))) return 'turnstile';

    const recaptcha = document.querySelector('.g-recaptcha');
    if (visible(recaptcha) && recaptcha.getAttribute('data-size') !== 'invisible') return 'recaptcha';

    if (visible(document.querySelector('.h-captcha'))) return 'hcaptcha';

    return null;
}"""


async def detect_captcha(page: Optional[Page]) -> Optional[str]:
    """Return the CAPTCHA type if a *visible* challenge is up, else None.

    Deliberately ignores the invisible reCAPTCHA v3 badge, which is present on
    a large share of the web and is not a challenge.
    """
    if not page:
        return None

    try:
        for frame in page.frames:
            url = frame.url
            if "google.com/recaptcha" in url:
                if "bframe" in url or ("anchor" in url and "size=invisible" not in url):
                    return "recaptcha"
            if "hcaptcha.com" in url and "/challenge" in url:
                return "hcaptcha"
            if "challenges.cloudflare.com" in url and "interactive" in url:
                return "turnstile"

        return await page.evaluate(_CAPTCHA_DOM_JS)
    except Exception as e:
        # A detection failure must not kill the step that triggered it.
        logger.debug("CAPTCHA detection failed", error=str(e)[:200])
        return None


# ---------------------------------------------------------------------------
# BrowserController
# ---------------------------------------------------------------------------

class BrowserController:
    """Owns the Playwright lifecycle, action execution, and the screencast."""

    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = True,
    ):
        self._settings = get_settings()
        self._user_data_dir = user_data_dir
        self._headless = headless
        self._viewport = {
            "width": self._settings.viewport_width,
            "height": self._settings.viewport_height,
        }

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cdp: Optional[CDPSession] = None

        self.element_mapper = ElementMapper()

        self._pages: list[Page] = []
        self._active_tab: int = 0

        self._screencast_running = False
        self._on_frame: Optional[Callable[[str], Awaitable[None]]] = None

        # Last known cursor position, for human-ish mouse paths.
        self._cursor = (0.0, 0.0)

        # Set while a human is solving a CAPTCHA; the agent waits on it.
        self._captcha_event = asyncio.Event()
        self._captcha_event.set()
        self._waiting_for_human = False

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def viewport_size(self) -> dict:
        """Viewport dimensions the frontend scales click coordinates against."""
        return dict(self._viewport)

    @property
    def waiting_for_human(self) -> bool:
        return self._waiting_for_human

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch Chromium (or a persistent profile) and open a CDP session."""
        self._playwright = await async_playwright().start()

        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ]
        context_options = {
            "viewport": dict(self._viewport),
            "user_agent": _USER_AGENT,
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }

        if self._user_data_dir:
            logger.info("Launching persistent browser profile", user_data_dir=self._user_data_dir)
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self._user_data_dir,
                headless=self._headless,
                args=launch_args,
                **context_options,
            )
            self._page = (
                self._context.pages[0]
                if self._context.pages
                else await self._context.new_page()
            )
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=launch_args,
            )
            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()

        await self._context.add_init_script(_STEALTH_INIT_SCRIPT)

        self._pages = [self._page]
        self._active_tab = 0
        self._cdp = await self._context.new_cdp_session(self._page)
        logger.info("Browser launched", headless=self._headless, viewport=self._viewport)

    async def close(self) -> None:
        """Stop the screencast and tear the browser down."""
        await self.stop_screencast()
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug("Browser close error", error=str(e)[:200])
        finally:
            if self._playwright:
                await self._playwright.stop()
            self._page = None
            self._pages = []
        logger.info("Browser closed")

    # ------------------------------------------------------------------
    # CDP screencast
    # ------------------------------------------------------------------

    async def start_screencast(self, on_frame: Callable[[str], Awaitable[None]]) -> None:
        """Stream JPEG frames from the browser to *on_frame* as base64.

        Frame size matches the viewport 1:1 so the frontend can map a click on
        the image straight back to a browser coordinate.
        """
        if self._screencast_running or not self._cdp:
            return

        fps = max(1, min(30, self._settings.screencast_fps))
        self._on_frame = on_frame
        self._screencast_running = True
        self._cdp.on("Page.screencastFrame", self._handle_screencast_frame)

        await self._cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": self._settings.screencast_quality,
            "maxWidth": self._viewport["width"],
            "maxHeight": self._viewport["height"],
            "everyNthFrame": max(1, round(60 / fps)),
        })
        logger.info("Screencast started", fps=fps, quality=self._settings.screencast_quality)

    async def _handle_screencast_frame(self, params: dict) -> None:
        try:
            if self._cdp:
                await self._cdp.send(
                    "Page.screencastFrameAck",
                    {"sessionId": params.get("sessionId", 0)},
                )
            if self._on_frame and params.get("data"):
                await self._on_frame(params["data"])
        except Exception as e:
            logger.debug("Screencast frame error", error=str(e)[:200])

    async def stop_screencast(self) -> None:
        """Stop the CDP screencast."""
        if not self._screencast_running or not self._cdp:
            return
        try:
            await self._cdp.send("Page.stopScreencast")
        except Exception:
            pass
        self._screencast_running = False
        self._on_frame = None
        logger.info("Screencast stopped")

    async def _switch_cdp_to(self, page: Page) -> None:
        """Point the screencast at a different tab."""
        on_frame = self._on_frame  # stop_screencast clears it
        await self.stop_screencast()
        self._cdp = await self._context.new_cdp_session(page)
        if on_frame:
            await self.start_screencast(on_frame)

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    async def get_browser_state(self) -> BrowserState:
        """Re-read the page: elements, outline, tabs."""
        if not self._page:
            return BrowserState()

        elements = await self.element_mapper.map_elements(self._page)
        outline = await extract_page_outline(self._page)

        open_tabs = []
        for idx, p in enumerate(self._pages):
            open_tabs.append(TabInfo(
                tab_id=idx,
                title=await _safe_title(p),
                url=p.url,
                active=(idx == self._active_tab),
            ))

        return BrowserState(
            active_tab=self._active_tab,
            open_tabs=open_tabs,
            current_url=self._page.url,
            page_title=await _safe_title(self._page),
            page_structure=outline,
            interactive_elements=elements,
        )

    def resolve_element(self, params: dict) -> Optional[InteractiveElement]:
        """Resolve the ``element_id`` in *params* against the current page."""
        element_id = params.get("element_id")
        if element_id is None:
            return None
        try:
            return self.element_mapper.get(int(element_id))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict) -> dict:
        """Execute one action. Returns ``{"success": bool, ...}``."""
        if not self._page and action != "navigate":
            return {"success": False, "error": "Browser has no open page"}

        handlers = {
            "navigate": lambda: self._navigate(params.get("url", "")),
            "click": lambda: self._click(params),
            "type": lambda: self._type(params),
            "hover": lambda: self._hover(params),
            "select": lambda: self._select(params),
            "keypress": lambda: self._keypress(params.get("key", "Enter")),
            "back": self._back,
            "scroll": lambda: self._scroll(
                params.get("direction", "down"),
                int(params.get("amount", 600)),
            ),
            "extract": self._extract,
            "wait": lambda: self._wait(params.get("seconds", 2)),
            "new_tab": self._new_tab,
            "switch_tab": lambda: self._switch_tab(int(params.get("tab_id", 0))),
            "close_tab": lambda: self._close_tab(int(params.get("tab_id", 0))),
            "get_tabs": self._get_tabs,
        }

        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}"}

        try:
            return await handler()
        except Exception as e:
            logger.error("Action raised", action=action, error=str(e)[:300])
            return {"success": False, "error": str(e)[:300]}

    def _selector_for(self, params: dict) -> Optional[str]:
        element = self.resolve_element(params)
        if element:
            return element.selector
        # A selector straight from params is a fallback for a model that
        # ignored the element list; it is allowed but rarely correct.
        return params.get("selector") or None

    async def _navigate(self, url: str) -> dict:
        if not url:
            return {"success": False, "error": "navigate needs a url"}
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            await self._page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self._settings.browser_timeout_ms,
            )
            # Let a client-side redirect land before anyone maps this page's
            # elements, or every id is stale the moment it is handed over.
            await self._settle()
            logger.info("Navigated", requested=url[:80], landed=self._page.url[:80])
            return {"success": True, "url": self._page.url}
        except Exception as e:
            logger.warning("Navigation failed", url=url[:120], error=str(e)[:200])
            return {"success": False, "error": str(e)[:300]}

    async def _settle(self, timeout: int = 4000) -> None:
        """Wait briefly for the page to stop moving. Never raises."""
        try:
            await self._page.wait_for_load_state("load", timeout=timeout)
        except Exception:
            pass
        try:
            await self._page.wait_for_timeout(300)
        except Exception:
            pass

    async def _click(self, params: dict) -> dict:
        selector = self._selector_for(params)
        if not selector:
            return {"success": False, "error": "click needs a valid element_id"}

        timeout = self._settings.action_timeout_ms
        locator = self._page.locator(selector).first
        try:
            box = await locator.bounding_box(timeout=timeout)
        except Exception:
            box = None

        try:
            if box:
                x = box["x"] + box["width"] / 2 + random.uniform(-2, 2)
                y = box["y"] + box["height"] / 2 + random.uniform(-2, 2)
                await self._move_cursor(x, y)
                await self._page.mouse.click(x, y)
            else:
                await locator.click(timeout=timeout)
        except Exception as e:
            logger.warning("Click failed", selector=selector[:60], error=str(e)[:200])
            return {"success": False, "error": str(e)[:300]}

        await self._settle()
        logger.info("Clicked", selector=selector[:60])
        return {"success": True, "url": self._page.url}

    async def _type(self, params: dict) -> dict:
        selector = self._selector_for(params)
        text = str(params.get("text", ""))
        if not selector:
            return {"success": False, "error": "type needs a valid element_id"}

        locator = self._page.locator(selector).first
        try:
            # fill() waits for the field to be editable, clears it, and fires the
            # input event in one shot. Clicking first then typing per character
            # loses the race whenever the click itself moves the page.
            await locator.fill(text, timeout=self._settings.action_timeout_ms)

            if params.get("submit"):
                await locator.press("Enter", timeout=self._settings.action_timeout_ms)
                await self._settle(timeout=10000)
        except Exception as e:
            logger.warning("Type failed", selector=selector[:60], error=str(e)[:200])
            return {"success": False, "error": str(e)[:300]}

        logger.info("Typed", selector=selector[:60], text=text[:40], submitted=bool(params.get("submit")))
        return {"success": True, "url": self._page.url}

    async def _hover(self, params: dict) -> dict:
        selector = self._selector_for(params)
        if not selector:
            return {"success": False, "error": "hover needs a valid element_id"}
        await self._page.locator(selector).first.hover(timeout=self._settings.action_timeout_ms)
        return {"success": True}

    async def _select(self, params: dict) -> dict:
        selector = self._selector_for(params)
        if not selector:
            return {"success": False, "error": "select needs a valid element_id"}
        await self._page.locator(selector).first.select_option(
            str(params.get("value", "")),
            timeout=self._settings.action_timeout_ms,
        )
        await self._settle()
        return {"success": True}

    async def _keypress(self, key: str) -> dict:
        await self._page.keyboard.press(key)
        return {"success": True}

    async def _back(self) -> dict:
        await self._page.go_back(timeout=self._settings.browser_timeout_ms)
        return {"success": True, "url": self._page.url}

    async def _scroll(self, direction: str, amount: int) -> dict:
        delta = amount if direction == "down" else -amount
        await self._page.mouse.wheel(0, delta)
        await asyncio.sleep(0.3)  # let lazy content paint
        return {"success": True}

    async def _wait(self, seconds) -> dict:
        try:
            seconds = max(0.0, min(10.0, float(seconds)))
        except (ValueError, TypeError):
            seconds = 2.0
        await asyncio.sleep(seconds)
        return {"success": True}

    async def _extract(self) -> dict:
        content = await self._page.locator("body").inner_text()
        return {"success": True, "content": content}

    async def _move_cursor(self, x: float, y: float) -> None:
        """Move the mouse in a few steps rather than teleporting."""
        start_x, start_y = self._cursor
        steps = random.randint(3, 6)
        for i in range(1, steps + 1):
            t = i / steps
            await self._page.mouse.move(
                start_x + (x - start_x) * t,
                start_y + (y - start_y) * t,
            )
        self._cursor = (x, y)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    async def _new_tab(self) -> dict:
        page = await self._context.new_page()
        self._pages.append(page)
        self._active_tab = len(self._pages) - 1
        self._page = page
        await self._switch_cdp_to(page)
        logger.info("New tab opened", tab_id=self._active_tab)
        return {"success": True, "tab_id": self._active_tab}

    async def _switch_tab(self, tab_id: int) -> dict:
        if not 0 <= tab_id < len(self._pages):
            return {"success": False, "error": f"tab_id {tab_id} out of range (0-{len(self._pages) - 1})"}
        self._active_tab = tab_id
        self._page = self._pages[tab_id]
        await self._switch_cdp_to(self._page)
        return {"success": True, "tab_id": tab_id, "url": self._page.url}

    async def _close_tab(self, tab_id: int) -> dict:
        if not 0 <= tab_id < len(self._pages):
            return {"success": False, "error": f"tab_id {tab_id} out of range"}
        if len(self._pages) == 1:
            return {"success": False, "error": "Cannot close the only open tab"}

        page = self._pages.pop(tab_id)
        await page.close()
        self._active_tab = min(tab_id, len(self._pages) - 1)
        self._page = self._pages[self._active_tab]
        await self._switch_cdp_to(self._page)
        return {"success": True, "closed_tab_id": tab_id, "active_tab_id": self._active_tab}

    async def _get_tabs(self) -> dict:
        tabs = [
            {
                "tab_id": idx,
                "title": await _safe_title(page),
                "url": page.url,
                "active": idx == self._active_tab,
            }
            for idx, page in enumerate(self._pages)
        ]
        return {"success": True, "tabs": tabs}

    # ------------------------------------------------------------------
    # Input forwarded from the frontend viewer
    # ------------------------------------------------------------------

    async def handle_user_click(self, x: float, y: float) -> None:
        """Click at a viewport coordinate on the human's behalf."""
        if not self._page:
            return
        try:
            await self._page.mouse.click(x, y)
            self._cursor = (x, y)
            logger.info("User click forwarded", x=round(x), y=round(y))
        except Exception as e:
            logger.warning("User click failed", error=str(e)[:200])

    async def handle_user_type(self, text: str) -> None:
        """Type text on the human's behalf."""
        if not self._page:
            return
        try:
            await self._page.keyboard.type(text, delay=20)
        except Exception as e:
            logger.warning("User type failed", error=str(e)[:200])

    async def handle_user_keypress(self, key: str) -> None:
        """Press a key on the human's behalf."""
        if not self._page:
            return
        try:
            await self._page.keyboard.press(key)
        except Exception as e:
            logger.warning("User keypress failed", error=str(e)[:200])

    async def handle_user_scroll(self, delta_x: float, delta_y: float) -> None:
        """Scroll on the human's behalf."""
        if not self._page:
            return
        try:
            await self._page.mouse.wheel(delta_x, delta_y)
        except Exception as e:
            logger.warning("User scroll failed", error=str(e)[:200])

    # ------------------------------------------------------------------
    # Human-in-the-loop CAPTCHA
    # ------------------------------------------------------------------

    async def pause_for_human_captcha(self, timeout: float) -> bool:
        """Block until the human solves the CAPTCHA. False if *timeout* elapsed."""
        self._captcha_event.clear()
        self._waiting_for_human = True
        logger.info("Waiting for human to solve CAPTCHA", timeout=timeout)
        try:
            await asyncio.wait_for(self._captcha_event.wait(), timeout=timeout)
            logger.info("Human solved CAPTCHA")
            return True
        except asyncio.TimeoutError:
            logger.warning("CAPTCHA wait timed out")
            return False
        finally:
            self._waiting_for_human = False
            self._captcha_event.set()

    def resume_after_captcha(self) -> None:
        """Unblock the agent — the human says the CAPTCHA is solved."""
        self._captcha_event.set()


async def _safe_title(page: Page) -> str:
    try:
        return await page.title()
    except Exception:
        return ""
