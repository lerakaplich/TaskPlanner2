from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                             QLineEdit, QPushButton, QSplitter, QLabel, QFrame,
                             QScrollArea, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ChatView(QWidget):
    """Обновленный класс визуального отображения с поддержкой пузырьков"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- ЛЕВАЯ ПАНЕЛЬ (Без изменений) ---
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

        # --- ПРАВАЯ ПАНЕЛЬ (Окно переписки - ТУТ ИЗМЕНЕНИЯ) ---
        right_container = QFrame()
        right_container.setStyleSheet("background-color: #f0f2f5;")  # Светло-серый фон как в мессенджерах
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Заголовок
        self.chat_header = QLabel("Выберите чат...")
        self.chat_header.setFixedHeight(60)
        self.chat_header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.chat_header.setStyleSheet("padding: 15px; border-bottom: 1px solid #e0e0e0; background-color: white;")

        # --- ОБЛАСТЬ СООБЩЕНИЙ (Вместо QTextEdit) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")

        # Контейнер для пузырьков
        self.messages_container = QWidget()
        self.messages_container.setObjectName("messages_container")
        self.messages_container.setStyleSheet("background-color: #f0f2f5;")

        # Лейаут для пузырьков
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Прижимаем сообщения к верху

        # Добавляем "пружину" в конец, чтобы сообщения не растягивались по высоте
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.messages_layout.addSpacerItem(self.spacer)

        self.scroll_area.setWidget(self.messages_container)

        # Поле ввода
        input_container = QFrame()
        input_container.setFixedHeight(80)
        input_container.setStyleSheet("border-top: 1px solid #e0e0e0; background-color: white;")
        input_layout = QHBoxLayout(input_container)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Напишите сообщение...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px; 
                border: 1px solid #e0e0e0; 
                border-radius: 20px; 
                background: #f0f2f5;
                font-size: 14px;
            }
        """)

        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(45, 45)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton { 
                background-color: #D22730; 
                color: white; 
                border-radius: 22px; 
                font-size: 20px; 
                padding-left: 3px;
            }
            QPushButton:hover { background-color: #b01f28; }
        """)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.btn_send)

        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.scroll_area)
        right_layout.addWidget(input_container)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        main_layout.addWidget(self.splitter)