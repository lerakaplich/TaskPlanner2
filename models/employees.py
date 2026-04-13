# models/employees.py

from datetime import datetime, date, time
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Time,
    ForeignKey,
    Enum,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB

import enum


# =========================
# Base
# =========================
class Base(DeclarativeBase):
    pass


# =========================
# Enum из БД
# =========================
class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"


# =========================
# FOREIGN TABLE
# foreign_data.employees
# =========================
class ExternalEmployee(Base):
    __tablename__ = "employees"
    __table_args__ = {"schema": "foreign_data"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    last_name: Mapped[str]
    first_name: Mapped[str]
    middle_name: Mapped[Optional[str]]
    position: Mapped[Optional[str]]
    rights: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    birth_date: Mapped[Optional[date]]
    department_id: Mapped[Optional[int]]
    division_id: Mapped[Optional[int]]
    organization_id: Mapped[Optional[int]]
    session_token: Mapped[Optional[str]]
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)


# =========================
# public.employees_data
# =========================
class EmployeeData(Base):
    __tablename__ = "employees_data"
    __table_args__ = {"schema": "public"}

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("foreign_data.employees.id", ondelete="CASCADE"),
        primary_key=True,
    )

    last_login: Mapped[Optional[datetime]]
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean)
    role: Mapped[Optional[RoleEnum]] = mapped_column(
        Enum(RoleEnum, name="roles")
    )

    # relationship
    employee: Mapped["ExternalEmployee"] = relationship()


# =========================
# public.employees (локальная таблица)
# =========================
class LocalEmployee(Base):
    __tablename__ = "employees"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    last_name: Mapped[str]
    first_name: Mapped[str]
    middle_name: Mapped[Optional[str]]
    position: Mapped[Optional[str]]
    rights: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    birth_date: Mapped[Optional[date]]
    department_id: Mapped[Optional[int]]
    division_id: Mapped[Optional[int]]
    organization_id: Mapped[Optional[int]]
    session_token: Mapped[Optional[str]]
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)


# =========================
# public.employee_notes
# =========================
class EmployeeNote(Base):
    __tablename__ = "employee_notes"
    __table_args__ = {"schema": "public"}  # 👈 ДОБАВЛЯЕМ СХЕМУ

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(unique=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("public.employees.id", ondelete="CASCADE")
    )
    note_text: Mapped[Optional[str]] = mapped_column(Text)
    overtime_date: Mapped[date] = mapped_column(Date)
    overtime_start: Mapped[Optional[time]] = mapped_column(Time)
    overtime_end: Mapped[Optional[time]] = mapped_column(Time)

    # relationship
    employee: Mapped["LocalEmployee"] = relationship()

class DepartmentFDW(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "foreign_data"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    name: Mapped[str]
    boss: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    division_id: Mapped[Optional[int]]
    organization_id: Mapped[Optional[int]]


class DivisionFDW(Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": "foreign_data"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    name: Mapped[str]
    boss: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    workshop_code: Mapped[Optional[str]]
    organization_id: Mapped[Optional[int]]

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    name: Mapped[str]
    boss: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    division_id: Mapped[int]
    organization_id: Mapped[int]


class Division(Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    name: Mapped[str]
    boss: Mapped[Optional[str]]
    phone_number: Mapped[Optional[str]]
    workshop_code: Mapped[Optional[str]]
    organization_id: Mapped[int]