# windows/projects/project_edit_dialog.py

from windows.projects.base_project_dialog import BaseProjectDialog
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QDate


class ProjectEditDialog(BaseProjectDialog):
    """Диалог редактирования проекта"""

    def __init__(self, project_data, parent=None, service=None):
        self.original_data = project_data
        self.project_id = None
        self.permission_service = None  # Будет передан извне
        self._is_readonly_mode = False  # Флаг для режима просмотра

        super().__init__(parent, title="Редактирование проекта", project_data=project_data, service=service)

        project_name = project_data.get('name', '')
        self.setWindowTitle(f"Редактирование проекта: {project_name}")
        self.titleLabel.setText("Редактирование проекта")
        self.createBtn.setText("Сохранить изменения")

        # Устанавливаем дату
        created_date = project_data.get('created_date', '')
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        if created_date:
            self.dateLabel.setText(f"Создан: {created_date} | Изменен: {current_date}")
        else:
            self.dateLabel.setText(f"Изменен: {current_date}")

        self.createBtn.clicked.connect(self._on_save)

    # windows/projects/project_edit_dialog.py

    def setup_edit_mode(self, project_id: int):
        """Настраивает диалог в режиме редактирования/просмотра"""
        self.project_id = project_id

        # Проверяем права на редактирование
        if self.permission_service:
            can_edit = self.permission_service.can_edit_project(project_id)
            print(f"🔍 ProjectEditDialog: can_edit={can_edit}")

            if not can_edit:
                # Режим только для просмотра
                self._is_readonly_mode = True
                self.setWindowTitle(f"Просмотр проекта: {self.project_data.get('name', '')}")
                self.titleLabel.setText("Просмотр проекта")
                self.createBtn.setText("Закрыть")
                self.createBtn.setEnabled(True)

                # Отключаем поля ввода
                self._set_fields_readonly(True)

                # Меняем обработчик кнопки
                try:
                    self.createBtn.clicked.disconnect()
                except:
                    pass
                self.createBtn.clicked.connect(self.reject)
            else:
                # Режим редактирования
                self._is_readonly_mode = False
                self._set_fields_readonly(False)
                self.createBtn.setText("Сохранить изменения")
                try:
                    self.createBtn.clicked.disconnect()
                except:
                    pass
                self.createBtn.clicked.connect(self._on_save)

    def _set_fields_readonly(self, readonly: bool):
        """Устанавливает режим только для чтения для полей ввода (НЕ отключает кнопки)"""
        # Отключаем поля ввода
        if hasattr(self, 'nameInput'):
            self.nameInput.setReadOnly(readonly)
        if hasattr(self, 'descInput'):
            self.descInput.setReadOnly(readonly)
        if hasattr(self, 'activeCheckbox'):
            self.activeCheckbox.setEnabled(not readonly)
        if hasattr(self, 'comboManager'):
            self.comboManager.setEnabled(not readonly)

        # ВАЖНО: НЕ отключаем кнопки участников и администраторов!
        # Они должны оставаться кликабельными для просмотра
        # if hasattr(self, 'participantsBtn'):
        #     self.participantsBtn.setEnabled(not readonly)
        # if hasattr(self, 'adminsBtn'):
        #     self.adminsBtn.setEnabled(not readonly)

        # Отключаем чекбоксы колонок
        for checkbox in self.column_checkboxes.values():
            checkbox.setEnabled(not readonly)

    def select_participants(self):
        """Переопределяем выбор участников - в режиме просмотра открываем только для чтения"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        dialog = EmployeeSelectorDialog(self, service=self.project_service, mode="participants")
        if self.participants:
            preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
            dialog.set_preselected(preselected_ids)

        # Если режим просмотра - включаем read-only
        if self._is_readonly_mode:
            dialog.set_readonly_mode(True)
            dialog.setWindowTitle("Участники проекта (просмотр)")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # В режиме просмотра не сохраняем изменения
            if not self._is_readonly_mode:
                self.participants = dialog.get_selected_employees()
                self._update_participants_button_text()

    def select_admins(self):
        """Переопределяем выбор администраторов - в режиме просмотра открываем только для чтения"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        dialog = EmployeeSelectorDialog(self, service=self.project_service, mode="admins")
        if self.admins:
            preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
            dialog.set_preselected(preselected_ids)

        # Если режим просмотра - включаем read-only
        if self._is_readonly_mode:
            dialog.set_readonly_mode(True)
            dialog.setWindowTitle("Администраторы проекта (просмотр)")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # В режиме просмотра не сохраняем изменения
            if not self._is_readonly_mode:
                self.admins = dialog.get_selected_employees()
                self._update_admins_button_text()

    def load_project_data(self):
        """Загружает данные для редактирования"""
        super().load_project_data()

        # Убеждаемся, что администраторы включены в участников
        self.participants = self.dialog_service.ensure_admins_in_participants(
            self.participants, self.admins
        )
        self._update_participants_button_text()

    def _on_save(self):
        """Обработчик сохранения изменений"""
        if not self.validate_input():
            return

        current_data = self.get_project_data()

        if self.dialog_service.compare_changes(self.original_data, current_data):
            self.accept()
        else:
            reply = QMessageBox.question(
                self, "Нет изменений",
                "Вы не внесли изменений. Выйти без сохранения?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.reject()