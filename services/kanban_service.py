# services/kanban_service.py

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import select, func, update
from models.tasks import Task
from models.projects import BoardColumn


class KanbanService:
    """Сервис для работы с канбан-доской и задачами"""

    def __init__(self, session):
        self.session = session

    # ==========================================================
    # Работа с колонками
    # ==========================================================

    def get_column_by_id(self, column_id: int) -> Optional[Dict]:
        """Получает колонку по ID"""
        column = self.session.get(BoardColumn, column_id)
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
        columns = self.session.scalars(stmt).all()
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
        """Получает шаблонные колонки"""
        stmt = select(BoardColumn).where(
            BoardColumn.is_template == True
        ).order_by(BoardColumn.template_order)
        columns = self.session.scalars(stmt).all()
        return [
            {
                "id": col.id,
                "name": col.name,
                "color": col.color,
                "position": col.position,
                "is_done": col.is_done_column,
                "template_order": col.template_order
            }
            for col in columns
        ]

    # ==========================================================
    # Работа с задачами
    # ==========================================================

    def get_tasks_by_column(self, column_id: int, include_archived: bool = False) -> List[Dict]:
        """Получает все задачи в колонке"""
        stmt = select(Task).where(Task.column_id == column_id)
        if not include_archived:
            stmt = stmt.where(Task.is_archived == False)
        stmt = stmt.order_by(Task.position)
        tasks = self.session.scalars(stmt).all()
        return [self._task_to_dict(task) for task in tasks]

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получает задачу по ID"""
        task = self.session.get(Task, task_id)
        if not task:
            return None
        return self._task_to_dict(task)

    def can_move_task(self, task_id: int, target_column_id: int) -> bool:
        """
        Проверяет, можно ли переместить задачу в целевую колонку.
        Возвращает True если перемещение разрешено.
        """
        task = self.session.get(Task, task_id)
        if not task:
            return False

        # Задача уже в целевой колонке
        if task.column_id == target_column_id:
            return False

        target_column = self.session.get(BoardColumn, target_column_id)
        if not target_column:
            return False

        # Если задача в колонке "Выполнено" (is_done=True) - запрещаем перемещение
        if task.column and task.column.is_done_column:
            return False

        # Разрешаем перемещение
        return True

    def move_task(self, task_id: int, target_column_id: int, new_position: int = None) -> Optional[Dict]:
        """
        Перемещает задачу в другую колонку.
        Возвращает обновленные данные задачи или None.
        """
        task = self.session.get(Task, task_id)
        if not task:
            return None

        if not self.can_move_task(task_id, target_column_id):
            return None

        old_column_id = task.column_id
        task.column_id = target_column_id
        task.updated_at = datetime.now()

        # Обновляем позицию
        if new_position is not None:
            self._reorder_tasks_in_column(target_column_id, task_id, new_position)
        else:
            # Перемещаем в конец
            max_pos = self._get_max_position_in_column(target_column_id)
            task.position = max_pos + 1

        self.session.commit()
        return self._task_to_dict(task)

    def _reorder_tasks_in_column(self, column_id: int, task_id: int, new_position: int):
        """Переупорядочивает задачи в колонке после перемещения"""
        # Получаем все задачи в колонке
        tasks = self.session.scalars(
            select(Task).where(
                Task.column_id == column_id,
                Task.id != task_id
            ).order_by(Task.position)
        ).all()

        # Обновляем позиции
        for idx, task in enumerate(tasks):
            if idx >= new_position:
                task.position = idx + 2  # Сдвигаем вниз
            else:
                task.position = idx + 1

        # Устанавливаем позицию перемещенной задачи
        moved_task = self.session.get(Task, task_id)
        moved_task.position = new_position + 1

    def _get_max_position_in_column(self, column_id: int) -> int:
        """Возвращает максимальную позицию задачи в колонке"""
        result = self.session.scalar(
            select(func.max(Task.position)).where(Task.column_id == column_id)
        )
        return result or 0

    def reorder_task(self, task_id: int, new_position: int) -> bool:
        """
        Переупорядочивает задачу внутри той же колонки.
        Возвращает True при успехе.
        """
        task = self.session.get(Task, task_id)
        if not task:
            return False

        column_id = task.column_id
        self._reorder_tasks_in_column(column_id, task_id, new_position)
        self.session.commit()
        return True

    def get_task_position(self, task_id: int) -> int:
        """Возвращает позицию задачи в колонке"""
        task = self.session.get(Task, task_id)
        return task.position if task else -1

    # ==========================================================
    # Валидация перемещений
    # ==========================================================

    def validate_move(self, task_id: int, target_column_id: int) -> tuple:
        """
        Проверяет возможность перемещения задачи.
        Возвращает (разрешено_ли, сообщение_об_ошибке)
        """
        task = self.session.get(Task, task_id)
        if not task:
            return False, "Задача не найдена"

        if task.column_id == target_column_id:
            return False, "Задача уже находится в этой колонке"

        target_column = self.session.get(BoardColumn, target_column_id)
        if not target_column:
            return False, "Целевая колонка не найдена"

        if task.column and task.column.is_done_column:
            return False, "Нельзя переместить выполненную задачу"

        # Проверка на завершающую колонку
        if target_column.is_done_column:
            # Дополнительная валидация для завершающей колонки
            if not self._can_complete_task(task):
                return False, "Задача не может быть отмечена как выполненная (проверьте все подзадачи или требования)"

        return True, ""

    def _can_complete_task(self, task: Task) -> bool:
        """Проверяет, можно ли отметить задачу как выполненную"""
        # Здесь можно добавить логику проверки:
        # - Все подзадачи выполнены
        # - Все необходимые поля заполнены
        # - и т.д.
        return True

    # ==========================================================
    # Преобразование данных
    # ==========================================================

    def _task_to_dict(self, task: Task) -> Dict:
        """Преобразует задачу в словарь"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "position": task.position,
            "column_id": task.column_id,
            "project_id": task.project_id,
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
            "deadline": task.deadline,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "created_by": task.created_by,
            "assigned_to": task.assigned_to,
            "is_archived": task.is_archived,
            "difficulty": task.difficulty if task.difficulty else 0
        }

    # ==========================================================
    # Массовые операции
    # ==========================================================

    def move_all_tasks_to_column(self, from_column_id: int, to_column_id: int) -> int:
        """Перемещает все задачи из одной колонки в другую"""
        stmt = update(Task).where(
            Task.column_id == from_column_id
        ).values(
            column_id=to_column_id,
            updated_at=datetime.now()
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def reorder_column_tasks(self, column_id: int, task_order: List[int]) -> bool:
        """
        Переупорядочивает задачи в колонке согласно переданному порядку.
        task_order - список ID задач в правильном порядке
        """
        try:
            for idx, task_id in enumerate(task_order):
                task = self.session.get(Task, task_id)
                if task and task.column_id == column_id:
                    task.position = idx + 1
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка переупорядочивания задач: {e}")
            return False

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