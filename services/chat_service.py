from typing import List, Optional
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

    def load_history(self, chat_id: int, current_user_id: int) -> List[MessageReadDTO]:
        # Вызываем метод репозитория (который мы добавим ниже)
        messages = self.chat_repo.get_messages(chat_id)
        dtos = []

        for m in messages:
            # Проверяем, прочитал ли кто-то сообщение (для галочек)
            is_read = self.chat_repo.is_message_read_by_anyone(m.id, m.sender_id)

            dtos.append(MessageReadDTO(
                id=m.id,
                chat_id=chat_id,  # Исправлено
                sender_id=m.sender_id,
                sender_name=self.emp_repo.get_full_name(m.sender_id),
                content=m.content,
                created_at=m.created_at,
                time_display=m.created_at.strftime("%H:%M"),
                is_read=is_read
            ))
        return dtos

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
            is_edited=msg.updated_at is not None  # Если дата есть — значит редактировалось
        )

    def create_new_chat(self, creator_id: int, data: dict):
        chat_type = ChatType(data["type"])

        if chat_type == ChatType.private:
            created_chats = []
            for target_id in data["participants"]:
                # 1. Проверяем, существует ли уже чат 1-на-1
                existing_chat_id = self.chat_repo.get_private_chat(creator_id, target_id)

                if existing_chat_id:
                    print(f"ℹ️ Чат с пользователем {target_id} уже существует (ID: {existing_chat_id})")
                    continue  # Пропускаем создание дубликата

                # 2. Если нет — создаем новый
                new_chat = self.chat_repo.create_chat(chat_type=ChatType.private)
                self.chat_repo.add_participant(new_chat.id, creator_id)
                self.chat_repo.add_participant(new_chat.id, target_id)
                created_chats.append(new_chat)

            self.session.commit()
            return created_chats

        else:  # Логика для GROUP
            new_chat = self.chat_repo.create_chat(chat_type=ChatType.group, title=data["title"])
            self.chat_repo.add_participant(new_chat.id, creator_id)
            for emp_id in data["participants"]:
                self.chat_repo.add_participant(new_chat.id, emp_id)

            self.session.commit()
            return [new_chat]

    def get_message_read_info(self, message_id: int) -> str:
        names = self.chat_repo.get_who_read(message_id)
        if not names:
            return "Никто еще не прочитал"
        return "Прочитали: " + ", ".join(names)

    def mark_chat_as_read(self, chat_id: int, user_id: int):
        """Помечает все входящие сообщения как прочитанные текущим пользователем"""
        messages = self.chat_repo.get_messages(chat_id)
        for m in messages:
            if m.sender_id != user_id:
                self.chat_repo.mark_as_read(m.id, user_id)
        self.session.commit()

    def get_chat_messages(self, chat_id: int, current_user_id: int) -> List[MessageReadDTO]:
        messages = self.chat_repo.get_messages(chat_id)
        dtos = []
        for m in messages:
            # Проверяем статус прочтения
            is_read = self.chat_repo.is_message_read_by_anyone(m.id, m.sender_id)

            dtos.append(MessageReadDTO(
                id=m.id,
                chat_id=m.chat_id,
                sender_id=m.sender_id,
                sender_name=m.sender.first_name if m.sender else "Система",
                content=m.content,
                created_at=m.created_at,
                time_display=m.created_at.strftime("%H:%M"),
                is_read=is_read,  # 👈 Передаем статус
                is_edited=m.updated_at is not None
            ))
        return dtos

    def get_message_by_id(self, message_id: int) -> Optional[MessageReadDTO]:
        """Получает сообщение из БД и превращает его в DTO для UI"""
        msg = self.chat_repo.get_message_by_id(message_id)
        if msg:
            return self._prepare_message_dto(msg)
        return None

    def update_message(self, message_id: int, new_content: str) -> bool:
        """Обновляет текст сообщения через репозиторий"""
        # Репозиторий сам делает commit() в вашем методе update_message_content
        return self.chat_repo.update_message_content(message_id, new_content)