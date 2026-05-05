# services/tasks_service/tasks_bulk_service.py

from typing import List, Dict
from datetime import datetime
from sqlalchemy import select, update

from models.tasks import Task
from models.schemas.tasks_dto import TaskPriority


class TasksBulkService:
    """Сервис для массовых операций с задачами"""

    def __init__(self, db_session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode

    def archive_all_tasks_in_column(self, column_id: int) -> int:
        """Архивировать все задачи в колонке"""
        stmt = update(Task).where(
            Task.column_id == column_id,
            Task.is_archived == False
        ).values(
            is_archived=True,
            archived_at=datetime.now(),
            updated_at=datetime.now()
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount

    def restore_all_tasks_in_column(self, column_id: int) -> int:
        """Восстановить все задачи в колонке"""
        stmt = update(Task).where(
            Task.column_id == column_id,
            Task.is_archived == True
        ).values(
            is_archived=False,
            archived_at=None,
            updated_at=datetime.now()
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount

    def delete_all_tasks_in_column(self, column_id: int) -> int:
        """Удалить все задачи в колонке"""
        stmt = select(Task.id).where(Task.column_id == column_id)
        task_ids = self.db_session.scalars(stmt).all()

        for task_id in task_ids:
            self.repo.delete(task_id)

        self.db_session.commit()
        return len(task_ids)

    def bulk_update_priority(self, task_ids: List[int], new_priority: str) -> int:
        """Массовое обновление приоритета"""
        priority_map = {
            "Низкий": TaskPriority.low,
            "Средний": TaskPriority.medium,
            "Высокий": TaskPriority.high,
            "Критический": TaskPriority.critical
        }
        priority_enum = priority_map.get(new_priority, TaskPriority.medium)

        stmt = update(Task).where(
            Task.id.in_(task_ids)
        ).values(
            priority=priority_enum,
            updated_at=datetime.now()
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount

    def bulk_move_to_column(self, task_ids: List[int], target_column_id: int) -> int:
        """Массовое перемещение задач в колонку"""
        max_pos = self.get_max_position_in_column(target_column_id) if hasattr(self, 'get_max_position_in_column') else 0

        for idx, task_id in enumerate(task_ids):
            stmt = update(Task).where(Task.id == task_id).values(
                column_id=target_column_id,
                position=max_pos + idx + 1,
                updated_at=datetime.now()
            )
            self.db_session.execute(stmt)

        self.db_session.commit()
        return len(task_ids)

    def bulk_assign_to(self, task_ids: List[int], assignee_id: int) -> int:
        """Массовое назначение исполнителя"""
        stmt = update(Task).where(
            Task.id.in_(task_ids)
        ).values(
            assigned_to=assignee_id,
            updated_at=datetime.now()
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount