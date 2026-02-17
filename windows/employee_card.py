import os
from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

from windows.projects_page import ProjectsPage


class EmployeeCard(QFrame):
    def __init__(self, emp_data, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")
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

        # Аналитика по темам
        self.setup_analytics()
        self.analytics_btn.toggled.connect(self.toggle_analytics_panel)

        # Подключение сигналов (проекты)
        self.projects_btn.toggled.connect(self.toggle_projects_panel)
        self.completed_projects_btn.toggled.connect(self.toggle_completed_projects_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def setup_analytics(self):
        """Создание таблицы аналитики и заполнение данными"""
        # Создаём таблицу
        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(3)
        self.analytics_table.setHorizontalHeaderLabels(["Тема (тег)", "КПД", "Количество задач"])

        # Настройка растягивания колонок по ширине
        header = self.analytics_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # тема растягивается
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # КПД по содержимому
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # количество по содержимому

        # Запрет редактирования
        self.analytics_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Заполнение тестовыми данными (заменить на реальные из emp_data если есть)
        sample_data = [
            ("Разработка", "95%", "12"),
            ("Тестирование", "88%", "8"),
            ("Документация", "100%", "5"),
            ("Митинги", "70%", "10"),
        ]
        self.analytics_table.setRowCount(len(sample_data))
        for row, (topic, efficiency, tasks) in enumerate(sample_data):
            self.analytics_table.setItem(row, 0, QTableWidgetItem(topic))
            self.analytics_table.setItem(row, 1, QTableWidgetItem(efficiency))
            self.analytics_table.setItem(row, 2, QTableWidgetItem(tasks))

        # Добавляем таблицу в панель аналитики
        self.analytics_panel.layout().addWidget(self.analytics_table)

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