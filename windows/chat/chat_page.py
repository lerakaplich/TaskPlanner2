# windows/chat/chat_page.py

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt

from models.schemas.chat_dto import MessageReadDTO
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
        self.editing_message_id = None
        self.reply_message_id = None  # Добавляем это

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
        self.ui.btn_cancel_edit.clicked.connect(self.cancel_editing)

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
            is_edited=msg_dto.is_edited,  # <--- Проверь это место!
            parent=self.ui.messages_container  # Лучше передавать контейнер как родителя
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
        if not text:
            return

        if self.editing_message_id:
            # --- РЕЖИМ СОХРАНЕНИЯ ПРАВОК ---
            if self.service.update_message(self.editing_message_id, text):
                # 1. Сбрасываем режим редактирования (скроет плашку и очистит поле)
                self.cancel_editing()
                # 2. Обновляем чат, чтобы увидеть надпись "ред."
                self.refresh_messages()
        elif self.reply_message_id:
            # ОТВЕТ
            self.service.save_reply(self.current_chat_id, self.current_user_id, text, self.reply_message_id)
            self.cancel_editing()  # Очистит всё
            self.refresh_messages()
        else:
            # --- ОБЫЧНАЯ ОТПРАВКА ---
            new_msg = self.service.save_new_message(
                chat_id=self.current_chat_id,
                sender_id=self.current_user_id,
                content=text
            )
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

    def display_message(self, msg_dto: MessageReadDTO):
        is_mine = (msg_dto.sender_id == self.current_user_id)

        # ПЕРЕДАЕМ ВСЕ НОВЫЕ ПАРАМЕТРЫ В ВИДЖЕТ
        msg_widget = ChatMessageWidget(
            message_id=msg_dto.id,
            text=msg_dto.content,
            sender_name=msg_dto.sender_name,
            time_str=msg_dto.time_display,
            is_mine=is_mine,
            is_read=msg_dto.is_read,
            is_edited=msg_dto.is_edited,
            # ВОТ ЭТИ ПОЛЯ:
            reply_to_id=msg_dto.reply_to_id,
            reply_text=msg_dto.reply_text,
            reply_sender_name=getattr(msg_dto, 'reply_sender_name', None),  # берем если есть
            forward_from_name=msg_dto.forward_from_name,
            parent=self.ui.messages_container
        )
        msg_widget.action_triggered.connect(self.handle_message_action)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg_widget)
        self.scroll_to_bottom()

    def handle_message_action(self, action_type, message_id):
        """Обработка действий из контекстного меню сообщения"""
        if action_type == "delete":
            if self.service.delete_message(message_id):
                self.refresh_messages()
        elif action_type == "edit":
            # Получаем актуальные данные сообщения из базы через сервис
            msg = self.service.get_message_by_id(message_id)
            if msg:
                # Вызываем новый метод, который настроит UI
                self.start_editing(message_id, msg.content)
        elif action_type == "reply":
            msg = self.service.get_message_by_id(message_id)
            if msg:
                self.start_replying(message_id, msg.content, msg.sender_name)
        elif action_type == "forward":
            self.open_forward_dialog(message_id)
        elif action_type == "goto":
            self.scroll_to_message(message_id)

    def scroll_to_bottom(self):
        """Прокрутка чата вниз"""
        # Используем QTimer, чтобы прокрутка сработала после того, как виджет отрисуется
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, lambda: self.ui.scroll_area.verticalScrollBar().setValue(
            self.ui.scroll_area.verticalScrollBar().maximum()
        ))

    def scroll_to_message(self, message_id: int):
        # 1. Ищем нужный виджет среди дочерних элементов layout'а сообщений
        target_widget = None
        container = self.ui.messages_container  # Тот, где лежит QVBoxLayout с сообщениями

        for i in range(container.layout().count()):
            item = container.layout().itemAt(i)
            if not item: continue
            widget = item.widget()
            # Проверяем, что это ChatMessageWidget и ID совпадает
            if isinstance(widget, ChatMessageWidget) and widget.message_id == message_id:
                target_widget = widget
                break

        if target_widget:
            # 2. Прокручиваем ScrollArea к виджету
            self.ui.scroll_area.ensureWidgetVisible(target_widget, 0, 200)

            # 3. Эффект выделения (как в TG — мигнуть цветом)
            target_widget.highlight()

    def start_editing(self, message_id, original_text):
        """Вызывается при нажатии 'Редактировать' в контекстном меню"""
        self.editing_message_id = message_id

        # 1. Показываем панель только для чтения (индикатор)
        # Обрезаем текст для превью, если он слишком длинный
        preview = original_text if len(original_text) < 60 else original_text[:57] + "..."
        self.ui.edit_label.setText(preview)
        self.ui.edit_panel.setVisible(True)

        # 2. Переносим текст в поле ввода для ФАКТИЧЕСКОГО редактирования
        self.ui.message_input.setText(original_text)
        self.ui.message_input.setFocus()

        # 3. Меняем иконку кнопки на галочку
        self.ui.btn_send.setText("✅")

    def cancel_editing(self):
        """Вызывается при нажатии на крестик в edit_panel"""
        self.editing_message_id = None
        self.ui.edit_panel.setVisible(False)
        self.ui.message_input.clear()
        self.ui.btn_send.setText("➤")

    def start_replying(self, message_id, text, sender):
        self.reply_message_id = message_id
        self.ui.edit_label.setText(f"Ответ пользователю {sender}: {text[:40]}...")
        self.ui.edit_panel.setVisible(True)
        self.ui.btn_send.setText("↪️")  # Меняем иконку
        self.ui.message_input.setFocus()