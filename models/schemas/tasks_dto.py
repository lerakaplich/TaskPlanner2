from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
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
    is_archived: bool = False
    priority: TaskPriority
    deadline: Optional[datetime]
    assigned_to_name: Optional[str]
    is_overdue: bool

    @field_validator('priority', mode='before')
    @classmethod
    def parse_priority(cls, v):
        # Если пришел объект SQLAlchemy Enum, берем его значение
        if hasattr(v, 'value'):
            return v.value
        return v


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

class TagDTO(BaseModel):
    """DTO для тега"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str = "#ccab6e"
    is_archived: bool = False
    usage_count: int = 0  # Количество использований в задачах


class TagCardDTO(BaseModel):
    """DTO для карточки тега в настройках"""
    id: int
    name: str
    color: str
    usage_count: int = 0