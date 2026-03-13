from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QFrame, QVBoxLayout, QWidget, QApplication, QMenu


class ChatMessageWidget(QWidget):
    action_triggered = pyqtSignal(str, int)

    def __init__(self, message_id, text, sender_name, time_str, is_mine=True, is_read=False, parent=None):
        super().__init__(parent)
        self.message_id = message_id
        self.text = text
        self.sender_name = sender_name
        self.time_str = time_str
        self.is_mine = is_mine
        self.is_read = is_read
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self.bubble = QFrame()
        self.bubble.setObjectName("bubble")
        bg = "#DCF8C6" if self.is_mine else "#FFFFFF"
        self.bubble.setStyleSheet(
            f"QFrame#bubble {{ background-color: {bg}; border-radius: 12px; border: 1px solid #E0E0E0; }}")

        bubble_layout = QVBoxLayout(self.bubble)

        # Имя (для чужих)
        if not self.is_mine:
            name_lbl = QLabel(self.sender_name)
            name_lbl.setStyleSheet("font-weight: bold; color: #D22730; font-size: 10px;")
            bubble_layout.addWidget(name_lbl)

        # Текст
        msg_lbl = QLabel(self.text)
        msg_lbl.setWordWrap(True)
        bubble_layout.addWidget(msg_lbl)

        # Время и галочки
        meta_layout = QHBoxLayout()
        time_lbl = QLabel(self.time_str)
        time_lbl.setStyleSheet("color: gray; font-size: 9px;")
        meta_layout.addStretch()
        meta_layout.addWidget(time_lbl)

        if self.is_mine:
            status = "✓✓" if self.is_read else "✓"
            color = "#34B7F1" if self.is_read else "gray"
            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
            meta_layout.addWidget(status_lbl)

        bubble_layout.addLayout(meta_layout)

        if self.is_mine:
            layout.addStretch(); layout.addWidget(self.bubble)
        else:
            layout.addWidget(self.bubble); layout.addStretch()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_act = QAction("📋 Копировать", self)
        edit_act = QAction("✏️ Редактировать", self)
        delete_act = QAction("🗑️ Удалить", self)

        menu.addActions([copy_act, edit_act])
        menu.addSeparator()
        menu.addAction(delete_act)

        action = menu.exec(self.mapToGlobal(pos))
        if action == edit_act:
            self.action_triggered.emit("edit", self.message_id)
        elif action == delete_act:
            self.action_triggered.emit("delete", self.message_id)
        elif action == copy_act:
            QApplication.clipboard().setText(self.text)