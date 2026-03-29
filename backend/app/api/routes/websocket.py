"""WebSocket endpoint for live task execution updates.

Dual-mode: subscribes to Redis PubSub when Redis is available,
otherwise falls back to polling the SQLite task log table so local mode
works without Redis.
"""

from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import asyncio
import json

from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per task."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active:
            self.active[task_id] = []
        self.active[task_id].append(websocket)
        logger.info("WebSocket connected", task_id=task_id)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active:
            try:
                self.active[task_id].remove(websocket)
            except ValueError:
                pass
            if not self.active[task_id]:
                del self.active[task_id]
        logger.info("WebSocket disconnected", task_id=task_id)

    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.active:
            dead = []
            for ws in list(self.active[task_id]):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(task_id, ws)


manager = ConnectionManager()


async def _redis_available() -> bool:
    """Check if Redis is reachable."""
    try:
        import redis.asyncio as aioredis
        settings = get_settings()
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
        await r.ping()
        await r.close()
        return True
    except Exception:
        return False


async def _stream_via_redis(websocket: WebSocket, task_id: str):
    """Forward task updates from Redis PubSub to the WebSocket."""
    import redis.asyncio as aioredis
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"task_updates:{task_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
                if data.get("status") in ("completed", "failed", "cancelled"):
                    break
    finally:
        await pubsub.unsubscribe(f"task_updates:{task_id}")
        await redis_client.close()


async def _stream_via_polling(websocket: WebSocket, task_id: str):
    """Poll the database for new task logs and broadcast them to the WebSocket.

    Used as the local/Redis-free fallback. Sends task log entries as they
    appear, then watches for a terminal status on the task itself.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.database import AsyncSessionLocal
    from app.models.task import Task, TaskLog

    # Coerce str → UUID so SQLAlchemy Uuid columns work
    task_uuid = _uuid.UUID(task_id) if isinstance(task_id, str) else task_id

    last_log_step = -1
    poll_interval = 0.5  # seconds
    timeout_secs = 600   # 10 minutes max

    for _ in range(int(timeout_secs / poll_interval)):
        try:
            async with AsyncSessionLocal() as db:
                # Fetch any new log entries since last seen step
                logs_result = await db.execute(
                    select(TaskLog)
                    .where(TaskLog.task_id == task_uuid)
                    .where(TaskLog.step_number > last_log_step)
                    .order_by(TaskLog.step_number)
                )
                new_logs = logs_result.scalars().all()
                for log in new_logs:
                    await websocket.send_json({
                        "task_id": task_id,
                        "step": log.step_number,
                        "action": log.action,
                        "raw_event": log.details or {},
                        "ui_event": {
                            "type": "info",
                            "message": log.action,
                            "step": log.step_number,
                            "timestamp": log.created_at.isoformat(),
                        },
                        "timestamp": log.created_at.isoformat(),
                    })
                    last_log_step = max(last_log_step, log.step_number)

                # Check task terminal state
                task_result = await db.execute(
                    select(Task).where(Task.id == task_uuid)
                )
                task = task_result.scalar_one_or_none()
                if task and task.status in ("completed", "failed", "cancelled"):
                    await websocket.send_json({
                        "task_id": task_id,
                        "status": task.status,
                        "action": f"task_{task.status}",
                    })
                    break
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.warning("WS poll error", error=str(e)[:200])
            break

        await asyncio.sleep(poll_interval)


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: UUID):
    """Stream live task execution updates to the client.

    Uses Redis PubSub when Redis is available; falls back to DB polling
    for local development without Redis.
    """
    task_id_str = str(task_id)
    await manager.connect(task_id_str, websocket)

    try:
        if await _redis_available():
            logger.info("WS using Redis PubSub", task_id=task_id_str)
            await _stream_via_redis(websocket, task_id_str)
        else:
            logger.info("WS using DB polling fallback", task_id=task_id_str)
            await _stream_via_polling(websocket, task_id_str)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error", task_id=task_id_str, error=str(e)[:200])
    finally:
        manager.disconnect(task_id_str, websocket)
