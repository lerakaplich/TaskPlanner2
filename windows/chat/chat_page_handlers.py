# windows/chat/chat_page_handlers.py

from typing import Optional, List
from PyQt6.QtWidgets import QMessageBox

from models.schemas.chat_dto import MessageEditDTO, MessageDeleteDTO


class ChatPageHandlers:
    """Обработчики событий для ChatPage"""

    def __init__(self, page):
        self.page = page

    # ==========================================================
    # Действия с сообщениями
    # ==========================================================

    def handle_message_action(self, action_type: str, message_id: int):
        """Обработка действий из контекстного меню"""
        if action_type == "goto":
            self.page.scroll_to_message(message_id)
        elif action_type == "delete":
            self.confirm_and_delete(message_id)
        elif action_type == "edit":
            self.start_editing(message_id)
        elif action_type == "reply":
            self.start_replying(message_id)
        elif action_type == "forward":
            self.open_forward_dialog(message_id)
        elif action_type == "select":
            self.enter_selection_mode(message_id)

    def confirm_and_delete(self, message_id: int):
        """Подтверждение и удаление сообщения"""
        widget = self.page.find_message_widget_by_id(message_id)
        if not widget:
            return

        msg_box = QMessageBox(self.page)
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
            self._delete_for_me(message_id)
        elif btn_everyone and clicked == btn_everyone:
            self._delete_for_everyone(message_id)

    def _delete_for_me(self, message_id: int):
        """Удаление сообщения только для себя"""
        if self.page.service.delete_message_for_me(message_id, self.page.current_user_id):
            self.page.remove_message_from_ui(message_id)
            if self.page.sio:
                self.page.sio.emit("delete_chat_msg", {
                    "message_id": message_id,
                    "chat_id": self.page.current_chat_id,
                    "user_id": self.page.current_user_id,
                    "mode": "me"
                })

    def _delete_for_everyone(self, message_id: int):
        """Удаление сообщения для всех"""
        if self.page.service.delete_message_for_everyone(message_id):
            if self.page.sio:
                self.page.sio.emit("delete_chat_msg", {
                    "message_id": message_id,
                    "chat_id": self.page.current_chat_id,
                    "mode": "everyone"
                })
            self.page.remove_message_from_ui(message_id)

    def start_editing(self, message_id: int):
        """Начало редактирования сообщения"""
        msg = self.page.service.get_message_by_id(message_id)
        if msg:
            self.page.start_editing(message_id, msg.content)

    def start_replying(self, message_id: int):
        """Начало ответа на сообщение"""
        msg = self.page.service.get_message_by_id(message_id)
        if msg:
            self.page.start_replying(message_id, msg.content, msg.sender_name)

    def open_forward_dialog(self, message_id: int):
        """Открытие диалога пересылки"""
        try:
            chats = self.page.service.get_user_chats(self.page.current_user_id)
            from windows.chat.chat_forward_dialog import ForwardDialog
            dialog = ForwardDialog(chats, self.page)

            if dialog.exec():
                target_chat_id = dialog.get_selected_chat_id()
                if target_chat_id:
                    self.page.sio.emit('forward_message', {
                        "message_id": message_id,
                        "target_chat_id": target_chat_id,
                        "user_id": self.page.current_user_id
                    })
        except Exception as e:
            print(f"❌ Ошибка при пересылке: {e}")

    def enter_selection_mode(self, first_msg_id: int):
        """Вход в режим мультивыбора"""
        self.page.enter_selection_mode(first_msg_id)

    # ==========================================================
    # Массовые операции
    # ==========================================================

    def forward_selected_messages(self):
        """Массовая пересылка выбранных сообщений"""
        if not self.page.selected_messages:
            return

        try:
            chats = self.page.service.get_user_chats(self.page.current_user_id)
            from windows.chat.chat_forward_dialog import ForwardDialog
            dialog = ForwardDialog(chats, self.page)

            if dialog.exec():
                target_chat_id = dialog.get_selected_chat_id()
                if target_chat_id:
                    sorted_ids = sorted(list(self.page.selected_messages))
                    for msg_id in sorted_ids:
                        self.page.sio.emit('forward_message', {
                            "message_id": msg_id,
                            "target_chat_id": target_chat_id,
                            "user_id": self.page.current_user_id
                        })
                    self.page.exit_selection_mode()
        except Exception as e:
            print(f"❌ Ошибка при массовой пересылке: {e}")