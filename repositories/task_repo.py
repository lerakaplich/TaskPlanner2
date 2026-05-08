# repositories/task_repo.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, update, delete
from datetime import datetime

from models.tasks import Task


class TaskRepo:
    """
    Репозиторий для работы с задачами.
    """

    def __init__(self, session: Session):
        self.session = session

    # =====================================================
    # CRUD операции с задачами
    # =====================================================

    def get_by_id(self, task_id: int, load_column: bool = True) -> Optional[Task]:
        query = select(Task).where(Task.id == task_id)
        if load_column:
            query = query.options(joinedload(Task.column))
        return self.session.scalar(query)

    def get_by_column(self, column_id: int) -> List[Task]:
        stmt = select(Task).where(Task.column_id == column_id).order_by(Task.position)
        return list(self.session.scalars(stmt))

    def get_by_project(self, project_id: int, load_column: bool = True,
                       include_archived: bool = False) -> List[Task]:
        """Получить задачи проекта"""
        query = select(Task).where(Task.project_id == project_id)

        if not include_archived:
            query = query.where(Task.is_archived == False)

        if load_column:
            query = query.options(joinedload(Task.column))

        return list(self.session.scalars(query))

    def get_by_assignee(self, employee_id: int, include_archived: bool = False) -> List[Task]:
        """Получить задачи, назначенные на сотрудника"""
        query = select(Task).where(Task.assigned_to == employee_id)
        if not include_archived:
            query = query.where(Task.is_archived == False)
        return list(self.session.scalars(query))

    def get_by_creator(self, employee_id: int, include_archived: bool = False) -> List[Task]:
        """Получить задачи, созданные сотрудником"""
        query = select(Task).where(Task.created_by == employee_id)
        if not include_archived:
            query = query.where(Task.is_archived == False)
        return list(self.session.scalars(query))

    def get_overdue_tasks(self, project_id: int = None) -> List[Task]:
        """Получить просроченные задачи"""
        query = select(Task).where(
            and_(
                Task.deadline < func.now(),
                Task.is_archived == False
            )
        )
        if project_id:
            query = query.where(Task.project_id == project_id)
        return list(self.session.scalars(query))

    def get_tasks_for_kanban(self, project_id: int) -> List[Task]:
        """Получить задачи для канбан-доски (с колонками)"""
        stmt = (
            select(Task)
            .where(Task.project_id == project_id, Task.is_archived == False)
            .options(joinedload(Task.column))
            .order_by(Task.position)
        )
        return list(self.session.scalars(stmt))

    def create(self, **kwargs) -> Task:
        """Создать новую задачу"""
        if 'position' not in kwargs:
            max_pos = self.session.scalar(
                select(func.max(Task.position)).where(Task.column_id == kwargs.get('column_id'))
            )
            kwargs['position'] = (max_pos or 0) + 1

        if 'difficulty' not in kwargs:
            kwargs['difficulty'] = 0.0

        required_fields = ['project_id', 'title', 'position']
        for field in required_fields:
            if field not in kwargs:
                raise ValueError(f"Missing required field: {field}")

        task = Task(**kwargs)
        self.session.add(task)
        self.session.flush()
        return task

    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        """Обновить задачу"""
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.session.flush()
        return task

    def delete(self, task_id: int) -> bool:
        """Удалить задачу (мягкое удаление)"""
        task = self.get_by_id(task_id)
        if task:
            task.is_archived = True
            task.archived_at = datetime.now()
            self.session.flush()
            return True
        return False

    def hard_delete(self, task_id: int) -> bool:
        """Полное удаление задачи из БД"""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()
            return True
        return False

    def restore(self, task_id: int) -> bool:
        """Восстановить задачу из архива"""
        task = self.get_by_id(task_id)
        if task:
            task.is_archived = False
            task.archived_at = None
            self.session.flush()
            return True
        return False

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

    def reorder_in_column(self, column_id: int, task_ids: List[int]):
        """Переупорядочить задачи в колонке"""
        for position, task_id in enumerate(task_ids):
            stmt = (
                update(Task)
                .where(Task.id == task_id, Task.column_id == column_id)
                .values(position=position)
            )
            self.session.execute(stmt)

    # =====================================================
    # Статистика
    # =====================================================

    def get_task_count_by_column(self, project_id: int) -> Dict[str, int]:
        """Получить количество задач по колонкам проекта"""
        from models.projects import BoardColumn

        columns = self.session.scalars(
            select(BoardColumn).where(BoardColumn.project_id == project_id)
        ).all()

        result = {col.name: 0 for col in columns}

        stmt = (
            select(BoardColumn.name, func.count(Task.id))
            .join(Task, BoardColumn.id == Task.column_id, isouter=True)
            .where(BoardColumn.project_id == project_id, Task.is_archived == False)
            .group_by(BoardColumn.name)
        )
        for col_name, count in self.session.execute(stmt):
            result[col_name] = count

        return result

    def get_total_task_count(self, project_id: int, include_archived: bool = False) -> int:
        """Общее количество задач в проекте"""
        stmt = select(func.count(Task.id)).where(Task.project_id == project_id)
        if not include_archived:
            stmt = stmt.where(Task.is_archived == False)
        return self.session.scalar(stmt) or 0

    def get_completed_task_count(self, project_id: int) -> int:
        """Количество выполненных задач в проекте"""
        from models.projects import BoardColumn

        # Используем select из SQLAlchemy (уже импортирован в начале файла)
        done_columns = select(BoardColumn.id).where(
            BoardColumn.project_id == project_id,
            BoardColumn.is_done_column == True
        ).subquery()

        stmt = select(func.count(Task.id)).where(
            Task.project_id == project_id,
            Task.is_archived == False,
            Task.column_id.in_(select(done_columns))
        )
        return self.session.scalar(stmt) or 0

    def get_overdue_count(self, project_id: int) -> int:
        """Количество просроченных задач в проекте"""
        from models.projects import BoardColumn

        # Используем select из SQLAlchemy (уже импортирован в начале файла)
        done_columns = select(BoardColumn.id).where(
            BoardColumn.project_id == project_id,
            BoardColumn.is_done_column == True
        ).subquery()

        stmt = select(func.count(Task.id)).where(
            and_(
                Task.project_id == project_id,
                Task.deadline < func.now(),
                Task.is_archived == False,
                Task.column_id.not_in(select(done_columns))
            )
        )
        return self.session.scalar(stmt) or 0

    def get_employee_task_stats(self, employee_id: int, project_id: int = None) -> Dict[str, int]:
        """Получить статистику по задачам сотрудника"""
        from models.projects import BoardColumn

        query = select(Task).where(Task.assigned_to == employee_id, Task.is_archived == False)
        if project_id:
            query = query.where(Task.project_id == project_id)

        tasks = list(self.session.scalars(query))

        done_columns = set()
        if project_id:
            done_cols = self.session.scalars(
                select(BoardColumn.id).where(
                    BoardColumn.project_id == project_id,
                    BoardColumn.is_done_column == True
                )
            ).all()
            done_columns = set(done_cols)

        active = 0
        completed = 0
        for task in tasks:
            if task.column_id in done_columns:
                completed += 1
            else:
                active += 1

        return {"active": active, "completed": completed}