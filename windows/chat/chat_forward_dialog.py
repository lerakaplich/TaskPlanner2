from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QLineEdit, QPushButton, QLabel)
from PyQt6.QtCore import Qt


class ForwardDialog(QDialog):
    """Окно выбора чата для пересылки сообщения"""

    def __init__(self, chats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Переслать")
        self.setFixedSize(350, 450)
        self.all_chats = chats  # Список DTO чатов
        self.selected_chat_id = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel("Выберите чат")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background: #f9f9f9;
            }
        """)
        self.search_input.textChanged.connect(self.filter_chats)
        layout.addWidget(self.search_input)

        # Список чатов
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("""
            QListWidget { border: 1px solid #eee; border-radius: 5px; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background-color: #f0f2f5; color: #D22730; }
        """)
        # Двойной клик сразу выбирает чат
        self.chat_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.chat_list)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("padding: 8px 15px;")

        self.btn_forward = QPushButton("Переслать")
        self.btn_forward.setStyleSheet("""
            QPushButton { 
                background-color: #D22730; 
                color: white; 
                border-radius: 5px; 
                padding: 8px 20px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #b01f28; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.btn_forward.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_forward)
        layout.addLayout(btn_layout)

        self.fill_chats()

        # Блокируем кнопку, если ничего не выбрано
        self.btn_forward.setEnabled(False)
        self.chat_list.itemSelectionChanged.connect(
            lambda: self.btn_forward.setEnabled(len(self.chat_list.selectedItems()) > 0)
        )

    def fill_chats(self, filter_text=""):
        self.chat_list.clear()
        for chat in self.all_chats:
            if filter_text.lower() in chat.display_name.lower():
                icon = "📁" if chat.type == "project" else "👥" if chat.type == "group" else "👤"
                item = QListWidgetItem(f"{icon} {chat.display_name}")
                item.setData(Qt.ItemDataRole.UserRole, chat.id)
                self.chat_list.addItem(item)

    def filter_chats(self, text):
        self.fill_chats(text)

    def get_selected_chat_id(self):
        """Возвращает ID выбранного чата как целое число"""
        item = self.chat_list.currentItem()
        if item:
            return int(item.data(Qt.ItemDataRole.UserRole))
        return None