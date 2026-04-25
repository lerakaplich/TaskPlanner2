# models/schemas/tasks_dto.py
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from enum import Enum


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

    # Дополнительные поля для Ганта
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: int = 0
    parent_id: Optional[int] = None

    def __post_init__(self):
        if self.deadline:
            if not self.start_date:
                self.start_date = self.deadline.date()
            if not self.end_date:
                self.end_date = self.deadline.date()


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