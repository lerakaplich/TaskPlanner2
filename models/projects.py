# models/projects.py

from datetime import datetime, time
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .employees import Base


# =========================
# projects
# =========================
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]]
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[Optional[int]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deadline: Mapped[Optional[time]]
    owner: Mapped[int]

    selected_column_ids: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    manager_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # relationships
    columns: Mapped[List["BoardColumn"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )

    members: Mapped[List["EmployeeProject"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )


# =========================
# board_columns (колонки доски проекта)
# =========================
class BoardColumn(Base):
    __tablename__ = "board_columns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#ffffff")  # #ffffff как в дампе
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_done_column: Mapped[bool] = mapped_column(Boolean, default=False)

    # Поля из дампа БД
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="columns")
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="column",
        cascade="all, delete-orphan"
    )


# =========================
# employees_projects
# =========================
class EmployeeProject(Base):
    __tablename__ = "employees_projects"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("public.employees.id", ondelete="CASCADE"),
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    is_admin: Mapped[Optional[bool]]

    project: Mapped["Project"] = relationship(back_populates="members")