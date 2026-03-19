from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QFrame, QVBoxLayout, QWidget, QApplication, QMenu, QSizePolicy, \
    QCheckBox


class ChatMessageWidget(QWidget):
    action_triggered = pyqtSignal(str, int)
    toggled = pyqtSignal(int, bool)  # Сигнал для ChatPage

    def __init__(self, message_id, text, sender_name, time_str,
                 is_mine=True, is_read=False, is_edited=False,
                 reply_to_id=None, reply_text=None, reply_sender_name=None,
                 forward_from_name=None, parent=None):
        super().__init__(parent)
        self.message_id = message_id
        self.text = text
        self.sender_name = sender_name
        self.time_str = time_str
        self.is_mine = is_mine
        self.is_read = is_read
        self.is_edited = is_edited

        self.reply_to_id = reply_to_id
        self.reply_text = reply_text
        self.reply_sender_name = reply_sender_name
        self.forward_from_name = forward_from_name

        self.init_ui()
        self.update_bubble_width()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 2, 10, 2)
        self.main_layout.setSpacing(10)  # Добавим немного отступа для чекбокса

        # СНАЧАЛА создаем чекбокс
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(False)
        self.checkbox.stateChanged.connect(self._on_toggled)

        # ДОБАВЛЯЕМ его в лейаут самым первым (слева)
        self.main_layout.addWidget(self.checkbox)

        self.bubble = QFrame()
        self.bubble.setObjectName("bubble")
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

        if self.forward_from_name:
            forward_label = QLabel(f"↪ Переслано от {self.forward_from_name}")
            forward_label.setStyleSheet(
                "font-size: 10px; font-style: italic; color: #888; border-left: 2px solid #D22730; padding-left: 5px;")
            bubble_layout.addWidget(forward_label)

        if not self.is_mine:
            name_lbl = QLabel(self.sender_name)
            name_lbl.setStyleSheet("font-weight: bold; color: #D22730; font-size: 11px;")
            bubble_layout.addWidget(name_lbl)

        if self.reply_text:
            self.reply_pane = QFrame()
            self.reply_pane.setObjectName("reply_pane")
            self.reply_pane.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reply_pane.setStyleSheet(
                "QFrame#reply_pane { background-color: rgba(0, 0, 0, 0.05); border-left: 3px solid #34B7F1; border-radius: 4px; }")
            r_lay = QVBoxLayout(self.reply_pane)
            r_name = QLabel(self.reply_sender_name or "Сообщение")
            r_name.setStyleSheet("font-weight: bold; color: #34B7F1; font-size: 10px;")
            short_text = self.reply_text[:50] + "..." if len(self.reply_text) > 50 else self.reply_text
            r_content = QLabel(short_text)
            r_content.setStyleSheet("color: #555; font-size: 10px;")
            r_lay.addWidget(r_name)
            r_lay.addWidget(r_content)
            bubble_layout.addWidget(self.reply_pane)
            self.reply_pane.mousePressEvent = self.on_reply_clicked

        self.msg_lbl = QLabel(self.text)
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(self.msg_lbl)

        meta_layout = QHBoxLayout()
        meta_layout.addStretch()
        self.edit_label = QLabel("ред.")
        self.edit_label.setStyleSheet("color: gray; font-size: 9px; font-style: italic;")
        self.edit_label.setVisible(self.is_edited)
        meta_layout.addWidget(self.edit_label)

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

    def set_read_status(self, status: bool):
        """Обновляет визуальное состояние галочек"""
        self.is_read = status
        # Проверяем, существует ли статусная метка (она есть только у 'mine' сообщений)
        if self.is_read and self.status_lbl:
            icon = "✓✓" if status else "✓"
            color = "#34B7F1" if status else "gray"
            self.status_lbl.setText(icon)
            self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def on_reply_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.action_triggered.emit("goto", self.reply_to_id)

    def update_bubble_width(self):
        p = self.parentWidget()
        # Определяем доступную ширину (70% от окна)
        parent_w = p.width() if p and p.width() > 1 else 600
        max_bubble_w = int(parent_w * 0.7)

        metrics = self.msg_lbl.fontMetrics()

        # 1. Считаем ширину имени отправителя (если оно есть и сообщение не моё)
        name_w = 0
        if not self.is_mine and hasattr(self, 'sender_name'):
            # Добавляем запас на отступы (padding)
            name_w = metrics.horizontalAdvance(self.sender_name) + 25

        # 2. Считаем ширину текста сообщения
        # boundingRect определит, сколько места займет текст с учетом переносов
        rect = metrics.boundingRect(0, 0, max_bubble_w - 30, 1000, Qt.TextFlag.TextWordWrap, self.text)
        text_w = rect.width() + 35

        # 3. Считаем ширину строки пересылки (если есть)
        forward_w = 0
        if self.forward_from_name:
            f_text = f"↪ Переслано от {self.forward_from_name}"
            forward_w = metrics.horizontalAdvance(f_text) + 45

        # 4. Считаем ширину цитаты (Reply Pane), если она есть
        reply_w = 0
        if self.reply_text:
            # Берем либо имя отправителя цитаты, либо кусочек текста цитаты
            r_name_w = metrics.horizontalAdvance(self.reply_sender_name or "") + 40
            reply_w = max(r_name_w, 150)  # Минимум 150 для красоты цитаты

        # Итоговая ширина — это максимум из всех элементов, но не больше max_bubble_w
        final_w = max(text_w, name_w, forward_w, reply_w, 100)

        self.bubble.setFixedWidth(min(final_w, max_bubble_w))

    def update_text(self, new_text):
        """Прямое и жесткое обновление текста"""
        # Блокируем сигналы на время обновления, чтобы не вызвать рекурсию
        self.blockSignals(True)
        try:
            self.text = new_text
            self.is_edited = True

            if self.msg_lbl:
                self.msg_lbl.setText(new_text)
                # Заставляем лейбл немедленно пересчитать свой размер
                self.msg_lbl.adjustSize()

            if hasattr(self, 'edit_label') and self.edit_label:
                self.edit_label.setVisible(True)

            # Пересчитываем пузырек
            self.update_bubble_width()

            # ВАЖНО: говорим Qt, что виджет нужно перерисовать прямо сейчас
            self.update()

            self.highlight_update()
            print(f"✅ Виджет {self.message_id} успешно перерисован с новым текстом")

        finally:
            self.blockSignals(False)

    def highlight_update(self):
        """Легкая подсветка изменений"""
        if not hasattr(self, 'bubble') or self.bubble is None:
            return

        try:
            # Используем встроенный механизм свойств Qt, это стабильнее, чем менять таблицу стилей целиком
            self.bubble.setLineWidth(2)
            # Через полсекунды возвращаем как было
            QTimer.singleShot(500, lambda: self.bubble.setLineWidth(1) if self.bubble else None)
        except RuntimeError:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_bubble_width()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        reply_act = QAction("↪️ Ответить", self)
        forward_act = QAction("➡️ Переслать", self)
        select_act = QAction("✅ Выбрать", self)  # Добавляем пункт в меню
        copy_act = QAction("📋 Копировать", self)

        menu.addActions([reply_act, forward_act, select_act, copy_act])

        edit_act = None
        delete_act = None
        if self.is_mine:
            menu.addSeparator()
            edit_act = QAction("✏️ Редактировать", self)
            delete_act = QAction("🗑️ Удалить", self)
            menu.addActions([edit_act, delete_act])

        action = menu.exec(self.mapToGlobal(pos))
        if action == copy_act:
            QApplication.clipboard().setText(self.text)
        elif action == select_act:
            self.action_triggered.emit("select", self.message_id)
        elif action == reply_act:
            self.action_triggered.emit("reply", self.message_id)
        elif action == forward_act:
            self.action_triggered.emit("forward", self.message_id)
        elif edit_act and action == edit_act:
            self.action_triggered.emit("edit", self.message_id)
        elif delete_act and action == delete_act:
            self.action_triggered.emit("delete", self.message_id)

    def highlight(self):
        old_style = self.bubble.styleSheet()
        highlight_color = "#E1F5FE"
        self.bubble.setStyleSheet(f"""
            QFrame#bubble {{ 
                background-color: {highlight_color}; 
                border-radius: 12px; 
                border: 2px solid #34B7F1; 
            }}
        """)
        QTimer.singleShot(1000, lambda: self.bubble.setStyleSheet(old_style))

    def _on_toggled(self, state):
        # Отправляем сигнал наверх в ChatPage
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)
        self.toggled.emit(self.message_id, is_checked)

    def set_selection_mode(self, enabled):
        """Включает/выключает отображение чекбокса"""
        if hasattr(self, 'checkbox'):
            self.checkbox.setVisible(enabled)
            if not enabled:
                self.checkbox.setChecked(False)

    def set_selected(self, selected):
        """Программная установка галочки"""
        if hasattr(self, 'checkbox'):
            self.checkbox.setChecked(selected)