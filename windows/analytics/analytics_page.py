# windows/analytics/analytics_page.py

import os
from typing import List, Dict

from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QScrollArea,
    QVBoxLayout, QLabel, QFrame, QSizePolicy, QComboBox, QHBoxLayout, QLineEdit
)

from services.analytics_service.analytics_service import AnalyticsService
from windows.analytics.analytics_page_handlers import AnalyticsPageHandlers
from windows.analytics.analytics_page_views import AnalyticsPageViews


class AnalyticsPage(QWidget):
    """Страница аналитики - ТОЛЬКО UI"""

    # ⭐ Сигнал для внешнего поиска
    search_filter_changed = None  # Будет установлен в main_window

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
        self._employees_filtered_data = []  # Данные с учётом фильтров (отдел, период)
        self._employees_display_data = []  # Данные с учётом поиска (для отображения)
        self._themes_data = []
        self._themes_display_data = []
        self._projects_data = []
        self._projects_display_data = []
        self._is_loading = False
        self._current_search_text = ""
        self._current_tab_index = 0
        self._search_widget = None  # ⭐ Ссылка на виджет поиска

        # Фильтры
        self.department_filter = None
        self.rating_department_filter = None
        self.period_filter = None
        self._current_department_filter = "all"
        self._current_rating_department_filter = "all"
        self._current_period_filter = "all"

        self._setup_ui()
        self._setup_filters()

        # Подключаем сигнал смены вкладки
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

        if self.service:
            self.load_all_data()
        else:
            self._show_placeholder()

    def set_search_widget(self, search_widget: QLineEdit):
        """Устанавливает виджет поиска и подключает его сигналы"""
        self._search_widget = search_widget
        if search_widget:
            # ⭐ Подключаем сигнал изменения текста
            search_widget.textChanged.connect(self.apply_search_filter)
            # ⭐ Подключаем сигнал очистки (когда пользователь кликает на крестик)
            search_widget.textChanged.connect(self._on_search_text_changed)

    def _on_search_text_changed(self, text: str):
        """Обработчик изменения текста поиска"""
        # ⭐ Если текст стал пустым - сбрасываем
        if not text.strip():
            self.clear_search_filter()

    def apply_search_filter(self, query: str):
        """Применяет фильтр поиска ко всем вкладкам аналитики"""
        new_text = query.strip().lower()

        # ⭐ Если текст пустой - сбрасываем немедленно
        if not new_text:
            self.clear_search_filter()
            return

        # Если текст не изменился - ничего не делаем
        if new_text == self._current_search_text:
            return

        self._current_search_text = new_text
        self._apply_search_to_current_tab()

    def clear_search_filter(self):
        """Очищает фильтр поиска и восстанавливает все данные"""
        # ⭐ Если есть виджет поиска - очищаем его текст (избегаем рекурсии)
        if self._search_widget:
            self._search_widget.blockSignals(True)
            self._search_widget.setText("")
            self._search_widget.blockSignals(False)

        # ⭐ Сбрасываем текст поиска
        self._current_search_text = ""

        # ⭐ Восстанавливаем данные из отфильтрованных
        self._restore_display_data()

        # ⭐ Принудительно обновляем отображение
        self._display_current_tab_data()

        # ⭐ Дополнительно обновляем все вкладки для синхронизации
        self._refresh_all_tabs()

    def _refresh_all_tabs(self):
        """Обновляет все вкладки для синхронизации"""
        # Сохраняем текущую вкладку
        current_tab = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0

        # Обновляем все вкладки
        self.views.display_employees(self._employees_display_data)
        self.views.display_rating(self._employees_display_data)
        self.views.display_themes(self._themes_display_data)
        self.views.display_projects(self._projects_display_data)

        # Восстанавливаем текущую вкладку
        if hasattr(self, 'tabWidget'):
            self.tabWidget.setCurrentIndex(current_tab)

    def force_refresh_display(self):
        """Принудительно обновляет отображение (вызывается извне при проблемах)"""
        self._restore_display_data()
        self._display_current_tab_data()
        self.repaint()

    def _restore_display_data(self):
        """
        Восстанавливает данные для отображения из отфильтрованных данных
        (это данные с учётом фильтров отдела/периода, но без поиска)
        """
        self._employees_display_data = self._employees_filtered_data.copy()
        self._themes_display_data = self._themes_data.copy()
        self._projects_display_data = self._projects_data.copy()

    def get_filtered_count(self) -> int:
        """Возвращает количество найденных элементов на текущей вкладке"""
        if not self._current_search_text:
            return self._get_total_items_count()
        return self._count_filtered_items()

    def _get_total_items_count(self) -> int:
        """Возвращает общее количество элементов на текущей вкладке"""
        current_tab = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0

        if current_tab == 0:  # Рейтинг
            return len(self._employees_display_data)
        elif current_tab == 1:  # Сотрудники
            return len(self._employees_display_data)
        elif current_tab == 2:  # Темы
            return len(self._themes_display_data)
        elif current_tab == 3:  # Проекты
            return len(self._projects_display_data)
        return 0

    def _count_filtered_items(self) -> int:
        """Подсчитывает количество отфильтрованных элементов на текущей вкладке"""
        if not self._current_search_text:
            return self._get_total_items_count()

        current_tab = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0
        search_text = self._current_search_text

        if current_tab == 0:  # Рейтинг
            return len(self._filter_rating_data(search_text))
        elif current_tab == 1:  # Сотрудники
            return len(self._filter_employees_data(search_text))
        elif current_tab == 2:  # Темы
            return len(self._filter_themes_data(search_text))
        elif current_tab == 3:  # Проекты
            return len(self._filter_projects_data(search_text))
        return 0

    def _apply_search_to_current_tab(self):
        """Применяет поиск к текущей вкладке"""
        # ⭐ Если поиск пустой - просто показываем все данные
        if not self._current_search_text:
            self._display_current_tab_data()
            return

        current_tab = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0
        search_text = self._current_search_text

        if current_tab == 0:  # Рейтинг
            filtered = self._filter_rating_data(search_text)
            self.views.display_rating(filtered)
        elif current_tab == 1:  # Сотрудники
            filtered = self._filter_employees_data(search_text)
            self.views.display_employees(filtered)
        elif current_tab == 2:  # Темы
            filtered = self._filter_themes_data(search_text)
            self.views.display_themes(filtered)
        elif current_tab == 3:  # Проекты
            filtered = self._filter_projects_data(search_text)
            self.views.display_projects(filtered)

    def _display_current_tab_data(self):
        """Отображает все данные на текущей вкладке"""
        current_tab = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0

        if current_tab == 0:  # Рейтинг
            self.views.display_rating(self._employees_display_data)
        elif current_tab == 1:  # Сотрудники
            self.views.display_employees(self._employees_display_data)
        elif current_tab == 2:  # Темы
            self.views.display_themes(self._themes_display_data)
        elif current_tab == 3:  # Проекты
            self.views.display_projects(self._projects_display_data)

    def _filter_rating_data(self, search_text: str) -> List[Dict]:
        """Фильтрует данные рейтинга по поисковому запросу"""
        if not search_text:
            return self._employees_display_data

        result = []
        for emp in self._employees_display_data:
            if self._employee_matches_search(emp, search_text):
                result.append(emp)
        return result

    def _filter_employees_data(self, search_text: str) -> List[Dict]:
        """Фильтрует данные сотрудников по поисковому запросу"""
        if not search_text:
            return self._employees_display_data

        result = []
        for emp in self._employees_display_data:
            if self._employee_matches_search(emp, search_text):
                result.append(emp)
        return result

    def _filter_themes_data(self, search_text: str) -> List[Dict]:
        """Фильтрует данные тем по поисковому запросу"""
        if not search_text:
            return self._themes_display_data

        result = []
        for theme in self._themes_display_data:
            if self._theme_matches_search(theme, search_text):
                result.append(theme)
        return result

    def _filter_projects_data(self, search_text: str) -> List[Dict]:
        """Фильтрует данные проектов по поисковому запросу"""
        if not search_text:
            return self._projects_display_data

        result = []
        for project in self._projects_display_data:
            if self._project_matches_search(project, search_text):
                result.append(project)
        return result

    def load_all_data(self):
        """Загружает данные через сервис"""
        if not self.service:
            return

        self._is_loading = True

        try:
            self._employees_raw_data = self.service.get_all_employees_with_stats()
            self._employees_filtered_data = self._employees_raw_data.copy()
            self._employees_display_data = self._employees_filtered_data.copy()
            self._themes_data = self.service.get_themes_stats()
            self._themes_display_data = self._themes_data.copy()
            self._projects_data = self.service.get_projects_stats()
            self._projects_display_data = self._projects_data.copy()

            self._load_departments()

            self.views.display_employees(self._employees_display_data)
            self.views.display_rating(self._employees_display_data)
            self.views.display_themes(self._themes_display_data)
            self.views.display_projects(self._projects_display_data)

        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_loading = False

    def refresh(self):
        """Обновляет данные"""
        if self.service:
            self.load_all_data()
            # После обновления применяем текущий поиск
            if self._current_search_text:
                self._apply_search_to_current_tab()

    def _apply_employee_filter(self):
        """Применяет фильтр к сотрудникам"""
        if not self._employees_raw_data:
            return

        dept_id = self._current_department_filter
        if dept_id == "all":
            dept_id = None

        filtered = self.service.filter_employees_by_department(
            self._employees_raw_data,
            dept_id
        ) if self.service else self._employees_raw_data

        self._employees_filtered_data = filtered

        # ⭐ Если нет активного поиска или поиск пустой - обновляем отображение
        if not self._current_search_text:
            self._employees_display_data = filtered.copy()
            self.views.display_employees(filtered)
        else:
            self._employees_display_data = filtered.copy()
            self._apply_search_to_current_tab()

    def _apply_rating_filters(self):
        """Применяет все фильтры к рейтингу"""
        if not self._employees_raw_data:
            return

        filtered = self._employees_raw_data

        if self._current_period_filter and self._current_period_filter != "all":
            filtered = self.service.filter_employees_by_period(
                filtered,
                self._current_period_filter
            ) if self.service else filtered

        dept_id = self._current_rating_department_filter
        if dept_id and dept_id != "all":
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

        self._employees_filtered_data = filtered

        # ⭐ Если нет активного поиска или поиск пустой - обновляем отображение
        if not self._current_search_text:
            self._employees_display_data = filtered.copy()
            self.views.display_rating(filtered)
        else:
            self._employees_display_data = filtered.copy()
            self._apply_search_to_current_tab()

    def on_tab_changed(self, index: int):
        """Обработчик смены вкладки"""
        self._current_tab_index = index
        # ⭐ При смене вкладки всегда обновляем отображение
        if self._current_search_text:
            self._apply_search_to_current_tab()
        else:
            self._display_current_tab_data()

    def _employee_matches_search(self, emp: Dict, search_text: str) -> bool:
        """
        Проверяет, соответствует ли сотрудник поисковому запросу.
        Поиск по: имени, фамилии, должности, отделу, подразделению.
        """
        # Имя
        if search_text in emp.get("name", "").lower():
            return True
        # Фамилия
        if search_text in emp.get("last_name", "").lower():
            return True
        # Должность
        if search_text in emp.get("position", "").lower():
            return True
        # Отдел
        if search_text in emp.get("department", "").lower():
            return True
        # Подразделение
        if search_text in emp.get("subdivision", "").lower():
            return True
        # КПД (цифры)
        kpd = str(emp.get("kpd_percent", 0))
        if search_text in kpd:
            return True
        # Количество задач
        if search_text in str(emp.get("total_tasks", 0)):
            return True
        # Количество выполненных задач
        if search_text in str(emp.get("completed_tasks", 0)):
            return True
        # ID сотрудника
        if search_text in str(emp.get("id", "")):
            return True
        return False

    def _theme_matches_search(self, theme: Dict, search_text: str) -> bool:
        """
        Проверяет, соответствует ли тема поисковому запросу.
        Поиск по: названию темы, количеству задач, КПД.
        """
        # Название темы
        if search_text in theme.get("theme_name", "").lower():
            return True
        # Количество задач
        if search_text in str(theme.get("task_count", 0)):
            return True
        # Количество выполненных
        if search_text in str(theme.get("completed_count", 0)):
            return True
        # КПД
        kpd = str(int(theme.get("kpd", 0) * 100))
        if search_text in kpd:
            return True
        # Сотрудники по теме
        for emp in theme.get("employee_stats", []):
            if isinstance(emp, dict):
                if search_text in emp.get("employee_name", "").lower():
                    return True
        # Проекты по теме
        for proj in theme.get("project_stats", []):
            if isinstance(proj, dict):
                if search_text in proj.get("project_name", "").lower():
                    return True
        return False

    def _project_matches_search(self, project: Dict, search_text: str) -> bool:
        """
        Проверяет, соответствует ли проект поисковому запросу.
        Поиск по: названию, описанию, статусу, количеству задач.
        """
        # Название
        if search_text in project.get("name", "").lower():
            return True
        # Описание
        if search_text in project.get("description", "").lower():
            return True
        # Статус
        if search_text in project.get("status_display", "").lower():
            return True
        # Количество задач
        if search_text in str(project.get("total_tasks", 0)):
            return True
        # Количество активных задач
        if search_text in str(project.get("active_tasks", 0)):
            return True
        # Количество выполненных задач
        if search_text in str(project.get("completed_tasks", 0)):
            return True
        # Количество просроченных задач
        if search_text in str(project.get("overdue_tasks", 0)):
            return True
        # Сотрудники проекта
        for emp in project.get("employees", []):
            if isinstance(emp, dict):
                if search_text in emp.get("name", "").lower():
                    return True
        return False

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""
        self._setup_filters()
        self._reorder_tabs()
        self._setup_rating_tab()
        self._setup_employee_tab()
        self._setup_tab_container('themesTab', 'themesContainer', 'themesGrid')
        self._setup_tab_container('projectsTab', 'projectsContainer', 'projectsGrid')

        # ⭐ Подключаем сигнал смены вкладки
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def _setup_ui(self):
        """Загружает UI файл или создаёт программно"""
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "analytics", "analytics_page.ui")

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._setup_ui_from_file()
        else:
            self._create_ui_programmatically()

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

    def _setup_filters(self):
        """Настраивает фильтры"""
        self._setup_employee_filter()
        self._setup_rating_filter()
        self._setup_period_filter()

    def _setup_employee_filter(self):
        """Настраивает фильтр для сотрудников (ТОЛЬКО ВЫПАДАЮЩИЙ СПИСОК)"""
        if hasattr(self, 'departmentFilter_2'):
            self.department_filter = self.departmentFilter_2
            self.department_filter.clear()
            self.department_filter.addItem("Все отделы", "all")
            self.department_filter.setCurrentIndex(0)
            self.department_filter.currentIndexChanged.connect(self._on_employee_filter_changed)

    def _setup_rating_filter(self):
        """Настраивает фильтр для рейтинга (ТОЛЬКО ВЫПАДАЮЩИЙ СПИСОК)"""
        if hasattr(self, 'departmentFilter'):
            self.rating_department_filter = self.departmentFilter
            self.rating_department_filter.clear()
            self.rating_department_filter.addItem("Все отделы", "all")
            self.rating_department_filter.setCurrentIndex(0)
            self.rating_department_filter.currentIndexChanged.connect(self._on_rating_filter_changed)

    def _setup_period_filter(self):
        """Настраивает фильтр периода"""
        if hasattr(self, 'periodFilter'):
            self.period_filter = self.periodFilter
            self.period_filter.clear()
            for option in self.service.get_period_options() if self.service else []:
                self.period_filter.addItem(option["name"], option["value"])
            self.period_filter.setCurrentIndex(0)
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
        return "all"

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