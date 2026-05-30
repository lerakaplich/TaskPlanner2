from datetime import datetime

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from ..states import RegistrationStates
from ..keyboards import get_main_keyboard
from ..utils import get_phone_by_chat, get_employee_id_by_chat
from ..services.user_service import UserService


def register_auth_handlers(dp, bot_instance):
    """Регистрация обработчиков авторизации"""

    user_service = bot_instance.user_service
    user_passwords = bot_instance.user_passwords
    user_sessions = bot_instance.user_sessions

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        await state.clear()
        chat_id = message.chat.id

        from database import get_employees_session, get_tasks_session
        from sqlalchemy import select
        from models.employees import Employee, EmployeeData

        with get_employees_session() as emp_session:
            stmt = select(Employee).where(Employee.chat_id == chat_id)
            existing_employee = emp_session.scalar(stmt)

            if existing_employee:
                phone_digits = existing_employee.phone_number
                saved_password = user_passwords.get(phone_digits)

                if saved_password:
                    await message.answer(
                        f"🤖 *Добро пожаловать, {existing_employee.first_name}!*\n\n"
                        f"✅ Вы уже зарегистрированы в системе.\n\n"
                        f"📞 Телефон: {phone_digits}\n"
                        f"🔐 *Ваш пароль:* `{saved_password}`\n\n"
                        f"⚠️ *Сохраните этот пароль!*",
                        parse_mode="Markdown", reply_markup=get_main_keyboard()
                    )
                    return

                with get_tasks_session() as tasks_session:
                    employee_data = tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == existing_employee.id
                    ).first()

                    if employee_data and employee_data.password_hash:
                        await message.answer(
                            f"🤖 *Добро пожаловать, {existing_employee.first_name}!*\n\n"
                            f"✅ Вы уже зарегистрированы в системе.\n\n"
                            f"⚠️ *Если вы забыли пароль, используйте /reset_password*",
                            parse_mode="Markdown", reply_markup=get_main_keyboard()
                        )
                        return

                    new_password = user_service.generate_password()
                    new_password_hash = user_service.hash_password(new_password)

                    if employee_data:
                        employee_data.password_hash = new_password_hash
                        employee_data.updated_at = datetime.now()
                    else:
                        from models.employees import RoleEnum
                        employee_data = EmployeeData(
                            employee_id=existing_employee.id,
                            password_hash=new_password_hash,
                            is_active=True,
                            role=RoleEnum.user,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        tasks_session.add(employee_data)

                    tasks_session.commit()
                    user_passwords[phone_digits] = new_password

                    await message.answer(
                        f"🤖 *Добро пожаловать, {existing_employee.first_name}!*\n\n"
                        f"✅ Вы уже зарегистрированы в системе.\n\n"
                        f"📞 Телефон: {phone_digits}\n"
                        f"🔐 *Ваш пароль:* `{new_password}`\n\n"
                        f"⚠️ *Сохраните этот пароль!*",
                        parse_mode="Markdown", reply_markup=get_main_keyboard()
                    )
                    return

        # Если пользователь не найден, просим отправить номер
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.answer(
            "🔐 *Для привязки аккаунта к Telegram*\n\n"
            "Нажмите кнопку ниже и разрешите отправку номера телефона.",
            parse_mode="Markdown", reply_markup=keyboard
        )

    @dp.message(Command("reset_password"))
    async def cmd_reset_password(message: types.Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        await message.answer(
            "🔐 *Сброс пароля*\n\n"
            "Введите ваш номер телефона (в формате 375XXXXXXXXX):",
            parse_mode="Markdown"
        )
        user_sessions[user_id] = {"awaiting_reset_phone": True}