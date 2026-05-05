# services/tasks_service.py
from typing import Dict, Optional

from services.tasks_service.tasks_crud_service import TasksCrudService
from services.tasks_service.tasks_move_service import TasksMoveService
from services.tasks_service.tasks_filter_service import TasksFilterService
from services.tasks_service.tasks_tag_service import TasksTagService
from services.tasks_service.tasks_statistics_service import TasksStatisticsService
from services.tasks_service.tasks_bulk_service import TasksBulkService


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

        # Устанавливаем конвертер
        self.move.set_task_converter(self.crud._task_to_dict)
        self.stats.set_task_converter(self.crud._task_to_dict)

        # Сохраняем ссылку на метод конвертации
        self._task_to_dict = self.crud._task_to_dict

    # Проксируем основные методы
    @property
    def repo(self):
        return self.crud.repo

    def is_deadline_overdue(self, deadline_str, completed):
        return self.crud.is_deadline_overdue(deadline_str, completed)

    def prepare_dialog_data(self, mode: str, task_data: Optional[Dict] = None) -> Dict:
        """Подготавливает данные для диалога"""
        return self.crud.prepare_dialog_data(mode, task_data)

    def validate_form_data(self, form_data: Dict) -> Optional[str]:
        """Валидация данных формы"""
        return self.crud.validate_form_data(form_data)

    def process_form_data(self, form_data: Dict, current_user: Dict) -> Dict:
        """Обработка данных формы"""
        return self.crud.process_form_data(form_data, current_user)

    def delete_task(self, task_id: int) -> bool:
        """Удалить задачу (прокси)"""
        return self.crud.delete_task(task_id)

    def get_task_by_id(self, task_id):
        return self.crud.get_task_by_id(task_id)

    def get_tasks_by_ids(self, task_ids):
        return self.crud.get_tasks_by_ids(task_ids)

    def create_task(self, data):
        return self.crud.create_task(data)

    def update_task(self, task_id, updated_data):
        return self.crud.update_task(task_id, updated_data)

    def delete_task_by_id(self, task_id):
        return self.crud.delete_task(task_id)

    def archive_task_by_id(self, task_id):
        return self.crud.archive_task(task_id)

    def duplicate_task(self, task_id):
        return self.crud.duplicate_task(task_id)

    def get_tasks_for_board(self):
        return self.crud.get_tasks_for_board()

    def load_tasks(self):
        return self.crud.load_tasks()

    def format_assignee_name(self, assignee_id):
        return self.crud.format_assignee_name(assignee_id)

    def get_columns_for_board(self):
        return self.crud.get_columns_for_board()

    def get_column_data(self):
        return self.crud.get_column_data()

    def get_all_columns(self):
        return self.crud.get_all_columns()

    def serialize_task_for_drag(self, task_data):
        return self.crud.serialize_task_for_drag(task_data)

    def deserialize_task_from_drag(self, raw):
        return self.crud.deserialize_task_from_drag(raw)

    # Методы из move сервиса
    def move_task(self, task_id, new_column_name):
        return self.move.move_task(task_id, new_column_name)

    def move_task_to_column(self, task_id, target_column_id):
        return self.move.move_task_to_column(task_id, target_column_id)

    def move_task_to_position(self, task_id, target_column_id, new_position):
        return self.move.move_task_to_position(task_id, target_column_id, new_position)

    def reorder_tasks_in_column(self, column_id, task_order):
        return self.move.reorder_tasks_in_column(column_id, task_order)

    def validate_task_before_move(self, task_id, target_column_id):
        return self.move.validate_task_before_move(task_id, target_column_id)

    # Методы из filter сервиса
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

    # Методы из tag сервиса
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

    # Методы из stats сервиса
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

    # Методы из bulk сервиса
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