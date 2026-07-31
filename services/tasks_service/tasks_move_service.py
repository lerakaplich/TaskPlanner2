# services/tasks_service/tasks_move_service.py

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from models.projects import BoardColumn
from models.tasks import Task


class TasksMoveService:
    """Сервис для перемещения и переупорядочивания задач (включая канбан-логику)"""

    def __init__(self, db_session: Session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.current_user = current_user
        self.mode = mode
        self._task_to_dict = None

    def set_task_converter(self, converter_func):
        """Установка функции конвертации задачи в словарь"""
        self._task_to_dict = converter_func

    # services/tasks_service/tasks_move_service.py

    def move_task(self, task_id: int, new_column_name: str) -> Optional[Tuple]:
        """Переместить задачу в другую колонку по имени"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        old_column_name = task.column.name if task.column else None
        new_column = self._get_column_by_name(new_column_name, task.project_id)

        if not new_column or task.column_id == new_column.id:
            return None

        can_move, error = self.validate_move(task_id, new_column.id)
        if not can_move:
            print(f"❌ Невозможно переместить задачу: {error}")
            return None

        # Обновляем статус и прогресс
        if new_column.is_done_column:
            task.progress_percent = 100.0
            task.completed_at = datetime.now()
            # ❌ НЕ ИСПОЛЬЗУЙТЕ: task.completed = True

        task.column_id = new_column.id
        task.updated_at = datetime.now()
        self.db_session.commit()

        # === СОХРАНЯЕМ ДАННЫЕ ===
        try:
            from services.tasks_service.task_data_collector import get_task_data_collector
            collector = get_task_data_collector()
            task_dict = self._task_to_dict(task) if self._task_to_dict else None
            if task_dict:
                collector.save_task_data(
                    task_data=task_dict,
                    user_id=task.created_by or 0,
                    project_id=task.project_id
                )
        except Exception as e:
            print(f"⚠️ Ошибка сохранения данных: {e}")

        return old_column_name, self._task_to_dict(task) if self._task_to_dict else None

    def move_task_to_column(self, task_id: int, target_column_id: int) -> Optional[Dict]:
        """Переместить задачу в колонку по ID"""
        task = self.repo.get_by_id(task_id)
        if not task:
            print(f"❌ move_task_to_column: Задача {task_id} не найдена")
            return None

        print(f"🔧 move_task_to_column: задача={task_id}, target_col={target_column_id}, current_col={task.column_id}")

        if task.column_id == target_column_id:
            print("ℹ️ Задача уже в целевой колонке")
            return None

        target_column = self.db_session.get(BoardColumn, target_column_id)
        if not target_column:
            print(f"❌ Колонка {target_column_id} не найдена")
            return None

        can_move, error = self.validate_move(task_id, target_column_id)
        if not can_move:
            print(f"❌ Валидация не прошла: {error}")
            return None

        # ===== ЛОГИКА ДЛЯ ПРОГРЕССА ПРИ ПЕРЕМЕЩЕНИИ =====
        if target_column.is_done_column:
            print(f"✅ Перемещение в Done колонку '{target_column.name}' - устанавливаем прогресс 100%")
            task.progress_percent = 100.0
            task.completed_at = datetime.now()
            # ❌ НЕ ИСПОЛЬЗУЙТЕ: task.completed = True
            print(f"   Прогресс: {task.progress_percent}%")
            print(f"   Дата завершения: {task.completed_at}")
        else:
            print(
                f"📦 Перемещение из колонки '{task.column.name if task.column else 'None'}' в '{target_column.name}' - прогресс не меняется")

        if task.column and task.column.is_done_column and not target_column.is_done_column:
            print(f"⚠️ Перемещение из Done колонки - задача возвращена в работу")
            task.completed_at = None
            # ❌ НЕ ИСПОЛЬЗУЙТЕ: task.completed = False

        task.column_id = target_column_id
        task.updated_at = datetime.now()
        self.db_session.commit()

        # === СОХРАНЯЕМ ДАННЫЕ ДЛЯ ОБУЧЕНИЯ ===
        try:
            from services.tasks_service.task_data_collector import get_task_data_collector
            collector = get_task_data_collector()
            task_dict = self._task_to_dict(task) if self._task_to_dict else None
            if task_dict:
                collector.save_task_data(
                    task_data=task_dict,
                    user_id=task.created_by or 0,
                    project_id=task.project_id
                )
                print(f"📊 Данные задачи {task_id} сохранены для обучения (перемещение)")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения данных при перемещении: {e}")

        # Обновляем КПД сотрудника при любом перемещении
        if task.assigned_to:
            self._update_employee_kpd(task.assigned_to)

        return self._task_to_dict(task) if self._task_to_dict else None

    def _update_employee_kpd(self, employee_id: int) -> None:
        """Обновить КПД сотрудника"""
        try:
            from models.employees import EmployeeData
            employee_data = self.db_session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()
            if employee_data:
                print(f"🔄 Пересчет КПД для сотрудника {employee_id}")
                employee_data.update_kpd(self.db_session)
                self.db_session.commit()
                print(f"   Новый КПД: {employee_data.kpd_rating:.1f}%")
        except Exception as e:
            print(f"⚠️ Ошибка обновления КПД сотрудника {employee_id}: {e}")

    def move_task_to_position(self, task_id: int, target_column_id: int, new_position: int) -> Optional[Dict]:
        """Переместить задачу на указанную позицию"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        can_move, error = self.validate_move(task_id, target_column_id)
        if not can_move:
            print(f"❌ Невозможно переместить задачу: {error}")
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

    def validate_move(self, task_id: int, target_column_id: int) -> Tuple[bool, str]:
        """Проверить возможность перемещения задачи"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return False, "Задача не найдена"

        target_column = self.db_session.get(BoardColumn, target_column_id)
        if not target_column:
            return False, "Целевая колонка не найдена"

        if task.column_id == target_column_id:
            return False, "Задача уже в этой колонке"

        # КОММЕНТИРУЕМ - пользователь может перемещать любые задачи
        # if task.column and task.column.is_done_column:
        #     return False, "Нельзя переместить выполненную задачу"

        # Проверка для завершающей колонки
        if target_column.is_done_column:
            if not self._can_complete_task(task):
                return False, "Невозможно отметить задачу как выполненную"

        return True, ""

    def can_move_task(self, task_id: int, target_column_id: int) -> bool:
        """Проверяет, можно ли переместить задачу"""
        can_move, _ = self.validate_move(task_id, target_column_id)
        return can_move

    def _can_complete_task(self, task: Task) -> bool:
        """Проверить, можно ли отметить задачу как выполненную"""
        # Здесь можно добавить логику проверки подзадач
        return True

    def move_all_tasks_to_column(self, from_column_id: int, to_column_id: int) -> int:
        """Перемещает все задачи из одной колонки в другую"""
        stmt = update(Task).where(
            Task.column_id == from_column_id
        ).values(
            column_id=to_column_id,
            updated_at=datetime.now()
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount

    def _get_column_by_name(self, column_name: str, project_id: int = None) -> Optional[BoardColumn]:
        """Получить колонку по имени"""
        stmt = select(BoardColumn).where(BoardColumn.name == column_name)
        if project_id:
            stmt = stmt.where(BoardColumn.project_id == project_id)
        return self.db_session.scalar(stmt)

    def get_max_position_in_column(self, column_id: int) -> int:
        """Возвращает максимальную позицию задачи в колонке"""
        result = self.db_session.scalar(
            select(func.max(Task.position)).where(Task.column_id == column_id)
        )
        return result or 0