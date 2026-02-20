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

        self.project_data = project_data

        # Основная информация
        self.name_btn.setText(project_data["name"])

        # Форматирование даты старта
        start_date = project_data.get("start_date", "не указана")
        if start_date != "не указана":
            try:
                date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                start_date = date_obj.strftime("%d.%m.%Y")
            except:
                pass

        # Статус проекта
        status = project_data.get("status", "unknown")
        status_display = {
            "to_do": "к выполнению",
            "in_progress": "в работе",
            "review": "на проверке",
            "completed": "выполнен",
            "archived": "архивирован"
        }.get(status, status)

        # Количество сотрудников
        emp_count = len(project_data.get("employees", []))

        self.info_label.setText(
            f"Старт: {start_date} · Статус: {status_display} · Сотрудников: {emp_count}"
        )

        # Заполняем панели
        self._populate_tasks()
        self._populate_employees()

        # Подключение сигналов
        self.tasks_btn.toggled.connect(self._toggle_tasks_panel)
        self.employees_btn.toggled.connect(self._toggle_employees_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _toggle_tasks_panel(self, checked):
        """Переключение видимости панели задач."""
        self.tasks_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.tasks_btn.setText(f"{arrow} Задачи")

    def _toggle_employees_panel(self, checked):
        """Переключение видимости панели сотрудников."""
        self.employees_panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.employees_btn.setText(f"{arrow} Сотрудники")

    def _populate_tasks(self):
        """Заполняет панель задач с группировкой по статусам."""
        # Очищаем панель задач
        layout = self.tasks_panel.layout()
        if layout is None:
            layout = QVBoxLayout(self.tasks_panel)
            self.tasks_panel.setLayout(layout)
        else:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Устанавливаем правильные отступы в layout панели задач
        layout.setSpacing(8)  # ← ВАЖНО: добавляем расстояние между элементами
        layout.setContentsMargins(5, 5, 5, 5)  # небольшие отступы по краям

        tasks = self.project_data.get("tasks", [])

        # Группировка задач по статусам
        status_order = ["to_do", "in_progress", "review", "completed", "archived"]
        status_groups = {s: [] for s in status_order}

        for task in tasks:
            status = task.get("status", "").lower()
            if status in status_groups:
                status_groups[status].append(task)
            else:
                status_groups["to_do"].append(task)

        # Проверка просрочки для незавершённых проектов
        project_status = self.project_data.get("status", "").lower()
        check_overdue = project_status in ("to_do", "in_progress", "review")

        # Создаём сворачиваемые блоки для каждого статуса
        for status_key in status_order:
            status_tasks = status_groups.get(status_key, [])
            if not status_tasks:
                continue

            # Человеческое название статуса
            status_display = TaskCard.STATUS_MAP.get(status_key, status_key.capitalize())

            # Контейнер для одного блока статуса (кнопка + панель задач)
            status_container = QFrame()
            status_container.setStyleSheet("background-color: transparent;")
            container_layout = QVBoxLayout(status_container)
            container_layout.setSpacing(4)  # отступ между кнопкой и панелью
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Кнопка статуса
            status_btn = QPushButton(f"▶ {status_display} ({len(status_tasks)})")
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

            for task in status_tasks:
                card = TaskCard(
                    task_data=task,
                    compact=True,
                    show_theme=False,
                    show_project=False,
                    check_overdue=check_overdue,
                    creator_names=TaskCard.DEFAULT_CREATOR_NAMES,
                    parent=self
                )
                tasks_layout.addWidget(card)

            container_layout.addWidget(tasks_panel)
            layout.addWidget(status_container)

            # Связываем кнопку с панелью
            def make_toggle(panel):
                return lambda checked: panel.setVisible(checked)

            status_btn.toggled.connect(make_toggle(tasks_panel))
            status_btn.toggled.connect(
                lambda checked, btn=status_btn: btn.setText(
                    ("▼" if checked else "▶") + btn.text()[1:]
                )
            )

        # Если задач нет
        if not tasks:
            no_tasks = QLabel("Нет задач в этом проекте")
            no_tasks.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tasks.setStyleSheet("color: #888888; padding: 20px; font-size: 14px;")
            layout.addWidget(no_tasks)

        # Добавляем растяжение в конце, чтобы всё прижималось к верху
        layout.addStretch()
    def _populate_employees(self):
        """Заполняет панель сотрудников."""
        employees = self.project_data.get("employees", [])
        for emp in employees:
            card = EmployeeProjectCard(emp, self.project_data.get("id", ""))
            self.employees_panel.layout().addWidget(card)