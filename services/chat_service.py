from typing import List, Optional
from sqlalchemy.orm import Session
from repositories.chat_repo import ChatRepo
from repositories.external_employee_repo import ExternalEmployeeRepo
from models.schemas.chat_dto import MessageReadDTO, ChatReadDTO
from models.chat import ChatType, ChatMessage


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

    def load_history(self, chat_id: int, current_user_id: int, limit: int = 50, offset: int = 0) -> List[
        MessageReadDTO]:
        messages = self.chat_repo.get_messages(chat_id, current_user_id, limit, offset)
        dtos = []

        for m in messages:
            # Создаем DTO (здесь заполняются текст, дата, автор)
            dto = self._prepare_message_dto(m)

            # Устанавливаем статус прочтения (проверяем наличие записей в MessageRead)
            # Убедитесь, что метод is_message_read_by_anyone возвращает True/False
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

    def _to_message_dto(self, msg: ChatMessage, user_id: int) -> MessageReadDTO:
        is_read_by_me = any(r.user_id == user_id for r in msg.reads) if hasattr(msg, 'reads') else False

        # Ответы
        reply_text = None
        reply_sender_name = None
        if msg.replied_to_message:
            reply_text = msg.replied_to_message.content
            reply_sender_name = self.emp_repo.get_full_name(msg.replied_to_message.sender_id)

        # Пересылка
        forward_name = None
        if msg.forward_from_id:
            forward_name = self.emp_repo.get_full_name(msg.forward_from_id)

        return MessageReadDTO(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            sender_name=self.emp_repo.get_full_name(msg.sender_id),
            content=msg.content,
            created_at=msg.created_at,
            time_display=msg.created_at.strftime("%H:%M"),
            is_read=is_read_by_me,
            is_edited=msg.is_edited,  # Это @property в модели ChatMessage
            is_deleted=msg.is_deleted,
            reply_to_id=msg.reply_to_id,
            reply_text=reply_text,
            reply_sender_name=reply_sender_name,
            forward_from_name=forward_name
        )

    def get_first_unread_offset(self, chat_id: int, user_id: int) -> int:
        """Находит позицию первого непрочитанного сообщения"""
        unread_count = self.chat_repo.get_unread_count(chat_id, user_id)
        if unread_count == 0:
            return 0  # Все прочитано, берем последние 50

        # Если есть непрочитанные, берем их с небольшим запасом старых сообщений (например, 10 сверху)
        return max(0, unread_count - 10)

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
        # Убеждаемся, что тип чата — это Enum
        chat_type = ChatType(data["type"])

        if chat_type == ChatType.private:
            created_chats = []
            # Предполагаем, что в data["participants"] список ID собеседников
            for target_id in data["participants"]:
                # Пропускаем, если пытаемся создать чат с самим собой (на всякий случай)
                if int(target_id) == int(creator_id):
                    continue

                # 1. Проверяем, существует ли уже чат 1-на-1
                existing_chat_id = self.chat_repo.get_private_chat(creator_id, target_id)

                if existing_chat_id:
                    print(f"ℹ️ Чат с пользователем {target_id} уже существует (ID: {existing_chat_id})")
                    continue

                    # 2. Создаем новый приватный чат
                # ВАЖНО: передаем None или пустую строку в title, так как это private
                # Аргументы: title, chat_type
                new_chat = self.chat_repo.create_chat(
                    title=None,
                    chat_type=chat_type.value  # .value, так как в репозитории ожидается str
                )

                # Добавляем участников (используем is_admin из предыдущего шага)
                self.chat_repo.add_participant(new_chat.id, creator_id, is_admin=True)
                self.chat_repo.add_participant(new_chat.id, target_id, is_admin=True)

                created_chats.append(new_chat)

            self.session.commit()
            return created_chats

        else:  # Логика для GROUP / PROJECT
            # Исправляем порядок: сначала title, потом type
            new_chat = self.chat_repo.create_chat(
                title=data.get("title", "Групповой чат"),
                chat_type=chat_type.value,
                project_id=data.get("project_id")
            )

            # Создатель — админ
            self.chat_repo.add_participant(new_chat.id, creator_id, is_admin=True)

            # Остальные участники — не админы
            for emp_id in data["participants"]:
                if int(emp_id) != int(creator_id):
                    self.chat_repo.add_participant(new_chat.id, emp_id, is_admin=False)

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

    def get_chat_details(self, chat_id: int):
        """Метод сервиса: получает данные из репозитория и обогащает именами"""
        chat = self.chat_repo.get_chat_with_participants(chat_id)
        if not chat:
            return None

        # Наполняем объекты участников ФИО
        for p in chat.participants:
            # Используем ваш emp_repo для получения данных сотрудника
            emp = self.emp_repo.get_by_id(p.employee_id)
            if emp:
                p.full_name = f"{emp.last_name} {emp.first_name}"
            else:
                p.full_name = f"Сотрудник #{p.employee_id}"

        return chat

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

    def delete_chat(self, chat_id: int) -> bool:
        success = self.chat_repo.delete_chat(chat_id)
        if success:
            self.session.commit()
        return success

    def update_chat_participants(self, chat_id: int, added_ids: list[int], removed_ids: list[int]):
        try:
            if added_ids:
                self.chat_repo.add_participants(chat_id, added_ids)
            if removed_ids:
                self.chat_repo.remove_participants(chat_id, removed_ids)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error updating participants: {e}")
            return False