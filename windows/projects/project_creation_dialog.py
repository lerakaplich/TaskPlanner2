# windows/projects/project_creation_dialog.py

import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt6.QtCore import QDate

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from windows.projects.employee_selector import EmployeeSelectorDialog


class ProjectCreationDialog(QDialog):
    def __init__(self, parent=None, project_data=None):
        """
        :param parent: родительский виджет
        :param project_data: данные проекта для редактирования (если None - создание нового)
        """
        super().__init__(parent)
        self.project_data = project_data
        self.participants = []  # Список выбранных участников
        self.admins = []  # Список выбранных администраторов

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/projects/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "projects"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        # Устанавливаем текущую дату
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")

        # Подключаем сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)
        self.createBtn.clicked.connect(self.validate_and_accept)

        # Если редактируем существующий проект, загружаем данные
        if project_data:
            self.load_project_data()
            self.createBtn.setText("Сохранить")
            self.dateLabel.setText(f"Изменен: {current_date}")

    def load_project_data(self):
        """Загрузка данных существующего проекта"""
        self.nameInput.setText(self.project_data.get('name', ''))
        self.descInput.setPlainText(self.project_data.get('description', ''))
        self.activeCheckbox.setChecked(self.project_data.get('is_active', True))

        # Загружаем участников и администраторов
        self.participants = self.project_data.get('participants', [])
        self.admins = self.project_data.get('admins', [])

        self.update_participants_button_text()
        self.update_admins_button_text()

    def select_participants(self):
        """Открыть диалог выбора участников"""
        dialog = EmployeeSelectorDialog(self, mode="participants")

        # Предустанавливаем уже выбранных участников
        if self.participants:
            dialog.set_preselected([p['id'] for p in self.participants])

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.participants = dialog.get_selected_employees()
            self.update_participants_button_text()

    def select_admins(self):
        """Открыть диалог выбора администраторов"""
        dialog = EmployeeSelectorDialog(self, mode="admins")

        # Предустанавливаем уже выбранных администраторов
        if self.admins:
            dialog.set_preselected([a['id'] for a in self.admins])

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.admins = dialog.get_selected_employees()
            self.update_admins_button_text()

    def update_participants_button_text(self):
        """Обновить текст на кнопке участников"""
        count = len(self.participants)
        if count == 0:
            self.participantsBtn.setText("Выбрать участников")
        elif count == 1:
            emp = self.participants[0]
            self.participantsBtn.setText(f"Участник: {emp['last_name']} {emp['first_name'][0]}.")
        else:
            self.participantsBtn.setText(f"Участники ({count} чел.)")

    def update_admins_button_text(self):
        """Обновить текст на кнопке администраторов"""
        count = len(self.admins)
        if count == 0:
            self.adminsBtn.setText("Выбрать администраторов")
        elif count == 1:
            emp = self.admins[0]
            self.adminsBtn.setText(f"Администратор: {emp['last_name']} {emp['first_name'][0]}.")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def validate_and_accept(self):
        """Проверка данных перед закрытием"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return

        self.accept()

    def get_project_data(self):
        """Получить данные проекта"""
        # Преобразуем списки ID в строки через запятую для сохранения
        participants_str = ','.join(str(p['id']) for p in self.participants) if self.participants else ''
        admins_str = ','.join(str(a['id']) for a in self.admins) if self.admins else ''

        # Для наглядности также возвращаем полные объекты
        return {
            'id': self.project_data.get('id') if self.project_data else None,
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'participants_ids': participants_str,
            'participants': self.participants,  # полные данные для отображения
            'admins_ids': admins_str,
            'admins': self.admins,  # полные данные для отображения
            'is_active': self.activeCheckbox.isChecked(),
            'created_date': QDate.currentDate().toString("dd.MM.yyyy")
        }


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Тестовые данные для редактирования
    test_project = {
        'id': 1,
        'name': 'Task Planner',
        'description': 'Планировщик задач для команды',
        'is_active': True,
        'participants': [],  # можно добавить тестовых участников
        'admins': []
    }

    # Создание нового проекта
    dialog = ProjectCreationDialog()
    # Для редактирования существующего проекта:
    # dialog = ProjectCreationDialog(project_data=test_project)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_project_data()
        print("\n" + "=" * 50)
        print("ДАННЫЕ ПРОЕКТА:")
        print("=" * 50)
        print(f"Название: {data['name']}")
        print(f"Описание: {data['description']}")
        print(f"Активен: {data['is_active']}")
        print(f"Дата: {data['created_date']}")
        print(f"ID участников: {data['participants_ids'] or 'не выбраны'}")
        print(f"ID администраторов: {data['admins_ids'] or 'не выбраны'}")

        if data['participants']:
            print("\nУчастники:")
            for p in data['participants']:
                print(f"  - {p['last_name']} {p['first_name']} ({p['position']})")

        if data['admins']:
            print("\nАдминистраторы:")
            for a in data['admins']:
                print(f"  - {a['last_name']} {a['first_name']} ({a['position']})")
        print("=" * 50)

    sys.exit(app.exec())