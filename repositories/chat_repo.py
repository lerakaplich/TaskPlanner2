from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql.dml import insert
from sqlalchemy.orm import Session
from models.chat import Chat, ChatMessage, ChatParticipant, ChatType, MessageRead
from models.employees import ExternalEmployee


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

    def get_private_chat(self, user_a: int, user_b: int) -> Optional[int]:
        """Ищет ID существующего приватного чата между двумя пользователями"""
        from sqlalchemy import text

        sql = text("""
            SELECT cp1.chat_id 
            FROM chat_participants cp1
            JOIN chat_participants cp2 ON cp1.chat_id = cp2.chat_id
            JOIN chats c ON cp1.chat_id = c.id
            WHERE c.type = 'private'
              AND cp1.employee_id = :u1
              AND cp2.employee_id = :u2
            LIMIT 1
        """)

        result = self.session.execute(sql, {"u1": user_a, "u2": user_b}).fetchone()
        return result[0] if result else None

    def create_chat(self, title: str, chat_type: str, project_id: Optional[int] = None) -> Chat:
        """Создает запись чата и возвращает объект"""
        chat = Chat(
            title=title,
            type=chat_type,
            project_id=project_id,
            created_at=datetime.now()
        )
        self.session.add(chat)
        self.session.flush()  # Получаем ID без фиксации транзакции
        return chat

    def add_participant(self, chat_id: int, employee_id: int):
        """Добавляет участника в чат"""
        participant = ChatParticipant(
            chat_id=chat_id,
            employee_id=employee_id
        )
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

    def mark_as_read(self, message_id: int, user_id: int):
        stmt = insert(MessageRead).values(
            message_id=message_id,
            user_id=user_id
        ).on_conflict_do_nothing()
        self.session.execute(stmt)

    def get_who_read(self, message_id: int):
        """Возвращает список ФИО сотрудников, прочитавших сообщение"""
        stmt = (
            select(ExternalEmployee.last_name, ExternalEmployee.first_name)
            .join(MessageRead, ExternalEmployee.id == MessageRead.user_id)
            .where(MessageRead.message_id == message_id)
        )
        results = self.session.execute(stmt).all()
        return [f"{r.last_name} {r.first_name[0]}." for r in results]

    def is_message_read_by_anyone(self, message_id: int, sender_id: int) -> bool:
        """Проверка: есть ли хоть одна запись в message_reads от другого человека"""
        from models.chat import MessageRead
        stmt = select(MessageRead).where(
            MessageRead.message_id == message_id,
            MessageRead.user_id != sender_id
        ).limit(1)
        return self.session.scalar(stmt) is not None

    def get_messages(self, chat_id: int, limit: int = 50) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = list(self.session.scalars(stmt).unique())
        return result[::-1]  # Переворачиваем для хронологии