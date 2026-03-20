from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

class EmployeesStatsView(QWidget):
    def __init__(self, theme_name, tasks, stats_data, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.all_stats = stats_data  # Готовый список от сервиса

        self._init_ui()
        self.refresh_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по сотруднику...")
        self.search_edit.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_edit)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Сотрудник", "Ср. КПД", "Выполнено",
            "Low", "Medium", "High", "Critical"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh_table(self, filter_text=""):
        # 1. Отключаем сортировку перед очисткой и заполнением
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row, stat in enumerate(self.all_stats):
            if filter_text.lower() not in stat["employee"].lower():
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(stat["employee"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(stat['avg_kpi'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(stat["completed"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(stat["low"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(stat["medium"])))
            self.table.setItem(row, 5, QTableWidgetItem(str(stat["high"])))
            self.table.setItem(row, 6, QTableWidgetItem(str(stat["critical"])))
        # 2. Включаем сортировку обратно
        self.table.setSortingEnabled(True)

    def filter_table(self, text):
        self.refresh_table(text)