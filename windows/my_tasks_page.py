import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QPushButton, QScrollArea, QComboBox,
                             QLineEdit, QProgressBar, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from PyQt6.uic import loadUi
import json
from datetime import datetime

from task_card import TaskCard


class MyTasksPage(QWidget):
    """Страница Мои задачи others_tasks_page.ui улучшенным интерфейсом"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "my_tasks_page.ui"), self)

        # Настраиваем канбан-доску
        self.setup_kanban()

        # Настраиваем задачи
        self.setup_tasks()

        # Подключаем сигналы
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)

    def setup_kanban(self):
        """Настройка канбан-доски"""
        self.kanbanLayout.setSpacing(15)

        # Создаем 4 колонки
        self.columns = {
            "todo": self.create_column("📝 К ВЫПОЛНЕНИЮ", "#2196F3"),
            "progress": self.create_column("🔧 В РАБОТЕ", "#FF9800"),
            "review": self.create_column("👀 НА ПРОВЕРКЕ", "#9C27B0"),
            "done": self.create_column("✅ ВЫПОЛНЕНО", "#4CAF50")
        }

        for column in self.columns.values():
            self.kanbanLayout.addWidget(column)

    def create_column(self, title, color):
        """Создание одной колонки канбан-доски"""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Заголовок колонки
        header = QHBoxLayout()

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {color};")
        header.addWidget(title_label)

        count_label = QLabel("0")
        count_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: white;
                background-color: #666;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        header.addWidget(count_label)

        header.addStretch()

        layout.addLayout(header)

        # Скроллируемая область для задач
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        # Контейнер для задач
        tasks_container = QWidget()
        tasks_container.setStyleSheet("background-color: transparent;")
        tasks_layout = QVBoxLayout()
        tasks_layout.setSpacing(8)
        tasks_layout.setContentsMargins(2, 2, 2, 2)
        tasks_layout.addStretch()  # Добавляем спейсер в конец
        tasks_container.setLayout(tasks_layout)

        scroll_area.setWidget(tasks_container)
        layout.addWidget(scroll_area)

        column.setLayout(layout)

        # Сохраняем ссылки на важные элементы
        column.tasks_container = tasks_container
        column.tasks_layout = tasks_layout
        column.count_label = count_label

        return column

    def setup_tasks(self):
        """Настройка начальных задач others_tasks_page.ui понятными данными"""
        # Тестовые данные others_tasks_page.ui четкой структурой
        self.sample_tasks = [
            {
                "id": 1,
                "title": "Разработать дизайн главной страницы",
                "description": "Создать современный дизайн главной страницы сайта others_tasks_page.ui адаптивной версткой",
                "project": "Разработка сайта компании",
                "creator": "Алексей Петров",
                "priority": "high",
                "deadline": "20.12.2024",
                "status": "todo",
                "created_at": "15.11.2024",
                "updated_at": "18.11.2024",
                "tags": [
                    {"text": "Дизайн", "type": "design"},
                    {"text": "СРОЧНО", "type": "urgent"}
                ],
                "completed": False
            },
            {
                "id": 2,
                "title": "Исправить баг в модуле авторизации",
                "description": "Пользователи не могут войти в систему после обновления",
                "project": "Внутренний портал",
                "creator": "Мария Сидорова",
                "priority": "critical",
                "deadline": "10.12.2024",
                "status": "progress",
                "created_at": "10.11.2024",
                "updated_at": "19.11.2024",
                "tags": [
                    {"text": "Баг", "type": "bug"},
                    {"text": "Безопасность", "type": "security"}
                ],
                "completed": False
            },
            {
                "id": 3,
                "title": "Написать документацию для API",
                "description": "Подготовить подробную документацию для REST API",
                "project": "Мобильное приложение",
                "creator": "Иван Иванов",
                "priority": "medium",
                "deadline": "25.12.2024",
                "status": "review",
                "created_at": "05.11.2024",
                "updated_at": "17.11.2024",
                "tags": [
                    {"text": "Документация", "type": "docs"},
                    {"text": "Разработка", "type": "development"}
                ],
                "completed": False
            },
            {
                "id": 4,
                "title": "Провести тестирование новой функции",
                "description": "Протестировать функцию импорта данных из Excel",
                "project": "ERP система",
                "creator": "Ольга Ковалева",
                "priority": "low",
                "deadline": "05.12.2024",
                "status": "done",
                "created_at": "01.11.2024",
                "updated_at": "05.11.2024",
                "tags": [
                    {"text": "Тестирование", "type": "testing"}
                ],
                "completed": True
            },
            {
                "id": 5,
                "title": "Обновить контакты клиентов",
                "description": "Обновить базу данных контактов ключевых клиентов",
                "project": "CRM система",
                "creator": "Сергей Васильев",
                "priority": "medium",
                "deadline": "15.12.2024",
                "status": "todo",
                "created_at": "12.11.2024",
                "updated_at": "12.11.2024",
                "tags": [
                    {"text": "Данные", "type": "data"},
                    {"text": "Обновление", "type": "update"}
                ],
                "completed": False
            }
        ]

        # Распределяем задачи по колонкам
        self.all_tasks = []
        for task_data in self.sample_tasks:
            task_card = TaskCard(task_data)
            self.all_tasks.append(task_card)

            # Добавляем в соответствующую колонку
            status = task_data["status"]
            if status == "todo":
                self.columns["todo"].tasks_layout.insertWidget(
                    self.columns["todo"].tasks_layout.count() - 1, task_card
                )
            elif status == "progress":
                self.columns["progress"].tasks_layout.insertWidget(
                    self.columns["progress"].tasks_layout.count() - 1, task_card
                )
            elif status == "review":
                self.columns["review"].tasks_layout.insertWidget(
                    self.columns["review"].tasks_layout.count() - 1, task_card
                )
            elif status == "done":
                self.columns["done"].tasks_layout.insertWidget(
                    self.columns["done"].tasks_layout.count() - 1, task_card
                )

        # Обновляем статистику
        self.update_statistics()

        # Заполняем фильтр проектов
        projects = set(task["project"] for task in self.sample_tasks)
        self.projectFilter.addItems(sorted(list(projects)))

    def update_statistics(self):
        """Обновление статистики"""
        # Подсчет задач по статусам
        todo_count = len([t for t in self.sample_tasks if t["status"] == "todo"])
        progress_count = len([t for t in self.sample_tasks if t["status"] == "progress"])
        review_count = len([t for t in self.sample_tasks if t["status"] == "review"])
        done_count = len([t for t in self.sample_tasks if t["status"] == "done"])

        total_count = len(self.sample_tasks)

        # Обновляем заголовки колонок
        self.columns["todo"].count_label.setText(str(todo_count))
        self.columns["progress"].count_label.setText(str(progress_count))
        self.columns["review"].count_label.setText(str(review_count))
        self.columns["done"].count_label.setText(str(done_count))

        # Обновляем статистику
        self.totalTasksLabel.setText(f"📊 Всего задач: {total_count}")
        self.completedTasksLabel.setText(f"✅ Выполнено: {done_count}")

        # Подсчет просроченных задач
        overdue_count = 0
        current_date = QDate.currentDate()
        for task in self.sample_tasks:
            deadline = task.get("deadline", "")
            if deadline:
                deadline_date = self.parse_date(deadline)
                if deadline_date and deadline_date < current_date and not task.get("completed", False):
                    overdue_count += 1

        self.overdueTasksLabel.setText(f"⏰ Просрочено: {overdue_count}")

        # Расчет и установка прогресса
        progress = int((done_count / total_count * 100)) if total_count > 0 else 0
        self.overallProgress.setValue(progress)

    def parse_date(self, date_str):
        """Парсинг даты из строки"""
        try:
            return QDate.fromString(date_str, "dd.MM.yyyy")
        except:
            return None

    def filter_tasks(self):
        """Фильтрация задач"""
        priority_filter = self.priorityFilter.currentText()
        project_filter = self.projectFilter.currentText()
        print(f"Фильтр: приоритет={priority_filter}, проект={project_filter}")