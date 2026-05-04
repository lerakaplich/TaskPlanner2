# windows/analytics/theme/theme_card.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QPushButton, QLabel, QFrame as QFrameWidget
from PyQt6.QtCore import Qt

from windows.analytics.theme.employees_stats_view import EmployeesStatsView
from windows.analytics.theme.theme_projects_view import ThemeProjectsView


class ThemeCard(QFrame):
    """Карточка темы - только отображение данных"""

    def __init__(self, theme_data: dict, analytics_service=None, parent=None):
        super().__init__(parent)

        self.analytics_service = analytics_service
        self.theme_data = theme_data

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "theme", "theme_card.ui"
        )

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._remove_old_ui_panels()
        else:
            self._create_ui_programmatically()

        self._setup_basic_info()
        self._setup_employees_section()
        self._setup_projects_section()

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _setup_basic_info(self):
        """Заполняет основную информацию о теме"""
        theme_name = self.theme_data.get("theme_name", "Без названия")
        color = self.theme_data.get("color", "#ccab6e")
        task_count = self.theme_data.get("task_count", 0)
        completed_count = self.theme_data.get("completed_count", 0)
        kpd_percent = self.theme_data.get("kpd_percent", 0)

        if hasattr(self, 'name_btn'):
            self.name_btn.setText(theme_name)
            self.name_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 16px;
                    font-weight: bold;
                    color: {color};
                    text-align: left;
                    border: none;
                    background-color: transparent;
                }}
            """)

        if hasattr(self, 'count_label'):
            self.count_label.setText(
                f"📊 Задач: {task_count} | ✅ Выполнено: {completed_count} | 🎯 КПД: {kpd_percent}%"
            )

    def _remove_old_ui_panels(self):
        """Удаляет старые панели из UI файла"""
        old_widgets = ['employees_btn', 'projects_btn', 'employees_panel', 'projects_panel']
        for widget_name in old_widgets:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if widget:
                    widget.deleteLater()
                    delattr(self, widget_name)

    def _setup_employees_section(self):
        """Создает секцию с сотрудниками - по умолчанию скрыта"""
        employee_stats = self.theme_data.get("employee_stats", [])
        employee_count = len(employee_stats)

        btn = QPushButton(f"▶ Сотрудники ({employee_count})", self)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px;
                text-align: left;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:checked {
                background-color: #E0E0E0;
            }
        """)

        panel = QFrameWidget(self)
        panel.setVisible(False)
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        # Создаем виджет статистики сотрудников
        self.employees_stats = EmployeesStatsView(self)
        self.employees_stats.display_data(employee_stats)

        # Настраиваем поиск
        if self.analytics_service:
            self.employees_stats.set_search_callback(
                lambda text: self._filter_employees(text, employee_stats)
            )

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.employees_stats)

        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        self.employees_btn = btn
        self.employees_panel = panel
        self._all_employee_stats = employee_stats

        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _filter_employees(self, search_text: str, all_stats: list):
        """Фильтрует сотрудников по тексту поиска"""
        if self.analytics_service:
            filtered = self.analytics_service.filter_employees_by_name(all_stats, search_text)
            self.employees_stats.display_data(filtered)
        else:
            # Fallback: простая фильтрация
            if not search_text:
                self.employees_stats.display_data(all_stats)
            else:
                search_lower = search_text.lower()
                filtered = [s for s in all_stats if search_lower in s.get("employee_name", "").lower()]
                self.employees_stats.display_data(filtered)

    def _setup_projects_section(self):
        """Создает секцию с проектами - по умолчанию скрыта"""
        project_stats = self.theme_data.get("project_stats", [])

        btn = QPushButton(f"▶ Проекты ({len(project_stats)})", self)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px;
                text-align: left;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:checked {
                background-color: #E0E0E0;
            }
        """)

        panel = QFrameWidget(self)
        panel.setVisible(False)
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        # Создаем виджет проектов
        self.projects_view = ThemeProjectsView(self)
        self.projects_view.display_data(project_stats)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.projects_view)

        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        self.projects_btn = btn
        self.projects_panel = panel
        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _toggle_panel(self, checked, panel, button):
        """Переключает видимость панели и текст кнопки"""
        panel.setVisible(checked)
        current_text = button.text()
        if current_text.startswith("▼"):
            button.setText("▶" + current_text[1:])
        else:
            button.setText("▼" + current_text[1:])

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("ThemeCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                margin: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.name_btn = QPushButton()
        self.name_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; text-align: left; border: none; background-color: transparent;")
        layout.addWidget(self.name_btn)

        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(self.count_label)