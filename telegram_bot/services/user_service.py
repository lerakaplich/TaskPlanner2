from typing import Dict, List, Optional
from sqlalchemy import text
from database import get_employees_session, get_tasks_session
from models.employees import Employee, EmployeeData


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self):
        self.user_passwords: Dict[str, str] = {}
        self.user_sessions: Dict[int, dict] = {}

    def generate_password(self, length: int = 8) -> str:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def hash_password(self, password: str) -> str:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    async def get_employees_list(self) -> List[Dict]:
        """Получить список сотрудников для выбора исполнителя"""
        with get_employees_session() as emp_session:
            stmt = text("""
                SELECT id, last_name, first_name, middle_name
                FROM public.employees
                ORDER BY last_name, first_name
            """)
            employees = emp_session.execute(stmt).fetchall()
            return [{"id": e.id, "name": f"{e.last_name} {e.first_name} {e.middle_name or ''}".strip()} for e in employees]

    async def get_employee_by_chat(self, chat_id: int) -> Optional[Employee]:
        with get_employees_session() as emp_session:
            from sqlalchemy import select
            stmt = select(Employee).where(Employee.chat_id == chat_id)
            return emp_session.scalar(stmt)