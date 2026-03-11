# repositories/overtime_repo.py

from datetime import date, time
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from models.employees import EmployeeNote


class OvertimeRepo:
    """Репозиторий для работы с переработками из таблицы employee_notes"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_employee(self, employee_id: int) -> List[EmployeeNote]:
        """Получить все переработки сотрудника"""
        stmt = select(EmployeeNote).where(
            EmployeeNote.employee_id == employee_id
        ).order_by(EmployeeNote.overtime_date.desc())
        return list(self.session.scalars(stmt))

    def get_all(self) -> List[EmployeeNote]:
        """Получить все переработки всех сотрудников"""
        stmt = select(EmployeeNote).order_by(
            EmployeeNote.overtime_date.desc(),
            EmployeeNote.employee_id
        )
        return list(self.session.scalars(stmt))

    def create(self, employee_id: int, overtime_date: date, note_text: Optional[str] = None,
               overtime_start: Optional[time] = None, overtime_end: Optional[time] = None) -> EmployeeNote:
        """Создать новую запись о переработке"""
        # Получаем следующий номер
        max_num = self.session.scalar(select(func.max(EmployeeNote.number)))
        next_num = (max_num or 0) + 1

        note = EmployeeNote(
            number=next_num,
            employee_id=employee_id,
            note_text=note_text,
            overtime_date=overtime_date,
            overtime_start=overtime_start,
            overtime_end=overtime_end
        )
        self.session.add(note)
        self.session.flush()
        return note