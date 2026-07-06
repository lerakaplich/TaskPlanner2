# windows/analytics/analytics_page.py

import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QScrollArea,
    QVBoxLayout, QLabel, QFrame, QSizePolicy, QComboBox, QHBoxLayout
)

from services.analytics_service.analytics_service import AnalyticsService
from windows.analytics.analytics_page_handlers import AnalyticsPageHandlers
from windows.analytics.analytics_page_views import AnalyticsPageViews


class AnalyticsPage(QWidget):
    """Страница аналитики - ТОЛЬКО UI"""

    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        # Инициализация
        self.session = session
        self.service = AnalyticsService(session) if session else None

        # Контроллеры и обработчики
        self.handlers = AnalyticsPageHandlers(self)
        self.views = AnalyticsPageViews(self)

        # Данные (будут загружены через сервис)
        self._employees_raw_data = []
        self._employees_data = []
        self._themes_data = []
        self._projects_data = []
        self._is_loading = False

        # Фильтры
        self.department_filter = None
        self.rating_department_filter = None
        self.period_filter = None
        self._current_department_filter = "all"
        self._current_rating_department_filter = "all"
        self._current_period_filter = "all"

        self._setup_ui()
        self._setup_filters()
        # self._setup_containers()  # УДАЛИТЬ - контейнеры создаются в _setup_ui_from_file

        if self.service:
            self.load_all_data()
        else:
            self._show_placeholder()

    def _setup_ui(self):
        """Загружает UI файл или создаёт программно"""
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "analytics", "analytics_page.ui")

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._setup_ui_from_file()
        else:
            self._create_ui_programmatically()

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""
        self._setup_filters()
        self._reorder_tabs()
        self._setup_rating_tab()
        self._setup_employee_tab()
        self._setup_tab_container('themesTab', 'themesContainer', 'themesGrid')
        self._setup_tab_container('projectsTab', 'projectsContainer', 'projectsGrid')

    def _reorder_tabs(self):
        """Переупорядочивает вкладки"""
        if not hasattr(self, 'tabWidget'):
            return

        tabs = {}
        for i in range(self.tabWidget.count()):
            text = self.tabWidget.tabText(i)
            tabs[text] = self.tabWidget.widget(i)

        self.tabWidget.clear()

        order = ["Рейтинг сотрудников", "Сотрудники", "Темы", "Проекты"]
        for text in order:
            if text in tabs and tabs[text]:
                self.tabWidget.addTab(tabs[text], text)

        self.tabWidget.setCurrentIndex(0)

    def _setup_employee_tab(self):
        """Настраивает вкладку сотрудников"""
        if hasattr(self, 'employeesContainer'):
            self.employees_grid = self.employeesContainer.layout()
            if self.employees_grid is None:
                self.employees_grid = QGridLayout(self.employeesContainer)
                self.employees_grid.setHorizontalSpacing(15)
                self.employees_grid.setVerticalSpacing(15)
                self.employees_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.employeesContainer.setLayout(self.employees_grid)

    def _setup_tab_container(self, tab_name, container_name, grid_name):
        """Настраивает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            return

        layout = tab.layout()
        if not layout:
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            tab.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _setup_rating_tab(self):
        """Настраивает вкладку рейтинга"""
        if not hasattr(self, 'ratingTab'):
            return

        if hasattr(self, 'ratingContainer'):
            self.rating_layout = self.ratingContainer.layout()
            if self.rating_layout is None:
                self.rating_layout = QVBoxLayout(self.ratingContainer)
                self.rating_layout.setSpacing(10)
                self.rating_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.ratingContainer.setLayout(self.rating_layout)

    # ==================== ФИЛЬТРЫ ====================

    def _setup_filters(self):
        """Настраивает фильтры"""
        self._setup_employee_filter()
        self._setup_rating_filter()
        self._setup_period_filter()

    def _setup_employee_filter(self):
        """Настраивает фильтр для сотрудников"""
        if hasattr(self, 'departmentFilter_2'):
            self.department_filter = self.departmentFilter_2
            self.department_filter.clear()
            self.department_filter.addItem("Все отделы", "all")
            self.department_filter.setEditable(True)
            self.department_filter.setCurrentIndex(0)
            self.department_filter.currentIndexChanged.connect(self._on_employee_filter_changed)

    def _setup_rating_filter(self):
        """Настраивает фильтр для рейтинга"""
        if hasattr(self, 'departmentFilter'):
            self.rating_department_filter = self.departmentFilter
            self.rating_department_filter.clear()
            self.rating_department_filter.addItem("Все отделы", "all")
            self.rating_department_filter.setEditable(True)
            self.rating_department_filter.setCurrentIndex(0)  # ✅ Устанавливаем "Все отделы"
            self.rating_department_filter.currentIndexChanged.connect(self._on_rating_filter_changed)

    def _setup_period_filter(self):
        """Настраивает фильтр периода"""
        if hasattr(self, 'periodFilter'):
            self.period_filter = self.periodFilter
            self.period_filter.clear()
            for option in self.service.get_period_options() if self.service else []:
                self.period_filter.addItem(option["name"], option["value"])
            # ❌ Убираем editable - запрещаем ввод текста
            # self.period_filter.setEditable(True)
            self.period_filter.setCurrentIndex(0)  # ✅ Устанавливаем "Все время"
            self.period_filter.currentIndexChanged.connect(self._on_period_filter_changed)

    def _on_employee_filter_changed(self, text: str):
        """Фильтр по отделу для сотрудников"""
        if self._is_loading:
            return
        self._current_department_filter = self._get_filter_value(self.department_filter, text)
        self._apply_employee_filter()

    def _on_rating_filter_changed(self, text: str):
        """Фильтр по отделу для рейтинга"""
        if self._is_loading:
            return
        self._current_rating_department_filter = self._get_filter_value(self.rating_department_filter, text)
        self._apply_rating_filters()

    def _on_period_filter_changed(self, text: str):
        """Фильтр по периоду для рейтинга"""
        if self._is_loading:
            return
        self._current_period_filter = self._get_filter_value(self.period_filter, text)
        self._apply_rating_filters()

    def _get_filter_value(self, combo, text: str):
        """Получает значение фильтра"""
        current_data = combo.currentData()
        if current_data is not None:
            # Если это строка вида "dept_X", извлекаем ID
            if isinstance(current_data, str) and current_data.startswith("dept_"):
                try:
                    return int(current_data.split("_")[1])
                except (ValueError, IndexError):
                    return "all"
            return current_data
        return "all"  # Всегда возвращаем "all" или число

    def _apply_employee_filter(self):
        """Применяет фильтр к сотрудникам"""
        if not self._employees_raw_data:
            return

        # Получаем ID отдела
        dept_id = self._current_department_filter
        if dept_id == "all":
            dept_id = None

        filtered = self.service.filter_employees_by_department(
            self._employees_raw_data,
            dept_id
        ) if self.service else self._employees_raw_data

        self._employees_data = filtered
        self.views.display_employees(filtered)

    def _apply_rating_filters(self):
        """Применяет все фильтры к рейтингу"""
        if not self._employees_raw_data:
            return

        filtered = self._employees_raw_data

        # Фильтр по периоду
        if self._current_period_filter and self._current_period_filter != "all":
            filtered = self.service.filter_employees_by_period(
                filtered,
                self._current_period_filter
            ) if self.service else filtered

        # Фильтр по отделу
        dept_id = self._current_rating_department_filter
        if dept_id and dept_id != "all":
            # Убеждаемся, что это число
            if isinstance(dept_id, str) and dept_id.startswith("dept_"):
                try:
                    dept_id = int(dept_id.split("_")[1])
                except (ValueError, IndexError):
                    dept_id = None
            if dept_id:
                filtered = self.service.filter_employees_by_department(
                    filtered,
                    dept_id
                ) if self.service else filtered

        self.views.display_rating(filtered)

    def load_all_data(self):
        """Загружает данные через сервис"""
        if not self.service:
            return

        self._is_loading = True

        try:
            self._employees_raw_data = self.service.get_all_employees_with_stats()
            self._employees_data = self._employees_raw_data.copy()
            self._themes_data = self.service.get_themes_stats()
            self._projects_data = self.service.get_projects_stats()

            self._load_departments()

            self.views.display_employees(self._employees_data)
            self.views.display_rating(self._employees_data)
            self.views.display_themes(self._themes_data)
            self.views.display_projects(self._projects_data)

        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_loading = False

    def _load_departments(self):
        """Загружает отделы в фильтры"""
        if not self.service:
            return

        departments = self.service.get_departments_list()

        for combo in [self.department_filter, self.rating_department_filter]:
            if combo:
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("Все отделы", "all")
                for dept in departments:
                    combo.addItem(dept["name"], f"dept_{dept['id']}")
                combo.blockSignals(False)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _show_placeholder(self):
        """Показывает заглушку"""
        for grid_attr in ['employees_grid', 'themesGrid', 'projectsGrid']:
            grid = getattr(self, grid_attr, None)
            if grid:
                self.views._clear_grid(grid)
                label = QLabel("Нет данных для отображения")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
                grid.addWidget(label, 0, 0)

    def showEvent(self, event):
        """Обновляет при показе"""
        super().showEvent(event)
        QTimer.singleShot(100, self.refresh)

    def refresh(self):
        """Обновляет данные"""
        if self.service:
            self.load_all_data()

    def _create_ui_programmatically(self):
        """Создает UI программно (только если UI файл не найден)"""

        self.setObjectName("AnalyticsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.titleLabel = QLabel("Аналитика / Навыки")
        self.titleLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #1B232A; padding: 10px 0;")
        layout.addWidget(self.titleLabel)

        self.tabWidget = QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabBar::tab { background-color: white; color: #666; padding: 12px 20px;
                margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px;
                border: 1px solid #E0E0E0; border-bottom: none; font-weight: bold; font-size: 14px; }
            QTabBar::tab:selected { background-color: #1B232A; color: white; }
            QTabWidget::pane { background-color: white; border: 1px solid #E0E0E0;
                border-radius: 0px 8px 8px 8px; margin-top: -1px; }
        """)

        self._add_tab("Рейтинг", "ratingTab", "ratingScroll", "ratingContainer", "ratingGrid")
        self._add_tab("Сотрудники", "employeesTab", "employeesScroll", "employeesContainer", "employeesGrid")
        self._add_tab("Темы", "themesTab", "themesScroll", "themesContainer", "themesGrid")
        self._add_tab("Проекты", "projectsTab", "projectsScroll", "projectsContainer", "projectsGrid")

        layout.addWidget(self.tabWidget)
        self.tabWidget.setCurrentIndex(0)