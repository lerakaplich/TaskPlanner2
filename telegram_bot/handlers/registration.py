from datetime import datetime

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import text
from database import get_employees_session, get_tasks_session
from models.employees import Employee, EmployeeData
from shared_state import pending_registrations
from ..keyboards import get_main_keyboard
from ..utils import get_phone_by_chat


def register_registration_handlers(dp, bot_instance):
    """Регистрация обработчиков регистрации (привязка телефона, одобрение заявок)"""

    @dp.message(lambda msg: msg.contact is not None)
    async def process_contact(message: types.Message):
        chat_id = message.chat.id
        phone_number = message.contact.phone_number
        phone_digits = ''.join(filter(str.isdigit, phone_number))

        if phone_digits.startswith('8') and len(phone_digits) == 11:
            phone_digits = '375' + phone_digits[1:]
        if len(phone_digits) == 9:
            phone_digits = '375' + phone_digits

        found_request_id = None
        for req_id, data in pending_registrations.items():
            data_phone = data.get('phone_number', '')
            if data_phone == phone_digits:
                found_request_id = req_id
                break

        if found_request_id:
            pending_registrations[found_request_id]['chat_id'] = chat_id
            await bot_instance.send_registration_to_admins(found_request_id, pending_registrations[found_request_id])
            await message.answer(
                "✅ *Ваш Telegram привязан к заявке!*\n\n"
                "🙏 *Заявка отправлена администратору на одобрение.*\n"
                "Пароль придёт в этот чат после одобрения.",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

        with get_employees_session() as emp_session:
            select_stmt = text("""
                SELECT id, last_name, first_name 
                FROM public.employees 
                WHERE phone_number = :phone
            """)
            employee = emp_session.execute(select_stmt, {'phone': phone_digits}).first()

            if employee:
                employee_id = employee.id
                last_name = employee.last_name
                first_name = employee.first_name

                with get_tasks_session() as tasks_session:
                    employee_data = tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == employee_id
                    ).first()

                    if not employee_data or not employee_data.password_hash:
                        new_password = bot_instance.user_service.generate_password()
                        new_password_hash = bot_instance.user_service.hash_password(new_password)

                        if employee_data:
                            employee_data.password_hash = new_password_hash
                            employee_data.updated_at = datetime.now()
                        else:
                            from models.employees import RoleEnum
                            employee_data = EmployeeData(
                                employee_id=employee_id,
                                password_hash=new_password_hash,
                                is_active=True,
                                role=RoleEnum.user,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            tasks_session.add(employee_data)

                        update_chat_stmt = text("""
                            UPDATE public.employees 
                            SET chat_id = :chat_id
                            WHERE id = :employee_id
                        """)
                        emp_session.execute(update_chat_stmt, {
                            'chat_id': chat_id,
                            'employee_id': employee_id
                        })
                        emp_session.commit()
                        tasks_session.commit()

                        bot_instance.user_passwords[phone_digits] = new_password

                        await message.answer(
                            f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                            f"👤 ФИО: {last_name} {first_name}\n"
                            f"📞 Телефон: {phone_digits}\n"
                            f"🔐 *Ваш пароль:* `{new_password}`\n\n"
                            f"⚠️ *Сохраните этот пароль!*\n\n"
                            f"📅 Я буду присылать вам напоминания о задачах каждый день в 9:00.",
                            parse_mode="Markdown",
                            reply_markup=get_main_keyboard()
                        )
                    else:
                        update_chat_stmt = text("""
                            UPDATE public.employees 
                            SET chat_id = :chat_id
                            WHERE phone_number = :phone
                        """)
                        emp_session.execute(update_chat_stmt, {'chat_id': chat_id, 'phone': phone_digits})
                        emp_session.commit()

                        saved_password = bot_instance.user_passwords.get(phone_digits)
                        if saved_password:
                            await message.answer(
                                f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                                f"👤 ФИО: {last_name} {first_name}\n"
                                f"🔐 *Ваш пароль:* `{saved_password}`\n\n"
                                f"⚠️ *Сохраните этот пароль!*",
                                parse_mode="Markdown",
                                reply_markup=get_main_keyboard()
                            )
                        else:
                            await message.answer(
                                f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                                f"👤 ФИО: {last_name} {first_name}\n\n"
                                f"⚠️ *Если вы забыли пароль, используйте /reset_password*",
                                parse_mode="Markdown",
                                reply_markup=get_main_keyboard()
                            )
                return

        await message.answer(
            "❌ *Не найдено ни заявки, ни зарегистрированного пользователя*\n\n"
            "Пожалуйста, сначала отправьте заявку через приложение TaskPlanner.",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )