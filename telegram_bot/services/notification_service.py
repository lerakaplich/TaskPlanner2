import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import text
from database import get_tasks_session, get_employees_session
from models.employees import Employee

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений"""

    def __init__(self, bot):
        self.bot = bot

    async def send_deadline_reminders(self):
        """Отправляет напоминания о задачах с приближающимися дедлайнами"""
        logger.info("📅 Отправка ежедневных напоминаний о задачах")

        with get_tasks_session() as tasks_session:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            day_after = today + timedelta(days=2)

            stmt = text("""
                SELECT t.id, t.title, t.deadline, t.project_id, p.name as project_name,
                       t.assigned_to, e.chat_id, e.last_name, e.first_name
                FROM public.tasks t
                JOIN public.projects p ON t.project_id = p.id
                JOIN public.employees e ON t.assigned_to = e.id
                WHERE t.deadline IS NOT NULL
                  AND t.is_archived = false
                  AND (t.progress_percent < 100 OR t.progress_percent IS NULL)
                  AND DATE(t.deadline) IN (:today, :tomorrow, :day_after)
                  AND e.chat_id IS NOT NULL
            """)
            tasks = tasks_session.execute(stmt, {
                'today': today, 'tomorrow': tomorrow, 'day_after': day_after
            }).fetchall()

            for task in tasks:
                deadline_date = task.deadline.date() if task.deadline else None
                days_left = (deadline_date - today).days if deadline_date else None

                if days_left == 0:
                    message = f"⚠️ *СРОЧНО!* ⚠️\n\nЗадача *{task.title}* должна быть выполнена *СЕГОДНЯ*!\n📁 Проект: {task.project_name}"
                elif days_left == 1:
                    message = f"📅 *Напоминание о задаче*\n\nЗадача *{task.title}* должна быть выполнена *ЗАВТРА*!\n📁 Проект: {task.project_name}"
                else:
                    message = f"📅 *Напоминание о задаче*\n\nЗадача *{task.title}* должна быть выполнена *ПОСЛЕЗАВТРА*!\n📁 Проект: {task.project_name}"

                try:
                    await self.bot.send_message(chat_id=task.chat_id, text=message, parse_mode="Markdown")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки напоминания: {e}")

    async def send_task_notification(self, task_id: int, assignee_id: int, task_title: str, project_name: str):
        """Отправляет уведомление о новой задаче исполнителю"""
        with get_employees_session() as emp_session:
            employee = emp_session.query(Employee).filter(Employee.id == assignee_id).first()
            if employee and employee.chat_id:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                message = (
                    f"🆕 *НОВАЯ ЗАДАЧА!*\n\n"
                    f"📋 *Название:* {task_title}\n"
                    f"📁 *Проект:* {project_name}\n\n"
                    f"Вам назначена новая задача."
                )
                reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Посмотреть задачи", callback_data="show_my_tasks")]
                ])
                try:
                    await self.bot.send_message(chat_id=employee.chat_id, text=message, parse_mode="Markdown", reply_markup=reply_markup)
                    logger.info(f"✅ Уведомление о задаче {task_id} отправлено")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки уведомления: {e}")