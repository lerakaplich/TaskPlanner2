import os

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy

from windows.analytics.projects.employee_project_card import EmployeeProjectCard
from windows.analytics.projects.task_card_analytics import TaskCard


class ProjectCard(QFrame):
    def __init__(self, project_data, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..", "..",  # поднимаемся до корня проекта
            "ui", "analytics", "projects"  # спускаемся в нужную подпапку ui
        )

        uic.loadUi(os.path.join(ui_path, "project_card_analytics.ui"), self)

        self.project_data = project_data
        self.employees_base_text = self.employees_btn.text()  # для сохранения текста без стрелки

        # Основная информация
        self.name_btn.setText(project_data["name"])
        start_str = project_data.get("start_date", "не указана")
        status = project_data.get("status", "unknown")
        status_display = {
            "to_do": "к выполнению",
            "in_progress": "в работе",
            "review": "на проверке",
            "completed": "выполнен",
            "archived": "архивирован"
        }.get(status, status)
        self.info_label.setText(f"Старт: {start_str} · Статус: {status_display}")

        # Кнопка сотрудников с общим количеством
        emp_count = len(project_data.get("employees", []))
        self.employees_btn.setText(f"▶ Сотрудники (всего: {emp_count})")
        self.employees_base_text = self.employees_btn.text()  # обновляем базовый текст

        # Заполняем панели
        self._populate_tasks()
        self._populate_employees()

        # Подключение сигналов
        self.tasks_btn.toggled.connect(self._toggle_tasks_panel)
        self.employees_btn.toggled.connect(self._toggle_employees_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _toggle_tasks_panel(self, checked):
        self.tasks_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.tasks_btn.setText(f"{arrow} Задачи")

    def _toggle_employees_panel(self, checked):
        self.employees_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        # Восстанавливаем базовый текст без стрелки
        if self.employees_base_text and self.employees_base_text[0] in ("▶", "▼"):
            base = self.employees_base_text[2:] if self.employees_base_text[1] == ' ' else self.employees_base_text[1:]
        else:
            base = self.employees_base_text
        self.employees_btn.setText(f"{arrow} {base}")

    def _populate_tasks(self):
        """Добавляет карточки задач в панель задач."""
        tasks = self.project_data.get("tasks", [])
        for task in tasks:
            card = TaskCard(task)
            self.tasks_panel.layout().addWidget(card)

    def _populate_employees(self):
        """Добавляет карточки сотрудников в панель сотрудников."""
        employees = self.project_data.get("employees", [])
        for emp in employees:
            card = EmployeeProjectCard(emp, self.project_data["id"])
            self.employees_panel.layout().addWidget(card)