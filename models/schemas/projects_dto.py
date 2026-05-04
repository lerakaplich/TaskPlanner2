# models/schemas/projects_dto.py

from datetime import datetime, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

from models.schemas.tasks_dto import BoardColumnDTO, TaskCardDTO


# =========================
# Базовый DTO проекта
# =========================
# models/schemas/projects_dto.py

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
    selected_column_ids: Optional[str] = None
    manager_id: Optional[int] = None


class ProjectWithMembersDTO(ProjectDTO):
    member_ids: List[int] = []
    admin_ids: List[int] = []
    is_admin: Optional[bool] = None
    selected_columns_data: List[Dict[str, Any]] = []
    manager_name: Optional[str] = None

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
    admin_count: int = 0
    owner_name: str = "Не назначен"
    owner_id: Optional[int] = None
    created_at: Optional[str] = None
    columns_count: int = 0
    manager_name: Optional[str] = None


class ProjectAnalyticsDTO(BaseModel):
    id: int
    name: str
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    high_priority_tasks: int


class BoardColumnWithTasksDTO(BoardColumnDTO):
    tasks: List[TaskCardDTO] = []


class ProjectBoardDTO(BaseModel):
    project: ProjectWithMembersDTO
    columns: List[BoardColumnWithTasksDTO]