from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QFrame, QVBoxLayout, QWidget, QApplication, QMenu, QSizePolicy


class ChatMessageWidget(QWidget):
    action_triggered = pyqtSignal(str, int)

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

        # Данные для ответов и пересылок
        self.reply_to_id = reply_to_id
        self.reply_text = reply_text
        self.reply_sender_name = reply_sender_name
        self.forward_from_name = forward_from_name

        self.init_ui()
        self.update_bubble_width()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 2, 10, 2)
        self.main_layout.setSpacing(0)

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

        # Основной лейаут внутри пузырька
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(10, 8, 10, 8)
        bubble_layout.setSpacing(4)

        # 1. Если это ПЕРЕСЛАННОЕ сообщение
        if self.forward_from_name:
            forward_label = QLabel(f"↪ Переслано от {self.forward_from_name}")
            forward_label.setStyleSheet("""
                font-size: 10px; 
                font-style: italic; 
                color: #888; 
                margin-bottom: 2px;
                border-left: 2px solid #D22730;
                padding-left: 5px;
            """)
            bubble_layout.insertWidget(0, forward_label)  # Ставим в самый верх пузырька

        # 2. Имя отправителя (если не моё)
        if not self.is_mine:
            name_lbl = QLabel(self.sender_name)
            name_lbl.setStyleSheet("font-weight: bold; color: #D22730; font-size: 11px;")
            bubble_layout.addWidget(name_lbl)

        # 3. ЦИТАТА (если есть ответ)
        if self.reply_text:
            self.reply_pane = QFrame()
            self.reply_pane.setObjectName("reply_pane")
            self.reply_pane.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reply_pane.setStyleSheet("""
                QFrame#reply_pane {
                    background-color: rgba(0, 0, 0, 0.05);
                    border-left: 3px solid #34B7F1;
                    border-radius: 4px;
                }
                QFrame#reply_pane:hover { background-color: rgba(0, 0, 0, 0.08); }
            """)

            reply_lay = QVBoxLayout(self.reply_pane)
            reply_lay.setContentsMargins(8, 4, 4, 4)
            reply_lay.setSpacing(2)

            r_name = QLabel(self.reply_sender_name or "Сообщение")
            r_name.setStyleSheet("font-weight: bold; color: #34B7F1; font-size: 10px;")

            short_text = self.reply_text[:50] + "..." if len(self.reply_text) > 50 else self.reply_text
            r_content = QLabel(short_text)
            r_content.setStyleSheet("color: #555; font-size: 10px;")

            reply_lay.addWidget(r_name)
            reply_lay.addWidget(r_content)
            bubble_layout.addWidget(self.reply_pane)

            # Подключаем клик по цитате
            self.reply_pane.mousePressEvent = self.on_reply_clicked

        # 4. Текст сообщения
        self.msg_lbl = QLabel(self.text)
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(self.msg_lbl)

        # 5. Мета-данные (Время, Статус, Редактирование)
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(5)
        meta_layout.addStretch()

        # Создаем edit_label ВСЕГДА, но скрываем, если не редактировалось
        self.edit_label = QLabel("ред.")
        self.edit_label.setStyleSheet("color: gray; font-size: 9px; font-style: italic;")
        self.edit_label.setVisible(self.is_edited)  # Показываем только если True
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

        # Добавляем пузырек в основной лейаут виджета
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
        if hasattr(self, 'status_lbl') and self.status_lbl:
            icon = "✓✓" if status else "✓"
            color = "#34B7F1" if status else "gray"
            self.status_lbl.setText(icon)
            self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def on_reply_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.action_triggered.emit("goto", self.reply_to_id)

    def update_bubble_width(self):
        # Если виджет в процессе удаления или нет ссылки на пузырек
        if not self or not hasattr(self, 'bubble') or self.bubble is None:
            return

        try:
            # Проверяем, жив ли родитель
            p = self.parentWidget()
            if p is None:
                return

            parent_w = p.width()
            # Если ширина родителя еще не определена (0 или 1), берем фиксированную
            if parent_w <= 1:
                parent_w = 600

            max_bubble_w = int(parent_w * 0.7)

            # Обновляем размеры
            self.msg_lbl.setMinimumWidth(10)  # Сброс, чтобы не мешал расчету
            metrics = self.msg_lbl.fontMetrics()
            # Используем boundingRect для более точного расчета
            rect = metrics.boundingRect(0, 0, max_bubble_w - 20, 1000, Qt.TextFlag.TextWordWrap, self.text)

            target_width = max(rect.width() + 25, 100)
            self.bubble.setFixedWidth(min(target_width, max_bubble_w))

        except (RuntimeError, AttributeError):
            pass

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
        copy_act = QAction("📋 Копировать", self)
        menu.addActions([reply_act, forward_act, copy_act])

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
