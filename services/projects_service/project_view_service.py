# services/projects_service/project_view_service.py
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from PyQt6.QtWidgets import QMessageBox

from models.schemas.projects_dto import ProjectWithMembersDTO
from services.tasks_service.tasks_service import TasksService


class ProjectViewService:
    """Сервис для работы со страницей просмотра проекта"""

    def __init__(self, session: Session, project_service, current_user: Dict):
        self.session = session
        self.project_service = project_service
        self.current_user = current_user
        self.current_user_id = current_user.get('id') if current_user else None

    def get_project_tasks_for_user(self, project_id: int, user_id: int,
                                   include_archived: bool = False,
                                   view_all: bool = True) -> List[Dict]:
        """
        Получает задачи проекта с учётом прав пользователя

        Args:
            project_id: ID проекта
            user_id: ID пользователя
            include_archived: включать архивные задачи
            view_all: если True - все задачи, если False - только свои
        """
        tasks = self.get_project_tasks(project_id, include_archived)

        if not view_all:
            # Показываем только задачи, созданные пользователем
            tasks = [t for t in tasks if t.get('created_by') == user_id]

        return tasks

    def get_project_data(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        """Получает данные проекта"""
        return self.project_service.get_project_for_edit(project_id)

    def get_project_columns(self, project_id: int) -> List[Dict]:
        """Получает колонки проекта"""
        return self.project_service.get_project_columns(project_id)

    def get_project_tasks(self, project_id: int, include_archived: bool = False) -> List[Dict]:
        """Получает задачи проекта"""
        return self.project_service.get_project_tasks_for_view(project_id, include_archived)

    def create_task_card_data(self, task_data: Dict) -> Dict:
        """Подготавливает данные для карточки задачи"""
        is_archived = task_data.get('is_archived', False)
        is_creator = (task_data.get('created_by') == self.current_user_id)

        return {
            'task_data': task_data,
            'is_archived': is_archived,
            'is_creator': is_creator,
            'is_archived_project': False  # будет установлено отдельно
        }

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        return self.project_service.restore_task(task_id)

    def delete_task_permanently(self, task_id: int) -> bool:
        """Удаляет задачу навсегда"""
        return self.project_service.delete_task_permanently(task_id)

    def get_tasks_service(self) -> TasksService:
        """Возвращает сервис задач"""
        return TasksService(
            db_session=self.session,
            current_user=self.current_user,
            mode="all"
        )

    def group_tasks_by_column(self, tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """Группирует задачи по колонкам"""
        tasks_by_column = {}
        for task in tasks:
            column_name = task.get('status', "К выполнению")
            if column_name not in tasks_by_column:
                tasks_by_column[column_name] = []
            tasks_by_column[column_name].append(task)
        return tasks_by_column

    def calculate_statistics(self, all_tasks: List[Dict]) -> Dict:
        """Рассчитывает статистику по задачам"""
        total = len(all_tasks)

        if total > 0:
            total_progress = sum(task.get("progress_percent", 0) for task in all_tasks)
            avg_progress = int(total_progress / total)
        else:
            avg_progress = 0

        return {
            'total': total,
            'avg_progress': avg_progress
        }

    def get_project_name(self, project_id: int) -> str:
        """Получает название проекта"""
        project = self.project_service.get_project_for_edit(project_id)
        return project.name if project else f"Проект #{project_id}"

    def is_project_archived(self, project_id: int) -> bool:
        """Проверяет, архивирован ли проект"""
        project = self.project_service.get_project_for_edit(project_id)
        return project.is_archived if project else False