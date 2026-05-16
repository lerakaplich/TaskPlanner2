# models/schemas/tasks_dto.py

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from enum import Enum


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


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
    difficulty: float = 0.0
    progress_percent: float = 0.0  # 👈 добавлено
    completed_at: Optional[datetime] = None  # 👈 добавлено
    started_at: Optional[datetime] = None  # 👈 добавлено
    actual_hours: float = 0.0  # 👈 добавлено
    kpd_score: Optional[float] = None  # 👈 КПД задачи


class TaskCardDTO(BaseModel):
    id: int
    title: str
    is_archived: bool = False
    priority: TaskPriority
    deadline: Optional[datetime]
    assigned_to_name: Optional[str]
    is_overdue: bool
    difficulty: float = 0.0
    progress_percent: float = 0.0  # 👈 добавлено
    kpd_score: Optional[float] = None  # 👈 добавлено

    @field_validator('priority', mode='before')
    @classmethod
    def parse_priority(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return v


class TaskWithTagsDTO(TaskDTO):
    tags: List[str] = []


class BoardColumnDTO(BaseModel):
    id: int
    name: str
    color: str
    position: int
    is_done_column: bool


class TagDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str = "#ccab6e"
    is_archived: bool = False
    usage_count: int = 0


class TagCardDTO(BaseModel):
    id: int
    name: str
    color: str
    usage_count: int = 0