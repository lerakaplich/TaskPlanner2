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

        # --- ЛЕВАЯ ПАНЕЛЬ ---
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

        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_container = QFrame()
        right_container.setStyleSheet("background-color: #f0f2f5;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Заголовок чата
        self.chat_header = QLabel("Выберите чат...")
        self.chat_header.setFixedHeight(60)
        self.chat_header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.chat_header.setStyleSheet("padding: 15px; border-bottom: 1px solid #e0e0e0; background-color: white;")

        # Область сообщений
        self.scroll_container = QWidget()
        scroll_container_layout = QVBoxLayout(self.scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""

        /* Скроллбары */
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            background: #F5F5F5;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #C1C1C1;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar:horizontal {
            border: none;
            background: #F5F5F5;
            height: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background: #c1c1c1;
            border-radius: 4px;
            min-width: 20px;
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            border: none;
            background: none;
        }

                """)

        scroll_container_layout.addWidget(self.scroll_area)

        # --- КНОПКА ПРОКРУТКИ ВНИЗ ---
        self.btn_scroll_down = QPushButton("↓", self.scroll_container)
        self.btn_scroll_down.setFixedSize(40, 40)
        self.btn_scroll_down.setVisible(False)  # По умолчанию скрыта
        self.btn_scroll_down.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scroll_down.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #555;
                        border: 1px solid #ddd;
                        border-radius: 20px;
                        font-size: 18px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #f8f8f8; }
                """)

        self.messages_container = QWidget()
        self.messages_container.setObjectName("messages_container")
        self.messages_container.setStyleSheet("background-color: #f0f2f5;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.messages_layout.addSpacerItem(self.spacer)
        self.scroll_area.setWidget(self.messages_container)

        # --- ПАНЕЛЬ РЕДАКТИРОВАНИЯ (Над вводом) ---
        self.edit_panel = QFrame()
        self.edit_panel.setFixedHeight(50)
        self.edit_panel.setVisible(False)
        # Белый фон, серая полоска сверху и красная акцентная полоска слева
        self.edit_panel.setStyleSheet("""
            QFrame { 
                background-color: white; 
                border-top: 1px solid #e0e0e0; 
            }
        """)

        edit_layout = QHBoxLayout(self.edit_panel)
        edit_layout.setContentsMargins(15, 5, 15, 5)
        edit_layout.setSpacing(10)

        # Акцентная линия слева (как в ТГ)
        line = QFrame()
        line.setFixedWidth(2)
        line.setStyleSheet("background-color: #D22730; border: none;")
        edit_layout.addWidget(line)

        # Текстовый блок (Иконка + Текст)
        text_container = QVBoxLayout()
        text_container.setSpacing(2)

        self.edit_title = QLabel("Редактирование")
        self.edit_title.setStyleSheet(
            "color: #D22730; font-weight: bold; font-size: 11px; border: none; background: transparent;")

        self.edit_label = QLabel("")  # Сюда будем писать исходный текст (Read Only)
        self.edit_label.setStyleSheet("color: #555555; font-size: 12px; border: none; background: transparent;")
        # Чтобы длинный текст не распирал панель, ставим ограничение или эллипсис
        self.edit_label.setMinimumWidth(100)

        text_container.addWidget(self.edit_title)
        text_container.addWidget(self.edit_label)
        edit_layout.addLayout(text_container, 1)

        # Кнопка отмены (Крестик)
        self.btn_cancel_edit = QPushButton("✕")
        self.btn_cancel_edit.setFixedSize(30, 30)
        self.btn_cancel_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_edit.setStyleSheet("""
            QPushButton { border: none; color: #999999; font-size: 16px; background: transparent; }
            QPushButton:hover { color: #333333; }
        """)
        edit_layout.addWidget(self.btn_cancel_edit)

        # --- ПОЛЕ ВВОДА ---
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

        # Собираем всё в правую часть
        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.scroll_container)  # Вместо прямого scroll_area
        right_layout.addWidget(self.edit_panel)  # Панель над вводом
        right_layout.addWidget(input_container)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        main_layout.addWidget(self.splitter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Сдвигаем кнопку чуть выше поля ввода (примерно на 20px от правого края и 20px от низа контейнера)
        margin_right = 25
        margin_bottom = 25

        btn_x = self.scroll_container.width() - self.btn_scroll_down.width() - margin_right
        btn_y = self.scroll_container.height() - self.btn_scroll_down.height() - margin_bottom

        self.btn_scroll_down.move(btn_x, btn_y)
        self.btn_scroll_down.raise_()  # Всегда поверх пузырьков