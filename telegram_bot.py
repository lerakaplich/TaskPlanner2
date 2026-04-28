# telegram_bot.py

import asyncio
import logging
import secrets
import string
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import select, update
from database import get_tasks_session, get_employees_session
from models.employees import ExternalEmployee, LocalEmployee
from shared_state import pending_registrations

import hashlib

# Простое хеширование без bcrypt
def simple_hash(password: str) -> str:
    """Простое хеширование пароля SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_simple_hash(plain_password: str, hashed_password: str) -> bool:
    """Проверка простого хеша"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8715984575:AAE-wp9YLbVjRR57ETtzULprSjeta5n9fl8"
user_passwords: Dict[str, str] = {}


# Состояния для FSM
class RegistrationStates(StatesGroup):
    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_middle_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_position = State()
    waiting_for_division = State()
    waiting_for_department = State()


# Хранилище пользовательских сессий
user_sessions: Dict[int, dict] = {}


class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self._setup_handlers()
        self._task = None

    def generate_password(self, length: int = 8) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def hash_password(self, password: str) -> str:
        """Хеширует пароль (простой SHA256)"""
        return simple_hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        if not hashed_password:
            return False
        return verify_simple_hash(plain_password, hashed_password)

    async def send_registration_to_admins(self, request_id: str, registration_data: dict):
        """Отправляет заявку на одобрение администраторам"""
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        with get_tasks_session() as session:
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            # Получаем данные для красивого отображения
            division_name = "Не указано"
            department_name = "Не указано"

            if registration_data.get('division_id'):
                from models.employees import DivisionFDW
                div = session.get(DivisionFDW, registration_data['division_id'])
                division_name = div.name if div else "Не указано"

            if registration_data.get('department_id'):
                from models.employees import DepartmentFDW
                dept = session.get(DepartmentFDW, registration_data['department_id'])
                department_name = dept.name if dept else "Не указано"

            birth_date = registration_data.get('birth_date', 'Не указана')
            if birth_date and birth_date != 'Не указана':
                try:
                    from datetime import datetime
                    birth_date_obj = datetime.fromisoformat(birth_date)
                    birth_date = birth_date_obj.strftime("%d.%m.%Y")
                except:
                    pass

            work_number = registration_data.get('work_number', 'Не указан')
            if not work_number or work_number == '':
                work_number = 'Не указан'

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve|{request_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject|{request_id}")
                ]
            ])

            message_text = (
                f"🆕 *Новая заявка на регистрацию!*\n\n"
                f"📝 *ФИО:* {registration_data.get('last_name')} {registration_data.get('first_name')} {registration_data.get('middle_name') or ''}\n"
                f"📞 *Моб. телефон:* {registration_data.get('phone_number')}\n"
                f"📞 *Раб. телефон:* {work_number}\n"
                f"📧 *Email:* {registration_data.get('email') or 'Не указан'}\n"
                f"🎂 *Дата рождения:* {birth_date}\n"
                f"💼 *Должность:* {registration_data.get('position')}\n"
                f"🏢 *Подразделение:* {division_name}\n"
                f"📁 *Отдел:* {department_name}\n\n"
                f"Telegram привязан ✅\n\n"
                f"Используйте кнопки ниже для подтверждения или отклонения заявки."
            )

            stmt = select(ExternalEmployee).where(
                ExternalEmployee.rights.in_(['admin', 'superadmin'])
            )
            admins = list(session.scalars(stmt))

            if not admins:
                print("⚠️ Нет администраторов для уведомления")
                return

            for admin in admins:
                if admin.chat_id:
                    try:
                        await self.bot.send_message(
                            admin.chat_id,
                            message_text,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                        print(f"✅ Заявка отправлена администратору {admin.id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки администратору {admin.id}: {e}")

    def _setup_handlers(self):
        """Настройка обработчиков команд"""

        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            user_id = message.from_user.id
            chat_id = message.chat.id

            print(f"📱 Пользователь {user_id} (chat_id={chat_id}) нажал /start")

            # Сначала проверяем, есть ли уже пользователь в БД с таким chat_id
            with get_tasks_session() as session:
                stmt = select(ExternalEmployee).where(ExternalEmployee.chat_id == chat_id)
                existing_employee = session.scalar(stmt)

                if existing_employee:
                    await message.answer(
                        f"🤖 *Добро пожаловать, {existing_employee.first_name}!*\n\n"
                        f"Вы уже зарегистрированы в системе.\n"
                        f"Ваш пароль вы получили при регистрации.\n\n"
                        f"Для входа в Telegram бота используйте команду /login",
                        parse_mode="Markdown"
                    )
                    return

            # Проверяем, есть ли пользователь с таким номером телефона в БД (был одобрен, но не привязан Telegram)
            # Для этого сначала просим номер телефона
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Отправить номер телефона", callback_data="send_phone")]
            ])

            await message.answer(
                "🔐 *Для привязки аккаунта к Telegram*\n\n"
                "Пожалуйста, нажмите кнопку ниже и разрешите отправку номера телефона.\n"
                "Мы проверим, зарегистрированы ли вы в системе.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        @self.dp.callback_query(lambda c: c.data == "send_phone")
        async def request_phone(callback: types.CallbackQuery):
            await callback.message.answer(
                "📱 Пожалуйста, отправьте ваш номер телефона, нажав на кнопку ниже:",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[[types.KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            await callback.answer()

        @self.dp.message(lambda msg: msg.contact is not None)
        async def process_contact(message: types.Message):
            chat_id = message.chat.id
            phone_number = message.contact.phone_number

            # Нормализуем номер
            phone_digits = ''.join(filter(str.isdigit, phone_number))

            print(f"📞 Получен номер от Telegram: {phone_number}")
            print(f"📞 Цифры: {phone_digits}")

            # Конвертируем в формат 375XXXXXXXXX
            if phone_digits.startswith('8') and len(phone_digits) == 11:
                phone_digits = '375' + phone_digits[1:]
                print(f"📞 Конвертирован из 8 в 375: {phone_digits}")

            if len(phone_digits) == 9:
                phone_digits = '375' + phone_digits
                print(f"📞 Добавлен 375: {phone_digits}")

            print(f"📞 Итоговый номер для поиска: {phone_digits}")

            # 1. Сначала ищем заявку в pending_registrations
            found_request_id = None
            for req_id, data in pending_registrations.items():
                data_phone = data.get('phone_number', '')
                print(f"🔍 Сравниваем заявку {req_id}: '{data_phone}' == '{phone_digits}'")

                if data_phone == phone_digits:
                    found_request_id = req_id
                    break

            if found_request_id:
                # Привязываем chat_id к заявке
                pending_registrations[found_request_id]['chat_id'] = chat_id
                pending_registrations[found_request_id]['chat_id_bound'] = True

                print(f"✅ Найдена заявка {found_request_id}, привязан chat_id={chat_id}")

                # ТЕПЕРЬ отправляем заявку администратору на одобрение
                await self.send_registration_to_admins(found_request_id, pending_registrations[found_request_id])

                await message.answer(
                    "✅ *Ваш Telegram привязан к заявке!*\n\n"
                    "🙏 *Заявка отправлена администратору на одобрение.*\n"
                    "Пароль придёт в этот чат после одобрения.\n\n"
                    "🕐 Обычно это занимает несколько минут.",
                    parse_mode="Markdown",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return

            # 2. Если заявки нет, проверяем, есть ли пользователь в БД
            with get_employees_session() as emp_session:
                from sqlalchemy import text

                select_stmt = text("""
                    SELECT id, last_name, first_name, middle_name, password_hash, phone_number
                    FROM public.employees 
                    WHERE phone_number = :phone
                """)
                employee = emp_session.execute(select_stmt, {'phone': phone_digits}).first()

                if employee:
                    print(f"✅ Найден сотрудник в БД: {employee.last_name} {employee.first_name}")

                    # Обновляем chat_id в БД
                    update_stmt = text("""
                        UPDATE public.employees 
                        SET chat_id = :chat_id 
                        WHERE phone_number = :phone
                    """)
                    emp_session.execute(update_stmt, {'chat_id': chat_id, 'phone': phone_digits})
                    emp_session.commit()

                    saved_password = user_passwords.get(phone_digits)

                    if saved_password:
                        await message.answer(
                            f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                            f"📋 *Ваши данные:*\n"
                            f"👤 ФИО: {employee.last_name} {employee.first_name} {employee.middle_name or ''}\n"
                            f"📞 Телефон: {phone_digits}\n"
                            f"🔐 *Ваш пароль:* `{saved_password}`\n\n"
                            f"⚠️ *Сохраните этот пароль!*",
                            parse_mode="Markdown",
                            reply_markup=types.ReplyKeyboardRemove()
                        )
                    else:
                        await message.answer(
                            f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                            f"📋 *Ваши данные:*\n"
                            f"👤 ФИО: {employee.last_name} {employee.first_name} {employee.middle_name or ''}\n"
                            f"📞 Телефон: {phone_digits}\n\n"
                            f"⚠️ *Если вы забыли пароль, обратитесь к администратору.*",
                            parse_mode="Markdown",
                            reply_markup=types.ReplyKeyboardRemove()
                        )
                    return

            # 3. Ни заявки, ни пользователя не найдено
            await message.answer(
                "❌ *Не найдено ни заявки, ни зарегистрированного пользователя*\n\n"
                "С таким номером телефона нет активной заявки.\n\n"
                "Пожалуйста:\n"
                "1. Откройте приложение TaskPlanner\n"
                "2. Нажмите 'Нет аккаунта?'\n"
                "3. Заполните форму и отправьте заявку\n"
                "4. Затем вернитесь сюда и нажмите /start\n\n"
                f"Ваш номер: {phone_digits}",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer(
                "📚 *Справка по командам*\n\n"
                "🔐 /login - Вход в систему\n"
                "📝 /register - Регистрация нового пользователя\n"
                "✅ /my_tasks - Показать мои задачи (после входа)\n"
                "➕ /create_task - Создать новую задачу (после входа)\n"
                "📊 /stats - Показать статистику (после входа)\n"
                "❓ /help - Эта справка",
                parse_mode="Markdown"
            )


        @self.dp.message(Command("login"))
        async def cmd_login(message: types.Message):
            user_id = message.from_user.id
            await message.answer(
                "🔐 *Вход в систему*\n\n"
                "Введите ваш номер телефона (в формате 375XXXXXXXXX):",
                parse_mode="Markdown"
            )
            user_sessions[user_id] = {"awaiting_phone": True}

        @self.dp.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("awaiting_phone", False))
        async def process_phone(message: types.Message):
            user_id = message.from_user.id
            phone = message.text.strip()

            with get_tasks_session() as session:
                stmt = select(ExternalEmployee).where(ExternalEmployee.phone_number == phone)
                employee = session.scalar(stmt)

                if not employee:
                    await message.answer(
                        "❌ Пользователь с таким номером не найден. Зарегистрируйтесь с помощью /register")
                    user_sessions.pop(user_id, None)
                    return

                if not employee.password_hash:
                    await message.answer("❌ У этого аккаунта еще нет пароля. Обратитесь к администратору.")
                    user_sessions.pop(user_id, None)
                    return

                user_sessions[user_id] = {
                    "awaiting_password": True,
                    "employee_id": employee.id,
                    "employee_phone": phone
                }
                await message.answer("🔐 Введите ваш пароль:")

        @self.dp.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("awaiting_password", False))
        async def process_password(message: types.Message):
            user_id = message.from_user.id
            password = message.text.strip()
            session_data = user_sessions.get(user_id, {})
            employee_id = session_data.get("employee_id")

            with get_tasks_session() as session:
                stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
                employee = session.scalar(stmt)

                if not employee or not self.verify_password(password, employee.password_hash):
                    await message.answer("❌ Неверный пароль. Попробуйте снова /login")
                    user_sessions.pop(user_id, None)
                    return

                stmt = update(ExternalEmployee).where(ExternalEmployee.id == employee_id).values(chat_id=user_id)
                session.execute(stmt)
                session.commit()

                user_sessions[user_id] = {
                    "authenticated": True,
                    "employee_id": employee_id,
                    "name": f"{employee.last_name} {employee.first_name}",
                    "rights": employee.rights
                }

                await message.answer(
                    f"✅ *Вход выполнен!*\n\n"
                    f"Добро пожаловать, {employee.last_name} {employee.first_name}!\n\n"
                    f"Теперь вы можете использовать все команды бота.",
                    parse_mode="Markdown"
                )

        @self.dp.callback_query(lambda c: c.data.startswith("approve|"))
        async def approve_registration(callback: types.CallbackQuery):
            request_id = callback.data.replace("approve|", "")

            print(f"🔍 Поиск заявки с ID: {request_id}")
            print(f"📋 Доступные заявки: {list(pending_registrations.keys())}")

            registration_data = pending_registrations.get(request_id)

            if not registration_data:
                await callback.answer("❌ Заявка не найдена", show_alert=True)
                return

            print(f"✅ Заявка найдена: {registration_data}")

            password = self.generate_password()
            password_hash = self.hash_password(password)

            # Сохраняем пароль для возможного восстановления
            phone_number = registration_data.get('phone_number')
            if phone_number:
                user_passwords[phone_number] = password
                print(f"💾 Сохранен пароль для {phone_number}: {password}")

            with get_employees_session() as emp_session:
                try:
                    from sqlalchemy import text

                    max_number = emp_session.query(LocalEmployee.number).order_by(LocalEmployee.number.desc()).first()
                    next_number = (max_number[0] + 1) if max_number else 1

                    insert_stmt = text("""
                        INSERT INTO public.employees (
                            number, last_name, first_name, middle_name, 
                            position, rights, phone_number, email,
                            birth_date, department_id, division_id, organization_id,
                            password_hash, chat_id
                        ) VALUES (
                            :number, :last_name, :first_name, :middle_name,
                            :position, :rights, :phone_number, :email,
                            :birth_date, :department_id, :division_id, :organization_id,
                            :password_hash, :chat_id
                        )
                    """)
                    emp_session.execute(insert_stmt, {
                        'number': next_number,
                        'last_name': registration_data.get('last_name'),
                        'first_name': registration_data.get('first_name'),
                        'middle_name': registration_data.get('middle_name'),
                        'position': registration_data.get('position'),
                        'rights': 'user',
                        'phone_number': registration_data.get('phone_number'),
                        'email': registration_data.get('email'),
                        'birth_date': registration_data.get('birth_date'),
                        'department_id': registration_data.get('department_id'),
                        'division_id': registration_data.get('division_id'),
                        'organization_id': 1,
                        'password_hash': password_hash,
                        'chat_id': registration_data.get('chat_id')
                    })
                    emp_session.commit()

                    result = emp_session.execute(text("SELECT lastval()")).scalar()
                    employee_id = result

                    print(f"✅ Сотрудник добавлен, ID: {employee_id}")

                except Exception as e:
                    emp_session.rollback()
                    print(f"❌ Ошибка при добавлении сотрудника: {e}")
                    import traceback
                    traceback.print_exc()
                    await callback.answer(f"Ошибка: {e}", show_alert=True)
                    return

            user_chat_id = registration_data.get('chat_id')
            if user_chat_id:
                try:
                    await self.bot.send_message(
                        user_chat_id,
                        f"✅ *Ваша заявка на регистрацию одобрена!*\n\n"
                        f"📋 *Ваши данные для входа:*\n"
                        f"📞 *Телефон:* {registration_data.get('phone_number')}\n"
                        f"🔐 *Пароль:* `{password}`\n\n"
                        f"⚠️ *Сохраните этот пароль!*\n"
                        f"Вы можете изменить его в приложении TaskPlanner.\n\n"
                        f"Для входа в приложение используйте:\n"
                        f"👉 Телефон: {registration_data.get('phone_number')}\n"
                        f"👉 Пароль: {password}\n\n"
                        f"Также вы можете войти в Telegram бота командой /login",
                        parse_mode="Markdown"
                    )
                    print(f"✅ Пароль отправлен пользователю {user_chat_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки уведомления пользователю: {e}")

            await callback.message.edit_text(
                f"✅ *Заявка одобрена!*\n\n"
                f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} зарегистрирован.\n",
                parse_mode="Markdown"
            )

            pending_registrations.pop(request_id, None)
            await callback.answer("✅ Заявка одобрена")

        @self.dp.callback_query(lambda c: c.data.startswith("reject|"))
        async def reject_registration(callback: types.CallbackQuery):
            request_id = callback.data.replace("reject|", "")
            registration_data = pending_registrations.get(request_id)

            if registration_data:
                user_chat_id = registration_data.get('chat_id')
                # Удаляем сохраненный пароль, если был
                phone_number = registration_data.get('phone_number')
                if phone_number and phone_number in user_passwords:
                    del user_passwords[phone_number]
                    print(f"🗑️ Удален пароль для {phone_number}")

                if user_chat_id:
                    try:
                        await self.bot.send_message(
                            user_chat_id,
                            f"❌ *Ваша заявка на регистрацию отклонена.*\n\n"
                            f"Пожалуйста, свяжитесь с администратором для уточнения причин.\n"
                            f"Вы можете отправить заявку повторно через приложение TaskPlanner.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"❌ Ошибка отправки уведомления пользователю: {e}")

                await callback.message.edit_text(
                    f"❌ *Заявка отклонена*\n\n"
                    f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} получил уведомление об отказе.",
                    parse_mode="Markdown"
                )
                pending_registrations.pop(request_id, None)

            await callback.answer("❌ Заявка отклонена")

    async def start(self):
        """Запуск бота"""
        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)


# Создаем глобальный экземпляр бота
telegram_bot = TelegramBot()
temp_registrations: Dict[int, str] = {}  # {chat_id: request_id}

async def start_bot():
    """Запуск бота"""
    await telegram_bot.start()