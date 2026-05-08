# repositories/employee_data_repo.py

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
from datetime import datetime

from models.employees import EmployeeData, RoleEnum


class EmployeeDataRepo:
    """Репозиторий для работы с EmployeeData (таблица в taskplanner)"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, employee_id: int) -> Optional[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.employee_id == employee_id)
        return self.session.scalar(stmt)

    def get_all_active(self) -> List[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.is_active == True)
        return list(self.session.scalars(stmt))

    def create(self, employee_id: int, role: RoleEnum = RoleEnum.user) -> EmployeeData:
        employee_data = EmployeeData(
            employee_id=employee_id,
            is_active=True,
            role=role,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(employee_data)
        self.session.flush()
        return employee_data

    def update_role(self, employee_id: int, role: RoleEnum) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(role=role, updated_at=datetime.now())
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def set_active(self, employee_id: int, is_active: bool) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(is_active=is_active, updated_at=datetime.now())
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def update_last_login(self, employee_id: int) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(last_login=datetime.now(), updated_at=datetime.now())
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def update_session_token(self, employee_id: int, session_token: str, is_app: bool = False) -> bool:
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
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def is_active(self, employee_id: int) -> bool:
        emp_data = self.get_by_id(employee_id)
        return emp_data.is_active if emp_data else False

    def get_role(self, employee_id: int) -> Optional[RoleEnum]:
        emp_data = self.get_by_id(employee_id)
        return emp_data.role if emp_data else None