# windows/projects/project_creation_dialog.py

import os
import sys
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from windows.projects.base_project_dialog import BaseProjectDialog


class ProjectCreationDialog(BaseProjectDialog):
    """Диалог создания нового проекта - только UI, логика в сервисе"""

    def __init__(self, parent=None, service=None, creator_id=None):
        self.service = service
        self.creator_id = creator_id

        # Вызываем конструктор родителя без service (передадим позже)
        super().__init__(parent, title="Создание проекта", service=service)

        self.setup_creation_ui()
        self.createBtn.clicked.connect(self.validate_and_accept)

    def setup_creation_ui(self):
        """Настройка UI для режима создания"""
        self.setWindowTitle("Создание проекта")
        self.titleLabel.setText("Создание проекта")
        self.createBtn.setText("Создать проект")

        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")
        self.activeCheckbox.setChecked(True)

    def validate_and_accept(self):
        """Проверка данных через сервис и закрытие диалога"""
        if not self.service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        # Получаем данные из UI
        raw_data = self.get_raw_ui_data()

        # Валидация через сервис
        error = self.service.validate_project_data(raw_data)
        if error:
            QMessageBox.warning(self, "Ошибка", error)
            return

        self.accept()

    def get_raw_ui_data(self) -> dict:
        """
        Получает сырые данные из UI без преобразований
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

        # Получаем ключи выбранных колонок
        selected_column_keys = [col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                                for col in self.selected_columns_data]

        return {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'is_active': self.activeCheckbox.isChecked(),
            'participants_ids': ','.join(participants_ids),
            'admins_ids': ','.join(admins_ids),
            'selected_columns_data': self.selected_columns_data,  # Данные выбранных колонок
            'selected_columns': selected_column_keys,  # Ключи выбранных колонок
            'manager_id': self.get_manager_id(),
        }

    def get_project_data(self):
        """
        Возвращает подготовленные данные для создания проекта
        (используется в MainWindow)
        """
        if not self.service:
            return {}

        raw_data = self.get_raw_ui_data()
        prepared_data = self.service.prepare_project_data_for_creation(raw_data, self.creator_id)

        # Добавляем дату создания и отображение названий колонок
        prepared_data.update({
            'id': None,
            'created_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'columns_display_names': {col['col_key']: col['name'] for col in self.selected_columns_data}
        })

        # Добавляем информацию о кураторе
        manager_id = self.get_manager_id()
        if manager_id:
            prepared_data['manager_id'] = manager_id
            prepared_data['manager_name'] = self.get_manager_name()

        # Добавляем списки ID участников и администраторов для создания чата
        participants_ids = []
        for p in self.participants:
            emp_id = p.get('id') if isinstance(p, dict) else p
            if emp_id:
                participants_ids.append(emp_id)
        prepared_data['participants_ids_list'] = participants_ids

        admins_ids = []
        for a in self.admins:
            emp_id = a.get('id') if isinstance(a, dict) else a
            if emp_id:
                admins_ids.append(emp_id)
        prepared_data['admins_ids_list'] = admins_ids

        return prepared_data