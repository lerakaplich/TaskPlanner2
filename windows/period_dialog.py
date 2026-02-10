import os
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6 import uic
from datetime import datetime, timedelta
import random

from PyQt6.uic import loadUi

from windows.overtime_card import OvertimeCard


class PeriodDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "period_dialog.ui"), self)
        self.setWindowTitle("Выбор периода экспорта")

        # Устанавливаем даты по умолчанию
        today = QDate.currentDate()
        self.dateStart.setDate(today.addMonths(-1))
        self.dateEnd.setDate(today)

        self.btnOk.clicked.connect(self.accept)

    def get_period(self):
        return self.dateStart.date(), self.dateEnd.date()