import os

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from services.profile_service import ProfileService


class ProjectsPage(QWidget):

    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False, projects_data=None):

        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode
        self.compact = compact
        self.projects_data = projects_data

        self.profile_service = ProfileService()

        if not self.compact:

            ui_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "ui", "profile"
            )

            uic.loadUi(os.path.join(ui_path, "projects_page.ui"), self)

            self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")

        else:

            self.setLayout(QVBoxLayout())

            self.projects_layout = self.layout()

            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

        self.refresh_data()

    # ---------- DATA ----------

    def load_projects(self):

        if self.projects_data is None:

            self.projects_data = self.profile_service.get_employee_projects(
                self.employee_id
            )

        return self.projects_data

    # ---------- UI ----------

    def refresh_data(self):

        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projects = self.load_projects()

        projects, no_data_text = self.profile_service.filter_projects_by_mode(
            projects,
            self.mode
        )

        if not projects:

            label = QLabel(no_data_text)

            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label.setStyleSheet(
                "font-size: 18px; color: #666666; margin: 50px;"
            )

            self.projects_layout.addWidget(label)

        else:

            for project in projects:
                self.add_project_section(
                    project["name"],
                    project["tasks"]
                )

        self.projects_layout.addStretch()

    # ---------- PROJECT ----------

    def add_project_section(self, project_name, tasks):

        header_btn = QPushButton(project_name + " ►")

        header_btn.setCheckable(True)

        header_btn.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 18px;
                border: none;
                text-align: left;
                padding: 15px;
            }
        """)

        project_panel = QFrame()

        project_panel.setVisible(False)

        panel_layout = QVBoxLayout(project_panel)

        from windows.analytics.task_card_analytics import TaskCard

        status_groups = self.profile_service.group_tasks_by_status(tasks)

        status_order = self.profile_service.get_status_order()

        for status in status_order:

            status_tasks = status_groups.get(status, [])

            if not status_tasks:
                continue

            status_display = TaskCard.STATUS_MAP.get(
                status,
                status.capitalize()
            )

            status_btn = QPushButton(
                f"▶ {status_display} ({len(status_tasks)})"
            )

            status_btn.setCheckable(True)

            tasks_panel = QFrame()

            tasks_panel.setVisible(False)

            tasks_layout = QVBoxLayout(tasks_panel)

            for task in status_tasks:

                card = TaskCard(
                    task_data=task,
                    compact=self.compact,
                    show_theme=(self.mode == "active"),
                    show_project=False,
                    check_overdue=(self.mode == "active"),
                    creator_names=TaskCard.DEFAULT_CREATOR_NAMES
                )

                tasks_layout.addWidget(card)

            panel_layout.addWidget(status_btn)
            panel_layout.addWidget(tasks_panel)

            status_btn.toggled.connect(
                lambda checked, p=tasks_panel: p.setVisible(checked)
            )

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        def toggle(checked):

            project_panel.setVisible(checked)

            arrow = " ▼" if checked else " ►"

            header_btn.setText(project_name + arrow)

        header_btn.toggled.connect(toggle)

    # ---------- API ----------

    def set_employee_id(self, employee_id):

        self.employee_id = employee_id

        self.projects_data = None

        self.refresh_data()