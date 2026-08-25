import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
from datetime import datetime
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

post_router = Router()

class PostStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    choosing_channel = State()
    choosing_action = State()


@post_router.callback_query(F.data == "post_new")
async def handle_post_new(callback: CallbackQuery, state: FSMContext):
    """Handle new post creation."""
    await callback.message.edit_text(
        "📝 **Создать новый пост**\n\n"
        "Отправьте заголовок поста:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_posts")]]
        )
    )
    await state.set_state(PostStates.waiting_for_title)
    await callback.answer()


@post_router.message(PostStates.waiting_for_title)
async def process_post_title(message: Message, state: FSMContext):
    """Process post title."""
    await state.update_data(post_title=message.text)
    await message.answer(
        "Отправьте текст поста:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_posts")]]
        )
    )
    await state.set_state(PostStates.waiting_for_content)


@post_router.message(PostStates.waiting_for_content)
async def process_post_content(message: Message, state: FSMContext):
    """Process post content and save as draft."""
    data = await state.get_data()
    title = data.get("post_title")
    content = message.text

    try:
        response = await make_authenticated_request(
            "POST",
            "/api/posts",
            user_id=message.from_user.id,
            json={
                "title": title,
                "body": content,
                "status": "draft",
                "user_id": message.from_user.id
            }
        )

        if response and response.status_code == 200:
            post_data = response.json()
            post_id = post_data.get("id")
            await message.answer(
                f"✅ Пост сохранен как черновик\n\n"
                f"📌 ID: {post_id}\n"
                f"📝 Заголовок: {title}\n"
                f"📄 Текст: {content[:50]}...",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"post_edit_{post_id}")],
                        [InlineKeyboardButton(text="📢 Опубликовать", callback_data=f"post_publish_{post_id}")],
                        [InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]
                    ]
                )
            )
        else:
            await message.answer(
                f"❌ Ошибка: {response.text}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
                )
            )
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
            )
        )
    finally:
        await state.clear()


@post_router.callback_query(F.data == "post_drafts")
async def handle_post_drafts(callback: CallbackQuery):
    """Show draft posts."""
    try:
        response = await make_authenticated_request(
            "GET",
            "/api/posts",
            params={
                "status": "draft",
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            posts = response.json()
            if not posts:
                text = "✏️ **Черновики**\n\n" \
                       "У вас нет черновиков"
                markup = [[InlineKeyboardButton(text="🆕 Создать", callback_data="post_new")]]
            else:
                text = "✏️ **Черновики**\n\n"
                keyboard = []
                for post in posts[:5]:  # Show first 5
                    text += f"📝 {post['title'][:30]}\n"
                    post_id = post['id']
                    keyboard.append(
                        [InlineKeyboardButton(
                            text=f"✏️ {post['title'][:25]}",
                            callback_data=f"post_edit_{post_id}"
                        )]
                    )
                keyboard.append([InlineKeyboardButton(text="🆕 Создать", callback_data="post_new")])
                markup = keyboard
        else:
            text = "❌ Ошибка при загрузке черновиков"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_drafts")]]

    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="post_drafts")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@post_router.callback_query(F.data.startswith("post_publish_"))
async def handle_post_publish(callback: CallbackQuery):
    """Show channels for publishing."""
    post_id = callback.data.split("_")[-1]

    try:
        channels_response = await make_authenticated_request(
            "GET",
            "/api/channels",
            params={"user_id": callback.from_user.id}
        )

        if channels_response and channels_response.status_code == 200:
            channels = channels_response.json()
            if not channels:
                text = "📢 **Выберите канал**\n\n" \
                       "У вас нет каналов. Добавьте канал перед публикацией."
                markup = [[InlineKeyboardButton(text="📢 К каналам", callback_data="menu_channels")]]
            else:
                text = "📢 **Выберите канал для публикации**\n\n"
                markup = []
                for ch in channels:
                    if ch['enabled']:
                        text += f"✅ {ch['name']}\n"
                        markup.append(
                            [InlineKeyboardButton(
                                text=ch['name'],
                                callback_data=f"confirm_publish_{post_id}_{ch['id']}"
                            )]
                        )
                if not markup:
                    text = "📢 **Выберите канал**\n\n" \
                           "Нет активных каналов"
                    markup = [[InlineKeyboardButton(text="📢 К каналам", callback_data="menu_channels")]]
        else:
            text = "❌ Ошибка при загрузке каналов"
            markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")]]

    except Exception as e:
        logger.error(f"Error fetching channels: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_posts")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@post_router.callback_query(F.data.startswith("confirm_publish_"))
async def handle_confirm_publish(callback: CallbackQuery):
    """Confirm and publish post."""
    parts = callback.data.split("_")
    post_id = parts[2]
    channel_id = parts[3]

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/posts/{post_id}/publish",
            json={
                "channel_id": int(channel_id),
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                "✅ Пост успешно опубликован!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
                )
            )
    except Exception as e:
        logger.error(f"Error publishing post: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
            )
        )

    await callback.answer()
