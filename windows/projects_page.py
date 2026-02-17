import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi


class ProjectsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False, projects_data=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode                # "completed" или "active"
        self.compact = compact
        self.projects_data = projects_data

        if not self.compact:
            # Полноэкранный режим — загружаем .ui файл
            ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", "projects_page.ui")
            loadUi(ui_path, self)
            self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")
        else:
            # Компактный режим — создаём layout программно (без лишних элементов UI)
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

        self.refresh_data()

    def parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    def format_date(self, date_str):
        date = self.parse_date(date_str)
        return date.strftime("%d.%m.%Y") if date else (date_str or "—")

    def calculate_kpi(self, created_str, completed_str, due_str):
        created = self.parse_date(created_str)
        completed = self.parse_date(completed_str)
        due = self.parse_date(due_str)
        if not all([created, completed, due]):
            return None
        planned = (due - created).days
        actual = (completed - created).days
        if actual <= 0:
            return float('inf')
        return planned / actual

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
        # Очистка
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Данные
        if self.projects_data is None:
            self.projects_data = self._get_default_projects()

        projects = self.projects_data

        # Фильтрация задач в зависимости от режима
        if self.mode == "completed":
            filtered_projects = []
            for project in projects:
                filtered_tasks = [
                    task for task in project["tasks"]
                    if task.get("status", "").lower() in ("completed", "archived")
                ]
                if filtered_tasks:
                    filtered_projects.append({"name": project["name"], "tasks": filtered_tasks})
            projects_to_show = filtered_projects
            no_data_text = "Нет выполненных проектов"
        else:
            # В активном режиме показываем все проекты с задачами
            projects_to_show = [p for p in projects if p.get("tasks")]
            no_data_text = "Нет активных проектов"

        if not projects_to_show:
            no_data_label = QLabel(no_data_text)
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet(
                f"font-size: {'18px' if not self.compact else '16px'}; "
                "color: #666666; margin: 50px;" if not self.compact else "margin: 20px;"
            )
            self.projects_layout.addWidget(no_data_label)
        else:
            for project in projects_to_show:
                self.add_project_section(project["name"], project["tasks"])

        self.projects_layout.addStretch()

    def add_project_section(self, project_name, tasks):
        priority_map = {'low': 'Низкий', 'medium': 'Средний', 'high': 'Высокий', 'critical': 'Критический'}
        priority_colors = {'low': '#2ecc71', 'medium': '#f1c40f', 'high': '#e67e22', 'critical': '#e74c3c'}
        status_map = {
            'to_do': 'К выполнению', 'in_progress': 'В работе', 'review': 'На проверке',
            'completed': 'Выполнено', 'archived': 'Архивировано', 'overdue': 'Просрочена'
        }
        creator_names = {1: "Иван Иванов", 2: "Анна Петрова", 3: "Алексей Сидоров"}

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

        content_frame = QFrame()
        content_frame.setVisible(False)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(
            20 if not self.compact else 10, 15 if not self.compact else 10,
            20 if not self.compact else 10, 15 if not self.compact else 10
        )
        content_layout.setSpacing(15 if not self.compact else 8)
        content_frame.setStyleSheet("background-color: transparent;")

        show_theme = self.mode == "active"
        check_overdue = self.mode == "active"

        if not tasks:
            no_tasks = QLabel("Нет задач в этом проекте")
            no_tasks.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tasks.setStyleSheet("color: #888888; padding: 30px; font-size: 16px;")
            content_layout.addWidget(no_tasks)
        else:
            for task in tasks:
                # === Карточка задачи (единая логика для обоих режимов) ===
                card = QFrame()

                # Просрочка
                overdue = False
                if check_overdue:
                    due_str = task.get("due_date")
                    status_lower = task.get("status", "").lower()
                    if due_str and status_lower not in ("completed", "archived"):
                        due_date = self.parse_date(due_str)
                        if due_date and due_date < datetime.now().date():
                            overdue = True

                # Цвет границы и фон
                if overdue:
                    bg_color = "#ffeeee"
                    border_color = "#e74c3c"
                else:
                    bg_color = "white"
                    border_color = priority_colors.get(task.get("priority", "medium"), "#cccccc")

                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_color};
                        border-radius: 8px;
                        border-left: 6px solid {border_color};
                        border: none;
                    }}
                """)

                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(15 if not self.compact else 12, 15 if not self.compact else 12,
                                               15 if not self.compact else 12, 15 if not self.compact else 12)
                card_layout.setSpacing(8 if not self.compact else 5)

                # Название
                title_label = QLabel(task.get("title", "Без названия"))
                title_label.setWordWrap(True)
                title_label.setStyleSheet(f"font-size: {'16px' if not self.compact else '14px'}; font-weight: bold; color: #1B232A;")
                card_layout.addWidget(title_label)

                # Тема (только в active)
                if show_theme:
                    theme = task.get("theme", "нет")
                    theme_label = QLabel(f"Тема: {theme}")
                    theme_label.setStyleSheet("color: #555; font-size: 12px;")
                    card_layout.addWidget(theme_label)

                # Теги
                tags = task.get("tags", [])
                tags_str = ", ".join(tags) if tags else "нет"
                tags_label = QLabel(f"Теги: {tags_str}")
                tags_label.setStyleSheet("color: #555;")
                card_layout.addWidget(tags_label)

                # Приоритет
                prio_text = priority_map.get(task.get("priority", "medium"), task.get("priority", "medium").capitalize())
                prio_color = "#e74c3c" if overdue else priority_colors.get(task.get("priority", "medium"), "#000000")
                prio_label = QLabel(f"Приоритет: {prio_text}")
                prio_label.setStyleSheet(f"color: {prio_color}; font-weight: bold;")
                card_layout.addWidget(prio_label)

                # Даты
                created_label = QLabel(f"Дата создания: {self.format_date(task.get('created_at'))}")
                card_layout.addWidget(created_label)

                due_display = self.format_date(task.get("due_date")) or "Нет"
                due_text = f"Дедлайн: {due_display}"
                if overdue:
                    due_text += " (просрочена)"
                    due_style = "color: #e74c3c; font-weight: bold;"
                else:
                    due_style = "color: #555;"
                due_label = QLabel(due_text)
                due_label.setStyleSheet(due_style)
                card_layout.addWidget(due_label)

                if task.get("completed_at"):
                    completed_label = QLabel(f"Дата выполнения: {self.format_date(task.get('completed_at'))}")
                    card_layout.addWidget(completed_label)

                # Статус
                status_text = status_map.get(task.get("status", "").lower(), task.get("status", "неизвестно").capitalize())
                status_label = QLabel(f"Статус: {status_text}")
                card_layout.addWidget(status_label)

                # Создатель
                creator_raw = task.get("creator") or task.get("creator_id")
                if creator_raw is None:
                    creator = "неизвестно"
                elif isinstance(creator_raw, int):
                    creator = creator_names.get(creator_raw, str(creator_raw))
                else:
                    creator = creator_raw
                creator_label = QLabel(f"Создатель: {creator}")
                card_layout.addWidget(creator_label)

                # КПД
                if task.get("status", "").lower() in ("completed", "archived", "выполнено"):
                    kpi = self.calculate_kpi(
                        task.get("created_at"),
                        task.get("completed_at"),
                        task.get("due_date")
                    )
                    if kpi is not None:
                        kpi_text = "∞" if kpi == float('inf') else f"{kpi:.2f}"
                        kpi_label = QLabel(f"КПД: {kpi_text}")
                        kpi_label.setStyleSheet("font-weight: bold; color: #27ae60;")
                        card_layout.addWidget(kpi_label)

                content_layout.addWidget(card)

        # Переключение видимости секции
        def toggle(checked):
            content_frame.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle)

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(content_frame)

    def set_employee_id(self, employee_id):
        self.employee_id = employee_id
        self.refresh_data()