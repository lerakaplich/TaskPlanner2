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

        # Настройка UI для создания
        self.setup_creation_ui()

        # Подключаем сигнал создания
        self.createBtn.clicked.connect(self.validate_and_accept)

    def setup_creation_ui(self):
        """Настройка UI для режима создания"""
        self.setWindowTitle("Создание проекта")
        self.titleLabel.setText("Создание проекта")
        self.createBtn.setText("Создать проект")

        # Устанавливаем текущую дату создания
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")

        # По умолчанию проект активен
        self.activeCheckbox.setChecked(True)

    def validate_and_accept(self):
        """Проверка данных и закрытие диалога"""
        if self.validate_input():
            self.accept()

    def get_project_data(self):
        """Получить данные нового проекта"""
        data = self.get_common_data()

        # Добавляем специфичные для создания поля
        data.update({
            'id': None,  # ID будет присвоен при сохранении в БД
            'created_date': QDate.currentDate().toString("dd.MM.yyyy")
        })

        return data


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = ProjectCreationDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_project_data()
        print("\n" + "=" * 50)
        print("ДАННЫЕ НОВОГО ПРОЕКТА:")
        print("=" * 50)
        print(f"Название: {data['name']}")
        print(f"Описание: {data['description']}")
        print(f"Активен: {data['is_active']}")
        print(f"Создан: {data['created_date']}")
        print(f"ID участников: {data['participants_ids'] or 'не выбраны'}")
        print(f"ID администраторов: {data['admins_ids'] or 'не выбраны'}")
        print("=" * 50)

    sys.exit(app.exec())