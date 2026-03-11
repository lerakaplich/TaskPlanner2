# windows/chat/chat_page.py

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt
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
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_chat_id = chat_id
        self.ui.chat_header.setText(item.text())
        self.refresh_messages()

    def refresh_messages(self):
        """Подгрузка истории сообщений для выбранного чата"""
        if not self.current_chat_id:
            return

        self.ui.chat_history.clear()
        history = self.service.load_history(self.current_chat_id)
        for msg in history:
            self.append_message_to_ui(msg)

    def append_message_to_ui(self, msg_dto):
        """Отрисовка одного сообщения с простым HTML-стилем"""
        is_my_msg = msg_dto.sender_id == self.current_user_id
        color = "#2c3e50" if not is_my_msg else "#D22730"
        align = "left" if not is_my_msg else "right"

        html = f"""
            <div style="margin-bottom: 10px;">
                <b style="color: {color};">{msg_dto.sender_name}</b> 
                <small style="color: gray;">{msg_dto.time_display}</small><br>
                {msg_dto.content}
            </div>
        """
        self.ui.chat_history.append(html)

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