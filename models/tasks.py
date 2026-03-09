# models/tasks.py

from datetime import datetime
from typing import Optional, List
import enum

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .employees import Base

# =========================
# Enum из БД
# =========================
class TaskPriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# =========================
# tasks
# =========================
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    column_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("board_columns.id", ondelete="SET NULL")
    )

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]]
    position: Mapped[int]

    priority: Mapped[TaskPriorityEnum] = mapped_column(
        Enum(TaskPriorityEnum, name="task_priority"),
        default=TaskPriorityEnum.medium,
    )

    deadline: Mapped[Optional[datetime]]
    created_by: Mapped[Optional[int]]
    assigned_to: Mapped[Optional[int]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # relationships
    column: Mapped[Optional["BoardColumn"]] = relationship(
        back_populates="tasks"
    )

    tags: Mapped[List["TaskTag"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )

    # Добавляем виртуальные поля для удобства работы в UI
    @property
    def status(self) -> Optional[str]:
        """Возвращает статус задачи на основе связанной колонки."""
        if self.column:
            return self.column.name
        return None

    @property
    def completed(self) -> bool:
        """Возвращает True, если задача находится в 'done' колонке."""
        if self.column and self.column.is_done_column:
            return True
        return False


# =========================
# tags
# =========================
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    name: Mapped[str]

    tasks: Mapped[List["TaskTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan"
    )


# =========================
# task_tags
# =========================
class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    task: Mapped["Task"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="tasks")