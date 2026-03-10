from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from models.employees import EmployeeData, RoleEnum, ExternalEmployee


class EmployeeRepo:

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # Получение
    # =========================
    def get_by_id(self, employee_id: int) -> Optional[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.employee_id == employee_id)
        return self.session.scalar(stmt)

    def get_all(self) -> List[ExternalEmployee]:
        """Получить всех сотрудников из внешней БД"""
        stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
        return list(self.session.scalars(stmt))

    # =========================
    # Создание
    # =========================
    def create(self, employee_id: int, role: RoleEnum = RoleEnum.user) -> EmployeeData:
        obj = EmployeeData(
            employee_id=employee_id,
            role=role,
            is_active=True
        )
        self.session.add(obj)
        return obj

    # =========================
    # Обновление
    # =========================
    def update_role(self, employee_id: int, role: RoleEnum):
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(role=role)
        )
        self.session.execute(stmt)

    def set_active(self, employee_id: int, is_active: bool):
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(is_active=is_active)
        )
        self.session.execute(stmt)

    # =========================
    # Удаление
    # =========================
    def delete(self, employee_id: int):
        stmt = delete(EmployeeData).where(EmployeeData.employee_id == employee_id)
        self.session.execute(stmt)