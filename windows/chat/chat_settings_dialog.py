# windows/chat/chat_settings_dialog.py
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QCheckBox, QMessageBox, QWidget, QFrame, QMenu, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.chat.chat_settings_handlers import ChatSettingsHandlers


class ParticipantWidget(QFrame):
    """Кастомный виджет для отображения участника чата - ТОЛЬКО UI"""
    action_requested = pyqtSignal(str, int)

    def __init__(self, participant, current_user_id, is_i_admin, parent=None):
        super().__init__(parent)
        self.participant = participant
        self.eid = participant.employee_id
        self.is_i_admin = is_i_admin

        self.setObjectName("ParticipantRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#ParticipantRow {
                background-color: white;
                border-bottom: 1px solid #ececf0;
                border-radius: 8px;
                margin: 2px 5px;
            }
            QFrame#ParticipantRow:hover {
                background-color: #f0f2f5;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_str = participant.full_name
        if self.eid == current_user_id:
            name_str += " (Вы)"
        self.name_label = QLabel(name_str)
        self.name_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")

        status_str = "Администратор" if participant.is_admin else "Участник"
        self.status_label = QLabel(status_str)
        status_color = "#D22730" if participant.is_admin else "#7f8c8d"
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        joined_date = participant.joined_at.strftime("%d.%m.%Y")
        time_label = QLabel(f"В чате с: {joined_date}")
        time_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        if is_i_admin and self.eid != current_user_id:
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #e0e0e0; border-radius: 5px; padding: 5px; }
            QMenu::item { padding: 8px 20px; color: #333; border-radius: 3px; }
            QMenu::item:selected { background-color: #f0f2f5; color: #D22730; }
        """)

        role_text = "Снять админку" if self.participant.is_admin else "Сделать админом"
        action_role = QAction(role_text, self)
        action_role.triggered.connect(lambda: self.action_requested.emit("toggle_admin", self.eid))
        menu.addAction(action_role)

        menu.addSeparator()

        action_kick = QAction("❌ Исключить из чата", self)
        action_kick.triggered.connect(lambda: self.action_requested.emit("kick", self.eid))
        menu.addAction(action_kick)

        menu.exec(self.mapToGlobal(pos))


class ChatSettingsDialog(QDialog):
    """Диалог настроек чата - ТОЛЬКО UI"""
    action_requested = pyqtSignal(str, int)
    chats_changed = pyqtSignal()
    request_refresh = pyqtSignal()

    def __init__(self, chat_id, service, current_user_id, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.service = service
        self.current_user_id = current_user_id

        # Загружаем данные через сервис
        self.chat_data = self.service.get_chat_details(chat_id)
        if not self.chat_data:
            self.reject()
            return

        # Проверка прав админа
        self.is_i_admin = any(
            p.employee_id == current_user_id and p.is_admin
            for p in self.chat_data.participants
        )

        # Обработчики
        self.handlers = ChatSettingsHandlers(self)

        self.request_refresh.connect(self.refresh_participants_list)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки чата")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self.setStyleSheet("QDialog { background-color: #f7f7f9; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- БЛОК 1: Название ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("Название чата")
        title_label.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 11px; text-transform: uppercase;")
        header_layout.addWidget(title_label)

        self.title_edit = QLineEdit(self.chat_data.title or "")
        self.title_edit.setPlaceholderText("Введите название чата...")
        input_style = """
            QLineEdit {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                font-size: 14px;
                background-color: #f0f2f5;
            }
            QLineEdit:focus { border: 1px solid #D22730; background-color: white; }
            QLineEdit:disabled { color: #888; background-color: #f5f5f5; border: 1px solid #eee; }
        """
        self.title_edit.setStyleSheet(input_style)

        is_edit_allowed = self.is_i_admin and self.chat_data.type != "private"
        self.title_edit.setEnabled(is_edit_allowed)
        header_layout.addWidget(self.title_edit)

        type_str = "Проект" if self.chat_data.type == "project" else "Группа" if self.chat_data.type == "group" else "Личный"
        info_lbl = QLabel(f"Тип: {type_str} • ID: {self.chat_id}")
        info_lbl.setStyleSheet("color: #95a5a6; font-size: 12px; margin-top: 5px;")
        header_layout.addWidget(info_lbl)

        main_layout.addWidget(header_frame)

        # --- БЛОК 2: Участники ---
        part_header_layout = QHBoxLayout()
        part_title = QLabel(f"Участники ({len(self.chat_data.participants)})")
        part_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        part_header_layout.addWidget(part_title)
        part_header_layout.addStretch()

        if self.is_i_admin and self.chat_data.type != "private":
            self.add_emp_btn = QPushButton("+ Добавить")
            self.add_emp_btn.setStyleSheet("""
                QPushButton { background-color: #D22730; color: white; border-radius: 15px; padding: 5px 15px; font-weight: bold; font-size: 12px;}
                QPushButton:hover { background-color: #b01f28; }
            """)
            self.add_emp_btn.clicked.connect(self.handlers.add_participant)
            part_header_layout.addWidget(self.add_emp_btn)

        main_layout.addLayout(part_header_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.participants_container = QWidget()
        self.participants_container.setStyleSheet("background-color: transparent;")
        self.participants_layout = QVBoxLayout(self.participants_container)
        self.participants_layout.setContentsMargins(0, 0, 0, 0)
        self.participants_layout.setSpacing(0)
        self.participants_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.participants_container)
        main_layout.addWidget(self.scroll_area, 1)

        # --- БЛОК 3: Кнопки ---
        btns_frame = QFrame()
        btns_frame.setStyleSheet("background-color: white; border-top: 1px solid #e0e0e0; margin-top: 10px;")
        btns_layout = QHBoxLayout(btns_frame)
        btns_layout.setContentsMargins(15, 15, 15, 15)

        btns_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.setStyleSheet("""
            QPushButton { padding: 10px 20px; border: 1px solid #ccc; border-radius: 5px; background: white; color: #333;}
            QPushButton:hover { background-color: #f0f2f5; }
        """)
        self.close_btn.clicked.connect(self.accept)
        btns_layout.addWidget(self.close_btn)

        if self.is_i_admin:
            self.save_btn = QPushButton("Применить изменения")
            self.save_btn.setMinimumWidth(180)
            self.save_btn.setStyleSheet("""
                QPushButton { background-color: #D22730; color: white; border-radius: 5px; padding: 10px 20px; font-weight: bold;}
                QPushButton:hover { background-color: #b01f28; }
            """)
            self.save_btn.clicked.connect(self.handlers.save_changes)
            btns_layout.addWidget(self.save_btn)

        main_layout.addWidget(btns_frame)

        self.refresh_participants_list()

    def refresh_participants_list(self):
        """Обновление списка участников (вызывается из обработчика)"""
        while self.participants_layout.count():
            item = self.participants_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.chat_data = self.service.get_chat_details(self.chat_id)
        if not self.chat_data:
            return

        me = next((p for p in self.chat_data.participants
                   if p.employee_id == self.current_user_id), None)
        self.is_i_admin = me.is_admin if me else False

        self.apply_permissions()

        sorted_list = sorted(
            self.chat_data.participants,
            key=lambda p: (not p.is_admin, getattr(p, 'full_name', f"ID {p.employee_id}").lower())
        )

        for p in sorted_list:
            if not hasattr(p, 'full_name') or not p.full_name:
                emp = self.service.emp_repo.get_by_id(p.employee_id)
                p.full_name = f"{emp.last_name} {emp.first_name}" if emp else f"ID {p.employee_id}"

            pw = ParticipantWidget(p, self.current_user_id, self.is_i_admin)
            pw.action_requested.connect(self.handlers.handle_participant_action)
            self.participants_layout.addWidget(pw)

    def apply_permissions(self):
        """Применение прав к UI"""
        can_edit = self.is_i_admin and self.chat_data.type != "private"

        self.title_edit.setEnabled(can_edit)

        if hasattr(self, 'add_emp_btn'):
            self.add_emp_btn.setVisible(can_edit)
            self.add_emp_btn.setEnabled(can_edit)

        if hasattr(self, 'save_btn'):
            self.save_btn.setVisible(self.is_i_admin)
            self.save_btn.setEnabled(self.is_i_admin)