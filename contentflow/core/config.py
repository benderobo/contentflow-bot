from functools import lru_cache
from typing import Optional, Any, List
from pydantic import Field
from pydantic_settings import BaseSettings
from ipaddress import ip_address
import os
import json


def is_private_ip(ip_str: str) -> bool:
    """Check if IP is private/reserved."""
    try:
        ip = ip_address(ip_str)
        return (
            ip.is_private or ip.is_loopback or ip.is_link_local or
            ip.is_multicast or ip.is_reserved or str(ip) == "0.0.0.0"
        )
    except ValueError:
        return False


def _parse_admin_ids(value: Any) -> List[int]:
    if isinstance(value, list):
        return [int(x) for x in value if isinstance(x, int)]
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        if not value:
            return []
        if value.startswith("[") and value.endswith("]"):
            try:
                ids = json.loads(value)
                return [int(x) for x in ids if isinstance(x, int)]
            except (json.JSONDecodeError, TypeError):
                pass
        if value.isdigit():
            return [int(value)]
        if "," in value:
            return [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]
    return []


class Settings(BaseSettings):
    # Telegram
    bot_token: str
    webhook_url: Optional[str] = None
    admin_telegram_ids: str = ""
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None

    # Database
    database_url: str
    sqlalchemy_echo: bool = False

    # Redis
    redis_url: str

    # AI
    ai_provider: str = "openrouter"
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
        extra = "ignore"


class SettingsWithAdminIds:
    """Wrapper to provide parsed admin_telegram_ids."""
    def __init__(self):
        self._settings = Settings()
        self._admin_ids = _parse_admin_ids(self._settings.admin_telegram_ids)

    def __getattr__(self, name):
        if name == "admin_telegram_ids":
            return self._admin_ids
        return getattr(self._settings, name)

@lru_cache()
def get_settings() -> Settings:
    return SettingsWithAdminIds()  # type: ignore
