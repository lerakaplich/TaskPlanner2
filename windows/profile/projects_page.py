import os

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal


class ProjectsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False, projects_data=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode
        self.compact = compact
        self.projects_data = projects_data

        if not self.compact:
            ui_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "ui", "profile"
            )
            uic.loadUi(os.path.join(ui_path, "projects_page.ui"), self)
            self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")

            # Скрываем заголовок для компактного режима
            if hasattr(self, 'page_title'):
                self.page_title.setVisible(False)
        else:
            # Компактный режим - создаем layout вручную
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

        self.refresh_data()

    def _get_default_projects(self):
        # Тестовые данные для режима "completed" (как было раньше)
        return [
            {
                "name": "Task Planner",
                "tasks": [
                    {
                        "title": "Сверстать экран задач",
                        "priority": "high",
                        "due_date": "10.02.2026",
                        "created_at": "20.01.2026",
                        "completed_at": "08.02.2026",
                        "status": "completed",
                        "tags": ["UI", "срочно"],
                        "creator": "Иван Иванов"
                    },
                    {
                        "title": "Реализовать профиль сотрудника",
                        "priority": "medium",
                        "due_date": "01.02.2026",
                        "created_at": "10.01.2026",
                        "completed_at": None,
                        "status": "in_progress",
                        "tags": ["backend"],
                        "creator": "Иван Иванов"
                    }
                ]
            },
            {
                "name": "Модернизация системы учета 2024",
                "tasks": [
                    {
                        "title": "Перенос данных в новую БД",
                        "priority": "critical",
                        "due_date": None,
                        "created_at": "15.11.2024",
                        "completed_at": "20.11.2024",
                        "status": "archived",
                        "tags": ["база данных"],
                        "creator": "Анна Петрова"
                    }
                ]
            }
        ]

    def refresh_data(self):
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.projects_data is None:
            self.projects_data = self._get_default_projects()

        projects = self.projects_data

        if self.mode == "completed":
            filtered_projects = []
            for project in projects:
                filtered_tasks = [
                    t for t in project["tasks"]
                    if t.get("status", "").lower() in ("completed", "archived")
                ]
                if filtered_tasks:
                    filtered_projects.append({"name": project["name"], "tasks": filtered_tasks})
            projects_to_show = filtered_projects
            no_data_text = "Нет выполненных проектов"
        else:
            projects_to_show = [p for p in projects if p.get("tasks")]
            no_data_text = "Нет активных проектов"

        if not projects_to_show:
            no_data_label = QLabel(no_data_text)
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if self.compact:
                no_data_label.setStyleSheet("font-size: 16px; color: #666666; margin: 20px;")
            else:
                no_data_label.setStyleSheet("font-size: 18px; color: #666666; margin: 50px;")

            self.projects_layout.addWidget(no_data_label)
        else:
            for project in projects_to_show:
                self.add_project_section(project["name"], project["tasks"])

        self.projects_layout.addStretch()

    def add_project_section(self, project_name, tasks):
        # Стиль заголовка проекта (как было ранее)
        if self.compact:
            header_style = """
                QPushButton { 
                    background-color: #D22730; 
                    color: white; 
                    border-radius: 6px;
                    font-weight: bold; 
                    font-size: 14px; 
                    border: none; 
                    text-align: left;
                    padding: 8px 12px; 
                }
                QPushButton:hover { 
                    background-color: #862633; 
                }
                QPushButton:pressed { 
                    background-color: #6a1e29; 
                }
            """
        else:
            header_style = """
                QPushButton { 
                    background-color: #D22730; 
                    color: white; 
                    border-radius: 10px;
                    font-weight: bold; 
                    font-size: 18px; 
                    border: none; 
                    text-align: left;
                    padding: 15px 15px; 
                }
                QPushButton:hover { 
                    background-color: #862633; 
                }
                QPushButton:pressed { 
                    background-color: #6a1e29; 
                }
            """

        header_btn = QPushButton(project_name + " ►")
        header_btn.setCheckable(True)
        header_btn.setChecked(False)
        header_btn.setStyleSheet(header_style)

        # Панель проекта (скрыта по умолчанию)
        project_panel = QFrame()
        project_panel.setVisible(False)
        project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
        panel_layout = QVBoxLayout(project_panel)

        if self.compact:
            panel_layout.setContentsMargins(10, 10, 10, 10)
        else:
            panel_layout.setContentsMargins(20, 10, 10, 10)

        panel_layout.setSpacing(8)

        # Импортируем TaskCard, если ещё не импортирован в начале файла
        from windows.analytics.task_card_analytics import TaskCard

        # Статусы для группировки (в порядке отображения)
        status_order = ["to_do", "in_progress", "review", "completed", "archived"]
        status_groups = {s: [] for s in status_order}

        for task in tasks:
            status = task.get("status", "").lower()
            if status in status_groups:
                status_groups[status].append(task)
            else:
                # Неизвестный статус кладём в "to_do"
                status_groups["to_do"].append(task)

        # Определяем параметры для карточек
        check_overdue = (self.mode == "active")  # проверять просрочку только в активном режиме
        show_theme = (self.mode == "active")  # тему показывать только в активном
        creator_names = TaskCard.DEFAULT_CREATOR_NAMES  # можно переопределить при необходимости

        # Создаём сворачиваемые блоки для каждого статуса
        for status_key in status_order:
            status_tasks = status_groups.get(status_key, [])
            if not status_tasks:
                continue

            # Человеческое название статуса
            status_display = TaskCard.STATUS_MAP.get(status_key, status_key.capitalize())

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
                    margin-left: 5px;
                }
                QPushButton:hover {
                    background-color: #D9D9D6;
                    color: black;
                }
                QPushButton:pressed {
                    background-color: #B8B8B5;
                }
            """)
            panel_layout.addWidget(status_btn)

            # Панель задач статуса
            tasks_panel = QFrame()
            tasks_panel.setVisible(False)
            tasks_panel.setStyleSheet("background-color: white; border-radius: 4px;")
            tasks_layout = QVBoxLayout(tasks_panel)
            tasks_layout.setContentsMargins(8, 8, 8, 8)
            tasks_layout.setSpacing(6)

            for task in status_tasks:
                card = TaskCard(
                    task_data=task,
                    compact=self.compact,
                    show_theme=show_theme,
                    show_project=False,  # не показываем проект, т.к. уже в контексте
                    check_overdue=check_overdue,
                    creator_names=creator_names
                )
                tasks_layout.addWidget(card)

            panel_layout.addWidget(tasks_panel)

            # Связываем кнопку статуса с панелью
            def make_toggle(panel):
                return lambda checked: panel.setVisible(checked)

            status_btn.toggled.connect(make_toggle(tasks_panel))
            status_btn.toggled.connect(lambda checked, btn=status_btn:
                                       btn.setText(("▼" if checked else "▶") + btn.text()[1:]))

        # Если задач в проекте нет
        if not tasks:
            no_tasks = QLabel("Нет задач в этом проекте")
            no_tasks.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if self.compact:
                no_tasks.setStyleSheet("color: #888888; padding: 20px; font-size: 14px;")
            else:
                no_tasks.setStyleSheet("color: #888888; padding: 30px; font-size: 16px;")

            panel_layout.addWidget(no_tasks)

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        # Переключение видимости панели проекта
        def toggle_project_panel(checked):
            project_panel.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle_project_panel)

    def set_employee_id(self, employee_id):
        self.employee_id = employee_id
        self.refresh_data()