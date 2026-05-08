# windows/profile/projects_page.py

import os
from typing import List, Dict, Any

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from windows.analytics.task_card_analytics import TaskCard


class ProjectsPage(QWidget):
    """Страница проектов (только UI)"""

    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False,
                 projects_data=None, profile_service=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode
        self.compact = compact
        self.projects_data = projects_data
        self.profile_service = profile_service

        if not self.compact:
            self.setMinimumSize(800, 600)
            self.resize(900, 700)

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        """Настраивает UI"""
        if not self.compact:
            ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
            ui_file = os.path.join(ui_path, "projects_page.ui")
            if os.path.exists(ui_file):
                uic.loadUi(ui_file, self)
                self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")
                if hasattr(self, 'btnClose'):
                    self.btnClose.clicked.connect(self.close)
            else:
                self.setLayout(QVBoxLayout())
                self.projects_layout = self.layout()
        else:
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

    def set_employee_id(self, employee_id):
        self.employee_id = employee_id
        self.projects_data = None

    def update_data(self, projects_data=None, employee_id=None):
        """Обновляет данные и перерисовывает UI"""
        if projects_data is not None:
            self.projects_data = projects_data
        if employee_id is not None:
            self.employee_id = employee_id
        self.refresh_data()

    def refresh_data(self):
        """Обновляет отображение проектов через сервис"""
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projects = self._load_projects()

        if not projects:
            empty_texts = {"active": "Нет активных проектов",
                           "completed": "Нет выполненных проектов",
                           "all": "Нет проектов"}
            label = QLabel(empty_texts.get(self.mode, "Нет проектов"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666666; margin: 50px;")
            self.projects_layout.addWidget(label)
        else:
            for project in projects:
                self._add_project_section(project)

        self.projects_layout.addStretch()

    def _load_projects(self) -> List[Dict]:
        """Загружает проекты через сервис"""
        if self.projects_data is not None:
            projects = self.projects_data
        elif self.profile_service and self.employee_id:
            all_projects = self.profile_service.get_employee_projects(self.employee_id)
            projects = self._filter_projects_by_mode(all_projects)
        else:
            projects = []

        return projects

    def _filter_projects_by_mode(self, projects: List[Dict]) -> List[Dict]:
        """Фильтрует проекты по режиму"""
        filtered = []
        for project in projects:
            is_archived = project.get("is_archived", False)
            if self.mode == "active" and not is_archived:
                filtered.append(project)
            elif self.mode == "completed" and is_archived:
                filtered.append(project)
            elif self.mode == "all":
                filtered.append(project)
        return filtered

    def _add_project_section(self, project: Dict):
        """Добавляет секцию проекта с задачами"""
        project_name = project.get("name", "Без названия")
        total_tasks = project.get("total_tasks", 0)
        completed_tasks = project.get("completed_tasks", 0)

        header_style = f"""
            QPushButton {{ background-color: #D22730; color: white; border-radius: {10 if not self.compact else 6}px;
                          font-weight: bold; font-size: {18 if not self.compact else 14}px;
                          border: none; text-align: left; padding: {15 if not self.compact else 8}px 15px; }}
            QPushButton:hover {{ background-color: #862633; }}
        """

        header_btn = QPushButton(f"{project_name} ({completed_tasks}/{total_tasks}) ►")
        header_btn.setCheckable(True)
        header_btn.setStyleSheet(header_style)

        project_panel = QFrame()
        project_panel.setVisible(False)
        project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
        panel_layout = QVBoxLayout(project_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)

        # Информация о проекте
        info_label = QLabel(f"✅ Выполнено: {completed_tasks}/{total_tasks} задач")
        info_label.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 5px;")
        panel_layout.addWidget(info_label)

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        def toggle_panel(checked):
            project_panel.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(f"{project_name} ({completed_tasks}/{total_tasks}){arrow}")

        header_btn.toggled.connect(toggle_panel)