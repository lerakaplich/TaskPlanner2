from typing import List
from sqlalchemy.orm import Session
from repositories.chat_repo import ChatRepo
from repositories.external_employee_repo import ExternalEmployeeRepo
from models.schemas.chat_dto import MessageReadDTO, ChatReadDTO
from models.chat import ChatType


class ChatService:
    def __init__(self, db_session: Session):
        self.session = db_session
        self.chat_repo = ChatRepo(db_session)
        self.emp_repo = ExternalEmployeeRepo(db_session)

    def get_user_chats(self, user_id: int) -> List[ChatReadDTO]:
        """Загружает список чатов для отображения в левой панели"""
        chats = self.chat_repo.get_chats_for_user(user_id)
        dtos = []
        for c in chats:
            display_name = c.title or "Без названия"

            # Если это личный чат, названием должно быть имя собеседника
            if c.type == ChatType.private:
                # Находим второго участника (не текущего юзера)
                # В реальном приложении лучше сделать через подзапрос, здесь для простоты:
                other_participant = next((p for p in c.participants if p.employee_id != user_id), None)
                if other_participant:
                    display_name = self.emp_repo.get_full_name(other_participant.employee_id)

            dtos.append(ChatReadDTO(
                id=c.id,
                title=c.title,
                type=c.type.value,
                project_id=c.project_id,
                display_name=display_name
            ))
        return dtos

    def load_history(self, chat_id: int) -> List[MessageReadDTO]:
        history = self.chat_repo.get_history(chat_id)
        return [self._prepare_message_dto(m) for m in history]

    def save_new_message(self, chat_id: int, sender_id: int, content: str) -> MessageReadDTO:
        msg_orm = self.chat_repo.create_message(chat_id, sender_id, content)
        self.session.commit()
        self.session.refresh(msg_orm)
        return self._prepare_message_dto(msg_orm)

    def _prepare_message_dto(self, msg) -> MessageReadDTO:
        sender_name = self.emp_repo.get_full_name(msg.sender_id)
        return MessageReadDTO(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            sender_name=sender_name,
            content=msg.content,
            created_at=msg.created_at,
            time_display=msg.created_at.strftime("%H:%M"),
            date_display=msg.created_at.strftime("%d.%m.%Y %H:%M")
        )

    def create_new_chat(self, creator_id: int, data: dict):
        """Создает комнату и добавляет участников"""
        # 1. Создаем саму комнату
        new_chat = self.chat_repo.create_chat(
            chat_type=ChatType(data["type"]),
            title=data.get("title")
        )

        # 2. Добавляем создателя
        self.chat_repo.add_participant(new_chat.id, creator_id)

        # 3. Добавляем остальных участников
        for emp_id in data["participants"]:
            self.chat_repo.add_participant(new_chat.id, emp_id)

        self.session.commit()
        return new_chat