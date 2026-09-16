"""Task runner — drives one AgentLoop and records what it did.

This is the only execution path. It runs the loop in the API process as a
background task, which is what lets the live browser panel forward clicks into
the very same ``BrowserController`` the agent is using.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select

from app.api.routes.websocket import manager
from app.models.database import AsyncSessionLocal
from app.models.result import Result
from app.models.task import Task, TaskLog
from app.services.agent.loop import AgentLoop

logger = structlog.get_logger()

# Holds a reference to every in-flight run; without one, asyncio may collect
# the task mid-execution.
_running: set[asyncio.Task] = set()

# Events that are pure video and must never reach the database.
_TRANSIENT_ACTIONS = {"screencast_frame"}


def start_task_run(task_id: str, goal: str) -> None:
    """Kick off a task run in the background."""
    task = asyncio.create_task(run_task(task_id, goal))
    _running.add(task)
    task.add_done_callback(_running.discard)


async def run_task(task_id: str, goal: str) -> dict:
    """Run one task: execute the agent, stream events, persist the outcome."""
    task_uuid = uuid.UUID(task_id)

    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if not task:
            logger.error("Runner: task not found", task_id=task_id)
            return {"status": "failed", "error": "task not found"}

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        await _broadcast(task_id, {
            "task_id": task_id,
            "status": "running",
            "action": "task_started",
            "raw_event": {"goal": goal},
            "ui_event": {
                "type": "info",
                "message": "Task started",
                "step": 0,
                "timestamp": _now(),
            },
            "timestamp": _now(),
        })

        async def on_event(message: dict) -> None:
            action = message.get("action", "")
            if action not in _TRANSIENT_ACTIONS:
                db.add(TaskLog(
                    task_id=task_uuid,
                    step_number=message.get("step", 0),
                    action=action,
                    details=message.get("raw_event", {}),
                ))
                await db.commit()
            await _broadcast(task_id, message)

        agent = AgentLoop(task_id=task_id, goal=goal, on_event=on_event)

        try:
            final = await agent.run()
        except Exception as e:
            logger.error("Runner: agent raised", task_id=task_id, error=str(e), exc_info=True)
            final = {
                "status": "failed",
                "summary": f"Agent crashed: {str(e)[:200]}",
                "error": str(e),
                "results": [],
            }

        if final.get("results"):
            db.add(Result(
                task_id=task_uuid,
                data_type="extracted",
                data={"items": final["results"]},
                summary=final.get("summary", ""),
            ))

        task.status = final.get("status", "completed")
        task.completed_at = datetime.now(timezone.utc)
        # Keep the reason with the task, so a run that did not succeed explains
        # itself without having to dig through the event log.
        task.error_message = final.get("error") or (
            final.get("summary") if task.status != "completed" else None
        )
        await db.commit()

        await _broadcast(task_id, {
            "task_id": task_id,
            "status": task.status,
            "action": f"task_{task.status}",
            "raw_event": {
                "summary": final.get("summary", ""),
                "results": final.get("results", []),
                "error": final.get("error"),
            },
            "ui_event": {
                "type": "result" if task.status == "completed" else "error",
                "message": final.get("summary", task.status),
                "step": final.get("steps_executed", 0),
                "timestamp": _now(),
            },
            "timestamp": _now(),
        })

        logger.info("Runner finished", task_id=task_id, status=task.status)
        return final


async def _broadcast(task_id: str, message: dict) -> None:
    try:
        await manager.broadcast(task_id, message)
    except Exception as e:
        logger.debug("Broadcast failed", error=str(e)[:200])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
