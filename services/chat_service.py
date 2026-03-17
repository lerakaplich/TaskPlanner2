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
        messages = self.chat_repo.get_messages(chat_id, current_user_id)
        dtos = []

        for m in messages:
            dto = self._prepare_message_dto(m)

            # 3. Дополнительно проверяем статус прочтения (как и было)
            dto.is_read = self.chat_repo.is_message_read_by_anyone(m.id, m.sender_id)

            dtos.append(dto)

        return dtos

    def save_new_message(self, chat_id: int, sender_id: int, content: str,
                         reply_to_id: int = None,
                         forward_from_id: int = None) -> MessageReadDTO:
        # Теперь передаем все аргументы в репозиторий
        msg_orm = self.chat_repo.create_message(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
            forward_from_id=forward_from_id
        )
        self.session.commit()
        self.session.refresh(msg_orm)
        return self._prepare_message_dto(msg_orm)

    def _prepare_message_dto(self, msg) -> MessageReadDTO:
        sender_name = self.emp_repo.get_full_name(msg.sender_id)

        reply_text = None
        reply_sender_name = None  # Новое
        if msg.replied_to_message:
            reply_text = msg.replied_to_message.content
            # Получаем имя автора оригинального сообщения
            reply_sender_name = self.emp_repo.get_full_name(msg.replied_to_message.sender_id)
            if len(reply_text) > 50: reply_text = reply_text[:47] + "..."

        # Получаем имя автора оригинала
        forward_from_name = None
        if msg.forward_from_id:
            forward_from_name = self.emp_repo.get_full_name(msg.forward_from_id)

        dto = MessageReadDTO(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            sender_name=sender_name,
            content=msg.content,
            created_at=msg.created_at,
            time_display=msg.created_at.strftime("%H:%M"),
            is_edited=msg.updated_at is not None,
            reply_to_id=msg.reply_to_id,
            reply_text=reply_text,
            forward_from_name=forward_from_name
        )
        dto.reply_sender_name = reply_sender_name  # Передаем в DTO
        return dto

    def forward_message(self, message_id: int, to_chat_id: int, current_user_id: int):
        """Пересылка сообщения в другой чат"""
        original = self.chat_repo.get_message_by_id(message_id)
        if not original: return None

        # Для пересылки forward_from_id — это либо автор оригинала,
        # либо тот, кто уже переслал (если это цепочка)
        forward_id = original.forward_from_id or original.sender_id

        new_msg = self.chat_repo.create_message(
            chat_id=to_chat_id,
            sender_id=current_user_id,
            content=original.content,
            forward_from_id=forward_id
        )
        self.session.commit()
        return self._prepare_message_dto(new_msg)

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
        messages = self.chat_repo.get_messages(chat_id, user_id)
        for m in messages:
            if m.sender_id != user_id:
                self.chat_repo.mark_as_read(m.id, user_id)
        self.session.commit()

    def mark_messages_as_read(self, user_id: int, message_ids: List[int]):
        """Помечает конкретные сообщения как прочитанные"""
        for m_id in message_ids:
            # Не помечаем свои же сообщения как прочитанные нами
            msg = self.chat_repo.get_message_by_id(m_id)
            if msg and msg.sender_id != user_id:
                self.chat_repo.mark_as_read(m_id, user_id)
        self.session.commit()

    def get_chat_messages(self, chat_id: int, current_user_id: int) -> List[MessageReadDTO]:
        messages = self.chat_repo.get_messages(chat_id, current_user_id)
        return [self._prepare_message_dto(m) for m in messages]

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

    def delete_message_for_me(self, message_id: int, user_id: int) -> bool:
        """Мягкое удаление только для конкретного пользователя"""
        success = self.chat_repo.delete_message_for_user(message_id, user_id)
        if success:
            self.session.commit()
        return success

    def delete_message_for_everyone(self, message_id: int) -> bool:
        """Удаление сообщения для всех участников чата"""
        success = self.chat_repo.delete_message_for_everyone(message_id)
        if success:
            self.session.commit()
        return success

    def save_reply(self, chat_id: int, sender_id: int, content: str, reply_to_id: int) -> MessageReadDTO:
        """Сохранение ответа на сообщение"""
        # Создаем сообщение через репозиторий с указанием reply_to_id
        msg_orm = self.chat_repo.create_message(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id
        )
        self.session.commit()
        self.session.refresh(msg_orm)

        # Возвращаем готовый DTO для отображения в интерфейсе
        return self._prepare_message_dto(msg_orm)