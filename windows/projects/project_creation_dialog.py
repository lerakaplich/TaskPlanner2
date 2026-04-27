# windows/projects/project_creation_dialog.py

import os
import sys
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QDate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from windows.projects.base_project_dialog import BaseProjectDialog


class ProjectCreationDialog(BaseProjectDialog):
    """Диалог создания нового проекта"""

    def __init__(self, parent=None):
        super().__init__(parent, title="Создание проекта")

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
        """Проверка данных и закрытие диалога"""
        if self.validate_input():
            self.accept()

    def get_project_data(self):
        """Получить данные нового проекта"""
        data = self.get_common_data()

        data.update({
            'id': None,
            'created_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'selected_columns': self.selected_columns_keys,
            'selected_columns_data': self.selected_columns_data,
            'columns_display_names': {col['col_key']: col['name'] for col in self.selected_columns_data}
        })

        return data