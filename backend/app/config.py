"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).parent.parent / ".env"  # backend/.env


class Settings(BaseSettings):
    # App
    app_name: str = "AI Web Automation Agent"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite:///./agent.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    max_tokens_plan: int = 1024
    max_tokens_replan: int = 1024

    # Agent
    max_steps_per_task: int = 20
    browser_timeout_ms: int = 30000
    max_retries: int = 3
    default_replan_attempts: int = 2

    # Worker
    worker_concurrency: int = 2

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
