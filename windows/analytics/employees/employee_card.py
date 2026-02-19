from PyQt6 import uic
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
            f"{emp_data['position']} · {emp_data['department']} · {emp_data['subdivision']}"
        )
        # Активные проекты
        self.active_projects_view = ProjectsPage(
            employee_id=emp_data["id"],
            parent=self.projects_panel,
            mode="active",
            compact=True,
            projects_data=emp_data.get("projects", [])
        )
        self.projects_panel.layout().addWidget(self.active_projects_view)
        # Выполненные проекты
        self.completed_projects_view = ProjectsPage(
            employee_id=emp_data["id"],
            parent=self.completed_projects_panel,
            mode="completed",
            compact=True,
            projects_data=emp_data.get("projects", [])
        )
        self.completed_projects_panel.layout().addWidget(self.completed_projects_view)
        # Аналитика по темам (тестовые данные)
        analytics_data = [
            {"tag": "UI", "kpd": 2.5, "count": 2},
            {"tag": "срочно", "kpd": 1.8, "count": 3},
            {"tag": "backend", "kpd": 3.0, "count": 1},
            {"tag": "design", "kpd": 2.0, "count": 4},
        ]
        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(3)
        self.analytics_table.setHorizontalHeaderLabels(["Тема (тег)", "КПД", "Количество выполненных задач"])
        self.analytics_table.setRowCount(len(analytics_data))
        for i, data in enumerate(analytics_data):
            self.analytics_table.setItem(i, 0, QTableWidgetItem(data["tag"]))
            self.analytics_table.setItem(i, 1, QTableWidgetItem(f"{data['kpd']:.1f}"))
            self.analytics_table.setItem(i, 2, QTableWidgetItem(str(data["count"])))
        self.analytics_table.horizontalHeader().setStretchLastSection(True)
        self.analytics_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.analytics_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.analytics_panel.layout().addWidget(self.analytics_table)
        # Подключение сигналов
        self.projects_btn.toggled.connect(self.toggle_projects_panel)
        self.completed_projects_btn.toggled.connect(self.toggle_completed_projects_panel)
        self.analytics_btn.toggled.connect(self.toggle_analytics_panel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    def toggle_projects_panel(self, checked):
        self.projects_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.projects_btn.setText(f"{arrow} Активные проекты")
    def toggle_completed_projects_panel(self, checked):
        self.completed_projects_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.completed_projects_btn.setText(f"{arrow} Выполненные проекты")
    def toggle_analytics_panel(self, checked):
        self.analytics_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.analytics_btn.setText(f"{arrow} Аналитика по темам")