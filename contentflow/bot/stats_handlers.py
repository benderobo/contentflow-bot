import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

stats_router = Router()


@stats_router.callback_query(F.data == "stats_overview")
async def handle_stats_overview(callback: CallbackQuery):
    """Show statistics overview."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/stats/overview?user_id={callback.from_user.id}&user_signature={_get_signature(callback.from_user.id)}"
        )

        if response and response.status_code == 200:
            stats = response.json()

            text = "📊 **Статистика**\n\n"
            text += f"📝 Постов создано: {stats.get('posts_created', 0)}\n"
            text += f"✅ Опубликовано: {stats.get('posts_published', 0)}\n"
            text += f"📅 Запланировано: {stats.get('posts_scheduled', 0)}\n"
            text += f"📡 Источников: {stats.get('sources_count', 0)}\n"
            text += f"📢 Каналов: {stats.get('channels_count', 0)}\n"

            markup = [
                [InlineKeyboardButton(text="📈 По времени", callback_data="stats_timeline")],
                [InlineKeyboardButton(text="📢 По каналам", callback_data="stats_by_channel")],
                [InlineKeyboardButton(text="📡 По источникам", callback_data="stats_by_source")],
            ]
        else:
            text = "❌ Ошибка при загрузке статистики"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_overview")]]

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_overview")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_stats")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@stats_router.callback_query(F.data == "stats_timeline")
async def handle_stats_timeline(callback: CallbackQuery):
    """Show statistics over time."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/stats/timeline?user_id={callback.from_user.id}&user_signature={_get_signature(callback.from_user.id)}&period=7d"
        )

        if response and response.status_code == 200:
            timeline = response.json()

            text = "📈 **Статистика по дням (последние 7 дней)**\n\n"
            for day in timeline:
                text += f"📅 {day.get('date')}: "
                text += f"{day.get('published', 0)} опубликовано, "
                text += f"{day.get('scheduled', 0)} запланировано\n"

            markup = [
                [InlineKeyboardButton(text="30 дней", callback_data="stats_timeline_30d")],
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_timeline")],
            ]
        else:
            text = "❌ Ошибка при загрузке статистики"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_timeline")]]

    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_timeline")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="stats_overview")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@stats_router.callback_query(F.data == "stats_by_channel")
async def handle_stats_by_channel(callback: CallbackQuery):
    """Show statistics by channel."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/stats/by-channel?user_id={callback.from_user.id}&user_signature={_get_signature(callback.from_user.id)}"
        )

        if response and response.status_code == 200:
            channels = response.json()

            text = "📢 **Статистика по каналам**\n\n"
            for ch in channels[:10]:
                text += f"📢 {ch.get('channel_name', 'Unknown')}\n"
                text += f"   ✅ Опубликовано: {ch.get('published_count', 0)}\n"
                text += f"   📅 Запланировано: {ch.get('scheduled_count', 0)}\n\n"

            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_channel")]]
        else:
            text = "❌ Ошибка при загрузке статистики"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_channel")]]

    except Exception as e:
        logger.error(f"Error fetching channel stats: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_channel")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="stats_overview")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@stats_router.callback_query(F.data == "stats_by_source")
async def handle_stats_by_source(callback: CallbackQuery):
    """Show statistics by source."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/stats/by-source?user_id={callback.from_user.id}&user_signature={_get_signature(callback.from_user.id)}"
        )

        if response and response.status_code == 200:
            sources = response.json()

            text = "📡 **Статистика по источникам**\n\n"
            for src in sources[:10]:
                text += f"📡 {src.get('source_name', 'Unknown')}\n"
                text += f"   📰 Статей спарсено: {src.get('items_parsed', 0)}\n"
                text += f"   📝 Постов создано: {src.get('posts_created', 0)}\n\n"

            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_source")]]
        else:
            text = "❌ Ошибка при загрузке статистики"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_source")]]

    except Exception as e:
        logger.error(f"Error fetching source stats: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_by_source")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="stats_overview")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


def _get_signature(user_id: int) -> str:
    """Helper to get HMAC signature for user_id."""
    from utils.auth import sign_user_id
    return sign_user_id(user_id)
