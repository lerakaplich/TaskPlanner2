from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, Text, DateTime, String, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from models.employees import Base

class ChatType(enum.Enum):
    project = "project"
    group = "group"
    private = "private"

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    type: Mapped[ChatType] = mapped_column(Enum(ChatType))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # Связи
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    participants = relationship("ChatParticipant", back_populates="chat")

class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    employee_id: Mapped[int] = mapped_column(primary_key=True) # ID из foreign_data
    joined_at: Mapped[datetime] = mapped_column(default=datetime.now)

    chat = relationship("Chat", back_populates="participants")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    chat = relationship("Chat", back_populates="messages")
    # Связь с сотрудником через primaryjoin (так как это внешняя таблица)
    sender = relationship(
        "ExternalEmployee",
        primaryjoin="ChatMessage.sender_id == ExternalEmployee.id",
        foreign_keys=[sender_id],
        viewonly=True
    )

class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True) # ID из внешней базы
    read_at: Mapped[datetime] = mapped_column(default=datetime.now)