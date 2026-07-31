# windows/gantt/gantt_widget.py

import os
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidgetItem,
    QDialog, QMessageBox, QPushButton, QComboBox, QFrame, QGroupBox, QScrollArea, QTabWidget
)
from PyQt6 import uic

from sqlalchemy.orm import Session

from services.gantt_service.gantt_service import GanttService


class GanttWidget(QWidget):
    """Основной виджет диаграммы Ганта - ТОЛЬКО UI"""

    def __init__(self, session: Session, current_user_id: int = None, project_service=None, permission_service=None,
                 parent=None):
        super().__init__(parent)

        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service
        self.permission_service = permission_service
        self._first_show = True
        self._dont_show_link_dialog = False
        self._current_project_filter = "all"
        self._current_executor_filter = "all"

        # Инициализация сервиса
        self._service = GanttService(session, current_user_id, project_service, permission_service)

        # Инициализация UI компонентов
        self.gantt_canvas = None
        self.calendar_widget = None
        self.projectFilter = None
        self.executorFilter = None
        self.periodFilter = None
        self.projectsTree = None
        self.addTaskButton = None
        self.createLinkButton = None
        self.btnExport = None
        self.tabWidget = None

        # Инициализация обработчиков и представлений
        from windows.gantt.gantt_widget_handlers import GanttWidgetHandlers
        from windows.gantt.gantt_widget_views import GanttWidgetViews

        self._handlers = GanttWidgetHandlers(self)
        self._views = GanttWidgetViews(self)

        self._setup_ui()
        self._connect_signals()
        self._setup_permission_ui()

    # ==========================================================
    # ПРАВА ДОСТУПА
    # ==========================================================

    def _setup_permission_ui(self):
        if hasattr(self, 'addTaskButton') and self.addTaskButton:
            self.addTaskButton.setVisible(self._service.can_create_task())

        if hasattr(self, 'createLinkButton') and self.createLinkButton:
            self.createLinkButton.setVisible(self._service.can_create_link())

        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.setVisible(self._service.can_export())

    # ==========================================================
    # ЖИЗНЕННЫЙ ЦИКЛ
    # ==========================================================

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(10, self._handlers.load_initial_data)
        else:
            QTimer.singleShot(10, self._handlers.full_reload)

    # ==========================================================
    # НАСТРОЙКА UI
    # ==========================================================

    def _setup_ui(self) -> None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        ui_path = os.path.join(project_root, "ui", "gantt", "gantt_widget.ui")

        if not os.path.exists(ui_path):
            self._create_ui_programmatically()
        else:
            uic.loadUi(ui_path, self)
            self._setup_loaded_ui()
            QTimer.singleShot(100, self._setup_priorities)

    def _create_ui_programmatically(self) -> None:
        from PyQt6.QtWidgets import QTreeWidget
        from windows.gantt.gantt_canvas import GanttCanvas
        from windows.gantt.calendar_widget import CalendarWidget

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Левая панель
        left_panel = QFrame()
        left_panel.setFixedWidth(300)
        left_panel.setStyleSheet("background-color: #F8F9FA; border-right: 1px solid #E8E8E8;")
        left_layout = QVBoxLayout(left_panel)

        title_label = QLabel("📊 Диаграмма Ганта")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 15px;")
        left_layout.addWidget(title_label)

        # Фильтры
        filters_group = QFrame()
        filters_group.setStyleSheet("background-color: white; border-radius: 10px; margin: 10px;")
        filters_layout = QVBoxLayout(filters_group)

        filters_layout.addWidget(QLabel("📁 Проект:"))
        self.projectFilter = QComboBox()
        self.projectFilter.addItem("Все проекты", "all")
        filters_layout.addWidget(self.projectFilter)

        filters_layout.addWidget(QLabel("👤 Исполнитель:"))
        self.executorFilter = QComboBox()
        self.executorFilter.addItem("Все исполнители", "all")
        filters_layout.addWidget(self.executorFilter)

        self.addTaskButton = QPushButton("➕ Добавить задачу")
        self.createLinkButton = QPushButton("🔗 Создать связь")
        self.btnExport = QPushButton("📎 Экспорт")
        filters_layout.addWidget(self.addTaskButton)
        filters_layout.addWidget(self.createLinkButton)
        filters_layout.addWidget(self.btnExport)

        left_layout.addWidget(filters_group)

        # Легенда приоритетов
        legend_group = QFrame()
        legend_group.setStyleSheet("background-color: white; border-radius: 10px; margin: 10px;")
        legend_layout = QVBoxLayout(legend_group)
        legend_layout.addWidget(QLabel("🎨 Приоритеты:"))
        self.prioritiesLayout = QVBoxLayout()
        legend_layout.addLayout(self.prioritiesLayout)
        left_layout.addWidget(legend_group)

        # Дерево проектов
        self.projectsTree = QTreeWidget()
        self.projectsTree.setHeaderLabel("Задачи")
        self.projectsTree.setStyleSheet("""
            QTreeWidget { border: none; background-color: transparent; }
            QTreeWidget::item { padding: 5px; }
        """)
        left_layout.addWidget(self.projectsTree)
        left_layout.addStretch()

        # Правая панель
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Период:"))
        self.periodFilter = QComboBox()
        self.periodFilter.addItems(["Неделя", "Месяц", "Квартал", "Год", "Выбрать период"])
        top_bar.addWidget(self.periodFilter)
        top_bar.addStretch()
        right_layout.addLayout(top_bar)

        # Вкладки
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(QWidget(), "Диаграмма Ганта")
        self.tabWidget.addTab(QWidget(), "Календарь")
        right_layout.addWidget(self.tabWidget)

        # Настройка вкладки Диаграмма Ганта
        gantt_tab = self.tabWidget.widget(0)
        gantt_tab.setLayout(QVBoxLayout())
        gantt_scroll = QScrollArea()
        gantt_scroll.setWidgetResizable(True)
        gantt_tab.layout().addWidget(gantt_scroll)

        self.gantt_canvas = GanttCanvas(self._service)
        gantt_scroll.setWidget(self.gantt_canvas)

        # Настройка вкладки Календарь
        calendar_tab = self.tabWidget.widget(1)
        calendar_tab.setLayout(QVBoxLayout())
        calendar_tab.layout().setContentsMargins(0, 0, 0, 0)
        calendar_tab.layout().setSpacing(0)

        self.calendar_widget = CalendarWidget(self._service)
        calendar_tab.layout().addWidget(self.calendar_widget)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        self._setup_priorities()

    def _setup_loaded_ui(self) -> None:
        from windows.gantt.gantt_canvas import GanttCanvas
        from windows.gantt.calendar_widget import CalendarWidget

        self.gantt_canvas = GanttCanvas(self._service)

        if hasattr(self, 'ganttScrollArea'):
            gantt_layout = self.ganttScrollArea.layout()
            if gantt_layout is None:
                gantt_layout = QVBoxLayout(self.ganttScrollArea)
                self.ganttScrollArea.setLayout(gantt_layout)

            old_widget = self.ganttScrollArea.widget()
            if old_widget and old_widget != self.gantt_canvas:
                gantt_layout.removeWidget(old_widget)
                old_widget.deleteLater()

            gantt_layout.addWidget(self.gantt_canvas)
            self.ganttScrollArea.setWidget(self.gantt_canvas)

        # Календарь
        self.calendar_widget = CalendarWidget(self._service)

        calendar_tab = self.findChild(QWidget, "calendarTab")
        if calendar_tab:
            tab_layout = calendar_tab.layout()
            if tab_layout is None:
                tab_layout = QVBoxLayout(calendar_tab)
                tab_layout.setContentsMargins(0, 0, 0, 0)
                tab_layout.setSpacing(0)
                calendar_tab.setLayout(tab_layout)
            else:
                while tab_layout.count():
                    item = tab_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            tab_layout.addWidget(self.calendar_widget)

        placeholder = self.findChild(QLabel, "calendarPlaceholder")
        if placeholder:
            placeholder.hide()
            placeholder.deleteLater()

    def _setup_priorities(self) -> None:
        priorities = [
            ("Критический", "#D22730"),
            ("Высокий", "#ccab6e"),
            ("Средний", "#1B232A"),
            ("Низкий", "#998664"),
        ]

        container = self.findChild(QGroupBox, "prioritiesGroup")
        if not container:
            return

        container.setVisible(True)
        container.setMinimumHeight(80)
        container.setMaximumHeight(120)

        layout = container.layout()
        if layout is None:
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(20)
            container.setLayout(layout)
        else:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for name, color in priorities:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            indicator = QLabel()
            indicator.setFixedSize(12, 12)
            indicator.setStyleSheet(f"""
                background-color: {color};
                border-radius: 6px;
                border: 1px solid rgba(0,0,0,0.1);
            """)
            item_layout.addWidget(indicator)

            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 12px; color: #1B232A; font-weight: normal;")
            item_layout.addWidget(name_label)

            layout.addWidget(item_widget)

        layout.addStretch()
        container.updateGeometry()

    # ==========================================================
    # ПОДКЛЮЧЕНИЕ СИГНАЛОВ
    # ==========================================================

    def _connect_signals(self) -> None:
        if hasattr(self, 'addTaskButton') and self.addTaskButton:
            self.addTaskButton.clicked.connect(self._handlers.on_add_task)
        if hasattr(self, 'createLinkButton') and self.createLinkButton:
            self.createLinkButton.clicked.connect(self._handlers.on_create_link)
        if hasattr(self, 'periodFilter') and self.periodFilter:
            self.periodFilter.currentTextChanged.connect(self._handlers.on_period_changed)
        if hasattr(self, 'projectFilter') and self.projectFilter:
            self.projectFilter.currentTextChanged.connect(self._handlers.on_project_filter_changed)
        if hasattr(self, 'executorFilter') and self.executorFilter:
            self.executorFilter.currentTextChanged.connect(self._handlers.on_executor_filter_changed)
        if hasattr(self, 'projectsTree') and self.projectsTree:
            self.projectsTree.itemClicked.connect(self._handlers.on_project_item_clicked)
        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.clicked.connect(self._handlers.on_export_clicked)

        if hasattr(self, 'gantt_canvas') and self.gantt_canvas:
            self.gantt_canvas.task_moved_signal.connect(self._handlers.on_task_moved)
            self.gantt_canvas.link_created_signal.connect(self._handlers.on_link_created)

        if hasattr(self, 'calendar_widget') and self.calendar_widget:
            self.calendar_widget.task_clicked.connect(self._handlers.on_calendar_task_clicked)


    def _refresh_ui(self):
        self._views.refresh_ui()

    def _apply_filters(self):
        self._views.apply_filters()

    def _load_initial_data(self):
        self._handlers.load_initial_data()

    def _full_reload(self):
        self._handlers.full_reload()