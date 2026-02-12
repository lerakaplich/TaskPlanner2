import os
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi


class CompletedProjectsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None):
        super().__init__(parent)

        # Правильный путь к .ui файлу
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", "completed_projects_page.ui")
        loadUi(ui_path, self)

        self.employee_id = employee_id


        # Layout для проектов
        self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")

        self.refresh_data()

    def set_employee_id(self, employee_id):
        self.employee_id = employee_id
        self.refresh_data()

    def refresh_data(self):
        # Очистка
        while self.projects_layout.count():
            child = self.projects_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # === ТЕСТОВЫЕ ДАННЫЕ ===
        completed_projects = [
            {
                "name": "Task Planner",
                "tasks": [
                    {
                        "title": "Сверстать экран задач",
                        "priority": "high",
                        "due_date": "10.02.2026",
                        "created_at": "20.01.2026",
                        "is_archived": False
                    },
                    {
                        "title": "Реализовать профиль сотрудника",
                        "priority": "medium",
                        "due_date": "01.02.2026",
                        "created_at": "10.01.2026",
                        "is_archived": False
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
                        "is_archived": True
                    }
                ]
            }
        ]

        # === РЕАЛЬНЫЙ ЗАПРОС К БД (раскомментируйте при необходимости) ===
        # ...

        if not completed_projects:
            no_data_label = QLabel("Нет выполненных проектов")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("font-size: 18px; color: #666666; margin: 50px;")
            self.projects_layout.addWidget(no_data_label)
        else:
            for project in completed_projects:
                self.add_project_section(project["name"], project["tasks"])

        self.projects_layout.addStretch()

    def add_project_section(self, project_name, tasks):
        # Заголовок проекта (красный, как у вас)
        header_btn = QPushButton(project_name + " ►")
        header_btn.setCheckable(True)
        header_btn.setChecked(False)
        header_btn.setStyleSheet("""
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
        """)

        # Контейнер с карточками задач
        content_frame = QFrame()
        content_frame.setVisible(False)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(15)
        content_frame.setStyleSheet("background-color: transparent;")

        if not tasks:
            no_tasks = QLabel("Нет выполненных задач в этом проекте")
            no_tasks.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tasks.setStyleSheet("color: #888888; padding: 30px; font-size: 16px;")
            content_layout.addWidget(no_tasks)
        else:
            priority_map = {
                'low': 'Низкий',
                'medium': 'Средний',
                'high': 'Высокий',
                'critical': 'Критический'
            }
            priority_colors = {
                'low': '#2ecc71',
                'medium': '#f1c40f',
                'high': '#e67e22',
                'critical': '#e74c3c'
            }

            for task in tasks:
                # Карточка задачи
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: white;
                        border-radius: 8px;
                        border-left: 6px solid {priority_colors.get(task['priority'], '#cccccc')};
                        border: none;
                    }}
                """)

                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(15, 15, 15, 15)
                card_layout.setSpacing(8)

                # Название задачи
                title_label = QLabel(task["title"])
                title_label.setWordWrap(True)
                title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
                card_layout.addWidget(title_label)

                # Приоритет
                prio_text = priority_map.get(task["priority"], task["priority"].capitalize())
                prio_label = QLabel(f"Приоритет: {prio_text}")
                prio_label.setStyleSheet(f"color: {priority_colors.get(task['priority'], '#000000')}; font-weight: bold;")
                card_layout.addWidget(prio_label)

                # Срок выполнения
                due = task.get("due_date") or "Нет"
                due_label = QLabel(f"Срок выполнения: {due}")
                card_layout.addWidget(due_label)

                # Дата создания
                created = task.get("created_at") or ""
                created_label = QLabel(f"Дата создания: {created}")
                card_layout.addWidget(created_label)

                # Архивировано
                archived = "Да" if task.get("is_archived") else "Нет"
                archived_label = QLabel(f"Архивировано: {archived}")
                if task.get("is_archived"):
                    archived_label.setStyleSheet("color: #888888;")
                card_layout.addWidget(archived_label)

                content_layout.addWidget(card)

        # Переключение видимости
        def toggle(checked):
            content_frame.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle)

        # Добавляем в основной layout
        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(content_frame)