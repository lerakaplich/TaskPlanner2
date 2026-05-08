# repositories/employee_repo.py (исправленный)

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func

from models.employees import Employee, Department, Division


class EmployeeRepo:
    """Репозиторий для работы с сотрудниками (только таблица employees в БД employees)"""

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # Получение
    # =========================
    def get_by_id(self, employee_id: int) -> Optional[Employee]:
        return self.session.get(Employee, employee_id)

    def get_by_number(self, number: int) -> Optional[Employee]:
        stmt = select(Employee).where(Employee.number == number)
        return self.session.scalar(stmt)

    def get_by_chat_id(self, chat_id: int) -> Optional[Employee]:
        stmt = select(Employee).where(Employee.chat_id == chat_id)
        return self.session.scalar(stmt)

    def get_all(self) -> List[Employee]:
        stmt = select(Employee).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def get_by_department(self, department_id: int) -> List[Employee]:
        stmt = select(Employee).where(Employee.department_id == department_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def get_by_division(self, division_id: int) -> List[Employee]:
        stmt = select(Employee).where(Employee.division_id == division_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def search(self, query: str) -> List[Employee]:
        search_pattern = f"%{query}%"
        stmt = select(Employee).where(
            (Employee.last_name.ilike(search_pattern)) |
            (Employee.first_name.ilike(search_pattern)) |
            (Employee.middle_name.ilike(search_pattern))
        ).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    # =========================
    # Создание
    # =========================
    def create(self, data: dict) -> Employee:
        max_number = self.session.query(func.max(Employee.number)).scalar()
        next_number = (max_number + 1) if max_number else 1

        employee = Employee(
            number=next_number,
            **data
        )
        self.session.add(employee)
        self.session.flush()
        return employee

    # =========================
    # Обновление
    # =========================
    def update(self, employee_id: int, data: dict) -> Optional[Employee]:
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                           'department_id', 'division_id', 'organization_id',
                           'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

        for key, value in data.items():
            if key in employee_fields and value is not None:
                setattr(employee, key, value)

        return employee

    def get_full_name(self, employee_id: int) -> str:
        try:
            employee = self.get_by_id(employee_id)
            if not employee:
                return "Не назначен"

            parts = []
            if hasattr(employee, 'last_name') and employee.last_name:
                parts.append(employee.last_name)
            if hasattr(employee, 'first_name') and employee.first_name:
                parts.append(employee.first_name)
            if hasattr(employee, 'middle_name') and employee.middle_name:
                parts.append(employee.middle_name)

            full_name = ' '.join(parts).strip()
            return full_name if full_name else f"ID: {employee_id}"
        except Exception as e:
            print(f"⚠️ Ошибка в get_full_name: {e}")
            return f"ID: {employee_id}"

    # =========================
    # Удаление (только в employees)
    # =========================
    def hard_delete(self, employee_id: int) -> bool:
        employee = self.get_by_id(employee_id)
        if employee:
            self.session.delete(employee)
            return True
        return False