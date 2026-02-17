import os
import sys
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# Импорт универсального компонента (путь может отличаться)
from windows.employee_card import EmployeeCard


class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "analytics_page.ui"), self)


        # Создаём тестовые данные
        self.test_employees = self.create_test_employees()

        # Заполняем вкладку сотрудников карточками
        self.populate_employees_tab()

    def create_test_employees(self):
        """Создаёт список сотрудников с их данными (темы, проекты, задачи)."""
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

    def populate_employees_tab(self):
        """Заполняет сетку на вкладке сотрудников карточками."""
        grid = self.employeesContainer.layout()  # QGridLayout
        if grid is None:
            return

        # Очищаем сетку (если ранее были добавлены карточки)
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        row = col = 0
        max_cols = 3
        for emp_data in self.test_employees:
            card = EmployeeCard(emp_data)
            grid.addWidget(card, row, col)
            grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Растяжение последней строки (чтобы карточки не разъезжались)
        grid.setRowStretch(row + 1, 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnalyticsPage()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())