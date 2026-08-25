import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

source_router = Router()

class SourceStates(StatesGroup):
    choosing_type = State()
    waiting_for_name = State()
    waiting_for_url = State()
    waiting_for_parse_interval = State()
    waiting_for_custom_interval = State()


@source_router.callback_query(F.data == "source_add")
async def handle_source_add(callback: CallbackQuery, state: FSMContext):
    """Handle source add - show type selection."""
    await callback.message.edit_text(
        "📡 **Добавить новый источник**\n\n"
        "Выберите тип источника:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔗 RSS", callback_data="source_type_rss")],
                [InlineKeyboardButton(text="🌐 Веб-сайт", callback_data="source_type_website")],
                [InlineKeyboardButton(text="✈️ Telegram (открытый)", callback_data="source_type_telegram_public")],
                [InlineKeyboardButton(text="🔐 Telegram (закрытый)", callback_data="source_type_telegram_private")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]
            ]
        )
    )
    await state.set_state(SourceStates.choosing_type)
    await callback.answer()


@source_router.callback_query(F.data.startswith("source_type_"))
async def handle_source_type(callback: CallbackQuery, state: FSMContext):
    """Handle source type selection."""
    callback_data = callback.data
    is_private = "private" in callback_data

    if "telegram" in callback_data:
        source_type = "telegram"
        type_name = "Telegram (закрытый)" if is_private else "Telegram (открытый)"
    else:
        source_type = callback_data.split("_")[-1]
        type_names = {
            "rss": "RSS",
            "website": "Веб-сайт",
        }
        type_name = type_names.get(source_type, source_type)

    await state.update_data(source_type=source_type, is_private=is_private)
    await callback.message.edit_text(
        f"📡 Добавить {type_name}\n\n"
        "Отправьте название источника:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]]
        )
    )
    await state.set_state(SourceStates.waiting_for_name)
    await callback.answer()


@source_router.message(SourceStates.waiting_for_name)
async def process_source_name(message: Message, state: FSMContext):
    """Process source name."""
    data = await state.get_data()
    source_type = data.get("source_type")

    await state.update_data(source_name=message.text)

    # Different prompts for different types
    if source_type == "telegram":
        is_private = data.get("is_private", False)
        if is_private:
            prompt = "🔐 Укажите username закрытого канала (@private_channel)\n\n⚠️ Убедитесь, что добавили номер телефона в TELEGRAM_PHONE для доступа к закрытым каналам."
        else:
            prompt = "Укажите username открытого канала (@habr_ru или t.me/habr_ru):"
    elif source_type == "rss":
        prompt = "Укажите RSS URL (https://example.com/feed.xml):"
    else:  # website
        prompt = "Укажите URL сайта (https://example.com):"

    await message.answer(
        prompt,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]]
        )
    )
    await state.set_state(SourceStates.waiting_for_url)


@source_router.message(SourceStates.waiting_for_url)
async def process_source_url(message: Message, state: FSMContext):
    """Process source URL."""
    data = await state.get_data()
    source_type = data.get("source_type")

    # Validate based on type
    if source_type == "telegram":
        # For Telegram, accept @username or t.me/username
        if not (message.text.startswith("@") or message.text.startswith("t.me/") or message.text.startswith("https://t.me/")):
            await message.answer("❌ Укажите username канала (@habr_ru) или ссылку (t.me/habr_ru)")
            return
    else:
        # For RSS and Website, validate URL
        if not message.text.startswith(("http://", "https://")):
            await message.answer("❌ URL должен начинаться с http:// или https://")
            return

    await state.update_data(source_url=message.text)
    await message.answer(
        "⏱️ Интервал проверки источника:\n\n"
        "Выберите готовый вариант или введите свое значение в минутах:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏱️ 1 час", callback_data="interval_3600")],
                [InlineKeyboardButton(text="⏱️ 30 мин", callback_data="interval_1800")],
                [InlineKeyboardButton(text="⏱️ 5 мин", callback_data="interval_300")],
                [InlineKeyboardButton(text="✏️ Свое значение", callback_data="interval_custom")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]
            ]
        )
    )
    await state.set_state(SourceStates.waiting_for_parse_interval)


@source_router.callback_query(F.data.startswith("interval_"))
async def handle_parse_interval(callback: CallbackQuery, state: FSMContext):
    """Handle parse interval selection and save source."""
    interval_str = callback.data.split("_")[-1]

    # Handle custom interval input
    if interval_str == "custom":
        await callback.message.edit_text(
            "✏️ Введите интервал проверки в минутах:\n\n"
            "Примеры:\n"
            "• 60 = 1 час\n"
            "• 30 = 30 минут\n"
            "• 5 = 5 минут\n"
            "• 1 = 1 минута\n\n"
            "Минимум: 1 минута, максимум: 10080 минут (7 дней)"
        )
        await state.set_state(SourceStates.waiting_for_custom_interval)
        await callback.answer()
        return

    interval = int(interval_str)
    data = await state.get_data()

    source_name = data.get("source_name")
    source_url = data.get("source_url")
    source_type = data.get("source_type")
    is_private = data.get("is_private", False)

    try:
        payload = {
            "name": source_name,
            "type": source_type,
            "url": source_url,
            "parse_interval": interval,
            "enabled": True,
            "user_id": callback.from_user.id
        }

        # For Telegram sources, include is_private flag in parser_config
        if source_type == "telegram":
            payload["parser_config"] = {"is_private": is_private}

        response = await make_authenticated_request(
            "POST",
            "/api/sources",
            user_id=callback.from_user.id,
            json=payload
        )

        if response and response.status_code == 200:
            source_data = response.json()
            source_id = source_data.get("id")
            await callback.message.edit_text(
                f"✅ Источник '{source_name}' добавлен!\n\n"
                f"📡 Тип: {source_type}\n"
                f"🔗 URL: {source_url[:50]}...\n"
                f"⏱️ Интервал: {interval}с",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
                )
            )
        else:
            error_text = response.text if response else "Ошибка подключения к API"
            await callback.message.edit_text(
                f"❌ Ошибка: {error_text}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
                )
            )
    except Exception as e:
        logger.error(f"Error creating source: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
            )
        )
    finally:
        await state.clear()

    await callback.answer()


@source_router.message(SourceStates.waiting_for_custom_interval)
async def process_custom_interval(message: Message, state: FSMContext):
    """Process custom interval input."""
    try:
        interval_minutes = int(message.text)

        # Validate interval
        if interval_minutes < 1 or interval_minutes > 10080:
            await message.answer(
                "❌ Ошибка! Интервал должен быть от 1 до 10080 минут.\n\n"
                "Попробуйте еще раз:"
            )
            return

        # Convert minutes to seconds
        interval = interval_minutes * 60

        data = await state.get_data()
        source_name = data.get("source_name")
        source_url = data.get("source_url")
        source_type = data.get("source_type")
        is_private = data.get("is_private", False)

        try:
            payload = {
                "name": source_name,
                "type": source_type,
                "url": source_url,
                "parse_interval": interval,
                "enabled": True,
                "user_id": message.from_user.id
            }

            if source_type == "telegram":
                payload["parser_config"] = {"is_private": is_private}

            response = await make_authenticated_request(
                "POST",
                "/api/sources",
                user_id=message.from_user.id,
                json=payload
            )

            if response and response.status_code == 200:
                await message.answer(
                    f"✅ Источник '{source_name}' добавлен!\n\n"
                    f"📡 Тип: {source_type}\n"
                    f"🔗 URL: {source_url[:50]}...\n"
                    f"⏱️ Интервал: {interval_minutes} мин ({interval}с)",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
                    )
                )
            else:
                error_text = response.text if response else "Ошибка подключения к API"
                await message.answer(
                    f"❌ Ошибка: {error_text}",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
                    )
                )
        except Exception as e:
            logger.error(f"Error creating source: {e}")
            await message.answer(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
                )
            )
        finally:
            await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число (целое число минут).\n\n"
            "Попробуйте еще раз:"
        )


@source_router.callback_query(F.data == "source_list")
async def handle_source_list(callback: CallbackQuery):
    """Show all sources."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/sources?user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            sources = response.json()
            if not sources:
                text = "📡 **Источники**\n\n" \
                       "У вас еще нет источников. Добавьте первый!"
                markup = [[InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")]]
            else:
                text = "📡 **Источники**\n\n"
                for src in sources:
                    status = "✅" if src["enabled"] else "❌"
                    text += f"{status} {src['name']} ({src['type']})\n"
                markup = [
                    [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                ]
        else:
            text = "❌ Ошибка при загрузке источников"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="source_list")]]

    except Exception as e:
        logger.error(f"Error fetching sources: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="source_list")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@source_router.callback_query(F.data == "source_settings")
async def handle_source_settings(callback: CallbackQuery):
    """Show source settings."""
    text = "⚙️ Настройки источников\n\n" \
           "📋 Управление парсингом и интервалами обновления\n\n" \
           "Настройки доступны в разработке."

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_sources")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()
