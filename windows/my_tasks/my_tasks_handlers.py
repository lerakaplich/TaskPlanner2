# windows/my_tasks/my_tasks_handlers.py

from typing import Dict, Optional
from PyQt6.QtWidgets import QMessageBox


class MyTasksHandlers:
    """Обработчики событий для MyTasksPage"""

    def __init__(self, page):
        self.page = page

    # ==========================================================
    # ДЕЙСТВИЯ С ЗАДАЧАМИ
    # ==========================================================

    def on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        task = self.page.service.get_task_by_id(task_id)
        if task:
            from windows.other_tasks.task_dialog import TaskDialog
            dialog = TaskDialog(
                self.page,
                task_data=task,
                mode="edit",
                current_user=self.page.current_user
            )
            dialog.set_service(self.page.service)
            dialog.task_saved.connect(self._on_task_updated_from_edit)
            dialog.exec()

    def _on_task_updated_from_edit(self, task_id: int, form_data: dict):
        """Обработчик обновления задачи из диалога"""
        updated_task = self.page.service.update_task(task_id, form_data)
        if updated_task:
            self.page.update_task_card(updated_task)
            self.page.update_statistics()

    def on_duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        new_task = self.page.service.duplicate_task(task_id)
        if new_task:
            from windows.my_tasks.task_card import TaskCard
            task_card = TaskCard(new_task)
            self.page._connect_task_card_signals(task_card)
            column_name = new_task.get("status")
            if column_name in self.page.columns:
                self.page.columns[column_name].add_task(task_card)
            self.page.update_statistics()
            QMessageBox.information(self.page, "Успех", f"Задача '{new_task.get('title')}' дублирована")

    def on_pause_task(self, task_id: int):
        """Поставить задачу на паузу"""
        updated_task = self.page.service.pause_task(task_id)
        if updated_task:
            self.page._update_task_card_data(task_id, updated_task)
            self.page.update_statistics()
            QMessageBox.information(self.page, "Пауза", "Задача поставлена на паузу")

    def on_resume_task(self, task_id: int):
        """Возобновить задачу"""
        updated_task = self.page.service.resume_task(task_id)
        if updated_task:
            self.page._update_task_card_data(task_id, updated_task)
            self.page.update_statistics()
            QMessageBox.information(self.page, "Возобновление", "Задача возобновлена")

    def on_archive_task(self, task_id: int):
        """Архивирование задачи"""
        reply = QMessageBox.question(
            self.page, "Архивирование",
            "Вы уверены, что хотите архивировать задачу?\nОна будет перемещена в архив.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.page.service.archive_task_by_id(task_id):
                self.page._remove_task_card_from_ui(task_id)
                self.page.update_statistics()
                QMessageBox.information(self.page, "Успех", "Задача архивирована")

    def on_delete_task(self, task_id: int):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self.page, "Удаление",
            "Вы уверены, что хотите полностью удалить задачу?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.page.service.delete_task_by_id(task_id):
                    self.page._remove_task_card_from_ui(task_id)
                    self.page.update_statistics()
                    QMessageBox.information(self.page, "Успех", "Задача удалена")
                else:
                    QMessageBox.warning(self.page, "Ошибка", "Не удалось удалить задачу")
            except Exception as e:
                QMessageBox.critical(self.page, "Ошибка", f"Ошибка при удалении: {str(e)}")

    def on_progress_changed(self, task_id: int, progress_percent: int):
        """Обработчик изменения прогресса задачи"""
        updated_task = self.page.service.update_task_progress(task_id, progress_percent)
        if updated_task:
            self.page._update_progress_in_ui(task_id, progress_percent)
            self.page.update_statistics()
            self.page.task_moved.emit()

    def on_task_dropped(self, task_id: int, target_column_id: int):
        """Обработчик drop задачи в колонку"""
        target_column = self.page._find_column_by_id(target_column_id)
        if not target_column:
            return

        task = self.page.service.get_task_by_id(task_id)
        if not task:
            return

        old_status = task.get("status")
        new_status = target_column.column_name

        if old_status == new_status:
            return

        result = self.page.service.move_task_to_column(task_id, target_column_id)
        if result:
            self.page.update_task_card(result)
            self.page.update_statistics()
            self.page.task_moved.emit()
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(150, self.page.load_tasks)

    def on_project_clicked(self, project_id: int):
        """Обработчик клика по проекту"""
        self.page.open_project_requested.emit(project_id)

    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================

    def can_delete_task(self) -> bool:
        """Проверяет права на удаление"""
        if not self.page.permission_service:
            return True
        app_role = self.page.permission_service.app_manager.role
        return app_role.value in ('super_admin', 'admin')

    def can_archive_task(self) -> bool:
        """Проверяет права на архивацию"""
        if not self.page.permission_service:
            return True
        app_role = self.page.permission_service.app_manager.role
        return app_role.value in ('super_admin', 'admin')