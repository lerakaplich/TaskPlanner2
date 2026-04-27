# windows/analytics/theme/theme_card.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy

from windows.analytics.theme.employees_stats_view import EmployeesStatsView
from windows.analytics.theme.theme_projects_view import ThemeProjectsView


class ThemeCard(QFrame):
    def __init__(self, theme_data, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "theme"
        )

        full_ui_path = os.path.join(ui_path, "theme_card.ui")
        if os.path.exists(full_ui_path):
            uic.loadUi(full_ui_path, self)
        else:
            self._create_ui_programmatically()

        self.data = theme_data
        theme_name = theme_data.get("theme_name", "Без названия")
        color = theme_data.get("color", "#ccab6e")
        task_count = theme_data.get("task_count", 0)
        completed_count = theme_data.get("completed_count", 0)
        kpd = theme_data.get("kpd", 0)
        kpd_percent = int(kpd * 100)

        # Основные данные
        if hasattr(self, 'name_btn'):
            self.name_btn.setText(theme_name)
            self.name_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 16px;
                    font-weight: bold;
                    color: {color};
                    text-align: left;
                    border: none;
                }}
            """)

        if hasattr(self, 'count_label'):
            self.count_label.setText(f"📊 Задач: {task_count} | ✅ Выполнено: {completed_count}")

        # КПД прогресс бар
        if hasattr(self, 'kpd_progress'):
            self.kpd_progress.setValue(kpd_percent)
            self.kpd_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 10px;
                    background-color: #E0E0E0;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 10px;
                }}
            """)

        if hasattr(self, 'kpd_label'):
            self.kpd_label.setText(f"🎯 КПД: {kpd_percent}%")

        # Панель сотрудников
        if hasattr(self, 'employees_panel') and hasattr(self, 'employees_btn'):
            employee_stats = theme_data.get("employee_stats", [])
            self.employees_stats = EmployeesStatsView(
                theme_name,
                employee_stats,
                self
            )
            if self.employees_panel.layout():
                self.employees_panel.layout().addWidget(self.employees_stats)
            self.employees_btn.toggled.connect(self.toggle_employees_panel)

        # Панель проектов
        if hasattr(self, 'projects_panel') and hasattr(self, 'projects_btn'):
            project_stats = theme_data.get("project_stats", [])
            self.projects_view = ThemeProjectsView(
                theme_name,
                project_stats,
                self
            )
            if self.projects_panel.layout():
                self.projects_panel.layout().addWidget(self.projects_view)
            self.projects_btn.toggled.connect(self.toggle_projects_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _create_ui_programmatically(self):
        """Создает UI программно"""
        self.setObjectName("ThemeCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                margin: 2px;
            }
        """)

        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QFrame, QProgressBar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Название
        self.name_btn = QPushButton()
        self.name_btn.setStyleSheet("font-size: 16px; font-weight: bold; text-align: left; border: none;")
        layout.addWidget(self.name_btn)

        # Счетчик
        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(self.count_label)

        # КПД прогресс
        self.kpd_label = QLabel()
        self.kpd_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.kpd_label)

        self.kpd_progress = QProgressBar()
        self.kpd_progress.setFixedHeight(8)
        self.kpd_progress.setTextVisible(False)
        layout.addWidget(self.kpd_progress)

        # Сотрудники
        self.employees_btn = QPushButton("▶ Сотрудники")
        self.employees_btn.setCheckable(True)
        self.employees_btn.setStyleSheet(
            "background-color: #F0F0F0; border-radius: 6px; padding: 8px; text-align: left; margin-top: 5px;")
        layout.addWidget(self.employees_btn)

        self.employees_panel = QFrame()
        self.employees_panel.setVisible(False)
        self.employees_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        emp_layout = QVBoxLayout(self.employees_panel)
        emp_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.employees_panel)

        # Проекты
        self.projects_btn = QPushButton("▶ Проекты")
        self.projects_btn.setCheckable(True)
        self.projects_btn.setStyleSheet(
            "background-color: #F0F0F0; border-radius: 6px; padding: 8px; text-align: left;")
        layout.addWidget(self.projects_btn)

        self.projects_panel = QFrame()
        self.projects_panel.setVisible(False)
        self.projects_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        proj_layout = QVBoxLayout(self.projects_panel)
        proj_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.projects_panel)

    def toggle_employees_panel(self, checked):
        if hasattr(self, 'employees_panel'):
            self.employees_panel.setVisible(checked)
        if hasattr(self, 'employees_btn'):
            self.employees_btn.setText(f"{'▼' if checked else '▶'} Сотрудники")

    def toggle_projects_panel(self, checked):
        if hasattr(self, 'projects_panel'):
            self.projects_panel.setVisible(checked)
        if hasattr(self, 'projects_btn'):
            self.projects_btn.setText(f"{'▼' if checked else '▶'} Проекты")