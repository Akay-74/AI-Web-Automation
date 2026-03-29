"""Redis Task Worker — Processes tasks from the queue.

Runs as a separate process alongside the FastAPI server.
Picks up tasks from Redis, runs the agent loop, and stores results.
"""

import asyncio
import json
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
import structlog

from app.config import get_settings
from app.models.database import AsyncSessionLocal
from app.models.task import Task, TaskLog
from app.models.result import Result
from app.services.agent.loop import AgentLoop

logger = structlog.get_logger()


async def publish_update(redis_client: aioredis.Redis, task_id: str, message: dict):
    """Publish a step update to Redis PubSub for WebSocket broadcast."""
    await redis_client.publish(
        f"task_updates:{task_id}",
        json.dumps(message),
    )


async def process_task(task_data: dict):
    """Process a single task: run agent loop and store results."""
    task_id = task_data["task_id"]
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)

    logger.info("Processing task", task_id=task_id)

    async with AsyncSessionLocal() as db:
        # Load task from database
        result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
        task = result.scalar_one_or_none()
        if not task:
            logger.error("Task not found", task_id=task_id)
            return

        # Update status to running
        task.status = "running"
        task.started_at = datetime.utcnow()
        await db.commit()

        # Broadcast status
        await publish_update(redis_client, task_id, {
            "task_id": task_id,
            "status": "running",
            "action": "task_started",
        })

        try:
            # Create step callback for broadcasting
            async def on_step(message: dict):
                # Log to database
                log = TaskLog(
                    task_id=UUID(task_id),
                    step_number=message.get("step", 0),
                    action=message.get("action", ""),
                    details=message.get("details", {}),
                )
                db.add(log)
                await db.commit()

                # Broadcast via Redis PubSub
                await publish_update(redis_client, task_id, message)

            # Run the agent loop
            agent = AgentLoop(
                task_id=task_id,
                goal=task.goal,
                on_step=on_step,
            )
            final_result = await agent.run()

            # Store results
            if final_result.get("results"):
                db_result = Result(
                    task_id=UUID(task_id),
                    data_type="extracted",
                    data={"items": final_result["results"]},
                    summary=final_result.get("summary", ""),
                )
                db.add(db_result)

            # Update task status
            task.status = final_result.get("status", "completed")
            task.completed_at = datetime.utcnow()
            if final_result.get("error"):
                task.error_message = final_result["error"]
            await db.commit()

            await publish_update(redis_client, task_id, {
                "task_id": task_id,
                "status": task.status,
                "action": "task_completed" if task.status == "completed" else "task_failed",
                "summary": final_result.get("summary", ""),
            })

        except Exception as e:
            logger.error("Task processing error", task_id=task_id, error=str(e))
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            await db.commit()

            await publish_update(redis_client, task_id, {
                "task_id": task_id,
                "status": "failed",
                "action": "task_failed",
                "error": str(e),
            })

    await redis_client.close()


async def worker_loop():
    """Main worker loop — listens for tasks on Redis queue."""
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)

    logger.info("Worker started, listening for tasks...",
                concurrency=settings.worker_concurrency)

    semaphore = asyncio.Semaphore(settings.worker_concurrency)

    while True:
        try:
            # Blocking pop from queue (timeout 5s)
            result = await redis_client.blpop("task_queue", timeout=5)
            if result is None:
                continue

            _, task_json = result
            task_data = json.loads(task_json)

            # Run with concurrency limit
            async with semaphore:
                await process_task(task_data)

        except Exception as e:
            logger.error("Worker error", error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker_loop())
