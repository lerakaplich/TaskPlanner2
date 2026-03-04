import os
import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QGridLayout,
    QScrollArea, QVBoxLayout
)
from PyQt6.uic import loadUi

from services.analytics_service import AnalyticsService
from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from windows.analytics.theme.theme_card import ThemeCard# новый импорт


class AnalyticsPage(QWidget):
    def __init__(self, service: AnalyticsService, parent=None): # Передаем сервис
        super().__init__(parent)
        self.service = service
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "analytics"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "analytics_page.ui"), self)

        # Теперь данные берем только из сервиса
        self.employees_data = self.service.get_employees_analytics()
        self.projects_data = self.service.get_projects_analytics()
        self.themes_data = self.service.get_themes_analytics()
        self.populate_employees_tab()
        self.populate_themes_tab()
        self.populate_projects_tab()   # новая вкладка

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

        themes_map = self.service.get_themes_analytics()  # Получаем словарь {тег: [задачи]}

        row = col = 0
        max_cols = 3
        for theme_name, tasks in themes_map.items():
            theme_card_data = self.service.get_theme_card_data(theme_name, tasks)
            card = ThemeCard(theme_card_data)
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
        employees = self.service.get_employees_analytics()

        row = col = 0
        max_cols = 3
        for emp_data in employees:
            # ДООБОГАЩЕНИЕ: Получаем глубокую аналитику (КПД по тегам, проекты)
            # Этот метод мы обсуждали ранее в AnalyticsService
            personal_stats = self.service.get_employee_personal_analytics(emp_data['id'])

            # Склеиваем базу и аналитику в один DTO для карточки
            full_emp_data = {**emp_data, **personal_stats}

            # Создаем "тонкую" карточку
            card = EmployeeCard(full_emp_data)
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
        projects = self.service.get_projects_analytics()

        row = col = 0
        max_cols = 3
        for proj in projects:
            # proj содержит и статистику, и список сотрудников, посчитанные в сервисе
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