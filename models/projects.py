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
# board_columns
# =========================
class BoardColumn(Base):
    __tablename__ = "board_columns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    name: Mapped[str]
    color: Mapped[str] = mapped_column(default="#ffffff")
    position: Mapped[int]
    is_done_column: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]

    project: Mapped["Project"] = relationship(back_populates="columns")
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
        ForeignKey("employees_data.employee_id", ondelete="CASCADE"),
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    is_admin: Mapped[Optional[bool]]

    project: Mapped["Project"] = relationship(back_populates="members")