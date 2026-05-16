# services/tasks_service/tasks_service.py

from typing import Dict, Optional, List
from services.tasks_service.tasks_crud_service import TasksCrudService
from services.tasks_service.tasks_move_service import TasksMoveService
from services.tasks_service.tasks_filter_service import TasksFilterService
from services.tasks_service.tasks_tag_service import TasksTagService
from services.tasks_service.tasks_statistics_service import TasksStatisticsService
from services.tasks_service.tasks_bulk_service import TasksBulkService
from services.tasks_service.tasks_kanban_service import TasksKanbanService


class TasksService:
    """
    Главный сервис для работы с задачами.
    Объединяет все функциональные модули через композицию.
    """

    def __init__(self, db_session, current_user=None, mode="all"):
        # Создаём экземпляры сервисов
        self.crud = TasksCrudService(db_session, current_user, mode)
        self.move = TasksMoveService(db_session, self.crud.repo, current_user, mode)
        self.filter = TasksFilterService(db_session, self.crud.repo, current_user, mode)
        self.tag = TasksTagService(db_session, self.crud.repo, current_user, mode)
        self.stats = TasksStatisticsService(db_session, self.crud.repo, current_user, mode)
        self.bulk = TasksBulkService(db_session, self.crud.repo, current_user, mode)
        self.kanban = TasksKanbanService(db_session, self.crud.repo, current_user, mode)

        # Устанавливаем конвертеры
        self.move.set_task_converter(self.crud._task_to_dict)
        self.stats.set_task_converter(self.crud._task_to_dict)
        self.kanban.set_task_converter(self.crud._task_to_dict)

        # Сохраняем ссылку на метод конвертации
        self._task_to_dict = self.crud._task_to_dict

    # ==========================================================
    # Прокси для CRUD операций
    # ==========================================================
    @property
    def repo(self):
        return self.crud.repo

    def get_task_by_id(self, task_id):
        return self.crud.get_task_by_id(task_id)

    def get_tasks_by_ids(self, task_ids):
        return self.crud.get_tasks_by_ids(task_ids)

    def create_task(self, data):
        return self.crud.create_task(data)

    def update_task(self, task_id, updated_data):
        return self.crud.update_task(task_id, updated_data)

    def delete_task(self, task_id):
        return self.crud.delete_task(task_id)

    def archive_task_by_id(self, task_id):
        return self.crud.archive_task(task_id)

    def duplicate_task(self, task_id):
        return self.crud.duplicate_task(task_id)

    def load_tasks(self):
        return self.crud.load_tasks()

    def get_tasks_for_board(self):
        return self.crud.get_tasks_for_board()

    def prepare_dialog_data(self, mode: str, task_data: Optional[Dict] = None) -> Dict:
        return self.crud.prepare_dialog_data(mode, task_data)

    def validate_form_data(self, form_data: Dict) -> Optional[str]:
        return self.crud.validate_form_data(form_data)

    def process_form_data(self, form_data: Dict, current_user: Dict) -> Dict:
        return self.crud.process_form_data(form_data, current_user)

    def format_assignee_name(self, assignee_id):
        return self.crud.format_assignee_name(assignee_id)

    def is_deadline_overdue(self, deadline_str, completed):
        return self.crud.is_deadline_overdue(deadline_str, completed)

    # ==========================================================
    # Прокси для перемещения (бывший KanbanService)
    # ==========================================================
    def move_task(self, task_id, new_column_name):
        return self.move.move_task(task_id, new_column_name)

    def move_task_to_column(self, task_id, target_column_id):
        return self.move.move_task_to_column(task_id, target_column_id)

    def move_task_to_position(self, task_id, target_column_id, new_position):
        return self.move.move_task_to_position(task_id, target_column_id, new_position)

    def reorder_tasks_in_column(self, column_id, task_order):
        return self.move.reorder_tasks_in_column(column_id, task_order)

    def validate_task_before_move(self, task_id, target_column_id):
        return self.move.validate_move(task_id, target_column_id)

    def can_move_task(self, task_id, target_column_id):
        return self.move.can_move_task(task_id, target_column_id)

    def move_all_tasks_to_column(self, from_column_id, to_column_id):
        return self.move.move_all_tasks_to_column(from_column_id, to_column_id)

    # ==========================================================
    # Прокси для канбан-доски
    # ==========================================================
    def get_column_by_id(self, column_id):
        return self.kanban.get_column_by_id(column_id)

    def get_columns_by_project(self, project_id):
        return self.kanban.get_columns_by_project(project_id)

    def get_template_columns(self):
        return self.kanban.get_template_columns()

    def get_tasks_by_column(self, column_id, include_archived=False):
        return self.kanban.get_tasks_by_column(column_id, include_archived)

    def get_tasks_grouped_by_column(self, project_id=None):
        return self.kanban.get_tasks_grouped_by_column(project_id)

    def get_column_statistics(self, column_id):
        return self.kanban.get_column_statistics(column_id)

    def reorder_column_tasks(self, column_id, task_order):
        return self.kanban.reorder_column_tasks(column_id, task_order)

    def get_task_position(self, task_id):
        return self.kanban.get_task_position(task_id)

    # ==========================================================
    # Прокси для фильтрации
    # ==========================================================
    def filter_tasks_by_priority(self, tasks, priority):
        return self.filter.filter_tasks_by_priority(tasks, priority)

    def filter_tasks_by_project(self, tasks, project_id):
        return self.filter.filter_tasks_by_project(tasks, project_id)

    def filter_tasks_by_status(self, tasks, status):
        return self.filter.filter_tasks_by_status(tasks, status)

    def filter_tasks_by_assignee(self, tasks, assignee_id):
        return self.filter.filter_tasks_by_assignee(tasks, assignee_id)

    def search_tasks(self, tasks, query):
        return self.filter.search_tasks(tasks, query)

    # ==========================================================
    # Прокси для тегов
    # ==========================================================
    def get_all_tags(self, include_archived=False):
        return self.tag.get_all_tags(include_archived)

    def get_all_tags_with_usage(self):
        return self.tag.get_all_tags_with_usage()

    def create_tag(self, name, color="#ccab6e"):
        return self.tag.create_tag(name, color)

    def get_task_tags(self, task_id):
        return self.tag.get_task_tags(task_id)

    def set_task_tags(self, task_id, tag_names):
        return self.tag.set_task_tags(task_id, tag_names)

    def add_tag_to_task(self, task_id, tag_id):
        return self.tag.add_tag_to_task(task_id, tag_id)

    def remove_tag_from_task(self, task_id, tag_id):
        return self.tag.remove_tag_from_task(task_id, tag_id)

    def add_tags_to_task(self, task_id, tag_names):
        return self.tag.add_tags_to_task(task_id, tag_names)

    # ==========================================================
    # Прокси для статистики
    # ==========================================================
    def get_statistics(self):
        return self.stats.get_statistics()

    def get_statistics_for_display(self):
        return self.stats.get_statistics_for_display()

    def get_progress_percent(self):
        return self.stats.get_progress_percent()

    def get_tasks_statistics(self, tasks):
        return self.stats.get_tasks_statistics(tasks)

    def get_user_projects_with_stats(self, user_id):
        return self.stats.get_user_projects_with_stats(user_id)

    # ==========================================================
    # Прокси для массовых операций
    # ==========================================================
    def archive_all_tasks_in_column(self, column_id):
        return self.bulk.archive_all_tasks_in_column(column_id)

    def restore_all_tasks_in_column(self, column_id):
        return self.bulk.restore_all_tasks_in_column(column_id)

    def delete_all_tasks_in_column(self, column_id):
        return self.bulk.delete_all_tasks_in_column(column_id)

    def bulk_update_priority(self, task_ids, new_priority):
        return self.bulk.bulk_update_priority(task_ids, new_priority)

    def bulk_move_to_column(self, task_ids, target_column_id):
        return self.bulk.bulk_move_to_column(task_ids, target_column_id)

    def bulk_assign_to(self, task_ids, assignee_id):
        return self.bulk.bulk_assign_to(task_ids, assignee_id)

    def get_columns_for_board(self) -> List[Dict]:
        """Получить колонки для доски (адаптер для совместимости)"""
        return self.get_all_columns()

    def get_all_columns(self) -> List[Dict]:
        """Получить все уникальные колонки"""
        return self.crud.get_all_columns()

    def get_column_data(self) -> List[Dict]:
        """Получить данные колонок для UI"""
        return self.crud.get_column_data()

    def serialize_task_for_drag(self, task_data: Dict) -> bytes:
        """Сериализовать задачу для Drag & Drop"""
        import json
        return json.dumps(task_data, ensure_ascii=False, default=str).encode("utf-8")

    # ==========================================================
    # Прокси для работы с прогрессом
    # ==========================================================
    def update_task_progress(self, task_id: int, progress_percent: float):
        return self.crud.update_task_progress(task_id, progress_percent)

    def start_task(self, task_id: int):
        return self.crud.start_task(task_id)

    def complete_task(self, task_id: int, actual_hours: float = None):
        return self.crud.complete_task(task_id, actual_hours)

    def get_task_kpd_info(self, task_id: int):
        return self.crud.get_task_kpd_info(task_id)

    def deserialize_task_from_drag(self, data: bytes) -> Optional[Dict]:
        """Десериализовать задачу из Drag & Drop"""
        import json
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            print(f"❌ Ошибка десериализации: {e}")
            return None

    def delete_task_by_id(self, task_id: int) -> bool:
        """Удалить задачу по ID (алиас для delete_task)"""
        return self.delete_task(task_id)