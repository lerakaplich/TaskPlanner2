from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import select
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
        """Возвращает все архивные проекты"""
        from sqlalchemy import select
        from models.projects import Project
        from models.tasks import Task

        stmt = select(Project).where(Project.is_archived == True)
        projects = self.session.scalars(stmt).all()

        print(f"📦 ArchiveService.get_archived_projects: найдено {len(projects)} проектов")

        result = []
        for proj in projects:
            # Получаем количество архивных задач в проекте
            try:
                # Проверяем, есть ли поле is_archived в модели Task
                if hasattr(Task, 'is_archived'):
                    task_stmt = select(Task).where(
                        Task.project_id == proj.id,
                        Task.is_archived == True
                    )
                    tasks_count = len(self.session.scalars(task_stmt).all())
                else:
                    # Если поля нет, просто считаем 0
                    tasks_count = 0
                    print(f"⚠️ Поле is_archived не найдено в модели Task")
            except Exception as e:
                print(f"⚠️ Ошибка при подсчете архивных задач: {e}")
                tasks_count = 0

            result.append({
                "id": proj.id,
                "name": proj.name,
                "description": proj.description or "",
                "archived_at": proj.updated_at.strftime("%d.%m.%Y") if proj.updated_at else "Неизвестно",
                "archived_tasks_count": tasks_count
            })

        return result

    def search_projects(self, text: str) -> List[Dict]:
        """Поиск по архивным проектам"""
        from sqlalchemy import select
        from models.projects import Project

        text = text.lower()
        stmt = select(Project).where(
            Project.is_archived == True,
            Project.name.ilike(f"%{text}%")
        )
        projects = self.session.scalars(stmt).all()

        result = []
        for proj in projects:
            task_stmt = select(Task).where(
                Task.project_id == proj.id,
                Task.is_archived == True
            )
            tasks_count = len(self.session.scalars(task_stmt).all())

            result.append({
                "id": proj.id,
                "name": proj.name,
                "description": proj.description or "",
                "archived_at": proj.updated_at.strftime("%d.%m.%Y") if proj.updated_at else "Неизвестно",
                "archived_tasks_count": tasks_count
            })

        return result

    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Получает архивный проект по ID"""
        from models.projects import Project

        project = self.session.get(Project, project_id)
        if not project or not project.is_archived:
            return None

        task_stmt = select(Task).where(
            Task.project_id == project.id,
            Task.is_archived == True
        )
        tasks_count = len(self.session.scalars(task_stmt).all())

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description or "",
            "archived_at": project.updated_at.strftime("%d.%m.%Y") if project.updated_at else "Неизвестно",
            "archived_tasks_count": tasks_count
        }

    def restore_project(self, project_id: int) -> bool:
        """Восстанавливает проект из архива"""
        from models.projects import Project

        project = self.session.get(Project, project_id)
        if project:
            project.is_archived = False
            project.updated_at = datetime.now()
            self.session.commit()
            print(f"✅ Проект {project_id} восстановлен из архива")
            return True
        return False

    def delete_project_permanently(self, project_id: int) -> bool:
        """Полностью удаляет проект из БД"""
        from models.projects import Project

        project = self.session.get(Project, project_id)
        if project:
            self.session.delete(project)
            self.session.commit()
            print(f"🗑️ Проект {project_id} полностью удален")
            return True
        return False

    def get_project_display_name(self, project_id: int) -> str:
        """Возвращает название проекта для отображения"""
        project = self.session.get(Project, project_id)
        return project.name if project else ""

    # ======================================================
    # Задачи
    # ======================================================

    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Возвращает все архивные задачи проекта"""
        from models.tasks import Task

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True
        )
        tasks = self.session.scalars(stmt).all()

        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "name": task.title,
                "description": task.description or "",
                "archived_at": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "Неизвестно",
                "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
                "status": task.column.name if task.column else "Без статуса"
            })

        return result

    def search_tasks(self, project_id: int, text: str) -> List[Dict]:
        """Поиск по архивным задачам проекта"""
        from models.tasks import Task

        text = text.lower()
        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == True,
            Task.title.ilike(f"%{text}%")
        )
        tasks = self.session.scalars(stmt).all()

        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "name": task.title,
                "description": task.description or "",
                "archived_at": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "Неизвестно",
                "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
                "status": task.column.name if task.column else "Без статуса"
            })

        return result

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        from models.tasks import Task

        task = self.session.get(Task, task_id)
        if task:
            task.is_archived = False
            task.archived_at = None
            self.session.commit()
            print(f"✅ Задача {task_id} восстановлена из архива")
            return True
        return False

    def delete_task_permanently(self, task_id: int) -> bool:
        """Полностью удаляет задачу из БД"""
        from models.tasks import Task

        task = self.session.get(Task, task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            print(f"🗑️ Задача {task_id} полностью удалена")
            return True
        return False

    def get_task_display_name(self, task_id: int) -> str:
        """Возвращает название задачи для отображения"""
        task = self.session.get(Task, task_id)
        return task.title if task else ""