# windows/archive/archive_page.py

import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QLabel, QSpacerItem, QComboBox,
    QSizePolicy, QMessageBox
)

from services.archive_service import ArchiveService
from services.permissions.permission_service import PermissionService


class ArchivePage(QWidget):
    """UI страница архива - только отображение"""

    tasks_restored = pyqtSignal()

    def __init__(self, service: ArchiveService = None, permission_service: PermissionService = None, parent=None):
        super().__init__(parent)
        self.setObjectName("archivePage")
        self.archive_service = service
        self.permission_service = permission_service
        self.parent_window = parent

        # Состояние
        self.current_filter_type = "projects"
        self.current_search_text = ""
        self.current_project_id = None
        self._is_initialized = False

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive", "archive_page.ui"
        )
        uic.loadUi(ui_path, self)

        # Подключение сигналов
        self.back_button.clicked.connect(self.show_projects_list)
        self.filterCombo.currentTextChanged.connect(self.on_filter_changed)

        if hasattr(self, "search_input"):
            self.search_input.textChanged.connect(self.on_search)

        self.show_projects_list()
        self._is_initialized = True

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_current_view()

    # ==========================================================
    # Проверка прав
    # ==========================================================

    def _can_restore(self) -> bool:
        """Может ли пользователь восстанавливать из архива"""
        if not self.permission_service:
            return True  # Если сервис не передан, разрешаем (для обратной совместимости)

        # Только суперадмин может восстанавливать из архива
        from services.permissions.app_permissions import AppRole
        return self.permission_service.app_manager.role == AppRole.SUPER_ADMIN

    def _can_delete_permanently(self) -> bool:
        """Может ли пользователь удалять навсегда"""
        if not self.permission_service:
            return True

        # Только суперадмин может удалять навсегда
        from services.permissions.app_permissions import AppRole
        return self.permission_service.app_manager.role == AppRole.SUPER_ADMIN

    # ==========================================================
    # Фильтрация
    # ==========================================================

    def on_filter_changed(self, filter_text: str):
        if filter_text == "Проекты":
            self.current_filter_type = "projects"
            self.show_projects_list()
        elif filter_text == "Задачи":
            self.current_filter_type = "tasks"
            self.show_all_tasks()

    # ==========================================================
    # Навигация
    # ==========================================================

    def show_projects_list(self):
        self.current_project_id = None
        self.current_search_text = ""

        self.filterCombo.blockSignals(True)
        self.filterCombo.setCurrentText("Проекты")
        self.filterCombo.blockSignals(False)

        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)

        self.section_title.setText("Архивированные проекты")
        self.back_button.hide()
        self.projects_widget.show()
        self.tasks_widget.hide()
        self._update_projects_view()

    def show_all_tasks(self):
        self.current_project_id = None
        self.current_search_text = ""

        self.filterCombo.blockSignals(True)
        self.filterCombo.setCurrentText("Задачи")
        self.filterCombo.blockSignals(False)

        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)

        self.section_title.setText("Все архивированные задачи")
        self.back_button.show()
        self.projects_widget.hide()
        self.tasks_widget.show()
        self._update_all_tasks_view()

    def refresh_current_view(self):
        if self.current_filter_type == "projects":
            self._update_projects_view(force=True)
        elif self.current_project_id is not None:
            self._update_tasks_view(force=True)
        else:
            self._update_all_tasks_view(force=True)

    # ==========================================================
    # Обновление представлений
    # ==========================================================

    def _update_projects_view(self, force=False):
        self._clear_projects()

        projects = self.archive_service.search_projects(self.current_search_text)

        if not projects:
            self.empty_label.setText("Нет архивированных проектов")
            self.empty_label.show()
            self.projects_widget.hide()
            return

        self.empty_label.hide()
        self.projects_widget.show()

        from windows.archive.archived_project_card import ArchivedProjectCard

        columns = self._calculate_columns()
        can_restore = self._can_restore()
        can_delete = self._can_delete_permanently()

        for i, project in enumerate(projects):
            card = ArchivedProjectCard(
                project,
                self,
                can_restore=can_restore,
                can_delete=can_delete
            )
            card.clicked.connect(self._on_project_clicked)
            card.restore_requested.connect(self._on_restore_project)
            card.delete_permanently_requested.connect(self._on_delete_project_permanently)

            row = i // columns
            col = i % columns
            self.projects_layout.addWidget(card, row, col)

        self._add_bottom_spacer(projects, columns)

    def _update_tasks_view(self, force=False):
        self._clear_tasks()

        tasks = self.archive_service.search_tasks(self.current_project_id, self.current_search_text)

        if not tasks:
            self._show_empty_tasks_message("В этом проекте нет архивированных задач")
            return

        self._display_tasks(tasks)

    def _update_all_tasks_view(self, force=False):
        self._clear_tasks()

        tasks = self.archive_service.search_all_archived_tasks(self.current_search_text)

        if not tasks:
            self._show_empty_tasks_message("Нет архивированных задач")
            return

        self._display_tasks(tasks)

    def _display_tasks(self, tasks):
        self.empty_label.hide()
        self.tasks_widget.show()

        from windows.archive.archived_task_card import ArchivedTaskCard

        columns = self._calculate_columns()
        can_restore = self._can_restore()
        can_delete = self._can_delete_permanently()

        for i, task in enumerate(tasks):
            card = ArchivedTaskCard(
                task,
                self,
                can_restore=can_restore,
                can_delete=can_delete
            )
            card.restore_requested.connect(self._on_restore_task)
            card.delete_permanently_requested.connect(self._on_delete_task_permanently)

            row = i // columns
            col = i % columns
            self.tasks_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        for col in range(columns):
            self.tasks_layout.setColumnStretch(col, 0)
        if columns > 0:
            self.tasks_layout.setColumnStretch(columns - 1, 1)
        last_row = (len(tasks) + columns - 1) // columns
        if last_row > 0:
            self.tasks_layout.setRowStretch(last_row, 1)

    def _show_empty_tasks_message(self, message: str):
        self._clear_tasks()
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #999999; font-size: 18px; padding: 50px;")
        self.tasks_layout.addWidget(label, 0, 0, 1, self._calculate_columns(), Qt.AlignmentFlag.AlignCenter)

    def on_search(self, text: str):
        self.current_search_text = text.strip()

        if self.current_filter_type == "projects":
            self._update_projects_view()
        elif self.current_project_id is not None:
            self._update_tasks_view()
        else:
            self._update_all_tasks_view()

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
            self, "Восстановление проекта",
            f"Восстановить проект '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.restore_project(project_id):
                self.show_projects_list()
                QMessageBox.information(self, "Успех", "Проект восстановлен")

    def _on_delete_project_permanently(self, project_id: int):
        reply = QMessageBox.warning(
            self, "Удаление проекта",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.delete_project_permanently(project_id):
                self.show_projects_list()
                QMessageBox.information(self, "Удалено", "Проект удалён")

    def _on_restore_task(self, task_id: int):
        title = self.archive_service.get_task_title(task_id)
        if not title:
            return

        reply = QMessageBox.question(
            self, "Восстановление задачи",
            f"Восстановить задачу '{title}'?\nОна вернётся в активные задачи.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.restore_task(task_id):
                self.refresh_current_view()
                self.tasks_restored.emit()
                QMessageBox.information(self, "Успех", "Задача восстановлена и появится в активных задачах")

    def _on_delete_task_permanently(self, task_id: int):
        reply = QMessageBox.warning(
            self, "Удаление задачи",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.archive_service.delete_task_permanently(task_id):
                if self.current_project_id is not None:
                    self._update_tasks_view()
                else:
                    self._update_all_tasks_view()
                QMessageBox.information(self, "Удалено", "Задача удалена")

    def show_project_tasks(self, project_id: int):
        self.current_project_id = project_id
        self.current_search_text = ""

        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)

        project_name = self.archive_service.get_project_name(project_id)
        self.section_title.setText(f"Архивированные задачи: {project_name}")
        self.back_button.show()
        self.projects_widget.hide()
        self.tasks_widget.show()
        self._update_tasks_view(force=True)

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

    def _calculate_columns(self) -> int:
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
        from PyQt6.QtCore import QTimer
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(lambda: self.refresh_current_view())
        self._resize_timer.start(100)