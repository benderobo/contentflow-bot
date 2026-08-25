import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

source_settings_router = Router()


class SourceSettingsStates(StatesGroup):
    viewing_settings = State()
    editing_interval = State()
    editing_max_posts = State()
    editing_keywords = State()
    editing_exclusions = State()


@source_settings_router.callback_query(F.data == "source_settings")
async def handle_source_settings_menu(callback: CallbackQuery):
    """Show source settings menu."""
    await callback.message.edit_text(
        "⚙️ Настройки источников\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Управлять источником", callback_data="source_manage_list")],
                [InlineKeyboardButton(text="🔧 Общие настройки парсинга", callback_data="source_parsing_settings")],
                [InlineKeyboardButton(text="🔄 Настройки обновления", callback_data="source_update_settings")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")],
            ]
        )
    )
    await callback.answer()


@source_settings_router.callback_query(F.data == "source_manage_list")
async def handle_manage_source_list(callback: CallbackQuery):
    """Show list of user's sources with manage options."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/sources?user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            sources = response.json()
            if not sources:
                await callback.message.edit_text(
                    "📭 У вас нет источников.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                            [InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")]
                        ]
                    )
                )
                await callback.answer()
                return

            buttons = []
            for source in sources:
                status = "✅" if source.get("enabled") else "⛔"
                buttons.append(
                    [InlineKeyboardButton(
                        text=f"{status} {source.get('name')[:30]}",
                        callback_data=f"source_edit_{source.get('id')}"
                    )]
                )
            buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")])

            await callback.message.edit_text(
                "📋 Ваши источники:\n\n"
                "✅ - активный | ⛔ - отключен",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка загрузки источников",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")]]
                )
            )
    except Exception as e:
        logger.error(f"Error loading sources: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")]]
            )
        )

    await callback.answer()


@source_settings_router.callback_query(F.data.startswith("source_edit_"))
async def handle_edit_source(callback: CallbackQuery, state: FSMContext):
    """Show edit menu for a specific source."""
    source_id = int(callback.data.split("_")[-1])

    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            source = response.json()
            status = "✅ Активный" if source.get("enabled") else "⛔ Отключен"

            await state.update_data(editing_source_id=source_id, source_data=source)

            source_info = (
                f"📡 **{source.get('name')}**\n\n"
                f"📊 Тип: {source.get('type')}\n"
                f"🔗 URL: {source.get('url', 'N/A')[:50]}...\n"
                f"⏱️ Интервал: {source.get('parse_interval', 3600)}с\n"
                f"📍 Статус: {status}\n"
            )

            await callback.message.edit_text(
                source_info,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⏱️ Изменить интервал", callback_data=f"source_edit_interval_{source_id}")],
                        [InlineKeyboardButton(text="🔢 Макс постов", callback_data=f"source_edit_max_posts_{source_id}")],
                        [InlineKeyboardButton(text="🔑 Ключевые слова", callback_data=f"source_edit_keywords_{source_id}")],
                        [InlineKeyboardButton(text="❌ Исключить слова", callback_data=f"source_edit_exclusions_{source_id}")],
                        [InlineKeyboardButton(text="🔄 " + ("Отключить" if source.get("enabled") else "Включить"), callback_data=f"source_toggle_{source_id}")],
                        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"source_delete_{source_id}")],
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="source_manage_list")],
                    ]
                )
            )
        else:
            await callback.message.edit_text(
                "❌ Источник не найден",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="source_manage_list")]]
                )
            )
    except Exception as e:
        logger.error(f"Error editing source: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="source_manage_list")]]
            )
        )

    await callback.answer()


@source_settings_router.callback_query(F.data.startswith("source_edit_interval_"))
async def handle_edit_interval(callback: CallbackQuery, state: FSMContext):
    """Edit source parse interval."""
    source_id = int(callback.data.split("_")[-1])

    await state.update_data(editing_source_id=source_id)
    await callback.message.edit_text(
        "⏱️ Введите новый интервал обновления в минутах:\n\n"
        "Текущие варианты:\n"
        "• 60 = 1 час\n"
        "• 30 = 30 минут\n"
        "• 5 = 5 минут\n\n"
        "Минимум: 1 минута, максимум: 7 дней"
    )
    await state.set_state(SourceSettingsStates.editing_interval)
    await callback.answer()


@source_settings_router.message(SourceSettingsStates.editing_interval)
async def process_new_interval(message: Message, state: FSMContext):
    """Process new interval input."""
    try:
        interval_minutes = int(message.text)

        if interval_minutes < 1 or interval_minutes > 10080:
            await message.answer(
                "❌ Интервал должен быть от 1 до 10080 минут.\n\nПопробуйте еще раз:"
            )
            return

        data = await state.get_data()
        source_id = data.get("editing_source_id")
        interval_seconds = interval_minutes * 60

        try:
            response = await make_authenticated_request(
                "PATCH",
                f"/api/sources/{source_id}?user_id={message.from_user.id}",
                user_id=message.from_user.id,
                json={"user_id": message.from_user.id, "parse_interval": interval_seconds}
            )

            if response and response.status_code == 200:
                await message.answer(
                    f"✅ Интервал обновлен на {interval_minutes} минут!\n\n"
                    f"({interval_seconds} секунд)"
                )
            else:
                error = response.text if response else "Ошибка подключения"
                await message.answer(f"❌ Ошибка: {error}")
        except Exception as e:
            logger.error(f"Error updating interval: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")

        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число (целое число минут).\n\nПопробуйте еще раз:"
        )


@source_settings_router.callback_query(F.data.startswith("source_edit_max_posts_"))
async def handle_edit_max_posts(callback: CallbackQuery, state: FSMContext):
    """Edit max posts per parse."""
    source_id = int(callback.data.split("_")[-1])

    await state.update_data(editing_source_id=source_id)
    await callback.message.edit_text(
        "🔢 Введите максимальное количество постов для парсинга:\n\n"
        "Типичные значения:\n"
        "• 10 = быстро, экономно\n"
        "• 20 = баланс\n"
        "• 50 = полный контент\n\n"
        "Минимум: 1, максимум: 100"
    )
    await state.set_state(SourceSettingsStates.editing_max_posts)
    await callback.answer()


@source_settings_router.message(SourceSettingsStates.editing_max_posts)
async def process_max_posts(message: Message, state: FSMContext):
    """Process max posts input."""
    try:
        max_posts = int(message.text)

        if max_posts < 1 or max_posts > 100:
            await message.answer(
                "❌ Значение должно быть от 1 до 100.\n\nПопробуйте еще раз:"
            )
            return

        data = await state.get_data()
        source_id = data.get("editing_source_id")

        try:
            parser_config = {"max_posts": max_posts}

            response = await make_authenticated_request(
                "PATCH",
                f"/api/sources/{source_id}?user_id={message.from_user.id}",
                user_id=message.from_user.id,
                json={"user_id": message.from_user.id, "parser_config": parser_config}
            )

            if response and response.status_code == 200:
                await message.answer(
                    f"✅ Максимум постов установлен на {max_posts}!"
                )
            else:
                error = response.text if response else "Ошибка подключения"
                await message.answer(f"❌ Ошибка: {error}")
        except Exception as e:
            logger.error(f"Error updating max_posts: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")

        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число.\n\nПопробуйте еще раз:"
        )


@source_settings_router.callback_query(F.data.startswith("source_edit_keywords_"))
async def handle_edit_keywords(callback: CallbackQuery, state: FSMContext):
    """Edit filter keywords."""
    source_id = int(callback.data.split("_")[-1])

    await state.update_data(editing_source_id=source_id)
    await callback.message.edit_text(
        "🔑 Выберите готовый фильтр или введите свои ключевые слова:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💻 IT & Технологии", callback_data="keyword_it")],
                [InlineKeyboardButton(text="📰 Новости", callback_data="keyword_news")],
                [InlineKeyboardButton(text="💰 Бизнес & Финансы", callback_data="keyword_business")],
                [InlineKeyboardButton(text="📱 Социальные сети", callback_data="keyword_social")],
                [InlineKeyboardButton(text="✏️ Свои слова", callback_data="keyword_custom")],
                [InlineKeyboardButton(text="❌ Отключить фильтр", callback_data="keyword_disable")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="source_manage_list")],
            ]
        )
    )
    await callback.answer()


@source_settings_router.callback_query(F.data == "keyword_custom")
async def handle_custom_keywords(callback: CallbackQuery, state: FSMContext):
    """Handle custom keyword input."""
    await callback.message.edit_text(
        "✏️ Введите ключевые слова для фильтрации (разделите запятыми):\n\n"
        "Примеры:\n"
        "• python, javascript, golang\n"
        "• технология, новости, события\n\n"
        "Оставьте пусто для отключения фильтра"
    )
    await state.set_state(SourceSettingsStates.editing_keywords)
    await callback.answer()


# Preset keyword filters
PRESET_KEYWORDS = {
    "keyword_it": ["python", "javascript", "golang", "kotlin", "rust", "devops", "cloud", "ai"],
    "keyword_news": ["новости", "события", "происшествия", "сообщает", "объявил"],
    "keyword_business": ["бизнес", "компания", "стартап", "финансы", "инвестиции", "сделка"],
    "keyword_social": ["instagram", "tiktok", "facebook", "twitter", "telegram", "social"],
}


@source_settings_router.callback_query(F.data.in_(["keyword_it", "keyword_news", "keyword_business", "keyword_social"]))
async def handle_preset_keywords(callback: CallbackQuery, state: FSMContext):
    """Apply preset keywords."""
    filter_type = callback.data
    keywords = PRESET_KEYWORDS.get(filter_type, [])

    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        filters = {"keywords": keywords}

        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id, "filters": filters}
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                f"✅ Фильтр применен:\n\n"
                f"{', '.join(keywords)}"
            )
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error applying preset keywords: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await state.clear()
    await callback.answer()


@source_settings_router.callback_query(F.data == "keyword_disable")
async def handle_disable_keywords(callback: CallbackQuery, state: FSMContext):
    """Disable keywords filter."""
    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id, "filters": {}}
        )

        if response and response.status_code == 200:
            await callback.message.edit_text("✅ Фильтр ключевых слов отключен")
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error disabling keywords: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await state.clear()
    await callback.answer()


@source_settings_router.message(SourceSettingsStates.editing_keywords)
async def process_keywords(message: Message, state: FSMContext):
    """Process keywords input."""
    keywords = [k.strip().lower() for k in message.text.split(",") if k.strip()]

    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        filters = {"keywords": keywords} if keywords else {}

        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={message.from_user.id}",
            user_id=message.from_user.id,
            json={"user_id": message.from_user.id, "filters": filters}
        )

        if response and response.status_code == 200:
            if keywords:
                await message.answer(
                    f"✅ Ключевые слова установлены:\n\n"
                    f"{', '.join(keywords)}"
                )
            else:
                await message.answer("✅ Фильтр ключевых слов отключен")
        else:
            error = response.text if response else "Ошибка подключения"
            await message.answer(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error updating keywords: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

    await state.clear()


@source_settings_router.callback_query(F.data.startswith("source_edit_exclusions_"))
async def handle_edit_exclusions(callback: CallbackQuery, state: FSMContext):
    """Edit exclusion keywords."""
    source_id = int(callback.data.split("_")[-1])

    await state.update_data(editing_source_id=source_id)
    await callback.message.edit_text(
        "❌ Выберите готовый фильтр исключения или введите свои слова:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚫 Спам & Реклама", callback_data="exclusion_spam")],
                [InlineKeyboardButton(text="⚠️ Некачественный контент", callback_data="exclusion_low_quality")],
                [InlineKeyboardButton(text="🔞 NSFW", callback_data="exclusion_nsfw")],
                [InlineKeyboardButton(text="📢 Дублированное", callback_data="exclusion_duplicate")],
                [InlineKeyboardButton(text="✏️ Свои слова", callback_data="exclusion_custom")],
                [InlineKeyboardButton(text="❌ Отключить фильтр", callback_data="exclusion_disable")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="source_manage_list")],
            ]
        )
    )
    await callback.answer()


@source_settings_router.callback_query(F.data == "exclusion_custom")
async def handle_custom_exclusions(callback: CallbackQuery, state: FSMContext):
    """Handle custom exclusion input."""
    await callback.message.edit_text(
        "❌ Введите слова для исключения (разделите запятыми):\n\n"
        "Примеры:\n"
        "• спам, реклама, фейк\n"
        "• неработающие, старые\n\n"
        "Посты с этими словами будут пропущены."
    )
    await state.set_state(SourceSettingsStates.editing_exclusions)
    await callback.answer()


# Preset exclusion filters
PRESET_EXCLUSIONS = {
    "exclusion_spam": ["спам", "реклама", "рекламный", "маркетинг", "промо"],
    "exclusion_low_quality": ["фейк", "фальшивый", "неправда", "ложь", "несостоятельный"],
    "exclusion_nsfw": ["18+", "adult", "xxx", "explicit", "pornography"],
    "exclusion_duplicate": ["дублирован", "повтор", "скопирован", "копия", "переход"],
}


@source_settings_router.callback_query(F.data.in_(["exclusion_spam", "exclusion_low_quality", "exclusion_nsfw", "exclusion_duplicate"]))
async def handle_preset_exclusions(callback: CallbackQuery, state: FSMContext):
    """Apply preset exclusions."""
    filter_type = callback.data
    exclusions = PRESET_EXCLUSIONS.get(filter_type, [])

    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        filters = {"exclusions": exclusions}

        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id, "filters": filters}
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                f"✅ Фильтр исключения применен:\n\n"
                f"{', '.join(exclusions)}"
            )
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error applying preset exclusions: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await state.clear()
    await callback.answer()


@source_settings_router.callback_query(F.data == "exclusion_disable")
async def handle_disable_exclusions(callback: CallbackQuery, state: FSMContext):
    """Disable exclusion filter."""
    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id, "filters": {}}
        )

        if response and response.status_code == 200:
            await callback.message.edit_text("✅ Фильтр исключения отключен")
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error disabling exclusions: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await state.clear()
    await callback.answer()


@source_settings_router.message(SourceSettingsStates.editing_exclusions)
async def process_exclusions(message: Message, state: FSMContext):
    """Process exclusion words input."""
    exclusions = [w.strip().lower() for w in message.text.split(",") if w.strip()]

    data = await state.get_data()
    source_id = data.get("editing_source_id")

    try:
        filters = {"exclusions": exclusions} if exclusions else {}

        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={message.from_user.id}",
            user_id=message.from_user.id,
            json={"user_id": message.from_user.id, "filters": filters}
        )

        if response and response.status_code == 200:
            if exclusions:
                await message.answer(
                    f"✅ Слова исключения установлены:\n\n"
                    f"{', '.join(exclusions)}"
                )
            else:
                await message.answer("✅ Фильтр исключения отключен")
        else:
            error = response.text if response else "Ошибка подключения"
            await message.answer(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error updating exclusions: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

    await state.clear()


@source_settings_router.callback_query(F.data.startswith("source_toggle_"))
async def handle_toggle_source(callback: CallbackQuery, state: FSMContext):
    """Enable/disable source."""
    source_id = int(callback.data.split("_")[-1])

    try:
        data = await state.get_data()
        source_data = data.get("source_data", {})
        current_enabled = source_data.get("enabled", True)
        new_enabled = not current_enabled

        response = await make_authenticated_request(
            "PATCH",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id, "enabled": new_enabled}
        )

        if response and response.status_code == 200:
            status_text = "✅ Включен" if new_enabled else "⛔ Отключен"
            await callback.message.edit_text(
                f"✅ Источник {status_text}!"
            )
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error toggling source: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await callback.answer()


@source_settings_router.callback_query(F.data.startswith("source_delete_"))
async def handle_delete_source(callback: CallbackQuery):
    """Delete source with confirmation."""
    source_id = int(callback.data.split("_")[-1])

    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить этот источник?\n\n"
        "Это действие невозможно отменить!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"source_delete_confirm_{source_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"source_edit_{source_id}")],
            ]
        )
    )
    await callback.answer()


@source_settings_router.callback_query(F.data.startswith("source_delete_confirm_"))
async def handle_delete_confirm(callback: CallbackQuery):
    """Confirm source deletion."""
    source_id = int(callback.data.split("_")[-1])

    try:
        response = await make_authenticated_request(
            "DELETE",
            f"/api/sources/{source_id}?user_id={callback.from_user.id}",
            user_id=callback.from_user.id,
            json={"user_id": callback.from_user.id}
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                f"✅ Источник удален!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📋 К источникам", callback_data="source_manage_list")]]
                )
            )
        else:
            error = response.text if response else "Ошибка подключения"
            await callback.message.edit_text(f"❌ Ошибка: {error}")
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

    await callback.answer()


@source_settings_router.callback_query(F.data == "source_parsing_settings")
async def handle_parsing_settings(callback: CallbackQuery):
    """Show global parsing settings."""
    await callback.message.edit_text(
        "🔧 Настройки парсинга\n\n"
        "Эти настройки применяются ко всем новым источникам:\n\n"
        "⏱️ Интервал парсинга: 1 час (по умолчанию)\n"
        "🔢 Макс постов: 20 (по умолчанию)\n"
        "⚡ Таймаут: 30 сек\n"
        "🔁 Retry при ошибке: 3 попытки\n",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏱️ Интервал по умолчанию", callback_data="parsing_default_interval")],
                [InlineKeyboardButton(text="🔢 Макс постов по умолчанию", callback_data="parsing_default_max_posts")],
                [InlineKeyboardButton(text="⚡ Таймаут", callback_data="parsing_timeout")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")],
            ]
        )
    )
    await callback.answer()


@source_settings_router.callback_query(F.data == "source_update_settings")
async def handle_update_settings(callback: CallbackQuery):
    """Show update schedule settings."""
    await callback.message.edit_text(
        "🔄 Настройки обновления\n\n"
        "📊 Статус обновлений: ✅ Активны\n"
        "🔄 Обновлено источников: 12\n"
        "⏭️ Следующее обновление: в течение 5 мин\n"
        "📌 Время последнего обновления: 2 мин назад\n",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить все сейчас", callback_data="update_all_now")],
                [InlineKeyboardButton(text="⏸️ Приостановить обновления", callback_data="update_pause")],
                [InlineKeyboardButton(text="📊 История обновлений", callback_data="update_history")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="source_settings")],
            ]
        )
    )
    await callback.answer()
