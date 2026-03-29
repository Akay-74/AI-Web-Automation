"""Task API routes — CRUD and agent control."""

import asyncio
import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import json

from app.config import get_settings
from app.models.database import get_db, AsyncSessionLocal
from app.models.task import Task, TaskLog
from app.models.result import Result
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskLogResponse, TaskListResponse,
)

logger = structlog.get_logger()
router = APIRouter(tags=["tasks"])

# ---------- helpers ----------

async def _redis_available() -> bool:
    """Check if Redis is reachable."""
    try:
        import redis.asyncio as aioredis
        settings = get_settings()
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.close()
        return True
    except Exception:
        return False


async def _run_agent_background(task_id: str, goal: str):
    """Run AgentLoop directly in a background coroutine (Redis‑free fallback)."""
    import uuid as _uuid
    import redis.asyncio as aioredis
    from app.services.agent.loop import AgentLoop

    # Coerce str → UUID so SQLAlchemy's Uuid column type works on both SQLite/PG
    task_uuid = _uuid.UUID(task_id) if isinstance(task_id, str) else task_id

    settings = get_settings()
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await redis_client.ping()
    except Exception:
        redis_client = None

    async with AsyncSessionLocal() as db:
        result_row = await db.execute(select(Task).where(Task.id == task_uuid))
        task = result_row.scalar_one_or_none()
        if not task:
            logger.error("Background runner: task not found", task_id=task_id)
            return

        task.status = "running"
        task.started_at = datetime.utcnow()
        await db.commit()

        # Broadcast start
        if redis_client:
            await redis_client.publish(
                f"task_updates:{task_id}",
                json.dumps({"task_id": task_id, "status": "running", "action": "task_started"}),
            )

        try:
            async def on_step(message: dict):
                is_screenshot = message.get("action") == "screenshot"

                if not is_screenshot:
                    log_entry = TaskLog(
                        task_id=task_uuid,
                        step_number=message.get("step", 0),
                        action=message.get("action", ""),
                        details=message.get("details", {}),
                    )
                    db.add(log_entry)
                    await db.commit()
                
                if redis_client:
                    await redis_client.publish(f"task_updates:{task_id}", json.dumps(message))
                elif is_screenshot:
                    from app.api.routes.websocket import manager
                    asyncio.create_task(manager.broadcast(task_id, message))

            agent = AgentLoop(task_id=task_id, goal=goal, on_step=on_step)
            final_result = await agent.run()

            if final_result.get("results"):
                db.add(Result(
                    task_id=task_uuid,
                    data_type="extracted",
                    data={"items": final_result["results"]},
                    summary=final_result.get("summary", ""),
                ))

            task.status = final_result.get("status", "completed")
            task.completed_at = datetime.utcnow()
            if final_result.get("error"):
                task.error_message = final_result["error"]
            await db.commit()

            if redis_client:
                await redis_client.publish(
                    f"task_updates:{task_id}",
                    json.dumps({
                        "task_id": task_id,
                        "status": task.status,
                        "action": "task_completed" if task.status == "completed" else "task_failed",
                        "summary": final_result.get("summary", ""),
                    }),
                )

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("Background agent error", task_id=task_id, error=str(e), traceback=tb)
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            await db.commit()

            if redis_client:
                await redis_client.publish(
                    f"task_updates:{task_id}",
                    json.dumps({"task_id": task_id, "status": "failed", "action": "task_failed", "error": str(e)}),
                )

    if redis_client:
        await redis_client.close()


# ---------- routes ----------

@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new automation task."""
    task = Task(goal=payload.goal, priority=payload.priority)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await db.commit()
    logger.info("Task created", task_id=str(task.id), goal=task.goal[:80])
    return task


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all tasks with optional status filter."""
    query = select(Task).order_by(Task.created_at.desc())
    count_query = select(func.count(Task.id))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset(offset).limit(limit))
    tasks = result.scalars().all()

    return TaskListResponse(tasks=tasks, total=total)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single task by ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Enqueue a task for agent execution.

    If Redis is available, push to queue for the worker process.
    Otherwise, run the AgentLoop directly as a background coroutine.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"Task is already {task.status}")

    redis_ok = await _redis_available()

    if redis_ok:
        import redis.asyncio as aioredis
        settings = get_settings()
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.rpush("task_queue", json.dumps({"task_id": str(task.id)}))
        await redis_client.close()
        task.status = "queued"
        logger.info("Task enqueued to Redis", task_id=str(task.id))
    else:
        task.status = "queued"
        logger.info("Redis unavailable — launching background agent", task_id=str(task.id))
        asyncio.create_task(_run_agent_background(str(task.id), task.goal))

    await db.flush()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel a running or queued task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "queued", "running"):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    task.status = "cancelled"
    task.completed_at = datetime.utcnow()
    await db.flush()
    await db.refresh(task)

    logger.info("Task cancelled", task_id=str(task.id))
    return task


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogResponse])
async def get_task_logs(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get execution logs for a task."""
    result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.step_number)
    )
    logs = result.scalars().all()
    return logs
