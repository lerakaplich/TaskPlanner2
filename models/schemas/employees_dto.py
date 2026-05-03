# employees_dto.py
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# =========================
# Базовый DTO сотрудника
# =========================
class EmployeeDTO(BaseModel):
    """Базовый DTO для сотрудника (соответствует public.employees)"""
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

    # Добавляем поле для ФИО (удобно для отображения)
    full_name: Optional[str] = None

    @property
    def get_full_name(self) -> str:
        """Формирует ФИО из частей"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    def model_post_init(self, __context):
        """После инициализации заполняем full_name"""
        if not self.full_name:
            self.full_name = self.get_full_name


# =========================
# DTO для профиля (расширенный)
# =========================
class EmployeeProfileDTO(EmployeeDTO):
    """Расширенный DTO для профиля сотрудника"""
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    organization_id: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    last_login: Optional[datetime] = None
    work_number: Optional[str] = None  # Добавляем рабочий телефон
    department_name: Optional[str] = None  # Название отдела
    division_name: Optional[str] = None  # Название подразделения


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
    efficiency: Optional[float] = None  # Эффективность в процентах


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
    rights: Optional[str] = "user"
    password: Optional[str] = None  # Пароль (будет захэширован)


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
    rights: Optional[str] = None
    is_active: Optional[bool] = None


# =========================
# DTO для отдела
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
# DTO для подразделения
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
        email=employee.email,
        chat_id=employee.chat_id,
        birth_date=employee.birth_date
    )


def employee_to_profile_dto(employee, employee_data=None, department_name=None,
                            division_name=None) -> EmployeeProfileDTO:
    """Конвертирует модель Employee в EmployeeProfileDTO с дополнительными данными"""
    return EmployeeProfileDTO(
        id=employee.id,
        number=employee.number,
        last_name=employee.last_name,
        first_name=employee.first_name,
        middle_name=employee.middle_name,
        position=employee.position,
        phone_number=employee.phone_number,
        email=employee.email,
        chat_id=employee.chat_id,
        birth_date=employee.birth_date,
        department_id=employee.department_id,
        division_id=employee.division_id,
        organization_id=employee.organization_id,
        work_number=getattr(employee, 'work_number', None),
        role=employee_data.role.value if employee_data else None,
        is_active=employee.is_active if hasattr(employee, 'is_active') else True,
        last_login=employee_data.last_login if employee_data else None,
        department_name=department_name,
        division_name=division_name
    )


def employee_to_short_dto(employee, department_name=None) -> EmployeeShortDTO:
    """Конвертирует модель Employee в EmployeeShortDTO"""
    full_name = f"{employee.last_name} {employee.first_name}"
    if employee.middle_name:
        full_name += f" {employee.middle_name}"

    return EmployeeShortDTO(
        id=employee.id,
        full_name=full_name.strip(),
        position=employee.position,
        department_name=department_name,
        is_active=getattr(employee, 'is_active', True)
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