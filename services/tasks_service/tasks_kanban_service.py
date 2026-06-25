# services/tasks_service/tasks_kanban_service.py
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.projects import BoardColumn
from models.tasks import Task


class TasksKanbanService:
    """Специфичные для канбан-доски методы"""

    def __init__(self, db_session: Session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode
        self._task_to_dict = None

    def set_task_converter(self, converter_func):
        """Установка функции конвертации задачи в словарь"""
        self._task_to_dict = converter_func

    # ==========================================================
    # Работа с колонками
    # ==========================================================

    def get_column_by_id(self, column_id: int) -> Optional[Dict]:
        """Получает колонку по ID"""
        column = self.db_session.get(BoardColumn, column_id)
        if not column:
            return None
        return {
            "id": column.id,
            "name": column.name,
            "color": column.color,
            "position": column.position,
            "is_done": column.is_done_column,
            "project_id": column.project_id
        }

    def get_columns_by_project(self, project_id: int) -> List[Dict]:
        """Получает все колонки проекта"""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        columns = self.db_session.scalars(stmt).all()
        return [
            {
                "id": col.id,
                "name": col.name,
                "color": col.color,
                "position": col.position,
                "is_done": col.is_done_column,
                "project_id": col.project_id
            }
            for col in columns
        ]

    def get_template_columns(self) -> List[Dict]:
        """Получает все колонки"""
        stmt = select(BoardColumn).order_by(BoardColumn.position)
        columns = self.db_session.scalars(stmt).all()
        return [
            {
                "id": col.id,
                "name": col.name,
                "color": col.color,
                "position": col.position,
                "is_done": col.is_done_column
            }
            for col in columns
        ]

    def get_column_statistics(self, column_id: int) -> Dict:
        """Возвращает статистику по колонке"""
        tasks = self.get_tasks_by_column(column_id)
        total = len(tasks)
        overdue = sum(1 for t in tasks if t.get("deadline") and t.get("deadline") < datetime.now())
        high_priority = sum(1 for t in tasks if t.get("priority") in ["high", "critical"])

        return {
            "total": total,
            "overdue": overdue,
            "high_priority": high_priority
        }

    # ==========================================================
    # Работа с задачами для канбан-доски
    # ==========================================================

    def get_tasks_by_column(self, column_id: int, include_archived: bool = False) -> List[Dict]:
        """Получает все задачи в колонке"""
        stmt = select(Task).where(Task.column_id == column_id)
        if not include_archived:
            stmt = stmt.where(Task.is_archived == False)
        stmt = stmt.order_by(Task.position)
        tasks = self.db_session.scalars(stmt).all()
        return [self._task_to_dict(task) for task in tasks] if self._task_to_dict else []

    def get_tasks_grouped_by_column(self, project_id: int = None) -> Dict[str, List[Dict]]:
        """Возвращает задачи, сгруппированные по колонкам"""
        stmt = select(BoardColumn).order_by(BoardColumn.position)
        if project_id:
            stmt = stmt.where(BoardColumn.project_id == project_id)

        columns = self.db_session.scalars(stmt).all()
        result = {}

        for column in columns:
            tasks = self.get_tasks_by_column(column.id)
            result[column.name] = tasks

        return result

    def reorder_column_tasks(self, column_id: int, task_order: List[int]) -> bool:
        """
        Переупорядочивает задачи в колонке согласно переданному порядку.
        task_order - список ID задач в правильном порядке
        """
        try:
            for idx, task_id in enumerate(task_order):
                task = self.db_session.get(Task, task_id)
                if task and task.column_id == column_id:
                    task.position = idx + 1
            self.db_session.commit()
            return True
        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Ошибка переупорядочивания задач: {e}")
            return False

    def get_task_position(self, task_id: int) -> int:
        """Возвращает позицию задачи в колонке"""
        task = self.db_session.get(Task, task_id)
        return task.position if task else -1