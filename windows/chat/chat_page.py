# windows/chat/chat_page.py
from typing import Optional

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from models.schemas.chat_dto import MessageReadDTO, MessageEditDTO, MessageDeleteDTO
from windows.chat.chat_forward_dialog import ForwardDialog
from windows.chat.chat_message_widget import ChatMessageWidget
from windows.chat.chat_messages_separator import NewMessagesSeparator
from windows.chat.chat_settings_dialog import ChatSettingsDialog
from windows.chat.chat_view import ChatView


class ChatPage(QWidget):
    new_message_signal = pyqtSignal(MessageReadDTO)
    message_edited_signal = pyqtSignal(MessageEditDTO)
    message_deleted_signal = pyqtSignal(MessageDeleteDTO)

    def __init__(self, session, service, projects_service, current_user_id, sio):
        super().__init__()
        self.session = session
        self.service = service  # ChatService с EmployeeRepo внутри
        self.projects_service = projects_service
        self.current_user_id = current_user_id
        self.current_chat_id = None
        self.editing_message_id = None
        self.reply_message_id = None
        self.sio = sio

        self.offset_old = 0
        self.offset_new = 0
        self.loading = False
        self.current_offset = 0
        self.all_messages_loaded = False

        self.selection_mode = False
        self.selected_messages = set()

        # Инициализируем UI
        self.ui = ChatView()
        self.selection_toolbar = self.ui.selection_toolbar
        self.lbl_sel_count = self.ui.lbl_sel_count
        self.messages_layout = self.ui.messages_layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # СОЕДИНЯЕМ СИГНАЛ С МЕТОДОМ ОТРИСОВКИ
        self.new_message_signal.connect(self.append_message_to_ui)

        # Настраиваем обработчик сокета
        self.sio.sio.on('new_message', self.on_socket_message)
        self.sio.sio.on('message_edited', self.on_socket_message_edited)
        self.sio.sio.on('message_deleted', self.on_socket_message_deleted)

        # Таймер для проверки видимых сообщений (раз в 500мс, чтобы не грузить процессор)
        self.read_tracker_timer = QTimer()
        self.read_tracker_timer.timeout.connect(self.check_visible_messages)
        self.read_tracker_timer.start(500)
        # Список ID, которые мы уже отправили как "прочитанные", чтобы не слать дубли
        self.already_marked_read = set()

        self.sio.sio.on('messages_read_update', self.on_messages_read_update)

        # Привязываем события
        self.ui.chat_list.itemClicked.connect(self.on_chat_selected)
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.message_input.returnPressed.connect(self.send_message)
        self.ui.btn_create_chat.clicked.connect(self.open_create_chat_dialog)
        self.ui.btn_cancel_edit.clicked.connect(self.cancel_editing)
        self.ui.btn_cancel_sel.clicked.connect(self.exit_selection_mode)
        self.ui.btn_forward_sel.clicked.connect(self.forward_selected_messages)
        self.ui.btn_chat_info.clicked.connect(self.open_chat_settings)

        self.message_edited_signal.connect(self.process_message_edit)
        self.message_deleted_signal.connect(self.process_message_delete)

        self.ui.scroll_area.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        self.ui.btn_scroll_down.clicked.connect(lambda: self.scroll_to_bottom(force=True))
        self.ui.scroll_area.viewport().installEventFilter(self)

        # Первичная загрузка
        self.load_chat_list()

    def on_socket_message(self, data):
        try:
            msg_dto = MessageReadDTO.model_validate(data)
            if msg_dto.chat_id != self.current_chat_id:
                return

            if self.all_new_loaded:
                self.new_message_signal.emit(msg_dto)
            else:
                self.increment_unread_on_button()

        except Exception as e:
            print(f"❌ Ошибка сокета: {e}")

    def on_socket_message_edited(self, data):
        try:
            dto = MessageEditDTO.model_validate(data)
            self.message_edited_signal.emit(dto)
        except Exception as e:
            print(f"❌ Ошибка валидации EditDTO: {e}")

    def on_socket_message_deleted(self, data):
        msg_id = data.get("message_id")
        chat_id = data.get("chat_id")
        mode = data.get("mode", "everyone")

        if chat_id == self.current_chat_id:
            self.remove_message_from_ui(msg_id)

    def increment_unread_on_button(self):
        """Увеличивает число непрочитанных на кнопке скролла вниз"""
        if not hasattr(self, 'unread_below_count'):
            self.unread_below_count = 0

        self.unread_below_count += 1
        self.ui.btn_scroll_down.setText(f"↓ ({self.unread_below_count})")
        self.ui.btn_scroll_down.setVisible(True)
        self.ui.btn_scroll_down.setStyleSheet("background-color: #D22730; color: white; border-radius: 15px;")

    def reset_unread_on_button(self):
        """Сбрасывает счетчик при прокрутке в самый низ"""
        self.unread_below_count = 0
        self.ui.btn_scroll_down.setText("↓")
        self.ui.btn_scroll_down.setStyleSheet("")

    def update_widget_visually_deleted(self, message_id):
        """Находит виджет сообщения и помечает его удаленным (серым)"""
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for w in widgets:
            if w.message_id == message_id:
                w.mark_as_deleted()
                break

    def remove_widget_from_layout(self, message_id):
        """Полностью удаляет виджет с экрана (для режима 'удалить у себя')"""
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for w in widgets:
            if w.message_id == message_id:
                self.ui.messages_layout.removeWidget(w)
                w.deleteLater()
                break

    def process_message_edit(self, dto: MessageEditDTO):
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for widget in widgets:
            if int(widget.message_id) == int(dto.message_id):
                widget.update_text(dto.new_content)
                print(f"✅ Сообщение {dto.message_id} мгновенно обновлено!")
                break

    def process_message_delete(self, msg_id: int):
        """Безопасное удаление в UI-потоке"""
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for widget in widgets:
            if widget.message_id == msg_id:
                self.messages_layout.removeWidget(widget)
                widget.deleteLater()
                print(f"🗑️ Сообщение {msg_id} удалено")
                break

    def on_messages_read_update(self, data):
        if data.get("chat_id") != self.current_chat_id:
            return

        target_ids = data.get("message_ids", [])
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for widget in widgets:
            if widget.message_id in target_ids:
                if hasattr(widget, 'set_read_status'):
                    widget.set_read_status(True)

    def check_visible_messages(self):
        if not self.current_chat_id:
            return

        visible_ids = []
        viewport_rect = self.ui.scroll_area.viewport().rect()

        for i in range(self.messages_layout.count()):
            widget = self.messages_layout.itemAt(i).widget()
            if isinstance(widget, ChatMessageWidget):
                if not widget.is_mine and widget.message_id not in self.already_marked_read:
                    widget_pos = widget.mapTo(self.ui.scroll_area.viewport(), widget.rect().topLeft())
                    if viewport_rect.contains(widget_pos):
                        visible_ids.append(widget.message_id)
                        self.already_marked_read.add(widget.message_id)

        if visible_ids:
            self.sio.emit('messages_seen', {
                "chat_id": self.current_chat_id,
                "user_id": self.current_user_id,
                "message_ids": visible_ids
            })

    def load_chat_list(self):
        """Загрузка универсального списка чатов (проекты, группы, личные)"""
        self.ui.chat_list.clear()
        try:
            chats = self.service.get_user_chats(self.current_user_id)

            for chat in chats:
                icon = "📁" if chat.type == "project" else "👥" if chat.type == "group" else "👤"
                item = QListWidgetItem(f"{icon} {chat.display_name}")
                item.setData(Qt.ItemDataRole.UserRole, chat.id)
                self.ui.chat_list.addItem(item)

            print(f"✅ Загружено чатов: {len(chats)}")
        except Exception as e:
            print(f"❌ Ошибка загрузки списка чатов: {e}")

    def on_chat_selected(self, item):
        new_chat_id = item.data(Qt.ItemDataRole.UserRole)
        if self.current_chat_id == new_chat_id:
            return

        if self.current_chat_id:
            self.sio.emit('leave_chat', {'chat_id': self.current_chat_id})

        self.current_chat_id = new_chat_id
        self.sio.emit('join_chat', {'chat_id': self.current_chat_id})

        self.ui.chat_header.setText(item.text())
        self.ui.btn_chat_info.setVisible(True)
        self.refresh_messages()

    def refresh_messages(self):
        """Первоначальная загрузка при входе в чат"""
        if not self.current_chat_id:
            return
        self.clear_messages_layout()

        unread_count = self.service.chat_repo.get_unread_count(self.current_chat_id, self.current_user_id)
        start_offset = max(0, unread_count - 10)

        self.offset_old = start_offset
        self.offset_new = start_offset
        self.all_old_loaded = False
        self.all_new_loaded = (start_offset == 0)

        messages = self.service.load_history(
            self.current_chat_id, self.current_user_id, limit=50, offset=self.offset_old
        )

        if not messages:
            return

        separator_widget = None
        for msg in messages:
            if not msg.is_read and msg.sender_id != self.current_user_id and not separator_widget:
                separator_widget = NewMessagesSeparator()
                self.messages_layout.addWidget(separator_widget)

            self.append_message_to_ui(msg, force_scroll=False)

        self.offset_old += len(messages)

        if separator_widget:
            QTimer.singleShot(100, lambda: self.ui.scroll_area.ensureWidgetVisible(separator_widget))
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
            msg_widget = self._create_message_widget(msg_dto)

            if getattr(self, 'selection_mode', False):
                msg_widget.set_selection_mode(True)

            self.messages_layout.addWidget(msg_widget)

            is_mine = (msg_dto.sender_id == self.current_user_id)
            if force_scroll is False:
                pass
            elif force_scroll is True or (
                    force_scroll is None and (is_mine or not self.ui.btn_scroll_down.isVisible())):
                self.scroll_to_bottom(force=is_mine)

            return msg_widget

        except Exception as e:
            print(f"❌ Ошибка отрисовки сообщения: {e}")
            return None

    def prepend_message_to_ui(self, msg: MessageReadDTO):
        """Вставляет виджет в начало списка (сверху)"""
        widget = self._create_message_widget(msg)
        self.ui.messages_layout.insertWidget(0, widget)

    def _create_message_widget(self, msg: MessageReadDTO):
        """Вспомогательный метод создания виджета из DTO с полной поддержкой всех статусов"""
        is_mine = (msg.sender_id == self.current_user_id)
        is_read_val = getattr(msg, 'is_read', False)
        is_edited_val = getattr(msg, 'is_edited', False)

        widget = ChatMessageWidget(
            message_id=msg.id,
            text=msg.content,
            sender_name=msg.sender_name,
            time_str=msg.time_display,
            is_mine=is_mine,
            is_read=is_read_val,
            is_edited=is_edited_val,
            reply_to_id=getattr(msg, 'reply_to_id', None),
            reply_text=getattr(msg, 'reply_text', None),
            reply_sender_name=getattr(msg, 'reply_sender_name', None),
            forward_from_name=getattr(msg, 'forward_from_name', None),
            parent=self.ui.messages_container
        )

        widget.action_triggered.connect(self.handle_message_action)
        if hasattr(widget, 'toggled'):
            widget.toggled.connect(self.on_message_toggled)

        return widget

    def send_message(self):
        text = self.ui.message_input.toPlainText().strip()
        if not text:
            return

        if self.editing_message_id:
            self.sio.emit('edit_chat_msg', {
                "message_id": self.editing_message_id,
                "content": text,
                "chat_id": self.current_chat_id
            })
            self.cancel_editing()
        elif self.reply_message_id:
            self.sio.emit('send_chat_msg', {
                "chat_id": self.current_chat_id,
                "sender_id": self.current_user_id,
                "content": text,
                "reply_to_id": self.reply_message_id
            })
            self.cancel_editing()
        else:
            self.sio.emit('send_chat_msg', {
                "chat_id": self.current_chat_id,
                "sender_id": self.current_user_id,
                "content": text
            })

        self.ui.message_input.clear()
        self.ui.message_input.setFixedHeight(40)

    def forward_selected_messages(self):
        """Массовая пересылка выбранных сообщений"""
        if not self.selected_messages:
            return

        try:
            chats = self.service.get_user_chats(self.current_user_id)
            dialog = ForwardDialog(chats, self)

            if dialog.exec():
                target_chat_id = dialog.get_selected_chat_id()
                if target_chat_id:
                    sorted_ids = sorted(list(self.selected_messages))

                    for msg_id in sorted_ids:
                        self.sio.emit('forward_message', {
                            "message_id": msg_id,
                            "target_chat_id": target_chat_id,
                            "user_id": self.current_user_id
                        })

                    print(f"✅ Переслано сообщений: {len(sorted_ids)}")
                    self.exit_selection_mode()
        except Exception as e:
            print(f"❌ Ошибка при массовой пересылке: {e}")

    def open_create_chat_dialog(self):
        from windows.chat.chat_create_dialog import ChatCreateDialog

        # Используем emp_repo из ChatService (теперь это EmployeeRepo)
        dialog = ChatCreateDialog(
            emp_repo=self.service.emp_repo,  # ← EmployeeRepo
            current_user_id=self.current_user_id,
            parent=self
        )

        if dialog.exec():
            data = dialog.get_data()
            self.service.create_new_chat(self.current_user_id, data)
            self.load_chat_list()

    def open_chat_settings(self):
        if not self.current_chat_id:
            return

        dialog = ChatSettingsDialog(
            chat_id=self.current_chat_id,
            service=self.service,
            current_user_id=self.current_user_id,
            parent=self
        )
        if dialog.exec():
            self.load_chat_list()

            for i in range(self.ui.chat_list.count()):
                item = self.ui.chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_chat_id:
                    self.ui.chat_header.setText(item.text())
                    break

    def handle_message_action(self, action_type, message_id):
        """Обработка действий из контекстного меню сообщения"""
        if action_type == "goto":
            self.scroll_to_message(message_id)
        elif action_type == "delete":
            self.confirm_and_delete(message_id)
        elif action_type == "edit":
            msg = self.service.get_message_by_id(message_id)
            if msg:
                self.start_editing(message_id, msg.content)
        elif action_type == "reply":
            msg = self.service.get_message_by_id(message_id)
            if msg:
                self.start_replying(message_id, msg.content, msg.sender_name)
        elif action_type == "forward":
            self.open_forward_dialog(message_id)
        elif action_type == "select":
            self.enter_selection_mode(message_id)

    def confirm_and_delete(self, message_id):
        widget = self.find_message_widget_by_id(message_id)
        if not widget:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Удаление")
        msg_box.setText("Вы хотите удалить это сообщение?")

        btn_me = msg_box.addButton("Удалить у меня", QMessageBox.ButtonRole.ActionRole)
        btn_everyone = None

        if widget.is_mine:
            btn_everyone = msg_box.addButton("Удалить у всех", QMessageBox.ButtonRole.DestructiveRole)

        msg_box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()

        clicked = msg_box.clickedButton()

        if clicked == btn_me:
            if self.service.delete_message_for_me(message_id, self.current_user_id):
                self.remove_message_from_ui(message_id)
                if self.sio:
                    self.sio.emit("delete_chat_msg", {
                        "message_id": message_id,
                        "chat_id": self.current_chat_id,
                        "user_id": self.current_user_id,
                        "mode": "me"
                    })

        elif btn_everyone and clicked == btn_everyone:
            if self.service.delete_message_for_everyone(message_id):
                if self.sio:
                    self.sio.emit("delete_chat_msg", {
                        "message_id": message_id,
                        "chat_id": self.current_chat_id,
                        "mode": "everyone"
                    })
                self.remove_message_from_ui(message_id)

    def open_forward_dialog(self, message_id):
        """Логика открытия окна пересылки"""
        try:
            chats = self.service.get_user_chats(self.current_user_id)
            dialog = ForwardDialog(chats, self)

            if dialog.exec():
                target_chat_id = dialog.get_selected_chat_id()
                if target_chat_id:
                    payload = {
                        "message_id": message_id,
                        "target_chat_id": target_chat_id,
                        "user_id": self.current_user_id
                    }
                    print(f"📡 Отправка пересылки: {payload}")
                    self.sio.emit('forward_message', payload)

        except Exception as e:
            print(f"❌ Ошибка в ChatPage при пересылке: {e}")

    def scroll_to_bottom(self, force=False):
        if not self.all_new_loaded and force:
            self.refresh_messages()
            self.reset_unread_on_button()
            return

        v_bar = self.ui.scroll_area.verticalScrollBar()
        if force or not self.ui.btn_scroll_down.isVisible():
            QTimer.singleShot(50, lambda: v_bar.setValue(v_bar.maximum()))
            self.reset_unread_on_button()

    def handle_scroll(self, value):
        v_bar = self.ui.scroll_area.verticalScrollBar()
        dist_from_bottom = v_bar.maximum() - value

        if dist_from_bottom < 10:
            if getattr(self, 'unread_below_count', 0) > 0:
                self.reset_unread_on_button()
            self.ui.btn_scroll_down.setVisible(False)
            self.all_new_loaded = True
        else:
            self.ui.btn_scroll_down.setVisible(dist_from_bottom > 150)

        if self.loading:
            return

        if value <= 50 and not self.all_old_loaded:
            self.load_more_old()

        if value >= v_bar.maximum() - 50 and not self.all_new_loaded:
            self.load_more_new()

    def load_more_old(self):
        """Подгрузка истории вверх"""
        self.loading = True
        old_max = self.ui.scroll_area.verticalScrollBar().maximum()

        messages = self.service.load_history(
            self.current_chat_id, self.current_user_id, limit=50, offset=self.offset_old
        )

        if not messages:
            self.all_old_loaded = True
        else:
            for msg in reversed(messages):
                self.prepend_message_to_ui(msg)
            self.offset_old += len(messages)

        QTimer.singleShot(0, lambda: self.adjust_scroll_after_load(old_max))
        self.loading = False

    def load_more_new(self):
        """Подгрузка истории вниз (если зашли через непрочитанные)"""
        if self.offset_new <= 0:
            self.all_new_loaded = True
            return

        self.loading = True
        limit = min(50, self.offset_new)
        self.offset_new -= limit

        messages = self.service.load_history(
            self.current_chat_id, self.current_user_id, limit=limit, offset=self.offset_new
        )

        for msg in messages:
            self.append_message_to_ui(msg, force_scroll=False)

        if self.offset_new <= 0:
            self.all_new_loaded = True
        self.loading = False

    def scroll_to_message(self, message_id: int):
        target_widget = None
        container = self.ui.messages_container

        for i in range(container.layout().count()):
            item = container.layout().itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if isinstance(widget, ChatMessageWidget) and widget.message_id == message_id:
                target_widget = widget
                break

        if target_widget:
            self.ui.scroll_area.ensureWidgetVisible(target_widget, 0, 200)
            target_widget.highlight()

    def adjust_scroll_after_load(self, old_max):
        """Чтобы экран не прыгал при подгрузке вверх"""
        new_max = self.ui.scroll_area.verticalScrollBar().maximum()
        self.ui.scroll_area.verticalScrollBar().setValue(new_max - old_max)

    def start_editing(self, message_id, original_text):
        """Вызывается при нажатии 'Редактировать' в контекстном меню"""
        self.editing_message_id = message_id

        preview = original_text if len(original_text) < 60 else original_text[:57] + "..."
        self.ui.edit_label.setText(preview)
        self.ui.edit_panel.setVisible(True)

        self.ui.message_input.setPlainText(original_text)
        self.ui.message_input.setFocus()
        self.ui.btn_send.setText("✅")

    def cancel_editing(self):
        """Вызывается при нажатии на крестик в edit_panel"""
        self.editing_message_id = None
        self.reply_message_id = None
        self.ui.edit_panel.setVisible(False)
        self.ui.message_input.clear()
        self.ui.btn_send.setText("➤")

    def start_replying(self, message_id, text, sender):
        self.reply_message_id = message_id
        self.ui.edit_label.setText(f"Ответ пользователю {sender}: {text[:40]}...")
        self.ui.edit_panel.setVisible(True)
        self.ui.btn_send.setText("↪️")
        self.ui.message_input.setFocus()

    def remove_new_messages_separator(self):
        """Удаляет красную черту 'Новые сообщения'"""
        if hasattr(self, 'new_messages_separator') and self.new_messages_separator:
            self.messages_layout.removeWidget(self.new_messages_separator)
            self.new_messages_separator.deleteLater()
            self.new_messages_separator = None

    def eventFilter(self, source, event):
        if event.type() == event.Type.MouseButtonPress:
            self.remove_new_messages_separator()
        return super().eventFilter(source, event)

    def enter_selection_mode(self, first_msg_id):
        """Вход в режим мультивыбора"""
        self.selection_mode = True
        self.selected_messages = {first_msg_id}

        self.selection_toolbar.setVisible(True)
        self.ui.input_frame.setVisible(False)

        self.update_widgets_selection_state(True)
        self.update_selection_label()

    def exit_selection_mode(self):
        """Выход из режима мультивыбора"""
        self.selection_mode = False
        self.selected_messages.clear()

        self.selection_toolbar.setVisible(False)
        self.ui.input_frame.setVisible(True)

        self.update_widgets_selection_state(False)

    def update_widgets_selection_state(self, enabled):
        """Проходит по всем сообщениям и включает/выключает чекбоксы"""
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for w in widgets:
            w.set_selection_mode(enabled)
            if not enabled:
                w.set_selected(False)
            elif w.message_id in self.selected_messages:
                w.set_selected(True)

    def update_selection_label(self):
        """Обновляет текст 'Выбрано: 3' на панели"""
        self.lbl_sel_count.setText(f"Выбрано: {len(self.selected_messages)}")

    def on_message_toggled(self, message_id, is_selected):
        """Слот, который вызывается при клике на чекбокс в сообщении"""
        if is_selected:
            self.selected_messages.add(message_id)
        else:
            self.selected_messages.discard(message_id)
            if not self.selected_messages:
                self.exit_selection_mode()
                return

        self.update_selection_label()

    def find_message_widget_by_id(self, message_id: int) -> Optional[ChatMessageWidget]:
        """Ищет виджет сообщения в контейнере по его ID"""
        widgets = self.ui.messages_container.findChildren(ChatMessageWidget)
        for w in widgets:
            if w.message_id == message_id:
                return w
        return None

    def remove_message_from_ui(self, message_id: int):
        """Полностью удаляет виджет сообщения из интерфейса (для 'удалить у меня')"""
        widget = self.find_message_widget_by_id(message_id)
        if widget:
            self.ui.messages_layout.removeWidget(widget)
            widget.deleteLater()