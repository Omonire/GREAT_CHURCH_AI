from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every value is environment-driven. No secret is ever committed to the
    repository; ``.env.example`` documents the supported variables.
    """

    # --- Core -------------------------------------------------------------
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Flask
    secret_key: str = "dev-only-insecure-key"
    cors_origins: str = ""

    # Static frontend
    web_dist: str = "../../../web"

    # --- Scripture --------------------------------------------------------
    # Scripture is read from the bundled public-domain King James Version
    # (pythonbible_kjv). No API key, no network call, no rate limit.
    scripture_translation: str = "KJV"
    scripture_search_limit: int = 20

    # --- AI ---------------------------------------------------------------
    # The default product runs no paid AI service. The browser talks to
    # Puter.js directly, and this Flask API prepares the prompts it sends.
    # Setting an OpenAI-compatible base URL + key moves generation server-side.
    ai_provider_base_url: str = ""
    ai_provider_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_timeout: float = 30.0
    ai_max_history: int = 12

    @field_validator("app_env")
    @classmethod
    def _normalise_env(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.app_env in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def server_side_ai_enabled(self) -> bool:
        return bool(self.ai_provider_base_url and self.ai_provider_api_key)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
