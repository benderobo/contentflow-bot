import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

ai_router = Router()

class AIStates(StatesGroup):
    choosing_post = State()
    choosing_style = State()


@ai_router.callback_query(F.data == "ai_rewrite")
async def handle_ai_rewrite(callback: CallbackQuery, state: FSMContext):
    """Handle AI rewriting - list draft posts."""
    from utils.auth import sign_user_id

    user_id = callback.from_user.id
    user_signature = sign_user_id(user_id)

    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/posts?status=draft&user_id={user_id}&user_signature={user_signature}"
        )

        if response and response.status_code == 200:
            posts = response.json()
            if not posts:
                text = "🤖 **Переписать пост**\n\n" \
                       "У вас нет черновиков для переписывания"
                markup = [[InlineKeyboardButton(text="📝 Создать пост", callback_data="post_new")]]
            else:
                text = "🤖 **Выберите пост для переписывания**\n\n"
                markup = []
                for post in posts[:5]:  # Show first 5
                    text += f"📝 {post['title'][:40]}\n"
                    post_id = post['id']
                    markup.append(
                        [InlineKeyboardButton(
                            text=f"✏️ {post['title'][:25]}",
                            callback_data=f"ai_select_post_{post_id}"
                        )]
                    )
        else:
            text = "❌ Ошибка при загрузке постов"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_rewrite")]]

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_rewrite")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@ai_router.callback_query(F.data.startswith("ai_select_post_"))
async def handle_select_post_for_rewrite(callback: CallbackQuery, state: FSMContext):
    """Handle post selection for rewriting."""
    post_id = callback.data.split("_")[-1]
    await state.update_data(post_id=post_id)

    await callback.message.edit_text(
        "🤖 **Выберите стиль переписывания**\n\n"
        "Какой стиль вы предпочитаете?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📰 Нейтральный", callback_data="style_neutral")],
                [InlineKeyboardButton(text="✨ Привлекательный", callback_data="style_engaging")],
                [InlineKeyboardButton(text="🎯 Информативный", callback_data="style_informative")],
                [InlineKeyboardButton(text="💼 Профессиональный", callback_data="style_professional")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_rewrite")]
            ]
        )
    )
    await callback.answer()


@ai_router.callback_query(F.data.startswith("style_"))
async def handle_rewrite_style(callback: CallbackQuery, state: FSMContext):
    """Handle rewrite style selection and trigger AI."""
    data = await state.get_data()
    post_id = data.get("post_id")
    style = callback.data.split("_")[1]

    await callback.message.edit_text(
        "⏳ Переписываю пост через AI...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")]]
        )
    )

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/posts/{post_id}/rewrite",
            user_id=callback.from_user.id,
            json={
                "style": style,
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            result = response.json()
            rewritten_text = result.get("rewritten_content", "")

            await callback.message.edit_text(
                f"✅ **Пост переписан!**\n\n"
                f"📝 Оригинал:\n{result.get('original_content', '')[:200]}...\n\n"
                f"✨ Переписано:\n{rewritten_text[:200]}...",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Использовать", callback_data=f"use_rewrite_{post_id}")],
                        [InlineKeyboardButton(text="🔄 Другой стиль", callback_data="ai_rewrite")],
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")]
                    ]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при переписывании: {response.text if response else 'Unknown error'}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="ai_rewrite")]]
                )
            )
    except Exception as e:
        logger.error(f"Error rewriting post: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="ai_rewrite")]]
            )
        )

    await state.clear()
    await callback.answer()


@ai_router.callback_query(F.data.startswith("use_rewrite_"))
async def handle_use_rewrite(callback: CallbackQuery):
    """Handle using the rewritten content."""
    post_id = callback.data.split("_")[-1]

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/posts/{post_id}/use-rewrite",
            user_id=callback.from_user.id,
            json={
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                "✅ Переписанный текст применен к посту!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📝 К постам", callback_data="menu_posts")]]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text if response else 'Unknown error'}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")]]
                )
            )
    except Exception as e:
        logger.error(f"Error using rewrite: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")]]
            )
        )

    await callback.answer()


@ai_router.callback_query(F.data == "ai_analyze")
async def handle_ai_analyze(callback: CallbackQuery):
    """Show AI analysis of recent source items."""
    from utils.auth import sign_user_id

    user_id = callback.from_user.id
    user_signature = sign_user_id(user_id)

    try:
        # Get recent unanalyzed source items
        response = await make_authenticated_request(
            "GET",
            f"/api/sources/items/unanalyzed?user_id={user_id}&user_signature={user_signature}&limit=5"
        )

        if response and response.status_code == 200:
            items = response.json()
            if not items:
                text = "🔍 **AI Анализ**\n\n" \
                       "Нет новых элементов для анализа"
                markup = [[InlineKeyboardButton(text="📡 К источникам", callback_data="menu_sources")]]
            else:
                text = "🔍 **Результаты анализа**\n\n"
                markup = []
                for item in items[:3]:
                    text += f"📌 {item['title'][:50]}\n"
                    text += f"   📊 Важность: {item.get('importance', 5)}/10\n"
                    text += f"   💭 Настроение: {item.get('sentiment', 'unknown')}\n\n"

                markup.append([InlineKeyboardButton(text="🤖 Переписать", callback_data="ai_rewrite")])
        else:
            text = "❌ Ошибка при загрузке анализа"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_analyze")]]

    except Exception as e:
        logger.error(f"Error fetching analysis: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_analyze")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@ai_router.callback_query(F.data == "ai_auto_rewrite")
async def handle_ai_auto_rewrite(callback: CallbackQuery):
    """Auto-rewrite all new posts with AI."""
    await callback.message.edit_text(
        "⏳ Автоматически переписываю все новые посты...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]])
    )

    try:
        # Get all new posts
        response = await make_authenticated_request(
            "GET",
            f"/api/posts?status=new&user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            posts = response.json()
            if not posts:
                text = "✅ Все посты уже переписаны!\n\nНет новых постов"
                rewritten_count = 0
            else:
                rewritten_count = 0
                for post in posts:
                    try:
                        rewrite_response = await make_authenticated_request(
                            "POST",
                            f"/api/posts/{post['id']}/rewrite",
                            user_id=callback.from_user.id,
                            json={
                                "style": "engaging",
                                "user_id": callback.from_user.id
                            }
                        )

                        if rewrite_response and rewrite_response.status_code == 200:
                            use_response = await make_authenticated_request(
                                "POST",
                                f"/api/posts/{post['id']}/use-rewrite",
                                user_id=callback.from_user.id,
                                json={
                                    "user_id": callback.from_user.id
                                }
                            )
                            if use_response and use_response.status_code == 200:
                                rewritten_count += 1
                    except Exception as e:
                        logger.error(f"Error auto-rewriting post {post['id']}: {e}")
                        continue

                text = f"✅ Автоматическое переписывание завершено!\n\n" \
                       f"📝 Переписано постов: {rewritten_count}/{len(posts)}"
        else:
            text = "❌ Ошибка при получении постов"
            rewritten_count = 0

    except Exception as e:
        logger.error(f"Error in auto-rewrite: {e}")
        text = f"❌ Ошибка: {str(e)}"
        rewritten_count = 0

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Повторить", callback_data="ai_auto_rewrite")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_ai")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()
