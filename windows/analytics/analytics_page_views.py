# windows/analytics/analytics_page_views.py

from typing import List, Dict, Any
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt

from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.theme.theme_card import ThemeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from windows.analytics.rating.rating_employee_card import RatingEmployeeCard


class AnalyticsPageViews:
    """Менеджер отображения для AnalyticsPage"""

    def __init__(self, page):
        self.page = page

    def display_employees(self, employees_data: List[Dict]):
        """Отображает сотрудников в grid"""
        grid = self.page.employees_grid
        self._clear_grid(grid)

        if not employees_data:
            self._show_empty_message(grid, "Нет сотрудников в выбранном отделе")
            return

        row, col, max_cols = 0, 0, 3
        for emp_data in employees_data:
            try:
                card = EmployeeCard(emp_data)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                card.clicked.connect(self.page.handlers.open_employee_profile)
                grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки для {emp_data.get('name')}: {e}")

    def display_rating(self, employees_data: List[Dict]):
        """Отображает сотрудников в рейтинге"""
        layout = self.page.rating_layout
        self._clear_layout(layout)

        if not employees_data:
            self._show_empty_layout_message(layout, "Нет данных за выбранный период")
            return

        sorted_employees = sorted(employees_data, key=lambda x: x.get('kpd_percent', 0), reverse=True)

        for position, emp_data in enumerate(sorted_employees):
            try:
                card = RatingEmployeeCard(emp_data, position=position, parent=None)
                card.setMinimumHeight(80)
                card.clicked.connect(self.page.handlers.open_employee_profile)
                layout.addWidget(card)
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки рейтинга для {emp_data.get('name')}: {e}")

        layout.addStretch()

    def display_themes(self, themes_data: List[Dict]):
        """Отображает темы в grid"""
        grid = self.page.themesGrid
        self._clear_grid(grid)

        if not themes_data:
            self._show_empty_message(grid, "Нет данных о темах")
            return

        row, col, max_cols = 0, 0, 3
        for theme_data in themes_data:
            card_data = self.page.service.get_theme_card_data(theme_data)
            card = ThemeCard(card_data, analytics_service=self.page.service)
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def display_projects(self, projects_data: List[Dict]):
        """Отображает проекты в grid"""
        grid = self.page.projectsGrid
        self._clear_grid(grid)

        if not projects_data:
            self._show_empty_message(grid, "Нет данных о проектах")
            return

        row, col, max_cols = 0, 0, 3
        for proj_data in projects_data:
            if not proj_data.get("is_archived", False):
                card_data = self.page.service.get_project_card_data(proj_data)
                card = ProjectCard(card_data, analytics_service=self.page.service)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

    def _clear_grid(self, grid):
        if not grid:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_empty_message(self, grid, message):
        self._clear_grid(grid)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        grid.addWidget(label, 0, 0)

    def _show_empty_layout_message(self, layout, message):
        self._clear_layout(layout)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        layout.addWidget(label)