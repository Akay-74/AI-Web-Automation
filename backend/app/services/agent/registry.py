"""Global registry of running agent loops.

Allows the WebSocket input handler to look up a running agent's
BrowserController by task_id and forward user interactions (clicks,
key presses, CAPTCHA resume signals).
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.browser.controller import BrowserController

# task_id (str) → BrowserController
_active_browsers: dict[str, "BrowserController"] = {}


def register_browser(task_id: str, browser: "BrowserController") -> None:
    """Register a browser controller for a running task."""
    _active_browsers[task_id] = browser


def unregister_browser(task_id: str) -> None:
    """Remove a browser controller when a task finishes."""
    _active_browsers.pop(task_id, None)


def get_browser(task_id: str) -> Optional["BrowserController"]:
    """Get the browser controller for a running task, or None."""
    return _active_browsers.get(task_id)
