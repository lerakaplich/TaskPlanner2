# repositories/employee_data_repo.py - исправленный

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from datetime import datetime

from models.employees import EmployeeData, RoleEnum


class EmployeeDataRepo:
    """Репозиторий для работы с EmployeeData"""

    def __init__(self, session: Session):
        self.session = session

    def save_avatar_data(self, employee_id: int, image_data: bytes, mime_type: str = "image/png") -> bool:
        """
        Сохраняет фото в БД как BLOB
        """
        from datetime import datetime
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(
                avatar_data=image_data,
                avatar_mime_type=mime_type,
                updated_at=datetime.now()
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def get_avatar_data(self, employee_id: int) -> Optional[bytes]:
        """
        Получает фото из БД
        """
        emp_data = self.get_by_id(employee_id)
        return emp_data.avatar_data if emp_data else None

    def delete_avatar_data(self, employee_id: int) -> bool:
        """
        Удаляет фото из БД
        """
        from datetime import datetime
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(
                avatar_data=None,
                avatar_mime_type=None,
                updated_at=datetime.now()
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def get_by_id(self, employee_id: int) -> Optional[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.employee_id == employee_id)
        return self.session.scalar(stmt)

    def get_avatar_mime_type(self, employee_id: int) -> Optional[str]:
        """
        Получает MIME-тип фото из БД
        """
        emp_data = self.get_by_id(employee_id)
        return emp_data.avatar_mime_type if emp_data else None

    def get_all_active(self) -> List[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.is_active == True)
        return list(self.session.scalars(stmt))

    def get_all_with_kpd(self, min_kpd: float = 0.0) -> List[EmployeeData]:
        stmt = select(EmployeeData).where(EmployeeData.kpd_rating >= min_kpd)
        return list(self.session.scalars(stmt))

    def get_top_kpd(self, limit: int = 10) -> List[EmployeeData]:
        stmt = select(EmployeeData).order_by(EmployeeData.kpd_rating.desc()).limit(limit)
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

    def update_session_token(self, employee_id: int, session_token: str) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(app_session_token=session_token, updated_at=datetime.now())
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def update_kpd_rating(self, employee_id: int, kpd_rating: float) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(
                kpd_rating=kpd_rating,
                kpd_last_calculated=datetime.now(),
                updated_at=datetime.now()
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def update_task_stats(self, employee_id: int, total: int, on_time: int) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(
                tasks_completed_total=total,
                tasks_completed_on_time=on_time,
                updated_at=datetime.now()
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def update_completion_days(self, employee_id: int, avg_days: float) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(
                avg_task_completion_days=avg_days,
                updated_at=datetime.now()
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def increment_total_worked_hours(self, employee_id: int, hours: float) -> bool:
        stmt = (
            update(EmployeeData)
            .where(EmployeeData.employee_id == employee_id)
            .values(total_worked_hours=EmployeeData.total_worked_hours + hours)
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0

    def is_active(self, employee_id: int) -> bool:
        emp_data = self.get_by_id(employee_id)
        return emp_data.is_active if emp_data else False

    def get_role(self, employee_id: int) -> Optional[RoleEnum]:
        emp_data = self.get_by_id(employee_id)
        return emp_data.role if emp_data else None