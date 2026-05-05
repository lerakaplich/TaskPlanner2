# repositories/task_repo.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, update, delete
from datetime import datetime

from database import get_employees_session
from models.tasks import Task, Tag, TaskTag
from models.projects import BoardColumn
from models.employees import Employee


class TaskRepo:
    """
    Универсальный репозиторий для работы с задачами.
    """

    def __init__(self, session: Session):
        self.session = session  # для taskplanner БД
        self.employees_session = get_employees_session()  # ← ОТДЕЛЬНАЯ сессия для employees

    def __del__(self):
        """Закрываем сессию employees при удалении"""
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    # =====================================================
    # CRUD операции с задачами
    # =====================================================

    def get_by_id(self, task_id: int, load_column: bool = True) -> Optional[Task]:
        query = select(Task).where(Task.id == task_id)
        if load_column:
            query = query.options(joinedload(Task.column))
        return self.session.scalar(query)

    def get_by_column(self, column_id: int) -> List[Task]:
        stmt = select(Task).where(Task.column_id == column_id)
        return list(self.session.scalars(stmt))

    def get_by_project(self, project_id: int, load_column: bool = True, include_archived: bool = False) -> List[Task]:
        """Получить задачи проекта

        Args:
            project_id: ID проекта
            load_column: Загружать ли колонку задачи
            include_archived: Включать ли архивированные задачи
        """
        query = select(Task).where(Task.project_id == project_id)

        # Фильтрация по архивированным
        if not include_archived:
            query = query.where(Task.is_archived == False)

        if load_column:
            query = query.options(joinedload(Task.column))

        return list(self.session.scalars(query))

    def hard_delete(self, task_id: int) -> bool:
        """Полное удаление задачи из БД"""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()
            return True
        return False

    def get_tasks_for_kanban(self, project_id: int) -> List[Task]:
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .options(joinedload(Task.column))
            .order_by(Task.position)
        )
        return list(self.session.scalars(stmt))

    def create(self, **kwargs) -> Task:
        print("\n=== ОТЛАДКА: создание задачи в репозитории ===")
        print(f"Полученные параметры: {kwargs}")

        if 'position' not in kwargs:
            max_pos = self.session.scalar(
                select(func.max(Task.position)).where(Task.column_id == kwargs.get('column_id'))
            )
            kwargs['position'] = (max_pos or 0) + 1
            print(f"Установлена позиция: {kwargs['position']}")

        # Устанавливаем сложность по умолчанию, если не указана
        if 'difficulty' not in kwargs:
            kwargs['difficulty'] = 0.0

        try:
            required_fields = ['project_id', 'title', 'position']
            for field in required_fields:
                if field not in kwargs:
                    print(f"❌ Отсутствует обязательное поле: {field}")
                    raise ValueError(f"Missing required field: {field}")

            task = Task(**kwargs)
            self.session.add(task)
            self.session.flush()
            return task

        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            raise

    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.session.flush()
        return task

    def delete(self, task_id: int):
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()

    # =====================================================
    # Работа с позициями и перемещением
    # =====================================================

    def update_position(self, task_id: int, new_position: int):
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(position=new_position)
        )
        self.session.execute(stmt)

    def move_to_column(self, task_id: int, column_id: int):
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
        stmt = (
            select(BoardColumn)
            .where(BoardColumn.project_id == project_id)
            .order_by(BoardColumn.position)
        )
        return list(self.session.scalars(stmt))

    def get_column_by_name(self, project_id: int, column_name: str) -> Optional[BoardColumn]:
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id,
            BoardColumn.name == column_name
        )
        return self.session.scalar(stmt)

    def get_first_column(self, project_id: int) -> Optional[BoardColumn]:
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return self.session.scalar(stmt)

    # =====================================================
    # Статистика
    # =====================================================

    def get_task_count_by_column(self, project_id: int) -> Dict[str, int]:
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
        stmt = select(func.count(Task.id)).where(Task.project_id == project_id)
        return self.session.scalar(stmt) or 0

    def get_overdue_count(self, project_id: int) -> int:
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
    # Работа с сотрудниками - ИСПРАВЛЕНО
    # =====================================================

    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Получает сотрудника из БД employees"""
        stmt = select(Employee).where(Employee.id == employee_id)
        return self.employees_session.scalar(stmt)  # ← используем employees_session

    def get_employee_name_by_id(self, employee_id: int) -> Optional[str]:
        emp = self.get_employee_by_id(employee_id)
        if emp:
            parts = [emp.last_name or "", emp.first_name or ""]
            if emp.middle_name:
                parts.append(emp.middle_name)
            # Убираем пустые части
            name = " ".join([p for p in parts if p])
            return name if name else f"ID:{employee_id}"
        return None

    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Получает всех сотрудников из БД employees"""
        stmt = select(Employee).order_by(Employee.last_name)
        employees = self.employees_session.scalars(stmt).all()  # ← используем employees_session
        return [
            {
                "id": e.id,
                "last_name": e.last_name or "",
                "first_name": e.first_name or "",
                "middle_name": e.middle_name or ""
            }
            for e in employees
        ]

    # =====================================================
    # Работа с тегами
    # =====================================================

    def create_tag(self, project_id: int, name: str) -> Tag:
        tag = Tag(project_id=project_id, name=name)
        self.session.add(tag)
        return tag

    def add_tag_to_task(self, task_id: int, tag_id: int):
        rel = TaskTag(task_id=task_id, tag_id=tag_id)
        self.session.add(rel)

    def remove_tag_from_task(self, task_id: int, tag_id: int):
        stmt = delete(TaskTag).where(
            TaskTag.task_id == task_id,
            TaskTag.tag_id == tag_id
        )
        self.session.execute(stmt)

    def get_task_tags(self, task_id: int) -> List[Tag]:
        stmt = (
            select(Tag)
            .join(TaskTag, Tag.id == TaskTag.tag_id)
            .where(TaskTag.task_id == task_id)
        )
        return list(self.session.scalars(stmt))