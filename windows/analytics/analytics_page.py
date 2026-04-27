# windows/analytics/analytics_page.py

import os
from typing import List, Dict, Any
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QScrollArea,
    QVBoxLayout, QLabel, QFrame, QSizePolicy, QMessageBox
)

from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.theme.theme_card import ThemeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from services.analytics_service import AnalyticsService


class AnalyticsPage(QWidget):
    """Страница аналитики с вкладками: Сотрудники, Темы, Проекты"""

    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "analytics", "analytics_page.ui"
        )

        # Проверяем существование файла
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._setup_ui_from_file()
        else:
            print(f"⚠️ UI файл не найден: {ui_path}, создаем страницу программно")
            self._create_ui_programmatically()

        # Инициализируем сервис
        self.session = session
        self.service = AnalyticsService(session) if session else None

        # Кэш для данных
        self.employees_data = []
        self.themes_data = []
        self.projects_data = []

        # Загружаем данные
        if self.service:
            self.load_all_data()
        else:
            print("⚠️ Сервис аналитики не инициализирован (нет сессии)")
            self._show_placeholder()

    # windows/analytics/analytics_page.py

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""
        # Для вкладки Сотрудники
        if hasattr(self, 'employeesContainer'):
            if self.employeesContainer.layout():
                self.employees_grid = self.employeesContainer.layout()
            else:
                self.employees_grid = QGridLayout(self.employeesContainer)
                self.employees_grid.setHorizontalSpacing(15)
                self.employees_grid.setVerticalSpacing(15)
        else:
            self.employeesContainer = QWidget()
            self.employees_grid = QGridLayout(self.employeesContainer)
            self.employees_grid.setHorizontalSpacing(15)
            self.employees_grid.setVerticalSpacing(15)
            if hasattr(self, 'employeesScroll'):
                self.employeesScroll.setWidget(self.employeesContainer)

        # 🔧 ИСПРАВЛЕНИЕ: Для вкладки Темы - удаляем placeholder и создаем контейнер
        self._setup_tab_from_placeholder('themesTab', 'themesPlaceholder', 'themesContainer', 'themesGrid')

        # 🔧 ИСПРАВЛЕНИЕ: Для вкладки Проекты - удаляем placeholder и создаем контейнер
        self._setup_tab_from_placeholder('projectsTab', 'projectsPlaceholder', 'projectsContainer', 'projectsGrid')

    def _setup_tab_from_placeholder(self, tab_name, placeholder_name, container_name, grid_name):
        """Настраивает вкладку, заменяя placeholder на контейнер с grid"""
        tab = getattr(self, tab_name, None)
        if not tab:
            print(f"⚠️ Вкладка {tab_name} не найдена")
            return

        # Удаляем placeholder, если он есть
        placeholder = getattr(self, placeholder_name, None)
        if placeholder:
            placeholder.deleteLater()
            # Удаляем атрибут, чтобы не было конфликтов
            delattr(self, placeholder_name)

        # Очищаем вкладку
        old_layout = tab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            tab.setLayout(layout)

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        # Сохраняем ссылки
        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

        print(f"✅ Создан контейнер для вкладки {tab_name}: {grid_name}")

    def _setup_tab_container(self, tab_name, container_name, grid_name):
        """Настраивает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            print(f"⚠️ Вкладка {tab_name} не найдена")
            return

        # Очищаем вкладку
        old_layout = tab.layout()
        if old_layout:
            # Удаляем все виджеты из старого layout
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            # Создаем новый layout
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            tab.setLayout(layout)

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        # Сохраняем ссылки
        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

        print(f"✅ Создан контейнер для вкладки {tab_name}: {grid_name}")

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("AnalyticsPage")
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        self.titleLabel = QLabel("Аналитика / Навыки")
        self.titleLabel.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1B232A;
            padding: 10px 0;
        """)
        layout.addWidget(self.titleLabel)

        # Tab Widget
        self.tabWidget = QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabBar::tab {
                background-color: white;
                color: #666;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                font-weight: bold;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #1B232A;
                color: white;
                border-color: #1B232A;
            }
            QTabBar::tab:hover:!selected {
                background-color: #F0F0F0;
            }
            QTabWidget::pane {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 0px 8px 8px 8px;
                margin-top: -1px;
            }
        """)

        # Вкладка Сотрудники
        self._add_tab("Сотрудники", "employeesTab", "employeesScroll", "employeesContainer", "employeesGrid")

        # Вкладка Темы
        self._add_tab("Темы", "themesTab", "themesScroll", "themesContainer", "themesGrid")

        # Вкладка Проекты
        self._add_tab("Проекты", "projectsTab", "projectsScroll", "projectsContainer", "projectsGrid")

        layout.addWidget(self.tabWidget)

    def _add_tab(self, title, tab_name, scroll_name, container_name, grid_name):
        """Добавляет вкладку программно"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)

        self.tabWidget.addTab(tab, title)

        setattr(self, tab_name, tab)
        setattr(self, scroll_name, scroll)
        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _show_placeholder(self):
        """Показывает заглушку при отсутствии данных"""
        for grid_attr in ['employeesGrid', 'themesGrid', 'projectsGrid']:
            grid = getattr(self, grid_attr, None)
            if grid:
                # Очищаем grid
                self._clear_grid(grid)

                label = QLabel("Нет данных для отображения")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
                grid.addWidget(label, 0, 0)

    def _clear_grid(self, grid):
        """Очищает grid layout"""
        if not grid:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        """Рекурсивно очищает layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def load_all_data(self):
        """Загружает все данные из БД"""
        if not self.service:
            return

        try:
            # Загружаем сотрудников
            self.employees_data = self.service.get_all_employees_with_stats()
            print(f"📊 Загружено сотрудников: {len(self.employees_data)}")

            # Загружаем темы
            self.themes_data = self.service.get_themes_stats()
            print(f"📊 Загружено тем: {len(self.themes_data)}")

            # Загружаем проекты
            self.projects_data = self.service.get_projects_stats()
            print(f"📊 Загружено проектов: {len(self.projects_data)}")

            # Отображаем данные
            self.populate_employees_tab()
            self.populate_themes_tab()

            # 🔧 ПРОВЕРЯЕМ СУЩЕСТВОВАНИЕ projectsGrid
            print(
                f"🔍 Проверка projectsGrid: hasattr={hasattr(self, 'projectsGrid')}, value={getattr(self, 'projectsGrid', None)}")

            self.populate_projects_tab()

        except Exception as e:
            print(f"❌ Ошибка при загрузке данных аналитики: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}")

    def  populate_employees_tab(self):
        """Заполняет вкладку сотрудников"""
        # Проверяем наличие employeesGrid
        if not hasattr(self, 'employeesGrid') or self.employeesGrid is None:
            print("❌ employeesGrid не найден, создаем...")
            # Пытаемся найти или создать employeesContainer
            if hasattr(self, 'employeesContainer'):
                if self.employeesContainer.layout():
                    self.employeesGrid = self.employeesContainer.layout()
                else:
                    self.employeesGrid = QGridLayout(self.employeesContainer)
                    self.employeesGrid.setHorizontalSpacing(15)
                    self.employeesGrid.setVerticalSpacing(15)
            else:
                print("❌ Не удалось создать employeesGrid")
                return

        # Очищаем контейнер
        self._clear_grid(self.employeesGrid)

        if not self.employees_data:
            label = QLabel("Нет данных о сотрудниках")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
            self.employeesGrid.addWidget(label, 0, 0)
            return

        row = col = 0
        max_cols = 3

        for emp_data in self.employees_data:
            card = EmployeeCard(emp_data)
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            self.employeesGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.employeesGrid.setRowStretch(row + 1, 1)
        print(f"✅ Отображено {len(self.employees_data)} сотрудников")

    def populate_themes_tab(self):
        """Заполняет вкладку тем"""
        if not hasattr(self, 'themesGrid') or self.themesGrid is None:
            print("❌ themesGrid не найден")
            return

        self._clear_grid(self.themesGrid)

        if not self.themes_data:
            label = QLabel("Нет данных о темах")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
            self.themesGrid.addWidget(label, 0, 0)
            return

        row = col = 0
        max_cols = 3

        for theme_data in self.themes_data:
            card = ThemeCard(theme_data)
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            self.themesGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.themesGrid.setRowStretch(row + 1, 1)
        print(f"✅ Отображено {len(self.themes_data)} тем")

    def populate_projects_tab(self):
        """Заполняет вкладку проектов"""
        if not hasattr(self, 'projectsGrid') or self.projectsGrid is None:
            print("❌ projectsGrid не найден")
            return

        self._clear_grid(self.projectsGrid)

        if not self.projects_data:
            label = QLabel("Нет данных о проектах")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
            self.projectsGrid.addWidget(label, 0, 0)
            return

        row = col = 0
        max_cols = 3

        for proj_data in self.projects_data:
            # Показываем только активные проекты (не архивные)
            if not proj_data.get("is_archived", False):
                card = ProjectCard(proj_data)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                self.projectsGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        self.projectsGrid.setRowStretch(row + 1, 1)
        print(f"✅ Отображено проектов")

    def refresh(self):
        """Обновляет все данные"""
        if self.service:
            self.load_all_data()