import pytest
import asyncio
from sqlalchemy import select

from app.api.routes.tasks import _run_agent_background
from app.models.database import AsyncSessionLocal, engine, Base
from app.models.task import Task

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_agent_background_fallback():
    """Test that the background runner can complete a task execution loop without Redis."""
    
    # Create an initial task in the DB
    task_id = None
    async with AsyncSessionLocal() as session:
        t = Task(goal="Search Google for 'Testing the background agent'", priority=1, status="queued")
        session.add(t)
        await session.commit()
        await session.refresh(t)
        task_id = str(t.id)

    # Run the background coroutine explicitly
    await _run_agent_background(task_id, t.goal)

    # Verify task state in DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == t.id))
        updated_task = result.scalar_one()

        assert updated_task.status in ("completed", "failed"), "Task should be in a terminal state"
        assert updated_task.started_at is not None, "started_at must be set"
        assert updated_task.completed_at is not None, "completed_at must be set"
