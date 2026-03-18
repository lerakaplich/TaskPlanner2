from enum import Enum

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class DeleteMode(str, Enum):
    EVERYONE = "everyone"
    ME = "me"


class MessageReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime
    time_display: str
    is_read: bool = False
    is_edited: bool = False
    reply_to_id: Optional[int] = None
    reply_text: Optional[str] = None
    reply_sender_name: Optional[str] = None
    forward_from_name: Optional[str] = None

class MessageEditDTO(BaseModel):
    message_id: int
    new_content: str
    chat_id: int

class MessageDeleteDTO(BaseModel):
    message_id: int
    chat_id: int
    mode: str = "everyone" # "everyone" или "me"

class ChatReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    type: str  # 'project', 'group', 'private'
    project_id: Optional[int]

    # Для UI: имя чата может вычисляться (например, имя собеседника в private)
    display_name: str