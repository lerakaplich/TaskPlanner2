# telegram_bot.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from sqlalchemy import select, and_, or_
from database import get_tasks_session
from models.tasks import Task
from models.projects import Project
from models.employees import ExternalEmployee
from services.tasks_service import TasksService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8588263896:AAG3pbyT6HHcXxmXWOKYyc0-zdi2Gf2IAoY"


# Состояния для FSM
class TaskCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()
    waiting_for_project = State()


class StatsStates(StatesGroup):
    waiting_for_period = State()


# Хранилище пользовательских сессий
user_sessions: Dict[int, dict] = {}


class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.setup_handlers()
        self._task = None

    def setup_handlers(self):
        """Настройка обработчиков команд"""

        # === Основные команды ===
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            user_id = message.from_user.id
            user_sessions[user_id] = {"authenticated": False}

            await message.answer(
                "🤖 *TaskPlanner Бот*\n\n"
                "Я помогу вам управлять задачами, получать уведомления и статистику!\n\n"
                "🔐 Для начала работы выполните команду /auth\n\n"
                "📋 Доступные команды:\n"
                "/auth - Авторизация\n"
                "/my_tasks - Мои задачи\n"
                "/create_task - Создать задачу\n"
                "/stats - Статистика\n"
                "/reminders - Напомнить о задачах\n"
                "/help - Помощь",
                parse_mode="Markdown"
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer(
                "📚 *Справка по командам*\n\n"
                "🔐 /auth - Авторизоваться в системе\n"
                "✅ /my_tasks - Показать мои задачи\n"
                "➕ /create_task - Создать новую задачу\n"
                "📊 /stats - Показать статистику\n"
                "⏰ /reminders - Напомнить о просроченных задачах\n"
                "❓ /help - Эта справка",
                parse_mode="Markdown"
            )

        @self.dp.message(Command("auth"))
        async def cmd_auth(message: types.Message):
            await message.answer(
                "🔐 *Авторизация*\n\n"
                "Введите ваш ID сотрудника (число):\n\n"
                "💡 *Как узнать ID?*\n"
                "Обратитесь к администратору системы.",
                parse_mode="Markdown"
            )
            user_sessions[message.from_user.id] = {"authenticated": False, "awaiting_auth": True}

        @self.dp.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("awaiting_auth", False))
        async def process_auth(message: types.Message):
            user_id = message.from_user.id
            try:
                employee_id = int(message.text.strip())

                with get_tasks_session() as session:
                    stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
                    employee = session.scalar(stmt)

                    if employee:
                        user_sessions[user_id] = {
                            "authenticated": True,
                            "employee_id": employee_id,
                            "name": f"{employee.last_name} {employee.first_name}",
                            "awaiting_auth": False
                        }
                        await message.answer(
                            f"✅ *Авторизация успешна!*\n\n"
                            f"Добро пожаловать, {employee.last_name} {employee.first_name}!\n\n"
                            f"Теперь вы можете использовать все команды бота.",
                            parse_mode="Markdown"
                        )
                    else:
                        await message.answer(
                            "❌ *Ошибка авторизации*\n\n"
                            f"Сотрудник с ID {employee_id} не найден.\n"
                            "Попробуйте снова или обратитесь к администратору.",
                            parse_mode="Markdown"
                        )
            except ValueError:
                await message.answer("❌ Введите корректный числовой ID")

        @self.dp.message(Command("my_tasks"))
        async def cmd_my_tasks(message: types.Message):
            user_id = message.from_user.id
            if not user_sessions.get(user_id, {}).get("authenticated", False):
                await message.answer("⚠️ Сначала выполните авторизацию: /auth")
                return

            employee_id = user_sessions[user_id]["employee_id"]

            with get_tasks_session() as session:
                # Получаем задачи, где пользователь исполнитель
                stmt = select(Task).where(
                    or_(
                        Task.assigned_to == employee_id,
                        Task.created_by == employee_id
                    )
                ).order_by(Task.deadline)
                tasks = list(session.scalars(stmt))

                if not tasks:
                    await message.answer("📭 У вас нет задач")
                    return

                # Группируем задачи
                active_tasks = []
                overdue_tasks = []
                completed_tasks = []

                for task in tasks:
                    task_dict = self._task_to_dict(task)
                    if task.completed or (task.column and task.column.is_done_column):
                        completed_tasks.append(task_dict)
                    elif task.deadline and task.deadline.date() < datetime.now().date():
                        overdue_tasks.append(task_dict)
                    else:
                        active_tasks.append(task_dict)

                # Формируем сообщение
                msg = f"📋 *Мои задачи*\n\n"

                if overdue_tasks:
                    msg += "⚠️ *Просроченные:*\n"
                    for t in overdue_tasks[:5]:
                        msg += f"  • {t['title']} (до {t['deadline']})\n"
                    msg += "\n"

                if active_tasks:
                    msg += "🔄 *Активные:*\n"
                    for t in active_tasks[:10]:
                        msg += f"  • {t['title']}\n"
                    msg += "\n"

                if completed_tasks:
                    msg += f"✅ *Выполнено:* {len(completed_tasks)}\n"

                msg += f"\n📊 *Всего задач:* {len(tasks)}"

                await message.answer(msg, parse_mode="Markdown")

        @self.dp.message(Command("create_task"))
        async def cmd_create_task(message: types.Message, state: FSMContext):
            user_id = message.from_user.id
            if not user_sessions.get(user_id, {}).get("authenticated", False):
                await message.answer("⚠️ Сначала выполните авторизацию: /auth")
                return

            await message.answer("➕ *Создание новой задачи*\n\nВведите название задачи:", parse_mode="Markdown")
            await state.set_state(TaskCreationStates.waiting_for_title)
            await state.update_data(user_id=user_id)

        @self.dp.message(TaskCreationStates.waiting_for_title)
        async def process_task_title(message: types.Message, state: FSMContext):
            await state.update_data(title=message.text)
            await message.answer("📝 Введите описание задачи (или '-' чтобы пропустить):")
            await state.set_state(TaskCreationStates.waiting_for_description)

        @self.dp.message(TaskCreationStates.waiting_for_description)
        async def process_task_description(message: types.Message, state: FSMContext):
            desc = None if message.text == "-" else message.text
            await state.update_data(description=desc)

            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Низкий"), KeyboardButton(text="Средний")],
                    [KeyboardButton(text="Высокий"), KeyboardButton(text="Критический")]
                ],
                resize_keyboard=True
            )
            await message.answer("⚡ Выберите приоритет:", reply_markup=keyboard)
            await state.set_state(TaskCreationStates.waiting_for_priority)

        @self.dp.message(TaskCreationStates.waiting_for_priority)
        async def process_task_priority(message: types.Message, state: FSMContext):
            priority = message.text
            if priority not in ["Низкий", "Средний", "Высокий", "Критический"]:
                await message.answer("❌ Выберите один из вариантов на клавиатуре")
                return

            await state.update_data(priority=priority)

            # Убираем клавиатуру
            await message.answer("📅 Введите дату дедлайна в формате ГГГГ-ММ-ДД (или '-' чтобы пропустить):",
                                 reply_markup=types.ReplyKeyboardRemove())
            await state.set_state(TaskCreationStates.waiting_for_deadline)

        @self.dp.message(TaskCreationStates.waiting_for_deadline)
        async def process_task_deadline(message: types.Message, state: FSMContext):
            deadline = None
            if message.text != "-":
                try:
                    deadline = datetime.strptime(message.text, "%Y-%m-%d").date()
                except ValueError:
                    await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
                    return

            await state.update_data(deadline=deadline)

            # Получаем проекты
            with get_tasks_session() as session:
                stmt = select(Project).where(Project.is_archived == False)
                projects = list(session.scalars(stmt))

                if not projects:
                    await message.answer("❌ Нет доступных проектов для создания задачи")
                    await state.clear()
                    return

                keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=p.name)] for p in projects[:10]],
                    resize_keyboard=True
                )
                await message.answer("📁 Выберите проект:", reply_markup=keyboard)
                await state.set_state(TaskCreationStates.waiting_for_project)

        @self.dp.message(TaskCreationStates.waiting_for_project)
        async def process_task_project(message: types.Message, state: FSMContext):
            project_name = message.text
            data = await state.get_data()

            with get_tasks_session() as session:
                # Ищем проект
                stmt = select(Project).where(Project.name == project_name)
                project = session.scalar(stmt)

                if not project:
                    await message.answer("❌ Проект не найден. Попробуйте снова:",
                                         reply_markup=types.ReplyKeyboardRemove())
                    await state.clear()
                    return

                # Создаем задачу
                task_data = {
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "priority": data.get("priority"),
                    "deadline": data.get("deadline").isoformat() if data.get("deadline") else None,
                    "project_id": project.id,
                    "status": "К выполнению",
                    "created_by": user_sessions[data["user_id"]]["employee_id"],
                    "assigned_to": user_sessions[data["user_id"]]["employee_id"]
                }

                task_service = TasksService(session, {"id": data["user_id"]}, mode="my")

                try:
                    new_task = task_service.create_task(task_data)
                    await message.answer(
                        f"✅ *Задача создана!*\n\n"
                        f"📌 *Название:* {data['title']}\n"
                        f"📁 *Проект:* {project.name}\n"
                        f"⚡ *Приоритет:* {data['priority']}\n"
                        f"📅 *Дедлайн:* {data['deadline'] if data.get('deadline') else 'Не указан'}\n\n"
                        f"ID задачи: {new_task['id']}",
                        parse_mode="Markdown",
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                except Exception as e:
                    await message.answer(f"❌ Ошибка создания задачи: {str(e)}")

            await state.clear()

        @self.dp.message(Command("stats"))
        async def cmd_stats(message: types.Message):
            user_id = message.from_user.id
            if not user_sessions.get(user_id, {}).get("authenticated", False):
                await message.answer("⚠️ Сначала выполните авторизацию: /auth")
                return

            employee_id = user_sessions[user_id]["employee_id"]

            with get_tasks_session() as session:
                stmt = select(Task).where(
                    or_(
                        Task.assigned_to == employee_id,
                        Task.created_by == employee_id
                    )
                )
                tasks = list(session.scalars(stmt))

                total = len(tasks)
                completed = sum(1 for t in tasks if t.completed or (t.column and t.column.is_done_column))
                active = total - completed

                overdue = 0
                for t in tasks:
                    if t.deadline and not t.completed and not (t.column and t.column.is_done_column):
                        if t.deadline.date() < datetime.now().date():
                            overdue += 1

                # Прогресс
                progress = int((completed / total) * 100) if total > 0 else 0

                # Получаем количество проектов
                proj_stmt = select(Project).join(
                    "members", aliased=True
                ).where(...)
                # Упрощенно
                projects_count = len(set(t.project_id for t in tasks if t.project_id))

                msg = (
                    f"📊 *Ваша статистика*\n\n"
                    f"📋 *Всего задач:* {total}\n"
                    f"✅ *Выполнено:* {completed}\n"
                    f"🔄 *В работе:* {active}\n"
                    f"⚠️ *Просрочено:* {overdue}\n"
                    f"📁 *Проектов:* {projects_count}\n\n"
                    f"📈 *Прогресс:* {'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n"
                )

                # Рейтинг
                if total > 0:
                    rating = (completed / total) * 5
                    stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
                    msg += f"\n🏆 *Рейтинг:* {stars} ({rating:.1f}/5)"

                await message.answer(msg, parse_mode="Markdown")

        @self.dp.message(Command("reminders"))
        async def cmd_reminders(message: types.Message):
            user_id = message.from_user.id
            if not user_sessions.get(user_id, {}).get("authenticated", False):
                await message.answer("⚠️ Сначала выполните авторизацию: /auth")
                return

            employee_id = user_sessions[user_id]["employee_id"]

            with get_tasks_session() as session:
                # Просроченные задачи
                stmt = select(Task).where(
                    and_(
                        Task.assigned_to == employee_id,
                        Task.deadline < datetime.now().date(),
                        Task.completed == False
                    )
                )
                overdue_tasks = list(session.scalars(stmt))

                # Задачи на сегодня
                today = datetime.now().date()
                stmt = select(Task).where(
                    and_(
                        Task.assigned_to == employee_id,
                        Task.deadline == today,
                        Task.completed == False
                    )
                )
                today_tasks = list(session.scalars(stmt))

                # Задачи на завтра
                tomorrow = today + timedelta(days=1)
                stmt = select(Task).where(
                    and_(
                        Task.assigned_to == employee_id,
                        Task.deadline == tomorrow,
                        Task.completed == False
                    )
                )
                tomorrow_tasks = list(session.scalars(stmt))

                msg = "⏰ *Напоминания о задачах*\n\n"

                if overdue_tasks:
                    msg += "⚠️ *Просроченные задачи:*\n"
                    for t in overdue_tasks:
                        msg += f"  • {t.title}\n"
                    msg += "\n"
                else:
                    msg += "✅ Нет просроченных задач\n\n"

                if today_tasks:
                    msg += "🔴 *На сегодня:*\n"
                    for t in today_tasks:
                        msg += f"  • {t.title}\n"
                    msg += "\n"

                if tomorrow_tasks:
                    msg += "🟡 *На завтра:*\n"
                    for t in tomorrow_tasks:
                        msg += f"  • {t.title}\n"
                    msg += "\n"

                if not overdue_tasks and not today_tasks and not tomorrow_tasks:
                    msg += "🎉 У вас нет срочных задач на ближайшее время!"

                await message.answer(msg, parse_mode="Markdown")

    def _task_to_dict(self, task: Task) -> dict:
        """Преобразует задачу в словарь"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else None,
            "priority": task.priority.value if task.priority else "medium",
            "completed": task.completed or (task.column and task.column.is_done_column)
        }

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