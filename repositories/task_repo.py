# repositories/task_repo.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, update, delete
from datetime import datetime

from models.tasks import Task, TaskTag


class TaskRepo:
    """
    Репозиторий для работы с задачами.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, task_id: int, load_column: bool = True) -> Optional[Task]:
        query = select(Task).where(Task.id == task_id)
        if load_column:
            query = query.options(joinedload(Task.column))
        return self.session.scalar(query)

    def get_by_project_with_project(self, project_id: int, employee_id: int = None) -> List[Task]:
        """Получить задачи проекта с загрузкой связанных данных"""
        query = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == False
        ).options(
            joinedload(Task.column)
        )

        if employee_id:
            query = query.where(Task.assigned_to == employee_id)

        return list(self.session.scalars(query))

    def get_by_column(self, column_id: int) -> List[Task]:
        stmt = select(Task).where(Task.column_id == column_id).order_by(Task.position)
        return list(self.session.scalars(stmt))

    def get_by_project(self, project_id: int, load_column: bool = True,
                       include_archived: bool = False) -> List[Task]:
        """Получить задачи проекта с загрузкой тегов"""
        from sqlalchemy.orm import selectinload

        query = select(Task).where(Task.project_id == project_id)

        if not include_archived:
            query = query.where(Task.is_archived == False)

        if load_column:
            query = query.options(joinedload(Task.column))

        # ДОБАВИТЬ: загружаем теги
        query = query.options(selectinload(Task.tags).selectinload(TaskTag.tag))

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
                Task.is_archived == False,
                Task.completed_at.is_(None)  # Не завершенные
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

    def pause_task(self, task_id: int) -> Optional[Task]:
        """Поставить задачу на паузу"""
        task = self.get_by_id(task_id)
        if task and not task.is_paused and not task.completed:
            task.is_paused = True
            task.paused_at = datetime.now()
            self.session.flush()
            print(f"⏸️ Задача {task_id} поставлена на паузу в {task.paused_at}")
        return task

    def resume_task(self, task_id: int) -> Optional[Task]:
        """Возобновить выполнение задачи"""
        task = self.get_by_id(task_id)
        if task and task.is_paused and task.paused_at:
            # Рассчитываем время паузы
            paused_duration = (datetime.now() - task.paused_at).total_seconds()
            task.total_paused_seconds += int(paused_duration)
            task.is_paused = False
            task.paused_at = None
            self.session.flush()
            print(
                f"▶️ Задача {task_id} возобновлена. Время паузы: {paused_duration:.0f} сек. Всего пауз: {task.total_paused_seconds} сек.")
        return task

    def get_effective_work_seconds(self, task_id: int) -> float:
        """Получить эффективное время работы (без учёта пауз)"""
        task = self.get_by_id(task_id)
        if not task or not task.started_at:
            return 0.0

        total_seconds = (datetime.now() - task.started_at).total_seconds()
        effective_seconds = total_seconds - task.total_paused_seconds

        # Если задача на паузе сейчас, вычитаем текущую паузу
        if task.is_paused and task.paused_at:
            current_pause = (datetime.now() - task.paused_at).total_seconds()
            effective_seconds -= current_pause

        return max(0, effective_seconds)

    def update_progress(self, task_id: int, progress_percent: float) -> Optional[Task]:
        """Обновить прогресс выполнения задачи (0-100)"""
        print(f"\n🔍 [DEBUG] task_repo.update_progress: начало")
        print(f"   - task_id: {task_id}")
        print(f"   - progress_percent: {progress_percent}")

        if not 0 <= progress_percent <= 100:
            raise ValueError("Progress percent must be between 0 and 100")

        task = self.get_by_id(task_id)
        if task:
            old_progress = task.progress_percent
            print(f"   - найдена задача: {task.title}")
            print(f"   - старый прогресс: {old_progress}%")

            task.progress_percent = progress_percent

            # Если прогресс 100% и нет даты завершения, устанавливаем
            if progress_percent >= 100 and not task.completed_at:
                task.completed_at = datetime.now()
                print(f"   - установлена дата завершения: {task.completed_at}")
            # Если прогресс меньше 100% и есть дата завершения, убираем
            elif progress_percent < 100 and task.completed_at:
                task.completed_at = None
                print(f"   - сброшена дата завершения")

            self.session.flush()
            print(f"   - изменения сохранены в БД")
        else:
            print(f"   - ❌ задача НЕ найдена!")

        print(f"🔍 [DEBUG] task_repo.update_progress: конец, возвращаем {task}\n")
        return task

    def start_task(self, task_id: int) -> Optional[Task]:
        """Начать выполнение задачи (установить started_at)"""
        task = self.get_by_id(task_id)
        if task and not task.started_at:
            task.started_at = datetime.now()
            self.session.flush()
        return task

    def complete_task(self, task_id: int, actual_hours: float = None) -> Optional[Task]:
        """Завершить задачу"""
        task = self.get_by_id(task_id)
        if task and not task.completed_at:
            task.completed_at = datetime.now()
            task.progress_percent = 100.0

            if actual_hours is not None:
                task.actual_hours = actual_hours
            elif task.started_at:
                # Рассчитываем фактические часы если не указаны
                task.actual_hours = (datetime.now() - task.started_at).total_seconds() / 3600

            self.session.flush()
        return task

    def update_actual_hours(self, task_id: int, actual_hours: float) -> Optional[Task]:
        """Обновить фактические затраченные часы"""
        task = self.get_by_id(task_id)
        if task:
            task.actual_hours = actual_hours
            self.session.flush()
        return task

    def create(self, **kwargs) -> Task:
        """Создать новую задачу"""
        if 'position' not in kwargs:
            max_pos = self.session.scalar(
                select(func.max(Task.position)).where(Task.column_id == kwargs.get('column_id'))
            )
            kwargs['position'] = (max_pos or 0) + 1

        if 'difficulty' not in kwargs:
            kwargs['difficulty'] = 0.0

        if 'progress_percent' not in kwargs:
            kwargs['progress_percent'] = 0.0

        if 'actual_hours' not in kwargs:
            kwargs['actual_hours'] = 0.0

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
            # Специальная обработка для прогресса
            if 'progress_percent' in kwargs:
                progress = kwargs.pop('progress_percent')
                if 0 <= progress <= 100:
                    task.progress_percent = progress

                    # Автоматическое завершение при 100%
                    if progress >= 100 and not task.completed_at:
                        task.completed_at = datetime.now()
                    elif progress < 100 and task.completed_at:
                        task.completed_at = None

            # Обновляем остальные поля
            allowed_fields = [
                'column_id', 'title', 'description', 'position', 'priority',
                'deadline', 'assigned_to', 'difficulty', 'started_at',
                'completed_at', 'actual_hours', 'is_archived', 'archived_at'
            ]

            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
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
    # Статистика и аналитика
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

        done_columns = select(BoardColumn.id).where(
            BoardColumn.project_id == project_id,
            BoardColumn.is_done_column == True
        ).subquery()

        stmt = select(func.count(Task.id)).where(
            and_(
                Task.project_id == project_id,
                Task.deadline < func.now(),
                Task.is_archived == False,
                Task.completed_at.is_(None),  # Не завершены
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
            if task.completed_at or task.column_id in done_columns:
                completed += 1
            else:
                active += 1

        return {"active": active, "completed": completed}

    # =====================================================
    # НОВАЯ СТАТИСТИКА ПО КПД
    # =====================================================

    def get_tasks_with_kpd(self, employee_id: int = None) -> List[Dict[str, Any]]:
        """Получить задачи с рассчитанным КПД"""
        query = select(Task).where(Task.completed_at.isnot(None))
        if employee_id:
            query = query.where(Task.assigned_to == employee_id)

        tasks = list(self.session.scalars(query))
        return [
            {
                "id": t.id,
                "title": t.title,
                "kpd_score": t.kpd_score,
                "difficulty": t.difficulty,
                "priority": t.priority.value,
                "efficiency_factor": t.efficiency_factor,
                "completed_at": t.completed_at,
                "deadline": t.deadline
            }
            for t in tasks
        ]

    def get_average_kpd_by_project(self, project_id: int) -> float:
        """Средний КПД по проекту"""
        completed_tasks = self.session.scalars(
            select(Task).where(
                Task.project_id == project_id,
                Task.completed_at.isnot(None),
                Task.is_archived == False
            )
        ).all()

        if not completed_tasks:
            return 0.0

        kpds = [t.kpd_score for t in completed_tasks if t.kpd_score > 0]
        return sum(kpds) / len(kpds) if kpds else 0.0

    def get_tasks_by_kpd_range(self, min_kpd: float = 0, max_kpd: float = 100) -> List[Task]:
        """Получить задачи с КПД в заданном диапазоне"""
        tasks = self.session.scalars(
            select(Task).where(
                Task.completed_at.isnot(None),
                Task.is_archived == False
            )
        ).all()

        return [t for t in tasks if min_kpd <= t.kpd_score <= max_kpd]