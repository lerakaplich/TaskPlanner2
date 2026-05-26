
from typing import Optional


from PyQt6.QtWidgets import (
    QWidget, QLabel, QDialog, QVBoxLayout as QVBoxDialog,
    QCheckBox, QPushButton
)


class LinkDialog(QDialog):
    """Диалог с инструкцией по созданию связей."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создание связи между задачами")
        self.setMinimumSize(500, 350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка интерфейса диалога."""
        layout = QVBoxDialog(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Инструкция
        instruction_text = (
            "<h3 style='color: #1B232A;'>📋 Инструкция по созданию связей</h3>"
            "<p style='font-size: 14px; line-height: 1.6;'>"
            "Связи между задачами позволяют автоматически синхронизировать "
            "сроки зависимых задач при изменении дат основной задачи."
            "</p>"
            "<p style='font-size: 14px; line-height: 1.6;'>"
            "<b>Как создать связь:</b><br>"
            "1. Нажмите <b>Ctrl+клик</b> на первой задаче (предшественник)<br>"
            "2. Затем <b>Ctrl+клик</b> на второй задаче (последователь)<br>"
            "3. Подтвердите создание связи в появившемся окне"
            "</p>"
            "<p style='font-size: 14px; line-height: 1.6;'>"
            "<b>Пример:</b><br>"
            "<i>Ctrl+клик</i> на «Анализ конкурентов» → "
            "<i>Ctrl+клик</i> на «Прототипирование» → "
            "связь создана! Теперь при сдвиге «Анализа» "
            "«Прототипирование» сдвинется автоматически."
            "</p>"
            "<p style='font-size: 13px; color: #ccab6e;'>"
            "💡 <b>Совет:</b> Связи отображаются стрелками на диаграмме."
            "</p>"
        )
        instruction_label = QLabel(instruction_text)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("QLabel { padding: 10px; }")
        layout.addWidget(instruction_label)

        # Чекбокс "Больше не показывать"
        self.dont_show_checkbox = QCheckBox("Больше не показывать это окно")
        self.dont_show_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #1B232A;
                spacing: 8px;
            }
        """)
        layout.addWidget(self.dont_show_checkbox)

        # Кнопка закрытия
        close_button = QPushButton("Понятно")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                border: none;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)