# windows/archive/archive_page_handlers.py

from typing import Optional
from PyQt6.QtWidgets import QMessageBox


class ArchivePageHandlers:
    """Обработчики событий для ArchivePage"""

    def __init__(self, page):
        self.page = page

    # ==========================================================
    # Действия с проектами
    # ==========================================================

    def on_project_clicked(self, project_id: int):
        """Клик по проекту - показать его задачи"""
        self.page.show_project_tasks(project_id)

    def on_restore_project(self, project_id: int):
        """Восстановление проекта"""
        name = self.page.archive_service.get_project_name(project_id)
        if not name:
            return

        reply = QMessageBox.question(
            self.page,
            "Восстановление проекта",
            f"Восстановить проект '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.archive_service.restore_project(project_id):
                self.page.show_projects_list()
                QMessageBox.information(self.page, "Успех", "Проект восстановлен")

    def on_delete_project_permanently(self, project_id: int):
        """Удаление проекта навсегда"""
        reply = QMessageBox.warning(
            self.page,
            "Удаление проекта",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.archive_service.delete_project_permanently(project_id):
                self.page.show_projects_list()
                QMessageBox.information(self.page, "Удалено", "Проект удалён")

    # ==========================================================
    # Действия с задачами
    # ==========================================================

    def on_restore_task(self, task_id: int):
        """Восстановление задачи"""
        title = self.page.archive_service.get_task_title(task_id)
        if not title:
            return

        reply = QMessageBox.question(
            self.page,
            "Восстановление задачи",
            f"Восстановить задачу '{title}'?\nОна вернётся в активные задачи.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.archive_service.restore_task(task_id):
                self.page.refresh_current_view()
                self.page.tasks_restored.emit()
                QMessageBox.information(self.page, "Успех", "Задача восстановлена")

    def on_delete_task_permanently(self, task_id: int):
        """Удаление задачи навсегда"""
        reply = QMessageBox.warning(
            self.page,
            "Удаление задачи",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.archive_service.delete_task_permanently(task_id):
                self.page.refresh_current_view()
                QMessageBox.information(self.page, "Удалено", "Задача удалена")

    # ==========================================================
    # Проверка прав (делегирует сервису)
    # ==========================================================

    def can_restore(self) -> bool:
        """Может ли пользователь восстанавливать из архива"""
        if not self.page.permission_service:
            return True
        from services.permissions.app_permissions import AppRole
        return self.page.permission_service.app_manager.role == AppRole.SUPER_ADMIN

    def can_delete_permanently(self) -> bool:
        """Может ли пользователь удалять навсегда"""
        if not self.page.permission_service:
            return True
        from services.permissions.app_permissions import AppRole
        return self.page.permission_service.app_manager.role == AppRole.SUPER_ADMIN