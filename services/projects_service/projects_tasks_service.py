# services/projects_service/projects_tasks_service.py

from typing import List, Dict
from datetime import datetime
from models.schemas.tasks_dto import TaskPriority
from repositories.task_repo import TaskRepo
from repositories.employee_repo import EmployeeRepo
from database import get_employees_session


class ProjectsTasksService:
    """Работа с задачами проекта"""

    def __init__(self, session, employees_session, employee_repo):
        self.session = session
        self.employees_session = employees_session
        self.employee_repo = employee_repo

    # services/projects_service/projects_tasks_service.py

    def get_project_tasks_for_view(self, project_id: int, include_archived: bool = False, get_project_name_func=None) -> \
    List[Dict]:
        """Возвращает задачи проекта в виде словарей с полной информацией для отображения"""
        task_repo = TaskRepo(self.session)
        tasks = task_repo.get_by_project(project_id, load_column=True, include_archived=include_archived)

        # Загружаем теги для всех задач одним запросом (для производительности)
        task_ids = [task.id for task in tasks]
        tags_by_task = self._load_tags_for_tasks(task_ids)

        result = []
        for task in tasks:
            # Получаем имя исполнителя
            assignee_name = None
            if task.assigned_to:
                emp_session = get_employees_session()
                if emp_session:
                    emp_repo = EmployeeRepo(emp_session)
                    assignee_name = emp_repo.get_full_name(task.assigned_to)
                    emp_session.close()

            # Получаем имя автора
            author_name = None
            if task.created_by:
                emp_session = get_employees_session()
                if emp_session:
                    emp_repo = EmployeeRepo(emp_session)
                    author_name = emp_repo.get_full_name(task.created_by)
                    emp_session.close()

            priority_map = {
                TaskPriority.low: ("Низкий", "#4CAF50"),
                TaskPriority.medium: ("Средний", "#FFA726"),
                TaskPriority.high: ("Высокий", "#D22730"),
                TaskPriority.critical: ("Критический", "#D22730")
            }

            priority_text, priority_color = priority_map.get(
                task.priority,
                ("Средний", "#FFA726")
            )

            deadline_text = ""
            deadline_color = "#666"
            deadline_obj = None
            if task.deadline:
                deadline_text = task.deadline.strftime("%d.%m.%Y")
                deadline_obj = task.deadline
                if task.deadline.date() < datetime.now().date():
                    deadline_color = "#D22730"

            created_text = task.created_at.strftime("%d.%m.%Y") if task.created_at else ""
            updated_text = task.updated_at.strftime("%d.%m.%Y") if task.updated_at else ""

            # ===== ИСПРАВЛЕНИЕ: загружаем теги из предварительно загруженного словаря =====
            tags = tags_by_task.get(task.id, [])

            # Если теги не загрузились через массовый запрос, пробуем через hasattr
            if not tags and hasattr(task, 'tags') and task.tags:
                for tag_obj in task.tags:
                    if hasattr(tag_obj, 'tag') and tag_obj.tag:
                        tags.append(tag_obj.tag.name)
                    elif hasattr(tag_obj, 'name'):
                        tags.append(tag_obj.name)
                    elif isinstance(tag_obj, str):
                        tags.append(tag_obj)
                    else:
                        tags.append(str(tag_obj))

            archived_at = ""
            if task.is_archived and task.archived_at:
                archived_at = task.archived_at.strftime("%d.%m.%Y")

            result.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "status": task.column.name if task.column else None,
                "column_id": task.column_id,
                "priority": task.priority.value,
                "priority_text": priority_text,
                "priority_color": priority_color,
                "deadline": deadline_text,
                "deadline_obj": deadline_obj,
                "deadline_color": deadline_color,
                "assignee_name": assignee_name or "Не назначен",
                "assigned_to": task.assigned_to,
                "created_by": task.created_by,
                "author_text": author_name or "Неизвестен",
                "created_text": created_text,
                "updated_text": updated_text,
                "executor_text": assignee_name or "Не назначен",
                "completed": task.is_archived if hasattr(task, 'is_archived') else False,
                "difficulty": task.difficulty if hasattr(task, 'difficulty') else 0,
                "tags": tags,  # <-- ИСПРАВЛЕНО
                "project_id": task.project_id,
                "project_name": get_project_name_func(project_id) if get_project_name_func else f"Проект #{project_id}",
                "is_archived": task.is_archived if hasattr(task, 'is_archived') else False,
                "archived_at": archived_at,
                # Добавляем поля для совместимости с карточками
                "priority_color": priority_color,
                "progress_percent": task.progress_percent if hasattr(task, 'progress_percent') else 0,
                "is_paused": task.is_paused if hasattr(task, 'is_paused') else False,
                "total_paused_seconds": task.total_paused_seconds if hasattr(task, 'total_paused_seconds') else 0,
            })

        return result

    def _load_tags_for_tasks(self, task_ids: List[int]) -> Dict[int, List[str]]:
        """Загружает теги для списка задач одним запросом"""
        if not task_ids:
            return {}

        from models.tasks import TaskTag, Tag
        from sqlalchemy import select

        stmt = (
            select(TaskTag.task_id, Tag.name)
            .join(Tag, TaskTag.tag_id == Tag.id)
            .where(TaskTag.task_id.in_(task_ids))
        )

        result = self.session.execute(stmt).all()

        tags_by_task = {}
        for task_id, tag_name in result:
            if task_id not in tags_by_task:
                tags_by_task[task_id] = []
            tags_by_task[task_id].append(tag_name)

        return tags_by_task

    def get_project_name(self, project_id: int, project_repo) -> str:
        """Возвращает название проекта по ID"""
        project = project_repo.get_by_id(project_id)
        return project.name if project else f"Проект #{project_id}"

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        task_repo = TaskRepo(self.session)
        task = task_repo.get_by_id(task_id)
        if task:
            task.is_archived = False
            task.archived_at = None
            self.session.commit()
            return True
        return False

    def delete_task_permanently(self, task_id: int) -> bool:
        """Полное удаление задачи"""
        task_repo = TaskRepo(self.session)
        result = task_repo.hard_delete(task_id)
        self.session.commit()
        return result