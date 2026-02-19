import os
from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy

from windows.analytics.theme.employees_stats_view import EmployeesStatsView
from windows.analytics.theme.theme_projects_view import ThemeProjectsView

class ThemeCard(QFrame):
    def __init__(self, theme_name, tasks, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..", "..",  # поднимаемся до корня проекта
            "ui", "analytics", "theme"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "theme_card.ui"), self)

        self.theme_name = theme_name
        self.tasks = tasks  # список задач, содержащих этот тег

        # Основные данные
        self.name_btn.setText(theme_name)
        self.count_label.setText(f"Задач: {len(tasks)}")

        # Панель сотрудников
        self.employees_stats = EmployeesStatsView(theme_name, tasks, self)
        self.employees_panel.layout().addWidget(self.employees_stats)

        # Панель проектов
        self.projects_view = ThemeProjectsView(theme_name, tasks, self)
        self.projects_panel.layout().addWidget(self.projects_view)

        # Подключение сигналов
        self.employees_btn.toggled.connect(self.toggle_employees_panel)
        self.projects_btn.toggled.connect(self.toggle_projects_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def toggle_employees_panel(self, checked):
        self.employees_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.employees_btn.setText(f"{arrow} Сотрудники")

    def toggle_projects_panel(self, checked):
        self.projects_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.projects_btn.setText(f"{arrow} Проекты")