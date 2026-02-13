import os
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QTableWidgetItem, QListWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView, QFrame, QPushButton, QComboBox, QDateEdit,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QProgressBar,
    QScrollArea, QSplitter, QGroupBox, QGridLayout, QListWidget, QTableWidget
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont, QDragEnterEvent, QDropEvent, QIcon, QAction
from PyQt6.uic import loadUi

import random


class Task:
    """Класс задачи для тестовых данных"""

    def __init__(self, id, title, description, priority, due_date, created_date,
                 assignee, assignee_name, column_id, column_name, progress=0):
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.due_date = due_date
        self.created_date = created_date
        self.assignee = assignee
        self.assignee_name = assignee_name
        self.column_id = column_id
        self.column_name = column_name
        self.progress = progress
        self.duration = (due_date - created_date).days if due_date and created_date else 5


class GanttChartWidget(QWidget):
    """Виджет диаграммы Ганта с корпоративными цветами и тестовыми данными"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Тестовые данные
        self.current_project_id = 1
        self.current_project_name = "Task Planner"
        self.projects = []
        self.tasks = []
        self.employees = []
        self.dependencies = []

        # Параметры отображения
        self.current_date = datetime(2026, 2, 13)  # Текущая дата
        self.displayed_month = 2  # Февраль
        self.displayed_year = 2026
        self.column_width = 80  # Ширина колонки в пикселях

        # Загрузка UI
        try:
            self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

            # Загружаем UI из файла
            loadUi(os.path.join(self.ui_path, "gantt_chart.ui"), self)
        except:
            # Если файл .ui не найден, создаем интерфейс программно
            self.setup_ui_manually()

        # Инициализация тестовых данных
        self.init_test_data()

        # Настройка интерфейса
        self.setup_ui()

        # Подключение сигналов
        self.connect_signals()

        # Загрузка данных
        self.load_projects()
        self.load_tasks()

    def setup_ui_manually(self):
        """Создание интерфейса программно (если .ui файл отсутствует)"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Главный фрейм
        main_frame = QFrame()
        main_frame.setObjectName("mainFrame")
        main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: #1E2A36;
                border-radius: 12px;
                border: 1px solid #334756;
            }
        """)

        main_layout.addWidget(main_frame)

        # Горизонтальный layout для сайдбара и диаграммы
        h_layout = QHBoxLayout(main_frame)
        h_layout.setContentsMargins(10, 10, 10, 10)
        h_layout.setSpacing(10)

        # Сайдбар (список задач)
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")
        self.sidebar_frame.setMinimumWidth(350)
        self.sidebar_frame.setMaximumWidth(450)
        self.sidebar_frame.setStyleSheet("""
            QFrame#sidebarFrame {
                background-color: #17212B;
                border-radius: 12px;
                border: 1px solid #334756;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)

        # Заголовок сайдбара
        title_label = QLabel("📋 СПИСОК ЗАДАЧ ПРОЕКТА")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ccab6e;")
        sidebar_layout.addWidget(title_label)

        # Комбобокс проектов
        self.projectComboBox = QComboBox()
        self.projectComboBox.setMinimumHeight(45)
        self.projectComboBox.setStyleSheet("""
            QComboBox {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QComboBox:hover {
                border: 2px solid #D22730;
            }
        """)
        sidebar_layout.addWidget(self.projectComboBox)

        # Фрейм фильтров
        filter_frame = QFrame()
        filter_frame.setMinimumHeight(120)
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #1E2A36;
                border-radius: 10px;
                border: 1px solid #334756;
            }
        """)

        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Исполнитель:"), 0, 0)
        self.assigneeFilterCombo = QComboBox()
        self.assigneeFilterCombo.setMinimumHeight(35)
        filter_layout.addWidget(self.assigneeFilterCombo, 0, 1)

        filter_layout.addWidget(QLabel("Приоритет:"), 1, 0)
        self.priorityFilterCombo = QComboBox()
        self.priorityFilterCombo.setMinimumHeight(35)
        filter_layout.addWidget(self.priorityFilterCombo, 1, 1)

        self.applyFilterBtn = QPushButton("Применить фильтры")
        self.applyFilterBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 8px;
                font-size: 14px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
                border: 2px solid #D22730;
            }
        """)
        self.applyFilterBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        filter_layout.addWidget(self.applyFilterBtn, 2, 0, 1, 2)

        sidebar_layout.addWidget(filter_frame)

        # Заголовок списка задач
        task_header = QLabel("⚡ ЗАДАЧИ НА ДИАГРАММЕ")
        task_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #D22730; margin-top: 10px;")
        sidebar_layout.addWidget(task_header)

        # Список задач
        self.taskListWidget = QListWidget()
        self.taskListWidget.setMinimumHeight(350)
        self.taskListWidget.setDragEnabled(True)
        self.taskListWidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.taskListWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.taskListWidget.setAlternatingRowColors(True)
        self.taskListWidget.setStyleSheet("""
            QListWidget {
                background-color: #1E2A36;
                border: none;
                border-radius: 8px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                background-color: #2A3743;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
                border-left: 4px solid #ccab6e;
                color: white;
            }
            QListWidget::item:selected {
                background-color: #D22730;
                border-left: 4px solid #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #3E4E5D;
            }
        """)
        sidebar_layout.addWidget(self.taskListWidget)

        # Фрейм действий
        actions_frame = QFrame()
        actions_frame.setMinimumHeight(100)
        actions_frame.setStyleSheet("""
            QFrame {
                background-color: #1E2A36;
                border-radius: 10px;
                border: 1px solid #334756;
            }
        """)

        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(10, 10, 10, 10)
        actions_layout.setSpacing(10)

        self.addTaskBtn = QPushButton("➕ Добавить задачу на Гант")
        self.addTaskBtn.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        self.addTaskBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.addTaskBtn)

        self.editTaskBtn = QPushButton("✏️ Редактировать сроки")
        self.editTaskBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: 2px solid #D22730;
                font-size: 15px;
                padding: 12px;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        self.editTaskBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.editTaskBtn)

        sidebar_layout.addWidget(actions_frame)

        # Добавляем сайдбар в основной layout
        h_layout.addWidget(self.sidebar_frame)

        # Фрейм диаграммы Ганта
        self.gantt_frame = QFrame()
        self.gantt_frame.setStyleSheet("""
            QFrame {
                background-color: #1E2A36;
                border-radius: 12px;
                border: 1px solid #334756;
            }
        """)

        gantt_layout = QVBoxLayout(self.gantt_frame)
        gantt_layout.setContentsMargins(15, 15, 15, 15)
        gantt_layout.setSpacing(10)

        # Верхняя панель управления диаграммой
        controls_layout = QHBoxLayout()

        title_label = QLabel("📊 ДИАГРАММА ГАНТА")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ccab6e;")
        controls_layout.addWidget(title_label)

        controls_layout.addStretch()

        # Кнопки масштабирования
        self.zoomInBtn = QPushButton("+")
        self.zoomInBtn.setFixedSize(50, 50)
        self.zoomInBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border-radius: 25px;
                border: 2px solid #ccab6e;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        self.zoomInBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.zoomInBtn)

        self.zoomOutBtn = QPushButton("-")
        self.zoomOutBtn.setFixedSize(50, 50)
        self.zoomOutBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border-radius: 25px;
                border: 2px solid #ccab6e;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        self.zoomOutBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.zoomOutBtn)

        self.scaleCombo = QComboBox()
        self.scaleCombo.addItems(["День", "Неделя", "Месяц"])
        self.scaleCombo.setMinimumWidth(120)
        self.scaleCombo.setMinimumHeight(40)
        self.scaleCombo.setStyleSheet("""
            QComboBox {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        controls_layout.addWidget(self.scaleCombo)

        self.exportBtn = QPushButton("📥 Экспорт")
        self.exportBtn.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #862633;
            }
        """)
        self.exportBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.exportBtn)

        gantt_layout.addLayout(controls_layout)

        # Панель временной шкалы
        timeline_frame = QFrame()
        timeline_frame.setMinimumHeight(80)
        timeline_frame.setStyleSheet("""
            QFrame {
                background-color: #17212B;
                border-radius: 8px;
                border: 1px solid #334756;
            }
        """)

        timeline_layout = QHBoxLayout(timeline_frame)
        timeline_layout.setSpacing(20)

        self.month_label = QLabel("🗓️ Февраль 2026")
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ccab6e;")
        timeline_layout.addWidget(self.month_label)

        self.prevPeriodBtn = QPushButton("◀")
        self.prevPeriodBtn.setFixedSize(40, 40)
        self.prevPeriodBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
                color: white;
                border: 1px solid #ccab6e;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        timeline_layout.addWidget(self.prevPeriodBtn)

        self.nextPeriodBtn = QPushButton("▶")
        self.nextPeriodBtn.setFixedSize(40, 40)
        self.nextPeriodBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
                color: white;
                border: 1px solid #ccab6e;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        timeline_layout.addWidget(self.nextPeriodBtn)

        self.todayBtn = QPushButton("Сегодня")
        self.todayBtn.setMinimumHeight(40)
        self.todayBtn.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                border-radius: 5px;
                padding: 5px 15px;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        timeline_layout.addWidget(self.todayBtn)

        timeline_layout.addStretch()

        # Легенда
        timeline_layout.addWidget(QLabel("Легенда:"))

        crit_frame = QFrame()
        crit_frame.setFixedSize(20, 20)
        crit_frame.setStyleSheet("background-color: #D22730; border-radius: 4px;")
        timeline_layout.addWidget(crit_frame)
        timeline_layout.addWidget(QLabel("Critical"))

        high_frame = QFrame()
        high_frame.setFixedSize(20, 20)
        high_frame.setStyleSheet("background-color: #ccab6e; border-radius: 4px;")
        timeline_layout.addWidget(high_frame)
        timeline_layout.addWidget(QLabel("High"))

        medium_frame = QFrame()
        medium_frame.setFixedSize(20, 20)
        medium_frame.setStyleSheet("background-color: #3498db; border-radius: 4px;")
        timeline_layout.addWidget(medium_frame)
        timeline_layout.addWidget(QLabel("Medium"))

        gantt_layout.addWidget(timeline_frame)

        # Область прокрутки для диаграммы
        scroll_area = QScrollArea()
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidgetResizable(True)

        self.gantt_content = QWidget()
        self.gantt_content_layout = QVBoxLayout(self.gantt_content)

        # Таблица Ганта
        self.ganttTable = QTableWidget()
        self.ganttTable.setStyleSheet("""
            QTableWidget {
                background-color: #1E2A36;
                border: none;
                gridline-color: #334756;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #334756;
            }
            QHeaderView::section {
                background-color: #17212B;
                color: #ccab6e;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-right: 1px solid #334756;
                border-bottom: 2px solid #D22730;
            }
        """)

        self.gantt_content_layout.addWidget(self.ganttTable)

        # Фрейм зависимостей
        self.dependency_frame = QFrame()
        self.dependency_frame.setMinimumHeight(80)
        self.dependency_frame.setStyleSheet("""
            QFrame {
                background-color: #17212B;
                border-radius: 8px;
                border-left: 4px solid #ccab6e;
                border: 1px solid #334756;
            }
        """)

        dep_layout = QHBoxLayout(self.dependency_frame)

        dep_label = QLabel("🔗 ЛОГИЧЕСКИЕ СВЯЗИ")
        dep_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ccab6e;")
        dep_layout.addWidget(dep_label)

        self.addDependencyBtn = QPushButton("➕ Добавить связь")
        self.addDependencyBtn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                border: 2px solid #D22730;
                border-radius: 6px;
                padding: 8px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        dep_layout.addWidget(self.addDependencyBtn)

        dep_layout.addStretch()

        self.dependency_label = QLabel("Задача 1 → Задача 2 (Финиш-Старт)")
        self.dependency_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: white;
                padding: 5px 10px;
                background-color: #1E2A36;
                border-radius: 4px;
            }
        """)
        dep_layout.addWidget(self.dependency_label)

        self.gantt_content_layout.addWidget(self.dependency_frame)

        scroll_area.setWidget(self.gantt_content)
        gantt_layout.addWidget(scroll_area)

        h_layout.addWidget(self.gantt_frame)

        # Устанавливаем соотношение размеров сайдбара и диаграммы
        h_layout.setStretchFactor(self.sidebar_frame, 1)
        h_layout.setStretchFactor(self.gantt_frame, 3)

    def init_test_data(self):
        """Инициализация тестовых данных"""

        # Проекты
        self.projects = [
            {"id": 1, "name": "Task Planner", "description": "Планировщик задач", "active": True},
            {"id": 2, "name": "Маркетинговый сайт", "description": "Разработка корпоративного сайта", "active": True},
            {"id": 3, "name": "Мобильное приложение", "description": "Приложение для клиентов", "active": True},
            {"id": 4, "name": "CRM система", "description": "Внутренняя CRM", "active": False},
        ]

        # Сотрудники
        self.employees = [
            {"id": 1, "name": "Иванов Иван", "position": "Senior Developer", "avatar": "👨‍💻"},
            {"id": 2, "name": "Петрова Анна", "position": "Frontend Developer", "avatar": "👩‍💻"},
            {"id": 3, "name": "Сидоров Петр", "position": "QA Engineer", "avatar": "🧪"},
            {"id": 4, "name": "Козлова Елена", "position": "Project Manager", "avatar": "👩‍💼"},
            {"id": 5, "name": "Смирнов Алексей", "position": "Backend Developer", "avatar": "👨‍🔧"},
        ]

        # Задачи с реальными датами
        base_date = datetime(2026, 2, 1)

        self.tasks = [
            Task(
                id=1,
                title="Сверстать экран задач",
                description="Сделать UI карточек задач для доски",
                priority="high",
                due_date=datetime(2026, 2, 15),
                created_date=datetime(2026, 2, 3),
                assignee=2,
                assignee_name="Петрова Анна",
                column_id=2,
                column_name="In Progress",
                progress=60
            ),
            Task(
                id=2,
                title="Разработать бэкенд API",
                description="Создать REST API для управления задачами",
                priority="critical",
                due_date=datetime(2026, 2, 20),
                created_date=datetime(2026, 2, 5),
                assignee=1,
                assignee_name="Иванов Иван",
                column_id=2,
                column_name="In Progress",
                progress=30
            ),
            Task(
                id=3,
                title="Написать тесты",
                description="Покрыть функционал модульными тестами",
                priority="medium",
                due_date=datetime(2026, 2, 25),
                created_date=datetime(2026, 2, 10),
                assignee=3,
                assignee_name="Сидоров Петр",
                column_id=1,
                column_name="To Do",
                progress=0
            ),
            Task(
                id=4,
                title="Документация",
                description="Написать документацию по API",
                priority="low",
                due_date=datetime(2026, 2, 28),
                created_date=datetime(2026, 2, 1),
                assignee=2,
                assignee_name="Петрова Анна",
                column_id=3,
                column_name="Done",
                progress=90
            ),
            Task(
                id=5,
                title="Рефакторинг кода",
                description="Оптимизировать существующий код",
                priority="high",
                due_date=datetime(2026, 3, 5),
                created_date=datetime(2026, 2, 15),
                assignee=1,
                assignee_name="Иванов Иван",
                column_id=1,
                column_name="To Do",
                progress=20
            ),
            Task(
                id=6,
                title="Дизайн системы",
                description="Разработать дизайн-систему компонентов",
                priority="medium",
                due_date=datetime(2026, 2, 18),
                created_date=datetime(2026, 2, 8),
                assignee=2,
                assignee_name="Петрова Анна",
                column_id=3,
                column_name="Done",
                progress=100
            ),
            Task(
                id=7,
                title="Настройка CI/CD",
                description="Настроить пайплайны сборки и деплоя",
                priority="high",
                due_date=datetime(2026, 2, 22),
                created_date=datetime(2026, 2, 12),
                assignee=5,
                assignee_name="Смирнов Алексей",
                column_id=2,
                column_name="In Progress",
                progress=45
            ),
        ]

        # Зависимости между задачами
        self.dependencies = [
            {"from_task": 1, "to_task": 2, "type": "finish_start"},
            {"from_task": 2, "to_task": 3, "type": "finish_start"},
            {"from_task": 4, "to_task": 1, "type": "start_start"},
            {"from_task": 5, "to_task": 6, "type": "finish_start"},
        ]

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""

        # Настройка таблицы Ганта, если .ui загружен
        if hasattr(self, 'ganttTable'):
            # Настройка заголовков
            header = self.ganttTable.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            header.setDefaultSectionSize(self.column_width)

            vertical_header = self.ganttTable.verticalHeader()
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            vertical_header.setDefaultSectionSize(50)
            vertical_header.setVisible(True)

            # Drag and drop
            self.ganttTable.setDragEnabled(True)
            self.ganttTable.setAcceptDrops(True)
            self.ganttTable.setDropIndicatorShown(True)
            self.ganttTable.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        # Установка заголовка
        self.update_timeline_label()

    def connect_signals(self):
        """Подключение сигналов к слотам"""

        # Проекты
        if hasattr(self, 'projectComboBox'):
            self.projectComboBox.currentIndexChanged.connect(self.on_project_changed)

        # Фильтры
        if hasattr(self, 'applyFilterBtn'):
            self.applyFilterBtn.clicked.connect(self.apply_filters)

        # Кнопки действий
        if hasattr(self, 'addTaskBtn'):
            self.addTaskBtn.clicked.connect(self.add_task_dialog)
        if hasattr(self, 'editTaskBtn'):
            self.editTaskBtn.clicked.connect(self.edit_task_dialog)
        if hasattr(self, 'exportBtn'):
            self.exportBtn.clicked.connect(self.export_gantt)

        # Масштабирование
        if hasattr(self, 'zoomInBtn'):
            self.zoomInBtn.clicked.connect(self.zoom_in)
        if hasattr(self, 'zoomOutBtn'):
            self.zoomOutBtn.clicked.connect(self.zoom_out)
        if hasattr(self, 'scaleCombo'):
            self.scaleCombo.currentIndexChanged.connect(self.change_scale)

        # Навигация по времени
        if hasattr(self, 'prevPeriodBtn'):
            self.prevPeriodBtn.clicked.connect(self.prev_period)
        if hasattr(self, 'nextPeriodBtn'):
            self.nextPeriodBtn.clicked.connect(self.next_period)
        if hasattr(self, 'todayBtn'):
            self.todayBtn.clicked.connect(self.go_to_today)

        # Связи
        if hasattr(self, 'addDependencyBtn'):
            self.addDependencyBtn.clicked.connect(self.add_dependency_dialog)

        # Drag and drop
        if hasattr(self, 'taskListWidget'):
            self.taskListWidget.model().rowsMoved.connect(self.on_tasks_reordered)

    def load_projects(self):
        """Загрузка тестовых проектов"""
        if hasattr(self, 'projectComboBox'):
            self.projectComboBox.clear()

            for project in self.projects:
                if project["active"]:
                    self.projectComboBox.addItem(project["name"], project["id"])

            # Выбираем первый проект
            if self.projectComboBox.count() > 0:
                self.projectComboBox.setCurrentIndex(0)

    def load_tasks(self):
        """Загрузка тестовых задач"""

        # Обновляем список задач в сайдбаре
        self.update_task_list()

        # Обновляем диаграмму Ганта
        self.update_gantt_chart()

        # Обновляем фильтры
        self.update_filters()

    def update_task_list(self):
        """Обновление списка задач в сайдбаре"""
        if not hasattr(self, 'taskListWidget'):
            return

        self.taskListWidget.clear()

        priority_icons = {
            'critical': '🔴',
            'high': '🟡',
            'medium': '🟢',
            'low': '🔵'
        }

        priority_colors = {
            'critical': QColor(210, 39, 48),
            'high': QColor(204, 171, 110),
            'medium': QColor(52, 152, 219),
            'low': QColor(46, 204, 113)
        }

        for task in self.tasks:
            if task.project_id != self.current_project_id and hasattr(self, 'current_project_id'):
                continue

            due_str = task.due_date.strftime('%d.%m.%Y') if task.due_date else 'Нет срока'
            icon = priority_icons.get(task.priority, '⚪')

            # Прогресс-бар в текстовом виде
            progress_bar = "█" * (task.progress // 10) + "░" * (10 - task.progress // 10)

            display_text = f"{icon} {task.title}\n👤 {task.assignee_name} | ⏰ {due_str} | {progress_bar} {task.progress}%"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, task.id)

            # Цветовая индикация приоритета
            if task.priority == 'critical':
                item.setForeground(QBrush(priority_colors['critical']))
                item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            elif task.priority == 'high':
                item.setForeground(QBrush(priority_colors['high']))
            elif task.priority == 'medium':
                item.setForeground(QBrush(priority_colors['medium']))
            else:
                item.setForeground(QBrush(priority_colors['low']))

            # Устанавливаем тултип с подробной информацией
            tooltip = f"Задача: {task.title}\n"
            tooltip += f"Описание: {task.description}\n"
            tooltip += f"Исполнитель: {task.assignee_name}\n"
            tooltip += f"Приоритет: {task.priority.upper()}\n"
            tooltip += f"Создана: {task.created_date.strftime('%d.%m.%Y')}\n"
            tooltip += f"Дедлайн: {due_str}\n"
            tooltip += f"Статус: {task.column_name}\n"
            tooltip += f"Прогресс: {task.progress}%"

            item.setToolTip(tooltip)

            self.taskListWidget.addItem(item)

    def update_filters(self):
        """Обновление фильтров"""
        if not hasattr(self, 'assigneeFilterCombo') or not hasattr(self, 'priorityFilterCombo'):
            return

        # Фильтр исполнителей
        self.assigneeFilterCombo.clear()
        self.assigneeFilterCombo.addItem("Все исполнители")

        assignees = set()
        for task in self.tasks:
            if task.project_id == self.current_project_id:
                assignees.add(task.assignee_name)

        for assignee in sorted(assignees):
            self.assigneeFilterCombo.addItem(assignee)

        # Фильтр приоритетов
        self.priorityFilterCombo.clear()
        self.priorityFilterCombo.addItem("Все приоритеты")
        self.priorityFilterCombo.addItems(['critical', 'high', 'medium', 'low'])

    def update_gantt_chart(self):
        """Обновление диаграммы Ганта"""
        if not hasattr(self, 'ganttTable'):
            return

        # Фильтруем задачи для текущего проекта
        project_tasks = [t for t in self.tasks if t.project_id == self.current_project_id]

        # Сортируем по дате создания
        project_tasks.sort(key=lambda x: x.created_date)

        # Устанавливаем количество строк
        self.ganttTable.setRowCount(len(project_tasks))

        # Получаем количество дней в текущем месяце
        if self.displayed_month == 2:  # Февраль 2026 не високосный
            days_in_month = 28
        else:
            days_in_month = 31

        self.ganttTable.setColumnCount(days_in_month)

        # Устанавливаем заголовки колонок (дни месяца)
        for col in range(days_in_month):
            day_num = col + 1
            item = QTableWidgetItem(str(day_num))
            self.ganttTable.setHorizontalHeaderItem(col, item)

        # Заполняем таблицу
        for row, task in enumerate(project_tasks):
            # Установка названия задачи в вертикальный заголовок
            title_text = f"{task.title[:20]}..." if len(task.title) > 20 else task.title
            self.ganttTable.setVerticalHeaderItem(row, QTableWidgetItem(title_text))

            # Получаем позицию на диаграмме
            start_day = task.created_date.day
            duration = task.duration

            # Определяем цвет по приоритету
            color = self.get_priority_color(task.priority)

            # Создаем элемент для каждой ячейки в диапазоне
            for day_offset in range(duration):
                col = start_day + day_offset - 1  # -1 потому что дни с 1

                if col < days_in_month:
                    item = QTableWidgetItem()

                    # Для первого дня добавляем название
                    if day_offset == 0:
                        item.setText(task.title[:15])

                    item.setBackground(QBrush(color))
                    item.setForeground(QBrush(QColor('white')))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    font = QFont()
                    font.setBold(True)
                    font.setPointSize(9)
                    item.setFont(font)

                    # Сохраняем ID задачи в данных
                    item.setData(Qt.ItemDataRole.UserRole, task.id)

                    # Добавляем информацию о прогрессе
                    item.setData(Qt.ItemDataRole.UserRole + 1, task.progress)

                    # Устанавливаем тултип
                    tooltip = f"{task.title}\n"
                    tooltip += f"Исполнитель: {task.assignee_name}\n"
                    tooltip += f"Прогресс: {task.progress}%\n"
                    tooltip += f"Дедлайн: {task.due_date.strftime('%d.%m.%Y')}"
                    item.setToolTip(tooltip)

                    self.ganttTable.setItem(row, col, item)

        # Растягиваем последний столбец
        self.ganttTable.horizontalHeader().setStretchLastSection(True)

    def get_priority_color(self, priority):
        """Получение цвета по приоритету задачи"""
        colors = {
            'critical': QColor(210, 39, 48),  # Красный
            'high': QColor(204, 171, 110),  # Золотой
            'medium': QColor(52, 152, 219),  # Синий
            'low': QColor(46, 204, 113)  # Зеленый
        }
        return colors.get(priority, QColor(128, 128, 128))

    def on_project_changed(self, index):
        """Обработчик смены проекта"""
        if hasattr(self, 'projectComboBox'):
            self.current_project_id = self.projectComboBox.currentData()
            self.current_project_name = self.projectComboBox.currentText()
            self.load_tasks()

    def apply_filters(self):
        """Применение фильтров к списку задач"""
        if not hasattr(self, 'taskListWidget'):
            return

        assignee = self.assigneeFilterCombo.currentText()
        priority = self.priorityFilterCombo.currentText()

        for i in range(self.taskListWidget.count()):
            item = self.taskListWidget.item(i)
            item.setHidden(False)

            text = item.text()

            if assignee != "Все исполнители" and assignee not in text:
                item.setHidden(True)

            if priority != "Все приоритеты" and priority not in text.lower():
                item.setHidden(True)

    def add_task_dialog(self):
        """Диалог добавления новой задачи на диаграмму"""
        dialog = QDialog(self)
        dialog.setWindowTitle("➕ Добавить задачу на диаграмму Ганта")
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E2A36;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #D22730;
            }
            QPushButton {
                background-color: #D22730;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #862633;
            }
        """)

        layout = QVBoxLayout(dialog)

        # Заголовок
        title_label = QLabel("НОВАЯ ЗАДАЧА")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ccab6e;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Форма
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Название задачи
        title_edit = QComboBox()
        title_edit.setEditable(True)
        title_edit.addItem("Сверстать дашборд")
        title_edit.addItem("Написать миграции БД")
        title_edit.addItem("Провести код-ревью")
        title_edit.addItem("Обновить зависимости")
        title_edit.addItem("Исправить баги")
        form_layout.addRow("Название задачи:", title_edit)

        # Описание
        desc_edit = QComboBox()
        desc_edit.setEditable(True)
        desc_edit.addItem("Создать интерфейс аналитики")
        desc_edit.addItem("Обновить схему базы данных")
        desc_edit.addItem("Проверить пул-реквесты")
        desc_edit.addItem("Обновить версии пакетов")
        form_layout.addRow("Описание:", desc_edit)

        # Даты
        start_date = QDateEdit()
        start_date.setDate(QDate(2026, 2, self.current_date.day + 1))
        start_date.setCalendarPopup(True)
        form_layout.addRow("Дата начала:", start_date)

        end_date = QDateEdit()
        end_date.setDate(QDate(2026, 2, self.current_date.day + 8))
        end_date.setCalendarPopup(True)
        form_layout.addRow("Дата окончания:", end_date)

        # Приоритет
        priority_combo = QComboBox()
        priority_combo.addItems(['critical', 'high', 'medium', 'low'])
        form_layout.addRow("Приоритет:", priority_combo)

        # Исполнитель
        assignee_combo = QComboBox()
        for emp in self.employees:
            assignee_combo.addItem(f"{emp['avatar']} {emp['name']}", emp['id'])
        form_layout.addRow("Исполнитель:", assignee_combo)

        # Прогресс
        progress_spin = QSpinBox()
        progress_spin.setRange(0, 100)
        progress_spin.setValue(0)
        progress_spin.setSuffix("%")
        form_layout.addRow("Прогресс:", progress_spin)

        layout.addLayout(form_layout)

        layout.addSpacing(20)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                padding: 10px 30px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                padding: 10px 30px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Создаем новую задачу
            new_id = max([t.id for t in self.tasks]) + 1
            new_task = Task(
                id=new_id,
                title=title_edit.currentText(),
                description=desc_edit.currentText(),
                priority=priority_combo.currentText(),
                due_date=end_date.date().toPyDateTime(),
                created_date=start_date.date().toPyDateTime(),
                assignee=assignee_combo.currentData(),
                assignee_name=assignee_combo.currentText().split(' ', 1)[
                    1] if ' ' in assignee_combo.currentText() else assignee_combo.currentText(),
                column_id=1,
                column_name="To Do",
                progress=progress_spin.value()
            )
            new_task.project_id = self.current_project_id
            new_task.duration = (new_task.due_date - new_task.created_date).days

            self.tasks.append(new_task)
            self.load_tasks()

            QMessageBox.information(self, "Успешно", "Задача добавлена на диаграмму Ганта!")

    def edit_task_dialog(self):
        """Диалог редактирования сроков задачи"""
        selected = self.taskListWidget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Предупреждение",
                                "Выберите задачу для редактирования")
            return

        task_id = selected[0].data(Qt.ItemDataRole.UserRole)
        task = next((t for t in self.tasks if t.id == task_id), None)

        if not task:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"✏️ Редактирование: {task.title[:30]}")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E2A36;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QDateEdit {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(dialog)

        form_layout = QFormLayout()

        # Дата начала
        start_date = QDateEdit()
        start_date.setDate(QDate(
            task.created_date.year,
            task.created_date.month,
            task.created_date.day
        ))
        start_date.setCalendarPopup(True)
        form_layout.addRow("Дата начала:", start_date)

        # Дата окончания
        end_date = QDateEdit()
        end_date.setDate(QDate(
            task.due_date.year,
            task.due_date.month,
            task.due_date.day
        ))
        end_date.setCalendarPopup(True)
        form_layout.addRow("Дата окончания:", end_date)

        # Прогресс
        progress_spin = QSpinBox()
        progress_spin.setRange(0, 100)
        progress_spin.setValue(task.progress)
        progress_spin.setSuffix("%")
        form_layout.addRow("Прогресс:", progress_spin)

        layout.addLayout(form_layout)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Обновляем задачу
            task.created_date = start_date.date().toPyDateTime()
            task.due_date = end_date.date().toPyDateTime()
            task.duration = (task.due_date - task.created_date).days
            task.progress = progress_spin.value()

            self.load_tasks()
            QMessageBox.information(self, "Успешно", "Сроки задачи обновлены!")

    def export_gantt(self):
        """Экспорт диаграммы Ганта"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Экспорт диаграммы")
        msg.setText("📊 Диаграмма Ганта успешно экспортирована!")
        msg.setInformativeText(f"Файл: Gantt_{self.current_project_name}_{datetime.now().strftime('%Y%m%d')}.pdf")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1E2A36;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #862633;
            }
        """)
        msg.exec()

    def zoom_in(self):
        """Увеличение масштаба диаграммы"""
        if hasattr(self, 'ganttTable'):
            self.column_width = min(self.column_width + 20, 200)
            self.ganttTable.horizontalHeader().setDefaultSectionSize(self.column_width)

    def zoom_out(self):
        """Уменьшение масштаба диаграммы"""
        if hasattr(self, 'ganttTable'):
            self.column_width = max(self.column_width - 20, 40)
            self.ganttTable.horizontalHeader().setDefaultSectionSize(self.column_width)

    def change_scale(self, index):
        """Изменение масштаба отображения"""
        scales = {0: 80, 1: 120, 2: 200}
        if hasattr(self, 'ganttTable'):
            self.column_width = scales.get(index, 80)
            self.ganttTable.horizontalHeader().setDefaultSectionSize(self.column_width)

    def prev_period(self):
        """Предыдущий период"""
        if self.displayed_month > 1:
            self.displayed_month -= 1
        else:
            self.displayed_month = 12
            self.displayed_year -= 1
        self.update_timeline_label()
        self.update_gantt_chart()

    def next_period(self):
        """Следующий период"""
        if self.displayed_month < 12:
            self.displayed_month += 1
        else:
            self.displayed_month = 1
            self.displayed_year += 1
        self.update_timeline_label()
        self.update_gantt_chart()

    def go_to_today(self):
        """Переход к текущей дате"""
        self.current_date = datetime(2026, 2, 13)  # Тестовая дата
        self.displayed_month = self.current_date.month
        self.displayed_year = self.current_date.year
        self.update_timeline_label()
        self.update_gantt_chart()

    def update_timeline_label(self):
        """Обновление метки временной шкалы"""
        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }

        month_name = month_names.get(self.displayed_month, "Февраль")

        if hasattr(self, 'month_label'):
            self.month_label.setText(f"🗓️ {month_name} {self.displayed_year}")
        elif hasattr(self, 'label_6'):
            self.label_6.setText(f"🗓️ {month_name} {self.displayed_year}")

    def add_dependency_dialog(self):
        """Диалог добавления связи между задачами"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🔗 Добавить логическую связь")
        dialog.setMinimumWidth(450)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E2A36;
                color: white;
            }
            QLabel {
                color: white;
            }
            QComboBox {
                background-color: #1B232A;
                color: white;
                border: 2px solid #ccab6e;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(dialog)

        form_layout = QFormLayout()

        # Предшествующая задача
        from_combo = QComboBox()
        for task in self.tasks:
            if task.project_id == self.current_project_id:
                from_combo.addItem(f"{task.title[:30]}", task.id)
        form_layout.addRow("Предшествует:", from_combo)

        # Последующая задача
        to_combo = QComboBox()
        for task in self.tasks:
            if task.project_id == self.current_project_id:
                to_combo.addItem(f"{task.title[:30]}", task.id)
        form_layout.addRow("Зависит от:", to_combo)

        # Тип связи
        type_combo = QComboBox()
        type_combo.addItems(["Финиш-Старт", "Старт-Старт", "Финиш-Финиш", "Старт-Финиш"])
        form_layout.addRow("Тип связи:", type_combo)

        layout.addLayout(form_layout)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            from_id = from_combo.currentData()
            to_id = to_combo.currentData()

            from_task = next((t for t in self.tasks if t.id == from_id), None)
            to_task = next((t for t in self.tasks if t.id == to_id), None)

            if from_task and to_task:
                # Обновляем зависимость
                dep_text = f"{from_task.title[:15]}... → {to_task.title[:15]}... ({type_combo.currentText()})"
                if hasattr(self, 'dependency_label'):
                    self.dependency_label.setText(dep_text)
                elif hasattr(self, 'label_12'):
                    self.label_12.setText(dep_text)

                QMessageBox.information(self, "Успешно", "Связь между задачами добавлена!")

    def on_tasks_reordered(self):
        """Обработчик изменения порядка задач"""
        print("Порядок задач изменен")
        # В реальном приложении здесь была бы синхронизация с БД
        self.update_gantt_chart()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработчик входа перетаскивания"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Обработчик сброса перетаскивания"""
        # Здесь можно реализовать логику изменения сроков через drag-and-drop
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Planner - Диаграмма Ганта (Тестовые данные)")
        self.setGeometry(100, 100, 1600, 900)

        # Применение корпоративного стиля к главному окну
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F1A24;
            }
        """)

        # Создание и установка центрального виджета
        self.gantt_widget = GanttChartWidget()
        self.setCentralWidget(self.gantt_widget)

        # Создание меню (для полноты интерфейса)
        self.create_menu()

    def create_menu(self):
        """Создание меню приложения"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #17212B;
                color: white;
                border-bottom: 2px solid #D22730;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #D22730;
                border-radius: 5px;
            }
            QMenu {
                background-color: #1E2A36;
                color: white;
                border: 1px solid #ccab6e;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #D22730;
            }
        """)

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        export_action = QAction("📥 Экспорт диаграммы", self)
        export_action.triggered.connect(self.gantt_widget.export_gantt)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("🚪 Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Вид
        view_menu = menubar.addMenu("Вид")

        zoom_in_action = QAction("🔍 Увеличить", self)
        zoom_in_action.triggered.connect(self.gantt_widget.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("🔍 Уменьшить", self)
        zoom_out_action.triggered.connect(self.gantt_widget.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        """Показ информации о программе"""
        QMessageBox.about(self, "О программе",
                          "<h2 style='color: #ccab6e;'>Task Planner - Диаграмма Ганта</h2>"
                          "<p style='color: white;'>Версия: 1.0.0</p>"
                          "<p style='color: white;'>Корпоративная система управления проектами</p>"
                          "<p style='color: white;'>Разработано в корпоративных цветах: "
                          "<span style='color: #D22730;'>Красный</span>, "
                          "<span style='color: #ccab6e;'>Золотой</span></p>"
                          "<hr>"
                          "<p style='color: white;'>© 2026 Все права защищены</p>")


def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)

    # Установка глобального стиля
    app.setStyle('Fusion')

    # Создание и показ главного окна
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()