# services/gantt_service.py
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_

from models.tasks import Task, TaskDependency
from models.projects import Project
from models.schemas.projects_dto import ProjectDTO


@dataclass
class TaskGanttData:
    """Данные задачи для отображения на диаграмме Ганта"""
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    executor_name: str
    executor_initials: str
    executor_id: Optional[int]
    color: str
    priority: str
    progress: float
    dependencies: List[Dict]
    project_id: int
    project_name: str
    status: str

    @property
    def duration_days(self) -> int:
        return max(1, (self.end_date - self.start_date).days + 1)


class GanttService:
    """Сервис для работы с диаграммой Ганта - реальные данные из БД"""

    # Константы для отрисовки
    DAY_WIDTH = 30
    ROW_HEIGHT = 50
    HEADER_HEIGHT = 55
    LEFT_PADDING = 200

    # Цвета для приоритетов
    PRIORITY_COLORS = {
        "critical": "#D22730",  # Красный
        "high": "#ccab6e",  # Золотой
        "medium": "#1B232A",  # Темно-синий
        "low": "#998664"  # Коричневый
    }

    def __init__(self, session: Session, current_user_id: int = None, project_service=None):
        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service
        self._cached_tasks: List[TaskGanttData] = []
        self._cached_projects: List[ProjectDTO] = []

    def create_task_via_service(self, form_data: Dict) -> Optional[Dict]:
        """
        Создаёт задачу через сервис задач.

        Args:
            form_data: данные формы задачи

        Returns:
            Dict: созданная задача или None
        """
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        try:
            task_service = TasksService(
                db_session=self.session,
                current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
                mode="others",
                column_service=ColumnService(self.session)
            )

            # Добавляем created_by если нет
            if "created_by" not in form_data:
                form_data["created_by"] = self.current_user_id

            new_task = task_service.create_task(form_data)
            print(f"✅ Задача создана: {new_task.get('id')}")
            return new_task

        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_task_dates_with_linked(self, task_id: int, new_start: datetime, new_end: datetime) -> bool:
        """
        Обновляет даты задачи и всех зависимых задач.

        Args:
            task_id: ID задачи
            new_start: новая дата начала
            new_end: новая дата окончания

        Returns:
            bool: успех операции
        """
        try:
            # Обновляем основную задачу
            if not self.update_task_dates(task_id, new_start, new_end):
                return False

            # Обновляем зависимые задачи
            old_task = None
            for t in self._cached_tasks:
                if t.id == task_id:
                    old_start = t.start_date
                    old_end = t.end_date
                    break

            if old_task:
                delta = (new_start - old_start).days
                linked_ids = self.get_linked_tasks_for_update(task_id)

                for linked_id in linked_ids:
                    for t in self._cached_tasks:
                        if t.id == linked_id:
                            new_linked_start = t.start_date + timedelta(days=delta)
                            new_linked_end = t.end_date + timedelta(days=delta)
                            self.update_task_dates(linked_id, new_linked_start, new_linked_end)
                            break

            return True
        except Exception as e:
            print(f"❌ Ошибка обновления дат с зависимостями: {e}")
            return False

    def get_all_data(self) -> Dict:
        """
        Возвращает все данные для UI.

        Returns:
            Dict: словарь с проектами, задачами, связями
        """
        return {
            "projects": self._cached_projects,
            "tasks": self._cached_tasks,
            "links": self.get_all_links(),
            "executors": self.get_unique_executors()
        }

    def get_task_by_id(self, task_id: int) -> Optional[TaskGanttData]:
        """
        Возвращает задачу по ID.

        Args:
            task_id: ID задачи

        Returns:
            TaskGanttData или None
        """
        for task in self._cached_tasks:
            if task.id == task_id:
                return task
        return None

    def validate_project_selected(self, project_filter: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Проверяет, выбран ли проект.

        Args:
            project_filter: текущий фильтр проекта ("all" или "project_{id}")

        Returns:
            Tuple[bool, Optional[int], Optional[str]]: (is_valid, project_id, error_message)
        """
        if project_filter == "all":
            return False, None, "Пожалуйста, сначала выберите проект из списка проектов"

        try:
            project_id = int(project_filter.split("_")[1])
            return True, project_id, None
        except (ValueError, IndexError):
            return False, None, "Неверный формат фильтра проекта"

    def get_tasks_for_tree(self) -> List[Tuple[ProjectDTO, List[TaskGanttData]]]:
        """
        Возвращает проекты с их задачами для дерева.

        Returns:
            List[Tuple[ProjectDTO, List[TaskGanttData]]]: список (проект, задачи проекта)
        """
        result = []
        for project in self._cached_projects:
            tasks = self.get_tasks_for_project(project.id)
            result.append((project, tasks))
        return result

    def load_data(self, project_id: Optional[int] = None) -> None:
        """Загружает данные из БД"""
        print(f"📊 GanttService.load_data(project_id={project_id})")

        # Загружаем проекты
        self._load_projects()

        # Загружаем задачи
        self._load_tasks(project_id)

    def create_task_from_dialog(self, form_data: Dict, current_user_id: int) -> Optional[Dict]:
        """
        Создаёт задачу из данных диалога.

        Args:
            form_data: данные формы задачи
            current_user_id: ID текущего пользователя

        Returns:
            Dict: созданная задача или None
        """
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        try:
            task_service = TasksService(
                db_session=self.session,
                current_user={"id": current_user_id, "last_name": "", "first_name": ""},
                mode="others",
                column_service=ColumnService(self.session)
            )

            # Добавляем created_by если нет
            if "created_by" not in form_data:
                form_data["created_by"] = current_user_id

            new_task = task_service.create_task(form_data)
            print(f"✅ Задача создана: {new_task.get('id')}")
            return new_task

        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            import traceback
            traceback.print_exc()
            return None

    def refresh_all_data(self, project_id: Optional[int] = None) -> None:
        """
        Полностью перезагружает все данные.

        Args:
            project_id: опциональный ID проекта для фильтрации
        """
        self._cached_tasks = []
        self._cached_projects = []
        self.load_data(project_id)

    def get_project_name(self, project_id: int) -> str:
        """
        Возвращает имя проекта по ID.

        Args:
            project_id: ID проекта

        Returns:
            str: имя проекта или пустая строка
        """
        for project in self._cached_projects:
            if project.id == project_id:
                return project.name
        return ""

    def get_filtered_tasks(self, project_filter: str, executor_filter: str) -> List[TaskGanttData]:
        """
        Возвращает задачи с применением фильтров.

        Args:
            project_filter: "all" или "project_{id}"
            executor_filter: "all" или имя исполнителя

        Returns:
            List[TaskGanttData]: отфильтрованные задачи
        """
        all_tasks = self.get_all_tasks()

        # Фильтр по проекту
        if project_filter != "all":
            project_id = int(project_filter.split("_")[1])
            filtered = [t for t in all_tasks if t.project_id == project_id]
        else:
            filtered = all_tasks.copy()

        # Фильтр по исполнителю
        if executor_filter != "all":
            filtered = [t for t in filtered if t.executor_name == executor_filter]

        return filtered

    def get_date_range_for_tasks(self, tasks: List[TaskGanttData], padding_days: int = 7) -> Tuple[datetime, datetime]:
        """
        Возвращает диапазон дат для списка задач с отступом.

        Args:
            tasks: список задач
            padding_days: количество дней отступа

        Returns:
            Tuple[datetime, datetime]: (start_date, end_date)
        """
        if not tasks:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today, today + timedelta(days=30)

        start = min(t.start_date for t in tasks)
        end = max(t.end_date for t in tasks)

        return start - timedelta(days=padding_days), end + timedelta(days=padding_days)

    def get_unique_executors(self) -> List[str]:
        """
        Возвращает список уникальных имён исполнителей.

        Returns:
            List[str]: отсортированный список имён исполнителей
        """
        executors = set()
        for task in self.get_all_tasks():
            if task.executor_name:
                executors.add(task.executor_name)
        return sorted(executors)

    def _load_projects(self) -> None:
        """Загружает проекты из БД"""
        try:
            stmt = select(Project).where(Project.is_archived == False).order_by(Project.name)
            projects = self.session.scalars(stmt).all()
            self._cached_projects = [ProjectDTO.model_validate(p) for p in projects]
            print(f"   ✅ Загружено {len(self._cached_projects)} проектов")
        except Exception as e:
            print(f"   ❌ Ошибка загрузки проектов: {e}")
            self._cached_projects = []

    def _load_tasks(self, project_id: Optional[int] = None) -> None:
        """Загружает задачи из БД"""
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

            tasks = self.session.scalars(stmt).unique().all()
            print(f"   ✅ Загружено {len(tasks)} задач")

            self._cached_tasks = []
            for task in tasks:
                gantt_task = self._convert_to_gantt_data(task)
                if gantt_task:
                    self._cached_tasks.append(gantt_task)

        except Exception as e:
            print(f"   ❌ Ошибка загрузки задач: {e}")
            import traceback
            traceback.print_exc()
            self._cached_tasks = []

    def _convert_to_gantt_data(self, task: Task) -> Optional[TaskGanttData]:
        """Конвертирует Task в TaskGanttData"""
        try:
            # Получаем даты
            start_date = task.created_at if task.created_at else datetime.now()
            end_date = task.deadline if task.deadline else start_date + timedelta(days=7)

            # Нормализуем даты (без времени)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Корректируем если start > end
            if start_date > end_date:
                start_date, end_date = end_date, start_date + timedelta(days=1)

            # Получаем имя исполнителя
            executor_name = ""
            executor_initials = ""
            if task.assigned_to and self.project_service:
                user = self.project_service.get_user_by_id(task.assigned_to)
                if user:
                    executor_name = f"{user.get('last_name', '')} {user.get('first_name', '')}"
                    executor_initials = self._get_initials(user)

            # Получаем цвет по приоритету
            priority_value = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            color = self.PRIORITY_COLORS.get(priority_value, self.PRIORITY_COLORS["medium"])

            # Получаем зависимости
            dependencies = []
            for dep in task.dependencies_as_predecessor:
                dependencies.append({
                    "successor_id": dep.successor_id,
                    "lag": dep.lag,
                    "type": dep.type
                })

            # Получаем имя проекта
            project_name = ""
            if task.project_id:
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

    def _get_initials(self, user: Dict) -> str:
        """Получает инициалы пользователя"""
        first = user.get('first_name', '')
        last = user.get('last_name', '')
        if last and first:
            return f"{last[0]}{first[0]}".upper()
        return "??"

    def get_projects(self) -> List[ProjectDTO]:
        """Возвращает список проектов"""
        return self._cached_projects

    def get_all_tasks(self) -> List[TaskGanttData]:
        """Возвращает все задачи"""
        return self._cached_tasks

    def get_tasks_for_project(self, project_id: int) -> List[TaskGanttData]:
        """Возвращает задачи для конкретного проекта"""
        return [t for t in self._cached_tasks if t.project_id == project_id]

    def get_all_links(self) -> Dict[int, List[int]]:
        """Возвращает все связи между задачами"""
        links = {}
        for task in self._cached_tasks:
            for dep in task.dependencies:
                links[task.id] = links.get(task.id, [])
                links[task.id].append(dep["successor_id"])
        return links

    def get_linked_tasks_for_update(self, task_id: int) -> List[int]:
        """Возвращает ID задач, которые зависят от данной"""
        linked = []
        for task in self._cached_tasks:
            for dep in task.dependencies:
                if dep["successor_id"] == task_id:
                    linked.append(task.id)
        return linked

    def calculate_bar_position(self, task: TaskGanttData, start_date: datetime) -> Tuple[float, float]:
        """Вычисляет позицию и ширину полосы задачи"""
        total_days = max(1, (task.end_date - task.start_date).days + 1)
        offset_days = max(0, (task.start_date - start_date).days)

        x = self.LEFT_PADDING + offset_days * self.DAY_WIDTH
        width = total_days * self.DAY_WIDTH

        return float(x), float(width)

    def get_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """Возвращает диапазон дат для выбранного периода"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "Месяц":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            return start, end
        elif period == "Квартал":
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            if quarter == 3:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 3, day=1) - timedelta(days=1)
            return start, end
        elif period == "Год":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            return start, end
        else:  # "Неделя" или по умолчанию
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end

    def update_task_dates(self, task_id: int, start_date: datetime, end_date: datetime) -> bool:
        """Обновляет даты задачи в БД"""
        try:
            task = self.session.get(Task, task_id)
            if task:
                task.created_at = start_date
                task.deadline = end_date
                self.session.commit()

                # Обновляем в кэше
                for t in self._cached_tasks:
                    if t.id == task_id:
                        t.start_date = start_date
                        t.end_date = end_date
                        break

                print(f"✅ Задача {task_id}: даты обновлены на {start_date.date()} - {end_date.date()}")
                return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка обновления дат: {e}")
        return False

    def add_dependency(self, predecessor_id: int, successor_id: int, lag: int = 0, dep_type: str = "FS") -> bool:
        """Добавляет связь между задачами"""
        try:
            # Проверяем, существует ли уже такая связь
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                return False

            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.commit()

            # Обновляем кэш
            for t in self._cached_tasks:
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                    break

            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка создания связи: {e}")
            return False