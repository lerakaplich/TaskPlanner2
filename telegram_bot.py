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
BOT_TOKEN = "8715984575:AAE-wp9YLbVjRR57ETtzULprSjeta5n9fl8"


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

        # === Обработчики регистрации через бота ===

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

        # === ОБРАБОТЧИКИ КНОПОК ОДОБРЕНИЯ/ОТКЛОНЕНИЯ ===

        @self.dp.callback_query(lambda c: c.data.startswith("approve_"))
        async def approve_registration(callback: types.CallbackQuery):
            request_id = callback.data.split("_")[1]
            registration_data = pending_registrations.get(request_id)

            if not registration_data:
                await callback.answer("❌ Заявка не найдена", show_alert=True)
                return

            # Генерируем пароль
            password = self.generate_password()
            password_hash = self.hash_password(password)

            with get_employees_session() as emp_session:
                try:
                    # Проверяем, есть ли уже такой пользователь
                    from sqlalchemy import text

                    # Получаем следующий номер
                    max_number = emp_session.query(LocalEmployee.number).order_by(LocalEmployee.number.desc()).first()
                    next_number = (max_number[0] + 1) if max_number else 1

                    # Создаем сотрудника в public.employees
                    insert_stmt = text("""
                        INSERT INTO public.employees (
                            number, last_name, first_name, middle_name, 
                            position, rights, phone_number, email, chat_id,
                            birth_date, department_id, division_id, organization_id,
                            password_hash
                        ) VALUES (
                            :number, :last_name, :first_name, :middle_name,
                            :position, :rights, :phone_number, :email, :chat_id,
                            :birth_date, :department_id, :division_id, :organization_id,
                            :password_hash
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
                        'chat_id': registration_data.get('chat_id'),
                        'birth_date': registration_data.get('birth_date'),
                        'department_id': registration_data.get('department_id'),
                        'division_id': registration_data.get('division_id'),
                        'organization_id': 1,
                        'password_hash': password_hash
                    })
                    emp_session.commit()

                    # Получаем ID нового сотрудника
                    result = emp_session.execute(text("SELECT lastval()")).scalar()
                    employee_id = result

                    print(f"✅ Сотрудник добавлен в исходную БД employees, ID: {employee_id}")

                except Exception as e:
                    emp_session.rollback()
                    print(f"❌ Ошибка при добавлении сотрудника: {e}")
                    await callback.answer(f"Ошибка: {e}", show_alert=True)
                    return

            # Отправляем уведомление пользователю
            user_chat_id = registration_data.get('chat_id')
            if user_chat_id:
                try:
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
                except Exception as e:
                    print(f"❌ Ошибка отправки уведомления пользователю: {e}")

            # Обновляем сообщение администратора
            await callback.message.edit_text(
                f"✅ *Заявка одобрена!*\n\n"
                f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} зарегистрирован.\n"
                f"📋 ID сотрудника: {employee_id}",
                parse_mode="Markdown"
            )

            # Удаляем заявку
            pending_registrations.pop(request_id, None)
            await callback.answer("✅ Заявка одобрена")

        @self.dp.callback_query(lambda c: c.data.startswith("reject_"))
        async def reject_registration(callback: types.CallbackQuery):
            request_id = callback.data.split("_")[1]
            registration_data = pending_registrations.get(request_id)

            if registration_data:
                # Уведомляем пользователя об отказе
                user_chat_id = registration_data.get('chat_id')
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


def get_bot():
    """Возвращает экземпляр бота"""
    return telegram_bot.bot