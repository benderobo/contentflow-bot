from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    bot_token: str
    webhook_url: Optional[str] = None
    admin_telegram_ids: list[int] = []

    # Database
    database_url: str
    sqlalchemy_echo: bool = False

    # Redis
    redis_url: str

    # AI
    ai_provider: str = "openrouter"  # openrouter, openai, anthropic, ollama
    ai_model: str = "openrouter/auto"
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None

    # Security
    secret_key: str
    webhook_secret: Optional[str] = None

    # Environment
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "UTC"

    # Features
    auto_publish_enabled: bool = False
    enable_rewrite: bool = True
    enable_analytics: bool = True

    # Rate Limiting
    telegram_rate_limit: int = 30
    parser_rate_limit: int = 10

    # Storage
    max_file_size: int = 52428800  # 50MB
    media_storage_path: str = "/app/storage/media"

    # Celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
