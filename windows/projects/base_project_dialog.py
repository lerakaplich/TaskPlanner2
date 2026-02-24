# windows/projects/base_project_dialog.py

import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов создания и редактирования проектов"""

    def __init__(self, parent=None, title="Проект", project_data=None):
        super().__init__(parent)

        # Загрузка UI (один и тот же файл для создания и редактирования)
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        self.project_data = project_data or {}
        self.participants = []  # Список выбранных участников (полные данные)
        self.admins = []  # Список выбранных администраторов (полные данные)

        # Базовая настройка UI
        self.setup_base_ui()

        # Подключаем базовые сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

        # Если есть данные проекта - загружаем их
        if project_data:
            self.load_project_data()

    def setup_base_ui(self):
        """Базовая настройка UI (может быть переопределена)"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Дата: {current_date}")

        # По умолчанию кнопка называется "Сохранить" (для редактирования)
        # Будет переопределено в наследниках
        self.createBtn.setText("Сохранить")

    def load_project_data(self):
        """Загрузка данных проекта (общая логика)"""
        self.nameInput.setText(self.project_data.get('name', ''))
        self.descInput.setPlainText(self.project_data.get('description', ''))

        # Загружаем статус активности
        is_active = self.project_data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        self.activeCheckbox.setChecked(is_active)

        # Загружаем участников и администраторов
        self.load_participants_and_admins()

    def load_participants_and_admins(self):
        """Загрузка участников и администраторов из project_data"""
        # Загружаем участников
        participants_data = self.project_data.get('participants', [])
        self.participants = self._normalize_employee_data(participants_data)

        # Загружаем администраторов
        admins_data = self.project_data.get('admins', [])
        self.admins = self._normalize_employee_data(admins_data)

        self.update_participants_button_text()
        self.update_admins_button_text()

    def _normalize_employee_data(self, data):
        """
        Приводит данные сотрудников к единому формату (список словарей)
        Поддерживает:
        - список словарей с ключами 'id', 'first_name', 'last_name'
        - список целых чисел (ID)
        - строку с ID через запятую
        """
        if not data:
            return []

        # Если это строка с ID через запятую
        if isinstance(data, str):
            ids = [int(id.strip()) for id in data.split(',') if id.strip()]
            return [self._create_employee_stub(emp_id) for emp_id in ids]

        # Если это список
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    # Уже словарь - проверяем наличие нужных ключей
                    if 'id' in item:
                        # Если нет first_name/last_name, создаем заглушки
                        if 'first_name' not in item:
                            item['first_name'] = f"User{item['id']}"
                        if 'last_name' not in item:
                            item['last_name'] = f"LastName{item['id']}"
                        normalized.append(item)
                elif isinstance(item, int):
                    # Это ID - создаем заглушку
                    normalized.append(self._create_employee_stub(item))
            return normalized

        return []

    def _create_employee_stub(self, emp_id):
        """Создает заглушку сотрудника по ID"""
        return {
            'id': emp_id,
            'first_name': f"User{emp_id}",
            'last_name': f"LastName{emp_id}",
            'position': 'Сотрудник'
        }

    def select_participants(self):
        """Открыть диалог выбора участников"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, mode="participants")

            # Предустанавливаем уже выбранных участников
            if self.participants:
                # Извлекаем ID из словарей
                preselected_ids = []
                for p in self.participants:
                    if isinstance(p, dict):
                        preselected_ids.append(p.get('id'))
                    else:
                        preselected_ids.append(p)
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.participants = dialog.get_selected_employees()
                self.update_participants_button_text()
        except ImportError as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить диалог выбора: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе участников: {e}")

    def select_admins(self):
        """Открыть диалог выбора администраторов"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, mode="admins")

            # Предустанавливаем уже выбранных администраторов
            if self.admins:
                preselected_ids = []
                for a in self.admins:
                    if isinstance(a, dict):
                        preselected_ids.append(a.get('id'))
                    else:
                        preselected_ids.append(a)
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.admins = dialog.get_selected_employees()
                self.update_admins_button_text()
        except ImportError as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить диалог выбора: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе администраторов: {e}")

    def update_participants_button_text(self):
        """Обновить текст на кнопке участников"""
        count = len(self.participants)
        if count == 0:
            self.participantsBtn.setText("Выбрать участников")
        elif count == 1:
            emp = self.participants[0]
            if isinstance(emp, dict):
                # Формируем краткое имя из словаря
                first_name = emp.get('first_name', '')
                last_name = emp.get('last_name', '')
                if first_name and last_name:
                    short_name = f"{last_name} {first_name[0]}."
                else:
                    short_name = f"ID: {emp.get('id', '')}"
                self.participantsBtn.setText(f"Участник: {short_name}")
            else:
                # Если это просто ID (число)
                self.participantsBtn.setText(f"Участник: ID {emp}")
        else:
            self.participantsBtn.setText(f"Участники ({count} чел.)")

    def update_admins_button_text(self):
        """Обновить текст на кнопке администраторов"""
        count = len(self.admins)
        if count == 0:
            self.adminsBtn.setText("Выбрать администраторов")
        elif count == 1:
            emp = self.admins[0]
            if isinstance(emp, dict):
                # Формируем краткое имя из словаря
                first_name = emp.get('first_name', '')
                last_name = emp.get('last_name', '')
                if first_name and last_name:
                    short_name = f"{last_name} {first_name[0]}."
                else:
                    short_name = f"ID: {emp.get('id', '')}"
                self.adminsBtn.setText(f"Администратор: {short_name}")
            else:
                # Если это просто ID (число)
                self.adminsBtn.setText(f"Администратор: ID {emp}")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def validate_input(self):
        """Проверка введенных данных (может быть переопределена)"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False
        return True

    def get_common_data(self):
        """Получить общие данные проекта (используется в create и edit)"""
        # Преобразуем списки ID в строки через запятую для сохранения
        participants_ids = []
        for p in self.participants:
            if isinstance(p, dict):
                participants_ids.append(str(p.get('id', '')))
            else:
                participants_ids.append(str(p))
        participants_str = ','.join(participants_ids) if participants_ids else ''

        admins_ids = []
        for a in self.admins:
            if isinstance(a, dict):
                admins_ids.append(str(a.get('id', '')))
            else:
                admins_ids.append(str(a))
        admins_str = ','.join(admins_ids) if admins_ids else ''

        return {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'participants_ids': participants_str,
            'participants': self.participants,  # полные данные для отображения
            'admins_ids': admins_str,
            'admins': self.admins,  # полные данные для отображения
            'is_active': self.activeCheckbox.isChecked(),
            'updated_date': QDate.currentDate().toString("dd.MM.yyyy")
        }

    def _ids_to_employee_list(self, ids_string):
        """Преобразование строки с ID в список сотрудников"""
        if not ids_string:
            return []

        ids = [int(id.strip()) for id in ids_string.split(',') if id.strip()]
        return [self._create_employee_stub(emp_id) for emp_id in ids]