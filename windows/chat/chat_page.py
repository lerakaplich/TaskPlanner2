# windows/chat/chat_page.py

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt

from windows.chat.chat_message_widget import ChatMessageWidget
from windows.chat.chat_view import ChatView


class ChatPage(QWidget):
    def __init__(self, session, service, projects_service, current_user_id):
        super().__init__()
        self.session = session
        self.service = service
        self.projects_service = projects_service
        self.current_user_id = current_user_id
        self.current_chat_id = None

        # Инициализируем UI
        self.ui = ChatView()
        self.messages_layout = self.ui.messages_layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # Привязываем события
        self.ui.chat_list.itemClicked.connect(self.on_chat_selected)
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.message_input.returnPressed.connect(self.send_message)
        self.ui.btn_create_chat.clicked.connect(self.open_create_chat_dialog)

        # Первичная загрузка
        self.load_chat_list()

    def load_chat_list(self):
        """Загрузка универсального списка чатов (проекты, группы, личные)"""
        self.ui.chat_list.clear()
        try:
            # Используем обновленный ChatService
            chats = self.service.get_user_chats(self.current_user_id)

            for chat in chats:
                # Иконка зависит от типа чата
                icon = "📁" if chat.type == "project" else "👥" if chat.type == "group" else "👤"
                item = QListWidgetItem(f"{icon} {chat.display_name}")
                item.setData(Qt.ItemDataRole.UserRole, chat.id)
                self.ui.chat_list.addItem(item)

            print(f"✅ Загружено чатов: {len(chats)}")
        except Exception as e:
            print(f"❌ Ошибка загрузки списка чатов: {e}")

    def on_chat_selected(self, item):
        self.current_chat_id = item.data(Qt.ItemDataRole.UserRole)

        # Помечаем прочитанным при открытии
        self.service.mark_chat_as_read(self.current_chat_id, self.current_user_id)

        self.ui.chat_header.setText(item.text())
        self.refresh_messages()

    def refresh_messages(self):
        """Перезагрузка сообщений текущего чата"""
        if self.current_chat_id:
            self.clear_messages_layout()
            messages = self.service.get_chat_messages(self.current_chat_id, self.current_user_id)
            for m in messages:
                self.display_message(m)

    def clear_messages_layout(self):
        """Удаляет все виджеты сообщений, оставляя только spacer в конце"""
        while self.messages_layout.count() > 1:  # Оставляем 1, так как последний — это spacer
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def append_message_to_ui(self, msg_dto):
        """Отрисовка одного сообщения в виде пузырька"""
        is_mine = (msg_dto.sender_id == self.current_user_id)

        # Создаем виджет пузырька
        msg_widget = ChatMessageWidget(
            message_id=msg_dto.id,
            text=msg_dto.content,
            sender_name=msg_dto.sender_name,
            time_str=msg_dto.time_display,
            is_mine=is_mine,
            is_read=msg_dto.is_read,
            parent=self
        )

        # Подключаем контекстное меню (удаление/редактирование)
        msg_widget.action_triggered.connect(self.handle_message_action)

        # Вставляем виджет в лейаут ПЕРЕД распоркой (spacer)
        # self.ui.messages_layout — это ваш QVBoxLayout из ChatView
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg_widget)

        # Прокручиваем вниз
        self.scroll_to_bottom()

    def send_message(self):
        text = self.ui.message_input.text().strip()
        if not text or not self.current_chat_id:
            return

        # 1. Сохраняем в БД через сервис
        new_msg = self.service.save_new_message(
            chat_id=self.current_chat_id,
            sender_id=self.current_user_id,
            content=text
        )

        # 2. Очищаем ввод и добавляем в UI (в будущем здесь будет сигнал Socket.IO)
        self.ui.message_input.clear()
        self.append_message_to_ui(new_msg)

    def open_create_chat_dialog(self):
        from windows.chat.chat_create_dialog import ChatCreateDialog

        # В ChatService мы уже инициализировали self.emp_repo = ExternalEmployeeRepo(db_session)
        # Используем его:
        dialog = ChatCreateDialog(
            emp_repo=self.service.emp_repo,
            current_user_id=self.current_user_id,
            parent=self
        )

        if dialog.exec():
            data = dialog.get_data()
            self.service.create_new_chat(self.current_user_id, data)
            self.load_chat_list()

    def display_message(self, msg_dto):
        is_mine = (msg_dto.sender_id == self.current_user_id)

        msg_widget = ChatMessageWidget(
            message_id=msg_dto.id,
            text=msg_dto.content,
            sender_name=msg_dto.sender_name,
            time_str=msg_dto.time_display,
            is_mine=is_mine,
            is_read=msg_dto.is_read
        )
        msg_widget.action_triggered.connect(self.handle_message_action)

        # Вставляем ПЕРЕД распоркой (spacer)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg_widget)
        self.scroll_to_bottom()

    def handle_message_action(self, action_type, message_id):
        """Обработка действий из контекстного меню сообщения"""
        if action_type == "delete":
            # Вызываем метод удаления из репозитория/сервиса
            if self.service.delete_message(message_id):
                self.refresh_messages()  # Обновляем список после удаления

        elif action_type == "edit":
            # Находим сообщение, чтобы перенести текст в поле ввода
            msg = self.service.get_message_by_id(message_id)
            if msg:
                self.ui.message_input.setText(msg.content)
                self.ui.message_input.setFocus()
                self.editing_message_id = message_id
                self.ui.btn_send.setText("Сохранить")

    def scroll_to_bottom(self):
        """Прокрутка чата вниз"""
        # Используем QTimer, чтобы прокрутка сработала после того, как виджет отрисуется
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, lambda: self.ui.scroll_area.verticalScrollBar().setValue(
            self.ui.scroll_area.verticalScrollBar().maximum()
        ))