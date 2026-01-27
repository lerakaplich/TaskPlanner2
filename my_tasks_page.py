from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QCheckBox, QPushButton, QScrollArea, QComboBox,
                             QLineEdit, QProgressBar, QMenu, QApplication,
                             QSizePolicy, QGridLayout, QTextEdit, QDateEdit)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint, QDate, QDateTime
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QFont
from PyQt6.uic import loadUi
import json
from datetime import datetime, timedelta

from task_card import TaskCard


class MyTasksPage(QWidget):
    """Страница Мои задачи с улучшенным интерфейсом"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Устанавливаем стиль для всего виджета
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        # Основной layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.main_layout)

        # 1. ВЕРХНЯЯ ПАНЕЛЬ: Заголовок и кнопки
        self.setup_header()

        # 2. ПАНЕЛЬ СТАТИСТИКИ
        self.setup_statistics()

        # 3. ПАНЕЛЬ ФИЛЬТРОВ
        self.setup_filters()

        # 4. КАНБАН ДОСКА
        self.setup_kanban()

        # Настраиваем задачи
        self.setup_tasks()

    def setup_header(self):
        """Настройка верхней панели"""
        header_layout = QHBoxLayout()

        # Заголовок
        title_label = QLabel("Мои задачи")
        title_label.setStyleSheet("""font-size: 28px;
    font-weight: bold;
    color: #1B232A;""")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()





        self.main_layout.addLayout(header_layout)

    def setup_statistics(self):
        """Настройка панели статистики"""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        # Статистика задач
        stats_widget = QFrame()
        stats_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #E0E0E0;
            }
        """)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)

        # Всего задач
        total_label = QLabel("📊 Всего задач:")
        total_label.setStyleSheet("font-size: 12px; color: #666;")
        self.total_tasks_label = QLabel("0")
        self.total_tasks_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3;")
        stats_grid.addWidget(total_label, 0, 0)
        stats_grid.addWidget(self.total_tasks_label, 0, 1)

        # Выполнено
        done_label = QLabel("✅ Выполнено:")
        done_label.setStyleSheet("font-size: 12px; color: #666;")
        self.done_tasks_label = QLabel("0")
        self.done_tasks_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        stats_grid.addWidget(done_label, 0, 2)
        stats_grid.addWidget(self.done_tasks_label, 0, 3)

        # В работе
        progress_label = QLabel("🔧 В работе:")
        progress_label.setStyleSheet("font-size: 12px; color: #666;")
        self.progress_tasks_label = QLabel("0")
        self.progress_tasks_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800;")
        stats_grid.addWidget(progress_label, 1, 0)
        stats_grid.addWidget(self.progress_tasks_label, 1, 1)

        # Просрочено
        overdue_label = QLabel("❗ Просрочено:")
        overdue_label.setStyleSheet("font-size: 12px; color: #666;")
        self.overdue_tasks_label = QLabel("0")
        self.overdue_tasks_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F44336;")
        stats_grid.addWidget(overdue_label, 1, 2)
        stats_grid.addWidget(self.overdue_tasks_label, 1, 3)

        stats_widget.setLayout(stats_grid)
        stats_layout.addWidget(stats_widget)

        # Прогресс-бар
        progress_widget = QFrame()
        progress_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #E0E0E0;
            }
        """)



    def setup_filters(self):
        """Настройка панели фильтров"""
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        # Поле поиска
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(10, 5, 10, 5)



        # Фильтр по приоритету
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["Все приоритеты", "Критический", "Высокий", "Средний", "Низкий"])
        self.priority_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                min-width: 140px;
            }
        """)
        self.priority_filter.currentTextChanged.connect(self.filter_tasks)
        filters_layout.addWidget(self.priority_filter)

        # Фильтр по проекту
        self.project_filter = QComboBox()
        self.project_filter.addItems(["Все проекты"])
        self.project_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                min-width: 160px;
            }
        """)
        self.project_filter.currentTextChanged.connect(self.filter_tasks)
        filters_layout.addWidget(self.project_filter)

        # Кнопка сброса фильтров
        btn_reset = QPushButton("Сбросить")
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        btn_reset.clicked.connect(self.reset_filters)
        filters_layout.addWidget(btn_reset)

        self.main_layout.addLayout(filters_layout)

    def setup_kanban(self):
        """Настройка канбан-доски"""
        self.kanban_layout = QHBoxLayout()
        self.kanban_layout.setSpacing(15)

        # Создаем 4 колонки
        self.columns = {
            "todo": self.create_column("📝 К ВЫПОЛНЕНИЮ", "#2196F3"),
            "progress": self.create_column("🔧 В РАБОТЕ", "#FF9800"),
            "review": self.create_column("👀 НА ПРОВЕРКЕ", "#9C27B0"),
            "done": self.create_column("✅ ВЫПОЛНЕНО", "#4CAF50")
        }

        for column in self.columns.values():
            self.kanban_layout.addWidget(column)

        self.main_layout.addLayout(self.kanban_layout, 1)

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
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 2)
        self.tasks_layout.addStretch()  # Добавляем спейсер в конец
        tasks_container.setLayout(self.tasks_layout)

        scroll_area.setWidget(tasks_container)
        layout.addWidget(scroll_area)

        column.setLayout(layout)

        # Сохраняем ссылки на важные элементы
        column.tasks_container = tasks_container
        column.tasks_layout = self.tasks_layout
        column.count_label = count_label

        return column

    def setup_tasks(self):
        """Настройка начальных задач с понятными данными"""
        # Тестовые данные с четкой структурой
        self.sample_tasks = [
            {
                "id": 1,
                "title": "Разработать дизайн главной страницы",
                "description": "Создать современный дизайн главной страницы сайта с адаптивной версткой",
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
        self.project_filter.addItems(sorted(list(projects)))

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
        self.total_tasks_label.setText(str(total_count))
        self.done_tasks_label.setText(str(done_count))
        self.progress_tasks_label.setText(str(progress_count))

        # Подсчет просроченных задач
        overdue_count = 0
        current_date = QDate.currentDate()
        for task in self.sample_tasks:
            deadline = task.get("deadline", "")
            if deadline:
                deadline_date = self.parse_date(deadline)
                if deadline_date and deadline_date < current_date and not task.get("completed", False):
                    overdue_count += 1

        self.overdue_tasks_label.setText(str(overdue_count))

        # Расчет прогресса
        progress = int((done_count / total_count * 100)) if total_count > 0 else 0

    def parse_date(self, date_str):
        """Парсинг даты из строки"""
        try:
            return QDate.fromString(date_str, "dd.MM.yyyy")
        except:
            return None

    def create_new_task(self):
        """Создать новую задачу"""
        print("Создание новой задачи...")
        # Здесь будет логика создания новой задачи

    def show_archive(self):
        """Показать архив задач"""
        print("Показать архив...")

    def search_tasks(self, text):
        """Поиск задач"""
        print(f"Поиск: {text}")

    def filter_tasks(self):
        """Фильтрация задач"""
        priority_filter = self.priority_filter.currentText()
        project_filter = self.project_filter.currentText()
        print(f"Фильтр: приоритет={priority_filter}, проект={project_filter}")

    def reset_filters(self):
        """Сброс фильтров"""
        self.priority_filter.setCurrentIndex(0)
        self.project_filter.setCurrentIndex(0)
        print("Фильтры сброшены")