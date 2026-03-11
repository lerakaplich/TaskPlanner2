from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class MessageReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime
    time_display: str
    date_display: str


class ChatReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    type: str  # 'project', 'group', 'private'
    project_id: Optional[int]

    # Для UI: имя чата может вычисляться (например, имя собеседника в private)
    display_name: str