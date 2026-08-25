import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Update
from aiogram.filters.command import Command

from core.config import get_settings
from core.database import init_db, close_db
from bot.handlers import register_handlers

logger = logging.getLogger(__name__)
settings = get_settings()


async def main():
    logging.basicConfig(level=logging.INFO)

    # Initialize database
    await init_db()

    # Create bot and dispatcher
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # Register handlers
    register_handlers(dp)

    # Start polling
    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
