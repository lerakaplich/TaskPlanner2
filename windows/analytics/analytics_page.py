# windows/analytics/analytics_page.py

import os
from typing import List, Dict, Any
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QScrollArea,
    QVBoxLayout, QLabel, QFrame, QSizePolicy, QMessageBox
)

from services.analytics_service.analytics_service import AnalyticsService
from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.theme.theme_card import ThemeCard
from windows.analytics.projects.project_card_analytics import ProjectCard

class AnalyticsPage(QWidget):
    """Страница аналитики - только отображение, логика в сервисе"""

    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        # Инициализируем сервис
        self.session = session
        self.service = AnalyticsService(session) if session else None

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "analytics", "analytics_page.ui"
        )

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._setup_ui_from_file()
        else:
            self._create_ui_programmatically()

        # Кэш для данных
        self._employees_data = []
        self._themes_data = []
        self._projects_data = []

        # Загружаем данные
        if self.service:
            self.load_all_data()
        else:
            self._show_placeholder()

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""

        # Для вкладки Сотрудники - используем существующие контейнеры из UI
        if hasattr(self, 'employeesContainer'):
            # Получаем существующий grid layout
            self.employees_grid = self.employeesContainer.layout()
            if self.employees_grid is None:
                # Если layout нет, создаем новый
                self.employees_grid = QGridLayout(self.employeesContainer)
                self.employees_grid.setHorizontalSpacing(15)
                self.employees_grid.setVerticalSpacing(15)
                self.employees_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.employeesContainer.setLayout(self.employees_grid)
            print("✅ Настроен employees_grid")
        else:
            print("❌ employeesContainer не найден в UI")
            # Создаем принудительно
            self._create_employees_container()

        # Для вкладки Темы - создаем контейнер принудительно, так как в UI его нет
        self._setup_tab_container_force('themesTab', 'themesContainer', 'themesGrid')

        # Для вкладки Проекты - создаем контейнер принудительно
        self._setup_tab_container_force('projectsTab', 'projectsContainer', 'projectsGrid')

    def _setup_tab_container_force(self, tab_name, container_name, grid_name):
        """Принудительно создает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            print(f"❌ {tab_name} не найден")
            return

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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        setattr(self, container_name, container)
        setattr(self, grid_name, grid)
        print(f"✅ Создан контейнер для {tab_name}")

    def _create_employees_container(self):
        """Создает контейнер для сотрудников принудительно"""
        if not hasattr(self, 'employeesTab'):
            print("❌ employeesTab не найден")
            return

        # Очищаем вкладку
        old_layout = self.employeesTab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.employeesTab)
            layout.setContentsMargins(15, 15, 15, 15)
            self.employeesTab.setLayout(layout)

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
        self.employees_grid = QGridLayout(container)
        self.employees_grid.setHorizontalSpacing(15)
        self.employees_grid.setVerticalSpacing(15)
        self.employees_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        self.employeesTab.layout().addWidget(scroll)

        self.employeesContainer = container
        print("✅ Контейнер для сотрудников создан принудительно")

    def _setup_tab_container(self, tab_name, container_name, grid_name):
        """Настраивает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            return

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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _create_ui_programmatically(self):
        """Создает UI программно"""
        self.setObjectName("AnalyticsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        self.titleLabel = QLabel("Аналитика / Навыки")
        self.titleLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #1B232A; padding: 10px 0;")
        layout.addWidget(self.titleLabel)

        # Tab Widget
        self.tabWidget = QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabBar::tab { background-color: white; color: #666; padding: 12px 20px;
                margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px;
                border: 1px solid #E0E0E0; border-bottom: none; font-weight: bold; font-size: 14px; }
            QTabBar::tab:selected { background-color: #1B232A; color: white; }
            QTabWidget::pane { background-color: white; border: 1px solid #E0E0E0;
                border-radius: 0px 8px 8px 8px; margin-top: -1px; }
        """)

        # Вкладки
        self._add_tab("Сотрудники", "employeesTab", "employeesScroll", "employeesContainer", "employeesGrid")
        self._add_tab("Темы", "themesTab", "themesScroll", "themesContainer", "themesGrid")
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
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        self.tabWidget.addTab(tab, title)

        setattr(self, tab_name, tab)
        setattr(self, scroll_name, scroll)
        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _clear_grid(self, grid):
        """Очищает grid layout"""
        if not grid:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        """Показывает заглушку"""
        for grid_attr in ['employees_grid', 'themesGrid', 'projectsGrid']:
            grid = getattr(self, grid_attr, None)
            if grid:
                self._clear_grid(grid)
                label = QLabel("Нет данных для отображения")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
                grid.addWidget(label, 0, 0)

    def load_all_data(self):
        """Загружает все данные через сервис"""
        if not self.service:
            return

        try:
            self._employees_data = self.service.get_all_employees_with_stats()
            print(f"📊 Загружено сотрудников: {len(self._employees_data)}")

            self._themes_data = self.service.get_themes_stats()
            print(f"📊 Загружено тем: {len(self._themes_data)}")

            self._projects_data = self.service.get_projects_stats()
            print(f"📊 Загружено проектов: {len(self._projects_data)}")

            self.populate_employees_tab()
            self.populate_themes_tab()
            self.populate_projects_tab()

        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()

    def populate_employees_tab(self):
        """Заполняет вкладку сотрудников"""
        if not hasattr(self, 'employees_grid'):
            print("❌ employees_grid не найден")
            return

        self._clear_grid(self.employees_grid)

        if not self._employees_data:
            print("❌ self._employees_data пуст")
            self._show_empty_message(self.employees_grid, "Нет данных о сотрудниках")
            return

        print(f"📊 Попытка отобразить {len(self._employees_data)} сотрудников")

        # Выводим первых несколько для проверки
        for i, emp_data in enumerate(self._employees_data[:3]):
            print(f"   Сотрудник {i}: {emp_data.get('name')} - {emp_data.get('position')}")

        row, col, max_cols = 0, 0, 3
        for emp_data in self._employees_data:
            try:
                card = EmployeeCard(emp_data)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                self.employees_grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                print(f"   ✅ Добавлена карточка для {emp_data.get('name')}")
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки для {emp_data.get('name')}: {e}")
                import traceback
                traceback.print_exc()

        # Принудительно обновляем контейнер
        if hasattr(self, 'employeesContainer'):
            self.employeesContainer.update()
            self.employeesContainer.repaint()

        print(f"✅ Отображено {len(self._employees_data)} сотрудников")

    def populate_themes_tab(self):
        """Заполняет вкладку тем"""
        if not hasattr(self, 'themesGrid'):
            return

        self._clear_grid(self.themesGrid)

        if not self._themes_data:
            self._show_empty_message(self.themesGrid, "Нет данных о темах")
            return

        row, col, max_cols = 0, 0, 3
        for theme_data in self._themes_data:
            # Подготавливаем данные через сервис
            card_data = self.service.get_theme_card_data(theme_data)
            card = ThemeCard(card_data, analytics_service=self.service)
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            self.themesGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        print(f"✅ Отображено {len(self._themes_data)} тем")

    def populate_projects_tab(self):
        """Заполняет вкладку проектов"""
        if not hasattr(self, 'projectsGrid'):
            return

        self._clear_grid(self.projectsGrid)

        if not self._projects_data:
            self._show_empty_message(self.projectsGrid, "Нет данных о проектах")
            return

        row, col, max_cols = 0, 0, 3
        for proj_data in self._projects_data:
            # Показываем только активные проекты
            if not proj_data.get("is_archived", False):
                card_data = self.service.get_project_card_data(proj_data)
                card = ProjectCard(card_data, analytics_service=self.service)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                self.projectsGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        print(f"✅ Отображено проектов: {row * max_cols + col}")

    def _show_empty_message(self, grid, message):
        """Показывает сообщение об отсутствии данных"""
        self._clear_grid(grid)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        grid.addWidget(label, 0, 0)

    def refresh(self):
        """Обновляет все данные"""
        if self.service:
            self.load_all_data()