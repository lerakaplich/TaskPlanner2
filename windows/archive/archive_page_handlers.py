# windows/archive/archive_page_handlers.py

from PyQt6.QtWidgets import QMessageBox

from models.permissions import ProjectRole
from models.tasks import Task


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
        # Проверяем права
        if not self.can_restore_project(project_id):
            QMessageBox.warning(
                self.page,
                "Доступ запрещён",
                "У вас нет прав на восстановление этого проекта.\n"
                "Требуется роль: Суперадмин, Админ, Руководитель проекта или Куратор."
            )
            return

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
        # Проверяем права
        if not self.can_delete_project_permanently(project_id):
            QMessageBox.warning(
                self.page,
                "Доступ запрещён",
                "У вас нет прав на удаление этого проекта.\n"
                "Требуется роль: Суперадмин, Админ, Руководитель проекта или Куратор."
            )
            return

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
        # Проверяем права на восстановление задачи (нужен проект)
        if not self.can_restore_task(task_id):
            QMessageBox.warning(
                self.page,
                "Доступ запрещён",
                "У вас нет прав на восстановление этой задачи."
            )
            return

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
        # Проверяем права на удаление задачи
        if not self.can_delete_task_permanently(task_id):
            QMessageBox.warning(
                self.page,
                "Доступ запрещён",
                "У вас нет прав на удаление этой задачи."
            )
            return

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
    # Проверка прав (через permission_service)
    # ==========================================================

    def can_restore_project(self, project_id: int) -> bool:
        """
        Может ли пользователь восстанавливать проект
        - Суперадмин - может
        - Админ - может
        - Руководитель проекта (PROJECT_MANAGER) - может
        - Куратор (CURATOR) - может
        """
        if not self.page.permission_service:
            return True

        # Проверяем роль в проекте
        project_role = self.page.permission_service.get_user_project_role(project_id)
        if project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True

        # Проверяем роль в приложении
        app_role = self.page.permission_service.app_manager.role
        if app_role.value in ('super_admin', 'superadmin', 'admin'):
            return True

        return False

    def can_delete_project_permanently(self, project_id: int) -> bool:
        """
        Может ли пользователь удалять проект навсегда
        - Суперадмин - может
        - Админ - может
        - Руководитель проекта (PROJECT_MANAGER) - может
        - Куратор (CURATOR) - может
        """
        if not self.page.permission_service:
            return True

        # Проверяем роль в проекте
        project_role = self.page.permission_service.get_user_project_role(project_id)
        if project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True

        # Проверяем роль в приложении
        app_role = self.page.permission_service.app_manager.role
        if app_role.value in ('super_admin', 'superadmin', 'admin'):
            return True

        return False

    def can_restore_task(self, task_id: int) -> bool:
        """
        Может ли пользователь восстанавливать задачу
        Проверяет права на проект, к которому относится задача
        """
        if not self.page.permission_service:
            return True

        # Получаем проект задачи
        task = self.page.archive_service.session.get(Task, task_id)
        if not task:
            return False

        project_id = task.project_id
        if not project_id:
            return False

        return self.can_restore_project(project_id)

    def can_delete_task_permanently(self, task_id: int) -> bool:
        """
        Может ли пользователь удалять задачу навсегда
        Проверяет права на проект, к которому относится задача
        """
        if not self.page.permission_service:
            return True

        # Получаем проект задачи
        task = self.page.archive_service.session.get(Task, task_id)
        if not task:
            return False

        project_id = task.project_id
        if not project_id:
            return False

        return self.can_delete_project_permanently(project_id)

    # ==========================================================
    # Старые методы (для совместимости)
    # ==========================================================

    def can_restore(self) -> bool:
        """Устаревший метод - используйте can_restore_project(project_id)"""
        if not self.page.permission_service:
            return True
        from services.permissions.app_permissions import AppRole
        return self.page.permission_service.app_manager.role in (
            AppRole.SUPER_ADMIN, AppRole.ADMIN
        )

    def can_delete_permanently(self) -> bool:
        """Устаревший метод - используйте can_delete_project_permanently(project_id)"""
        if not self.page.permission_service:
            return True
        from services.permissions.app_permissions import AppRole
        return self.page.permission_service.app_manager.role in (
            AppRole.SUPER_ADMIN, AppRole.ADMIN
        )