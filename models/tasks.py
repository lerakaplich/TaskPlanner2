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
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .employees import Base


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
    assigned_to: Mapped[Optional[int]]
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

    # Relationships
    column: Mapped[Optional["BoardColumn"]] = relationship(back_populates="tasks")
    tags: Mapped[List["TaskTag"]] = relationship(back_populates="task", cascade="all, delete-orphan")

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
    def efficiency_factor(self) -> float:
        """Коэффициент эффективности (для КПД)"""
        if self.completed_at and self.created_at:
            planned_days = (self.deadline - self.created_at).days if self.deadline else 1
            actual_days = (self.completed_at - self.created_at).days
            if actual_days <= 0:
                actual_days = 0.5
            if planned_days <= 0:
                planned_days = 1
            return planned_days / actual_days
        return 1.0

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

    @property
    def kpd_score(self) -> float:
        """Расчет КПД для задачи (0-100)"""
        if not self.completed:
            return 0.0

        # Базовая формула
        score = (
                self.difficulty *  # Сложность (0-5)
                self.priority_factor *  # Приоритет (0.8-1.5)
                self.efficiency_factor *  # Эффективность по времени
                self.progress_factor  # Готовность (1.0 для выполненных)
        )

        # Нормализация и перевод в 0-100
        normalized = min(100, max(0, score * 20))
        return round(normalized, 2)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#ccab6e")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    tasks: Mapped[List["TaskTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    task: Mapped["Task"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="tasks")