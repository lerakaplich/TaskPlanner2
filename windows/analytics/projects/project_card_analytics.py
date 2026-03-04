import os
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from windows.analytics.projects.employee_project_card import EmployeeProjectCard
from windows.analytics.task_card_analytics import TaskCard


class ProjectCard(QFrame):
    def __init__(self, project_data, parent=None):
        super().__init__(parent)

        # Определяем путь к UI-файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_card_analytics.ui"), self)

        self.data = project_data

        # Основная информация - берем готовые строки из DTO
        self.name_btn.setText(self.data.get("name", "Без названия"))
        self.info_label.setText(
            f"Старт: {self.data.get('start_date_str', '—')} · "
            f"Статус: {self.data.get('status_display', '—')} · "
            f"Сотрудников: {self.data.get('emp_count', 0)}"
        )

        self._populate_tasks()
        self._populate_employees()

        # Сигналы
        self.tasks_btn.toggled.connect(self._toggle_tasks_panel)
        self.employees_btn.toggled.connect(self._toggle_employees_panel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _toggle_tasks_panel(self, checked):
        self.tasks_panel.setVisible(checked)
        self.tasks_btn.setText(f"{'▼' if checked else '▶'} Задачи")

    def _toggle_employees_panel(self, checked):
        self.employees_panel.setVisible(checked)
        self.employees_btn.setText(f"{'▼' if checked else '▶'} Сотрудники")

    def _populate_tasks(self):
        """Заполняет панель задач с группировкой по статусам."""
        layout = self.tasks_panel.layout() or QVBoxLayout(self.tasks_panel)
        # Очистка layout (стандартный цикл while layout.count()...)
        self._clear_layout(layout)

        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        grouped_tasks = self.data.get("grouped_tasks", {})

        # Человеческие названия из TaskCard
        display_names = TaskCard.STATUS_MAP

        # Создаём сворачиваемые блоки для каждого статуса
        for status_key, tasks in grouped_tasks.items():
            if not tasks: continue

            # Создаем контейнер статуса
            status_container = QFrame()
            container_layout = QVBoxLayout(status_container)
            container_layout.setSpacing(4)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Кнопка статуса
            status_btn = QPushButton(f"▶ {display_names.get(status_key, status_key)} ({len(tasks)})")
            status_btn.setCheckable(True)
            status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1B232A;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #D9D9D6;
                    color: black;
                }
                QPushButton:pressed {
                    background-color: #B8B8B5;
                }
            """)
            container_layout.addWidget(status_btn)

            # Панель задач для данного статуса
            tasks_panel = QFrame()
            tasks_panel.setVisible(False)
            tasks_panel.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 4px;
                    margin-top: 2px;
                }
            """)
            tasks_layout = QVBoxLayout(tasks_panel)
            tasks_layout.setContentsMargins(8, 8, 8, 8)
            tasks_layout.setSpacing(6)  # отступы между карточками задач

            for task_dto in tasks:
                # TaskCard уже готов принимать DTO и не парсить даты!
                card = TaskCard(task_data=task_dto, compact=True)
                tasks_layout.addWidget(card)

            container_layout.addWidget(tasks_panel)
            layout.addWidget(status_container)

            # Связываем кнопку с панелью
            status_btn.toggled.connect(
                lambda ch, p=tasks_panel, b=status_btn: self._update_status_btn(ch, p, b)
            )

        if not any(grouped_tasks.values()):
            layout.addWidget(QLabel("Нет задач в этом проекте"))
        layout.addStretch()

    def _update_status_btn(self, checked, panel, button):
        panel.setVisible(checked)
        button.setText(f"{'▼' if checked else '▶'}{button.text()[1:]}")

    def _populate_employees(self):
        """Заполняет панель сотрудников."""
        layout = self.employees_panel.layout()
        self._clear_layout(layout)

        for emp in self.data.get("employees", []):
            # Передаем id проекта для контекста, если нужно
            card = EmployeeProjectCard(emp, self.data.get("id", ""))
            layout.addWidget(card)

    def _clear_layout(self, layout):
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()