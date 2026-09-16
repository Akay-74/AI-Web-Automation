"""Page observation — what the agent can see besides the element list.

Two jobs:
  * ``extract_page_outline`` — headings plus a visible-text preview, so the
    planner knows what the page actually says, not just what it can click.
  * ``detect_auto_pause_triggers`` — spots a page that needs the human
    (a login form, a one-time code prompt) so the agent hands over instead of
    typing the user's credentials itself.

Both run as one ``page.evaluate`` each, reading the rendered DOM. There is no
HTML re-parsing step: the browser already built the tree.
"""

import structlog

from app.services.browser.state import PageStructure

logger = structlog.get_logger()


_OUTLINE_JS = """() => {
    const headings = [];
    for (const h of document.querySelectorAll('h1, h2, h3')) {
        const text = (h.innerText || '').trim();
        if (!text) continue;
        headings.push({ level: h.tagName.toLowerCase(), text: text.slice(0, 150) });
        if (headings.length >= 15) break;
    }

    // Visible text only — skip script/style/nav chrome that the renderer hides.
    const body = document.body;
    const text = body ? (body.innerText || '') : '';
    const preview = text.split('\\n')
        .map(l => l.trim())
        .filter(Boolean)
        .join('\\n')
        .slice(0, 4000);

    return {
        headings,
        text_preview: preview,
        links_count: document.querySelectorAll('a[href]').length,
        images_count: document.querySelectorAll('img').length,
    };
}"""


async def extract_page_outline(page) -> PageStructure:
    """Read headings and a visible-text preview from the current page."""
    try:
        raw = await page.evaluate(_OUTLINE_JS)
    except Exception as e:
        logger.warning("Page outline extraction failed", error=str(e)[:200])
        return PageStructure()

    return PageStructure(
        headings=raw.get("headings", []),
        text_preview=raw.get("text_preview", ""),
        links_count=raw.get("links_count", 0),
        images_count=raw.get("images_count", 0),
    )


class AutoPauseResult:
    """Whether the agent should hand the browser to the human."""

    def __init__(self, should_pause: bool = False, trigger_type: str = "", reason: str = ""):
        self.should_pause = should_pause
        self.trigger_type = trigger_type
        self.reason = reason


# Only signals that genuinely need the person: a credential prompt the agent
# must not fill in itself. Matching OAuth buttons or any input named "code"
# fires on ordinary pages and strands the agent mid-task.
_AUTO_PAUSE_JS = """() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        const style = getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    };

    for (const pw of document.querySelectorAll('input[type="password"]')) {
        if (visible(pw)) {
            return { type: 'login_page', reason: 'A password field is on screen' };
        }
    }

    for (const otp of document.querySelectorAll('input[autocomplete="one-time-code"]')) {
        if (visible(otp)) {
            return { type: 'two_factor', reason: 'A one-time code prompt is on screen' };
        }
    }

    return null;
}"""


async def detect_auto_pause_triggers(page) -> AutoPauseResult:
    """Detect a page that the human should handle instead of the agent."""
    try:
        trigger = await page.evaluate(_AUTO_PAUSE_JS)
    except Exception as e:
        logger.debug("Auto-pause detection failed", error=str(e)[:200])
        return AutoPauseResult()

    if not trigger:
        return AutoPauseResult()

    logger.info(
        "Auto-pause trigger detected",
        trigger=trigger.get("type"),
        reason=trigger.get("reason"),
    )
    return AutoPauseResult(
        should_pause=True,
        trigger_type=trigger.get("type", "auto_pause"),
        reason=trigger.get("reason", "Human attention needed"),
    )
