# telegram_bot.py
import asyncio
import logging
import secrets
import string
from datetime import datetime
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from sqlalchemy import select, update, text
from database import get_tasks_session, get_employees_session
from models.employees import Employee, Department, Division  # ← ИСПРАВЛЕНО
from shared_state import pending_registrations

import hashlib

# Конфигурация
BOT_TOKEN = "8715984575:AAE-wp9YLbVjRR57ETtzULprSjeta5n9fl8"
ADMIN_CHAT_ID = -1002827849091  # ID канала/чата для поддержки

# Хранилище паролей
user_passwords: Dict[str, str] = {}

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для FSM
class RegistrationStates(StatesGroup):
    waiting_for_reset_phone = State()
    waiting_for_new_password = State()
    waiting_for_help_message = State()
    waiting_for_task_project = State()
    waiting_for_task_title = State()
    waiting_for_task_description = State()


# Хранилище пользовательских сессий
user_sessions: Dict[int, dict] = {}


# Вспомогательные функции
def simple_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_simple_hash(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_main_keyboard():
    """Главная клавиатура бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Мои задачи")],
            [KeyboardButton(text="➕ Создать задачу")],
            [KeyboardButton(text="🆘 Поддержка")],
            [KeyboardButton(text="🔄 Сбросить пароль")]
        ],
        resize_keyboard=True
    )
    return keyboard


async def get_phone_by_chat(chat_id: int) -> Optional[str]:
    """Получить номер телефона пользователя по chat_id"""
    with get_employees_session() as emp_session:
        select_stmt = text("""
            SELECT phone_number FROM public.employees WHERE chat_id = :chat_id
        """)
        result = emp_session.execute(select_stmt, {'chat_id': chat_id}).first()
        if result:
            return result[0]
    return None


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
        return simple_hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        return verify_simple_hash(plain_password, hashed_password)

    async def send_registration_to_admins(self, request_id: str, registration_data: dict):
        """Отправляет заявку на одобрение администраторам"""
        with get_tasks_session() as session:
            division_name = "Не указано"
            department_name = "Не указано"

            if registration_data.get('division_id'):
                div = session.get(Division, registration_data['division_id'])  # ← ИСПРАВЛЕНО
                division_name = div.name if div else "Не указано"

            if registration_data.get('department_id'):
                dept = session.get(Department, registration_data['department_id'])  # ← ИСПРАВЛЕНО
                department_name = dept.name if dept else "Не указано"

            birth_date = registration_data.get('birth_date', 'Не указана')
            if birth_date and birth_date != 'Не указана':
                try:
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

            # Получаем администраторов из public.employees
            stmt = select(Employee).where(Employee.rights.in_(['admin', 'superadmin']))  # ← ИСПРАВЛЕНО
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

    async def get_user_projects(self, user_id: int):
        """Получить проекты где пользователь является создателем или администратором"""
        with get_employees_session() as emp_session:
            select_stmt = text("""
                SELECT p.id, p.name, p.created_by
                FROM public.projects p
                WHERE p.created_by = :user_id 
                   OR p.id IN (
                       SELECT project_id FROM public.project_admins WHERE user_id = :user_id
                   )
                AND p.is_archived = false
                ORDER BY p.name
            """)
            projects = emp_session.execute(select_stmt, {'user_id': user_id}).fetchall()
            return projects

    async def create_task(self, project_id: int, title: str, description: str, creator_id: int):
        """Создать новую задачу"""
        with get_employees_session() as emp_session:
            insert_stmt = text("""
                INSERT INTO public.tasks (project_id, title, description, status, created_by, created_at)
                VALUES (:project_id, :title, :description, 'new', :creator_id, NOW())
                RETURNING id
            """)
            result = emp_session.execute(insert_stmt, {
                'project_id': project_id,
                'title': title,
                'description': description,
                'creator_id': creator_id
            })
            emp_session.commit()
            task_id = result.scalar()
            return task_id

    async def get_user_tasks(self, user_id: int):
        """Получить задачи пользователя"""
        with get_employees_session() as emp_session:
            select_stmt = text("""
                SELECT t.id, t.title, t.status, t.created_at, p.name as project_name
                FROM public.tasks t
                JOIN public.projects p ON t.project_id = p.id
                WHERE t.assigned_to = :user_id OR t.created_by = :user_id
                ORDER BY t.created_at DESC
                LIMIT 20
            """)
            tasks = emp_session.execute(select_stmt, {'user_id': user_id}).fetchall()
            return tasks

    def _setup_handlers(self):
        """Настройка обработчиков команд"""

        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message, state: FSMContext):
            await state.clear()
            user_id = message.from_user.id
            chat_id = message.chat.id

            print(f"📱 Пользователь {user_id} (chat_id={chat_id}) нажал /start")

            with get_employees_session() as session:
                stmt = select(Employee).where(Employee.chat_id == chat_id)  # ← ИСПРАВЛЕНО
                existing_employee = session.scalar(stmt)
                if existing_employee:
                    await message.answer(
                        f"🤖 *Добро пожаловать, {existing_employee.first_name}!*\n\n"
                        f"Вы уже зарегистрированы в системе.\n\n"
                        f"Используйте кнопки ниже для работы с ботом:",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                    return

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

        @self.dp.message(Command("reset_password"))
        async def cmd_reset_password(message: types.Message, state: FSMContext):
            await state.clear()
            user_id = message.from_user.id

            await message.answer(
                "🔐 *Сброс пароля*\n\n"
                "Введите ваш номер телефона (в формате 375XXXXXXXXX):\n\n"
                "⚠️ *Важно:* Новый пароль будет отправлен в этот чат.",
                parse_mode="Markdown"
            )
            user_sessions[user_id] = {"awaiting_reset_phone": True}

        @self.dp.message(Command("cancel"))
        async def cmd_cancel(message: types.Message, state: FSMContext):
            await state.clear()
            user_id = message.from_user.id
            if user_id in user_sessions:
                user_sessions.pop(user_id)
            await message.answer(
                "✅ *Операция отменена*",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer(
                "📚 Справка по командам\n\n"
                "🔄 /reset_password - Сброс пароля\n"
                "❌ /cancel - Отмена текущей операции\n"
                "✅ /my_tasks - Показать мои задачи\n"
                "➕ /create_task - Создать новую задачу\n"
                "🆘 /support - Поддержка\n"
                "❓ /help - Справочная информация"
            )

        @self.dp.message(Command("my_tasks"))
        async def cmd_my_tasks(message: types.Message, state: FSMContext):
            await state.clear()
            await self.show_my_tasks(message)

        @self.dp.message(Command("create_task"))
        async def cmd_create_task(message: types.Message, state: FSMContext):
            await state.clear()
            await self.start_create_task(message, state)

        @self.dp.message(Command("support"))
        async def cmd_support(message: types.Message, state: FSMContext):
            await state.clear()
            await message.answer(
                "🆘 *Поддержка*\n\n"
                "Напишите ваше сообщение, и администратор свяжется с вами.",
                parse_mode="Markdown"
            )
            await state.set_state(RegistrationStates.waiting_for_help_message)

        # ========== ОБРАБОТКА ТЕКСТОВЫХ КНОПОК ==========

        @self.dp.message(lambda msg: msg.text == "✅ Мои задачи")
        async def btn_my_tasks(message: types.Message, state: FSMContext):
            await state.clear()
            await self.show_my_tasks(message)

        @self.dp.message(lambda msg: msg.text == "➕ Создать задачу")
        async def btn_create_task(message: types.Message, state: FSMContext):
            await state.clear()
            await self.start_create_task(message, state)

        @self.dp.message(lambda msg: msg.text == "🆘 Поддержка")
        async def btn_support(message: types.Message, state: FSMContext):
            await state.clear()
            await message.answer(
                "🆘 *Поддержка*\n\n"
                "Напишите ваше сообщение, и администратор свяжется с вами.",
                parse_mode="Markdown"
            )
            await state.set_state(RegistrationStates.waiting_for_help_message)

        @self.dp.message(lambda msg: msg.text == "🔄 Сбросить пароль")
        async def btn_reset_password(message: types.Message, state: FSMContext):
            await state.clear()
            await cmd_reset_password(message, state)

        # ========== ОБРАБОТЧИКИ СОСТОЯНИЙ ==========

        @self.dp.message(RegistrationStates.waiting_for_help_message)
        async def process_help_message(msg: types.Message, state: FSMContext):
            """Обрабатывает сообщение поддержки и пересылает администратору в канал"""
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
                await self.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
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

        @self.dp.message(RegistrationStates.waiting_for_task_project)
        async def process_task_project(msg: types.Message, state: FSMContext):
            """Обработка выбора проекта для задачи"""
            project_id = msg.text.strip()
            if not project_id.isdigit():
                await msg.answer(
                    "❌ Пожалуйста, введите номер проекта из списка выше:",
                    reply_markup=get_main_keyboard()
                )
                return

            await state.update_data(project_id=int(project_id))
            await msg.answer(
                "📝 *Введите название задачи:*\n\n"
                "Например: Исправить баг в авторизации",
                parse_mode="Markdown"
            )
            await state.set_state(RegistrationStates.waiting_for_task_title)

        @self.dp.message(RegistrationStates.waiting_for_task_title)
        async def process_task_title(msg: types.Message, state: FSMContext):
            """Обработка названия задачи"""
            title = msg.text.strip()
            if len(title) < 3:
                await msg.answer(
                    "❌ Название задачи должно содержать минимум 3 символа.\n"
                    "Пожалуйста, введите название:"
                )
                return

            await state.update_data(task_title=title)
            await msg.answer(
                "📄 *Введите описание задачи:*\n\n"
                "Подробно опишите, что нужно сделать.",
                parse_mode="Markdown"
            )
            await state.set_state(RegistrationStates.waiting_for_task_description)

        @self.dp.message(RegistrationStates.waiting_for_task_description)
        async def process_task_description(msg: types.Message, state: FSMContext):
            """Обработка описания задачи и создание задачи"""
            description = msg.text.strip()
            data = await state.get_data()
            project_id = data.get('project_id')
            title = data.get('task_title')
            user_id = msg.from_user.id

            # Получаем реальный ID пользователя из БД
            with get_employees_session() as emp_session:
                select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
                employee = emp_session.execute(select_stmt, {'chat_id': user_id}).first()
                if not employee:
                    await msg.answer(
                        "❌ Вы не авторизованы. Используйте /login для входа.",
                        reply_markup=get_main_keyboard()
                    )
                    await state.clear()
                    return
                db_user_id = employee[0]

            try:
                task_id = await self.create_task(project_id, title, description, db_user_id)
                await msg.answer(
                    f"✅ *Задача успешно создана!*\n\n"
                    f"📋 ID задачи: {task_id}\n"
                    f"📝 Название: {title}\n\n"
                    f"Вы можете отслеживать её статус в приложении.",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка создания задачи: {e}")
                await msg.answer(
                    "❌ Ошибка при создании задачи. Попробуйте позже.",
                    reply_markup=get_main_keyboard()
                )

            await state.clear()

        # ========== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ==========

        @self.dp.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("awaiting_reset_phone", False))
        async def process_reset_phone(message: types.Message):
            """Обработка номера телефона для сброса пароля"""
            user_id = message.from_user.id
            phone = message.text.strip()

            phone_digits = ''.join(filter(str.isdigit, phone))

            if phone_digits.startswith('8') and len(phone_digits) == 11:
                phone_digits = '375' + phone_digits[1:]

            if len(phone_digits) == 9:
                phone_digits = '375' + phone_digits

            if len(phone_digits) != 12 or not phone_digits.startswith('375'):
                await message.answer(
                    "❌ *Неверный формат номера*\n\n"
                    "Пожалуйста, введите номер в формате 375XXXXXXXXX (12 цифр).",
                    parse_mode="Markdown"
                )
                return

            with get_employees_session() as emp_session:
                select_stmt = text("""
                    SELECT id, last_name, first_name FROM public.employees WHERE phone_number = :phone
                """)
                employee = emp_session.execute(select_stmt, {'phone': phone_digits}).first()

                if not employee:
                    await message.answer(
                        "❌ *Пользователь не найден*\n\n"
                        "Пользователь с таким номером телефона не зарегистрирован в системе.",
                        parse_mode="Markdown"
                    )
                    user_sessions.pop(user_id, None)
                    return

            user_sessions[user_id] = {
                "reset_phone": phone_digits,
                "awaiting_new_password": True,
                "employee_id": employee.id,
                "employee_name": f"{employee.last_name} {employee.first_name}"
            }

            await message.answer(
                f"✅ *Пользователь найден:* {employee.last_name} {employee.first_name}\n\n"
                f"🔐 *Введите новый пароль*\n\n"
                f"Пароль должен содержать не менее 6 символов.",
                parse_mode="Markdown"
            )

        @self.dp.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("awaiting_new_password", False))
        async def process_new_password(message: types.Message):
            """Установка нового пароля"""
            user_id = message.from_user.id
            new_password = message.text.strip()
            session_data = user_sessions.get(user_id, {})

            if len(new_password) < 6:
                await message.answer(
                    "❌ *Пароль слишком короткий*\n\n"
                    "Пароль должен содержать не менее 6 символов.\n"
                    "Пожалуйста, введите другой пароль:",
                    parse_mode="Markdown"
                )
                return

            phone_digits = session_data.get("reset_phone")
            new_password_hash = self.hash_password(new_password)

            with get_employees_session() as emp_session:
                update_stmt = text("""
                    UPDATE public.employees 
                    SET password_hash = :password_hash
                    WHERE phone_number = :phone
                """)
                emp_session.execute(update_stmt, {
                    'password_hash': new_password_hash,
                    'phone': phone_digits
                })
                emp_session.commit()
                user_passwords[phone_digits] = new_password
                print(f"✅ Пароль изменен для пользователя {phone_digits}")

            await message.answer(
                f"✅ *Пароль успешно изменен!*\n\n"
                f"📋 *Ваш новый пароль:* `{new_password}`\n\n"
                f"⚠️ *Сохраните этот пароль!*\n\n"
                f"Теперь вы можете войти в приложение TaskPlanner.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

            user_sessions.pop(user_id, None)

        # ========== КОЛБЭКИ ==========

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
                await self.send_registration_to_admins(found_request_id, pending_registrations[found_request_id])
                await message.answer(
                    "✅ *Ваш Telegram привязан к заявке!*\n\n"
                    "🙏 *Заявка отправлена администратору на одобрение.*\n"
                    "Пароль придёт в этот чат после одобрения.",
                    parse_mode="Markdown",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return

            with get_employees_session() as emp_session:
                select_stmt = text("SELECT id, last_name, first_name FROM public.employees WHERE phone_number = :phone")
                employee = emp_session.execute(select_stmt, {'phone': phone_digits}).first()

                if employee:
                    update_stmt = text("UPDATE public.employees SET chat_id = :chat_id WHERE phone_number = :phone")
                    emp_session.execute(update_stmt, {'chat_id': chat_id, 'phone': phone_digits})
                    emp_session.commit()

                    saved_password = user_passwords.get(phone_digits)
                    if saved_password:
                        await message.answer(
                            f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                            f"👤 ФИО: {employee.last_name} {employee.first_name}\n"
                            f"🔐 *Ваш пароль:* `{saved_password}`\n\n"
                            f"⚠️ *Сохраните этот пароль!*",
                            parse_mode="Markdown",
                            reply_markup=get_main_keyboard()
                        )
                    else:
                        await message.answer(
                            f"✅ *Вы уже зарегистрированы в системе!*\n\n"
                            f"👤 ФИО: {employee.last_name} {employee.first_name}\n\n"
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

        # ========== ОБРАБОТЧИКИ ОДОБРЕНИЯ/ОТКЛОНЕНИЯ ==========

        @self.dp.callback_query(lambda c: c.data.startswith("approve|"))
        async def approve_registration(callback: types.CallbackQuery):
            request_id = callback.data.replace("approve|", "")
            registration_data = pending_registrations.get(request_id)

            if not registration_data:
                await callback.answer("❌ Заявка не найдена", show_alert=True)
                return

            password = self.generate_password()
            password_hash = self.hash_password(password)

            phone_number = registration_data.get('phone_number')
            if phone_number:
                user_passwords[phone_number] = password

            with get_employees_session() as emp_session:
                try:
                    # Получаем следующий номер
                    max_number = emp_session.query(Employee.number).order_by(
                        Employee.number.desc()).first()  # ← ИСПРАВЛЕНО
                    next_number = (max_number[0] + 1) if max_number else 1

                    insert_stmt = text("""
                        INSERT INTO public.employees (
                            number, last_name, first_name, middle_name, 
                            position, rights, phone_number, email,
                            birth_date, department_id, division_id, organization_id,
                            password_hash, chat_id, is_active
                        ) VALUES (
                            :number, :last_name, :first_name, :middle_name,
                            :position, :rights, :phone_number, :email,
                            :birth_date, :department_id, :division_id, :organization_id,
                            :password_hash, :chat_id, true
                        )
                        RETURNING id
                    """)
                    result = emp_session.execute(insert_stmt, {
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
                    new_employee_id = result.scalar()
                    print(f"✅ Сотрудник добавлен, ID: {new_employee_id}")

                    # Добавляем запись в employees_data
                    insert_data_stmt = text("""
                        INSERT INTO public.employees_data (employee_id, is_active, role)
                        VALUES (:employee_id, true, 'user')
                    """)
                    emp_session.execute(insert_data_stmt, {'employee_id': new_employee_id})
                    emp_session.commit()

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
                        f"📞 *Телефон:* {registration_data.get('phone_number')}\n"
                        f"🔐 *Пароль:* `{password}`\n\n"
                        f"⚠️ *Сохраните этот пароль!*\n\n"
                        f"Теперь вы можете войти в приложение TaskPlanner.",
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
                phone_number = registration_data.get('phone_number')
                if phone_number and phone_number in user_passwords:
                    del user_passwords[phone_number]

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

    async def show_my_tasks(self, message: types.Message):
        """Показать задачи пользователя"""
        user_id = message.from_user.id

        with get_employees_session() as emp_session:
            select_employee = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
            employee = emp_session.execute(select_employee, {'chat_id': user_id}).first()

            if not employee:
                await message.answer(
                    "❌ Вы не авторизованы. Используйте /login для входа.",
                    reply_markup=get_main_keyboard()
                )
                return

            db_user_id = employee[0]
            tasks = await self.get_user_tasks(db_user_id)

            if not tasks:
                await message.answer(
                    "📋 *У вас пока нет задач*",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                return

            status_emoji = {
                'new': '🆕',
                'in_progress': '🔄',
                'done': '✅',
                'cancelled': '❌'
            }

            tasks_text = "📋 *Ваши задачи:*\n\n"
            for task in tasks:
                status = status_emoji.get(task.status, '📌')
                tasks_text += f"{status} *{task.title}*\n"
                tasks_text += f"   📁 Проект: {task.project_name}\n"
                tasks_text += f"   🆔 ID: {task.id}\n\n"

            await message.answer(tasks_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

    async def start_create_task(self, message: types.Message, state: FSMContext):
        """Начать создание задачи - показать список проектов"""
        user_id = message.from_user.id

        with get_employees_session() as emp_session:
            select_employee = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
            employee = emp_session.execute(select_employee, {'chat_id': user_id}).first()

            if not employee:
                await message.answer(
                    "❌ Вы не авторизованы. Используйте /login для входа.",
                    reply_markup=get_main_keyboard()
                )
                return

            db_user_id = employee[0]
            projects = await self.get_user_projects(db_user_id)

            if not projects:
                await message.answer(
                    "❌ *У вас нет проектов, в которых вы можете создавать задачи*\n\n"
                    "Вы можете создавать задачи только в проектах, где вы являетесь создателем или администратором.",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                return

            projects_text = "📁 *Выберите проект для создания задачи:*\n\n"
            for project in projects:
                projects_text += f"📌 `{project.id}` - {project.name}\n"

            projects_text += "\nВведите номер проекта из списка:"

            await message.answer(projects_text, parse_mode="Markdown")
            await state.set_state(RegistrationStates.waiting_for_task_project)

    async def start(self):
        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)


telegram_bot = TelegramBot()
temp_registrations: Dict[int, str] = {}


async def start_bot():
    await telegram_bot.start()