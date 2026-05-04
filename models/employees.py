# models/employees.py

from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Date, DateTime, ForeignKey, Text,
    Enum as SQLAlchemyEnum
)
from sqlalchemy.sql.sqltypes import Time as SQLTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"


class Employee(Base):
    """Сотрудник (основные данные, без служебных полей)"""
    __tablename__ = "employees"
    __table_args__ = {"schema": "public"}

    # Основные идентификаторы
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)  # Табельный номер

    # ФИО
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Должность и подразделения
    position: Mapped[Optional[str]] = mapped_column(String(200))
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    division_id: Mapped[Optional[int]] = mapped_column(Integer)
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    # Контакты
    work_number: Mapped[Optional[str]] = mapped_column(String(50))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Личные данные
    birth_date: Mapped[Optional[date]] = mapped_column(Date)

    # Relationships
    employee_data: Mapped[Optional["EmployeeData"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        uselist=False  # one-to-one
    )
    notes: Mapped[List["EmployeeNote"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan"
    )


class EmployeeData(Base):
    """Служебные данные сотрудника (в БД taskplanner)"""
    __tablename__ = "employees_data"
    __table_args__ = {"schema": "public"}

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("public.employees.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Служебные поля
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[RoleEnum] = mapped_column(
        SQLAlchemyEnum(RoleEnum, name="roles"),
        default=RoleEnum.user
    )

    # Пароль (хеш)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))  # ← ДОБАВЛЕНО

    # Токен сессий
    app_session_token: Mapped[Optional[str]] = mapped_column(String(255))

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationship
    employee: Mapped["Employee"] = relationship(back_populates="employee_data")


class EmployeeNote(Base):
    """Заметки и переработки сотрудников"""
    __tablename__ = "employee_notes"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("public.employees.id", ondelete="CASCADE"))
    note_text: Mapped[Optional[str]] = mapped_column(Text)
    overtime_date: Mapped[date] = mapped_column(Date)
    overtime_start: Mapped[Optional[time]] = mapped_column(SQLTime)
    overtime_end: Mapped[Optional[time]] = mapped_column(SQLTime)

    # Relationship
    employee: Mapped["Employee"] = relationship(back_populates="notes")


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