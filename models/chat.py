from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, Text, DateTime, String, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from models.employees import Base
# ВАЖНО: Убедись, что этот импорт есть, чтобы Metadata узнала о таблице сотрудников!
from models.employees import ExternalEmployee

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
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # НОВЫЕ ПОЛЯ
    reply_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_messages.id", ondelete="SET NULL"))
    forward_from_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("public.employees_data.employee_id", ondelete="SET NULL")
    )

    # Связь для получения имени (через цепочку отношений)
    is_deleted: Mapped[bool] = mapped_column(default=False)

    chat = relationship("Chat", back_populates="messages")

    # Связь для получения текста ответа
    replied_to_message = relationship("ChatMessage", remote_side=[id], viewonly=True)

    # 2. Ссылка на автора пересланного (forward_from_id -> ExternalEmployee.id)
    forward_sender = relationship(
        "ExternalEmployee",
        primaryjoin="ChatMessage.forward_from_id == foreign(ExternalEmployee.id)",
        viewonly=True,
        uselist=False
    )

    # 3. Ссылка на расширенные данные автора пересланного (forward_from_id -> EmployeeData.employee_id)
    forward_sender_data = relationship(
        "EmployeeData",
        primaryjoin="ChatMessage.forward_from_id == foreign(EmployeeData.employee_id)",
        viewonly=True,
        uselist=False
    )

    # 1. Ссылка на отправителя (sender_id -> ExternalEmployee.id)
    sender = relationship(
        "ExternalEmployee",
        primaryjoin="ChatMessage.sender_id == foreign(ExternalEmployee.id)",
        viewonly=True,
        uselist=False
    )

class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True) # ID из внешней базы
    read_at: Mapped[datetime] = mapped_column(default=datetime.now)