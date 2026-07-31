# services/gantt_service/gantt_service.py

from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session

from services.gantt_service.gantt_base_service import GanttBaseService, TaskGanttData
from services.gantt_service.gantt_data_service import GanttDataService
from services.gantt_service.gantt_dependency_service import GanttDependencyService
from services.gantt_service.gantt_export_service import GanttExportService
from services.gantt_service.gantt_filter_service import GanttFilterService


class GanttService(GanttBaseService):
    """Главный сервис для работы с диаграммой Ганта - ФАСАД"""

    def __init__(self, session: Session, current_user_id: int = None, project_service=None, permission_service=None):
        self.session = session
        self.current_user_id = current_user_id
        self.permission_service = permission_service  # <-- ДОБАВЛЕНО

        self.data = GanttDataService(session, current_user_id, project_service, permission_service)
        self.filter = GanttFilterService(self.data)
        self.deps = GanttDependencyService(session, self.data, permission_service)
        self.export = GanttExportService(permission_service)

    # services/gantt_service/gantt_service.py

    def add_dependency_with_message(
            self,
            predecessor_id: int,
            successor_id: int,
            lag: int = 0,
            dep_type: str = "FS"
    ) -> Tuple[bool, str]:
        """
        Добавляет связь между задачами и возвращает результат с сообщением.
        """
        return self.deps.add_dependency(predecessor_id, successor_id, lag, dep_type)

    def get_link_type_info(self, link_type: str) -> Dict:
        """Возвращает информацию о типе связи."""
        return self.deps.get_link_type_info(link_type)

    def get_all_link_types(self) -> Dict[str, Dict]:
        """Возвращает все доступные типы связей."""
        return self.deps.get_all_link_types()

    def get_link_info(self, predecessor_id: int, successor_id: int) -> Optional[Dict]:
        """Возвращает информацию о связи между двумя задачами."""
        all_links = self.get_all_links()
        deps = all_links.get(predecessor_id, [])
        for dep in deps:
            if dep.get("successor_id") == successor_id:
                link_type = dep.get("type", "FS")
                info = self.get_link_type_info(link_type)
                return {
                    "type": link_type,
                    "type_name": info.get("name", "Неизвестный"),
                    "description": info.get("description", ""),
                    "symbol": info.get("symbol", "?")
                }
        return None

    def load_data(self, project_id: Optional[int] = None) -> None:
        self.data.load_data(project_id)

    def clear_cache(self) -> None:
        self.data.clear_cache()

    def refresh_all_data(self, project_id: Optional[int] = None) -> None:
        self.data.refresh_all_data(project_id)

    def get_projects(self) -> List:
        return self.data.get_projects()

    def get_all_tasks(self) -> List[TaskGanttData]:
        return self.data.get_all_tasks()

    def get_task_by_id(self, task_id: int) -> Optional[TaskGanttData]:
        return self.data.get_task_by_id(task_id)

    def get_tasks_for_tree(self) -> List:
        return self.data.get_tasks_for_tree()

    def get_unique_executors(self) -> List[str]:
        return self.data.get_unique_executors()

    def get_project_name(self, project_id: int) -> str:
        return self.data.get_project_name(project_id)

    def has_tasks(self) -> bool:
        return self.data.has_tasks()

    def get_filtered_tasks(self, project_filter: str, executor_filter: str) -> List[TaskGanttData]:
        return self.filter.get_filtered_tasks(project_filter, executor_filter)

    def get_filtered_tasks_for_export(self, tasks: List[TaskGanttData], start_date, end_date) -> List[TaskGanttData]:
        return self.filter.get_filtered_tasks_for_export(tasks, start_date, end_date)

    def get_date_range(self, period: str) -> Tuple:
        return self.filter.get_date_range(period)

    def get_date_range_for_tasks(self, tasks: List[TaskGanttData], padding_days: int = 14) -> Tuple:
        return self.filter.get_date_range_for_tasks(tasks, padding_days)

    def get_default_export_period(self, tasks: List[TaskGanttData]) -> Tuple:
        return self.filter.get_default_export_period(tasks)

    def validate_project_selected(self, project_filter: str) -> Tuple:
        return self.filter.validate_project_selected(project_filter)

    def get_all_links(self) -> Dict[int, List[int]]:
        return self.deps.get_all_links()

    def get_linked_tasks_for_update(self, task_id: int) -> List[int]:
        return self.deps.get_linked_tasks_for_update(task_id)

    def add_dependency(self, predecessor_id: int, successor_id: int, lag: int = 0, dep_type: str = "FS") -> bool:
        return self.deps.add_dependency(predecessor_id, successor_id, lag, dep_type)

    def update_task_dates_with_linked(self, task_id: int, new_start, new_end) -> bool:
        return self.deps.update_task_dates_with_linked(task_id, new_start, new_end)

    def can_export(self) -> bool:
        return self.export.can_export()

    def export_to_image_with_period(self, canvas_widget, tasks, start_date, end_date) -> Optional[str]:
        return self.export.export_to_image_with_period(canvas_widget, tasks, start_date, end_date)

    def export_to_excel(self, tasks, start_date=None, end_date=None) -> Optional[str]:
        return self.export.export_to_excel(tasks, start_date, end_date)

    def export_to_docx(self, tasks, start_date=None, end_date=None) -> Optional[str]:
        return self.export.export_to_docx(tasks, start_date, end_date)

    def get_task_info_text(self, task: TaskGanttData) -> str:
        return self.export.get_task_info_text(task)

    def can_create_link(self) -> bool:
        """Проверяет права на создание связей"""
        if not self.permission_service:
            return False
        from services.permissions.app_permissions import AppRole
        return self.permission_service.app_manager.role == AppRole.SUPER_ADMIN

    def calculate_bar_position(self, task: TaskGanttData, start_date) -> Tuple[float, float]:
        total_days = max(1, (task.end_date - task.start_date).days + 1)
        offset_days = max(0, (task.start_date - start_date).days)

        x = self.LEFT_PADDING + offset_days * self.DAY_WIDTH
        width = total_days * self.DAY_WIDTH

        return float(x), float(width)

    def create_task_via_service(self, form_data: Dict) -> Optional[Dict]:
        """Создаёт задачу через сервис задач"""
        if not self.can_create_task():
            print("❌ Нет прав на создание задач")
            return None

        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        try:
            task_service = TasksService(
                db_session=self.session,
                current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
                mode="others",
                column_service=ColumnService(self.session)
            )

            if "created_by" not in form_data:
                form_data["created_by"] = self.current_user_id

            new_task = task_service.create_task(form_data)
            print(f"✅ Задача создана: {new_task.get('id')}")
            return new_task

        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            return None

    # services/gantt_service/gantt_service.py

    def get_manageable_projects(self) -> List[Dict[str, Any]]:
        """Возвращает проекты, где пользователь может управлять задачами"""
        return self.data.get_manageable_projects()

    def can_create_task(self) -> bool:
        """
        Проверяет, может ли пользователь создавать задачи
        """
        if not self.permission_service:
            return False

        from services.permissions.app_permissions import AppRole
        app_role = self.permission_service.app_manager.role

        # Суперадмин и админ могут создавать
        if app_role in (AppRole.SUPER_ADMIN, AppRole.ADMIN):
            return True

        # Проверяем, есть ли у пользователя проекты, где он администратор или куратор
        manageable_projects = self.get_manageable_projects()
        return len(manageable_projects) > 0