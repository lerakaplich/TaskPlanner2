from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QListWidget, QPushButton, QLabel, QComboBox, QFrame)
from PyQt6.QtCore import Qt


class ChatCreateView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового чата")
        self.setMinimumSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Тип чата
        layout.addWidget(QLabel("Тип чата:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Групповой чат", "Личная переписка"])
        layout.addWidget(self.type_combo)

        # Название (скрывается, если чат личный)
        self.title_label = QLabel("Название чата:")
        layout.addWidget(self.title_label)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Введите название...")
        layout.addWidget(self.title_input)

        # Поиск сотрудников
        layout.addWidget(QLabel("Выберите участников:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск сотрудника...")
        layout.addWidget(self.search_input)

        # Список сотрудников с чекбоксами
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("QListWidget::item { padding: 5px; }")
        layout.addWidget(self.user_list)

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Отмена")
        self.btn_create = QPushButton("Создать")
        self.btn_create.setStyleSheet("background-color: #D22730; color: white; font-weight: bold; padding: 8px;")

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_create)
        layout.addLayout(buttons_layout)