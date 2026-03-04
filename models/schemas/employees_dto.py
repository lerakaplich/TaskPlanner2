from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# =========================
# Базовый DTO сотрудника
# =========================
class EmployeeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    chat_id: Optional[int] = None
    birth_date: Optional[date] = None


# =========================
# DTO для профиля
# =========================
class EmployeeProfileDTO(EmployeeDTO):
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    organization_id: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    last_login: Optional[datetime] = None


# =========================
# DTO для карточки сотрудника
# (для analytics)
# =========================
class EmployeeCardDTO(BaseModel):
    id: int
    full_name: str
    position: Optional[str]
    active_projects: int
    completed_tasks: int
    overdue_tasks: int


# =========================
# DTO для выбора сотрудника
# =========================
class EmployeeShortDTO(BaseModel):
    id: int
    full_name: str