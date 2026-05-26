from datetime import datetime

from typing import Optional, Tuple

from PyQt6.QtCore import QDate

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
    QDialog, QVBoxLayout as QVBoxDialog,
    QPushButton, QDateEdit, QMessageBox

)

class PeriodDialog(QDialog):
    """Диалог выбора произвольного периода."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбрать период")
        self.setMinimumSize(350, 200)
        self.start_date: Optional[QDate] = None
        self.end_date: Optional[QDate] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка интерфейса диалога."""
        layout = QVBoxDialog(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Дата начала
        start_label = QLabel("Дата начала:")
        start_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1B232A;")
        layout.addWidget(start_label)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(QDate.currentDate())
        self.start_edit.setStyleSheet("""
            QDateEdit {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.start_edit)

        # Дата окончания
        end_label = QLabel("Дата окончания:")
        end_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1B232A;")
        layout.addWidget(end_label)

        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDate(QDate.currentDate().addMonths(1))
        self.end_edit.setStyleSheet("""
            QDateEdit {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.end_edit)

        # Кнопки
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Применить")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        ok_button.clicked.connect(self._on_accept)

        cancel_button = QPushButton("Отмена")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def _on_accept(self) -> None:
        """Обработка принятия диалога."""
        if self.start_edit.date() >= self.end_edit.date():
            QMessageBox.warning(
                self, "Ошибка",
                "Дата начала должна быть раньше даты окончания."
            )
            return
        self.start_date = self.start_edit.date()
        self.end_date = self.end_edit.date()
        self.accept()

    def get_dates(self) -> Tuple[datetime, datetime]:
        """Получить выбранные даты как datetime."""
        start = self.start_date.toPyDate()
        end = self.end_date.toPyDate()
        return (
            datetime(start.year, start.month, start.day),
            datetime(end.year, end.month, end.day)
        )