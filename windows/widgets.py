from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDateEdit, QSizePolicy
)
from PyQt6.QtCore import QDate

CALENDAR_STYLE = """
QCalendarWidget QWidget {
    color: black;
    background-color: white;
}

QCalendarWidget QAbstractItemView {
    color: black;
    selection-background-color: #ccab6e;
    selection-color: white;
}

QCalendarWidget QToolButton {
    color: black;
    font-weight: bold;
    background: transparent;
}

QCalendarWidget QToolButton:hover {
    background-color: #e6e6e6;
}

QCalendarWidget QSpinBox {
    color: black;
    background: white;
}

QCalendarWidget QHeaderView::section {
    color: black;
    background-color: #f2f2f2;
    font-weight: bold;
}
"""

class DateRangeDialog(QDialog):
    """
    Универсальный диалог выбора диапазона дат
    Используется ВЕЗДЕ
    """

    def __init__(
        self,
        parent=None,
        title="Выбор периода",
        start_label="Дата начала:",
        end_label="Дата окончания:",
        default_start=None,
        default_end=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setFixedSize(280, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # ----- Дата начала -----
        start_layout = QVBoxLayout()
        start_label_widget = QLabel(start_label)
        start_label_widget.setStyleSheet("font-size: 11px;")




        self.start_date_edit = QDateEdit()
        self.start_date_edit.setStyleSheet(CALENDAR_STYLE)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.start_date_edit.setDate(
            default_start if default_start else QDate.currentDate().addMonths(-1)
        )

        start_layout.addWidget(start_label_widget)
        start_layout.addWidget(self.start_date_edit)
        layout.addLayout(start_layout)

        # ----- Дата окончания -----
        end_layout = QVBoxLayout()
        end_label_widget = QLabel(end_label)
        end_label_widget.setStyleSheet("font-size: 11px;")

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setStyleSheet(CALENDAR_STYLE)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.end_date_edit.setDate(
            default_end if default_end else QDate.currentDate()
        )

        end_layout.addWidget(end_label_widget)
        end_layout.addWidget(self.end_date_edit)
        layout.addLayout(end_layout)

        # ----- Кнопка -----
        apply_btn = QPushButton("Применить")
        apply_btn.setFixedHeight(30)
        apply_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 4px;
                font-size: 12px;
                border: none;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
        """)

        apply_btn.clicked.connect(self.accept)
        layout.addWidget(apply_btn)

    # ===== ЕДИНЫЙ API =====

    def get_qdates(self):
        """
        Старый стиль — возвращает QDate
        """
        if self.exec() == QDialog.DialogCode.Accepted:
            return (
                self.start_date_edit.date(),
                self.end_date_edit.date(),
            )
        return None, None

    def get_dates(self):
        """
        Новый стиль — возвращает datetime.date
        """
        start_qdate, end_qdate = self.get_qdates()
        if not start_qdate:
            return None, None
        return start_qdate.toPyDate(), end_qdate.toPyDate()