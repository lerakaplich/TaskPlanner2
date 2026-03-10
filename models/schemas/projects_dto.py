from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from models.schemas.tasks_dto import BoardColumnDTO, TaskCardDTO


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
    member_ids: List[int] = []  # Все участники (включая админов)
    admin_ids: List[int] = []  # Только те, у кого есть флаг is_admin
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

# В файле схем проектов/задач
class BoardColumnWithTasksDTO(BoardColumnDTO):
    tasks: List[TaskCardDTO] = []

class ProjectBoardDTO(BaseModel):
    project: ProjectWithMembersDTO
    columns: List[BoardColumnWithTasksDTO]