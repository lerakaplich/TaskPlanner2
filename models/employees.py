# models/employees.py

from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Date, DateTime, ForeignKey, Text, Float,
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
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))

    app_session_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ============================================
    # Поля для КПД (ДОБАВЛЕНЫ)
    # ============================================
    kpd_rating: Mapped[float] = mapped_column(Float, default=0.0)
    kpd_last_calculated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tasks_completed_total: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed_on_time: Mapped[int] = mapped_column(Integer, default=0)

    # Дополнительные метрики (опционально)
    total_worked_hours: Mapped[float] = mapped_column(Float, default=0.0)
    avg_task_completion_days: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationship
    employee: Mapped["Employee"] = relationship(back_populates="employee_data")

    # ============================================
    # Свойства для удобного доступа к КПД
    # ============================================
    @property
    def on_time_rate(self) -> float:
        """Процент выполненных в срок задач (0-100)"""
        if self.tasks_completed_total == 0:
            return 0.0
        return round((self.tasks_completed_on_time / self.tasks_completed_total) * 100, 2)

    @property
    def kpd_level(self) -> str:
        """Текстовый уровень КПД"""
        if self.kpd_rating >= 85:
            return "Высокий 🏆"
        elif self.kpd_rating >= 65:
            return "Хороший ✅"
        elif self.kpd_rating >= 40:
            return "Средний 📊"
        elif self.kpd_rating >= 20:
            return "Низкий ⚠️"
        else:
            return "Критический ❌"

    def update_kpd(self, session):
        """Обновляет КПД сотрудника на основе завершённых задач с учётом пауз"""
        from models.tasks import Task

        completed_tasks = session.query(Task).filter(
            Task.assigned_to == self.employee_id,
            Task.completed_at.isnot(None)
        ).all()

        if not completed_tasks:
            self.kpd_rating = 0.0
            return

        # Усредняем КПД всех задач
        total_kpd = sum(task.kpd_score for task in completed_tasks)
        self.kpd_rating = round(total_kpd / len(completed_tasks), 2)

        # Дополнительная статистика
        self.tasks_completed_total = len(completed_tasks)

        # Количество выполненных в срок (с учётом пауз)
        on_time = 0
        for task in completed_tasks:
            if task.deadline and task.completed_at:
                # Эффективное время <= планового
                effective_days = task.actual_work_days
                planned_days = (task.deadline - task.created_at).days
                if planned_days <= 0:
                    planned_days = 1
                if effective_days <= planned_days * 1.2:  # Допуск 20%
                    on_time += 1

        self.tasks_completed_on_time = on_time
        self.kpd_last_calculated = datetime.now()


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