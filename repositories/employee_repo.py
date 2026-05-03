# repositories/employee_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func

from models.employees import Employee, EmployeeData, RoleEnum


class EmployeeRepo:
    """Репозиторий для работы с сотрудниками"""

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # Получение
    # =========================
    def get_by_id(self, employee_id: int) -> Optional[Employee]:
        """Получить сотрудника по ID"""
        return self.session.get(Employee, employee_id)

    def get_by_number(self, number: int) -> Optional[Employee]:
        """Получить сотрудника по табельному номеру"""
        stmt = select(Employee).where(Employee.number == number)
        return self.session.scalar(stmt)

    def get_by_chat_id(self, chat_id: int) -> Optional[Employee]:
        """Получить сотрудника по chat_id"""
        stmt = select(Employee).where(Employee.chat_id == chat_id)
        return self.session.scalar(stmt)

    def get_all(self, active_only: bool = True) -> List[Employee]:
        """Получить всех сотрудников"""
        stmt = select(Employee).order_by(Employee.last_name)
        if active_only:
            stmt = stmt.where(Employee.is_active == True)
        return list(self.session.scalars(stmt))

    def get_by_department(self, department_id: int) -> List[Employee]:
        """Получить сотрудников по отделу"""
        stmt = select(Employee).where(Employee.department_id == department_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def get_by_division(self, division_id: int) -> List[Employee]:
        """Получить сотрудников по подразделению"""
        stmt = select(Employee).where(Employee.division_id == division_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def search(self, query: str) -> List[Employee]:
        """Поиск сотрудников по ФИО"""
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
        """Создать нового сотрудника"""
        # Получаем следующий номер
        max_number = self.session.query(func.max(Employee.number)).scalar()
        next_number = (max_number + 1) if max_number else 1

        employee = Employee(
            number=next_number,
            **data
        )
        self.session.add(employee)
        self.session.flush()  # Чтобы получить ID

        # Создаем запись в EmployeeData
        employee_data = EmployeeData(
            employee_id=employee.id,
            is_active=True,
            role=RoleEnum.user
        )
        self.session.add(employee_data)

        return employee

    # =========================
    # Обновление
    # =========================
    def update(self, employee_id: int, data: dict) -> Optional[Employee]:
        """Обновить данные сотрудника"""
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        for key, value in data.items():
            if hasattr(employee, key) and value is not None:
                setattr(employee, key, value)

        return employee

    def update_role(self, employee_id: int, role: RoleEnum):
        """Обновить роль сотрудника"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(role=role)
        )
        self.session.execute(stmt)

    def set_active(self, employee_id: int, is_active: bool):
        """Установить статус активности"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(is_active=is_active)
        )
        self.session.execute(stmt)

        # Также обновляем в основной таблице
        employee = self.get_by_id(employee_id)
        if employee:
            employee.is_active = is_active

    def update_last_login(self, employee_id: int):
        """Обновить время последнего входа"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(last_login=datetime.now())
        )
        self.session.execute(stmt)

    # =========================
    # Удаление
    # =========================
    def delete(self, employee_id: int) -> bool:
        """Удалить сотрудника (мягкое удаление)"""
        return self.set_active(employee_id, False)

    def hard_delete(self, employee_id: int) -> bool:
        """Полностью удалить сотрудника"""
        employee = self.get_by_id(employee_id)
        if employee:
            self.session.delete(employee)
            return True
        return False