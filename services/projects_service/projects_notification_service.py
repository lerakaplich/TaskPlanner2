# services/projects_service/projects_notification_service.py

import asyncio
from typing import List, Optional, Dict
from sqlalchemy import text
from telegram_bot import telegram_bot


class ProjectsNotificationService:
    """Уведомления по проектам"""

    def __init__(self, employee_repo):
        self.employee_repo = employee_repo
        self.current_user_id = None

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id

    def ensure_local_employee(self, session, external_employee_id: int) -> Optional[int]:
        """Проверяет наличие записи сотрудника в БД taskplanner.public.employees_data"""
        try:
            check_data_stmt = text("""
                SELECT employee_id FROM public.employees_data WHERE employee_id = :emp_id
            """)
            data_exists = session.execute(check_data_stmt, {'emp_id': external_employee_id}).first()

            if not data_exists:
                insert_data_stmt = text("""
                    INSERT INTO public.employees_data (employee_id, is_active, role)
                    VALUES (:emp_id, :is_active, :role)
                """)
                session.execute(insert_data_stmt, {
                    'emp_id': external_employee_id,
                    'is_active': True,
                    'role': 'user'
                })
                session.flush()

            return external_employee_id
        except Exception as e:
            print(f"⚠️ Ошибка при создании локальной записи сотрудника: {e}")
            return None

    def get_employee_chat_id(self, employee_id: int) -> Optional[int]:
        """Получает chat_id сотрудника из БД employees"""
        try:
            employee = self.employee_repo.get_by_id(employee_id)
            if employee:
                return employee.chat_id
        except Exception as e:
            print(f"⚠️ Ошибка получения chat_id для сотрудника {employee_id}: {e}")
        return None

    def _get_employee_full_name(self, employee) -> str:
        """Возвращает ФИО сотрудника"""
        if not employee:
            return "Неизвестный"
        parts = []
        if hasattr(employee, 'last_name') and employee.last_name:
            parts.append(employee.last_name)
        if hasattr(employee, 'first_name') and employee.first_name:
            parts.append(employee.first_name)
        if hasattr(employee, 'middle_name') and employee.middle_name:
            parts.append(employee.middle_name)
        return " ".join(parts) if parts else f"User {employee.id if hasattr(employee, 'id') else '?'}"

    def _send_telegram_notification(self, chat_id: int, message: str):
        """Отправляет уведомление через Telegram бота"""
        if not chat_id:
            return
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                telegram_bot.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            )
            loop.close()
            print(f"✅ Уведомление отправлено в Telegram (chat_id={chat_id})")
        except Exception as e:
            print(f"⚠️ Ошибка отправки Telegram уведомления: {e}")

    def send_project_notification(self, project_name: str, project_description: str,
                                   creator_name: str, participants: List[dict],
                                   is_new: bool = True, project_id: int = None):
        """Отправляет уведомление всем участникам проекта"""
        if is_new:
            title = "🆕 **НОВЫЙ ПРОЕКТ**"
            action = "добавлены в проект"
            footer = "Вы можете просмотреть проект в приложении TaskPlanner."
        else:
            title = "✏️ **ПРОЕКТ ОБНОВЛЕН**"
            action = "проект обновлен"
            footer = "Обновленную информацию можно посмотреть в приложении TaskPlanner."

        message = f"""{title}

📋 **Название:** {project_name}
👤 **Создатель проекта:** {creator_name}
📝 **Описание:** {project_description[:200]}{'...' if len(project_description) > 200 else ''}

Вы были {action} «{project_name}».

{footer}"""

        for participant in participants:
            emp_id = participant.get('id') if isinstance(participant, dict) else participant

            if self.current_user_id and emp_id == self.current_user_id:
                continue

            chat_id = self.get_employee_chat_id(emp_id)
            if chat_id:
                self._send_telegram_notification(chat_id, message)
                print(f"📨 Уведомление отправлено участнику ID={emp_id}")

    def get_user_chats(self, user_id: int) -> List:
        """Получает чаты пользователя"""
        from services.chat_service import ChatService
        from database import get_tasks_session

        chat_session = get_tasks_session()
        if chat_session is None:
            print("⚠️ Нет подключения к БД чатов")
            return []

        try:
            chat_service = ChatService(chat_session)
            return chat_service.get_user_chats(user_id)
        finally:
            chat_session.close()