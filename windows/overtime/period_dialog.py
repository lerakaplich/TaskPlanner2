# windows/overtime/period_dialog.py

import os
from typing import Tuple, Optional
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QDate
from PyQt6 import uic


class PeriodDialog(QDialog):
    """Диалог выбора периода экспорта с фильтрами"""

    def __init__(self, parent=None, employee_service=None):
        super().__init__(parent)

        self.employee_service = employee_service

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "period_dialog.ui"), self)

        self.setWindowTitle("Выбор периода экспорта")

        today = QDate.currentDate()
        self.dateStart.setDate(today.addMonths(-1))
        self.dateEnd.setDate(today)

        self.init_filters()

        self.btnOk.clicked.connect(self.accept)
        self.comboDivision.currentIndexChanged.connect(self.on_division_changed)

    def init_filters(self):
        self.divisions_data = []
        if self.employee_service:
            self.divisions_data = self.employee_service.get_all_divisions()

        self.comboDivision.clear()
        self.comboDivision.addItem("Все подразделения", None)

        for div in self.divisions_data:
            self.comboDivision.addItem(div.get('name', 'Без названия'), div.get('id'))

        self.comboDivision.setCurrentIndex(0)

        self.comboDepartment.clear()
        self.comboDepartment.addItem("Все отделы", None)
        self.comboDepartment.setEnabled(False)

    def on_division_changed(self, index):
        division_id = self.comboDivision.currentData()
        if division_id is None:
            self.comboDepartment.setEnabled(False)
            self.comboDepartment.clear()
            self.comboDepartment.addItem("Все отделы", None)
            return

        self._load_departments(division_id)

    def _load_departments(self, division_id: int):
        self.comboDepartment.clear()
        self.comboDepartment.addItem("Все отделы", None)

        if self.employee_service:
            all_departments = self.employee_service.get_all_departments()
            filtered = [d for d in all_departments if d.get('division_id') == division_id]
            for dept in filtered:
                self.comboDepartment.addItem(dept.get('name', 'Без названия'), dept.get('id'))

        self.comboDepartment.setEnabled(True)
        self.comboDepartment.setCurrentIndex(0)

    def get_period(self) -> Tuple[QDate, QDate]:
        return self.dateStart.date(), self.dateEnd.date()

    def get_filters(self) -> dict:
        division_id = self.comboDivision.currentData()
        department_id = self.comboDepartment.currentData() if self.comboDepartment.isEnabled() else None

        division_name = None
        department_name = None

        if division_id:
            for div in self.divisions_data:
                if div.get('id') == division_id:
                    division_name = div.get('name')
                    break

        if department_id and self.employee_service:
            departments = self.employee_service.get_all_departments()
            for dept in departments:
                if dept.get('id') == department_id:
                    department_name = dept.get('name')
                    break

        return {
            'division_id': division_id,
            'division': division_name,
            'department_id': department_id,
            'department': department_name
        }