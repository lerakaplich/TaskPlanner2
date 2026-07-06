# windows/archive/archive_page.py

import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget

from services.archive_service import ArchiveService
from services.permissions.permission_service import PermissionService
from windows.archive.archive_page_handlers import ArchivePageHandlers
from windows.archive.archive_page_views import ArchivePageViews


class ArchivePage(QWidget):
    """Страница архива - ТОЛЬКО UI"""

    tasks_restored = pyqtSignal()

    def __init__(self, service: ArchiveService = None, permission_service: PermissionService = None, parent=None):
        super().__init__(parent)
        self.setObjectName("archivePage")

        # Сервисы
        self.archive_service = service or ArchiveService(None)
        self.permission_service = permission_service

        # Обработчики и отображение
        self.handlers = ArchivePageHandlers(self)
        self.views = ArchivePageViews(self)

        # Состояние
        self.current_filter_type = "projects"
        self.current_search_text = ""
        self.current_project_id = None
        self._is_initialized = False
        self._resize_timer = QTimer()  # ✅ Инициализируем сразу

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
    # Фильтрация
    # ==========================================================

    def on_filter_changed(self, filter_text: str):
        if filter_text == "Проекты":
            self.current_filter_type = "projects"
            self.show_projects_list()
        elif filter_text == "Задачи":
            self.current_filter_type = "tasks"
            self.show_all_tasks()

    def on_search(self, text: str):
        self.current_search_text = text.strip()

        if self.current_filter_type == "projects":
            self._update_projects_view()
        elif self.current_project_id is not None:
            self._update_tasks_view()
        else:
            self._update_all_tasks_view()

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

    def refresh_current_view(self):
        if self.current_filter_type == "projects":
            self._update_projects_view(force=True)
        elif self.current_project_id is not None:
            self._update_tasks_view(force=True)
        else:
            self._update_all_tasks_view(force=True)

    # ==========================================================
    # Обновление представлений (делегирует views)
    # ==========================================================

    def _update_projects_view(self, force=False):
        projects = self.archive_service.search_projects(self.current_search_text)
        self.views.display_projects(
            projects,
            self.handlers.can_restore(),
            self.handlers.can_delete_permanently()
        )

    def _update_tasks_view(self, force=False):
        tasks = self.archive_service.search_tasks(self.current_project_id, self.current_search_text)
        self.views.display_tasks(
            tasks,
            self.handlers.can_restore(),
            self.handlers.can_delete_permanently()
        )

    def _update_all_tasks_view(self, force=False):
        tasks = self.archive_service.search_all_archived_tasks(self.current_search_text)
        self.views.display_tasks(
            tasks,
            self.handlers.can_restore(),
            self.handlers.can_delete_permanently()
        )

    # ==========================================================
    # Обработка изменения размера
    # ==========================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_resize_timer'):
            if self._resize_timer is not None:
                self._resize_timer.stop()
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(lambda: self.refresh_current_view())
        self._resize_timer.start(100)