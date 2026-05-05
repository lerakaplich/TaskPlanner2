# windows/projects/project_edit_dialog.py

import os
import sys
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QDate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from windows.projects.base_project_dialog import BaseProjectDialog


class ProjectEditDialog(BaseProjectDialog):
    """Диалог редактирования существующего проекта - только UI, логика в сервисе"""

    def __init__(self, project_data, parent=None, service=None):
        self.original_data = project_data
        self.service = service

        super().__init__(parent, title="Редактирование проекта", project_data=project_data, service=service)

        # Настройка UI для редактирования
        self.setup_edit_ui()

        # Подключаем сигнал сохранения
        self.createBtn.clicked.connect(self.validate_and_accept)

    def setup_edit_ui(self):
        """Настройка UI для режима редактирования"""
        project_name = self.project_data.get('name', '')
        self.setWindowTitle(f"Редактирование проекта: {project_name}")
        self.titleLabel.setText("Редактирование проекта")
        self.createBtn.setText("Сохранить изменения")

        # Устанавливаем дату изменения
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        created_date = self.project_data.get('created_date', '')
        if created_date:
            self.dateLabel.setText(f"Создан: {created_date} | Изменен: {current_date}")
        else:
            self.dateLabel.setText(f"Изменен: {current_date}")

    def load_project_data(self):
        """Загрузка данных для редактирования (вызывается из родителя)"""
        super().load_project_data()

        # Загружаем сохраненные колонки
        if 'selected_columns_data' in self.project_data:
            self.selected_columns_data = self.project_data['selected_columns_data']
            self.selected_columns_keys = [col.get('col_key', '') for col in self.selected_columns_data]
            self.update_columns_button_text()

        # Убеждаемся, что администраторы также являются участниками
        if self.service:
            self.participants = self.service.ensure_admins_in_participants(self.participants, self.admins)
        else:
            self._ensure_admins_in_participants()

        self.update_participants_button_text()
        self.update_admins_button_text()

    def _ensure_admins_in_participants(self):
        """Fallback: убеждаемся, что администраторы также являются участниками"""
        admin_ids = set()
        for admin in self.admins:
            if isinstance(admin, dict):
                admin_ids.add(admin.get('id'))
            else:
                admin_ids.add(admin)

        participant_ids = set()
        for participant in self.participants:
            if isinstance(participant, dict):
                participant_ids.add(participant.get('id'))
            else:
                participant_ids.add(participant)

        for admin_id in admin_ids:
            if admin_id not in participant_ids:
                admin_stub = self._create_employee_stub(admin_id)
                self.participants.append(admin_stub)

    def validate_and_accept(self):
        """Проверка данных через сервис и закрытие диалога"""
        if not self.service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        # Получаем данные из UI
        current_data = self.get_raw_ui_data()

        # Валидация через сервис
        error = self.service.validate_project_data(current_data)
        if error:
            QMessageBox.warning(self, "Ошибка", error)
            return

        # Проверяем, были ли изменения
        if self.service.compare_project_changes(self.original_data, current_data):
            self.accept()
        else:
            reply = QMessageBox.question(
                self,
                "Нет изменений",
                "Вы не внесли изменений. Выйти без сохранения?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.reject()

    def get_raw_ui_data(self) -> dict:
        """
        Получает сырые данные из UI
        """
        participants_ids = []
        for p in self.participants:
            emp_id = p.get('id') if isinstance(p, dict) else p
            if emp_id:
                participants_ids.append(str(emp_id))

        admins_ids = []
        for a in self.admins:
            emp_id = a.get('id') if isinstance(a, dict) else a
            if emp_id:
                admins_ids.append(str(emp_id))

        return {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'is_active': self.activeCheckbox.isChecked(),
            'participants_ids': ','.join(participants_ids),
            'admins_ids': ','.join(admins_ids),
            'participants': self.participants,
            'admins': self.admins,
            'selected_columns_data': self.selected_columns_data,
            'selected_columns_keys': self.selected_columns_keys,
            'manager_id': self.get_manager_id(),
            'manager_name': self.get_manager_name(),
        }

    def get_project_data(self):
        """
        Возвращает подготовленные данные для обновления проекта
        (используется в MainWindow)
        """
        raw_data = self.get_raw_ui_data()

        # Добавляем ID проекта и дату создания
        raw_data['id'] = self.project_data.get('id')
        raw_data['created_date'] = self.project_data.get('created_date', QDate.currentDate().toString("dd.MM.yyyy"))

        # Добавляем колонки
        raw_data['selected_columns'] = self.selected_columns_keys
        raw_data['selected_columns_data'] = self.selected_columns_data
        raw_data['columns_display_names'] = {col['col_key']: col['name'] for col in self.selected_columns_data}

        return raw_data