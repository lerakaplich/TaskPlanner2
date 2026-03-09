# repositories/other_task_repo.py

from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_
from datetime import datetime

# Импортируем модели из БД проектов
from models.tasks import Task
# ИСПРАВЛЕНИЕ: Импортируем BoardColumn из projects.py
from models.projects import BoardColumn
# Импортируем DTO
from models.schemas.tasks_dto import TaskPriority, TaskCardDTO
# Импортируем модель сотрудников из внешней БД
from models.employees import ExternalEmployee


class OtherTaskRepo:
    """Репозиторий для задач на странице 'Задачи других сотрудников'."""

    def __init__(self, session: Session):
        self.session = session

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Получить задачу по ID с загрузкой связанной колонки."""
        stmt = select(Task).where(Task.id == task_id).options(joinedload(Task.column))
        return self.session.scalar(stmt)

    def get_tasks_for_kanban(self, project_id: int) -> List[Task]:
        """Получить все задачи проекта для отображения на канбан-доске."""
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .options(joinedload(Task.column))
            .order_by(Task.position)
        )
        return list(self.session.scalars(stmt))

    # repositories/other_task_repo.py

    def create_task(self, **kwargs) -> Task:
        """Создать новую задачу в БД."""
        print("\n=== ОТЛАДКА: создание задачи в репозитории ===")
        print(f"Полученные параметры: {kwargs}")

        # Проверяем типы данных
        for key, value in kwargs.items():
            print(f"  {key}: {value} (тип: {type(value)})")

        # Убедимся, что position установлена
        if 'position' not in kwargs:
            max_pos = self.session.scalar(
                select(func.max(Task.position)).where(Task.column_id == kwargs.get('column_id'))
            )
            kwargs['position'] = (max_pos or 0) + 1
            print(f"Установлена позиция: {kwargs['position']}")

        try:
            # Проверяем обязательные поля
            required_fields = ['project_id', 'title', 'position']
            for field in required_fields:
                if field not in kwargs:
                    print(f"❌ Отсутствует обязательное поле: {field}")
                    raise ValueError(f"Missing required field: {field}")

            print("✅ Все обязательные поля присутствуют")

            task = Task(**kwargs)
            print(f"✅ Создан объект Task: {task}")
            print(f"  ID: {task.id}")
            print(f"  title: {task.title}")
            print(f"  project_id: {task.project_id}")
            print(f"  column_id: {task.column_id}")
            print(f"  priority: {task.priority}")

            self.session.add(task)
            print("✅ Task добавлен в сессию")

            self.session.flush()
            print(f"✅ Flush выполнен, ID задачи: {task.id}")

            return task

        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            raise

    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Обновить задачу."""
        task = self.get_task_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.session.flush()
        return task

    def delete_task(self, task_id: int):
        """Удалить задачу."""
        task = self.get_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()

    def move_task_to_column(self, task_id: int, new_column_id: int):
        """Переместить задачу в другую колонку."""
        task = self.get_task_by_id(task_id)
        if task:
            task.column_id = new_column_id
            self.session.flush()

    # ========== Методы для статистики ==========
    def get_task_count_by_column(self, project_id: int) -> Dict[str, int]:
        """Возвращает словарь с количеством задач в каждой колонке."""
        columns = self.session.scalars(
            select(BoardColumn).where(BoardColumn.project_id == project_id)
        ).all()

        result = {col.name: 0 for col in columns}
        result['total'] = 0

        stmt = (
            select(BoardColumn.name, func.count(Task.id))
            .join(Task, BoardColumn.id == Task.column_id, isouter=True)
            .where(BoardColumn.project_id == project_id)
            .group_by(BoardColumn.name)
        )
        for col_name, count in self.session.execute(stmt):
            result[col_name] = count
            result['total'] += count

        return result

    def get_overdue_count(self, project_id: int) -> int:
        """Возвращает количество просроченных задач в проекте."""
        subquery = (
            select(BoardColumn.id)
            .where(
                and_(
                    BoardColumn.project_id == project_id,
                    BoardColumn.is_done_column == True
                )
            )
            .subquery()
        )

        stmt = select(func.count(Task.id)).where(
            and_(
                Task.project_id == project_id,
                Task.deadline < func.now(),
                Task.column_id.not_in(select(subquery))
            )
        )
        return self.session.scalar(stmt) or 0

    # ========== Методы для работы с сотрудниками ==========
    def get_employee_name_by_id(self, employee_id: int) -> Optional[str]:
        """Получить ФИО сотрудника из внешней БД."""
        stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
        emp = self.session.scalar(stmt)
        if emp:
            parts = [emp.last_name, emp.first_name]
            if emp.middle_name:
                parts.append(emp.middle_name)
            return " ".join(parts)
        return None

    def get_board_columns(self, project_id: int) -> List[BoardColumn]:
        """Получить все колонки доски для проекта."""
        stmt = (
            select(BoardColumn)
            .where(BoardColumn.project_id == project_id)
            .order_by(BoardColumn.position)
        )
        return list(self.session.scalars(stmt))

    def get_all_employees(self) -> List[Dict]:
        """Получить список всех сотрудников для выпадающего списка."""
        stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
        employees = self.session.scalars(stmt).all()
        return [
            {
                "id": e.id,
                "last_name": e.last_name,
                "first_name": e.first_name,
                "middle_name": e.middle_name
            }
            for e in employees
        ]