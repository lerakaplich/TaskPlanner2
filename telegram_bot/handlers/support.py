import logging

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from ..states import RegistrationStates
from ..keyboards import get_main_keyboard
from ..utils import get_phone_by_chat
from datetime import datetime

logger = logging.getLogger(__name__)

def register_support_handlers(dp, bot_instance):
    """Регистрация обработчиков поддержки"""

    @dp.message(Command("support"))
    async def cmd_support(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "🆘 *Поддержка*\n\n"
            "Напишите ваше сообщение, и администратор свяжется с вами.",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_help_message)

    @dp.message(lambda msg: msg.text == "🆘 Поддержка")
    async def btn_support(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "🆘 *Поддержка*\n\n"
            "Напишите ваше сообщение, и администратор свяжется с вами.",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_help_message)

    @dp.message(RegistrationStates.waiting_for_help_message)
    async def process_help_message(msg: types.Message, state: FSMContext):
        help_text = msg.text
        user_id = msg.from_user.id
        user_name = msg.from_user.full_name or "Неизвестный пользователь"
        username = msg.from_user.username or "нет username"

        phone = await get_phone_by_chat(user_id)
        phone_info = f"📱 Телефон: {phone}" if phone else "📱 Телефон: не привязан"

        admin_message = (
            f"🆘 <b>НОВОЕ СООБЩЕНИЕ В ПОДДЕРЖКУ ИЗ TASKPLANNER</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}\n"
            f"📛 <b>Username:</b> @{username}\n"
            f"{phone_info}\n"
            f"📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"💬 <b>Сообщение:</b>\n{help_text}"
        )

        try:
            await bot_instance.bot.send_message(
                chat_id=bot_instance.ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode="HTML"
            )
            await msg.answer(
                "✅ Ваше сообщение отправлено администратору. Ожидайте ответа.",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения в канал: {e}")
            await msg.answer(
                "❌ Произошла ошибка при отправке сообщения. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )

        await state.clear()