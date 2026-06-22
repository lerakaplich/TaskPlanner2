# services/tasks_service/tasks_filter_service.py

from typing import Dict, List, Optional
from datetime import datetime


class TasksFilterService:
    """Сервис для фильтрации и поиска задач"""

    def __init__(self, db_session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode

    def filter_tasks_by_priority_and_project(
            self,
            tasks: List[Dict],
            priority: str,
            project_id: Optional[int]
    ) -> List[Dict]:
        """Фильтрация по приоритету и проекту"""
        filtered = tasks

        if priority and priority != "Все приоритеты":
            priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high", "Критический": "critical"}
            target_priority = priority_map.get(priority, priority.lower())
            filtered = [t for t in filtered if t.get("priority") == target_priority]

        if project_id:
            filtered = [t for t in filtered if t.get("project_id") == project_id]

        return filtered

    def filter_tasks_by_priority_and_project_ids(
            self,
            tasks: List[Dict],
            priority: str,
            project_id: Optional[int]
    ) -> set:
        """Возвращает множество ID отфильтрованных задач"""
        return self.get_filtered_task_ids(tasks, priority, project_id)

    def get_filtered_task_ids(self, tasks: List[Dict], priority: str, project_id: Optional[int]) -> set:
        """Возвращает множество ID отфильтрованных задач"""
        filtered = self.filter_tasks_by_priority_and_project(tasks, priority, project_id)
        return {t["id"] for t in filtered}

    def filter_tasks_by_priority(self, tasks: List[Dict], priority: str) -> List[Dict]:
        """Фильтрация по приоритету"""
        if priority == "Все приоритеты":
            return tasks
        priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high", "Критический": "critical"}
        target_priority = priority_map.get(priority, priority.lower())
        return [t for t in tasks if t.get("priority") == target_priority]

    def filter_tasks_by_project(self, tasks: List[Dict], project_id: int) -> List[Dict]:
        """Фильтрация по проекту"""
        if not project_id:
            return tasks
        return [t for t in tasks if t.get("project_id") == project_id]

    def filter_tasks_by_status(self, tasks: List[Dict], status: str) -> List[Dict]:
        """Фильтрация по статусу"""
        if not status or status == "Все":
            return tasks
        return [t for t in tasks if t.get("status") == status]

    def filter_tasks_by_assignee(self, tasks: List[Dict], assignee_id: int) -> List[Dict]:
        """Фильтрация по исполнителю"""
        if not assignee_id:
            return tasks
        return [t for t in tasks if t.get("assigned_to") == assignee_id]

    def search_tasks(self, tasks: List[Dict], query: str) -> List[Dict]:
        """Поиск задач по названию"""
        if not query:
            return tasks
        query_lower = query.lower()
        return [t for t in tasks if query_lower in t.get("title", "").lower()]

    def get_tasks_by_column(self, column_name: str) -> List[Dict]:
        """Получить задачи в колонке"""
        all_tasks = self.load_tasks() if hasattr(self, 'load_tasks') else []
        result = [task for task in all_tasks if task.get("status") == column_name]
        result.sort(key=lambda x: x.get("position", 0))
        return result