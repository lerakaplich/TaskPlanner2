# windows/other_tasks/others_tasks_handlers.py

from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox


class OthersTasksHandlers:
    """Обработчики событий для OthersTasksPage"""

    def __init__(self, page):
        self.page = page

    def can_edit_or_delete_task(self) -> bool:
        """Может ли пользователь редактировать/удалять чужие задачи"""
        if not self.page.permission_service:
            return True
        app_role = self.page.permission_service.app_manager.role
        return app_role.value in ('super_admin', 'superadmin', 'admin')

    def can_create_task(self) -> bool:
        """Может ли пользователь создавать задачи в чужих задачах"""
        if not self.page.permission_service:
            return True
        # ✅ ИСПРАВЛЕНО: проверяем обе возможные роли
        app_role = self.page.permission_service.app_manager.role
        return app_role.value in ('super_admin', 'superadmin', 'admin')

    def can_archive_task(self) -> bool:
        """Может ли пользователь архивировать чужие задачи"""
        if not self.page.permission_service:
            return True
        app_role = self.page.permission_service.app_manager.role
        return app_role.value in ('super_admin', 'superadmin', 'admin')

    # ==========================================================
    # ЗАГРУЗКА И ОБНОВЛЕНИЕ
    # ==========================================================

    def load_tasks(self):
        """Загружает чужие задачи"""
        if self.page._is_loading:
            return

        self.page._is_loading = True

        try:
            if hasattr(self.page.service.crud, '_column_cache'):
                self.page.service.crud._column_cache = None

            self.page.clear_all_columns()
            tasks = self.page.service.load_tasks()

            self.page.setUpdatesEnabled(False)
            for column in self.page.column_widgets:
                column.setUpdatesEnabled(False)

            for task in tasks:
                column_name = task.get("status")
                if column_name not in self.page.columns:
                    continue

                card = self.page.create_task_card(task)
                self.page.connect_task_card_signals(card)

                column = self.page.columns[column_name]
                if card.parent() != column.tasks_container:
                    card.setParent(column.tasks_container)
                column.add_task(card)

            for column in self.page.column_widgets:
                column.setUpdatesEnabled(True)
            self.page.setUpdatesEnabled(True)

            self.page.update_statistics()
            self.page.updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка при загрузке задач: {e}")
            self.page.setUpdatesEnabled(True)
            for column in self.page.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self.page._is_loading = False

    def load_tasks_for_current_project(self):
        """Загружает задачи для текущего выбранного проекта"""
        if self.page._is_loading:
            return

        self.page._is_loading = True

        try:
            if hasattr(self.page.service.crud, '_column_cache'):
                self.page.service.crud._column_cache = None

            self.page.clear_all_columns()
            all_tasks = self.page.service.load_tasks()

            user_id = self.page.current_user.get("id")
            filtered_tasks = self.page.service.crud.get_tasks_for_project_filter_others(
                all_tasks,
                self.page._current_project_id,
                user_id
            )

            self.page.setUpdatesEnabled(False)
            for column in self.page.column_widgets:
                column.setUpdatesEnabled(False)

            for task in filtered_tasks:
                column_name = task.get("status")
                if column_name and column_name in self.page.columns:
                    card = self.page.create_task_card(task)
                    self.page.connect_task_card_signals(card)
                    column = self.page.columns[column_name]
                    if card.parent() != column.tasks_container:
                        card.setParent(column.tasks_container)
                    column.add_task(card)

            for column in self.page.column_widgets:
                column.setUpdatesEnabled(True)
            self.page.setUpdatesEnabled(True)

            self.page.update_statistics()
            self.page.updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка загрузки задач для проекта: {e}")
            self.page.setUpdatesEnabled(True)
            for column in self.page.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self.page._is_loading = False

    def full_reload(self):
        """Полная перезагрузка страницы"""
        if hasattr(self.page.service.crud, '_column_cache'):
            self.page.service.crud._column_cache = None

        self.page.setup_kanban()
        self.page._load_projects_for_filter()
        self.load_tasks()

    # ==========================================================
    # ДЕЙСТВИЯ С ЗАДАЧАМИ
    # ==========================================================

    def on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        task = self.page.service.get_task_by_id(task_id)
        if not task:
            return

        from windows.other_tasks.task_dialog import TaskDialog
        dialog = TaskDialog(
            self.page,
            task_data=task,
            mode="edit",
            current_user=self.page.current_user
        )
        dialog.set_service(self.page.service)
        dialog.task_saved.connect(self._on_task_updated)
        dialog.exec()

    def _on_task_updated(self, task_id: int, form_data: dict):
        """Обработчик обновления задачи"""
        updated_task = self.page.service.update_task(task_id, form_data)
        if updated_task:
            self.page.update_task_card(updated_task)
            self.page.update_statistics()
            self.page.taskUpdated.emit()

    def on_delete_task(self, task_id: int):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self.page, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.service.delete_task(task_id):
                self.page.remove_task_card(task_id)
                self.page.update_statistics()
                self.page.taskUpdated.emit()

    def on_archive_task(self, task_id: int):
        """Архивирование задачи"""
        reply = QMessageBox.question(
            self.page, "Архивирование",
            "Вы уверены, что хотите архивировать задачу?\nОна будет перемещена в архив.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.page.service.archive_task_by_id(task_id):
                self.page.remove_task_card(task_id)
                self.page.update_statistics()
                self.page.taskUpdated.emit()
                QMessageBox.information(self.page, "Успех", "Задача архивирована")

    def on_duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        new_task = self.page.service.duplicate_task(task_id)
        if new_task:
            self.page.add_task_card(new_task)
            self.page.update_statistics()
            self.page.taskUpdated.emit()
            QMessageBox.information(self.page, "Успех", f"Задача '{new_task.get('title')}' дублирована")

    def on_pause_task(self, task_id: int):
        """Поставить задачу на паузу"""
        updated_task = self.page.service.pause_task(task_id)
        if updated_task:
            self.page._update_existing_task_card(task_id, updated_task)
            self.page.update_statistics()
            self.page.taskUpdated.emit()
            QMessageBox.information(self.page, "Пауза", "Задача поставлена на паузу")

    def on_resume_task(self, task_id: int):
        """Возобновить задачу"""
        updated_task = self.page.service.resume_task(task_id)
        if updated_task:
            self.page._update_existing_task_card(task_id, updated_task)
            self.page.update_statistics()
            self.page.taskUpdated.emit()
            QMessageBox.information(self.page, "Возобновление", "Задача возобновлена")

    def on_move_to_done(self, task_id: int):
        """Перемещает задачу в колонку 'Готово'"""
        target_column_name = "Готово"
        target_column = None
        for col in self.page.column_widgets:
            if col.column_name == target_column_name:
                target_column = col
                break

        if not target_column:
            QMessageBox.warning(self.page, "Ошибка", f"Колонка '{target_column_name}' не найдена")
            return

        result = self.page.service.move_task_to_column(task_id, target_column.column_id)

        if result:
            self.page.remove_task_card(task_id)
            new_card = self.page.create_task_card(result)
            self.page.connect_task_card_signals(new_card)
            target_column.add_task(new_card)
            target_column.update_count(len(target_column.get_tasks()))

            self.page.update_statistics()
            self.page.taskUpdated.emit()
            QMessageBox.information(self.page, "Успех", "Задача отмечена как выполненная")
        else:
            QMessageBox.warning(self.page, "Ошибка", "Не удалось отметить задачу как выполненную")

    # windows/other_tasks/others_tasks_handlers.py

    def on_task_dropped(self, task_id: int, target_column_id: int):
        """Обработчик drop из KanbanColumn"""
        target_column = None
        for col in self.page.column_widgets:
            if col.column_id == target_column_id:
                target_column = col
                break

        if not target_column:
            return

        new_status = target_column.column_name
        task = self.page.service.get_task_by_id(task_id)
        if not task:
            return

        old_status = task.get("status")
        if old_status == new_status:
            return

        # Проверяем права (суперадмин всегда может)
        if not self.page._can_edit_or_delete_task(task.get("created_by")):
            QMessageBox.warning(self.page, "Ошибка", "У вас нет прав для перемещения этой задачи")
            return

        result = self.page.service.move_task_to_column(task_id, target_column_id)

        if result:
            self.page.update_task_card(result)
            self.page.update_statistics()
            self.page.taskUpdated.emit()
            # Не перезагружаем все задачи, просто обновляем карточку
            self.page.updateGeometry()
        else:
            QMessageBox.warning(self.page, "Ошибка", "Не удалось переместить задачу")

    def on_create_task(self):
        """Создание новой задачи"""
        from windows.other_tasks.task_dialog import TaskDialog

        dialog = TaskDialog(
            self.page,
            mode="create",
            current_user=self.page.current_user
        )
        dialog.set_service(self.page.service)
        dialog.task_saved.connect(self._on_task_created)
        dialog.exec()

    def _on_task_created(self, task_id: int, form_data: dict):
        """Обработчик создания задачи"""
        try:
            new_task = self.page.service.create_task(form_data)
            if new_task:
                self.page.add_task_card(new_task)
                self.page.update_statistics()
                self.page.taskUpdated.emit()
        except Exception as e:
            QMessageBox.critical(self.page, "Ошибка", f"Не удалось создать задачу: {str(e)}")

    def on_project_clicked(self, project_id: int):
        """Обработчик клика по проекту"""
        self.page.open_project_requested.emit(project_id)

    # ==========================================================
    # ФИЛЬТРАЦИЯ
    # ==========================================================

    def filter_tasks(self, priority: str, project_id: Optional[int]):
        """Фильтрация задач по приоритету и проекту"""
        all_tasks = []
        for column in self.page.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered_ids = self.page.service.crud.filter_tasks_by_priority_and_project_ids(
            all_tasks, priority, project_id
        )

        for column in self.page.column_widgets:
            for card in column.get_tasks():
                card.setVisible(card.task_data.get("id") in filtered_ids)