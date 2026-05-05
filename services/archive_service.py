# services/archive_service.py

from datetime import datetime
from typing import List, Dict, Optional
from PyQt6.QtWidgets import QMessageBox
from sqlalchemy import select, func, update
from models.projects import Project
from models.tasks import Task
from models.employees import Employee
from database import get_employees_session


class ArchiveService:
    """Бизнес-логика архива проектов и задач"""

    def __init__(self, session):
        self.session = session

    # ======================================================
    # Обновление данных карточек
    # ======================================================

    def update_project_card_data(self, project_id: int) -> Optional[Dict]:
        """Обновляет данные проекта для карточки"""
        project = self.session.get(Project, project_id)
        if not project or not project.is_archived:
            return None
        return self._prepare_project_data(project)

    def update_task_card_data(self, task_id: int) -> Optional[Dict]:
        """Обновляет данные задачи для карточки"""
        task = self.session.get(Task, task_id)
        if not task or not task.is_archived:
            return None
        return self._prepare_task_data(task)

    def get_project_tasks_count(self, project_id: int) -> int:
        """Возвращает количество архивных задач в проекте"""
        return self._get_archived_tasks_count(project_id)

    # ======================================================
    # Пакетные операции
    # ======================================================

    def restore_all_tasks(self, project_id: int) -> int:
        """Восстанавливает все задачи проекта, возвращает количество восстановленных"""
        stmt = update(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True
        ).values(is_archived=False, archived_at=None)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def get_archived_projects_count(self) -> int:
        """Возвращает количество архивированных проектов"""
        stmt = select(func.count(Project.id)).where(Project.is_archived == True)
        return self.session.scalar(stmt) or 0

    def get_archived_tasks_count(self) -> int:
        """Возвращает общее количество архивированных задач"""
        stmt = select(func.count(Task.id)).where(Task.is_archived == True)
        return self.session.scalar(stmt) or 0

    # ======================================================
    # Валидация
    # ======================================================

    def can_restore_project(self, project_id: int) -> bool:
        """Проверяет, можно ли восстановить проект"""
        project = self.session.get(Project, project_id)
        return project is not None and project.is_archived

    def can_restore_task(self, task_id: int) -> bool:
        """Проверяет, можно ли восстановить задачу"""
        task = self.session.get(Task, task_id)
        return task is not None and task.is_archived

    def can_delete_project(self, project_id: int) -> bool:
        """Проверяет, можно ли удалить проект"""
        project = self.session.get(Project, project_id)
        return project is not None

    def can_delete_task(self, task_id: int) -> bool:
        """Проверяет, можно ли удалить задачу"""
        task = self.session.get(Task, task_id)
        return task is not None

    # ======================================================
    # Проекты
    # ======================================================

    def get_archived_projects(self) -> List[Dict]:
        """Возвращает все архивные проекты (подготовленные данные)"""
        stmt = select(Project).where(Project.is_archived == True).order_by(Project.updated_at.desc())
        projects = self.session.scalars(stmt).all()
        return [self._prepare_project_data(proj) for proj in projects]

    def search_projects(self, text: str) -> List[Dict]:
        """Поиск по архивным проектам"""
        if not text:
            return self.get_archived_projects()

        stmt = select(Project).where(
            Project.is_archived == True,
            Project.name.ilike(f"%{text}%")
        ).order_by(Project.updated_at.desc())
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
        if not project:
            return False

        project.is_archived = False
        project.updated_at = datetime.now()

        # Восстанавливаем все задачи проекта
        stmt = update(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True
        ).values(is_archived=False, archived_at=None)
        self.session.execute(stmt)

        self.session.commit()
        return True

    def delete_project_permanently(self, project_id: int) -> bool:
        """Полностью удаляет проект из БД (каскадно удаляет задачи)"""
        project = self.session.get(Project, project_id)
        if not project:
            return False

        self.session.delete(project)
        self.session.commit()
        return True

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
            print("⚠️ У задачи нет поля is_archived")
            return []

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True
        ).order_by(Task.archived_at.desc())
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
        ).order_by(Task.archived_at.desc())
        tasks = self.session.scalars(stmt).all()
        return [self._prepare_task_data(task) for task in tasks]

    def _prepare_task_data(self, task: Task) -> Dict:
        """Подготавливает данные задачи для UI"""
        priority = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
        priority_map = {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "critical": "Критический"
        }
        priority_text = priority_map.get(priority, "Средний")

        # Получаем имя исполнителя
        assignee_name = None
        if task.assigned_to:
            emp_session = get_employees_session()
            if emp_session:
                from repositories.employee_repo import EmployeeRepo
                emp_repo = EmployeeRepo(emp_session)
                assignee_name = emp_repo.get_full_name(task.assigned_to)
                emp_session.close()

        # Получаем название проекта
        project_name = ""
        if task.project_id:
            project = self.session.get(Project, task.project_id)
            if project:
                project_name = project.name

        # Получаем теги
        tags = []
        if hasattr(task, 'tags') and task.tags:
            for tag in task.tags:
                if hasattr(tag, 'name'):
                    tags.append(tag.name)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "archived_at": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "Неизвестно",
            "priority": priority_text,
            "priority_key": priority,
            "status": task.column.name if task.column and task.column.name else "Без статуса",
            "assignee_name": assignee_name or "Не назначен",
            "project_name": project_name,
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "tags": tags
        }

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        task = self.session.get(Task, task_id)
        if not task:
            return False

        task.is_archived = False
        task.archived_at = None
        self.session.commit()
        return True

    def delete_task_permanently(self, task_id: int) -> bool:
        """Полностью удаляет задачу из БД"""
        task = self.session.get(Task, task_id)
        if not task:
            return False

        self.session.delete(task)
        self.session.commit()
        return True

    def get_task_title(self, task_id: int) -> str:
        """Возвращает название задачи"""
        task = self.session.get(Task, task_id)
        return task.title if task else ""

    def has_archived_tasks(self, project_id: int) -> bool:
        """Проверяет, есть ли архивные задачи в проекте"""
        return self._get_archived_tasks_count(project_id) > 0

    # ======================================================
    # UI Helpers (для диалогов)
    # ======================================================

    def get_restore_project_confirmation(self, project_name: str) -> bool:
        """Показывает диалог подтверждения восстановления проекта"""
        # Этот метод должен вызываться из UI, но логика перенесена в сервис
        pass

    def get_delete_project_confirmation(self, project_name: str) -> bool:
        """Показывает диалог подтверждения удаления проекта"""
        pass

    def get_restore_task_confirmation(self, task_title: str) -> bool:
        """Показывает диалог подтверждения восстановления задачи"""
        pass

    def get_delete_task_confirmation(self, task_title: str) -> bool:
        """Показывает диалог подтверждения удаления задачи"""
        pass