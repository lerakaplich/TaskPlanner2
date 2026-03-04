from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# =========================
# Базовый DTO проекта
# =========================
class ProjectDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    deadline: Optional[time] = None
    owner: int


# =========================
# DTO проекта с участниками
# =========================
class ProjectWithMembersDTO(ProjectDTO):
    members: List[int] = []  # список employee_id
    is_admin: Optional[bool] = None


# =========================
# DTO карточки проекта
# =========================
class ProjectCardDTO(BaseModel):
    id: int
    name: str
    description: Optional[str]
    tasks_total: int
    tasks_done: int
    deadline: Optional[time]
    is_archived: bool


# =========================
# DTO для аналитики
# =========================
class ProjectAnalyticsDTO(BaseModel):
    id: int
    name: str
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    high_priority_tasks: int