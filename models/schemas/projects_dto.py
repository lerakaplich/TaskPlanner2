# models/schemas/projects_dto.py

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

from models.schemas.tasks_dto import BoardColumnDTO, TaskCardDTO
from models.projects import ProjectRoleEnum


# =========================
# Базовый DTO проекта
# =========================
class ProjectDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_archived: bool = False
    created_by: Optional[int] = None  # ✅ ДОБАВЛЕНО (было в БД)
    created_at: datetime
    updated_at: datetime
    deadline_date: Optional[date] = None  # ✅ ИСПРАВЛЕНО (было deadline: time)
    owner: Optional[int] = None  # ⚠️ Можно удалить, если дублирует created_by
    selected_column_ids: Optional[str] = None
    manager_id: Optional[int] = None


# =========================
# DTO с участниками (исправлен)
# =========================
class ProjectMemberDTO(BaseModel):
    """DTO участника проекта с ролью"""
    employee_id: int
    full_name: str
    role: str  # project_manager, curator, member
    joined_at: datetime


class ProjectWithMembersDTO(ProjectDTO):
    """DTO проекта с участниками"""
    members: List[ProjectMemberDTO] = []  # ✅ Вместо member_ids и admin_ids

    selected_columns_data: List[Dict[str, Any]] = []
    manager_name: Optional[str] = None

    # Текущая роль пользователя в проекте (для UI)
    current_user_role: Optional[str] = None


# =========================
# DTO карточки проекта
# =========================
class ProjectCardDTO(BaseModel):
    id: int
    name: str
    description: Optional[str]
    tasks_total: int
    tasks_done: int
    is_archived: bool = False
    member_count: int = 0
    owner_name: str = "Не назначен"
    owner_id: Optional[int] = None
    created_at: Optional[str] = None
    columns_count: int = 0
    manager_name: Optional[str] = None
    # Текущая роль пользователя в проекте
    user_role: Optional[str] = None