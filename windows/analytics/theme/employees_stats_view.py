# windows/analytics/theme/employees_stats_view.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt


class EmployeesStatsView(QWidget):
    """Виджет для отображения статистики сотрудников по теме - только UI"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._search_callback = None
        self._display_data = []

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

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

    def set_search_callback(self, callback):
        """Устанавливает callback для поиска"""
        self._search_callback = callback

    def _on_search(self, text):
        """Обработчик поиска"""
        if self._search_callback:
            self._search_callback(text)

    def display_data(self, employees_data: list):
        """
        Отображает данные сотрудников.
        employees_data - список словарей с ключами:
        - employee_name, avg_kpi, completed_count, low, medium, high, critical
        """
        self._display_data = employees_data
        self._refresh_table()

    def _refresh_table(self):
        """Обновляет таблицу с данными"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        if not self._display_data:
            self._show_no_data_message()
            self.table.setSortingEnabled(True)
            return

        row = 0
        for stat in self._display_data:
            if not isinstance(stat, dict):
                continue

            self.table.insertRow(row)

            # Сотрудник
            self.table.setItem(row, 0, QTableWidgetItem(stat.get("employee_name", "Неизвестно")))

            # КПД
            kpi_value = stat.get('avg_kpi', 0)
            kpi_text = f"{kpi_value:.1f}%" if isinstance(kpi_value, (int, float)) else str(kpi_value)
            self.table.setItem(row, 1, QTableWidgetItem(kpi_text))

            # Выполнено
            self.table.setItem(row, 2, QTableWidgetItem(str(stat.get("completed_count", 0))))

            # Приоритеты
            self.table.setItem(row, 3, QTableWidgetItem(str(stat.get("low", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(stat.get("medium", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(stat.get("high", 0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(stat.get("critical", 0))))

            row += 1

        self.table.setSortingEnabled(True)

    def _show_no_data_message(self):
        """Показывает сообщение об отсутствии данных"""
        self.table.setRowCount(1)
        self.table.setSpan(0, 0, 1, 7)
        no_data_item = QTableWidgetItem("Нет данных по сотрудникам")
        no_data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 0, no_data_item)