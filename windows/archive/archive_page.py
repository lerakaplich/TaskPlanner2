# windows/archive/archive_page.py

import os
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QSpacerItem,
    QSizePolicy, QMessageBox
)

from services.archive_service import ArchiveService


class ArchivePage(QWidget):
    """UI страница архива - только отображение"""

    def __init__(self, service: ArchiveService = None, parent=None):
        super().__init__(parent)
        self.setObjectName("archivePage")

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive", "archive_page.ui"
        )
        uic.loadUi(ui_path, self)

        # Сервис
        self.archive_service = service

        # Состояние
        self.current_project_id = None
        self.current_search_text = ""

        # Сигналы
        self.back_button.clicked.connect(self.show_projects_list)
        if hasattr(self, "search_input"):
            self.search_input.textChanged.connect(self.on_search)

        # Инициализация
        self.show_projects_list()

    # ==========================================================
    # Отображение проектов
    # ==========================================================

    def show_projects_list(self):
        self.current_project_id = None
        self.current_search_text = ""

        if hasattr(self, "search_input"):
            self.search_input.clear()

        self.section_title.setText("Архивированные проекты")
        self.back_button.hide()

        self.projects_widget.show()
        self.tasks_widget.hide()

        self._update_projects_view()

    def _update_projects_view(self):
        """Обновляет отображение проектов"""
        self._clear_projects()

        projects = self.archive_service.search_projects(self.current_search_text)

        if not projects:
            self.empty_label.setText("📭 Нет архивированных проектов")
            self.empty_label.show()
            self.projects_widget.hide()
            return

        self.empty_label.hide()

        from windows.archive.archived_project_card import ArchivedProjectCard

        columns = self._calculate_columns()

        for i, project in enumerate(projects):
            card = ArchivedProjectCard(project, self)
            card.clicked.connect(self._on_project_clicked)
            card.restore_requested.connect(self._on_restore_project)
            card.delete_permanently_requested.connect(self._on_delete_project_permanently)

            row = i // columns
            col = i % columns
            self.projects_layout.addWidget(card, row, col)

        self._add_bottom_spacer(projects, columns)

    # ==========================================================
    # Отображение задач
    # ==========================================================

    def show_project_tasks(self, project_id: int):
        self.current_project_id = project_id
        self.current_search_text = ""

        if hasattr(self, "search_input"):
            self.search_input.clear()

        project_name = self.archive_service.get_project_name(project_id)
        self.section_title.setText(f"Задачи проекта: {project_name}")
        self.back_button.show()

        self.projects_widget.hide()
        self.tasks_widget.show()

        self._update_tasks_view()

    def _update_tasks_view(self):
        """Обновляет отображение задач"""
        self._clear_tasks()

        tasks = self.archive_service.search_tasks(
            self.current_project_id,
            self.current_search_text
        )

        if not tasks:
            self._show_empty_tasks_message()
            return

        from windows.archive.archived_task_card import ArchivedTaskCard

        columns = self._calculate_columns()

        for i, task in enumerate(tasks):
            card = ArchivedTaskCard(task, self)
            card.restore_requested.connect(self._on_restore_task)
            card.delete_permanently_requested.connect(self._on_delete_task_permanently)

            row = i // columns
            col = i % columns
            self.tasks_layout.addWidget(card, row, col)

    def _show_empty_tasks_message(self):
        """Показывает сообщение об отсутствии задач"""
        label = QLabel("📭 В этом проекте нет архивированных задач")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #999999; font-size: 18px; padding: 50px;")
        self.tasks_layout.addWidget(label, 0, 0, 1, self._calculate_columns())

    # ==========================================================
    # Поиск
    # ==========================================================

    def on_search(self, text: str):
        self.current_search_text = text.strip()

        if self.current_project_id is None:
            self._update_projects_view()
        else:
            self._update_tasks_view()

    # ==========================================================
    # Обработчики действий
    # ==========================================================

    def _on_project_clicked(self, project_id: int):
        self.show_project_tasks(project_id)

    def _on_restore_project(self, project_id: int):
        name = self.archive_service.get_project_name(project_id)
        if not name:
            return

        reply = QMessageBox.question(
            self,
            "Восстановление проекта",
            f"Восстановить проект '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.restore_project(project_id):
                self.show_projects_list()
                QMessageBox.information(self, "Успех", "Проект восстановлен")

    def _on_restore_task(self, task_id: int):
        title = self.archive_service.get_task_title(task_id)
        if not title:
            return

        reply = QMessageBox.question(
            self,
            "Восстановление задачи",
            f"Восстановить задачу '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.restore_task(task_id):
                self._update_tasks_view()
                QMessageBox.information(self, "Успех", "Задача восстановлена")

    def _on_delete_project_permanently(self, project_id: int):
        reply = QMessageBox.warning(
            self,
            "Удаление проекта",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.delete_project_permanently(project_id):
                self.show_projects_list()
                QMessageBox.information(self, "Удалено", "Проект удалён")

    def _on_delete_task_permanently(self, task_id: int):
        reply = QMessageBox.warning(
            self,
            "Удаление задачи",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.delete_task_permanently(task_id):
                self._update_tasks_view()
                QMessageBox.information(self, "Удалено", "Задача удалена")

    # ==========================================================
    # Вспомогательные методы
    # ==========================================================

    def _clear_projects(self):
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_tasks(self):
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _calculate_columns(self):
        width = self.width()
        if width > 1400:
            return 4
        elif width > 1100:
            return 3
        elif width > 800:
            return 2
        return 1

    def _add_bottom_spacer(self, items, columns):
        rows = (len(items) + columns - 1) // columns
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.projects_layout.addItem(spacer, rows, 0, 1, columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_project_id is None:
            self._update_projects_view()
        else:
            self._update_tasks_view()