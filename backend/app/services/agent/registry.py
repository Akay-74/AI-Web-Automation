"""Registry of in-flight agent loops, keyed by task id.

The WebSocket handler uses this to reach a running task's browser so a click in
the live panel lands in the real page, and to pass control commands
(take over, approve, cancel) to the loop.

The registry is per-process and deliberately so: forwarding user input needs
the actual ``BrowserController`` object, which cannot cross a process boundary.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.agent.loop import AgentLoop
    from app.services.browser.controller import BrowserController

_agents: dict[str, "AgentLoop"] = {}
_browsers: dict[str, "BrowserController"] = {}


def register_agent(task_id: str, agent: "AgentLoop", browser: "BrowserController") -> None:
    """Record a running task's agent and browser."""
    _agents[task_id] = agent
    _browsers[task_id] = browser


def unregister_agent(task_id: str) -> None:
    """Drop a finished task."""
    _agents.pop(task_id, None)
    _browsers.pop(task_id, None)


def get_agent(task_id: str) -> Optional["AgentLoop"]:
    """The running agent for *task_id*, or None."""
    return _agents.get(task_id)


def get_browser(task_id: str) -> Optional["BrowserController"]:
    """The running browser for *task_id*, or None."""
    return _browsers.get(task_id)
