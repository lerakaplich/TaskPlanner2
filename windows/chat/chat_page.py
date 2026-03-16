# windows/chat/chat_page.py

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from models.schemas.chat_dto import MessageReadDTO
from windows.chat.chat_message_widget import ChatMessageWidget
from windows.chat.chat_messages_separator import NewMessagesSeparator
from windows.chat.chat_view import ChatView


class ChatPage(QWidget):
    new_message_signal = pyqtSignal(MessageReadDTO)

    def __init__(self, session, service, projects_service, current_user_id, sio):
        super().__init__()
        self.session = session
        self.service = service
        self.projects_service = projects_service
        self.current_user_id = current_user_id
        self.current_chat_id = None
        self.editing_message_id = None
        self.reply_message_id = None  # Добавляем это
        self.sio = sio

        # Инициализируем UI
        self.ui = ChatView()
        self.messages_layout = self.ui.messages_layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # СОЕДИНЯЕМ СИГНАЛ С МЕТОДОМ ОТРИСОВКИ
        self.new_message_signal.connect(self.append_message_to_ui)

        # Настраиваем обработчик сокета
        self.sio.on('new_message', self.on_socket_message)

        # Таймер для проверки видимых сообщений (раз в 500мс, чтобы не грузить процессор)
        self.read_tracker_timer = QTimer()
        self.read_tracker_timer.timeout.connect(self.check_visible_messages)
        self.read_tracker_timer.start(500)
        # Список ID, которые мы уже отправили как "прочитанные", чтобы не слать дубли
        self.already_marked_read = set()

        self.sio.on('messages_read_update', self.on_messages_read_update)

        # Привязываем события
        self.ui.chat_list.itemClicked.connect(self.on_chat_selected)
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.message_input.returnPressed.connect(self.send_message)
        self.ui.btn_create_chat.clicked.connect(self.open_create_chat_dialog)
        self.ui.btn_cancel_edit.clicked.connect(self.cancel_editing)

        # 1. При ручном скролле проверяем положение
        self.ui.scroll_area.verticalScrollBar().valueChanged.connect(self.handle_scroll)

        # 2. При нажатии на кнопку "Вниз" — крутим принудительно (force=True)
        self.ui.btn_scroll_down.clicked.connect(lambda: self.scroll_to_bottom(force=True))

        self.ui.scroll_area.viewport().installEventFilter(self)

        # Первичная загрузка
        self.load_chat_list()

    def on_socket_message(self, data):
        print(f"DEBUG: Получены данные от сокета: {data}") # Посмотрите, что тут прилетает!
        try:
            msg_dto = MessageReadDTO.model_validate(data)
            if msg_dto.chat_id == self.current_chat_id:
                self.new_message_signal.emit(msg_dto)
        except Exception as e:
            print(f"❌ Ошибка валидации DTO: {e}")

    def on_messages_read_update(self, data):
        # data = {"message_ids": [101, 102], "chat_id": 5}
        if data.get("chat_id") != self.current_chat_id:
            return

        target_ids = data.get("message_ids", [])
        for i in range(self.messages_layout.count()):
            widget = self.messages_layout.itemAt(i).widget()
            if isinstance(widget, ChatMessageWidget) and widget.message_id in target_ids:
                # Вызываем метод, который мы добавили в ChatMessageWidget в прошлом шаге
                if hasattr(widget, 'set_read_status'):
                    widget.set_read_status(True)

    def check_visible_messages(self):
        if not self.current_chat_id:
            return

        visible_ids = []
        viewport_rect = self.ui.scroll_area.viewport().rect()

        # Перебираем все виджеты в лайауте сообщений
        for i in range(self.messages_layout.count()):
            widget = self.messages_layout.itemAt(i).widget()
            if isinstance(widget, ChatMessageWidget):
                # Если сообщение не наше И еще не помечено нами как прочитанное
                if not widget.is_mine and widget.message_id not in self.already_marked_read:
                    # Проверяем, находится ли виджет в зоне видимости
                    widget_pos = widget.mapTo(self.ui.scroll_area.viewport(), widget.rect().topLeft())
                    if viewport_rect.contains(widget_pos):
                        visible_ids.append(widget.message_id)
                        self.already_marked_read.add(widget.message_id)

        if visible_ids:
            # Шлем на сервер
            self.sio.emit('messages_seen', {
                "chat_id": self.current_chat_id,
                "user_id": self.current_user_id,
                "message_ids": visible_ids
            })

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
        new_chat_id = item.data(Qt.ItemDataRole.UserRole)
        if self.current_chat_id == new_chat_id: return

        if self.current_chat_id:
            self.sio.emit('leave_chat', {'chat_id': self.current_chat_id})

        self.current_chat_id = new_chat_id
        self.sio.emit('join_chat', {'chat_id': self.current_chat_id})

        self.ui.chat_header.setText(item.text())

        # Сначала грузим историю, позиционируемся,
        # а пометку "прочитано" сделает наш таймер видимости (check_visible_messages)
        self.refresh_messages()

    def refresh_messages(self):
        """Загрузка истории с разделителем новых сообщений"""
        self.clear_messages_layout()
        self.already_marked_read.clear()

        # Переменная для хранения ссылки на разделитель, чтобы потом его удалить
        self.new_messages_separator = None

        self.ui.scroll_area.setUpdatesEnabled(False)

        # Используем правильный метод загрузки истории из вашего сервиса
        messages = self.service.load_history(self.current_chat_id, self.current_user_id)
        first_unread_widget = None

        for msg in messages:
            # Если это первое непрочитанное чужое сообщение — ставим разделитель
            if not msg.is_read and not first_unread_widget and msg.sender_id != self.current_user_id:
                self.new_messages_separator = NewMessagesSeparator()
                self.messages_layout.addWidget(self.new_messages_separator)

            widget = self.append_message_to_ui(msg, force_scroll=False)

            if not msg.is_read and not first_unread_widget and msg.sender_id != self.current_user_id:
                first_unread_widget = widget

        self.ui.scroll_area.setUpdatesEnabled(True)

        if first_unread_widget:
            # Скроллим так, чтобы было видно и разделитель, и сообщение
            QTimer.singleShot(300, lambda: self.ui.scroll_area.ensureWidgetVisible(first_unread_widget, 0, 120))
        else:
            self.scroll_to_bottom(force=True)

    def clear_messages_layout(self):
        """Полная очистка всех сообщений"""
        while self.messages_layout.count() > 0:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def append_message_to_ui(self, msg_dto: MessageReadDTO, force_scroll=None) -> ChatMessageWidget | None:
        try:
            is_mine = (msg_dto.sender_id == self.current_user_id)

            msg_widget = ChatMessageWidget(
                message_id=msg_dto.id,
                text=msg_dto.content,
                sender_name=msg_dto.sender_name,
                time_str=msg_dto.time_display,
                is_mine=is_mine,
                is_read=msg_dto.is_read,
                is_edited=msg_dto.is_edited,
                reply_to_id=msg_dto.reply_to_id,
                reply_text=msg_dto.reply_text,
                reply_sender_name=getattr(msg_dto, 'reply_sender_name', None),
                forward_from_name=getattr(msg_dto, 'forward_from_name', None),
                parent=self.ui.messages_container
            )

            # Просто добавляем в конец, AlignTop сам все прижмет кверху
            self.messages_layout.addWidget(msg_widget)

            # Умный скролл (обновленная логика из прошлого шага)
            if force_scroll is False:
                pass
            elif force_scroll is True or (
                    force_scroll is None and (is_mine or not self.ui.btn_scroll_down.isVisible())):
                self.scroll_to_bottom(force=is_mine)

            return msg_widget

        except Exception as e:
            print(f"❌ Ошибка отрисовки: {e}")
            return None

    def send_message(self):
        self.remove_new_messages_separator()  # Пользователь начал активность — убираем метку
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
        else:
            # ДЛЯ ВСЕХ сообщений (и ответов, и обычных) используем сокет!
            payload = {
                "chat_id": self.current_chat_id,
                "sender_id": self.current_user_id,
                "content": text
            }
            if self.reply_message_id:
                payload["reply_to_id"] = self.reply_message_id

            # Отправляем на сервер
            self.sio.emit('send_chat_msg', payload)

            # Очищаем ввод и закрываем панели
            self.ui.message_input.clear()
            if self.reply_message_id:
                self.cancel_editing()

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

    def scroll_to_bottom(self, force=False):
        """
        Универсальный метод прокрутки вниз.
        :param force: Если True, игнорирует положение пользователя и крутит вниз в любом случае.
        """
        v_bar = self.ui.scroll_area.verticalScrollBar()

        # Если кнопка "Вниз" скрыта (значит мы внизу) ИЛИ это наше сообщение (force=True)
        if force or not self.ui.btn_scroll_down.isVisible():
            # Используем QTimer, так как макс. значение скролла обновится только после отрисовки виджета
            QTimer.singleShot(50, lambda: v_bar.setValue(v_bar.maximum()))

    def handle_scroll(self, value):
        """Отслеживает положение скролла для показа кнопки 'Вниз'"""
        v_bar = self.ui.scroll_area.verticalScrollBar()
        # Разница между максимумом и текущим положением
        dist_from_bottom = v_bar.maximum() - value

        # Показываем кнопку, если отмотали вверх более чем на 150px
        self.ui.btn_scroll_down.setVisible(dist_from_bottom > 150)

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

    def remove_new_messages_separator(self):
        """Удаляет красную черту 'Новые сообщения'"""
        if hasattr(self, 'new_messages_separator') and self.new_messages_separator:
            self.messages_layout.removeWidget(self.new_messages_separator)
            self.new_messages_separator.deleteLater()
            self.new_messages_separator = None

    def eventFilter(self, source, event):
        # Если нажали мышкой в области чата — убираем полоску
        if event.type() == event.Type.MouseButtonPress:
            self.remove_new_messages_separator()
        return super().eventFilter(source, event)