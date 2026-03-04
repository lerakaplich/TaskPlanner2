from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from enum import Enum


# Если хочешь не тянуть enum из SQLAlchemy
class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# =========================
# Базовый DTO задачи
# =========================
class TaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    column_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    position: int
    priority: TaskPriority = TaskPriority.medium
    deadline: Optional[datetime] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# =========================
# DTO карточки задачи
# =========================
class TaskCardDTO(BaseModel):
    id: int
    title: str
    priority: TaskPriority
    deadline: Optional[datetime]
    assigned_to_name: Optional[str]
    is_overdue: bool


# =========================
# DTO задачи с тегами
# =========================
class TaskWithTagsDTO(TaskDTO):
    tags: List[str] = []


# =========================
# DTO для канбан-колонки
# =========================
class BoardColumnDTO(BaseModel):
    id: int
    name: str
    color: str
    position: int
    is_done_column: bool