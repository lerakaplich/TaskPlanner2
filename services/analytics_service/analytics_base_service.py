# services/analytics_service/analytics_base_service.py

from typing import Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from models.tasks import Task
from models.projects import Project
from models.employees import Employee
from server_app.database import get_employees_session


class AnalyticsBaseService:
    """Базовый сервис для аналитики с общими утилитами"""

    def __init__(self, session: Session):
        self.session = session
        self.employees_session = get_employees_session()

    def __del__(self):
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получить название отдела по ID"""
        if not department_id:
            return "—"
        from models.employees import Department
        dept = self.employees_session.get(Department, department_id)
        return dept.name if dept else "—"

    def _get_division_name(self, division_id: Optional[int]) -> str:
        """Получить название подразделения по ID"""
        if not division_id:
            return "—"
        from models.employees import Division
        div = self.employees_session.get(Division, division_id)
        return div.name if div else "—"

    def _format_employee_name(self, emp: Employee) -> str:
        """Форматирует ФИО сотрудника"""
        parts = [emp.last_name or "", emp.first_name or ""]
        if emp.middle_name:
            parts.append(emp.middle_name)
        return " ".join([p for p in parts if p]) or f"ID:{emp.id}"

    def _task_to_analytics_dto(self, task: Task, status: str, is_completed: bool) -> Dict:
        """Преобразует задачу в DTO для аналитики"""
        from repositories.tag_repo import TagRepo
        tag_repo = TagRepo(self.session)

        task_tags = tag_repo.get_task_tags(task.id)
        tags_list = [tag.name for tag in task_tags]

        creator_name = "Неизвестен"
        if task.created_by:
            creator = self.employees_session.get(Employee, task.created_by)
            if creator:
                creator_name = self._format_employee_name(creator)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
            "status": status,
            "is_overdue": task.deadline and task.deadline.date() < datetime.now().date() and not is_completed,
            "is_completed": is_completed,
            "created_at_str": task.created_at.strftime("%d.%m.%Y") if task.created_at else "",
            "due_date_str": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "completed_at_str": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "",
            "creator_name": creator_name,
            "tags_list": tags_list,
            "project_name": self.session.get(Project, task.project_id).name if task.project_id else ""
        }

    def _project_to_dict(self, project: Project) -> Dict:
        """Преобразует проект в словарь для карточки сотрудника"""
        from sqlalchemy import select
        from models.tasks import Task

        tasks = self.session.scalars(
            select(Task).where(Task.project_id == project.id)
        ).all()

        completed_tasks = 0
        for task in tasks:
            if task.column and task.column.is_done_column:
                completed_tasks += 1

        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
            "tasks_total": len(tasks),
            "tasks_done": completed_tasks,
            "tasks": tasks,
            "is_archived": project.is_archived
        }

    def get_task_card_data(self, task_data: Dict) -> Dict:
        """Подготавливает данные для карточки задачи TaskCard"""
        priority = task_data.get("priority", "medium")
        status = task_data.get("status", "to_do")
        is_overdue = task_data.get("is_overdue", False)

        priority_map = {
            'low': ('Низкий', '#2ecc71'),
            'medium': ('Средний', '#f1c40f'),
            'high': ('Высокий', '#e67e22'),
            'critical': ('Критический', '#e74c3c')
        }
        priority_text, priority_color = priority_map.get(priority, ('Средний', '#f1c40f'))

        status_map = {
            'to_do': 'К выполнению',
            'in_progress': 'В работе',
            'review': 'На проверке',
            'completed': 'Выполнено',
            'archived': 'Архивировано'
        }
        status_text = status_map.get(status, status.capitalize() if status else "Неизвестно")

        tags_list = task_data.get("tags_list", [])

        return {
            "id": task_data.get("id"),
            "title": task_data.get("title", "Без названия"),
            "description": task_data.get("description", ""),
            "priority": priority,
            "priority_text": priority_text,
            "priority_color": priority_color,
            "status": status,
            "status_text": status_text,
            "is_overdue": is_overdue,
            "due_date_str": task_data.get("due_date_str", "Нет"),
            "created_at_str": task_data.get("created_at_str", ""),
            "completed_at_str": task_data.get("completed_at_str", ""),
            "creator_name": task_data.get("creator_name", ""),
            "project_name": task_data.get("project_name", ""),
            "tags_list": tags_list[:3],
            "tags_extra_count": max(0, len(tags_list) - 3)
        }

    def get_task_card_background_color(self, task_data: Dict) -> str:
        """Возвращает цвет фона для карточки задачи"""
        is_overdue = task_data.get("is_overdue", False)
        return "#ffeeee" if is_overdue else "white"

    def get_task_card_border_color(self, task_data: Dict) -> str:
        """Возвращает цвет границы для карточки задачи"""
        priority = task_data.get("priority", "medium")
        priority_colors = {
            'low': '#2ecc71',
            'medium': '#f1c40f',
            'high': '#e67e22',
            'critical': '#e74c3c'
        }
        is_overdue = task_data.get("is_overdue", False)
        if is_overdue:
            return "#e74c3c"
        return priority_colors.get(priority, "#cccccc")