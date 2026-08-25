import logging
from aiogram import Dispatcher, F, Router
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from core.config import get_settings

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher):
    """Register all bot handlers."""
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        """Handle /start command."""
        settings = get_settings()
        inline_keyboard = [
            [InlineKeyboardButton(text="📥 Источники", callback_data="menu_sources")],
            [InlineKeyboardButton(text="📝 Посты", callback_data="menu_posts")],
            [InlineKeyboardButton(text="🤖 AI", callback_data="menu_ai")],
            [InlineKeyboardButton(text="📅 Планировщик", callback_data="menu_scheduler")],
            [InlineKeyboardButton(text="📢 Каналы", callback_data="menu_channels")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
        ]

        if message.from_user and message.from_user.id == 8660988275:
            inline_keyboard.append(
                [InlineKeyboardButton(text="✨ Редактор", web_app=WebAppInfo(url="http://localhost:3000"))]
            )

        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await message.answer(
            "🎯 ContentFlow Bot\n\n"
            "Автоматическая система управления контентом для Telegram-каналов.\n\n"
            "Выберите действие:",
            reply_markup=markup,
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        """Handle /help command."""
        help_text = """
/start - Главное меню
/help - Помощь
/sources - Управление источниками
/posts - Управление постами
/channels - Управление каналами
/stats - Статистика
"""
        await message.answer(help_text)

    @router.callback_query(F.data == "menu_sources")
    async def handle_sources_menu(callback: CallbackQuery):
        """Handle sources menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                [InlineKeyboardButton(text="📋 Список", callback_data="source_list")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="source_settings")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📥 **Управление источниками**\n\n"
            "Добавьте новые источники контента.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_posts")
    async def handle_posts_menu(callback: CallbackQuery):
        """Handle posts menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🆕 Новые", callback_data="post_new")],
                [InlineKeyboardButton(text="✏️ Черновики", callback_data="post_drafts")],
                [InlineKeyboardButton(text="🔍 На проверке", callback_data="post_review")],
                [InlineKeyboardButton(text="📅 Запланированные", callback_data="post_scheduled")],
                [InlineKeyboardButton(text="✅ Опубликованные", callback_data="post_published")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📝 **Управление постами**\n\n"
            "Просмотрите и управляйте постами.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_channels")
    async def handle_channels_menu(callback: CallbackQuery):
        """Handle channels menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить канал", callback_data="channel_add")],
                [InlineKeyboardButton(text="📋 Мои каналы", callback_data="channel_list")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📢 **Управление каналами**\n\n"
            "Настройте Telegram-каналы для публикации.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_scheduler")
    async def handle_scheduler_menu(callback: CallbackQuery):
        """Handle scheduler menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏰ Расписание", callback_data="scheduler_schedule")],
                [InlineKeyboardButton(text="📅 Календарь", callback_data="scheduler_calendar")],
                [InlineKeyboardButton(text="📊 История", callback_data="scheduler_history")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📅 **Планировщик публикаций**\n\n"
            "Управляйте расписанием публикаций.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_ai")
    async def handle_ai_menu(callback: CallbackQuery):
        """Handle AI menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Провайдер", callback_data="ai_provider")],
                [InlineKeyboardButton(text="📝 Шаблоны", callback_data="ai_templates")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="ai_stats")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "🤖 **Настройки AI**\n\n"
            "Настройте провайдера и модели для переписывания.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_stats")
    async def handle_stats_menu(callback: CallbackQuery):
        """Handle statistics menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Основные", callback_data="stats_general")],
                [InlineKeyboardButton(text="💰 AI стоимость", callback_data="stats_ai_cost")],
                [InlineKeyboardButton(text="📈 Тренды", callback_data="stats_trends")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📊 **Статистика**\n\n"
            "Просмотрите статистику работы системы.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_settings")
    async def handle_settings_menu(callback: CallbackQuery):
        """Handle settings menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Общие", callback_data="settings_general")],
                [InlineKeyboardButton(text="🔐 Безопасность", callback_data="settings_security")],
                [InlineKeyboardButton(text="📌 Профиль", callback_data="settings_profile")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "⚙️ **Настройки**\n\n"
            "Управляйте параметрами системы.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_main")
    async def handle_back_to_main(callback: CallbackQuery):
        """Handle back to main menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📥 Источники", callback_data="menu_sources")],
                [InlineKeyboardButton(text="📝 Посты", callback_data="menu_posts")],
                [InlineKeyboardButton(text="🤖 AI", callback_data="menu_ai")],
                [InlineKeyboardButton(text="📅 Планировщик", callback_data="menu_scheduler")],
                [InlineKeyboardButton(text="📢 Каналы", callback_data="menu_channels")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
            ]
        )
        await callback.message.edit_text(
            "🎯 ContentFlow Bot\n\n"
            "Выберите действие:",
            reply_markup=markup,
        )
        await callback.answer()

    # Generic handler for all submenu items
    async def show_submenu(callback: CallbackQuery, title: str):
        """Show submenu item."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")]]
        )
        await callback.message.edit_text(
            f"{title}\n\n⏳ Функция в разработке",
            reply_markup=markup,
        )
        await callback.answer()

    # Source submenu
    @router.callback_query(F.data == "source_add")
    async def handle_source_add(callback: CallbackQuery):
        await show_submenu(callback, "➕ Добавить источник")

    @router.callback_query(F.data == "source_list")
    async def handle_source_list(callback: CallbackQuery):
        await show_submenu(callback, "📋 Список источников")

    @router.callback_query(F.data == "source_settings")
    async def handle_source_settings(callback: CallbackQuery):
        await show_submenu(callback, "⚙️ Настройки источников")

    # Post submenu
    @router.callback_query(F.data == "post_new")
    async def handle_post_new(callback: CallbackQuery):
        await show_submenu(callback, "🆕 Новые посты")

    @router.callback_query(F.data == "post_drafts")
    async def handle_post_drafts(callback: CallbackQuery):
        await show_submenu(callback, "✏️ Черновики")

    @router.callback_query(F.data == "post_review")
    async def handle_post_review(callback: CallbackQuery):
        await show_submenu(callback, "🔍 На проверке")

    @router.callback_query(F.data == "post_scheduled")
    async def handle_post_scheduled(callback: CallbackQuery):
        await show_submenu(callback, "📅 Запланированные")

    @router.callback_query(F.data == "post_published")
    async def handle_post_published(callback: CallbackQuery):
        await show_submenu(callback, "✅ Опубликованные")

    # Channel submenu
    @router.callback_query(F.data == "channel_add")
    async def handle_channel_add(callback: CallbackQuery):
        await show_submenu(callback, "➕ Добавить канал")

    @router.callback_query(F.data == "channel_list")
    async def handle_channel_list(callback: CallbackQuery):
        await show_submenu(callback, "📋 Мои каналы")

    # AI submenu
    @router.callback_query(F.data == "ai_provider")
    async def handle_ai_provider(callback: CallbackQuery):
        await show_submenu(callback, "⚙️ Выбор провайдера")

    @router.callback_query(F.data == "ai_templates")
    async def handle_ai_templates(callback: CallbackQuery):
        await show_submenu(callback, "📝 Шаблоны")

    @router.callback_query(F.data == "ai_stats")
    async def handle_ai_stats(callback: CallbackQuery):
        await show_submenu(callback, "📊 Статистика AI")

    # Stats submenu
    @router.callback_query(F.data == "stats_general")
    async def handle_stats_general(callback: CallbackQuery):
        await show_submenu(callback, "📊 Общая статистика")

    @router.callback_query(F.data == "stats_ai_cost")
    async def handle_stats_ai_cost(callback: CallbackQuery):
        await show_submenu(callback, "💰 Стоимость AI")

    @router.callback_query(F.data == "stats_trends")
    async def handle_stats_trends(callback: CallbackQuery):
        await show_submenu(callback, "📈 Тренды")

    # Settings submenu
    @router.callback_query(F.data == "settings_general")
    async def handle_settings_general(callback: CallbackQuery):
        await show_submenu(callback, "⚙️ Общие настройки")

    @router.callback_query(F.data == "settings_security")
    async def handle_settings_security(callback: CallbackQuery):
        await show_submenu(callback, "🔐 Безопасность")

    @router.callback_query(F.data == "settings_profile")
    async def handle_settings_profile(callback: CallbackQuery):
        await show_submenu(callback, "📌 Профиль")

    # Scheduler submenu
    @router.callback_query(F.data == "scheduler_schedule")
    async def handle_scheduler_schedule(callback: CallbackQuery):
        await show_submenu(callback, "⏰ Расписание")

    @router.callback_query(F.data == "scheduler_calendar")
    async def handle_scheduler_calendar(callback: CallbackQuery):
        await show_submenu(callback, "📅 Календарь")

    @router.callback_query(F.data == "scheduler_history")
    async def handle_scheduler_history(callback: CallbackQuery):
        await show_submenu(callback, "📊 История")

    dp.include_router(router)
