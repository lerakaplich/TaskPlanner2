# services/tasks_service/tasks_move_service.py

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, update

from models.projects import BoardColumn
from models.tasks import Task


class TasksMoveService:
    """Сервис для перемещения задач"""

    def __init__(self, db_session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode
        self._task_to_dict = None  # Будет установлен из основного класса

    def set_task_converter(self, converter_func):
        """Установка функции конвертации задачи в словарь"""
        self._task_to_dict = converter_func

    def move_task(self, task_id: int, new_column_name: str) -> Optional[Tuple]:
        """Переместить задачу в другую колонку по имени"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        old_column_name = task.column.name if task.column else None
        new_column = self._get_column_by_name(new_column_name, task.project_id)

        if not new_column or task.column_id == new_column.id:
            return None

        task.column_id = new_column.id
        task.updated_at = datetime.now()
        self.db_session.commit()

        return old_column_name, self._task_to_dict(task) if self._task_to_dict else None

    def move_task_to_column(self, task_id: int, target_column_id: int) -> Optional[Dict]:
        """Переместить задачу в колонку по ID"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        if task.column_id == target_column_id:
            return None

        task.column_id = target_column_id
        task.updated_at = datetime.now()
        self.db_session.commit()

        return self._task_to_dict(task) if self._task_to_dict else None

    def move_task_to_position(self, task_id: int, target_column_id: int, new_position: int) -> Optional[Dict]:
        """Переместить задачу на указанную позицию"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        old_column_id = task.column_id

        if old_column_id == target_column_id:
            self._reorder_in_same_column(target_column_id, task_id, new_position)
        else:
            self._move_to_other_column(task, target_column_id, new_position)

        task.updated_at = datetime.now()
        self.db_session.commit()
        return self._task_to_dict(task) if self._task_to_dict else None

    def _reorder_in_same_column(self, column_id: int, task_id: int, new_position: int):
        """Переупорядочить задачи внутри одной колонки"""
        tasks = self.db_session.scalars(
            select(Task)
            .where(Task.column_id == column_id, Task.id != task_id)
            .order_by(Task.position)
        ).all()

        for idx, task in enumerate(tasks):
            if idx < new_position:
                task.position = idx + 1
            else:
                task.position = idx + 2

        moved_task = self.db_session.get(Task, task_id)
        moved_task.position = new_position + 1

    def _move_to_other_column(self, task: Task, target_column_id: int, new_position: int):
        """Переместить задачу в другую колонку"""
        tasks_in_target = self.db_session.scalars(
            select(Task)
            .where(Task.column_id == target_column_id)
            .order_by(Task.position)
        ).all()

        for idx, t in enumerate(tasks_in_target):
            if idx >= new_position:
                t.position = idx + 2

        task.column_id = target_column_id
        task.position = new_position + 1

    def reorder_tasks_in_column(self, column_id: int, task_order: List[int]) -> bool:
        """Переупорядочить задачи в колонке"""
        try:
            for idx, task_id in enumerate(task_order):
                self.db_session.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(position=idx + 1, updated_at=datetime.now())
                )
            self.db_session.commit()
            return True
        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Ошибка переупорядочивания: {e}")
            return False

    def validate_task_before_move(self, task_id: int, target_column_id: int) -> Tuple[bool, str]:
        """Проверить возможность перемещения задачи"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return False, "Задача не найдена"

        target_column = self.db_session.get(BoardColumn, target_column_id)
        if not target_column:
            return False, "Целевая колонка не найдена"

        if task.column_id == target_column_id:
            return False, "Задача уже в этой колонке"

        if target_column.is_done_column and not task.column.is_done_column:
            if not self._can_complete_task(task):
                return False, "Невозможно отметить задачу как выполненную"

        return True, ""

    def _can_complete_task(self, task: Task) -> bool:
        """Проверить, можно ли отметить задачу как выполненную"""
        return True

    def _get_column_by_name(self, column_name: str, project_id: int = None):
        """Получить колонку по имени"""
        from sqlalchemy import select

        stmt = select(BoardColumn).where(BoardColumn.name == column_name)
        if project_id:
            stmt = stmt.where(BoardColumn.project_id == project_id)
        return self.db_session.scalar(stmt)