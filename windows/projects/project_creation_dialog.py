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

        # По умолчанию все колонки включены
        self.set_default_columns()

    def set_default_columns(self):
        """Устанавливаем колонки по умолчанию (все выбраны)"""
        self.colNameCheckbox.setChecked(True)
        self.colDescriptionCheckbox.setChecked(True)
        self.colStatusCheckbox.setChecked(True)
        self.colCreatedDateCheckbox.setChecked(True)
        self.colDeadlineCheckbox.setChecked(True)
        self.colParticipantsCheckbox.setChecked(True)
        self.colProgressCheckbox.setChecked(True)

    def get_selected_columns(self):
        """Получить список выбранных колонок"""
        columns = []

        if self.colNameCheckbox.isChecked():
            columns.append('name')
        if self.colDescriptionCheckbox.isChecked():
            columns.append('description')
        if self.colStatusCheckbox.isChecked():
            columns.append('status')
        if self.colCreatedDateCheckbox.isChecked():
            columns.append('created_date')
        if self.colDeadlineCheckbox.isChecked():
            columns.append('deadline')
        if self.colParticipantsCheckbox.isChecked():
            columns.append('participants_count')
        if self.colProgressCheckbox.isChecked():
            columns.append('progress')

        return columns

    def get_columns_display_names(self):
        """Получить отображаемые названия выбранных колонок"""
        columns_display = {}

        if self.colNameCheckbox.isChecked():
            columns_display['name'] = 'Название проекта'
        if self.colDescriptionCheckbox.isChecked():
            columns_display['description'] = 'Описание проекта'
        if self.colStatusCheckbox.isChecked():
            columns_display['status'] = 'Статус проекта'
        if self.colCreatedDateCheckbox.isChecked():
            columns_display['created_date'] = 'Дата создания'
        if self.colDeadlineCheckbox.isChecked():
            columns_display['deadline'] = 'Дедлайн'
        if self.colParticipantsCheckbox.isChecked():
            columns_display['participants_count'] = 'Участники'
        if self.colProgressCheckbox.isChecked():
            columns_display['progress'] = 'Прогресс'

        return columns_display

    def validate_and_accept(self):
        """Проверка данных и закрытие диалога"""
        if self.validate_input():
            # Проверяем, что выбрана хотя бы одна колонка
            if not self.get_selected_columns():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Предупреждение",
                                    "Выберите хотя бы одну колонку для отображения в проекте!")
                return
            self.accept()

    def get_project_data(self):
        """Получить данные нового проекта"""
        data = self.get_common_data()

        # Добавляем специфичные для создания поля
        data.update({
            'id': None,
            'created_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'selected_columns': self.get_selected_columns(),
            'columns_display_names': self.get_columns_display_names()
        })

        # Отладочный вывод
        print("\n=== ДАННЫЕ ДЛЯ СОЗДАНИЯ ПРОЕКТА ===")
        print(f"Название: {data['name']}")
        print(f"Описание: {data['description']}")
        print(f"Активен: {data['is_active']}")
        print(f"Участники (ID): {data['participants_ids']}")
        print(f"Администраторы (ID): {data['admins_ids']}")
        print(f"Выбранные колонки: {data['selected_columns']}")
        print(f"Названия колонок: {data['columns_display_names']}")
        print("\n📊 Настройки колонок:")
        for col, visible in data['column_visibility'].items():
            status = "✅" if visible else "❌"
            print(f"  {status} {col}")
        print("=" * 40)

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
        print(f"Выбранные колонки: {data['selected_columns']}")
        print("\n📊 ВИДИМОСТЬ КОЛОНОК:")
        for col, visible in data['column_visibility'].items():
            status = "✓" if visible else "✗"
            print(f"  {status} {col}")
        print("=" * 50)

    sys.exit(app.exec())