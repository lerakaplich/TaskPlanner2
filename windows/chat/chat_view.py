from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                             QTextEdit, QLineEdit, QPushButton, QSplitter, QLabel, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ChatView(QWidget):
    """Класс, отвечающий исключительно за визуальное отображение чата"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Разделитель для изменения размеров панелей
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- ЛЕВАЯ ПАНЕЛЬ (Список чатов) ---
        left_container = QFrame()
        left_container.setFixedWidth(280)
        left_container.setStyleSheet("background-color: #f7f7f9; border-right: 1px solid #e0e0e0;")
        left_layout = QVBoxLayout(left_container)

        self.sidebar_label = QLabel("Чаты")
        self.sidebar_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.sidebar_label.setStyleSheet("padding: 10px; color: #2c3e50; border: none;")

        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: none; }
            QListWidget::item { padding: 15px; border-bottom: 1px solid #ececf0; }
            QListWidget::item:selected { background-color: #ffffff; color: #D22730; border-left: 4px solid #D22730; }
        """)

        self.btn_create_chat = QPushButton("+ Создать чат")
        self.btn_create_chat.setStyleSheet("""
            QPushButton { background-color: #D22730; color: white; border-radius: 5px; padding: 10px; margin: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #b01f28; }
        """)

        left_layout.addWidget(self.sidebar_label)
        left_layout.addWidget(self.chat_list)
        left_layout.addWidget(self.btn_create_chat)

        # --- ПРАВАЯ ПАНЕЛЬ (Окно переписки) ---
        right_container = QFrame()
        right_container.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_container)

        # Заголовок текущего чата
        self.chat_header = QLabel("Выберите чат...")
        self.chat_header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.chat_header.setStyleSheet("padding: 15px; border-bottom: 1px solid #ececf0; background-color: white;")

        # История сообщений
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("border: none; background-color: #ffffff; padding: 10px;")

        # Поле ввода
        input_container = QFrame()
        input_container.setStyleSheet("border-top: 1px solid #ececf0; background-color: #f9f9f9;")
        input_layout = QHBoxLayout(input_container)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Напишите сообщение...")
        self.message_input.setStyleSheet(
            "padding: 10px; border: 1px solid #e0e0e0; border-radius: 20px; background: white;")

        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(40, 40)
        self.btn_send.setStyleSheet("""
            QPushButton { background-color: #D22730; color: white; border-radius: 20px; font-size: 18px; }
            QPushButton:hover { background-color: #b01f28; }
        """)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.btn_send)

        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.chat_history)
        right_layout.addWidget(input_container)

        # Сборка
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        main_layout.addWidget(self.splitter)