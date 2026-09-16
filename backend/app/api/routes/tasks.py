"""Task API routes — CRUD plus starting and cancelling a run."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.task import Task, TaskLog
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskLogResponse,
    TaskResponse,
)
from app.services.agent.registry import get_agent
from app.services.agent.runner import start_task_run

logger = structlog.get_logger()
router = APIRouter(tags=["tasks"])

_CANCELLABLE = ("pending", "queued", "running")


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new automation task."""
    task = Task(goal=payload.goal, priority=payload.priority)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    logger.info("Task created", task_id=str(task.id), goal=task.goal[:80])
    return task


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List tasks, newest first."""
    query = select(Task).order_by(Task.created_at.desc())
    count_query = select(func.count(Task.id))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    total = (await db.execute(count_query)).scalar()
    tasks = (await db.execute(query.offset(offset).limit(limit))).scalars().all()
    return TaskListResponse(tasks=tasks, total=total)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single task."""
    return await _require_task(task_id, db)


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Start executing a task in the background."""
    task = await _require_task(task_id, db)
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"Task is already {task.status}")

    task.status = "queued"
    await db.flush()
    await db.refresh(task)

    start_task_run(str(task.id), task.goal)
    logger.info("Task run started", task_id=str(task.id))
    return task


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel a task, stopping the running agent if there is one."""
    task = await _require_task(task_id, db)
    if task.status not in _CANCELLABLE:
        raise HTTPException(status_code=400, detail=f"Task is {task.status} and cannot be cancelled")

    agent = get_agent(str(task_id))
    if agent:
        # The loop writes the final status itself once it unwinds.
        agent.cancel()
        logger.info("Cancel signalled to running agent", task_id=str(task_id))
    else:
        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogResponse])
async def get_task_logs(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get the stored execution log for a task."""
    result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.created_at, TaskLog.step_number)
    )
    return result.scalars().all()


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a task, with its logs and results."""
    task = await _require_task(task_id, db)
    # Logs and results go with it via cascade="all, delete-orphan".
    await db.delete(task)
    logger.info("Task deleted", task_id=str(task_id))


async def _require_task(task_id: uuid.UUID, db: AsyncSession) -> Task:
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
