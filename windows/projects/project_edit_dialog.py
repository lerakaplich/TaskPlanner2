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
        """Переопределяем загрузку данных для редактирования"""
        super().load_project_data()

        # Дополнительная логика для редактирования
        # Например, можно проверить, что администраторы являются также участниками
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
                # Создаем заглушку для администратора
                admin_stub = self._create_employee_stub(admin_id)
                self.participants.append(admin_stub)

        # Обновляем текст на кнопках
        self.update_participants_button_text()
        self.update_admins_button_text()

    def validate_and_accept(self):
        """Проверка данных и закрытие диалога"""
        if self.validate_input():
            # Дополнительная проверка для редактирования
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

        # Сравниваем участников (по ID)
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

        return data

    # Добавьте этот метод в класс ProjectEditDialog в project_edit_dialog.py

    def _format_employee_name(self, emp):
        """Форматирование имени сотрудника для отображения"""
        if isinstance(emp, dict):
            first_name = emp.get('first_name', '')
            last_name = emp.get('last_name', '')
            if first_name and last_name:
                return f"{last_name} {first_name[0]}."
            else:
                return f"ID: {emp.get('id', '')}"
        else:
            return f"ID: {emp}"


# Для тестирования
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Тестовые данные для редактирования (разные форматы)
    test_project = {
        'id': 1,
        'name': 'Task Planner',
        'description': 'Планировщик задач для команды',
        'is_active': True,
        'created_date': '01.02.2026',
        'participants': [1, 2, 3],  # Только ID
        'admins': [1]  # Только ID
    }

    dialog = ProjectEditDialog(test_project)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_project_data()
        print("\n" + "=" * 50)
        print("ОБНОВЛЕННЫЕ ДАННЫЕ ПРОЕКТА:")
        print("=" * 50)
        print(f"ID: {data['id']}")
        print(f"Название: {data['name']}")
        print(f"Описание: {data['description']}")
        print(f"Активен: {data['is_active']}")
        print(f"Создан: {data['created_date']}")
        print(f"ID участников: {data['participants_ids'] or 'не выбраны'}")
        print(f"ID администраторов: {data['admins_ids'] or 'не выбраны'}")
        print("=" * 50)

    sys.exit(app.exec())