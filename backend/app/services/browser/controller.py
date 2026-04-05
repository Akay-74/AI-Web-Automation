"""Browser Controller — Playwright wrapper with CDP screencast,
anti-detection stealth, human-like input simulation, and CAPTCHA solving.

Key upgrades over the original screenshot-based controller:
  • CDP Screencast: streams compressed JPEG frames at ~5 FPS via
    ``Page.startScreencast`` instead of taking expensive PNG screenshots.
  • Stealth: applies ``playwright_stealth`` to mask automation flags so
    websites see a regular Chrome browser.
  • Human-like input: bezier-curve mouse movement and randomised keystroke
    delays to defeat behavioural bot-detection.
  • CAPTCHA solver: optional integration with 2Captcha / CapSolver APIs —
    detects reCAPTCHA / hCaptcha iframes and auto-solves them.
"""

import asyncio
import math
import random
from typing import Optional, Callable, Awaitable, List, Tuple

from playwright.async_api import (
    async_playwright, Page, Browser, BrowserContext, CDPSession,
)
import structlog

from app.config import get_settings

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Helpers: human-like mouse & keyboard
# ---------------------------------------------------------------------------

def _bezier_curve(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 20,
) -> List[Tuple[float, float]]:
    """Generate points along a cubic bezier curve between *start* and *end*.

    Two random control points are placed to simulate the natural arc a
    human hand takes when moving a mouse.
    """
    sx, sy = start
    ex, ey = end
    # Random control points offset from the straight line
    cp1 = (
        sx + (ex - sx) * random.uniform(0.2, 0.4) + random.uniform(-80, 80),
        sy + (ey - sy) * random.uniform(0.0, 0.3) + random.uniform(-80, 80),
    )
    cp2 = (
        sx + (ex - sx) * random.uniform(0.6, 0.8) + random.uniform(-80, 80),
        sy + (ey - sy) * random.uniform(0.7, 1.0) + random.uniform(-80, 80),
    )

    points: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = (u**3 * sx + 3 * u**2 * t * cp1[0]
             + 3 * u * t**2 * cp2[0] + t**3 * ex)
        y = (u**3 * sy + 3 * u**2 * t * cp1[1]
             + 3 * u * t**2 * cp2[1] + t**3 * ey)
        points.append((x, y))
    return points


async def _human_move(page: Page, x: float, y: float) -> None:
    """Move mouse to (*x*, *y*) along a bezier curve with jitter."""
    try:
        current = await page.evaluate("() => ({x: window._lastMouseX || 0, y: window._lastMouseY || 0})")
        start = (current.get("x", 0), current.get("y", 0))
    except Exception:
        start = (0, 0)

    for px, py in _bezier_curve(start, (x, y), steps=random.randint(15, 30)):
        await page.mouse.move(px, py)
        await asyncio.sleep(random.uniform(0.005, 0.02))

    # Remember position for next move
    await page.evaluate(f"() => {{ window._lastMouseX = {x}; window._lastMouseY = {y}; }}")


async def _human_type(page: Page, selector: str, text: str, timeout: int) -> None:
    """Type *text* into *selector* with randomised per-key delays."""
    await page.click(selector, timeout=timeout)
    await page.fill(selector, "", timeout=timeout)  # clear first
    for ch in text:
        await page.keyboard.type(ch, delay=random.randint(40, 160))
        # occasional micro-pause
        if random.random() < 0.08:
            await asyncio.sleep(random.uniform(0.15, 0.4))


# ---------------------------------------------------------------------------
# CAPTCHA detection & solving
# ---------------------------------------------------------------------------

async def _detect_captcha(page: Page) -> Optional[str]:
    """Return the CAPTCHA type if a **visible challenge** is detected, else ``None``.

    Strictly avoids false positives (like the reCAPTCHA v3 invisible badge).
    """
    try:
        # 1. Check iframes for actual challenge URLs
        for iframe in page.frames:
            url = iframe.url
            # reCAPTCHA v2 active challenge popup
            if "google.com/recaptcha" in url and "bframe" in url:
                return "recaptcha"
            # reCAPTCHA v2 "I'm not a robot" checkbox (must NOT be the invisible badge)
            if "google.com/recaptcha" in url and "anchor" in url and "size=invisible" not in url:
                return "recaptcha"
            
            # hCaptcha active challenge
            if "hcaptcha.com" in url and "/challenge" in url:
                return "hcaptcha"
                
            # Cloudflare Turnstile interactive challenge frame
            if "challenges.cloudflare.com" in url and "interactive" in url:
                return "turnstile"

        # 2. Check for Cloudflare full-page block in DOM
        visible = await page.evaluate("""() => {
            const isVis = (el) => el && el.offsetWidth > 0 && el.offsetHeight > 0 && getComputedStyle(el).display !== 'none';
            if (isVis(document.querySelector('#challenge-running, #challenge-form'))) return 'turnstile';
            return null;
        }""")
        if visible:
            return visible

    except Exception:
        pass
    return None


async def _solve_captcha(page: Page, captcha_type: str, settings) -> bool:
    """Attempt to solve a CAPTCHA via a third-party solver API.

    Requires ``CAPTCHA_API_KEY`` to be set in the environment.  If not set,
    logs a warning and returns ``False``.
    """
    api_key = getattr(settings, "captcha_api_key", "")
    if not api_key:
        logger.warning("CAPTCHA detected but no CAPTCHA_API_KEY configured")
        return False

    try:
        import httpx

        # Extract the sitekey from the page
        sitekey = await page.evaluate("""() => {
            const el = document.querySelector('[data-sitekey]');
            return el ? el.getAttribute('data-sitekey') : null;
        }""")

        if not sitekey:
            logger.warning("CAPTCHA detected but sitekey not found in DOM")
            return False

        page_url = page.url

        # Use 2Captcha API format
        async with httpx.AsyncClient(timeout=120) as client:
            # Submit CAPTCHA task
            captcha_type_param = "userrecaptcha" if captcha_type == "recaptcha" else "hcaptcha"
            submit_resp = await client.get(
                "https://2captcha.com/in.php",
                params={
                    "key": api_key,
                    "method": captcha_type_param,
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                },
            )
            submit_data = submit_resp.json()

            if submit_data.get("status") != 1:
                logger.error("CAPTCHA submit rejected", response=submit_data)
                return False

            captcha_id = submit_data["request"]
            logger.info("CAPTCHA submitted to solver", captcha_id=captcha_id)

            # Poll for solution (max 120s)
            for _ in range(24):
                await asyncio.sleep(5)
                poll_resp = await client.get(
                    "https://2captcha.com/res.php",
                    params={"key": api_key, "action": "get", "id": captcha_id, "json": 1},
                )
                poll_data = poll_resp.json()

                if poll_data.get("status") == 1:
                    token = poll_data["request"]
                    # Inject solution token into the page
                    await page.evaluate(f"""() => {{
                        document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                        if (typeof ___grecaptcha_cfg !== 'undefined') {{
                            Object.entries(___grecaptcha_cfg.clients).forEach(([k,v]) => {{
                                const cb = v?.S?.S?.callback || v?.S?.callback;
                                if (cb) cb('{token}');
                            }});
                        }}
                    }}""")
                    logger.info("CAPTCHA solved and injected")
                    return True

                if "CAPCHA_NOT_READY" not in str(poll_data.get("request", "")):
                    logger.error("CAPTCHA solve failed", response=poll_data)
                    return False

        logger.warning("CAPTCHA solve timed out")
        return False

    except Exception as e:
        logger.error("CAPTCHA solver error", error=str(e)[:300])
        return False


# ---------------------------------------------------------------------------
# BrowserController
# ---------------------------------------------------------------------------

class BrowserController:
    """Manages the Playwright browser lifecycle, actions, CDP screencast,
    and anti-detection measures."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cdp: Optional[CDPSession] = None
        self._settings = get_settings()

        # Screencast state
        self._screencast_running = False
        self._on_frame: Optional[Callable[[str], Awaitable[None]]] = None

        # Human-in-the-loop CAPTCHA: agent pauses here until human solves it
        self._captcha_event = asyncio.Event()
        self._captcha_event.set()  # starts unblocked
        self._waiting_for_human = False

    @property
    def page(self) -> Page:
        return self._page

    @property
    def viewport_size(self) -> dict:
        """Return the browser viewport dimensions for coordinate scaling."""
        return {"width": 1920, "height": 1080}

    @property
    def waiting_for_human(self) -> bool:
        return self._waiting_for_human

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch a stealthy Chromium browser and optionally start screencast."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Apply stealth patches (mask webdriver flags, plugin arrays, etc.)
        try:
            from playwright_stealth import stealth_async
            await stealth_async(self._context)
            logger.info("Stealth patches applied")
        except ImportError:
            logger.warning("playwright-stealth not installed — skipping stealth patches")

        self._page = await self._context.new_page()

        # Extra stealth: override navigator.webdriver at page level
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        # Open a CDP session for screencast
        self._cdp = await self._page.context.new_cdp_session(self._page)
        logger.info("Browser launched with stealth + CDP session")

    async def close(self) -> None:
        """Stop screencast, close browser, and release resources."""
        await self.stop_screencast()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    # ------------------------------------------------------------------
    # CDP Screencast
    # ------------------------------------------------------------------

    async def start_screencast(
        self,
        on_frame: Callable[[str], Awaitable[None]],
        fps: int = 60,
        quality: int = 60,
    ) -> None:
        """Begin streaming JPEG frames from the browser via CDP.

        Args:
            on_frame: async callback receiving a base64-encoded JPEG string.
            fps: informational — everyNthFrame is always 1 for max smoothness.
            quality: JPEG quality 1-100 (default 60 — crisp but efficient).
        """
        if self._screencast_running or not self._cdp:
            return

        self._on_frame = on_frame
        self._screencast_running = True

        # Listen for frames from the CDP session
        self._cdp.on("Page.screencastFrame", self._handle_screencast_frame)

        await self._cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": quality,
            "maxWidth": 1920,
            "maxHeight": 1080,
            "everyNthFrame": 1,  # every single rendered frame
        })
        logger.info("CDP screencast started", quality=quality)

    async def _handle_screencast_frame(self, params: dict) -> None:
        """Process an incoming screencast frame from CDP."""
        try:
            session_id = params.get("sessionId", 0)
            # Acknowledge the frame so CDP keeps sending
            if self._cdp:
                await self._cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
            # Forward base64 JPEG data to the callback
            if self._on_frame and params.get("data"):
                await self._on_frame(params["data"])
        except Exception as e:
            logger.debug("Screencast frame error", error=str(e)[:200])

    async def stop_screencast(self) -> None:
        """Stop the CDP screencast stream."""
        if not self._screencast_running or not self._cdp:
            return
        try:
            await self._cdp.send("Page.stopScreencast")
        except Exception:
            pass
        self._screencast_running = False
        self._on_frame = None
        logger.info("CDP screencast stopped")

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _retry(
        self,
        coro_factory,
        retries: int = 2,
        base_delay: float = 1.0,
        label: str = "operation",
    ):
        """Retry a coroutine with exponential backoff."""
        last_error = None
        for attempt in range(1 + retries):
            try:
                return await coro_factory()
            except Exception as e:
                last_error = e
                if attempt < retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Retrying {label}",
                        attempt=attempt + 1, delay=delay, error=str(e)[:200],
                    )
                    await asyncio.sleep(delay)
        raise last_error

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def execute(self, step: dict) -> dict:
        """Execute a single browser action from a plan step.

        CAPTCHA detection/handling is done by the AgentLoop after each
        action — not here — so it can broadcast events to the frontend.
        """
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
                return {"success": True}
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Action failed: {action}", error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _navigate(self, url: str) -> dict:
        """Navigate with retry, networkidle, and a small human pause."""
        timeout = self._settings.browser_timeout_ms

        async def _do_nav():
            await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        try:
            await self._retry(_do_nav, retries=2, label=f"navigate {url[:60]}")
            # Small random pause to appear human
            await asyncio.sleep(random.uniform(0.5, 1.5))
            logger.info("Navigated", url=url[:120])
            return {"success": True, "url": self._page.url}
        except Exception as e:
            logger.error("Navigation failed", url=url[:120], error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _click(self, selector: str) -> dict:
        """Click with human-like mouse movement and retry."""
        timeout = self._settings.browser_timeout_ms

        async def _do_click():
            # Get element bounding box for human-like movement
            try:
                box = await self._page.locator(selector).first.bounding_box(timeout=timeout)
                if box:
                    target_x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
                    target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                    await _human_move(self._page, target_x, target_y)
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                    await self._page.mouse.click(target_x, target_y)
                else:
                    await self._page.click(selector, timeout=timeout)
            except Exception:
                # Fallback to standard click
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
        """Type text with human-like keystroke delays."""
        try:
            await _human_type(self._page, selector, text, self._settings.browser_timeout_ms)
            logger.info("Typed text", selector=selector[:60], text=text[:40])
            return {"success": True}
        except Exception as e:
            logger.error("Type failed", selector=selector[:60], error=str(e)[:300])
            return {"success": False, "error": str(e)}

    async def _scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page with a small natural pause."""
        try:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)
            await asyncio.sleep(random.uniform(0.8, 1.5))
            logger.info("Scrolled", direction=direction, amount=amount)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _extract(self) -> dict:
        """Extract page content for LLM processing."""
        try:
            content = await self._page.locator("body").inner_text()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_html(self) -> str:
        """Return raw HTML of the current page."""
        return await self._page.content()

    async def screenshot(self) -> bytes:
        """Capture a PNG screenshot (fallback for non-screencast callers)."""
        return await self._page.screenshot(type="png")

    # ------------------------------------------------------------------
    # User input forwarding (interactive browser from frontend)
    # ------------------------------------------------------------------

    async def handle_user_click(self, x: float, y: float) -> None:
        """Forward a user's mouse click from the frontend to the browser.

        Coordinates should be in the browser viewport space (1920×1080).
        """
        if not self._page:
            return
        try:
            await self._page.mouse.click(x, y)
            logger.info("User click forwarded", x=round(x), y=round(y))
        except Exception as e:
            logger.warning("User click failed", error=str(e)[:200])

    async def handle_user_type(self, text: str) -> None:
        """Forward keyboard text input from the frontend."""
        if not self._page:
            return
        try:
            await self._page.keyboard.type(text, delay=50)
            logger.info("User type forwarded", text=text[:40])
        except Exception as e:
            logger.warning("User type failed", error=str(e)[:200])

    async def handle_user_keypress(self, key: str) -> None:
        """Forward a special key press (Enter, Tab, Escape, etc.)."""
        if not self._page:
            return
        try:
            await self._page.keyboard.press(key)
            logger.info("User keypress forwarded", key=key)
        except Exception as e:
            logger.warning("User keypress failed", error=str(e)[:200])

    async def handle_user_scroll(self, delta_x: float, delta_y: float) -> None:
        """Forward a scroll event from the frontend."""
        if not self._page:
            return
        try:
            await self._page.mouse.wheel(delta_x, delta_y)
            logger.info("User scroll forwarded", dx=round(delta_x), dy=round(delta_y))
        except Exception as e:
            logger.warning("User scroll failed", error=str(e)[:200])

    # ------------------------------------------------------------------
    # Human-in-the-loop CAPTCHA
    # ------------------------------------------------------------------

    async def pause_for_human_captcha(self) -> None:
        """Block the agent loop until a human has solved the CAPTCHA.

        The frontend calls ``resume_after_captcha()`` to unblock.
        """
        self._captcha_event.clear()
        self._waiting_for_human = True
        logger.info("Agent paused — waiting for human to solve CAPTCHA")
        await self._captcha_event.wait()
        self._waiting_for_human = False
        logger.info("Agent resumed after human CAPTCHA solve")

    def resume_after_captcha(self) -> None:
        """Unblock the agent loop after the human has solved the CAPTCHA."""
        self._captcha_event.set()

