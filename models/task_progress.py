# models/task_progress.py

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .employees import Base


class TaskProgress(Base):
    """Прогресс выполнения задачи"""
    __tablename__ = "task_progress"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), unique=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100%
    updated_by: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)