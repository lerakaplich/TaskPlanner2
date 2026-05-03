# models/employees.py
from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Date, DateTime, Time, ForeignKey, Text, Column,
    Enum as SQLAlchemyEnum
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
# Enum (должен совпадать с типом в БД)
# =========================
class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"


# =========================
# public.employees - ОСНОВНАЯ ТАБЛИЦА
# =========================
class Employee(Base):
    """Сотрудник (прямое подключение к public.employees)"""
    __tablename__ = "employees"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    position: Mapped[Optional[str]] = mapped_column(String(200))
    rights: Mapped[Optional[str]] = mapped_column(String(50), default='user')
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    work_number: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    division_id: Mapped[Optional[int]] = mapped_column(Integer)
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    session_token: Mapped[Optional[str]] = mapped_column(String(255))
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    app_session_token: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    employee_data: Mapped[Optional["EmployeeData"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    notes: Mapped[List["EmployeeNote"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


# =========================
# public.employees_data
# =========================
class EmployeeData(Base):
    """Дополнительные данные сотрудника (активность, роль)"""
    __tablename__ = "employees_data"
    __table_args__ = {"schema": "public"}

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("public.employees.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    role: Mapped[Optional[RoleEnum]] = mapped_column(SQLAlchemyEnum(RoleEnum, name="roles"), default=RoleEnum.user)

    # Relationship
    employee: Mapped["Employee"] = relationship(back_populates="employee_data")


# =========================
# public.employee_notes
# =========================
class EmployeeNote(Base):
    """Заметки и переработки сотрудников"""
    __tablename__ = "employee_notes"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("public.employees.id", ondelete="CASCADE"))
    note_text: Mapped[Optional[str]] = mapped_column(Text)
    overtime_date: Mapped[date] = mapped_column(Date)
    overtime_start: Mapped[Optional[time]] = mapped_column(Time)
    overtime_end: Mapped[Optional[time]] = mapped_column(Time)

    # Relationship
    employee: Mapped["Employee"] = relationship(back_populates="notes")


# =========================
# public.departments
# =========================
class Department(Base):
    """Отдел"""
    __tablename__ = "departments"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    boss: Mapped[Optional[str]] = mapped_column(String(150))
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    division_id: Mapped[int] = mapped_column(Integer)
    organization_id: Mapped[int] = mapped_column(Integer)


# =========================
# public.divisions
# =========================
class Division(Base):
    """Подразделение"""
    __tablename__ = "divisions"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    boss: Mapped[Optional[str]] = mapped_column(String(150))
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    workshop_code: Mapped[Optional[str]] = mapped_column(String(50))
    organization_id: Mapped[int] = mapped_column(Integer)