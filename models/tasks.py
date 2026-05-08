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


# =========================
# Задачи
# =========================
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    column_id: Mapped[Optional[int]] = mapped_column(ForeignKey("board_columns.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]]
    position: Mapped[int]
    priority: Mapped[TaskPriorityEnum] = mapped_column(Enum(TaskPriorityEnum, name="task_priority"),
                                                       default=TaskPriorityEnum.medium)
    deadline: Mapped[Optional[datetime]]
    created_by: Mapped[Optional[int]]
    assigned_to: Mapped[Optional[int]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)

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
        if self.column and self.column.is_done_column:
            return True
        return False


# =========================
# Теги
# =========================
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