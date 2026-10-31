"""WebSocket endpoint for live task updates and user input.

One transport, both directions:
  * server → client: agent events and screencast frames, pushed by the running
    loop through ``manager.broadcast``.
  * client → server: clicks, keystrokes, and control commands, forwarded to the
    task's ``BrowserController`` / ``AgentLoop`` via the agent registry.

There is no database polling and no message broker in this path. The agent runs
in this process, so it hands its events straight to the connection manager.
"""

import asyncio
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.auth import websocket_authorized
from app.services.agent.registry import get_agent, get_browser

logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """Tracks the open sockets watching each task."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(task_id, []).append(websocket)
        logger.info("WebSocket connected", task_id=task_id, watchers=len(self.active[task_id]))

    def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        sockets = self.active.get(task_id)
        if not sockets:
            return
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            del self.active[task_id]
        logger.info("WebSocket disconnected", task_id=task_id)

    async def broadcast(self, task_id: str, message: dict) -> None:
        """Push one message to every socket watching *task_id*."""
        sockets = self.active.get(task_id)
        if not sockets:
            return

        dead = []
        for ws in list(sockets):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)


manager = ConnectionManager()


async def _handle_user_message(task_id: str, data: dict) -> None:
    """Apply one inbound command from the live browser panel."""
    action = data.get("user_action")
    if not action:
        return

    agent = get_agent(task_id)
    browser = get_browser(task_id)

    if agent:
        if action == "take_control":
            await agent.control.take_control()
            return
        if action in ("give_control_back", "resume_ai", "resume"):
            await agent.control.give_control_back()
            return
        if action == "pause":
            await agent.control.pause_for_human()
            return
        if action == "approve_action":
            await agent.control.respond_to_approval(True)
            return
        if action == "reject_action":
            await agent.control.respond_to_approval(False)
            return
        if action == "cancel":
            agent.cancel()
            return

    if not browser:
        logger.debug("Input for a task with no live browser", task_id=task_id, user_action=action)
        return

    if action == "click":
        await browser.handle_user_click(float(data.get("x", 0)), float(data.get("y", 0)))
    elif action == "type":
        await browser.handle_user_type(str(data.get("text", "")))
    elif action == "keypress":
        await browser.handle_user_keypress(str(data.get("key", "Enter")))
    elif action == "scroll":
        await browser.handle_user_scroll(
            float(data.get("deltaX", 0)),
            float(data.get("deltaY", 0)),
        )
    elif action == "captcha_resume":
        browser.resume_after_captcha()
        if agent:
            await agent.control.give_control_back()


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: UUID):
    """Stream a task's events, and accept user input for its browser."""
    if not websocket_authorized(websocket):
        # 1008 = policy violation; closing before accept rejects the handshake.
        await websocket.close(code=1008)
        return

    task_id_str = str(task_id)
    await manager.connect(task_id_str, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                await _handle_user_message(task_id_str, data)
            except Exception as e:
                logger.warning("User command failed", task_id=task_id_str, error=str(e)[:200])
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("WebSocket error", task_id=task_id_str, error=str(e)[:200])
    finally:
        manager.disconnect(task_id_str, websocket)
