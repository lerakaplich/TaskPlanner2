from PyQt6.QtWidgets import QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal


class GrowingTextEdit(QTextEdit):
    returnPressed = pyqtSignal()  # Чтобы сохранить совместимость с QLineEdit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Напишите сообщение...")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.min_height = 40
        self.max_height = 150
        self.setFixedHeight(self.min_height)

        self.textChanged.connect(self.adjust_height)

        # Полный набор стилей для самого поля и его скроллбара
        self.setStyleSheet("""
            QTextEdit {
                padding: 8px 15px;
                border: 1px solid #e0e0e0;
                border-radius: 18px;
                background: #f0f2f5;
                font-size: 14px;
                selection-background-color: #D22730;
            }

            /* Стилизация вертикального скроллбара внутри QTextEdit */
            QTextEdit QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0;
            }

            QTextEdit QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 3px;
                min-height: 20px;
            }

            QTextEdit QScrollBar::handle:vertical:hover {
                background: #A8A8A8;
            }

            QTextEdit QScrollBar::add-line:vertical, 
            QTextEdit QScrollBar::sub-line:vertical,
            QTextEdit QScrollBar::add-page:vertical, 
            QTextEdit QScrollBar::sub-page:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)

    def adjust_height(self):
        doc_height = self.document().size().height()
        new_height = int(doc_height + 10)

        if new_height < self.min_height:
            new_height = self.min_height

        if new_height >= self.max_height:
            new_height = self.max_height
            # Включаем скролл, когда достигли лимита
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            # Прячем, если места достаточно
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        if self.height() != new_height:
            self.setFixedHeight(new_height)
            self.updateGeometry()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.returnPressed.emit()
        else:
            super().keyPressEvent(event)