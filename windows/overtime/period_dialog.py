# windows/overtime/period_dialog.py

import os
from typing import Tuple, Optional
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QDate
from PyQt6 import uic


class PeriodDialog(QDialog):
    """Диалог выбора периода экспорта с фильтрами"""

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

        # Инициализация фильтров
        self.init_filters()

        # Сигналы
        self.btnOk.clicked.connect(self.accept)
        self.comboDivision.currentIndexChanged.connect(self.on_division_changed)

    def init_filters(self):
        """Инициализация фильтров"""
        # Фильтр по подразделениям (выбираем сначала)
        self.comboDivision.clear()
        self.comboDivision.addItem("Все подразделения", None)
        self.comboDivision.addItem("Разработка", "Разработка")
        self.comboDivision.addItem("Тестирование", "Тестирование")
        self.comboDivision.addItem("Инфраструктура", "Инфраструктура")
        self.comboDivision.addItem("Аналитика", "Аналитика")
        self.comboDivision.addItem("Управление", "Управление")
        self.comboDivision.addItem("Дизайн", "Дизайн")
        self.comboDivision.addItem("Бухгалтерия", "Бухгалтерия")
        self.comboDivision.addItem("Администрирование", "Администрирование")
        self.comboDivision.setCurrentIndex(0)
        self.comboDivision.setEnabled(True)

        # Фильтр по отделам (зависит от выбранного подразделения)
        self.comboDepartment.clear()
        self.comboDepartment.addItem("Сначала выберите подразделение", None)
        self.comboDepartment.setEnabled(False)

    def on_division_changed(self, index):
        """Обработчик изменения выбранного подразделения"""
        division = self.comboDivision.currentData()

        if division is None:
            self.comboDepartment.setEnabled(False)
            self.comboDepartment.clear()
            self.comboDepartment.addItem("Сначала выберите подразделение", None)
            return

        # Загружаем отделы для выбранного подразделения
        self.load_departments(division)

    def load_departments(self, division: str):
        """Загружает отделы для выбранного подразделения"""
        self.comboDepartment.clear()
        self.comboDepartment.addItem("Все отделы", None)

        # Соответствие подразделений отделам
        departments_map = {
            "Разработка": ["IT", "Управление проектами"],
            "Тестирование": ["IT", "Управление проектами"],
            "Инфраструктура": ["IT", "Администрация"],
            "Аналитика": ["Управление проектами", "Финансы"],
            "Управление": ["Руководство", "Управление проектами"],
            "Дизайн": ["Маркетинг"],
            "Бухгалтерия": ["Финансы"],
            "Администрирование": ["Администрация"]
        }

        departments = departments_map.get(division, [])
        for dept in departments:
            self.comboDepartment.addItem(dept, dept)

        self.comboDepartment.setEnabled(True)
        self.comboDepartment.setCurrentIndex(0)

    def get_period(self) -> Tuple[QDate, QDate]:
        """Возвращает выбранные даты: (start_date, end_date)"""
        return self.dateStart.date(), self.dateEnd.date()

    def get_filters(self) -> dict:
        """Возвращает выбранные фильтры"""
        return {
            'division': self.comboDivision.currentData(),
            'department': self.comboDepartment.currentData() if self.comboDepartment.isEnabled() else None
        }