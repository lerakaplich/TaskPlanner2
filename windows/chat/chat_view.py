from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                             QLineEdit, QPushButton, QSplitter, QLabel, QFrame,
                             QScrollArea, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from windows.chat.chat_text_edit import GrowingTextEdit


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
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background: #F5F5F5; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #C1C1C1; border-radius: 4px; min-height: 20px; }
            QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; }
        """)

        self.messages_container = QWidget()
        self.messages_container.setObjectName("messages_container")
        self.messages_container.setStyleSheet("background-color: #f0f2f5;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.messages_container)
        scroll_container_layout.addWidget(self.scroll_area)

        # Кнопка прокрутки вниз
        self.btn_scroll_down = QPushButton("↓", self.scroll_container)
        self.btn_scroll_down.setFixedSize(40, 40)
        self.btn_scroll_down.setVisible(False)
        self.btn_scroll_down.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scroll_down.setStyleSheet("""
            QPushButton { background-color: white; color: #555; border: 1px solid #ddd; border-radius: 20px; font-size: 18px; font-weight: bold; }
            QPushButton:hover { background-color: #f8f8f8; }
        """)

        # --- ПАНЕЛЬ РЕДАКТИРОВАНИЯ ---
        self.edit_panel = QFrame()
        self.edit_panel.setFixedHeight(50)
        self.edit_panel.setVisible(False)
        self.edit_panel.setStyleSheet("QFrame { background-color: white; border-top: 1px solid #e0e0e0; }")

        edit_layout = QHBoxLayout(self.edit_panel)
        edit_layout.setContentsMargins(15, 5, 15, 5)
        line = QFrame()
        line.setFixedWidth(2)
        line.setStyleSheet("background-color: #D22730; border: none;")
        edit_layout.addWidget(line)

        text_container = QVBoxLayout()
        self.edit_title = QLabel("Редактирование")
        self.edit_title.setStyleSheet("color: #D22730; font-weight: bold; font-size: 11px; background: transparent;")
        self.edit_label = QLabel("")
        self.edit_label.setStyleSheet("color: #555555; font-size: 12px; background: transparent;")
        text_container.addWidget(self.edit_title)
        text_container.addWidget(self.edit_label)
        edit_layout.addLayout(text_container, 1)

        self.btn_cancel_edit = QPushButton("✕")
        self.btn_cancel_edit.setFixedSize(30, 30)
        self.btn_cancel_edit.setStyleSheet(
            "QPushButton { border: none; color: #999999; font-size: 16px; background: transparent; }")
        edit_layout.addWidget(self.btn_cancel_edit)

        # --- ОБЩИЙ НИЖНИЙ КОНТЕЙНЕР (Исправлено для роста вверх) ---
        self.input_container = QFrame()
        # Убрали fixedHeight, чтобы контейнер мог растягиваться
        self.input_container.setMinimumHeight(60)
        self.input_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.input_container.setStyleSheet("border-top: 1px solid #e0e0e0; background-color: white;")

        stack_layout = QVBoxLayout(self.input_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)

        # 1. Фрейм обычного ввода
        self.input_frame = QFrame()
        input_inner_layout = QHBoxLayout(self.input_frame)
        input_inner_layout.setContentsMargins(10, 10, 10, 10)
        # Прижимаем элементы ввода к низу, чтобы поле росло вверх
        input_inner_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.message_input = GrowingTextEdit()
        # Применяем стили, включая кастомный скроллбар
        self.message_input.setStyleSheet("""
                    QTextEdit { 
                        padding: 8px 15px; 
                        border: 1px solid #e0e0e0; 
                        border-radius: 18px; 
                        background: #f0f2f5; 
                        font-size: 14px; 
                    }
                    /* Красивый скроллбар для поля ввода */
                    QScrollBar:vertical {
                        background: transparent;
                        width: 6px;
                        margin: 4px 2px 4px 0;
                    }
                    QScrollBar::handle:vertical {
                        background: #C1C1C1;
                        border-radius: 3px;
                        min-height: 20px;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                """)

        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(45, 45)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet(
            "QPushButton { background-color: #D22730; color: white; border-radius: 22px; font-size: 20px; padding-left: 3px; }")

        input_inner_layout.addWidget(self.message_input)
        input_inner_layout.addWidget(self.btn_send)
        stack_layout.addWidget(self.input_frame)

        # 2. Фрейм выбора (selection_toolbar)
        self.selection_toolbar = QFrame()
        self.selection_toolbar.setFixedHeight(60)  # Для тулбара выбора можно оставить фикс
        self.selection_toolbar.setVisible(False)
        self.selection_toolbar.setStyleSheet("background-color: #f8f9fa; border-top: 1px solid #e0e0e0;")
        sel_inner_layout = QHBoxLayout(self.selection_toolbar)
        sel_inner_layout.setContentsMargins(15, 0, 15, 0)

        self.btn_cancel_sel = QPushButton("Отмена")
        self.btn_cancel_sel.setStyleSheet("color: #666; font-weight: bold; border: none; background: transparent;")

        self.lbl_sel_count = QLabel("Выбрано: 0")
        self.lbl_sel_count.setStyleSheet("font-weight: bold; color: #D22730; background: transparent;")

        self.btn_forward_sel = QPushButton("➡️ Переслать")
        self.btn_forward_sel.setStyleSheet(
            "QPushButton { background-color: #D22730; color: white; border-radius: 5px; padding: 8px 15px; font-weight: bold; }")

        sel_inner_layout.addWidget(self.btn_cancel_sel)
        sel_inner_layout.addStretch()
        sel_inner_layout.addWidget(self.lbl_sel_count)
        sel_inner_layout.addStretch()
        sel_inner_layout.addWidget(self.btn_forward_sel)
        stack_layout.addWidget(self.selection_toolbar)

        # Сборка правой панели
        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.scroll_container)
        right_layout.addWidget(self.edit_panel)
        right_layout.addWidget(self.input_container)

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