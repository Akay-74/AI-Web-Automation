"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"  # backend/.env


class Settings(BaseSettings):
    # App
    app_name: str = "AI Web Automation Agent"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite:///./agent.db"

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    max_tokens_decision: int = 700
    max_tokens_extraction: int = 2048

    # Agent
    max_steps_per_task: int = 25
    max_consecutive_failures: int = 4
    # Repeating one action verbatim means the page is not responding to it;
    # bail rather than spend the whole budget re-sending it.
    max_repeated_actions: int = 3
    max_elements_in_context: int = 100
    # Bounded waits — an unattended task must never hang forever.
    approval_timeout_seconds: int = 180
    human_pause_timeout_seconds: int = 300

    # Browser
    browser_headless: bool = True
    browser_user_data_dir: Optional[str] = None
    browser_timeout_ms: int = 30000  # page loads
    action_timeout_ms: int = 8000     # clicking/typing an element that should already be there
    viewport_width: int = 1440
    viewport_height: int = 900

    # CDP screencast (streamed to the browser panel over the WebSocket)
    screencast_fps: int = 8
    screencast_quality: int = 55

    # CAPTCHA solver (optional — leave blank to fall back to a human)
    captcha_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def chat_model(self) -> str:
        """Model id, namespaced when talking to a gateway that requires it.

        OpenRouter rejects bare ids like ``gpt-4o-mini``; it wants
        ``openai/gpt-4o-mini``. Keeps a plain OpenAI base URL untouched.
        """
        model = self.openai_model
        if "openrouter.ai" in self.openai_base_url and "/" not in model:
            return f"openai/{model}"
        return model


@lru_cache()
def get_settings() -> Settings:
    return Settings()
