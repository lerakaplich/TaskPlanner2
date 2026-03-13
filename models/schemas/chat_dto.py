from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class MessageReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int # Добавили поле
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime
    time_display: str
    is_read: bool = False # Добавили поле для галочек
    is_edited: bool = False


class ChatReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    type: str  # 'project', 'group', 'private'
    project_id: Optional[int]

    # Для UI: имя чата может вычисляться (например, имя собеседника в private)
    display_name: str