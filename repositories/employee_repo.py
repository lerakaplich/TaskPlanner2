# repositories/employee_repo.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from typing import Optional, List
from datetime import datetime  # ← ДОБАВИТЬ
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
            # Фильтруем через join с EmployeeData
            stmt = stmt.join(EmployeeData).where(EmployeeData.is_active == True)

        return list(self.session.scalars(stmt))

    def get_all_with_data(self, active_only: bool = True) -> List[tuple]:
        """Получить всех сотрудников вместе с EmployeeData"""
        stmt = select(Employee, EmployeeData).join(
            EmployeeData, Employee.id == EmployeeData.employee_id
        ).order_by(Employee.last_name)

        if active_only:
            stmt = stmt.where(EmployeeData.is_active == True)

        return list(self.session.execute(stmt))

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

    def get_employee_data(self, employee_id: int) -> Optional[EmployeeData]:
        """Получить служебные данные сотрудника"""
        stmt = select(EmployeeData).where(EmployeeData.employee_id == employee_id)
        return self.session.scalar(stmt)

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
            role=RoleEnum.user,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(employee_data)

        return employee

    # =========================
    # Обновление
    # =========================
    def update(self, employee_id: int, data: dict) -> Optional[Employee]:
        """Обновить данные сотрудника (только поля Employee)"""
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        # Обновляем только поля Employee
        employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                           'department_id', 'division_id', 'organization_id',
                           'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

        for key, value in data.items():
            if key in employee_fields and value is not None:
                setattr(employee, key, value)

        return employee

    def update_role(self, employee_id: int, role: RoleEnum):
        """Обновить роль сотрудника"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(role=role, updated_at=datetime.now())
        )
        self.session.execute(stmt)

    def set_active(self, employee_id: int, is_active: bool):
        """Установить статус активности (в EmployeeData)"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(is_active=is_active, updated_at=datetime.now())
        )
        self.session.execute(stmt)

    def update_session_token(self, employee_id: int, session_token: str, is_app: bool = False):
        """Обновить токен сессии"""
        if is_app:
            stmt = (
                update(EmployeeData)
                .where(EmployeeData.employee_id == employee_id)
                .values(app_session_token=session_token, updated_at=datetime.now())
            )
        else:
            stmt = (
                update(EmployeeData)
                .where(EmployeeData.employee_id == employee_id)
                .values(session_token=session_token, updated_at=datetime.now())
            )
        self.session.execute(stmt)

    def update_last_login(self, employee_id: int):
        """Обновить время последнего входа"""
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(last_login=datetime.now(), updated_at=datetime.now())
        )
        self.session.execute(stmt)

    def get_full_name(self, employee_id: int) -> str:
        """Возвращает ФИО сотрудника по ID"""
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
    # Удаление
    # =========================
    def delete(self, employee_id: int) -> bool:
        """Мягкое удаление сотрудника (установить is_active=False)"""
        return self.set_active(employee_id, False)

    def hard_delete(self, employee_id: int) -> bool:
        """Полностью удалить сотрудника (удалит и EmployeeData благодаря cascade)"""
        employee = self.get_by_id(employee_id)
        if employee:
            self.session.delete(employee)
            return True
        return False

    # =========================
    # Проверки
    # =========================
    def is_active(self, employee_id: int) -> bool:
        """Проверить, активен ли сотрудник"""
        employee_data = self.get_employee_data(employee_id)
        return employee_data.is_active if employee_data else False

    def get_role(self, employee_id: int) -> Optional[RoleEnum]:
        """Получить роль сотрудника"""
        employee_data = self.get_employee_data(employee_id)
        return employee_data.role if employee_data else None