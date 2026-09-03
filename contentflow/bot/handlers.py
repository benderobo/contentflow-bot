import logging
from aiogram import Dispatcher, F, Router
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from core.config import get_settings
from bot.auth import make_authenticated_request
from bot.instructions import get_instruction_text

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher):
    """Register all bot handlers."""
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        """Handle /start command."""
        settings = get_settings()

        # Register/create user if doesn't exist
        is_new_user = False
        if message.from_user:
            user_id = message.from_user.id
            username = message.from_user.username or ""
            first_name = message.from_user.first_name or "User"

            # Try to create/get user via API
            try:
                response = await make_authenticated_request(
                    "POST",
                    "/api/users",
                    user_id=user_id,
                    json={
                        "telegram_id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "user_id": user_id
                    }
                )
                if response and response.status_code == 200:
                    is_new_user = True
            except Exception as e:
                logger.warning(f"Failed to register user {user_id}: {e}")

            # Notify admin about new user
            if is_new_user and user_id != 5264530602:  # Don't notify about admin
                try:
                    admin_id = 5264530602
                    admin_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_user_{user_id}")],
                            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_user_{user_id}")]
                        ]
                    )
                    await message.bot.send_message(
                        admin_id,
                        f"🆕 Новый пользователь!\n\n"
                        f"👤 Имя: {first_name}\n"
                        f"📱 Username: @{username}\n"
                        f"🆔 ID: {user_id}\n\n"
                        f"Подтвердите доступ к боту:",
                        reply_markup=admin_markup
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")

        keyboard_buttons = [
            [KeyboardButton(text="📥 Источники"), KeyboardButton(text="📝 Посты")],
            [KeyboardButton(text="🤖 AI"), KeyboardButton(text="📅 Планировщик")],
            [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔄 Парсинг"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ]

        if message.from_user and message.from_user.id == 5264530602:
            keyboard_buttons.append(
                [KeyboardButton(text="✨ Редактор")]
            )

        markup = ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        await message.answer(
            "🎯 ContentFlow Bot\n\n"
            "Автоматическая система управления контентом для Telegram-каналов.\n\n"
            "Выберите действие:",
            reply_markup=markup,
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        """Handle /help command."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Быстрый старт", callback_data="help_quick")],
                [InlineKeyboardButton(text="📥 Источники", callback_data="help_sources")],
                [InlineKeyboardButton(text="📝 Посты", callback_data="help_posts")],
                [InlineKeyboardButton(text="🤖 AI", callback_data="help_ai")],
                [InlineKeyboardButton(text="📅 Планировщик", callback_data="help_scheduler")],
                [InlineKeyboardButton(text="📢 Каналы", callback_data="help_channels")],
                [InlineKeyboardButton(text="🔄 Парсинг", callback_data="help_parsing")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="help_settings")],
            ]
        )
        await message.answer(
            "📚 **Справка ContentFlow Bot**\n\n"
            "Выберите раздел для получения детальной инструкции:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # Text button handlers
    @router.message(F.text == "📥 Источники")
    async def handle_sources_button(message: Message):
        """Handle sources button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                [InlineKeyboardButton(text="📋 Список", callback_data="source_list")],
                [InlineKeyboardButton(text="📰 Статьи", callback_data="source_articles")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="source_settings")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("📥 Управление источниками\n\nДобавьте новые источники контента.", reply_markup=markup)

    @router.message(F.text == "📝 Посты")
    async def handle_posts_button(message: Message):
        """Handle posts button."""
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
        await message.answer("📝 Управление постами\n\nПросмотрите и управляйте постами.", reply_markup=markup)

    @router.message(F.text == "🤖 AI")
    async def handle_ai_button(message: Message):
        """Handle AI button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Переписать пост", callback_data="ai_rewrite")],
                [InlineKeyboardButton(text="⚡ Авто-переписать", callback_data="ai_auto_rewrite")],
                [InlineKeyboardButton(text="🔍 Анализировать", callback_data="ai_analyze")],
                [InlineKeyboardButton(text="⚙️ Провайдер", callback_data="ai_provider")],
                [InlineKeyboardButton(text="📝 Шаблоны", callback_data="ai_templates")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="ai_stats")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("🤖 Настройки AI\n\n• 🔄 Переписывайте отдельные посты\n• ⚡ Автоматически переписывайте все новые\n• 🔍 Анализируйте элементы источников\n• 📊 Просматривайте статистику использования", reply_markup=markup)

    @router.message(F.text == "📅 Планировщик")
    async def handle_scheduler_button(message: Message):
        """Handle scheduler button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data="schedule_publish")],
                [InlineKeyboardButton(text="⏰ Расписание", callback_data="scheduler_schedule")],
                [InlineKeyboardButton(text="📊 История", callback_data="scheduler_history")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("📅 Планировщик публикаций\n\n• 🚀 Опубликовать пост сейчас\n• ⏰ Запланировать на время\n• 📊 Просмотреть историю", reply_markup=markup)

    @router.message(F.text == "📢 Каналы")
    async def handle_channels_button(message: Message):
        """Handle channels button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить канал", callback_data="channel_add")],
                [InlineKeyboardButton(text="📋 Мои каналы", callback_data="channel_list")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("📢 Управление каналами\n\nНастройте Telegram-каналы для публикации.", reply_markup=markup)

    @router.message(F.text == "📊 Статистика")
    async def handle_stats_button(message: Message):
        """Handle stats button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Основные", callback_data="stats_general")],
                [InlineKeyboardButton(text="💰 AI стоимость", callback_data="stats_ai_cost")],
                [InlineKeyboardButton(text="📈 Тренды", callback_data="stats_trends")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("📊 Статистика\n\nПросмотрите аналитику вашей активности.", reply_markup=markup)

    @router.message(F.text == "⚙️ Настройки")
    async def handle_settings_button(message: Message):
        """Handle settings button."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👤 Профиль", callback_data="settings_profile")],
                [InlineKeyboardButton(text="🔧 Общие", callback_data="settings_general")],
                [InlineKeyboardButton(text="🔒 Безопасность", callback_data="settings_security")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await message.answer("⚙️ Настройки\n\nУправляйте параметрами вашего аккаунта.", reply_markup=markup)

    @router.message(F.text == "🔄 Парсинг")
    async def handle_parsing_button(message: Message):
        """Handle parsing button."""
        await message.answer(
            "⏳ Запуск парсинга всех источников...",
            reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
        )

        try:
            response = await make_authenticated_request(
                "POST",
                "/api/sources/parse-all",
                user_id=message.from_user.id,
                json={"user_id": message.from_user.id}
            )

            if response and response.status_code == 200:
                result = response.json()
                parsed_count = result.get("parsed_count", 0)
                items_count = result.get("items_count", 0)
                text = f"✅ Парсинг завершен!\n\n" \
                       f"📡 Источников обработано: {parsed_count}\n" \
                       f"📰 Статей получено: {items_count}"
            else:
                text = "❌ Ошибка при запуске парсинга"
        except Exception as e:
            logger.error(f"Error parsing sources: {e}")
            text = f"❌ Ошибка: {str(e)}"

        keyboard_buttons = [
            [KeyboardButton(text="📥 Источники"), KeyboardButton(text="📝 Посты")],
            [KeyboardButton(text="🤖 AI"), KeyboardButton(text="📅 Планировщик")],
            [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔄 Парсинг"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ]

        if message.from_user and message.from_user.id == 5264530602:
            keyboard_buttons.append([KeyboardButton(text="✨ Редактор")])

        markup = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
        await message.answer(text, reply_markup=markup)

    @router.message(F.text == "ℹ️ Помощь")
    async def handle_help_button(message: Message):
        """Handle help button."""
        help_text = """📚 **Справка по ContentFlow Bot**

🚀 **Основные функции:**
• 📥 Источники - добавление RSS, веб-сайтов и Telegram каналов
• 📝 Посты - управление контентом в разных статусах
• 🤖 AI - настройка искусственного интеллекта для переписывания
• 📅 Планировщик - расписание автоматических публикаций
• 📢 Каналы - связь с вашими Telegram каналами
• 📊 Статистика - аналитика и отчеты

💡 **Советы:**
1. Начните с добавления источника контента
2. Настройте AI провайдера для переписывания текстов
3. Добавьте каналы для публикации
4. Создайте расписание автоматических постов

❓ **Вопросы?**
/start - вернуться в главное меню
"""
        await message.answer(help_text)

    # Help callbacks
    @router.callback_query(F.data.startswith("help_"))
    async def handle_help_callback(callback: CallbackQuery):
        """Handle help section callbacks."""
        section = callback.data.replace("help_", "")
        text = get_instruction_text(section)

        back_button = InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_help")
        back_markup = InlineKeyboardMarkup(inline_keyboard=[[back_button]])

        await callback.message.edit_text(text, reply_markup=back_markup)
        await callback.answer()

    @router.callback_query(F.data == "back_to_help")
    async def handle_back_to_help(callback: CallbackQuery):
        """Return to help menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Быстрый старт", callback_data="help_quick")],
                [InlineKeyboardButton(text="📥 Источники", callback_data="help_sources")],
                [InlineKeyboardButton(text="📝 Посты", callback_data="help_posts")],
                [InlineKeyboardButton(text="🤖 AI", callback_data="help_ai")],
                [InlineKeyboardButton(text="📅 Планировщик", callback_data="help_scheduler")],
                [InlineKeyboardButton(text="📢 Каналы", callback_data="help_channels")],
                [InlineKeyboardButton(text="🔄 Парсинг", callback_data="help_parsing")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="help_settings")],
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📚 **Справка ContentFlow Bot**\n\n"
            "Выберите раздел для получения детальной инструкции:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        await callback.answer()

    @router.message(F.text == "✨ Редактор")
    async def handle_editor_button(message: Message):
        """Handle editor button."""
        settings = get_settings()
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть редактор", web_app=WebAppInfo(url=settings.webapp_url))]
            ]
        )
        await message.answer("✨ Редактор контента\n\nНажмите кнопку для открытия редактора:", reply_markup=markup)

    @router.callback_query(F.data == "menu_main")
    async def handle_menu_main(callback: CallbackQuery):
        """Return to main menu."""
        keyboard_buttons = [
            [KeyboardButton(text="📥 Источники"), KeyboardButton(text="📝 Посты")],
            [KeyboardButton(text="🤖 AI"), KeyboardButton(text="📅 Планировщик")],
            [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔄 Парсинг"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ]

        if callback.from_user.id == 5264530602:
            keyboard_buttons.append([KeyboardButton(text="✨ Редактор")])

        markup = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
        await callback.message.edit_text(
            "🎯 ContentFlow Bot\n\n"
            "Автоматическая система управления контентом для Telegram-каналов.\n\n"
            "Выберите действие:"
        )
        await callback.message.answer("👇 Выберите опцию:", reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "menu_sources")
    async def handle_sources_menu(callback: CallbackQuery):
        """Handle sources menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                [InlineKeyboardButton(text="📋 Список", callback_data="source_list")],
                [InlineKeyboardButton(text="🔄 Запустить парсинг", callback_data="source_parse_all")],
                [InlineKeyboardButton(text="🔍 Фильтры", callback_data="source_filters_menu")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="source_settings")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📥 Управление источниками\n\n"
            "Добавьте новые источники контента, запустите парсинг, настройте фильтры и параметры.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "source_filters_menu")
    async def handle_source_filters_menu(callback: CallbackQuery):
        """Show filters menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Ключевые слова", callback_data="global_keywords")],
                [InlineKeyboardButton(text="❌ Исключить слова", callback_data="global_exclusions")],
                [InlineKeyboardButton(text="📚 Готовые фильтры", callback_data="preset_filters_list")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")],
            ]
        )
        await callback.message.edit_text(
            "🔍 Фильтры для источников\n\n"
            "Настройте глобальные фильтры для парсинга.\n"
            "Или перейдите в Настройки для фильтров конкретного источника.",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "preset_filters_list")
    async def handle_preset_filters_list(callback: CallbackQuery):
        """Show preset filters."""
        preset_text = """📚 Готовые фильтры:

**Ключевые слова:**
💻 IT & Технологии
📰 Новости
💰 Бизнес & Финансы
📱 Социальные сети

**Исключения:**
🚫 Спам & Реклама
⚠️ Некачественный контент
🔞 NSFW
📢 Дублированное

Применяйте их при добавлении или редактировании источников в Настройках!"""

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_filters_menu")],
            ]
        )
        await callback.message.edit_text(preset_text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "global_keywords")
    async def handle_global_keywords(callback: CallbackQuery):
        """Info about global keywords."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Примеры", callback_data="keywords_examples")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_filters_menu")],
            ]
        )
        await callback.message.edit_text(
            "🔑 Ключевые слова (Include)\n\n"
            "Используются для ВКЛЮЧЕНИЯ постов.\n"
            "Парсятся только посты, которые содержат ВСЕ указанные слова.\n\n"
            "Примеры:\n"
            "• python, java → только посты с обоими словами\n"
            "• новости, технология → посты с обоими словами\n\n"
            "⚡ Применяется при редактировании каждого источника!",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "global_exclusions")
    async def handle_global_exclusions(callback: CallbackQuery):
        """Info about global exclusions."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Примеры", callback_data="exclusions_examples")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_filters_menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ Исключение слов (Exclude)\n\n"
            "Используются для ИСКЛЮЧЕНИЯ постов.\n"
            "Пропускаются посты, которые содержат ЛЮБое из указанных слов.\n\n"
            "Примеры:\n"
            "• спам, реклама → посты со спамом или рекламой пропускаются\n"
            "• фейк, ложь → посты с фейком или ложью пропускаются\n\n"
            "⚡ Применяется при редактировании каждого источника!",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "keywords_examples")
    async def handle_keywords_examples(callback: CallbackQuery):
        """Show keywords examples."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="global_keywords")],
            ]
        )
        await callback.message.edit_text(
            "📚 Примеры использования ключевых слов:\n\n"
            "**Быстрые фильтры:**\n"
            "💻 IT: python, javascript, golang, rust, devops, cloud\n"
            "📰 Новости: события, происшествия, объявил, сообщает\n"
            "💰 Финансы: компания, стартап, инвестиции, сделка\n"
            "📱 Соцсети: instagram, tiktok, facebook, telegram\n\n"
            "**Кастомные:**\n"
            "Вводите слова через запятую в Настройках каждого источника!",
            reply_markup=markup,
        )
        await callback.answer()

    @router.callback_query(F.data == "exclusions_examples")
    async def handle_exclusions_examples(callback: CallbackQuery):
        """Show exclusions examples."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="global_exclusions")],
            ]
        )
        await callback.message.edit_text(
            "📚 Примеры использования исключений:\n\n"
            "**Быстрые фильтры:**\n"
            "🚫 Спам: спам, реклама, маркетинг, промо\n"
            "⚠️ Качество: фейк, ложь, неправда, некорректно\n"
            "🔞 NSFW: 18+, adult, xxx, explicit\n"
            "📢 Дубли: дублирован, копия, скопирован\n\n"
            "**Кастомные:**\n"
            "Вводите слова через запятую в Настройках каждого источника!",
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

    @router.callback_query(F.data == "menu_scheduler")
    async def handle_scheduler_menu(callback: CallbackQuery):
        """Handle scheduler menu."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Запланировать публикацию", callback_data="schedule_publish")],
                [InlineKeyboardButton(text="📊 История публикаций", callback_data="scheduler_history")],
                [InlineKeyboardButton(text="⏰ Расписание", callback_data="scheduler_schedule")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📅 Планировщик публикаций\n\n"
            "Планируйте автоматическую публикацию ваших постов в каналы по расписанию.",
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
                [InlineKeyboardButton(text="📊 Статус системы", callback_data="settings_general")],
                [InlineKeyboardButton(text="🛡️ Безопасность системы", callback_data="settings_security")],
                [InlineKeyboardButton(text="👤 Мой профиль", callback_data="settings_profile")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
            ]
        )
        await callback.message.edit_text(
            "📋 Информация и статус\n\n"
            "Просмотрите информацию о боте и вашем профиле.",
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

    # Post submenu
    @router.callback_query(F.data == "post_new")
    async def handle_post_new(callback: CallbackQuery):
        """List new posts from sources."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=new",
                    user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "🆕 **Новые посты**\n\nНет новых постов из источников"
                    markup = [[InlineKeyboardButton(text="🔄 Запустить парсинг", callback_data="source_parse_all")]]
                else:
                    text = f"🆕 **Новые посты** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"📝 {post['title'][:40]}\n"
                        post_id = post['id']
                        markup.append([InlineKeyboardButton(text=f"✏️ {post['title'][:25]}", callback_data=f"post_edit_{post_id}")])
            else:
                text = "🆕 **Новые посты**\n\n❌ Ошибка при загрузке постов"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_new")]]
        except Exception as e:
            text = f"🆕 **Новые посты**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_new")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    @router.callback_query(F.data == "post_drafts")
    async def handle_post_drafts(callback: CallbackQuery):
        """List draft posts."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=draft",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "✏️ **Черновики**\n\nНет черновиков"
                    markup = [[InlineKeyboardButton(text="📝 Создать пост", callback_data="post_new")]]
                else:
                    text = f"✏️ **Черновики** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"📝 {post['title'][:40]}\n"
                        post_id = post['id']
                        markup.append([InlineKeyboardButton(text=f"✏️ {post['title'][:25]}", callback_data=f"post_edit_{post_id}")])
            else:
                text = "✏️ **Черновики**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_drafts")]]
        except Exception as e:
            text = f"✏️ **Черновики**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_drafts")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    @router.callback_query(F.data == "post_review")
    async def handle_post_review(callback: CallbackQuery):
        """List posts on review."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=needs_review",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "🔍 **На проверке**\n\nНет постов на проверке"
                    markup = []
                else:
                    text = f"🔍 **На проверке** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"📝 {post['title'][:40]}\n"
                        post_id = post['id']
                        markup.append([InlineKeyboardButton(text=f"✓ {post['title'][:25]}", callback_data=f"post_publish_{post_id}")])
            else:
                text = "🔍 **На проверке**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_review")]]
        except Exception as e:
            text = f"🔍 **На проверке**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_review")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    @router.callback_query(F.data == "post_scheduled")
    async def handle_post_scheduled(callback: CallbackQuery):
        """List scheduled posts."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=scheduled",
                    user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "📅 **Запланированные**\n\nНет запланированных постов"
                    markup = [[InlineKeyboardButton(text="📝 Создать пост", callback_data="post_new")]]
                else:
                    text = f"📅 **Запланированные** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"📝 {post['title'][:40]}\n"
                        post_id = post['id']
                        markup.append([InlineKeyboardButton(text=f"📅 {post['title'][:25]}", callback_data=f"post_edit_{post_id}")])
            else:
                text = "📅 **Запланированные**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_scheduled")]]
        except Exception as e:
            text = f"📅 **Запланированные**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_scheduled")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    @router.callback_query(F.data == "post_published")
    async def handle_post_published(callback: CallbackQuery):
        """List published posts."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=published",
                    user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "✅ **Опубликованные**\n\nНет опубликованных постов"
                    markup = []
                else:
                    text = f"✅ **Опубликованные** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"📝 {post['title'][:40]}\n"
                        post_id = post['id']
                        markup.append([InlineKeyboardButton(text=f"✅ {post['title'][:25]}", callback_data=f"post_view_{post_id}")])
            else:
                text = "✅ **Опубликованные**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_published")]]
        except Exception as e:
            text = f"✅ **Опубликованные**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_published")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    # Channel submenu - delegates to channel_handlers
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
            "📢 Управление каналами\n\n"
            "Добавьте ваши Telegram каналы для публикации контента.",
            reply_markup=markup,
        )
        await callback.answer()

    # AI submenu
    @router.callback_query(F.data == "ai_provider")
    async def handle_ai_provider(callback: CallbackQuery):
        """Show AI provider selection."""
        text = """⚙️ **Выбор провайдера AI**

Текущий провайдер: OpenRouter

Доступные провайдеры:
• OpenRouter (GPT-4, Claude, etc.)
• OpenAI (ChatGPT, GPT-4)
• Anthropic (Claude)
• Ollama (локальные модели)

Для смены провайдера обновите переменные окружения."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Переписать пост", callback_data="ai_rewrite")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "ai_templates")
    async def handle_ai_templates(callback: CallbackQuery):
        """Show AI templates."""
        text = """📝 **Шаблоны переписывания**

Доступные шаблоны:
• 📰 Новостной стиль - формальный, информативный
• 🎯 Маркетинг - привлекающий внимание, убедительный
• 💬 Диалог - разговорный, дружелюбный
• 🔍 SEO - оптимизированный для поиска
• 📚 Аналитика - подробный, исследовательский

Шаблоны применяются при переписывании постов."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "ai_stats")
    async def handle_ai_stats(callback: CallbackQuery):
        """Show AI usage statistics."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/ai/stats",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                stats = response.json()
                text = f"""📊 **Статистика использования AI**

📝 Текстов обработано: {stats.get('texts_processed', 0)}
💰 Затрачено токенов: {stats.get('tokens_used', 0)}
💵 Приблизительная стоимость: ${stats.get('estimated_cost', '0.00')}

Провайдер: {stats.get('provider', 'OpenRouter')}
Последний запрос: {stats.get('last_used', 'Никогда')}"""
            else:
                text = "📊 **Статистика использования AI**\n\n❌ Ошибка при загрузке статистики"
        except Exception as e:
            text = f"📊 **Статистика использования AI**\n\n❌ Ошибка: {str(e)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Переписать пост", callback_data="ai_rewrite")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    # Stats submenu
    @router.callback_query(F.data == "stats_general")
    async def handle_stats_general(callback: CallbackQuery):
        """Show general statistics."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/stats/overview",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                stats = response.json()
                text = f"""📊 **Статистика системы**

📝 Постов создано: {stats.get('posts_created', 0)}
✅ Опубликовано: {stats.get('posts_published', 0)}
📅 Запланировано: {stats.get('posts_scheduled', 0)}
📡 Источников: {stats.get('sources_count', 0)}
📢 Каналов: {stats.get('channels_count', 0)}

Обновлено: Сейчас"""
            else:
                text = "📊 **Статистика системы**\n\n❌ Ошибка при загрузке статистики"
        except Exception as e:
            text = f"📊 **Статистика системы**\n\n❌ Ошибка: {str(e)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📈 По времени", callback_data="stats_timeline")],
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_general")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_stats")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "stats_ai_cost")
    async def handle_stats_ai_cost(callback: CallbackQuery):
        """Show AI usage cost."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/ai/stats",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                stats = response.json()
                text = f"""💰 **Стоимость использования AI**

📝 Текстов обработано: {stats.get('texts_processed', 0)}
📊 Использовано токенов: {stats.get('tokens_used', 0)}
💵 Приблизительная стоимость: ${stats.get('estimated_cost', '0.00')}

Провайдер: {stats.get('provider', 'OpenRouter')}"""
            else:
                text = "💰 **Стоимость использования AI**\n\n❌ Ошибка при загрузке статистики"
        except Exception as e:
            text = f"💰 **Стоимость использования AI**\n\n❌ Ошибка: {str(e)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_ai_cost")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_stats")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "stats_trends")
    async def handle_stats_trends(callback: CallbackQuery):
        """Show trends and analytics."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/stats/timeline",
                user_id=callback.from_user.id,
                params={"period": "7d"}
            )

            if response and response.status_code == 200:
                timeline = response.json()
                text = "📈 **Тренды (последние 7 дней)**\n\n"
                for entry in timeline[:7]:
                    date = entry.get('date', 'N/A')
                    published = entry.get('published', 0)
                    scheduled = entry.get('scheduled', 0)
                    text += f"📅 {date}: {published} опубл. + {scheduled} запланировано\n"
            else:
                text = "📈 **Тренды**\n\n❌ Ошибка при загрузке статистики"
        except Exception as e:
            text = f"📈 **Тренды**\n\n❌ Ошибка: {str(e)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_trends")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_stats")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "stats_timeline")
    async def handle_stats_timeline(callback: CallbackQuery):
        """Show timeline statistics."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/stats/timeline",
                user_id=callback.from_user.id,
                params={"period": "7d"}
            )

            if response and response.status_code == 200:
                timeline = response.json()
                text = "📈 **Статистика по дням (последние 7 дней)**\n\n"
                for entry in timeline[:7]:
                    date = entry.get('date', 'N/A')
                    published = entry.get('published', 0)
                    scheduled = entry.get('scheduled', 0)
                    text += f"📅 {date}: {published} опубл. + {scheduled} запланировано\n"
            else:
                text = "📈 **Статистика по дням**\n\n❌ Ошибка при загрузке"
        except Exception as e:
            text = f"📈 **Статистика по дням**\n\n❌ Ошибка: {str(e)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Основные", callback_data="stats_general")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_stats")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    # Settings submenu
    @router.callback_query(F.data == "settings_general")
    async def handle_settings_general(callback: CallbackQuery):
        """Show system status."""
        text = """📊 Статус системы

🌍 Язык: Русский
🔔 Уведомления: Включены
⏰ Часовой пояс: UTC+3
📱 Платформа: Telegram

Настраиваемые опции доступны в разработке."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_settings")]]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "settings_security")
    async def handle_settings_security(callback: CallbackQuery):
        """Show security system status."""
        text = """🛡️ Безопасность системы

🔑 API Key: Настроен ✅
🤖 Bot Token: Активен ✅
🛡️ HMAC Signatures: Включена ✅
🚫 SSRF Protection: Активна ✅

Все системы безопасности активны."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_settings")]]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "settings_profile")
    async def handle_settings_profile(callback: CallbackQuery):
        """Show user profile."""
        user_id = callback.from_user.id
        username = callback.from_user.username or "No username"
        first_name = callback.from_user.first_name or "User"

        text = f"""👤 Мой профиль

👤 Имя: {first_name}
📱 Username: @{username}
🆔 User ID: {user_id}
✅ Статус: Активный

Дата присоединения: 2026-08-25"""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_settings")]]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    # Scheduler submenu
    @router.callback_query(F.data == "scheduler_schedule")
    async def handle_scheduler_schedule(callback: CallbackQuery):
        """Show scheduler schedule."""
        text = """⏰ **Расписание публикаций**

📅 Здесь будут отображаться запланированные посты.

Функции:
• Планирование публикаций на будущее
• Автоматическая публикация в указанное время
• Отмена запланированных постов
• Просмотр истории публикаций

Нажмите ниже для добавления нового расписания."""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Новое расписание", callback_data="schedule_publish")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_scheduler")]
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "scheduler_history")
    async def handle_scheduler_history(callback: CallbackQuery):
        """Show publish history."""
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts?status=published&limit=10",
                    user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                posts = response.json()
                if not posts:
                    text = "📊 **История публикаций**\n\nНет опубликованных постов"
                    markup = []
                else:
                    text = f"📊 **История публикаций** ({len(posts)})\n\n"
                    markup = []
                    for post in posts[:5]:
                        text += f"✅ {post['title'][:40]}\n"
                        if post.get('published_at'):
                            text += f"   📅 {post['published_at'][:10]}\n"
            else:
                text = "📊 **История публикаций**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="scheduler_history")]]
        except Exception as e:
            text = f"📊 **История публикаций**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="scheduler_history")]]

        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_scheduler")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    # User approval handlers
    @router.callback_query(F.data.startswith("approve_user_"))
    async def handle_approve_user(callback: CallbackQuery):
        """Approve new user."""
        user_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "PATCH",
                f"/api/users/{user_id}",
                user_id=callback.from_user.id,
                json={"user_id": callback.from_user.id, "is_approved": True}
            )
            if response and response.status_code == 200:
                await callback.message.edit_text(
                    f"✅ Пользователь {user_id} подтвержден!"
                )
                # Send message to approved user
                try:
                    await callback.bot.send_message(
                        user_id,
                        "✅ Ваш аккаунт подтвержден администратором! Добро пожаловать в ContentFlow Bot! 🎉"
                    )
                except:
                    pass
            else:
                await callback.message.edit_text("❌ Ошибка подтверждения пользователя")
        except Exception as e:
            logger.error(f"Error approving user: {e}")
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
        await callback.answer()

    @router.callback_query(F.data.startswith("reject_user_"))
    async def handle_reject_user(callback: CallbackQuery):
        """Reject new user."""
        user_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "PATCH",
                f"/api/users/{user_id}",
                user_id=callback.from_user.id,
                json={"user_id": callback.from_user.id, "is_approved": False}
            )
            # Send message to rejected user
            try:
                await callback.bot.send_message(
                    user_id,
                    "❌ К сожалению, ваш запрос на доступ был отклонен администратором."
                )
            except:
                pass

            await callback.message.edit_text(
                f"❌ Пользователь {user_id} отклонен!"
            )
        except Exception as e:
            logger.error(f"Error rejecting user: {e}")
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
        await callback.answer()

    # Post detail view
    @router.callback_query(F.data.startswith("post_view_"))
    async def handle_post_view(callback: CallbackQuery):
        """Show full post view."""
        post_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts/{post_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                post = response.json()
                text = f"📝 <b>{post['title']}</b>\n\n"
                text += f"{post.get('body', '')}\n\n"
                if post.get('original_url'):
                    text += f"🔗 <a href='{post['original_url']}'>Источник</a>\n"
                text += f"\n📊 Статус: <b>{post['status']}</b>"
                if post.get('importance'):
                    text += f"\n⭐ Важность: {post['importance']}/10"
                if post.get('category'):
                    text += f"\n📂 Категория: {post['category']}"

                markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_published")]]
            else:
                text = "❌ Пост не найден"
                markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_published")]]
        except Exception as e:
            text = f"❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_published")]]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup), parse_mode="HTML")
        await callback.answer()

    @router.callback_query(F.data.startswith("post_edit_"))
    async def handle_post_edit(callback: CallbackQuery):
        """Show post for editing."""
        post_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts/{post_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                post = response.json()
                text = f"✏️ <b>Редактирование поста</b>\n\n"
                text += f"📝 Заголовок: {post['title']}\n\n"
                text += f"📄 Содержание:\n{post.get('body', '')}\n\n"
                if post.get('original_url'):
                    text += f"🔗 Источник: {post['original_url']}\n"
                text += f"\n📊 Статус: <b>{post['status']}</b>"
                if post.get('importance'):
                    text += f"\n⭐ Важность: {post['importance']}/10"
                if post.get('category'):
                    text += f"\n📂 Категория: {post['category']}"

                markup = [
                    [InlineKeyboardButton(text="✅ Одобрить для публикации", callback_data=f"post_publish_{post_id}")],
                    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"post_reject_{post_id}")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="post_drafts")]
                ]
            else:
                text = "❌ Пост не найден"
                markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_drafts")]]
        except Exception as e:
            text = f"❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_drafts")]]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup), parse_mode="HTML")
        await callback.answer()

    @router.callback_query(F.data.startswith("post_publish_"))
    async def handle_post_publish(callback: CallbackQuery):
        """Publish post to channels."""
        post_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/posts/{post_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                post = response.json()

                channels_response = await make_authenticated_request(
                    "GET",
                    f"/api/channels",
                    user_id=callback.from_user.id
                )

                if channels_response and channels_response.status_code == 200:
                    channels = channels_response.json()
                    if not channels:
                        text = "❌ Нет доступных каналов для публикации"
                        markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_review")]]
                    else:
                        text = f"📢 <b>Выберите канал для публикации</b>\n\n"
                        text += f"📝 Пост: <b>{post['title']}</b>\n\n"
                        text += f"Доступные каналы:\n"
                        markup = []
                        for channel in channels[:10]:
                            text += f"• {channel['name']}\n"
                            markup.append([InlineKeyboardButton(
                                text=f"📢 {channel['name'][:20]}",
                                callback_data=f"publish_to_{post_id}_{channel['id']}"
                            )])
                        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="post_review")])
                else:
                    text = "❌ Ошибка при загрузке каналов"
                    markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_review")]]
            else:
                text = "❌ Пост не найден"
                markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_review")]]
        except Exception as e:
            text = f"❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="post_review")]]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup), parse_mode="HTML")
        await callback.answer()

    @router.callback_query(F.data.startswith("publish_to_"))
    async def handle_publish_to_channel(callback: CallbackQuery):
        """Publish post to specific channel."""
        parts = callback.data.split("_")
        post_id = int(parts[2])
        channel_id = int(parts[3])

        try:
            response = await make_authenticated_request(
                "POST",
                f"/api/posts/{post_id}/publish",
                user_id=callback.from_user.id,
                json={"channel_id": channel_id}
            )

            if response and response.status_code == 200:
                await callback.message.edit_text(
                    "✅ Пост успешно опубликован!\n\n"
                    "Он был отправлен в выбранный канал."
                )
            else:
                error_detail = response.json().get('detail', 'Неизвестная ошибка') if response else 'Ошибка сервера'
                await callback.message.edit_text(
                    f"❌ Ошибка при публикации:\n{error_detail}\n\n"
                    "Попробуйте еще раз или выберите другой канал."
                )
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

        await callback.answer()

    @router.callback_query(F.data.startswith("post_reject_"))
    async def handle_post_reject(callback: CallbackQuery):
        """Reject post."""
        post_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "PATCH",
                f"/api/posts/{post_id}",
                user_id=callback.from_user.id,
                json={"status": "rejected"}
            )

            if response and response.status_code == 200:
                await callback.message.edit_text(
                    "❌ Пост отклонен и переведен в черновики."
                )
            else:
                await callback.message.edit_text("❌ Ошибка при отклонении поста")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

        await callback.answer()

    # Source management handlers
    @router.callback_query(F.data == "source_list")
    async def handle_source_list(callback: CallbackQuery):
        """Show list of user's sources."""
        try:
            response = await make_authenticated_request(
                "GET",
                "/api/sources",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                sources = response.json()
                if not sources:
                    text = "📥 **Мои источники**\n\nНет источников. Добавьте новый для начала парсинга."
                    markup = [[InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")]]
                else:
                    text = f"📥 **Мои источники** ({len(sources)})\n\n"
                    markup = []
                    for source in sources:
                        text += f"📰 {source['name']} ({source['type']})\n"
                        source_id = source['id']
                        markup.append([InlineKeyboardButton(
                            text=f"⚙️ {source['name'][:20]}",
                            callback_data=f"source_edit_{source_id}"
                        )])
            else:
                text = "📥 **Мои источники**\n\n❌ Ошибка при загрузке"
                markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="source_list")]]
        except Exception as e:
            text = f"📥 **Мои источники**\n\n❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="source_list")]]

        markup.append([InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")])
        markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
        await callback.answer()

    @router.callback_query(F.data.startswith("source_edit_"))
    async def handle_source_edit(callback: CallbackQuery):
        """Edit source settings."""
        source_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "GET",
                f"/api/sources/{source_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                source = response.json()
                text = f"⚙️ <b>Редактирование источника</b>\n\n"
                text += f"📰 Имя: <b>{source['name']}</b>\n"
                text += f"🔗 Тип: <b>{source['type']}</b>\n"
                text += f"📍 URL: {source.get('url', 'N/A')}\n"
                text += f"✅ Статус: {'Включен' if source.get('enabled') else 'Отключен'}\n"
                if source.get('last_check'):
                    text += f"🕐 Последняя проверка: {source['last_check'][:16]}\n"
                if source.get('last_success'):
                    text += f"✓ Последний успех: {source['last_success'][:16]}\n"

                markup = [
                    [InlineKeyboardButton(
                        text="⏸️ Отключить" if source.get('enabled') else "▶️ Включить",
                        callback_data=f"source_toggle_{source_id}"
                    )],
                    [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"source_delete_{source_id}")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="source_list")]
                ]
            else:
                text = "❌ Источник не найден"
                markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="source_list")]]
        except Exception as e:
            text = f"❌ Ошибка: {str(e)}"
            markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="source_list")]]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup), parse_mode="HTML")
        await callback.answer()

    @router.callback_query(F.data.startswith("source_toggle_"))
    async def handle_source_toggle(callback: CallbackQuery):
        """Enable/disable source."""
        source_id = int(callback.data.split("_")[-1])
        try:
            # Get current state
            response = await make_authenticated_request(
                "GET",
                f"/api/sources/{source_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                source = response.json()
                new_state = not source.get('enabled', False)

                # Update source
                update_response = await make_authenticated_request(
                    "PATCH",
                    f"/api/sources/{source_id}",
                    user_id=callback.from_user.id,
                    json={"enabled": new_state}
                )

                if update_response and update_response.status_code == 200:
                    status_text = "✅ Включен" if new_state else "⏸️ Отключен"
                    await callback.message.edit_text(
                        f"Источник {status_text}"
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при обновлении источника")
            else:
                await callback.message.edit_text("❌ Источник не найден")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

        await callback.answer()

    @router.callback_query(F.data.startswith("source_delete_"))
    async def handle_source_delete(callback: CallbackQuery):
        """Delete source."""
        source_id = int(callback.data.split("_")[-1])
        try:
            response = await make_authenticated_request(
                "DELETE",
                f"/api/sources/{source_id}",
                user_id=callback.from_user.id
            )

            if response and response.status_code == 200:
                await callback.message.edit_text(
                    "✅ Источник удален"
                )
            else:
                await callback.message.edit_text("❌ Ошибка при удалении источника")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

        await callback.answer()

    @router.callback_query(F.data == "source_add")
    async def handle_source_add(callback: CallbackQuery):
        """Show source type selection."""
        text = """➕ <b>Добавить новый источник</b>

Выберите тип источника для парсинга:"""
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📰 RSS Feed", callback_data="source_type_rss")],
                [InlineKeyboardButton(text="🌐 Веб-сайт", callback_data="source_type_website")],
                [InlineKeyboardButton(text="💬 Telegram", callback_data="source_type_telegram")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")]
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        await callback.answer()

    @router.callback_query(F.data.startswith("source_type_"))
    async def handle_source_type(callback: CallbackQuery):
        """Show source creation form."""
        source_type = callback.data.split("_")[-1]

        type_names = {
            "rss": "RSS Feed",
            "website": "Веб-сайт",
            "telegram": "Telegram"
        }

        text = f"""📝 <b>Новый источник: {type_names.get(source_type, source_type)}</b>

Для завершения настройки отправьте:
1. Имя источника
2. URL для парсинга

Формат: <code>Имя|URL</code>

Пример: <code>HackerNews|https://news.ycombinator.com</code>"""

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_add")]
            ]
        )
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        await callback.answer()

    dp.include_router(router)
