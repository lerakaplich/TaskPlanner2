# Логика архивации и восстановления проектов/задач.
from typing import List, Dict, Optional


class ArchiveService:
    """
    Сервис архива.
    Хранит бизнес-логику и управление состоянием.
    UI ничего не знает о структуре данных.
    """

    def __init__(self):
        self._archived_projects: List[Dict] = []
        self._archived_tasks: List[Dict] = []

    # ======================================================
    # Загрузка данных
    # ======================================================

    def load_test_data(self):
        self._archived_projects = [
            {
                "id": 1,
                "name": "Разработка новой CRM (завершен)",
                "description": "Проект по разработке CRM системы",
                "archived_at": "2025-12-15",
                "created_at": "2025-01-10"
            },
            {
                "id": 2,
                "name": "Модернизация конвейера",
                "description": "Устаревшая версия проекта",
                "archived_at": "2025-10-20",
                "created_at": "2025-03-15"
            }
        ]

        self._archived_tasks = [
            {
                "id": 101,
                "title": "Написание документации",
                "description": "Старая версия",
                "project_id": 1,
                "priority": "medium"
            },
            {
                "id": 102,
                "title": "Интеграция API",
                "description": "Больше не используется",
                "project_id": 1,
                "priority": "high"
            }
        ]

    # ======================================================
    # Получение данных
    # ======================================================

    def get_archived_projects(self) -> List[Dict]:
        return [
            {
                **project,
                "archived_tasks_count": self._count_tasks(project["id"])
            }
            for project in self._archived_projects
        ]

    def get_project_tasks(self, project_id: int) -> List[Dict]:
        return [
            task for task in self._archived_tasks
            if task["project_id"] == project_id
        ]

    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        return next(
            (p for p in self._archived_projects if p["id"] == project_id),
            None
        )

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        return next(
            (t for t in self._archived_tasks if t["id"] == task_id),
            None
        )

    def _count_tasks(self, project_id: int) -> int:
        return len([
            t for t in self._archived_tasks
            if t["project_id"] == project_id
        ])

    # ======================================================
    # Поиск
    # ======================================================

    def search_projects(self, text: str) -> List[Dict]:
        text = text.lower()

        return [
            {
                **project,
                "archived_tasks_count": self._count_tasks(project["id"])
            }
            for project in self._archived_projects
            if text in project["name"].lower()
            or text in project.get("description", "").lower()
        ]

    def search_tasks(self, project_id: int, text: str) -> List[Dict]:
        text = text.lower()

        return [
            task for task in self._archived_tasks
            if task["project_id"] == project_id
            and (
                text in task["title"].lower()
                or text in task.get("description", "").lower()
            )
        ]

    # ======================================================
    # Восстановление
    # ======================================================

    def restore_project(self, project_id: int) -> bool:
        if not self.get_project_by_id(project_id):
            return False

        self._archived_projects = [
            p for p in self._archived_projects
            if p["id"] != project_id
        ]

        self._archived_tasks = [
            t for t in self._archived_tasks
            if t["project_id"] != project_id
        ]

        return True

    def restore_task(self, task_id: int) -> bool:
        if not self.get_task_by_id(task_id):
            return False

        self._archived_tasks = [
            t for t in self._archived_tasks
            if t["id"] != task_id
        ]

        return True

    # ======================================================
    # Полное удаление
    # ======================================================

    def delete_project_permanently(self, project_id: int) -> bool:
        return self.restore_project(project_id)

    def delete_task_permanently(self, task_id: int) -> bool:
        return self.restore_task(task_id)

    def get_project_display_name(self, project_id: int) -> str:
        project = self.get_project_by_id(project_id)
        return project["name"] if project else ""

    def get_task_display_name(self, task_id: int) -> str:
        task = self.get_task_by_id(task_id)
        return task["title"] if task else ""