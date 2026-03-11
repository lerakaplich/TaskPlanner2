# windows/profile/projects_page.py

import os

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from services.profile_service import ProfileService


class ProjectsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False, projects_data=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode  # "active", "completed", "all"
        self.compact = compact
        self.projects_data = projects_data

        self.profile_service = ProfileService()

        # Настройки окна
        self.setWindowTitle("Проекты сотрудника")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        if not self.compact:
            ui_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "ui", "profile"
            )
            uic.loadUi(os.path.join(ui_path, "projects_page.ui"), self)
            self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")

            # Добавляем кнопку закрытия, если её нет в UI
            if hasattr(self, 'btnClose'):
                self.btnClose.clicked.connect(self.close)
        else:
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

        self.refresh_data()

    # ---------- DATA ----------

    def load_projects(self):
        """Загружает проекты в зависимости от режима"""
        if self.projects_data is not None:
            projects = self.projects_data
        else:
            projects = self.profile_service.get_all_employee_projects_with_tasks(
                self.employee_id
            )

        # Фильтруем по режиму
        if self.mode == "completed":
            filtered_projects = []
            for project in projects:
                completed_tasks = [
                    t for t in project["tasks"]
                    if t.get("status", "").lower() in ("completed", "archived")
                ]
                if completed_tasks:
                    filtered_projects.append({
                        "name": project["name"],
                        "tasks": completed_tasks,
                        "id": project.get("id")
                    })
            return filtered_projects, "Нет выполненных проектов"

        elif self.mode == "active":
            filtered_projects = []
            for project in projects:
                active_tasks = [
                    t for t in project["tasks"]
                    if t.get("status", "").lower() not in ("completed", "archived")
                ]
                if active_tasks:
                    filtered_projects.append({
                        "name": project["name"],
                        "tasks": active_tasks,
                        "id": project.get("id")
                    })
            return filtered_projects, "Нет активных проектов"

        else:  # mode == "all"
            # Показываем все проекты со всеми задачами
            all_projects = []
            for project in projects:
                if project["tasks"]:  # Только проекты с задачами
                    all_projects.append({
                        "name": project["name"],
                        "tasks": project["tasks"],
                        "id": project.get("id")
                    })
            return all_projects, "Нет проектов"

    # ---------- UI ----------

    def refresh_data(self):
        """Обновляет отображение проектов"""
        # Очищаем layout
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Загружаем проекты
        projects, no_data_text = self.load_projects()

        if not projects:
            label = QLabel(no_data_text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666666; margin: 50px;")
            self.projects_layout.addWidget(label)
        else:
            for project in projects:
                self.add_project_section(
                    project["name"],
                    project["tasks"]
                )

        self.projects_layout.addStretch()

    # ---------- PROJECT ----------

    def add_project_section(self, project_name, tasks):
        """Добавляет секцию проекта с задачами"""
        from windows.analytics.task_card_analytics import TaskCard

        # Стиль заголовка проекта
        if self.compact:
            header_style = """
                QPushButton { background-color: #D22730; color: white; border-radius: 6px;
                              font-weight: bold; font-size: 14px; border: none; text-align: left;
                              padding: 8px 12px; }
                QPushButton:hover { background-color: #862633; }
                QPushButton:pressed { background-color: #6a1e29; }
            """
        else:
            header_style = """
                QPushButton { background-color: #D22730; color: white; border-radius: 10px;
                              font-weight: bold; font-size: 18px; border: none; text-align: left;
                              padding: 15px 15px; }
                QPushButton:hover { background-color: #862633; }
                QPushButton:pressed { background-color: #6a1e29; }
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
        panel_layout.setContentsMargins(10 if self.compact else 20, 10, 10, 10)
        panel_layout.setSpacing(8)

        # Статусы для группировки
        status_order = ["to_do", "in_progress", "review", "completed", "archived"]
        status_groups = {s: [] for s in status_order}

        for task in tasks:
            status = task.get("status", "").lower()
            if status in status_groups:
                status_groups[status].append(task)
            else:
                status_groups["to_do"].append(task)

        # Параметры для карточек
        check_overdue = (self.mode == "active")
        show_theme = (self.mode == "active")
        creator_names = TaskCard.DEFAULT_CREATOR_NAMES

        # Создаём блоки для каждого статуса
        for status_key in status_order:
            status_tasks = status_groups.get(status_key, [])
            if not status_tasks:
                continue

            status_display = TaskCard.STATUS_MAP.get(status_key, status_key.capitalize())

            # Кнопка статуса
            status_btn = QPushButton(f"▶ {status_display} ({len(status_tasks)})")
            status_btn.setCheckable(True)

            if self.compact:
                font_size = "14px"
                padding = "8px 12px"
            else:
                font_size = "15px"
                padding = "10px 15px"

            status_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1B232A;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: {padding};
                    font-size: {font_size};
                    font-weight: bold;
                    text-align: left;
                    margin-left: 5px;
                }}
                QPushButton:hover {{
                    background-color: #D9D9D6;
                    color: black;
                }}
                QPushButton:pressed {{
                    background-color: #B8B8B5;
                }}
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
                    show_project=False,
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
                no_tasks.setStyleSheet("color: #888888; padding: 30px; font-size: 15px;")
            else:
                no_tasks.setStyleSheet("color: #888888; padding: 30px; font-size: 18px;")

            panel_layout.addWidget(no_tasks)

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        # Переключение видимости панели проекта
        def toggle_project_panel(checked):
            project_panel.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle_project_panel)

    # ---------- API ----------

    def set_employee_id(self, employee_id):
        """Устанавливает ID сотрудника и обновляет данные"""
        self.employee_id = employee_id
        self.projects_data = None
        self.refresh_data()