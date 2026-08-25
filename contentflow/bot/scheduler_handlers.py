import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from bot.auth import make_authenticated_request

logger = logging.getLogger(__name__)

scheduler_router = Router()

class PublishScheduleStates(StatesGroup):
    choosing_post = State()
    choosing_channel = State()
    choosing_time_type = State()
    choosing_datetime = State()
    choosing_hour = State()
    choosing_minute = State()
    confirming = State()


@scheduler_router.callback_query(F.data == "schedule_publish")
async def handle_schedule_publish(callback: CallbackQuery, state: FSMContext):
    """Handle publish scheduling - list draft posts."""
    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/posts?status=draft&user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            posts = response.json()
            if not posts:
                text = "📅 **Запланировать публикацию**\n\n" \
                       "У вас нет черновиков для публикации"
                markup = [[InlineKeyboardButton(text="📝 Создать пост", callback_data="post_new")]]
            else:
                text = "📅 **Выберите пост для публикации**\n\n"
                markup = []
                for post in posts[:5]:
                    text += f"📝 {post['title'][:40]}\n"
                    post_id = post['id']
                    markup.append(
                        [InlineKeyboardButton(
                            text=f"📌 {post['title'][:25]}",
                            callback_data=f"schedule_select_post_{post_id}"
                        )]
                    )
        else:
            text = "❌ Ошибка при загрузке постов"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="schedule_publish")]]

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="schedule_publish")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_scheduler")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@scheduler_router.callback_query(F.data.startswith("schedule_select_post_"))
async def handle_select_post_for_schedule(callback: CallbackQuery, state: FSMContext):
    """Select post and show channels."""
    post_id = callback.data.split("_")[-1]
    await state.update_data(post_id=post_id)

    try:
        response = await make_authenticated_request(
            "GET",
            f"/api/channels?user_id={callback.from_user.id}"
        )

        if response and response.status_code == 200:
            channels = response.json()
            if not channels:
                text = "📢 **Выберите канал**\n\n" \
                       "У вас нет активных каналов. Добавьте сначала."
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
                                callback_data=f"schedule_select_channel_{ch['id']}"
                            )]
                        )
                if not markup:
                    text = "❌ Нет активных каналов"
                    markup = [[InlineKeyboardButton(text="📢 К каналам", callback_data="menu_channels")]]
        else:
            text = "❌ Ошибка при загрузке каналов"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="schedule_publish")]]

    except Exception as e:
        logger.error(f"Error fetching channels: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="schedule_publish")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_publish")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@scheduler_router.callback_query(F.data.startswith("schedule_select_channel_"))
async def handle_select_channel_for_schedule(callback: CallbackQuery, state: FSMContext):
    """Select channel and show time type options."""
    channel_id = callback.data.split("_")[-1]
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "⏰ **Выберите время публикации**\n\n"
        "Когда вы хотите опубликовать пост?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🕐 Сейчас", callback_data="time_now")],
                [InlineKeyboardButton(text="⏲️ Через время", callback_data="time_later")],
                [InlineKeyboardButton(text="📅 Конкретная дата", callback_data="time_specific")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_select_post")]
            ]
        )
    )
    await callback.answer()


@scheduler_router.callback_query(F.data == "time_now")
async def handle_publish_now(callback: CallbackQuery, state: FSMContext):
    """Publish immediately."""
    data = await state.get_data()
    post_id = data.get("post_id")
    channel_id = data.get("channel_id")

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/publish/now",
            user_id=callback.from_user.id,
            json={
                "post_id": int(post_id),
                "channel_id": int(channel_id),
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                "✅ Пост опубликован!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📅 К планировщику", callback_data="menu_scheduler")]]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text if response else 'Unknown error'}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="schedule_publish")]]
                )
            )
    except Exception as e:
        logger.error(f"Error publishing: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="schedule_publish")]]
            )
        )

    await state.clear()
    await callback.answer()


@scheduler_router.callback_query(F.data == "time_later")
async def handle_publish_later(callback: CallbackQuery, state: FSMContext):
    """Schedule for later - ask for hours and minutes."""
    await callback.message.edit_text(
        "⏰ **Через сколько часов опубликовать?**\n\n"
        "Выберите количество часов (1-24):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="1️⃣ 1 час", callback_data="delay_1")],
                [InlineKeyboardButton(text="2️⃣ 2 часа", callback_data="delay_2")],
                [InlineKeyboardButton(text="4️⃣ 4 часа", callback_data="delay_4")],
                [InlineKeyboardButton(text="8️⃣ 8 часов", callback_data="delay_8")],
                [InlineKeyboardButton(text="1️⃣2️⃣ 12 часов", callback_data="delay_12")],
                [InlineKeyboardButton(text="2️⃣4️⃣ 24 часа", callback_data="delay_24")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_select_channel")]
            ]
        )
    )
    await callback.answer()


@scheduler_router.callback_query(F.data.startswith("delay_"))
async def handle_delay_selection(callback: CallbackQuery, state: FSMContext):
    """Schedule with delay."""
    delay_hours = int(callback.data.split("_")[1])
    data = await state.get_data()
    post_id = data.get("post_id")
    channel_id = data.get("channel_id")

    scheduled_at = datetime.utcnow() + timedelta(hours=delay_hours)

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/publish/schedule",
            user_id=callback.from_user.id,
            json={
                "post_id": int(post_id),
                "channel_id": int(channel_id),
                "scheduled_at": scheduled_at.isoformat(),
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                f"✅ Пост запланирован на:\n"
                f"📅 {scheduled_at.strftime('%d.%m.%Y')}\n"
                f"🕐 {scheduled_at.strftime('%H:%M')}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📅 К планировщику", callback_data="menu_scheduler")]]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text if response else 'Unknown error'}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="schedule_publish")]]
                )
            )
    except Exception as e:
        logger.error(f"Error scheduling: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="schedule_publish")]]
            )
        )

    await state.clear()
    await callback.answer()


@scheduler_router.callback_query(F.data == "time_specific")
async def handle_specific_time(callback: CallbackQuery):
    """Specific time scheduling - placeholder."""
    await callback.message.edit_text(
        "📅 **Конкретная дата и время**\n\n"
        "Отправьте дату в формате: ДД.МММ.ГГГГ ЧЧ:МИ\n"
        "Пример: 25.12.2024 14:30",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_publish")]]
        )
    )
    await callback.answer()


@scheduler_router.callback_query(F.data == "view_scheduled")
async def handle_view_scheduled(callback: CallbackQuery):
    """Show scheduled posts."""
    try:
        from utils.auth import sign_user_id

        user_id = callback.from_user.id
        user_signature = sign_user_id(user_id)

        response = await make_authenticated_request(
            "GET",
            f"/api/publish/scheduled?user_id={user_id}&user_signature={user_signature}"
        )

        if response and response.status_code == 200:
            jobs = response.json()
            if not jobs:
                text = "📅 **Запланированные публикации**\n\n" \
                       "Нет запланированных постов"
                markup = [[InlineKeyboardButton(text="📅 Запланировать", callback_data="schedule_publish")]]
            else:
                text = "📅 **Запланированные публикации**\n\n"
                markup = []
                for job in jobs[:5]:
                    text += f"📝 {job.get('post_title', 'Пост')[:30]}\n"
                    text += f"   🕐 {job.get('scheduled_at', '')}\n"
                    text += f"   📢 {job.get('channel_name', 'Канал')}\n\n"
                    job_id = job.get('id')
                    markup.append(
                        [InlineKeyboardButton(
                            text=f"❌ Отменить",
                            callback_data=f"cancel_job_{job_id}"
                        )]
                    )

                markup.append([InlineKeyboardButton(text="📅 Запланировать еще", callback_data="schedule_publish")])
        else:
            text = "❌ Ошибка при загрузке"
            markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="view_scheduled")]]

    except Exception as e:
        logger.error(f"Error fetching scheduled: {e}")
        text = f"❌ Ошибка: {str(e)}"
        markup = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="view_scheduled")]]

    markup.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_scheduler")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup)
    )
    await callback.answer()


@scheduler_router.callback_query(F.data.startswith("cancel_job_"))
async def handle_cancel_job(callback: CallbackQuery):
    """Cancel scheduled publish job."""
    job_id = callback.data.split("_")[-1]

    try:
        response = await make_authenticated_request(
            "POST",
            f"/api/publish/{job_id}/cancel",
            user_id=callback.from_user.id,
            json={
                "user_id": callback.from_user.id
            }
        )

        if response and response.status_code == 200:
            await callback.message.edit_text(
                "✅ Публикация отменена",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📅 К расписанию", callback_data="view_scheduled")]]
                )
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка: {response.text if response else 'Unknown error'}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="view_scheduled")]]
                )
            )
    except Exception as e:
        logger.error(f"Error canceling job: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data="view_scheduled")]]
            )
        )

    await callback.answer()
