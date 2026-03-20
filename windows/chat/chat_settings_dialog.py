from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QCheckBox, QMessageBox, QWidget)
from PyQt6.QtCore import Qt


class ChatSettingsDialog(QDialog):
    def __init__(self, chat_id, service, current_user_id, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.service = service
        self.current_user_id = current_user_id

        # Получаем данные. Убедитесь, что сервис возвращает объект с атрибутами!
        self.chat_data = self.service.get_chat_details(chat_id)

        # Если сервис все же возвращает словарь, преобразуем его для удобства
        # или обращаемся через .get()
        participants = getattr(self.chat_data, 'participants', [])

        # Проверка прав админа
        self.is_i_admin = any(
            p.employee_id == current_user_id and getattr(p, 'is_admin', False)
            for p in participants
        )

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Информация о чате")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # Обращаемся через атрибуты, если это объект, или через .get() если словарь
        chat_title = getattr(self.chat_data, 'title', "") or ""
        chat_type = getattr(self.chat_data, 'type', "private")

        layout.addWidget(QLabel("Название чата:"))
        self.title_edit = QLineEdit(chat_title)

        # Запрещаем редактировать название личных чатов (там имя собеседника)
        self.title_edit.setEnabled(self.is_i_admin and chat_type != "private")
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel(f"Тип: {chat_type}"))

        # 2. Список участников
        layout.addWidget(QLabel("Участники:"))
        self.participants_list = QListWidget()
        self.refresh_participants()
        layout.addWidget(self.participants_list)

        # 3. Кнопки управления
        btns_layout = QHBoxLayout()
        if self.is_i_admin:
            self.save_btn = QPushButton("Сохранить изменения")
            self.save_btn.clicked.connect(self.save_changes)
            btns_layout.addWidget(self.save_btn)

            self.add_emp_btn = QPushButton("Добавить участника")
            self.add_emp_btn.clicked.connect(self.add_participant)
            btns_layout.addWidget(self.add_emp_btn)

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btns_layout.addWidget(self.close_btn)

        layout.addLayout(btns_layout)

    def refresh_participants(self):
        self.participants_list.clear()
        for p in self.chat_data.participants:
            item = QListWidgetItem()
            widget = QWidget()
            w_layout = QHBoxLayout(widget)

            name_label = QLabel(f"{p.full_name} {'(Админ)' if p.is_admin else ''}")
            w_layout.addWidget(name_label)
            w_layout.addStretch()

            # Если я админ и это не я сам — даем кнопки управления
            if self.is_i_admin and p.employee_id != self.current_user_id:
                # Кнопка смены прав
                role_btn = QPushButton("Сделать админом" if not p.is_admin else "Снять админку")
                role_btn.clicked.connect(lambda checked, eid=p.employee_id, adm=p.is_admin:
                                         self.toggle_admin(eid, adm))
                w_layout.addWidget(role_btn)

                # Кнопка удаления
                kick_btn = QPushButton("❌")
                kick_btn.setFixedSize(30, 30)
                kick_btn.clicked.connect(lambda checked, eid=p.employee_id: self.kick_user(eid))
                w_layout.addWidget(kick_btn)

            item.setSizeHint(widget.sizeHint())
            self.participants_list.addItem(item)
            self.participants_list.setItemWidget(item, widget)

    def save_changes(self):
        new_title = self.title_edit.text()
        if self.service.update_chat_settings(self.chat_id, new_title):
            QMessageBox.information(self, "Успех", "Настройки сохранены")
            self.accept()

    def toggle_admin(self, emp_id, current_admin_status):
        self.service.set_participant_admin(self.chat_id, emp_id, not current_admin_status)
        self.chat_data = self.service.get_chat_details(self.chat_id)  # Обновляем данные
        self.refresh_participants()

    def kick_user(self, emp_id):
        if QMessageBox.question(self, "Удаление", "Удалить пользователя из чата?") == QMessageBox.StandardButton.Yes:
            self.service.kick_user(self.chat_id, emp_id)
            self.chat_data = self.service.get_chat_details(self.chat_id)
            self.refresh_participants()

    def add_participant(self):
        # Здесь можно вызвать твой существующий диалог выбора сотрудников
        pass