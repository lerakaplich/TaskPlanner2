# models/projects.py

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Integer, Boolean, ForeignKey, DateTime,
    Enum as SQLAlchemyEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .employees import Base


class ProjectRoleEnum(str, PyEnum):
    PROJECT_MANAGER = "project_manager"
    CURATOR = "curator"
    MEMBER = "member"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]]
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[Optional[int]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # ✅ ОДНО ПОЛЕ для дедлайна (дата + время)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    selected_column_ids: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    manager_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    columns: Mapped[List["BoardColumn"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    members: Mapped[List["EmployeeProject"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )


# =========================
# board_columns
# =========================
class BoardColumn(Base):
    __tablename__ = "board_columns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#ffffff")
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_done_column: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    project: Mapped[Optional["Project"]] = relationship(back_populates="columns")
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="column",
        cascade="all, delete-orphan"
    )


class EmployeeProject(Base):
    __tablename__ = "employees_projects"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[ProjectRoleEnum] = mapped_column(
        SQLAlchemyEnum(ProjectRoleEnum),
        default=ProjectRoleEnum.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    project: Mapped["Project"] = relationship(back_populates="members")
    employee: Mapped["Employee"] = relationship()