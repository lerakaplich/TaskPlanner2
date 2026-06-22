# windows/chat/chat_settings_handlers.py

from PyQt6.QtWidgets import QMessageBox, QDialog

from windows.chat.employee_selection_dialog import EmployeeSelectionDialog


class ChatSettingsHandlers:
    """Обработчики событий для ChatSettingsDialog"""

    def __init__(self, dialog):
        self.dialog = dialog

    def save_changes(self):
        """Сохранение настроек чата"""
        try:
            if not self.dialog.service.is_user_admin(self.dialog.chat_id, self.dialog.current_user_id):
                QMessageBox.critical(self.dialog, "Доступ запрещен", "Ваши права администратора были отозваны.")
                self.dialog.reject()
                return

            new_title = self.dialog.title_edit.text().strip()
            if not new_title:
                QMessageBox.warning(self.dialog, "Внимание", "Название чата не может быть пустым.")
                return

            if new_title != self.dialog.chat_data.title:
                if hasattr(self.dialog.parent(), 'sio'):
                    self.dialog.parent().sio.emit('update_chat_settings', {
                        'chat_id': self.dialog.chat_id,
                        'new_title': new_title
                    })
                self.dialog.chat_data.title = new_title
                self.dialog.chats_changed.emit()

            QMessageBox.information(self.dialog, "Успех", "Настройки сохранены.")
            self.dialog.accept()

        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            QMessageBox.warning(self.dialog, "Ошибка", f"Не удалось сохранить изменения: {e}")

    def handle_participant_action(self, action_type: str, emp_id: int):
        """Обработка действий с участниками"""
        if action_type == "toggle_admin":
            self.toggle_admin(emp_id)
        elif action_type == "kick":
            self.kick_user(emp_id)

    def toggle_admin(self, emp_id: int):
        """Смена роли участника"""
        participant = next((p for p in self.dialog.chat_data.participants if p.employee_id == emp_id), None)
        if not participant:
            return

        new_status = not participant.is_admin

        if self.dialog.service.set_participant_admin(self.dialog.chat_id, emp_id, new_status):
            if hasattr(self.dialog.parent(), 'sio'):
                self.dialog.parent().sio.emit('change_participant_role', {
                    "chat_id": self.dialog.chat_id,
                    "target_user_id": emp_id,
                    "is_admin": new_status
                })
            self.dialog.chat_data = self.dialog.service.get_chat_details(self.dialog.chat_id)
            self.dialog.refresh_participants_list()

    def kick_user(self, emp_id: int):
        """Исключение пользователя"""
        participant = next((p for p in self.dialog.chat_data.participants if p.employee_id == emp_id), None)
        if not participant:
            return

        confirm = QMessageBox.question(
            self.dialog, "Удаление",
            f"Вы уверены, что хотите исключить {participant.full_name} из чата?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            if self.dialog.service.kick_user(self.dialog.chat_id, emp_id):
                self.dialog.chat_data.participants = [
                    p for p in self.dialog.chat_data.participants
                    if p.employee_id != emp_id
                ]
                self.dialog.refresh_participants_list()

    def add_participant(self):
        """Добавление участников"""
        current_ids = [p.employee_id for p in self.dialog.chat_data.participants]
        dialog = EmployeeSelectionDialog(
            exclude_ids=current_ids,
            emp_repo=self.dialog.service.emp_repo,
            parent=self.dialog
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = dialog.get_selected_employees()
            if not selected_items:
                return

            new_ids = [emp.id if hasattr(emp, 'id') else emp for emp in selected_items]

            if self.dialog.service.update_chat_participants(self.dialog.chat_id, new_ids, []):
                if hasattr(self.dialog.parent(), 'sio'):
                    self.dialog.parent().sio.emit('update_participants', {
                        "chat_id": self.dialog.chat_id,
                        "added_users": new_ids,
                        "removed_users": []
                    })

                self.dialog.chat_data = self.dialog.service.get_chat_details(self.dialog.chat_id)
                self.dialog.refresh_participants_list()
                self.dialog.chats_changed.emit()

                QMessageBox.information(self.dialog, "Успех", f"Добавлено участников: {len(new_ids)}")