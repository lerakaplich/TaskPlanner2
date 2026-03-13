from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QFrame, QVBoxLayout, QWidget, QApplication, QMenu, QSizePolicy


class ChatMessageWidget(QWidget):
    action_triggered = pyqtSignal(str, int)

    def __init__(self, message_id, text, sender_name, time_str,
                 is_mine=True, is_read=False, is_edited=False, parent=None): # Добавили аргумент
        super().__init__(parent)
        self.message_id = message_id
        self.text = text
        self.sender_name = sender_name
        self.time_str = time_str
        self.is_mine = is_mine
        self.is_read = is_read
        self.is_edited = is_edited  # ОБЯЗАТЕЛЬНО сохраняем в self
        self.init_ui()
        self.update_bubble_width()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 2, 10, 2)
        self.main_layout.setSpacing(0)

        self.bubble = QFrame()
        self.bubble.setObjectName("bubble")

        # Устанавливаем политику: пузырек может расти, но не жадничает
        self.bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        bg = "#DCF8C6" if self.is_mine else "#FFFFFF"
        self.bubble.setStyleSheet(f"""
            QFrame#bubble {{
                background-color: {bg};
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }}
            QFrame#bubble QLabel {{ background: transparent; border: none; }}
        """)

        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(10, 8, 10, 8)
        bubble_layout.setSpacing(4)

        if not self.is_mine:
            name_lbl = QLabel(self.sender_name)
            name_lbl.setStyleSheet("font-weight: bold; color: #D22730; font-size: 11px;")
            bubble_layout.addWidget(name_lbl)

        # Текст сообщения
        self.msg_lbl = QLabel(self.text)
        self.msg_lbl.setWordWrap(True)
        # Самая важная политика для растяжения вширь
        self.msg_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(self.msg_lbl)

        # Мета (время, ред, статус)
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(5)
        meta_layout.addStretch()

        if self.is_edited:
            edit_label = QLabel("ред.")
            edit_label.setStyleSheet("color: gray; font-size: 9px; font-style: italic; margin-right: 3px;")
            meta_layout.addWidget(edit_label)

        self.time_lbl = QLabel(self.time_str)
        self.time_lbl.setStyleSheet("color: gray; font-size: 10px;")
        meta_layout.addWidget(self.time_lbl)

        if self.is_mine:
            status = "✓✓" if self.is_read else "✓"
            color = "#34B7F1" if self.is_read else "gray"
            self.status_lbl = QLabel(status)
            self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
            meta_layout.addWidget(self.status_lbl)

        bubble_layout.addLayout(meta_layout)

        if self.is_mine:
            self.main_layout.addStretch(1)
            self.main_layout.addWidget(self.bubble)
        else:
            self.main_layout.addWidget(self.bubble)
            self.main_layout.addStretch(1)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_bubble_width(self):
        # Проверка на наличие всех критических виджетов
        if not hasattr(self, 'bubble') or not hasattr(self, 'msg_lbl'):
            return

        # Определяем доступную ширину чата (70% от родителя)
        parent_w = self.parentWidget().width() if self.parentWidget() else self.width()
        if parent_w < 100: parent_w = 500  # дефолт

        max_bubble_w = int(parent_w * 0.5)

        # Считаем, сколько пикселей занял бы текст БЕЗ переноса
        metrics = self.msg_lbl.fontMetrics()
        text_width = metrics.boundingRect(self.text).width() + 25  # +25 на отступы

        # Идеальная ширина: либо сколько нужно тексту, либо лимит 70%
        target_width = min(text_width, max_bubble_w)

        # Если в тексте есть принудительные переносы \n, target_width может быть меньше.
        # Поэтому установим MinimumWidth, чтобы QLabel расширился
        self.msg_lbl.setMinimumWidth(target_width)
        self.bubble.setMaximumWidth(max_bubble_w)

        # Важно вызвать это, чтобы QLayout пересчитал всё
        self.bubble.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_bubble_width()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_act = QAction("📋 Копировать", self)

        menu.addAction(copy_act)

        # Редактировать и Удалять можно только СВОИ сообщения
        if self.is_mine:
            edit_act = QAction("✏️ Редактировать", self)
            delete_act = QAction("🗑️ Удалить", self)
            menu.addSeparator()
            menu.addActions([edit_act, delete_act])
        else:
            edit_act = None
            delete_act = None

        action = menu.exec(self.mapToGlobal(pos))

        if action == copy_act:
            QApplication.clipboard().setText(self.text)
        elif edit_act and action == edit_act:
            self.action_triggered.emit("edit", self.message_id)
        elif delete_act and action == delete_act:
            self.action_triggered.emit("delete", self.message_id)