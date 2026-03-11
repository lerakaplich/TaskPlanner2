import os
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QDate
from PyQt6 import uic


class PeriodDialog(QDialog):
    """Диалог выбора периода. Только UI"""

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "period_dialog.ui"), self)

        self.setWindowTitle("Выбор периода экспорта")

        # Даты по умолчанию
        today = QDate.currentDate()
        self.dateStart.setDate(today.addMonths(-1))
        self.dateEnd.setDate(today)

        self.btnOk.clicked.connect(self.accept)

    def get_period(self):
        """Возвращает выбранные даты: (start_date, end_date)"""
        return self.dateStart.date(), self.dateEnd.date()