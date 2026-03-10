# repositories/external_employee_repo.py

from typing import Optional
from sqlalchemy import select
from models.employees import ExternalEmployee


class ExternalEmployeeRepo:

    def get_by_id(self, employee_id: int) -> Optional[ExternalEmployee]:
        """Получить сотрудника по ID"""
        stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
        return self.session.scalar(stmt)