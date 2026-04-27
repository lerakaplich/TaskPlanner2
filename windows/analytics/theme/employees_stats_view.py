# windows/analytics/theme/employees_stats_view.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt


class EmployeesStatsView(QWidget):
    def __init__(self, theme_name, stats_data, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.all_stats = stats_data if isinstance(stats_data, list) else []

        self._init_ui()
        self.refresh_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Поиск по сотруднику...")
        self.search_edit.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_edit)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Сотрудник", "Ср. КПД", "Выполнено",
            "Low", "Medium", "High", "Critical"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh_table(self, filter_text=""):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        if not self.all_stats:
            self.table.setSortingEnabled(True)
            return

        row = 0
        for stat in self.all_stats:
            if not isinstance(stat, dict):
                continue

            employee_name = stat.get("employee_name", stat.get("employee", "Неизвестно"))

            if filter_text.lower() not in employee_name.lower():
                continue

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(employee_name))
            self.table.setItem(row, 1, QTableWidgetItem(str(stat.get('avg_kpi', 0))))
            self.table.setItem(row, 2, QTableWidgetItem(str(stat.get("completed_count", 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(stat.get("low", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(stat.get("medium", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(stat.get("high", 0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(stat.get("critical", 0))))
            row += 1

        self.table.setSortingEnabled(True)

    def filter_table(self, text):
        self.refresh_table(text)