from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, update, delete
from sqlalchemy.dialects.postgresql.dml import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func

from models.chat import Chat, ChatMessage, ChatParticipant, ChatType, MessageRead, DeletedMessage
from models.employees import Employee
from sqlalchemy.orm import selectinload

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

    def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        return self.session.get(Chat, chat_id)

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

    def get_chat_with_participants(self, chat_id: int) -> Optional[Chat]:
        """Возвращает чат с предзагруженными участниками"""
        stmt = (
            select(Chat)
            .options(
                selectinload(Chat.participants)
            )
            .where(Chat.id == chat_id)
        )
        return self.session.scalar(stmt)

    def get_participant(self, chat_id: int, employee_id: int) -> Optional[ChatParticipant]:
        """Получить объект участника чата для проверки его свойств (например, is_admin)"""
        stmt = select(ChatParticipant).where(
            and_(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.employee_id == employee_id
            )
        )
        return self.session.scalar(stmt)

    def add_participant(self, chat_id: int, employee_id: int, is_admin: bool = False):
        """Добавляет участника в чат"""
        try:
            # Убираем аргумент role, заменяем на is_admin
            participant = ChatParticipant(
                chat_id=chat_id,
                employee_id=employee_id,
                is_admin=is_admin
            )
            self.session.add(participant)
            self.session.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении участника: {e}")
            self.session.rollback()
            return False

    def add_participants(self, chat_id: int, user_ids: list[int]):
        for uid in user_ids:
            # Проверяем, нет ли его уже там (на всякий случай)
            stmt = select(ChatParticipant).where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.employee_id == uid
            )
            if not self.session.scalar(stmt):
                p = ChatParticipant(chat_id=chat_id, employee_id=uid)
                self.session.add(p)

    def update_chat_info(self, chat_id: int, title: str):
        stmt = update(Chat).where(Chat.id == chat_id).values(title=title)
        self.session.execute(stmt)

    def remove_participant(self, chat_id: int, emp_id: int):
        stmt = delete(ChatParticipant).where(
            and_(ChatParticipant.chat_id == chat_id, ChatParticipant.employee_id == emp_id)
        )
        self.session.execute(stmt)

    def remove_participants(self, chat_id: int, user_ids: list[int]):
        from sqlalchemy import delete
        stmt = delete(ChatParticipant).where(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.employee_id.in_(user_ids)
        )
        self.session.execute(stmt)

    def delete_chat(self, chat_id: int) -> bool:
        try:
            chat = self.session.get(Chat, chat_id)
            if chat:
                self.session.delete(chat)
                return True
            return False
        except Exception:
            return False

    def create_message(self, chat_id: int, sender_id: int, content: str,
                       reply_to_id: Optional[int] = None,
                       forward_from_id: Optional[int] = None) -> ChatMessage:
        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
            forward_from_id=forward_from_id
        )
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
            select(Employee.last_name, Employee.first_name)  # ← ИСПРАВЛЕНО
            .join(MessageRead, Employee.id == MessageRead.user_id)
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

    def get_messages(self, chat_id: int, user_id: int, limit: int = 50, offset: int = 0) -> List[ChatMessage]:
        hidden_ids = select(DeletedMessage.message_id).where(DeletedMessage.user_id == user_id)

        stmt = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.reads))  # ПРЕДЗАГРУЗКА прочтений
            .where(
                and_(
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.id.not_in(hidden_ids)
                )
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        messages = list(self.session.scalars(stmt))
        return messages[::-1]

    def get_chat_messages_count(self, chat_id: int, user_id: int) -> int:
        """Общее количество доступных сообщений в чате"""
        hidden_ids = select(DeletedMessage.message_id).where(DeletedMessage.user_id == user_id)
        stmt = select(func.count(ChatMessage.id)).where(
            and_(ChatMessage.chat_id == chat_id, ChatMessage.id.not_in(hidden_ids))
        )
        return self.session.execute(stmt).scalar() or 0

    def get_unread_count(self, chat_id: int, user_id: int) -> int:
        """Считает количество непрочитанных пользователем чужих сообщений"""
        read_subquery = select(MessageRead.message_id).where(MessageRead.user_id == user_id)
        stmt = select(func.count(ChatMessage.id)).where(
            and_(
                ChatMessage.chat_id == chat_id,
                ChatMessage.sender_id != user_id,
                ChatMessage.id.not_in(read_subquery)
            )
        )
        return self.session.execute(stmt).scalar() or 0

    def update_message_content(self, message_id: int, new_content: str):
        try:
            stmt = (
                update(ChatMessage)
                .where(ChatMessage.id == message_id)
                .values(
                    content=new_content,
                    updated_at=datetime.now()  # Фиксируем время изменения
                )
            )
            self.session.execute(stmt)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            self.session.rollback()
            return False

    def get_message_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """Получить одно сообщение по его ID"""
        return self.session.get(ChatMessage, message_id)

    def delete_message_for_everyone(self, message_id: int):
        """Мягкое удаление для всех: сообщение просто помечается удаленным"""
        try:
            stmt = (
                update(ChatMessage)
                .where(ChatMessage.id == message_id)
                .values(
                    is_deleted=True  # Используем существующий флаг
                    # ТЕКСТ НЕ МЕНЯЕМ, updated_at НЕ ТРОГАЕМ
                )
            )
            self.session.execute(stmt)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            return False

    def delete_message_for_user(self, message_id: int, user_id: int):
        try:
            # Проверяем наличие записи
            exists_stmt = select(DeletedMessage).where(
                DeletedMessage.message_id == message_id,
                DeletedMessage.user_id == user_id
            )
            if self.session.scalar(exists_stmt):
                return True

            # Создаем запись в chat_hidden_messages
            new_hidden = DeletedMessage(message_id=message_id, user_id=user_id)
            self.session.add(new_hidden)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Ошибка скрытия сообщения: {e}")
            self.session.rollback()
            return False

    def update_participant_role(self, chat_id: int, emp_id: int, is_admin: bool):
        stmt = update(ChatParticipant).where(
            and_(ChatParticipant.chat_id == chat_id, ChatParticipant.employee_id == emp_id)
        ).values(is_admin=is_admin)
        self.session.execute(stmt)
        self.session.commit()