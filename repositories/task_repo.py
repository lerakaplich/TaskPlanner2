# repositories/task_repo.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, update, delete
from datetime import datetime

from models.tasks import Task, Tag, TaskTag
from models.projects import BoardColumn
from models.employees import ExternalEmployee


class TaskRepo:
    """
    Универсальный репозиторий для работы с задачами.
    Используется как для "Моих задач", так и для "Задач других сотрудников".
    """

    def __init__(self, session: Session):
        self.session = session

    # =====================================================
    # CRUD операции с задачами
    # =====================================================

    def get_by_id(self, task_id: int, load_column: bool = True) -> Optional[Task]:
        """
        Получить задачу по ID.

        Args:
            task_id: ID задачи
            load_column: загружать ли связанную колонку
        """
        query = select(Task).where(Task.id == task_id)
        if load_column:
            query = query.options(joinedload(Task.column))
        return self.session.scalar(query)

    # repositories/task_repo.py

    def get_by_column(self, column_id: int) -> List[Task]:
        """Получить все задачи в колонке"""
        stmt = select(Task).where(Task.column_id == column_id)
        return list(self.session.scalars(stmt))

    def get_by_project(self, project_id: int, load_column: bool = True) -> List[Task]:
        """
        Получить все задачи проекта.

        Args:
            project_id: ID проекта
            load_column: загружать ли связанные колонки
        """
        query = select(Task).where(Task.project_id == project_id)
        if load_column:
            query = query.options(joinedload(Task.column))
        return list(self.session.scalars(query))

    def get_tasks_for_kanban(self, project_id: int) -> List[Task]:
        """
        Получить все задачи проекта для отображения на канбан-доске.
        """
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .options(joinedload(Task.column))
            .order_by(Task.position)
        )
        return list(self.session.scalars(stmt))

    def create(self, **kwargs) -> Task:
        """
        Создать новую задачу.

        Автоматически устанавливает позицию, если не указана.
        """
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

    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        """
        Обновить задачу.

        Args:
            task_id: ID задачи
            **kwargs: поля для обновления
        """
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.session.flush()
        return task

    def delete(self, task_id: int):
        """Удалить задачу."""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()

    # =====================================================
    # Работа с позициями и перемещением
    # =====================================================

    def update_position(self, task_id: int, new_position: int):
        """Обновить позицию задачи."""
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(position=new_position)
        )
        self.session.execute(stmt)

    def move_to_column(self, task_id: int, column_id: int):
        """Переместить задачу в другую колонку."""
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(column_id=column_id)
        )
        self.session.execute(stmt)

    # =====================================================
    # Работа с колонками
    # =====================================================

    def get_board_columns(self, project_id: int) -> List[BoardColumn]:
        """Получить все колонки доски для проекта."""
        print(f"\n=== ОТЛАДКА: get_board_columns для project_id={project_id} ===")

        stmt = (
            select(BoardColumn)
            .where(BoardColumn.project_id == project_id)
            .order_by(BoardColumn.position)
        )

        columns = list(self.session.scalars(stmt))
        print(f"Найдено колонок: {len(columns)}")

        for col in columns:
            print(f"  - Колонка: id={col.id}, name='{col.name}', color='{col.color}'")

        return columns

    def get_column_by_name(self, project_id: int, column_name: str) -> Optional[BoardColumn]:
        """Получить колонку по названию."""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id,
            BoardColumn.name == column_name
        )
        return self.session.scalar(stmt)

    def get_first_column(self, project_id: int) -> Optional[BoardColumn]:
        """Получить первую колонку проекта."""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return self.session.scalar(stmt)

    # =====================================================
    # Статистика
    # =====================================================

    def get_task_count_by_column(self, project_id: int) -> Dict[str, int]:
        """
        Возвращает словарь с количеством задач в каждой колонке.
        """
        columns = self.session.scalars(
            select(BoardColumn).where(BoardColumn.project_id == project_id)
        ).all()

        result = {col.name: 0 for col in columns}

        stmt = (
            select(BoardColumn.name, func.count(Task.id))
            .join(Task, BoardColumn.id == Task.column_id, isouter=True)
            .where(BoardColumn.project_id == project_id)
            .group_by(BoardColumn.name)
        )
        for col_name, count in self.session.execute(stmt):
            result[col_name] = count

        return result

    def get_total_task_count(self, project_id: int) -> int:
        """Получить общее количество задач в проекте."""
        stmt = select(func.count(Task.id)).where(Task.project_id == project_id)
        return self.session.scalar(stmt) or 0

    def get_overdue_count(self, project_id: int) -> int:
        """
        Возвращает количество просроченных задач в проекте.
        Просроченными считаются задачи с дедлайном раньше текущей даты,
        которые не находятся в колонке "Выполнено".
        """
        # Получаем ID колонок, которые считаются выполненными
        done_columns_subquery = (
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
                Task.column_id.not_in(select(done_columns_subquery))
            )
        )
        return self.session.scalar(stmt) or 0

    # =====================================================
    # Работа с сотрудниками (внешняя БД)
    # =====================================================

    def get_employee_by_id(self, employee_id: int) -> Optional[ExternalEmployee]:
        """Получить сотрудника по ID."""
        stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
        return self.session.scalar(stmt)

    def get_employee_name_by_id(self, employee_id: int) -> Optional[str]:
        """Получить ФИО сотрудника."""
        emp = self.get_employee_by_id(employee_id)
        if emp:
            parts = [emp.last_name, emp.first_name]
            if emp.middle_name:
                parts.append(emp.middle_name)
            return " ".join(parts)
        return None

    def get_all_employees(self) -> List[Dict[str, Any]]:
        """
        Получить список всех сотрудников для выпадающего списка.
        """
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

    # =====================================================
    # Работа с тегами
    # =====================================================

    def create_tag(self, project_id: int, name: str) -> Tag:
        """Создать новый тег."""
        tag = Tag(project_id=project_id, name=name)
        self.session.add(tag)
        return tag

    def add_tag_to_task(self, task_id: int, tag_id: int):
        """Добавить тег к задаче."""
        rel = TaskTag(task_id=task_id, tag_id=tag_id)
        self.session.add(rel)

    def remove_tag_from_task(self, task_id: int, tag_id: int):
        """Удалить тег у задачи."""
        stmt = delete(TaskTag).where(
            TaskTag.task_id == task_id,
            TaskTag.tag_id == tag_id
        )
        self.session.execute(stmt)

    def get_task_tags(self, task_id: int) -> List[Tag]:
        """Получить все теги задачи."""
        stmt = (
            select(Tag)
            .join(TaskTag, Tag.id == TaskTag.tag_id)
            .where(TaskTag.task_id == task_id)
        )
        return list(self.session.scalars(stmt))