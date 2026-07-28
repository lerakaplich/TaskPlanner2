# services/gantt_service/gantt_data_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from models.tasks import Task
from models.projects import Project
from models.schemas.projects_dto import ProjectDTO
from services.permissions.app_permissions import AppRole
from .gantt_base_service import GanttBaseService, TaskGanttData


class GanttDataService(GanttBaseService):
    """Сервис для загрузки и кэширования данных"""

    def __init__(self, session: Session, current_user_id: int = None, project_service=None, permission_service=None):
        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service
        self.permission_service = permission_service
        self._cached_tasks: List[TaskGanttData] = []
        self._cached_projects: List[ProjectDTO] = []
        self._available_project_ids: Optional[set] = None

    def get_manageable_projects(self) -> List[Dict[str, Any]]:
        """
        Возвращает список проектов, где пользователь может управлять задачами
        (администратор или куратор проекта)
        """
        from models.permissions import ProjectRole

        if not self.permission_service or not self.current_user_id:
            return []

        try:
            from models.projects import Project, EmployeeProject
            from sqlalchemy import select, or_

            # Получаем все проекты, где пользователь является участником
            stmt = select(Project).where(
                Project.is_archived == False,
                or_(
                    Project.created_by == self.current_user_id,
                    Project.id.in_(
                        select(EmployeeProject.project_id).where(
                            EmployeeProject.employee_id == self.current_user_id
                        )
                    )
                )
            )
            projects = self.session.scalars(stmt).all()

            manageable_projects = []
            for project in projects:
                # Проверяем роль пользователя в проекте
                project_role = self.permission_service.get_user_project_role(project.id)

                # Только администратор (PROJECT_MANAGER) или куратор (CURATOR)
                if project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
                    manageable_projects.append({
                        "id": project.id,
                        "name": project.name,
                        "description": project.description or ""
                    })
                # Если пользователь создатель проекта - он тоже может управлять
                elif project.created_by == self.current_user_id:
                    manageable_projects.append({
                        "id": project.id,
                        "name": project.name,
                        "description": project.description or ""
                    })

            return manageable_projects

        except Exception as e:
            print(f"⚠️ Ошибка получения проектов для управления: {e}")
            return []

    def load_data(self, project_id: Optional[int] = None) -> None:
        """Загружает данные из БД"""
        print(f"📊 GanttDataService.load_data(project_id={project_id})")
        self._determine_available_projects()
        self._load_projects()
        self._load_tasks(project_id)

    def clear_cache(self) -> None:
        """Очищает кэш"""
        self._cached_tasks = []
        self._cached_projects = []
        self._available_project_ids = None

    def refresh_all_data(self, project_id: Optional[int] = None) -> None:
        """Полностью перезагружает данные"""
        self.clear_cache()
        self.load_data(project_id)

    def _determine_available_projects(self) -> None:
        """Определяет доступные проекты для пользователя"""
        if not self.permission_service:
            self._available_project_ids = None
            return

        app_role = self.permission_service.app_manager.role

        if app_role == AppRole.USER:
            self._available_project_ids = self._get_user_project_ids()
            print(f"   👤 Пользователь (USER): доступно {len(self._available_project_ids)} проектов")
        else:
            self._available_project_ids = None
            print(f"   👑 Администратор: видны все проекты")

    def _get_user_project_ids(self) -> set:
        """Возвращает ID проектов, в которых участвует пользователь"""
        from models.projects import EmployeeProject

        if not self.current_user_id:
            return set()

        try:
            stmt = select(EmployeeProject.project_id).where(
                EmployeeProject.employee_id == self.current_user_id
            )
            result = self.session.execute(stmt).all()
            project_ids = {row[0] for row in result}

            # Проекты, где пользователь создатель
            stmt_owner = select(Project.id).where(Project.owner == self.current_user_id)
            for row in self.session.execute(stmt_owner).all():
                project_ids.add(row[0])

            # Проекты, где пользователь куратор
            stmt_manager = select(Project.id).where(Project.manager_id == self.current_user_id)
            for row in self.session.execute(stmt_manager).all():
                project_ids.add(row[0])

            return project_ids
        except Exception as e:
            print(f"   ⚠️ Ошибка получения проектов: {e}")
            return set()

    def _load_projects(self) -> None:
        """Загружает проекты"""
        try:
            stmt = select(Project).where(Project.is_archived == False).order_by(Project.name)

            if self._available_project_ids is not None and len(self._available_project_ids) > 0:
                stmt = stmt.where(Project.id.in_(self._available_project_ids))

            projects = self.session.scalars(stmt).all()
            self._cached_projects = [ProjectDTO.model_validate(p) for p in projects]
            print(f"   ✅ Загружено {len(self._cached_projects)} проектов")
        except Exception as e:
            print(f"   ❌ Ошибка загрузки проектов: {e}")
            self._cached_projects = []

    def _load_tasks(self, project_id: Optional[int] = None) -> None:
        """Загружает задачи"""
        try:
            stmt = select(Task).where(
                Task.is_archived == False
            ).options(
                joinedload(Task.column),
                joinedload(Task.dependencies_as_predecessor),
                joinedload(Task.dependencies_as_successor)
            )

            if project_id:
                stmt = stmt.where(Task.project_id == project_id)
            elif self._available_project_ids is not None and len(self._available_project_ids) > 0:
                stmt = stmt.where(Task.project_id.in_(self._available_project_ids))

            tasks = self.session.scalars(stmt).unique().all()
            print(f"   ✅ Загружено {len(tasks)} задач")

            self._cached_tasks = []
            for task in tasks:
                gantt_task = self._convert_to_gantt_data(task)
                if gantt_task:
                    self._cached_tasks.append(gantt_task)

        except Exception as e:
            print(f"   ❌ Ошибка загрузки задач: {e}")
            self._cached_tasks = []

    def _convert_to_gantt_data(self, task: Task) -> Optional[TaskGanttData]:
        """Конвертирует Task в TaskGanttData"""
        try:
            start_date = task.created_at if task.created_at else datetime.now()
            end_date = task.deadline if task.deadline else start_date + timedelta(days=7)

            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

            if start_date > end_date:
                start_date, end_date = end_date, start_date + timedelta(days=1)

            executor_name = ""
            executor_initials = ""
            if task.assigned_to and self.project_service:
                user = self.project_service.get_user_by_id(task.assigned_to)
                if user:
                    executor_name = f"{user.get('last_name', '')} {user.get('first_name', '')}".strip()
                    executor_initials = self.get_initials(user)

            priority_value = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            color = self.get_priority_color(priority_value)

            dependencies = []
            for dep in task.dependencies_as_predecessor:
                dependencies.append({
                    "successor_id": dep.successor_id,
                    "lag": dep.lag,
                    "type": dep.type
                })

            project_name = ""
            for p in self._cached_projects:
                if p.id == task.project_id:
                    project_name = p.name
                    break

            return TaskGanttData(
                id=task.id,
                name=task.title,
                start_date=start_date,
                end_date=end_date,
                executor_name=executor_name,
                executor_initials=executor_initials,
                executor_id=task.assigned_to,
                color=color,
                priority=priority_value,
                progress=task.progress_percent,
                dependencies=dependencies,
                project_id=task.project_id,
                project_name=project_name,
                status=task.column.name if task.column else "unknown"
            )
        except Exception as e:
            print(f"   ⚠️ Ошибка конвертации задачи {task.id}: {e}")
            return None

    # ==========================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # ==========================================================

    def get_projects(self) -> List[ProjectDTO]:
        return self._cached_projects

    def get_all_tasks(self) -> List[TaskGanttData]:
        return self._cached_tasks

    def get_tasks_for_project(self, project_id: int) -> List[TaskGanttData]:
        return [t for t in self._cached_tasks if t.project_id == project_id]

    def get_task_by_id(self, task_id: int) -> Optional[TaskGanttData]:
        for task in self._cached_tasks:
            if task.id == task_id:
                return task
        return None

    def get_project_name(self, project_id: int) -> str:
        for project in self._cached_projects:
            if project.id == project_id:
                return project.name
        return ""

    def get_tasks_for_tree(self) -> List[Tuple[ProjectDTO, List[TaskGanttData]]]:
        result = []
        for project in self._cached_projects:
            tasks = self.get_tasks_for_project(project.id)
            result.append((project, tasks))
        return result

    def get_unique_executors(self) -> List[str]:
        executors = set()
        for task in self._cached_tasks:
            if task.executor_name:
                executors.add(task.executor_name)
        return sorted(executors)

    def has_tasks(self) -> bool:
        return len(self._cached_tasks) > 0