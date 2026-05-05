# services/tasks_service/tasks_statistics_service.py

from typing import Dict, List
from datetime import datetime
from sqlalchemy import select

from models.projects import EmployeeProject, Project
from models.tasks import Task


class TasksStatisticsService:
    """Сервис для статистики задач"""

    def __init__(self, db_session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode
        self._task_to_dict = None

    def set_task_converter(self, converter_func):
        """Установка функции конвертации задачи в словарь"""
        self._task_to_dict = converter_func

    def get_statistics(self) -> Dict[str, int]:
        """Получить статистику задач"""
        tasks = self.load_tasks() if hasattr(self, 'load_tasks') else []
        total = len(tasks)
        done = len([t for t in tasks if t.get("completed")])

        overdue = 0
        for t in tasks:
            deadline = t.get("deadline")
            if deadline and not t.get("completed"):
                try:
                    deadline_date = datetime.strptime(deadline, "%d.%m.%Y")
                    if deadline_date.date() < datetime.now().date():
                        overdue += 1
                except:
                    pass

        return {"total": total, "done": done, "overdue": overdue, "in_progress": total - done}

    def get_statistics_for_display(self) -> Dict:
        """Получить статистику для отображения"""
        stats = self.get_statistics()
        return {
            "total": stats["total"],
            "done": stats["done"],
            "overdue": stats["overdue"],
            "in_progress": stats["in_progress"],
            "column_counts": {}
        }

    def get_progress_percent(self) -> int:
        """Получить процент выполнения"""
        stats = self.get_statistics()
        if stats["total"] == 0:
            return 0
        return int((stats["done"] / stats["total"] * 100))

    def get_tasks_statistics(self, tasks: List[Dict]) -> Dict[str, int]:
        """Получить статистику по списку задач"""
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("completed"))
        overdue = sum(1 for t in tasks if t.get("deadline") and not t.get("completed"))

        high_priority = sum(1 for t in tasks if t.get("priority") in ["high", "critical"])
        medium_priority = sum(1 for t in tasks if t.get("priority") == "medium")
        low_priority = sum(1 for t in tasks if t.get("priority") == "low")

        return {
            "total": total,
            "completed": completed,
            "overdue": overdue,
            "in_progress": total - completed,
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "completion_percent": int((completed / total * 100)) if total > 0 else 0
        }

    def get_user_projects_with_stats(self, user_id: int) -> List[Dict]:
        """Получить проекты пользователя со статистикой"""
        memberships = self.db_session.scalars(
            select(EmployeeProject).where(EmployeeProject.employee_id == user_id)
        ).all()

        result = []
        for membership in memberships:
            project = self.db_session.get(Project, membership.project_id)
            if project and not project.is_archived:
                tasks = self.repo.get_by_project(project.id)
                stats = self.get_tasks_statistics([
                    self._task_to_dict(t) for t in tasks
                ]) if self._task_to_dict else {}
                result.append({
                    "id": project.id,
                    "name": project.name,
                    "description": project.description or "",
                    "is_admin": membership.is_admin,
                    "stats": stats
                })
        return result