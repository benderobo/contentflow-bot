import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.types import Update
from aiogram.filters.command import Command
from redis.asyncio import Redis

from core.config import get_settings
from core.database import init_db, close_db
from bot.handlers import register_handlers
from bot.channel_handlers import channel_router
from bot.post_handlers import post_router
from bot.source_handlers import source_router
from bot.ai_handlers import ai_router
from bot.scheduler_handlers import scheduler_router
from bot.stats_handlers import stats_router

logger = logging.getLogger(__name__)
settings = get_settings()


async def main():
    logging.basicConfig(level=logging.INFO)

    # Initialize database
    await init_db()

    # Create bot and dispatcher with Redis FSM storage
    bot = Bot(token=settings.bot_token)

    from urllib.parse import urlparse
    redis_url = urlparse(settings.redis_url)
    redis = Redis(
        host=redis_url.hostname or "localhost",
        port=redis_url.port or 6379,
        db=int(redis_url.path.lstrip("/")) if redis_url.path else 0
    )
    storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder())
    dp = Dispatcher(storage=storage)

    # Register handlers
    register_handlers(dp)
    dp.include_router(channel_router)
    dp.include_router(post_router)
    dp.include_router(source_router)
    dp.include_router(ai_router)
    dp.include_router(scheduler_router)
    dp.include_router(stats_router)

    # Start polling
    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
