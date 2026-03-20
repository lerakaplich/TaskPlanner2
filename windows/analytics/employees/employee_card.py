from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QSizePolicy, QTableWidget, QTableWidgetItem
from windows.profile.projects_page import ProjectsPage

class EmployeeCard(QFrame):
    def __init__(self, emp_data, parent=None):
        super().__init__(parent)
        import os

        # Определяем путь к папке с UI-файлом
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..", "..",  # поднимаемся до корня проекта
            "ui", "analytics", "employees"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "employee_card.ui"), self)
        self.emp_data = emp_data

        # Основные данные
        self.name_btn.setText(emp_data["name"])
        self.info_label.setText(
            f"{emp_data.get('position', '—')} · "
            f"{emp_data.get('department', '—')} · "
            f"{emp_data.get('subdivision', '—')}"
        )

        # Активные проекты
        self.active_projects_view = ProjectsPage(
            employee_id=emp_data["id"],
            parent=self.projects_panel,
            mode="active",
            compact=True,
            projects_data=emp_data.get("active_projects", [])
        )
        self.projects_panel.layout().addWidget(self.active_projects_view)

        # Выполненные проекты
        self.completed_projects_view = ProjectsPage(
            employee_id=emp_data["id"],
            parent=self.completed_projects_panel,
            mode="completed",
            compact=True,
            projects_data=emp_data.get("completed_projects", [])
        )
        self.completed_projects_panel.layout().addWidget(self.completed_projects_view)

        # 4. Аналитика по темам (берем данные из сервиса, а не хардкодим)
        self._setup_analytics_table(emp_data.get("tag_analytics", []))

        # Подключение сигналов
        self.projects_btn.toggled.connect(self.toggle_projects_panel)
        self.completed_projects_btn.toggled.connect(self.toggle_completed_projects_panel)
        self.analytics_btn.toggled.connect(self.toggle_analytics_panel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _setup_analytics_table(self, data_list):
        """Метод только для отрисовки таблицы."""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Тема (тег)", "КПД", "Выполнено задач"])
        table.setRowCount(len(data_list))

        for i, row_data in enumerate(data_list):
            table.setItem(i, 0, QTableWidgetItem(row_data["tag"]))
            # Вставляем как числа для правильной сортировки
            kpi_item = QTableWidgetItem()
            kpi_item.setData(Qt.ItemDataRole.DisplayRole, row_data["kpd"])
            table.setItem(i, 1, kpi_item)

            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.DisplayRole, row_data["count"])
            table.setItem(i, 2, count_item)

        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.analytics_panel.layout().addWidget(table)


    def toggle_projects_panel(self, checked):
        self.projects_panel.setVisible(checked)
        self.projects_btn.setText(f"{'▼' if checked else '▶'} Активные проекты")

    def toggle_completed_projects_panel(self, checked):
        self.completed_projects_panel.setVisible(checked)
        self.completed_projects_btn.setText(f"{'▼' if checked else '▶'} Выполненные проекты")

    def toggle_analytics_panel(self, checked):
        self.analytics_panel.setVisible(checked)
        self.analytics_btn.setText(f"{'▼' if checked else '▶'} Аналитика по темам")