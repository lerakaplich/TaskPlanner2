from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from models.chat import Chat, ChatMessage, ChatParticipant, ChatType

class ChatRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_chats_for_user(self, employee_id: int) -> List[Chat]:
        """Получить все чаты, в которых состоит пользователь"""
        stmt = (
            select(Chat)
            .join(ChatParticipant)
            .where(ChatParticipant.employee_id == employee_id)
            .order_by(Chat.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def create_chat(self, chat_type: ChatType, title: str = None, project_id: int = None) -> Chat:
        chat = Chat(type=chat_type, title=title, project_id=project_id)
        self.session.add(chat)
        self.session.flush() # Получаем ID без коммита
        return chat

    def add_participant(self, chat_id: int, employee_id: int):
        participant = ChatParticipant(chat_id=chat_id, employee_id=employee_id)
        self.session.add(participant)

    def create_message(self, chat_id: int, sender_id: int, content: str) -> ChatMessage:
        msg = ChatMessage(chat_id=chat_id, sender_id=sender_id, content=content)
        self.session.add(msg)
        return msg

    def get_history(self, chat_id: int, limit: int = 50) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = list(self.session.scalars(stmt))
        return result[::-1]