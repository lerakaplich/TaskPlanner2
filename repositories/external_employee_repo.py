from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.employees import ExternalEmployee


class ExternalEmployeeRepo:

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, employee_id: int) -> Optional[ExternalEmployee]:
        stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
        return self.session.scalar(stmt)

    def get_all(self) -> List[ExternalEmployee]:
        stmt = select(ExternalEmployee)
        return list(self.session.scalars(stmt))

    def search_by_name(self, query: str) -> List[ExternalEmployee]:
        stmt = select(ExternalEmployee).where(
            ExternalEmployee.last_name.ilike(f"%{query}%")
        )
        return list(self.session.scalars(stmt))