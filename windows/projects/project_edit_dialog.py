# windows/projects/project_edit_dialog.py

import os
import sys
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QDate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from windows.projects.base_project_dialog import BaseProjectDialog


class ProjectEditDialog(BaseProjectDialog):
    """Диалог редактирования существующего проекта"""

    def __init__(self, project_data, parent=None):
        super().__init__(parent, title="Редактирование проекта", project_data=project_data)

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
        """Загрузка данных для редактирования"""
        super().load_project_data()

        # Загружаем сохраненные колонки
        if 'selected_columns_data' in self.project_data:
            self.selected_columns_data = self.project_data['selected_columns_data']
            self.selected_columns_keys = [col.get('col_key', '') for col in self.selected_columns_data]
            self.update_columns_button_text()

        self._ensure_admins_in_participants()

    def _ensure_admins_in_participants(self):
        """Убеждаемся, что администраторы также являются участниками"""
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

        # Добавляем администраторов в участники, если их там нет
        for admin_id in admin_ids:
            if admin_id not in participant_ids:
                admin_stub = self._create_employee_stub(admin_id)
                self.participants.append(admin_stub)

        self.update_participants_button_text()
        self.update_admins_button_text()

    def validate_and_accept(self):
        """Проверка данных и закрытие диалога"""
        if self.validate_input():
            if self.has_changes():
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

    def has_changes(self):
        """Проверка, были ли внесены изменения"""
        original = self.project_data
        current = self.get_common_data()

        # Сравниваем основные поля
        if original.get('name') != current['name']:
            return True
        if original.get('description') != current['description']:
            return True
        if original.get('is_active') != current['is_active']:
            return True

        # 👇 ИСПРАВЛЯЕМ: убираем проверку column_visibility
        # Сравниваем выбранные колонки
        original_columns = original.get('selected_columns_data', [])
        current_columns = self.selected_columns_data
        if len(original_columns) != len(current_columns):
            return True

        # Сравниваем ID колонок
        original_col_ids = set([col.get('id') for col in original_columns if col.get('id')])
        current_col_ids = set([col.get('id') for col in current_columns if col.get('id')])
        if original_col_ids != current_col_ids:
            return True

        # Сравниваем участников
        original_participants = self._extract_ids(original.get('participants', []))
        current_participants = self._extract_ids(self.participants)
        if set(original_participants) != set(current_participants):
            return True

        # Сравниваем администраторов
        original_admins = self._extract_ids(original.get('admins', []))
        current_admins = self._extract_ids(self.admins)
        if set(original_admins) != set(current_admins):
            return True

        return False

    def _extract_ids(self, data):
        """Извлечение ID из данных участников/администраторов"""
        if isinstance(data, str):
            return [int(id.strip()) for id in data.split(',') if id.strip()]
        elif isinstance(data, list):
            ids = []
            for item in data:
                if isinstance(item, dict):
                    ids.append(item.get('id'))
                elif isinstance(item, int):
                    ids.append(item)
            return ids
        return []

    def get_project_data(self):
        """Получить обновленные данные проекта"""
        data = self.get_common_data()

        # Сохраняем оригинальный ID и дату создания
        data['id'] = self.project_data.get('id')
        data['created_date'] = self.project_data.get('created_date',
                                                     QDate.currentDate().toString("dd.MM.yyyy"))

        # 👇 ДОБАВЛЯЕМ ВЫБРАННЫЕ КОЛОНКИ
        data['selected_columns_data'] = self.selected_columns_data
        data['selected_columns'] = self.selected_columns_keys

        return data