import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramServerError, TelegramNetworkError
from core.config import get_settings

logger = logging.getLogger(__name__)

_bot_instance: Optional[Bot] = None


def get_bot() -> Bot:
    """Get or create Bot singleton instance."""
    global _bot_instance
    if _bot_instance is None:
        settings = get_settings()
        _bot_instance = Bot(token=settings.bot_token)
    return _bot_instance


async def close_bot():
    """Close bot session."""
    global _bot_instance
    if _bot_instance:
        await _bot_instance.session.close()
        _bot_instance = None


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    Temporary errors (network, server 5xx) → retryable
    Permanent errors (auth, invalid channel, bad request) → not retryable
    """
    if isinstance(error, TelegramNetworkError):
        return True
    if isinstance(error, TelegramServerError):
        error_str = str(error).lower()
        if any(x in error_str for x in ["timeout", "connection", "temporary"]):
            return True
        if "429" in error_str:
            return True
        if "502" in error_str or "503" in error_str or "504" in error_str:
            return True
        return False
    if isinstance(error, TelegramAPIError):
        error_str = str(error).lower()
        non_retryable_keywords = [
            "unauthorized",
            "invalid_channel_id",
            "channel_invalid",
            "not_found",
            "chat_not_found",
            "forbidden",
            "can't talk to bots",
            "user_is_bot",
            "bad_request",
        ]
        if any(keyword in error_str for keyword in non_retryable_keywords):
            return False
        if any(x in error_str for x in ["timeout", "connection", "temporary", "reset"]):
            return True
        return True
    return True


def get_retry_delay(attempt: int, base_delay: int = 5) -> int:
    """Calculate exponential backoff delay with jitter."""
    import random
    delay = min(base_delay * (2 ** attempt), 3600)
    jitter = random.randint(0, int(delay * 0.1))
    return delay + jitter
