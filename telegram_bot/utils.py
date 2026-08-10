import hashlib
from typing import Optional
from sqlalchemy import text
from server_app.database import get_employees_session


def simple_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_simple_hash(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


async def get_phone_by_chat(chat_id: int) -> Optional[str]:
    """Получить номер телефона пользователя по chat_id"""
    with get_employees_session() as emp_session:
        select_stmt = text("""
            SELECT phone_number FROM public.employees WHERE chat_id = :chat_id
        """)
        result = emp_session.execute(select_stmt, {'chat_id': chat_id}).first()
        if result:
            return result[0]
    return None


async def get_employee_id_by_chat(chat_id: int) -> Optional[int]:
    """Получить ID сотрудника по chat_id"""
    with get_employees_session() as emp_session:
        select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
        employee = emp_session.execute(select_stmt, {'chat_id': chat_id}).first()
        return employee[0] if employee else None