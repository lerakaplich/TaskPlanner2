# windows/projects/project_edit_dialog.py
from windows.projects.base_project_dialog import BaseProjectDialog
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QDate


class ProjectEditDialog(BaseProjectDialog):
    """Диалог редактирования проекта"""

    def __init__(self, project_data, parent=None, service=None):
        self.original_data = project_data

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