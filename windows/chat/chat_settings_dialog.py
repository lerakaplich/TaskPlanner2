from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QCheckBox, QMessageBox, QWidget, QFrame, QMenu, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal


class ParticipantWidget(QFrame):
    """Кастомный виджет для отображения участника чата"""
    # Сигналы для действий контекстного меню
    action_requested = pyqtSignal(str, int)  # (тип действия, id сотрудника)

    def __init__(self, participant, current_user_id, is_i_admin, parent=None):
        super().__init__(parent)
        self.participant = participant
        self.eid = participant.employee_id
        self.is_i_admin = is_i_admin

        self.setObjectName("ParticipantRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Стилизация строки: фон при наведении
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

        # 1. Основная инфо (ФИО + Роль)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # ФИО
        name_str = participant.full_name
        if self.eid == current_user_id:
            name_str += " (Вы)"
        self.name_label = QLabel(name_str)
        self.name_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")

        # Роль и статус
        status_str = "Администратор" if participant.is_admin else "Участник"
        # Добавим "В сети" (в будущем можно брать реальный статус из БД)
        status_str += " • В сети"

        self.status_label = QLabel(status_str)
        status_color = "#D22730" if participant.is_admin else "#7f8c8d"
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # 2. Время входа (или другая метаинформация)
        # joined_at берем из модели ChatParticipant
        joined_date = participant.joined_at.strftime("%d.%m.%Y")
        time_label = QLabel(f"В чате с: {joined_date}")
        time_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Включаем контекстное меню только если я админ и это не я
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

        # Действие 1: Смена роли
        role_text = "Снять админку" if self.participant.is_admin else "Сделать админом"
        action_role = QAction(role_text, self)
        action_role.triggered.connect(lambda: self.action_requested.emit("toggle_admin", self.eid))
        menu.addAction(action_role)

        menu.addSeparator()

        # Действие 2: Исключить
        action_kick = QAction("❌ Исключить из чата", self)
        # Специфический стиль для удаления в меню не задать через QAction,
        # но можно выделить иконкой или текстом
        action_kick.triggered.connect(lambda: self.action_requested.emit("kick", self.eid))
        menu.addAction(action_kick)

        menu.exec(self.mapToGlobal(pos))

class ChatSettingsDialog(QDialog):
    action_requested = pyqtSignal(str, int)  # (тип действия, id сотрудника)
    chats_changed = pyqtSignal()

    def __init__(self, chat_id, service, current_user_id, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.service = service
        self.current_user_id = current_user_id

        # Загружаем обогащенные данные через сервис -> репозиторий
        self.chat_data = self.service.get_chat_details(chat_id)
        if not self.chat_data:
            self.reject()
            return

        # Проверка прав админа
        self.is_i_admin = any(p.employee_id == current_user_id and p.is_admin
                              for p in self.chat_data.participants)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки чата")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self.setStyleSheet("QDialog { background-color: #f7f7f9; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- БЛОК 1: Название (Редактируемое админами) ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("Название чата")
        title_label.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 11px; text-transform: uppercase;")
        header_layout.addWidget(title_label)

        # Поле ввода в стиле вашего приложения
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

        # Доступно только админам не приватных чатов
        is_edit_allowed = self.is_i_admin and self.chat_data.type != "private"
        self.title_edit.setEnabled(is_edit_allowed)
        header_layout.addWidget(self.title_edit)

        # Метаинформация (Тип, ID)
        type_str = "Проект" if self.chat_data.type == "project" else "Группа" if self.chat_data.type == "group" else "Личный"
        info_lbl = QLabel(f"Тип: {type_str} • ID: {self.chat_id}")
        info_lbl.setStyleSheet("color: #95a5a6; font-size: 12px; margin-top: 5px;")
        header_layout.addWidget(info_lbl)

        main_layout.addWidget(header_frame)

        # --- БЛОК 2: Участники (Скролл + Кастомные виджеты) ---
        part_header_layout = QHBoxLayout()
        part_title = QLabel(f"Участники ({len(self.chat_data.participants)})")
        part_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        part_header_layout.addWidget(part_title)

        part_header_layout.addStretch()

        # Кнопка добавления (только для админов)
        if self.is_i_admin and self.chat_data.type != "private":
            self.add_emp_btn = QPushButton("+ Добавить")
            self.add_emp_btn.setStyleSheet("""
                QPushButton { background-color: #D22730; color: white; border-radius: 15px; padding: 5px 15px; font-weight: bold; font-size: 12px;}
                QPushButton:hover { background-color: #b01f28; }
            """)
            self.add_emp_btn.clicked.connect(self.add_participant)
            part_header_layout.addWidget(self.add_emp_btn)

        main_layout.addLayout(part_header_layout)

        # Область скролла
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # Контейнер для виджетов участников
        self.participants_container = QWidget()
        self.participants_container.setStyleSheet("background-color: transparent;")
        self.participants_layout = QVBoxLayout(self.participants_container)
        self.participants_layout.setContentsMargins(0, 0, 0, 0)
        self.participants_layout.setSpacing(0)  # Отступы внутри ParticipantWidget
        self.participants_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.participants_container)
        main_layout.addWidget(self.scroll_area, 1)  # Занимает все свободное место

        # --- БЛОК 3: Кнопки управления (Низ) ---
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
            self.save_btn.clicked.connect(self.save_changes)
            btns_layout.addWidget(self.save_btn)

        main_layout.addWidget(btns_frame)

        # Первичное наполнение списка
        self.refresh_participants_list()

    def refresh_participants_list(self):
        """Очищает скролл и заново создает виджеты участников"""
        # Очистка лейаута
        while self.participants_layout.count():
            item = self.participants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Сортировка: сначала админы, потом по алфавиту
        sorted_participants = sorted(
            self.chat_data.participants,
            key=lambda p: (not p.is_admin, p.full_name)
        )

        # Создание виджетов
        for p in sorted_participants:
            w = ParticipantWidget(p, self.current_user_id, self.is_i_admin)
            # Подключаем сигнал контекстного меню к методам диалога
            w.action_requested.connect(self.handle_participant_action)
            self.participants_layout.addWidget(w)

    def save_changes(self):
        new_title = self.title_edit.text().strip()
        if not new_title: return

        # 1. Обновляем в базе данных
        if self.service.update_chat_settings(self.chat_id, new_title):

            # 2. Отправляем в сокет, чтобы сервер разослал это ВСЕМ в комнате
            if hasattr(self.parent(), 'sio'):
                self.parent().sio.emit('update_chat_settings', {
                    "chat_id": self.chat_id,
                    "new_title": new_title
                })

            self.chats_changed.emit()
            self.accept()

    def handle_participant_action(self, action_type, emp_id):
        """Централизованная обработка действий из контекстного меню участника"""
        if action_type == "toggle_admin":
            self.toggle_admin(emp_id)
        elif action_type == "kick":
            self.kick_user(emp_id)

    def toggle_admin(self, emp_id):
        """Смена прав администратора через сервис"""
        participant = next((p for p in self.chat_data.participants if p.employee_id == emp_id), None)
        if not participant: return

        new_status = not participant.is_admin

        # Вызываем сервис
        if self.service.set_participant_admin(self.chat_id, emp_id, new_status):
            # Обновляем локальные данные и UI
            participant.is_admin = new_status
            self.refresh_participants_list()
            print(f"✅ Статус админа для {emp_id} изменен на {new_status}")

    def kick_user(self, emp_id):
        """Исключение пользователя через сервис"""
        participant = next((p for p in self.chat_data.participants if p.employee_id == emp_id), None)
        if not participant: return

        confirm = QMessageBox.question(
            self, "Удаление",
            f"Вы уверены, что хотите исключить {participant.full_name} из чата?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            if self.service.kick_user(self.chat_id, emp_id):
                # Обновляем локальные данные
                self.chat_data.participants = [p for p in self.chat_data.participants if p.employee_id != emp_id]
                self.refresh_participants_list()
                print(f"❌ Пользователь {emp_id} исключен")

    def add_participant(self):
        """Открывает диалог выбора сотрудников и добавляет их в чат"""
        # 1. Список тех, кто уже в чате
        current_ids = [p.employee_id for p in self.chat_data.participants]

        from windows.chat.employee_selection_dialog import EmployeeSelectionDialog

        # 2. Передаем репозиторий из сервиса
        dialog = EmployeeSelectionDialog(
            exclude_ids=current_ids,
            emp_repo=self.service.emp_repo,  # Достаем репозиторий из ChatService
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = dialog.get_selected_employees()
            if not selected_items:
                return

            # Превращаем объекты в список ID (если диалог вернул объекты)
            new_ids = [emp.id if hasattr(emp, 'id') else emp for emp in selected_items]

            # 3. Вызываем сервис ОДИН РАЗ со списком новых ID
            # added_ids = new_ids, removed_ids = []
            if self.service.update_chat_participants(self.chat_id, new_ids, []):

                # Оповещаем сервер через сокет, чтобы новые участники сразу увидели чат
                if hasattr(self.parent(), 'sio'):
                    self.parent().sio.emit('update_participants', {
                        "chat_id": self.chat_id,
                        "added_users": new_ids,  # список ID тех, кого только что добавили
                        "removed_users": []
                    })

                # 4. Обновляем UI
                self.chat_data = self.service.get_chat_details(self.chat_id)
                self.refresh_participants_list()
                self.chats_changed.emit()  # Сигнал для обновления боковой панели

                QMessageBox.information(self, "Успех", f"Добавлено участников: {len(new_ids)}")