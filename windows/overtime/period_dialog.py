import os

from PyQt6 import uic
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

from PyQt6.uic import loadUi


class PeriodDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "overtime"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "period_dialog.ui"), self)


        self.setWindowTitle("Выбор периода экспорта")

        # Устанавливаем даты по умолчанию
        today = QDate.currentDate()
        self.dateStart.setDate(today.addMonths(-1))
        self.dateEnd.setDate(today)

        self.btnOk.clicked.connect(self.accept)

    def get_period(self):
        return self.dateStart.date(), self.dateEnd.date()