from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel


class NewMessagesSeparator(QFrame):
    """Виджет-разделитель для новых сообщений"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)

        # Линия слева
        line_left = QFrame()
        line_left.setFrameShape(QFrame.Shape.HLine)
        line_left.setStyleSheet("color: #D22730; background-color: #D22730;")

        # Текст
        label = QLabel("Новые сообщения")
        label.setStyleSheet("color: #D22730; font-weight: bold; padding: 0 10px; background: transparent;")

        # Линия справа
        line_right = QFrame()
        line_right.setFrameShape(QFrame.Shape.HLine)
        line_right.setStyleSheet("color: #D22730; background-color: #D22730;")

        layout.addWidget(line_left, 1)
        layout.addWidget(label)
        layout.addWidget(line_right, 1)
        self.setStyleSheet("background: transparent; border: none;")