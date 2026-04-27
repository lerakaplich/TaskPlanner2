# windows/profile/projects_page.py

import os
from datetime import datetime
from typing import List, Dict, Any, Union

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from services.profile_service import ProfileService
from models.tasks import Task


class ProjectsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False, projects_data=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode  # "active", "completed", "all"
        self.compact = compact
        self.projects_data = projects_data

        self.profile_service = ProfileService()

        if not self.compact:
            self.setMinimumSize(800, 600)
            self.resize(900, 700)

        if not self.compact:
            ui_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "ui", "profile"
            )
            ui_file = os.path.join(ui_path, "projects_page.ui")
            if os.path.exists(ui_file):
                uic.loadUi(ui_file, self)
                self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")
                if hasattr(self, 'btnClose'):
                    self.btnClose.clicked.connect(self.close)
            else:
                self.setLayout(QVBoxLayout())
                self.projects_layout = self.layout()
        else:
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

        self.refresh_data()

    def _get_tasks_from_project(self, project):
        """Извлекает задачи из проекта в зависимости от режима"""
        tasks = []

        # Если есть grouped_tasks
        if "grouped_tasks" in project:
            grouped = project["grouped_tasks"]
            if self.mode == "active":
                # Активные задачи: to_do, in_progress, review
                tasks = grouped.get("to_do", []) + grouped.get("in_progress", []) + grouped.get("review", [])
            elif self.mode == "completed":
                # Выполненные задачи: completed, archived
                tasks = grouped.get("completed", []) + grouped.get("archived", [])
            else:
                tasks = grouped.get("to_do", []) + grouped.get("in_progress", []) + \
                        grouped.get("review", []) + grouped.get("completed", []) + \
                        grouped.get("archived", [])
        # Если есть обычные задачи
        elif "tasks" in project:
            raw_tasks = project["tasks"]
            for task in raw_tasks:
                is_completed = False
                if isinstance(task, Task):
                    is_completed = task.completed or task.is_archived
                elif isinstance(task, dict):
                    is_completed = task.get("is_completed", False) or task.get("status", "").lower() in ("completed",
                                                                                                         "archived")

                if self.mode == "active" and not is_completed:
                    tasks.append(task)
                elif self.mode == "completed" and is_completed:
                    tasks.append(task)
                elif self.mode == "all":
                    tasks.append(task)

        return tasks

    def load_projects(self):
        """Загружает проекты в зависимости от режима"""
        if self.projects_data is not None:
            projects = self.projects_data
        else:
            projects = self.profile_service.get_all_employee_projects_with_tasks(
                self.employee_id
            )

        filtered_projects = []
        for project in projects:
            # Получаем имя проекта
            project_name = project.get("name", "Без названия")
            project_id = project.get("id")

            # Получаем задачи для текущего режима
            tasks = self._get_tasks_from_project(project)

            # 🔧 ИСПРАВЛЕНИЕ: Показываем проект, даже если задач 0
            # Определяем, должен ли проект отображаться в текущем режиме
            is_archived = project.get("is_archived", False)

            if self.mode == "active":
                should_show = not is_archived  # Показываем все неархивные проекты
            elif self.mode == "completed":
                should_show = is_archived  # Показываем все архивные проекты
            else:  # all
                should_show = True

            # Показываем проект, если он подходит по режиму ИЛИ в нем есть задачи
            if should_show or tasks:
                filtered_projects.append({
                    "name": project_name,
                    "tasks": tasks,
                    "id": project_id,
                    "grouped_tasks": project.get("grouped_tasks"),
                    "tasks_total": project.get("tasks_total", 0),
                    "tasks_done": project.get("tasks_done", 0),
                    "is_archived": is_archived
                })

        # Текст для пустого состояния
        texts = {
            "active": "Нет активных проектов",
            "completed": "Нет выполненных проектов",
            "all": "Нет проектов"
        }

        print(f"   ProjectsPage ({self.mode}): загружено {len(filtered_projects)} проектов")
        for p in filtered_projects:
            print(f"      - {p['name']} (задач: {len(p['tasks'])}, всего: {p.get('tasks_total', 0)})")

        return filtered_projects, texts.get(self.mode, "Нет проектов")

    # windows/profile/projects_page.py

    def update_data(self, projects_data=None, employee_id=None):
        """Обновляет данные и перерисовывает UI"""
        if projects_data is not None:
            self.projects_data = projects_data
        if employee_id is not None:
            self.employee_id = employee_id
        self.refresh_data()

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
                    project["tasks"],
                    project.get("grouped_tasks")
                )

        self.projects_layout.addStretch()

    def _task_to_dict(self, task) -> Dict:
        """Преобразует задачу в словарь для UI"""
        if isinstance(task, dict):
            return task
        elif isinstance(task, Task):
            status = "to_do"
            is_completed = False
            if task.column:
                column_name = task.column.name.lower()
                if task.column.is_done_column:
                    status = "completed"
                    is_completed = True
                elif "проверк" in column_name:
                    status = "review"
                elif "работ" in column_name:
                    status = "in_progress"
                else:
                    status = "to_do"

            return {
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                "status": status,
                "is_overdue": task.deadline and task.deadline.date() < datetime.now().date() and not is_completed,
                "is_completed": is_completed,
                "created_at_str": task.created_at.strftime("%d.%m.%Y") if task.created_at else "",
                "due_date_str": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
                "completed_at_str": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "",
                "creator_name": "Неизвестен",
                "tags_list": [],
                "project_name": ""
            }
        return {}

    # windows/profile/projects_page.py

    def add_project_section(self, project_name, tasks, grouped_tasks=None):
        """Добавляет секцию проекта с задачами"""
        from windows.analytics.task_card_analytics import TaskCard

        # 🔧 Убираем ранний return, даже если задач нет
        # if not tasks:  # <-- УДАЛИТЬ ЭТУ СТРОКУ
        #     return     # <-- УДАЛИТЬ ЭТУ СТРОКУ

        # Стиль заголовка проекта (без изменений)
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

        # 🔧 Добавляем обработку для пустых проектов
        if not tasks:
            # Показываем сообщение "Нет задач"
            empty_label = QLabel("📭 Нет задач в этом проекте")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; padding: 20px; font-style: italic; font-size: 13px;")
            panel_layout.addWidget(empty_label)
        else:
            # Группируем задачи по статусам (код без изменений)
            status_groups = {
                "to_do": [],
                "in_progress": [],
                "review": [],
                "completed": [],
                "archived": []
            }

            for task in tasks:
                if isinstance(task, dict):
                    status = task.get("status", "to_do").lower()
                else:
                    status = "to_do"
                if status in status_groups:
                    status_groups[status].append(task)
                else:
                    status_groups["to_do"].append(task)

            # Создаём блоки для каждого статуса с задачами
            status_order = ["to_do", "in_progress", "review", "completed", "archived"]
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
                    task_dict = self._task_to_dict(task)
                    card = TaskCard(
                        task_data=task_dict,
                        compact=self.compact,
                        show_theme=False,
                        show_project=False
                    )
                    tasks_layout.addWidget(card)

                panel_layout.addWidget(tasks_panel)

                # Связываем кнопку статуса с панелью
                def make_toggle(panel, btn):
                    return lambda checked: self._toggle_status_panel(checked, panel, btn)

                status_btn.toggled.connect(make_toggle(tasks_panel, status_btn))

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        # Переключение видимости панели проекта
        def toggle_project_panel(checked):
            project_panel.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle_project_panel)

    def _toggle_status_panel(self, checked, panel, button):
        """Переключает видимость панели статуса"""
        panel.setVisible(checked)
        arrow = "▼" if checked else "▶"
        button.setText(arrow + button.text()[1:])

    def set_employee_id(self, employee_id):
        """Устанавливает ID сотрудника и обновляет данные"""
        self.employee_id = employee_id
        self.projects_data = None
        self.refresh_data()