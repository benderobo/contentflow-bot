import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

channel_router = Router()

class ChannelStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_telegram_id = State()


@channel_router.callback_query(F.data == "channel_add")
async def handle_channel_add(callback: CallbackQuery, state: FSMContext):
    """Handle channel add."""
    await callback.message.edit_text(
        "📢 **Добавить новый канал**\n\n"
        "Отправьте название канала:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_channels")]]
        )
    )
    await state.set_state(ChannelStates.waiting_for_name)
    await callback.answer()


@channel_router.message(ChannelStates.waiting_for_name)
async def process_channel_name(message: Message, state: FSMContext):
    """Process channel name."""
    await state.update_data(channel_name=message.text)
    await message.answer(
        "Отправьте Telegram ID канала (например: -1001234567890):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_channels")]]
        )
    )
    await state.set_state(ChannelStates.waiting_for_telegram_id)


@channel_router.message(ChannelStates.waiting_for_telegram_id)
async def process_channel_telegram_id(message: Message, state: FSMContext):
    """Process channel telegram ID and save."""
    data = await state.get_data()
    channel_name = data.get("channel_name")
    telegram_id = message.text

    try:
        # Validate telegram_id format
        int(telegram_id)

        response = await make_authenticated_request(
            "POST",
            "/api/channels",
            user_id=message.from_user.id,
            json={
                "name": channel_name,
                "telegram_id": telegram_id,
                "enabled": True,
                "user_id": message.from_user.id
            }
        )

        if response and response.status_code == 200:
            await message.answer(
                f"✅ Канал '{channel_name}' успешно добавлен!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📢 К каналам", callback_data="menu_channels")]]
                )
            )
        else:
            await message.answer(
                f"❌ Ошибка: {response.text}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📢 К каналам", callback_data="menu_channels")]]
                )
            )
    except ValueError:
        await message.answer("❌ Неверный формат Telegram ID")
    finally:
        await state.clear()


@channel_router.callback_query(F.data == "channel_list")
async def handle_channel_list(callback: CallbackQuery):
    """Handle channel list."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/channels?user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            channels = response.json()
            if not channels:
                text = "📢 **Мои каналы**\n\n" \
                       "У вас еще нет каналов. Добавьте первый!"
                markup = [[InlineKeyboardButton(text="➕ Добавить", callback_data="channel_add")]]
            else:
                text = "📢 **Мои каналы**\n\n"
                for ch in channels:
                    status = "✅" if ch["enabled"] else "❌"
                    text += f"{status} {ch['name']} ({ch['telegram_id']})\n"
                markup = [[InlineKeyboardButton(text="➕ Добавить", callback_data="channel_add")]]
        else:
            text = "❌ Ошибка при загрузке каналов"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="channel_list")]]

    except Exception as e:
        logger.error(f"Error fetching channels: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="channel_list")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_channels")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()
