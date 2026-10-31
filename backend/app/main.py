"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import require_api_key
from app.api.routes import results, tasks, websocket
from app.config import get_settings
from app.models.database import Base, engine

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup, dispose the engine on shutdown."""
    logger.info("Starting AI Web Automation Agent", debug=settings.debug)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready")

    yield

    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered browser automation platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(require_api_key)]
app.include_router(tasks.router, prefix="/api", dependencies=protected)
app.include_router(results.router, prefix="/api", dependencies=protected)
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-web-automation-agent",
        "llm_configured": bool(settings.openai_api_key),
        "auth_required": bool(settings.api_key),
    }
