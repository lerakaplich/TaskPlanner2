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
        """Получить всех сотрудников из внешней БД"""
        try:
            stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
            result = list(self.session.scalars(stmt))
            print(f"📊 ExternalEmployeeRepo.get_all() вернул {len(result)} записей")
            return result
        except Exception as e:
            print(f"❌ Ошибка в ExternalEmployeeRepo.get_all(): {e}")
            return []

    def search_by_name(self, query: str) -> List[ExternalEmployee]:
        stmt = select(ExternalEmployee).where(
            ExternalEmployee.last_name.ilike(f"%{query}%")
        )
        return list(self.session.scalars(stmt))

    def get_full_name(self, employee_id: int) -> str:
        """Возвращает форматированное имя сотрудника: Иванов И. И."""
        from models.employees import ExternalEmployee  # Убедись в правильности импорта
        emp = self.session.get(ExternalEmployee, employee_id)
        if not emp:
            return "Неизвестен"

        # Формируем ФИО
        first_initial = f"{emp.first_name[0]}." if emp.first_name else ""
        middle_initial = f"{emp.middle_name[0]}." if emp.middle_name else ""

        return f"{emp.last_name} {first_initial}{middle_initial}".strip()