# employees_dto.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# employees_dto.py

class EmployeeDTO(BaseModel):
    """Базовый DTO для сотрудника (только поля из Employee)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    chat_id: Optional[int] = None
    birth_date: Optional[date] = None
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    organization_id: Optional[int] = None

    full_name: Optional[str] = None

    @property
    def get_full_name(self) -> str:
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    def model_post_init(self, __context):
        if not self.full_name:
            self.full_name = self.get_full_name


class EmployeeProfileDTO(EmployeeDTO):
    """Расширенный DTO для профиля (с EmployeeData)"""
    # Только поля из EmployeeData
    role: Optional[str] = None
    is_active: Optional[bool] = None
    last_login: Optional[datetime] = None
    # ❌ УДАЛИТЬ session_token и app_session_token (они не нужны в UI)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    kpd_rating: Optional[float] = None
    kpd_level: Optional[str] = None
    on_time_rate: Optional[float] = None
    tasks_completed_total: Optional[int] = None
    tasks_completed_on_time: Optional[int] = None
    avg_task_completion_days: Optional[float] = None

    department_name: Optional[str] = None
    division_name: Optional[str] = None

# =========================
# DTO для карточки сотрудника (для analytics)
# =========================
class EmployeeCardDTO(BaseModel):
    """DTO для аналитической карточки сотрудника"""
    id: int
    full_name: str
    position: Optional[str]
    active_projects: int
    completed_tasks: int
    overdue_tasks: int
    efficiency: Optional[float] = None


# =========================
# DTO для выбора сотрудника (краткий)
# =========================
class EmployeeShortDTO(BaseModel):
    """Краткий DTO для выбора сотрудника"""
    id: int
    full_name: str
    position: Optional[str] = None
    department_name: Optional[str] = None
    is_active: Optional[bool] = True


# =========================
# DTO для создания/обновления сотрудника
# =========================
class EmployeeCreateDTO(BaseModel):
    """DTO для создания нового сотрудника"""
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    chat_id: Optional[int] = None
    birth_date: Optional[date] = None
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    # rights удален (используется role в EmployeeData)
    # password удален (аутентификация через Telegram)


class EmployeeUpdateDTO(BaseModel):
    """DTO для обновления сотрудника"""
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    chat_id: Optional[int] = None
    birth_date: Optional[date] = None
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    # is_active теперь в EmployeeData, но оставляем для удобства API
    is_active: Optional[bool] = None
    role: Optional[str] = None  # ← ДОБАВЛЕНО (для обновления роли)


# =========================
# DTO для отдела (без изменений)
# =========================
class DepartmentDTO(BaseModel):
    """DTO для отдела"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    boss: Optional[str] = None
    phone_number: Optional[str] = None
    division_id: int
    division_name: Optional[str] = None
    organization_id: int = 1


# =========================
# DTO для подразделения (без изменений)
# =========================
class DivisionDTO(BaseModel):
    """DTO для подразделения"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    boss: Optional[str] = None
    phone_number: Optional[str] = None
    workshop_code: Optional[str] = None
    organization_id: int = 1


# =========================
# Конвертеры (из моделей в DTO)
# =========================

def employee_to_dto(employee) -> EmployeeDTO:
    """Конвертирует модель Employee в EmployeeDTO"""
    return EmployeeDTO(
        id=employee.id,
        number=employee.number,
        last_name=employee.last_name,
        first_name=employee.first_name,
        middle_name=employee.middle_name,
        position=employee.position,
        phone_number=employee.phone_number,
        work_number=employee.work_number,
        email=employee.email,
        chat_id=employee.chat_id,
        birth_date=employee.birth_date,
        department_id=employee.department_id,
        division_id=employee.division_id,
        organization_id=employee.organization_id,
    )


def employee_to_profile_dto(employee, employee_data=None, department_name=None,
                            division_name=None) -> EmployeeProfileDTO:
    """Конвертирует модель Employee в EmployeeProfileDTO с данными из EmployeeData"""
    return EmployeeProfileDTO(
        id=employee.id,
        number=employee.number,
        last_name=employee.last_name,
        first_name=employee.first_name,
        middle_name=employee.middle_name,
        position=employee.position,
        phone_number=employee.phone_number,
        work_number=employee.work_number,
        email=employee.email,
        chat_id=employee.chat_id,
        birth_date=employee.birth_date,
        department_id=employee.department_id,
        division_id=employee.division_id,
        organization_id=employee.organization_id,
        role=employee_data.role.value if employee_data and employee_data.role else None,
        is_active=employee_data.is_active if employee_data else True,
        last_login=employee_data.last_login if employee_data else None,
        app_session_token=employee_data.app_session_token if employee_data else None,
        created_at=employee_data.created_at if employee_data else None,
        updated_at=employee_data.updated_at if employee_data else None,
        kpd_rating=employee_data.kpd_rating if employee_data else None,
        kpd_level=employee_data.kpd_level if employee_data else None,
        on_time_rate=employee_data.on_time_rate if employee_data else None,
        tasks_completed_total=employee_data.tasks_completed_total if employee_data else None,
        tasks_completed_on_time=employee_data.tasks_completed_on_time if employee_data else None,
        avg_task_completion_days=employee_data.avg_task_completion_days if employee_data else None,
        department_name=department_name,
        division_name=division_name
    )


def employee_to_short_dto(employee, employee_data=None, department_name=None) -> EmployeeShortDTO:
    """Конвертирует модель Employee в EmployeeShortDTO"""
    full_name = f"{employee.last_name} {employee.first_name}"
    if employee.middle_name:
        full_name += f" {employee.middle_name}"

    return EmployeeShortDTO(
        id=employee.id,
        full_name=full_name.strip(),
        position=employee.position,
        department_name=department_name,
        is_active=employee_data.is_active if employee_data else True
    )


def department_to_dto(department, division_name=None) -> DepartmentDTO:
    """Конвертирует модель Department в DepartmentDTO"""
    return DepartmentDTO(
        id=department.id,
        number=department.number,
        name=department.name,
        boss=department.boss,
        phone_number=department.phone_number,
        division_id=department.division_id,
        division_name=division_name,
        organization_id=department.organization_id
    )


def division_to_dto(division) -> DivisionDTO:
    """Конвертирует модель Division в DivisionDTO"""
    return DivisionDTO(
        id=division.id,
        number=division.number,
        name=division.name,
        boss=division.boss,
        phone_number=division.phone_number,
        workshop_code=division.workshop_code,
        organization_id=division.organization_id
    )