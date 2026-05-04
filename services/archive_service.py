# services/archive_service.py

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import select, func
from models.projects import Project
from models.tasks import Task


class ArchiveService:
    """Бизнес-логика архива проектов и задач"""

    def __init__(self, session):
        self.session = session

    # ======================================================
    # Проекты
    # ======================================================

    def get_archived_projects(self) -> List[Dict]:
        """Возвращает все архивные проекты (подготовленные данные)"""
        stmt = select(Project).where(Project.is_archived == True)
        projects = self.session.scalars(stmt).all()

        return [self._prepare_project_data(proj) for proj in projects]

    def search_projects(self, text: str) -> List[Dict]:
        """Поиск по архивным проектам"""
        if not text:
            return self.get_archived_projects()

        stmt = select(Project).where(
            Project.is_archived == True,
            Project.name.ilike(f"%{text}%")
        )
        projects = self.session.scalars(stmt).all()

        return [self._prepare_project_data(proj) for proj in projects]

    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Получает архивный проект по ID (подготовленные данные)"""
        project = self.session.get(Project, project_id)
        if not project or not project.is_archived:
            return None
        return self._prepare_project_data(project)

    def _prepare_project_data(self, project: Project) -> Dict:
        """Подготавливает данные проекта для UI"""
        tasks_count = self._get_archived_tasks_count(project.id)

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description or "",
            "archived_at": project.updated_at.strftime("%d.%m.%Y") if project.updated_at else "Неизвестно",
            "archived_tasks_count": tasks_count
        }

    def _get_archived_tasks_count(self, project_id: int) -> int:
        """Возвращает количество архивных задач в проекте"""
        try:
            if hasattr(Task, 'is_archived'):
                stmt = select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.is_archived == True
                )
                return self.session.scalar(stmt) or 0
        except Exception as e:
            print(f"⚠️ Ошибка при подсчете архивных задач: {e}")
        return 0

    def restore_project(self, project_id: int) -> bool:
        """Восстанавливает проект из архива"""
        project = self.session.get(Project, project_id)
        if project:
            project.is_archived = False
            project.updated_at = datetime.now()
            self.session.commit()
            return True
        return False

    def delete_project_permanently(self, project_id: int) -> bool:
        """Полностью удаляет проект из БД"""
        project = self.session.get(Project, project_id)
        if project:
            self.session.delete(project)
            self.session.commit()
            return True
        return False

    def get_project_name(self, project_id: int) -> str:
        """Возвращает название проекта"""
        project = self.session.get(Project, project_id)
        return project.name if project else ""

    # ======================================================
    # Задачи
    # ======================================================

    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Возвращает все архивные задачи проекта (подготовленные данные)"""
        if not hasattr(Task, 'is_archived'):
            return []

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True
        )
        tasks = self.session.scalars(stmt).all()

        return [self._prepare_task_data(task) for task in tasks]

    def search_tasks(self, project_id: int, text: str) -> List[Dict]:
        """Поиск по архивным задачам проекта"""
        if not text:
            return self.get_project_tasks(project_id)

        if not hasattr(Task, 'is_archived'):
            return []

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True,
            Task.title.ilike(f"%{text}%")
        )
        tasks = self.session.scalars(stmt).all()

        return [self._prepare_task_data(task) for task in tasks]

    def _prepare_task_data(self, task: Task) -> Dict:
        """Подготавливает данные задачи для UI"""
        priority = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "archived_at": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "Неизвестно",
            "priority": priority,
            "status": task.column.name if task.column and task.column.name else "Без статуса"
        }

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        task = self.session.get(Task, task_id)
        if task:
            task.is_archived = False
            task.archived_at = None
            self.session.commit()
            return True
        return False

    def delete_task_permanently(self, task_id: int) -> bool:
        """Полностью удаляет задачу из БД"""
        task = self.session.get(Task, task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False

    def get_task_title(self, task_id: int) -> str:
        """Возвращает название задачи"""
        task = self.session.get(Task, task_id)
        return task.title if task else ""

    def has_archived_tasks(self, project_id: int) -> bool:
        """Проверяет, есть ли архивные задачи в проекте"""
        return self._get_archived_tasks_count(project_id) > 0