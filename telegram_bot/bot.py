import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .handlers.auth import register_auth_handlers
from .handlers.callbacks import register_callback_handlers
from .handlers.overtime import register_overtime_handlers
from .handlers.registration import register_registration_handlers
from .handlers.support import register_support_handlers
from .handlers.tasks import register_tasks_handlers
from .states import RegistrationStates
from .keyboards import get_main_keyboard, get_priority_keyboard, get_difficulty_keyboard
from .utils import get_phone_by_chat, get_employee_id_by_chat
from .services.user_service import UserService
from .services.task_service import TaskService
from .services.notification_service import NotificationService

from sqlalchemy import text, select
from database import get_tasks_session, get_employees_session
from models.employees import Employee, Department, Division, EmployeeData
from shared_state import pending_registrations

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.BOT_TOKEN = "8715984575:AAE-wp9YLbVjRR57ETtzULprSjeta5n9fl8"
        self.ADMIN_CHAT_ID = -1002827849091

        self.bot = Bot(token=self.BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        self.user_service = UserService()
        self.task_service = TaskService()
        self.notification_service = NotificationService(self.bot)

        self.user_passwords = self.user_service.user_passwords
        self.user_sessions = self.user_service.user_sessions

        self._reminder_task = None
        self._setup_handlers()

    async def send_registration_to_admins(self, request_id: str, registration_data: dict):
        """Отправляет заявку на одобрение администраторам"""
        with get_employees_session() as emp_session:
            division_name = "Не указано"
            department_name = "Не указано"

            if registration_data.get('division_id'):
                div = emp_session.get(Division, registration_data['division_id'])
                division_name = div.name if div else "Не указано"

            if registration_data.get('department_id'):
                dept = emp_session.get(Department, registration_data['department_id'])
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

            # Получаем ID администраторов из БД taskplanner
            with get_tasks_session() as tasks_session:
                from models.employees import EmployeeData, RoleEnum

                stmt = select(EmployeeData.employee_id).where(
                    EmployeeData.role.in_([RoleEnum.admin, RoleEnum.superadmin])
                )
                admin_ids = [row[0] for row in tasks_session.execute(stmt).fetchall()]

                print(f"📋 Найдены ID администраторов: {admin_ids}")

            if not admin_ids:
                print("⚠️ Нет администраторов для уведомления")
                return

            # Получаем данные администраторов из БД employees
            with get_employees_session() as emp_session2:
                from models.employees import Employee

                stmt = select(Employee).where(Employee.id.in_(admin_ids))
                admins = list(emp_session2.scalars(stmt))

            for admin in admins:
                if admin.chat_id:
                    try:
                        await self.bot.send_message(
                            admin.chat_id,
                            message_text,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                        print(f"✅ Заявка отправлена администратору {admin.id} ({admin.last_name} {admin.first_name})")
                    except Exception as e:
                        print(f"❌ Ошибка отправки администратору {admin.id}: {e}")

    async def send_project_notification(self, user_chat_id: int, project_name: str,
                                        manager_name: str, description: str,
                                        role: str):
        """Отправляет уведомление пользователю о добавлении в проект"""
        try:
            # Определяем эмодзи в зависимости от роли
            role_emoji = {
                'куратор': '👤',
                'администратор': '🛡️',
                'админ': '🛡️',
                'участник': '👥',
                'member': '👥',
                'admin': '🛡️'
            }.get(role.lower(), '👥')

            # Правильное отображение роли
            role_display = {
                'куратор': 'Куратор',
                'администратор': 'Администратор',
                'админ': 'Администратор',
                'участник': 'Участник',
                'member': 'Участник',
                'admin': 'Администратор'
            }.get(role.lower(), role.capitalize())

            # Единый текст для всех
            message_text = (
                f"🆕 *НОВЫЙ ПРОЕКТ!*\n\n"
                f"📋 *Название:* {project_name}\n"
                f"{role_emoji} *Ваша роль:* {role_display}\n"
                f"👤 *Куратор:* {manager_name}\n"
                f"📝 *Описание:* {description[:200]}{'...' if len(description) > 200 else ''}\n\n"
                f"Вы были добавлены в проект *«{project_name}»* в роли *{role_display.lower()}*.\n\n"
                f"Вы можете просмотреть проект в приложении TaskPlanner."
            )

            await self.bot.send_message(
                chat_id=user_chat_id,
                text=message_text,
                parse_mode="Markdown"
            )
            logger.info(f"✅ Уведомление о проекте отправлено пользователю {user_chat_id} (роль: {role})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о проекте пользователю {user_chat_id}: {e}")
            return False

    async def start_create_task(self, message, state):
        """Начать создание задачи"""
        user_id = message.from_user.id
        with get_employees_session() as emp_session:
            select_employee = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
            employee = emp_session.execute(select_employee, {'chat_id': user_id}).first()
            if not employee:
                await message.answer("❌ Вы не авторизованы.", reply_markup=get_main_keyboard())
                return
            db_user_id = employee[0]

        projects = await self.task_service.get_user_projects(db_user_id)
        if not projects:
            await message.answer("❌ *У вас нет проектов для создания задач*", parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        buttons = [[InlineKeyboardButton(text=f"📌 {p.name}", callback_data=f"select_project|{p.id}")] for p in projects]
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_creation")])

        await message.answer("📁 *Выберите проект:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await state.set_state(RegistrationStates.waiting_for_task_project)

    async def ask_priority(self, message, state):
        await message.answer("🎯 *Выберите приоритет задачи:*", parse_mode="Markdown", reply_markup=get_priority_keyboard())

    async def ask_tags(self, message, state):
        tags = await self.task_service.get_tags_list()
        if tags:
            buttons = [[InlineKeyboardButton(text=f"🏷️ {tag['name']}", callback_data=f"add_tag|{tag['name']}")] for tag in tags[:15]]
            buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="tags_done")])
            await message.answer("🏷️ *Выберите теги:*\n\nНажимайте на теги. Когда закончите, нажмите 'Готово':", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        else:
            await self.finish_task_creation(message, state, message.from_user.id)

    async def finish_task_creation(self, message_or_callback, state, user_id: int = None):
        """Финальное создание задачи"""
        if user_id is None:
            if hasattr(message_or_callback, 'from_user'):
                user_id = message_or_callback.from_user.id
            else:
                logger.error("Не удалось определить user_id")
                return

        data = await state.get_data()
        project_id = data.get('project_id')
        title = data.get('task_title')
        description = data.get('task_description', '')
        assigned_to = data.get('assigned_to')
        priority = data.get('priority', 'medium')
        difficulty = data.get('difficulty', 0)
        deadline = data.get('deadline')
        status_id = data.get('status_id')
        selected_tags = data.get('selected_tags', [])

        with get_employees_session() as emp_session:
            select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
            employee = emp_session.execute(select_stmt, {'chat_id': user_id}).first()
            if not employee:
                await message_or_callback.answer("❌ Вы не авторизованы.", reply_markup=get_main_keyboard())
                await state.clear()
                return
            db_user_id = employee[0]

        status_name = None
        if status_id:
            with get_tasks_session() as tasks_session:
                status = tasks_session.execute(text("SELECT name FROM public.board_columns WHERE id = :id"), {'id': status_id}).first()
                status_name = status[0] if status else None

        task_data = {
            'project_id': project_id, 'title': title, 'description': description,
            'creator_id': db_user_id, 'assigned_to': assigned_to, 'priority': priority,
            'difficulty': difficulty, 'deadline': deadline.strftime("%Y-%m-%d %H:%M:%S") if deadline else None,
            'status': status_name, 'status_id': status_id, 'tags': selected_tags
        }

        task_id = await self.task_service.create_task_full(task_data)

        target = message_or_callback.message if hasattr(message_or_callback, 'answer') and not hasattr(message_or_callback, 'reply_markup') else message_or_callback

        if task_id:
            result_text = f"✅ *Задача успешно создана!*\n\n📋 *Название:* {title}\n🆔 *ID:* {task_id}\n"
            if assigned_to:
                with get_employees_session() as emp_session:
                    emp = emp_session.execute(text("SELECT last_name, first_name FROM public.employees WHERE id = :id"), {'id': assigned_to}).first()
                    if emp:
                        result_text += f"👤 *Исполнитель:* {emp.last_name} {emp.first_name}\n"
            result_text += f"🎯 *Приоритет:* {priority}\n📊 *Сложность:* {difficulty} ⭐\n"
            if deadline:
                result_text += f"📅 *Дедлайн:* {deadline.strftime('%d.%m.%Y')}\n"
            if selected_tags:
                result_text += f"🏷️ *Теги:* {', '.join(selected_tags)}\n"
            await target.answer(result_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        else:
            await target.answer("❌ Ошибка при создании задачи.", reply_markup=get_main_keyboard())

        await state.clear()

    async def show_my_tasks(self, message, page=0):
        """Показать задачи пользователя"""
        user_id = message.from_user.id
        with get_employees_session() as emp_session:
            employee = emp_session.execute(text("SELECT id FROM public.employees WHERE chat_id = :chat_id"),
                                           {'chat_id': user_id}).first()
            if not employee:
                await message.answer("❌ Вы не авторизованы.", reply_markup=get_main_keyboard())
                return
            db_user_id = employee[0]
            tasks = await self.task_service.get_user_tasks_detailed(db_user_id)

        if not tasks:
            await message.answer("📋 *У вас пока нет задач*", parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        tasks_per_page = 5
        total_pages = (len(tasks) + tasks_per_page - 1) // tasks_per_page
        start_idx = page * tasks_per_page
        end_idx = min(start_idx + tasks_per_page, len(tasks))
        current_tasks = tasks[start_idx:end_idx]

        tasks_text = f"📋 *Ваши задачи* (стр. {page + 1}/{total_pages})\n\n"
        for task in current_tasks:
            tasks_text += f"{task['priority_emoji']} *{task['title']}*\n"
            tasks_text += f"   📁 {task['project_name']}\n"
            if task['deadline_text']:
                tasks_text += f"   {task['deadline_text']}\n"
            tasks_text += f"   📊 Прогресс: {task['progress']}%\n\n"

        # ИСПРАВЛЕННАЯ КЛАВИАТУРА - каждая кнопка в отдельном списке
        keyboard_buttons = []
        if page > 0:
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"tasks_page_{page - 1}")])
        if page < total_pages - 1:
            keyboard_buttons.append([InlineKeyboardButton(text="Вперед ▶️", callback_data=f"tasks_page_{page + 1}")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        await message.answer(tasks_text, parse_mode="Markdown", reply_markup=reply_markup)

    async def start_reminder_scheduler(self):
        async def send_daily_reminders():
            while True:
                now = datetime.now()
                next_run = datetime(now.year, now.month, now.day, 11, 0, 5)
                if now >= next_run:
                    next_run = next_run + timedelta(days=1)
                await asyncio.sleep((next_run - now).total_seconds())
                await self.notification_service.send_deadline_reminders()
        self._reminder_task = asyncio.create_task(send_daily_reminders())
        logger.info("⏰ Планировщик напоминаний запущен")

    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        register_auth_handlers(self.dp, self)
        register_tasks_handlers(self.dp, self)
        register_support_handlers(self.dp, self)
        register_registration_handlers(self.dp, self)
        register_callback_handlers(self.dp, self)
        register_overtime_handlers(self.dp, self)

    async def start(self):
        logger.info("Starting Telegram bot...")
        await self.start_reminder_scheduler()
        await self.dp.start_polling(self.bot)

  
telegram_bot = TelegramBot()

async def start_bot():
    await telegram_bot.start()