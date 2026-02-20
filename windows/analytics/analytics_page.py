import os
import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QGridLayout,
    QScrollArea, QVBoxLayout
)
from PyQt6.uic import loadUi

from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from windows.analytics.theme.theme_card import ThemeCard# новый импорт


class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "analytics"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "analytics_page.ui"), self)


        self.test_employees = self.create_test_employees()
        self.test_tasks = self.create_test_tasks()
        self.populate_employees_tab()
        self.populate_themes_tab()
        self.populate_projects_tab()   # новая вкладка

    def create_test_employees(self):
        """Создаёт список сотрудников (без изменений)."""
        employees = [
            {
                "id": 1,
                "first_name": "Иван",
                "last_name": "Иванов",
                "middle_name": "Иванович",
                "position": "Ведущий разработчик",
                "department": "Отдел разработки",
                "subdivision": "Фронтенд"
            },
            {
                "id": 2,
                "first_name": "Анна",
                "last_name": "Петрова",
                "middle_name": "Сергеевна",
                "position": "Аналитик",
                "department": "Отдел аналитики",
                "subdivision": "Бизнес-анализ"
            },
            {
                "id": 3,
                "first_name": "Алексей",
                "last_name": "Сидоров",
                "middle_name": "Владимирович",
                "position": "Тестировщик",
                "department": "Отдел тестирования",
                "subdivision": "Автоматизация"
            }
        ]

        themes_data = {
            1: [
                {"theme": "Интерфейсы пользователя", "kpi": 1.2, "completed": 8},
                {"theme": "Оптимизация производительности", "kpi": 0.9, "completed": 3}
            ],
            2: [
                {"theme": "Сбор требований", "kpi": 1.5, "completed": 12},
                {"theme": "Документирование", "kpi": 1.1, "completed": 7}
            ],
            3: [
                {"theme": "Автотесты", "kpi": 0.8, "completed": 4},
                {"theme": "Регрессионное тестирование", "kpi": 1.3, "completed": 6}
            ]
        }

        projects_data = {
            1: [
                {
                    "name": "Портал самообслуживания",
                    "tasks": [
                        {
                            "title": "Разработать компонент таблицы",
                            "theme": "Интерфейсы пользователя",
                            "priority": "high",
                            "created_at": "2026-02-01",
                            "due_date": "2026-02-15",
                            "completed_at": None,
                            "status": "in_progress",
                            "creator_id": 1,
                            "tags": ["UI", "frontend"]
                        },
                        {
                            "title": "Настроить маршрутизацию",
                            "theme": "Архитектура",
                            "priority": "medium",
                            "created_at": "2026-02-05",
                            "due_date": "2026-02-20",
                            "completed_at": None,
                            "status": "to_do",
                            "creator_id": 2,
                            "tags": ["backend"]
                        }
                    ]
                },
                {
                    "name": "Мобильное приложение",
                    "tasks": [
                        {
                            "title": "Верстка экрана профиля",
                            "theme": "Интерфейсы пользователя",
                            "priority": "critical",
                            "created_at": "2026-02-10",
                            "due_date": "2026-02-12",
                            "completed_at": None,
                            "status": "review",
                            "creator_id": 1,
                            "tags": ["UI", "mobile"]
                        }
                    ]
                }
            ],
            2: [
                {
                    "name": "CRM система",
                    "tasks": [
                        {
                            "title": "Описать процесс продаж",
                            "theme": "Сбор требований",
                            "priority": "high",
                            "created_at": "2026-01-20",
                            "due_date": "2026-02-01",
                            "completed_at": "2026-01-30",
                            "status": "completed",
                            "creator_id": 2,
                            "tags": ["аналитика"]
                        },
                        {
                            "title": "Спецификация интеграции",
                            "theme": "Документирование",
                            "priority": "medium",
                            "created_at": "2026-01-25",
                            "due_date": "2026-02-10",
                            "completed_at": None,
                            "status": "in_progress",
                            "creator_id": 2,
                            "tags": ["документация"]
                        }
                    ]
                }
            ],
            3: [
                {
                    "name": "Интернет-банк",
                    "tasks": [
                        {
                            "title": "Написать тесты на платежи",
                            "theme": "Автотесты",
                            "priority": "critical",
                            "created_at": "2026-02-01",
                            "due_date": "2026-02-05",
                            "completed_at": None,
                            "status": "in_progress",
                            "creator_id": 3,
                            "tags": ["автотесты"]
                        }
                    ]
                }
            ]
        }

        result = []
        for emp in employees:
            emp_id = emp["id"]
            full_name = f"{emp['last_name']} {emp['first_name']} {emp['middle_name']}".strip()
            result.append({
                "id": emp_id,
                "name": full_name,
                "position": emp["position"],
                "department": emp["department"],
                "subdivision": emp["subdivision"],
                "themes": themes_data.get(emp_id, []),
                "projects": projects_data.get(emp_id, [])
            })
        return result

    def create_test_tasks(self):
        """Создаёт общий список задач (без изменений)."""
        tasks = []
        employee_names = {
            1: "Иван Иванов",
            2: "Анна Петрова",
            3: "Алексей Сидоров"
        }
        for emp in self.test_employees:
            emp_id = emp["id"]
            for proj in emp.get("projects", []):
                proj_name = proj["name"]
                for task in proj.get("tasks", []):
                    task_copy = task.copy()
                    task_copy["project"] = proj_name
                    if "assigned_to" not in task_copy:
                        task_copy["assigned_to"] = emp_id
                    if "creator_id" in task_copy and "creator" not in task_copy:
                        task_copy["creator"] = employee_names.get(task_copy["creator_id"], str(task_copy["creator_id"]))
                    tasks.append(task_copy)
        return tasks

    def get_all_tags(self):
        """Собирает все уникальные теги из задач (без изменений)."""
        tags = set()
        for task in self.test_tasks:
            for tag in task.get("tags", []):
                tags.add(tag)
        return sorted(tags)

    def populate_themes_tab(self):
        """Заполняет вкладку 'Темы'."""
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        themes_tab = None
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Темы":
                themes_tab = tab_widget.widget(i)
                break

        if themes_tab is None:
            return

        old_layout = themes_tab.layout()
        if old_layout:
            QWidget().setLayout(old_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)

        tags = self.get_all_tags()
        row = col = 0
        max_cols = 3
        for tag in tags:
            tag_tasks = [t for t in self.test_tasks if tag in t.get("tags", [])]
            card = ThemeCard(tag, tag_tasks)
            grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        grid.setRowStretch(row + 1, 1)

        scroll.setWidget(container)

        layout = QVBoxLayout(themes_tab)
        layout.setContentsMargins(15, 15, 15, 15)  # единые отступы
        layout.addWidget(scroll)

    def populate_employees_tab(self):
        """Заполняет вкладку 'Сотрудники'."""
        # Получаем вкладку Сотрудники
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        employees_tab = None
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Сотрудники":
                employees_tab = tab_widget.widget(i)
                break

        if employees_tab is None:
            return

        # Очищаем и создаем скролл с отступами (как в проектах)
        old_layout = employees_tab.layout()
        if old_layout:
            QWidget().setLayout(old_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)

        # Добавляем карточки
        row = col = 0
        max_cols = 3
        for emp_data in self.test_employees:
            card = EmployeeCard(emp_data)
            grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        grid.setRowStretch(row + 1, 1)

        scroll.setWidget(container)

        layout = QVBoxLayout(employees_tab)
        layout.setContentsMargins(15, 15, 15, 15)  # единые отступы
        layout.addWidget(scroll)

    def create_test_projects(self):
        """Создаёт список проектов с полным набором полей."""
        projects = []
        emp_dict = {e["id"]: e for e in self.test_employees}
        proj_map = {}

        for emp in self.test_employees:
            emp_id = emp["id"]
            for proj in emp.get("projects", []):
                proj_name = proj["name"]
                if proj_name not in proj_map:
                    proj_map[proj_name] = {
                        "name": proj_name,
                        "start_date": "2026-01-15",
                        "status": "in_progress",
                        "tasks": [],
                        "employees": {}
                    }
                for task in proj.get("tasks", []):
                    task_copy = task.copy()
                    task_copy["assigned_to"] = emp_id
                    task_copy["project"] = proj_name
                    proj_map[proj_name]["tasks"].append(task_copy)
                    if emp_id not in proj_map[proj_name]["employees"]:
                        proj_map[proj_name]["employees"][emp_id] = []
                    proj_map[proj_name]["employees"][emp_id].append(task_copy)

        for proj_name, data in proj_map.items():
            employees_list = []
            for emp_id, tasks in data["employees"].items():
                emp = emp_dict.get(emp_id, {})
                active = sum(1 for t in tasks if t.get("status") not in ("completed", "archived"))
                completed = sum(1 for t in tasks if t.get("status") in ("completed", "archived"))
                employees_list.append({
                    "id": emp_id,
                    "name": emp.get("name", f"Сотрудник {emp_id}"),
                    "active_tasks": active,
                    "completed_tasks": completed
                })
            projects.append({
                "id": proj_name,
                "name": proj_name,
                "start_date": data["start_date"],
                "status": data["status"],
                "tasks": data["tasks"],
                "employees": employees_list
            })
        return projects

    def populate_projects_tab(self):
        """Заполняет вкладку Проекты карточками проектов."""
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        if tab_widget is None:
            return

        projects_tab = None
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Проекты":
                projects_tab = tab_widget.widget(i)
                break

        if projects_tab is None:
            projects_tab = QWidget()
            tab_widget.addTab(projects_tab, "Проекты")

        # Очищаем содержимое вкладки
        old_layout = projects_tab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old_layout)

        # Создаём скролл область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # Контейнер для карточек
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Сетка для карточек
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        # grid.setContentsMargins(0, 0, 0, 0)  <-- УДАЛИТЕ ЭТУ СТРОКУ!

        # Получаем данные проектов
        projects = self.create_test_projects()

        # Добавляем карточки в сетку
        row = col = 0
        max_cols = 3

        for proj in projects:
            card = ProjectCard(proj)
            grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        grid.setRowStretch(row + 1, 1)

        scroll.setWidget(container)

        # Основной layout вкладки с отступами
        layout = QVBoxLayout(projects_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(scroll)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnalyticsPage()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())