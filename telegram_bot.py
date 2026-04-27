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

# Проверяем наличие passlib, если нет - используем простой хеш
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    HAS_PASSLIB = True
except ImportError:
    HAS_PASSLIB = False
    import hashlib
    print("⚠️ passlib не установлен, используется простой хеш SHA256")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8588263896:AAG3pbyT6HHcXxmXWOKYyc0-zdi2Gf2IAoY"


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
pending_registrations: Dict[int, dict] = {}


class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self._setup_handlers()
        self._task = None

    def generate_password(self, length: int = 8) -> str:
        """Генерирует случайный надежный пароль"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def hash_password(self, password: str) -> str:
        """Хеширует пароль"""
        if HAS_PASSLIB:
            return pwd_context.hash(password)
        else:
            # Простой хеш SHA256 для тестирования
            return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        if not hashed_password:
            return False
        if HAS_PASSLIB:
            try:
                return pwd_context.verify(plain_password, hashed_password)
            except:
                return False
        else:
            return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

    def _setup_handlers(self):
        """Настройка обработчиков команд"""

        # === Основные команды ===
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "🤖 *TaskPlanner Бот*\n\n"
                "Я помогу вам управлять задачами, получать уведомления и статистику!\n\n"
                "🔐 Если у вас уже есть аккаунт, войдите с помощью команды /login\n"
                "📝 Если нет аккаунта, зарегистрируйтесь с помощью команды /register\n\n"
                "📋 Доступные команды:\n"
                "/login - Вход в систему\n"
                "/register - Регистрация нового пользователя\n"
                "/my_tasks - Мои задачи (после входа)\n"
                "/create_task - Создать задачу (после входа)\n"
                "/stats - Статистика (после входа)\n"
                "/help - Помощь",
                parse_mode="Markdown"
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

                # Обновляем chat_id
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

        @self.dp.message(Command("register"))
        async def cmd_register(message: types.Message, state: FSMContext):
            user_id = message.from_user.id

            # Проверяем, не зарегистрирован ли уже пользователь
            with get_tasks_session() as session:
                stmt = select(ExternalEmployee).where(ExternalEmployee.chat_id == user_id)
                existing = session.scalar(stmt)
                if existing:
                    await message.answer("❌ Вы уже зарегистрированы в системе! Используйте /login для входа.")
                    return

            await message.answer(
                "📝 *Регистрация нового пользователя*\n\n"
                "Пожалуйста, введите вашу фамилию:",
                parse_mode="Markdown"
            )
            await state.set_state(RegistrationStates.waiting_for_last_name)
            await state.update_data(chat_id=user_id)

        @self.dp.message(RegistrationStates.waiting_for_last_name)
        async def process_last_name(message: types.Message, state: FSMContext):
            await state.update_data(last_name=message.text.strip())
            await message.answer("Введите ваше имя:")
            await state.set_state(RegistrationStates.waiting_for_first_name)

        @self.dp.message(RegistrationStates.waiting_for_first_name)
        async def process_first_name(message: types.Message, state: FSMContext):
            await state.update_data(first_name=message.text.strip())
            await message.answer("Введите ваше отчество (или '-' чтобы пропустить):")
            await state.set_state(RegistrationStates.waiting_for_middle_name)

        @self.dp.message(RegistrationStates.waiting_for_middle_name)
        async def process_middle_name(message: types.Message, state: FSMContext):
            middle_name = None if message.text == "-" else message.text.strip()
            await state.update_data(middle_name=middle_name)
            await message.answer("Введите ваш номер телефона (в формате 375XXXXXXXXX):")
            await state.set_state(RegistrationStates.waiting_for_phone)

        @self.dp.message(RegistrationStates.waiting_for_phone)
        async def process_phone_reg(message: types.Message, state: FSMContext):
            phone = message.text.strip()
            if not (len(phone) == 12 and phone.startswith('375')):
                await message.answer("❌ Неверный формат номера. Используйте формат 375XXXXXXXXX:")
                return

            # Проверяем, не занят ли номер
            with get_tasks_session() as session:
                stmt = select(ExternalEmployee).where(ExternalEmployee.phone_number == phone)
                existing = session.scalar(stmt)
                if existing:
                    await message.answer("❌ Этот номер телефона уже зарегистрирован. Используйте /login для входа.")
                    await state.clear()
                    return

            await state.update_data(phone_number=phone)
            await message.answer("Введите ваш email (или '-' чтобы пропустить):")
            await state.set_state(RegistrationStates.waiting_for_email)

        @self.dp.message(RegistrationStates.waiting_for_email)
        async def process_email(message: types.Message, state: FSMContext):
            email = None if message.text == "-" else message.text.strip()
            await state.update_data(email=email)
            await message.answer("Введите вашу должность:")
            await state.set_state(RegistrationStates.waiting_for_position)

        @self.dp.message(RegistrationStates.waiting_for_position)
        async def process_position(message: types.Message, state: FSMContext):
            await state.update_data(position=message.text.strip())

            # Получаем список подразделений
            with get_tasks_session() as session:
                from models.employees import DivisionFDW
                stmt = select(DivisionFDW).order_by(DivisionFDW.name)
                divisions = list(session.scalars(stmt))

                if not divisions:
                    await message.answer("❌ Нет доступных подразделений. Обратитесь к администратору.")
                    await state.clear()
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=div.name, callback_data=f"div_{div.id}")] for div in divisions[:10]
                ])
                await message.answer("📁 Выберите ваше подразделение:", reply_markup=keyboard)
                await state.set_state(RegistrationStates.waiting_for_division)

        @self.dp.callback_query(lambda c: c.data.startswith("div_"))
        async def process_division(callback: types.CallbackQuery, state: FSMContext):
            division_id = int(callback.data.split("_")[1])
            await state.update_data(division_id=division_id)

            # Получаем список отделов для выбранного подразделения
            with get_tasks_session() as session:
                from models.employees import DepartmentFDW
                stmt = select(DepartmentFDW).where(DepartmentFDW.division_id == division_id).order_by(
                    DepartmentFDW.name)
                departments = list(session.scalars(stmt))

                if not departments:
                    await callback.message.answer("⚠️ В этом подразделении нет отделов. Выберите другой.")
                    await state.set_state(RegistrationStates.waiting_for_division)
                    await callback.answer()
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=dept.name, callback_data=f"dept_{dept.id}")] for dept in departments[:10]
                ])
                await callback.message.answer("🏢 Выберите ваш отдел:", reply_markup=keyboard)
                await state.set_state(RegistrationStates.waiting_for_department)

            await callback.answer()

        @self.dp.callback_query(lambda c: c.data.startswith("dept_"))
        async def process_department(callback: types.CallbackQuery, state: FSMContext):
            department_id = int(callback.data.split("_")[1])
            await state.update_data(department_id=department_id)

            registration_data = await state.get_data()

            # Отправляем запрос на одобрение администраторам
            await self.send_approval_request(callback.message.chat.id, registration_data)
            await callback.message.answer(
                "✅ *Заявка на регистрацию отправлена!*\n\n"
                "Администратор рассмотрит вашу заявку и свяжется с вами.\n"
                "Обычно это занимает несколько минут.",
                parse_mode="Markdown"
            )
            await state.clear()
            await callback.answer()

        # Обработчики для одобрения/отклонения (внутри метода setup_handlers)
        @self.dp.callback_query(lambda c: c.data.startswith("approve_"))
        async def approve_registration(callback: types.CallbackQuery):
            user_chat_id = int(callback.data.split("_")[1])
            registration_data = pending_registrations.get(user_chat_id)

            if not registration_data:
                await callback.answer("❌ Заявка не найдена", show_alert=True)
                return

            # Генерируем пароль
            password = self.generate_password()
            password_hash = self.hash_password(password)

            # Получаем следующий номер
            with get_employees_session() as emp_session:
                from models.employees import LocalEmployee
                max_number = emp_session.query(LocalEmployee.number).order_by(LocalEmployee.number.desc()).first()
                next_number = (max_number[0] + 1) if max_number else 1

                # Создаем сотрудника в локальной БД
                new_employee = LocalEmployee(
                    number=next_number,
                    last_name=registration_data.get('last_name'),
                    first_name=registration_data.get('first_name'),
                    middle_name=registration_data.get('middle_name'),
                    position=registration_data.get('position'),
                    rights='user',
                    phone_number=registration_data.get('phone_number'),
                    email=registration_data.get('email'),
                    chat_id=user_chat_id,
                    department_id=registration_data.get('department_id'),
                    division_id=registration_data.get('division_id'),
                    organization_id=1,
                    password_hash=password_hash
                )
                emp_session.add(new_employee)
                emp_session.commit()

            # Отправляем уведомление пользователю
            await self.bot.send_message(
                user_chat_id,
                f"✅ *Ваша заявка одобрена!*\n\n"
                f"📋 *Ваши данные для входа:*\n"
                f"📞 *Телефон:* {registration_data.get('phone_number')}\n"
                f"🔐 *Пароль:* `{password}`\n\n"
                f"⚠️ *Сохраните этот пароль!*\n"
                f"Вы можете изменить его в приложении TaskPlanner.\n\n"
                f"Для входа используйте команду /login",
                parse_mode="Markdown"
            )

            await callback.message.edit_text(
                f"✅ *Заявка одобрена!*\n\n"
                f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} зарегистрирован.\n"
                f"Ему отправлены данные для входа.",
                parse_mode="Markdown"
            )

            # Удаляем заявку
            pending_registrations.pop(user_chat_id, None)
            await callback.answer()

        @self.dp.callback_query(lambda c: c.data.startswith("reject_"))
        async def reject_registration(callback: types.CallbackQuery):
            user_chat_id = int(callback.data.split("_")[1])
            registration_data = pending_registrations.get(user_chat_id)

            if registration_data:
                # Уведомляем пользователя об отказе
                await self.bot.send_message(
                    user_chat_id,
                    f"❌ *Ваша заявка на регистрацию отклонена.*\n\n"
                    f"Пожалуйста, свяжитесь с администратором для уточнения причин.\n"
                    f"Вы можете отправить заявку повторно с помощью команды /register.",
                    parse_mode="Markdown"
                )

                await callback.message.edit_text(
                    f"❌ *Заявка отклонена*\n\n"
                    f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} получил уведомление об отказе.",
                    parse_mode="Markdown"
                )
                pending_registrations.pop(user_chat_id, None)

            await callback.answer()

    async def send_approval_request(self, user_chat_id: int, registration_data: dict):
        """Отправляет запрос на одобрение всем администраторам и суперадминистраторам"""
        with get_tasks_session() as session:
            # Находим всех администраторов и суперадминистраторов
            stmt = select(ExternalEmployee).where(
                ExternalEmployee.rights.in_(['admin', 'superadmin'])
            )
            admins = list(session.scalars(stmt))

            # Сохраняем данные заявки
            pending_registrations[user_chat_id] = registration_data

            for admin in admins:
                if admin.chat_id:
                    # Получаем названия отдела и подразделения
                    division_name = ""
                    department_name = ""

                    if registration_data.get('division_id'):
                        from models.employees import DivisionFDW
                        div = session.get(DivisionFDW, registration_data['division_id'])
                        division_name = div.name if div else "Не указано"

                    if registration_data.get('department_id'):
                        from models.employees import DepartmentFDW
                        dept = session.get(DepartmentFDW, registration_data['department_id'])
                        department_name = dept.name if dept else "Не указано"

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_chat_id}"),
                            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_chat_id}")
                        ]
                    ])

                    await self.bot.send_message(
                        admin.chat_id,
                        f"🆕 *Новая заявка на регистрацию!*\n\n"
                        f"📝 *ФИО:* {registration_data.get('last_name')} {registration_data.get('first_name')} {registration_data.get('middle_name') or ''}\n"
                        f"📞 *Телефон:* {registration_data.get('phone_number')}\n"
                        f"📧 *Email:* {registration_data.get('email') or 'Не указан'}\n"
                        f"💼 *Должность:* {registration_data.get('position')}\n"
                        f"🏢 *Подразделение:* {division_name}\n"
                        f"📁 *Отдел:* {department_name}\n\n"
                        f"Используйте кнопки ниже для подтверждения или отклонения заявки.",
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    logger.info(f"Approval request sent to admin {admin.id}")

    async def send_notification(self, user_id: int, message: str):
        """Отправляет уведомление пользователю"""
        try:
            await self.bot.send_message(user_id, message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")

    async def start(self):
        """Запуск бота"""
        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)

    def run(self):
        """Запуск бота в отдельном потоке"""
        try:
            asyncio.run(self.start())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())


# Создаем глобальный экземпляр бота
telegram_bot = TelegramBot()


def start_telegram_bot():
    """Запуск бота в отдельном потоке"""
    import threading
    bot_thread = threading.Thread(target=telegram_bot.run, daemon=True)
    bot_thread.start()
    return bot_thread