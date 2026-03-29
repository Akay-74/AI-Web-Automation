"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import get_settings
from app.models.database import engine, Base
from app.api.routes import tasks, results, websocket

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    logger.info("Starting AI Web Automation Agent", debug=settings.debug)

    # Create database tables (use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    yield

    # Cleanup
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI Web Automation Agent",
    description="AI-powered browser automation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(tasks.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-web-automation-agent"}
