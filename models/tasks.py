# models/tasks.py

import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Enum,
    Boolean,
    Float, Integer, Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .employees import Base
from .projects import BoardColumn


class TaskPriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatusEnum(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    cancelled = "cancelled"


class TaskDependency(Base):
    """Модель связей между задачами для диаграммы Ганта"""
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True)
    predecessor_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    successor_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    lag = Column(Integer, default=0)  # Задержка в днях
    type = Column(String(2), default="FS")  # FS, FF, SS, SF

    # 👇 ПРАВИЛЬНЫЕ ОТНОШЕНИЯ
    predecessor = relationship(
        "Task",
        foreign_keys=[predecessor_id],
        back_populates="dependencies_as_predecessor"
    )
    successor = relationship(
        "Task",
        foreign_keys=[successor_id],
        back_populates="dependencies_as_successor"
    )

class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)  # <-- Убираем ForeignKey
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    task: Mapped["Task"] = relationship(back_populates="assignees")

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    column_id: Mapped[Optional[int]] = mapped_column(ForeignKey("board_columns.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]]
    position: Mapped[int]
    priority: Mapped[TaskPriorityEnum] = mapped_column(
        Enum(TaskPriorityEnum, name="task_priority"),
        default=TaskPriorityEnum.medium
    )
    deadline: Mapped[Optional[datetime]]
    created_by: Mapped[Optional[int]]
    assigned_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    assignees: Mapped[List["TaskAssignee"]] = relationship(
        "TaskAssignee",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin"
        # confirm_deleted_rows=False  # <-- УДАЛИТЕ эту строку
    )
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)

    # Новые поля для КПД и прогресса
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100%
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0)  # Фактические часы

    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_paused_seconds: Mapped[int] = mapped_column(Integer, default=0)  # Общее время пауз в секундах

    # Relationships
    column: Mapped[Optional["BoardColumn"]] = relationship(back_populates="tasks")
    tags: Mapped[List["TaskTag"]] = relationship(
        "TaskTag",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin"
        # confirm_deleted_rows=False  # <-- УДАЛИТЕ эту строку
    )

    # Связи как предшественник
    dependencies_as_predecessor = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.predecessor_id",
        back_populates="predecessor",
        cascade="all, delete-orphan"
    )
    # Связи как последователь
    dependencies_as_successor = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.successor_id",
        back_populates="successor",
        cascade="all, delete-orphan"
    )

    @property
    def effective_work_seconds(self) -> float:
        """
        Возвращает эффективное время работы над задачей (без учёта пауз) в секундах.
        Если задача ещё не начата или не завершена, возвращает 0.
        """
        if not self.started_at:
            return 0.0

        end_time = self.completed_at or datetime.now()
        total_seconds = (end_time - self.started_at).total_seconds()

        # Вычитаем общее время пауз
        effective_seconds = total_seconds - self.total_paused_seconds

        # Если задача на паузе сейчас, вычитаем текущую паузу
        if self.is_paused and self.paused_at:
            current_pause = (datetime.now() - self.paused_at).total_seconds()
            effective_seconds -= current_pause

        return max(0, effective_seconds)

    @property
    def effective_work_hours(self) -> float:
        """Эффективное время работы в часах"""
        return self.effective_work_seconds / 3600.0

    @property
    def actual_work_days(self) -> float:
        """Эффективное время работы в днях (8-часовой рабочий день)"""
        return self.effective_work_hours / 8.0

    @property
    def efficiency_factor(self) -> float:
        """
        Коэффициент эффективности с учётом пауз.
        Сравниваем плановое время (от создания до дедлайна) с эффективным временем выполнения.
        """
        if not self.completed_at or not self.created_at:
            return 1.0

        # Плановое время в днях (от создания до дедлайна)
        if self.deadline:
            planned_days = (self.deadline - self.created_at).days
        else:
            # Если дедлайн не задан, используем среднее 7 дней
            planned_days = 7

        if planned_days <= 0:
            planned_days = 1

        # Эффективное время выполнения в днях
        actual_days = self.actual_work_days
        if actual_days <= 0:
            actual_days = 0.5  # Минимальное время

        # Чем меньше эффективное время относительно планового, тем выше коэффициент
        # Но не больше 2.0 (чтобы не было перекоса)
        factor = min(planned_days / actual_days, 2.0)
        return factor

    @property
    def kpd_score(self) -> float:
        """Расчет КПД для задачи с учётом пауз (0-100)"""
        if not self.completed:
            return 0.0

        # Базовые компоненты
        difficulty_factor = self.difficulty / 5.0  # 0-1, где 5⭐ = 1.0
        priority_factor = self.priority_factor  # 0.8-1.5
        efficiency = self.efficiency_factor  # 0.5-2.0

        # Прогресс всегда 100% для завершённых задач
        progress_factor = 1.0

        # Итоговая формула
        raw_score = (difficulty_factor * 0.4 + efficiency * 0.6) * 100
        raw_score *= priority_factor

        # Нормализация и ограничение
        normalized = min(100, max(0, raw_score))
        return round(normalized, 2)

    @property
    def status(self) -> Optional[str]:
        if self.column:
            return self.column.name
        return None

    @property
    def completed(self) -> bool:
        return self.completed_at is not None or (self.column and self.column.is_done_column)

    @property
    def planned_hours(self) -> float:
        """Плановые часы на основе сложности"""
        # difficulty: 1 звезда = 2 часа, 5 звезд = 10 часов
        return self.difficulty * 2

    @property
    def is_overdue(self) -> bool:
        """Просрочена ли задача"""
        if not self.deadline or self.completed:
            return False
        return datetime.now() > self.deadline

    @property
    def priority_factor(self) -> float:
        """Коэффициент приоритета"""
        factors = {
            TaskPriorityEnum.critical: 1.5,
            TaskPriorityEnum.high: 1.2,
            TaskPriorityEnum.medium: 1.0,
            TaskPriorityEnum.low: 0.8,
        }
        return factors.get(self.priority, 1.0)

    @property
    def progress_factor(self) -> float:
        """Коэффициент готовности"""
        return self.progress_percent / 100.0

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#ccab6e")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    tasks: Mapped[List["TaskTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    task: Mapped["Task"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="tasks")