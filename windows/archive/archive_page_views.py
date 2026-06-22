# windows/archive/archive_page_views.py

from typing import List, Dict
from PyQt6.QtWidgets import QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

from windows.archive.archived_project_card import ArchivedProjectCard
from windows.archive.archived_task_card import ArchivedTaskCard


class ArchivePageViews:
    """Менеджер отображения для ArchivePage"""

    def __init__(self, page):
        self.page = page

    def display_projects(self, projects: List[Dict], can_restore: bool, can_delete: bool):
        """Отображает список проектов"""
        self._clear_projects()

        if not projects:
            self.page.empty_label.setText("Нет архивированных проектов")
            self.page.empty_label.show()
            self.page.projects_widget.hide()
            return

        self.page.empty_label.hide()
        self.page.projects_widget.show()

        columns = self._calculate_columns()

        for i, project in enumerate(projects):
            card = ArchivedProjectCard(
                project,
                self.page,
                can_restore=can_restore,
                can_delete=can_delete
            )
            card.clicked.connect(self.page.handlers.on_project_clicked)
            card.restore_requested.connect(self.page.handlers.on_restore_project)
            card.delete_permanently_requested.connect(self.page.handlers.on_delete_project_permanently)

            row = i // columns
            col = i % columns
            self.page.projects_layout.addWidget(card, row, col)

        self._add_bottom_spacer(len(projects), columns)

    def display_tasks(self, tasks: List[Dict], can_restore: bool, can_delete: bool):
        """Отображает список задач"""
        self._clear_tasks()

        if not tasks:
            self._show_empty_tasks_message("Нет архивированных задач")
            return

        self.page.empty_label.hide()
        self.page.tasks_widget.show()

        columns = self._calculate_columns()

        for i, task in enumerate(tasks):
            card = ArchivedTaskCard(
                task,
                self.page,
                can_restore=can_restore,
                can_delete=can_delete
            )
            card.restore_requested.connect(self.page.handlers.on_restore_task)
            card.delete_permanently_requested.connect(self.page.handlers.on_delete_task_permanently)

            row = i // columns
            col = i % columns
            self.page.tasks_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Растягиваем последнюю колонку
        for col in range(columns):
            self.page.tasks_layout.setColumnStretch(col, 0)
        if columns > 0:
            self.page.tasks_layout.setColumnStretch(columns - 1, 1)

        last_row = (len(tasks) + columns - 1) // columns
        if last_row > 0:
            self.page.tasks_layout.setRowStretch(last_row, 1)

    def show_empty_tasks(self, message: str):
        """Показывает сообщение об отсутствии задач"""
        self._clear_tasks()
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #999999; font-size: 18px; padding: 50px;")
        columns = self._calculate_columns()
        self.page.tasks_layout.addWidget(label, 0, 0, 1, columns, Qt.AlignmentFlag.AlignCenter)

    # ==========================================================
    # Вспомогательные методы
    # ==========================================================

    def _clear_projects(self):
        while self.page.projects_layout.count():
            item = self.page.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_tasks(self):
        while self.page.tasks_layout.count():
            item = self.page.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _calculate_columns(self) -> int:
        width = self.page.width()
        if width > 1400:
            return 4
        elif width > 1100:
            return 3
        elif width > 800:
            return 2
        return 1

    def _add_bottom_spacer(self, items_count: int, columns: int):
        rows = (items_count + columns - 1) // columns
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.page.projects_layout.addItem(spacer, rows, 0, 1, columns)

    def _show_empty_tasks_message(self, message: str):
        self._clear_tasks()
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #999999; font-size: 18px; padding: 50px;")
        columns = self._calculate_columns()
        self.page.tasks_layout.addWidget(label, 0, 0, 1, columns, Qt.AlignmentFlag.AlignCenter)