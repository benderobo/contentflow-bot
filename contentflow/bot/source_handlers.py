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
                [InlineKeyboardButton(text="✈️ Telegram канал", callback_data="source_type_telegram")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]
            ]
        )
    )
    await state.set_state(SourceStates.choosing_type)
    await callback.answer()


@source_router.callback_query(F.data.startswith("source_type_"))
async def handle_source_type(callback: CallbackQuery, state: FSMContext):
    """Handle source type selection."""
    source_type = callback.data.split("_")[-1]
    type_names = {
        "rss": "RSS",
        "website": "Веб-сайт",
        "telegram": "Telegram канал"
    }

    await state.update_data(source_type=source_type)
    await callback.message.edit_text(
        f"📡 **Добавить {type_names.get(source_type)}**\n\n"
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
    await state.update_data(source_name=message.text)
    await message.answer(
        "Отправьте URL источника:",
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

    # Validate URL
    if not message.text.startswith(("http://", "https://")):
        await message.answer("❌ URL должен начинаться с http:// или https://")
        return

    await state.update_data(source_url=message.text)
    await message.answer(
        "Интервал проверки в секундах (по умолчанию 3600 = 1 час):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏱️ 1 час", callback_data="interval_3600")],
                [InlineKeyboardButton(text="⏱️ 30 мин", callback_data="interval_1800")],
                [InlineKeyboardButton(text="⏱️ 5 мин", callback_data="interval_300")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_sources")]
            ]
        )
    )
    await state.set_state(SourceStates.waiting_for_parse_interval)


@source_router.callback_query(F.data.startswith("interval_"))
async def handle_parse_interval(callback: CallbackQuery, state: FSMContext):
    """Handle parse interval selection and save source."""
    interval = int(callback.data.split("_")[-1])
    data = await state.get_data()

    source_name = data.get("source_name")
    source_url = data.get("source_url")
    source_type = data.get("source_type")

    try:
        response = await make_authenticated_request(
            "POST",
            "/api/sources",
            user_id=callback.from_user.id,
            json={
                "name": source_name,
                "type": source_type,
                "url": source_url,
                "parse_interval": interval,
                "enabled": True,
                "user_id": callback.from_user.id
            }
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
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text}",
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
