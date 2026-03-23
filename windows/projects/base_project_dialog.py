# windows/projects/base_project_dialog.py

import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, pyqtSignal

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов создания и редактирования проектов"""

    # Сигнал для обновления карточек проектов
    columns_changed = pyqtSignal(dict)

    def __init__(self, parent=None, title="Проект", project_data=None):
        super().__init__(parent)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        self.project_data = project_data or {}
        self.participants = []
        self.admins = []

        # Словарь для хранения состояния видимости колонок
        self.column_visibility = {
            'name': True,
            'description': True,
            'status': True,
            'created_date': True,
            'deadline': True,
            'participants': True,
            'progress': True
        }

        # Базовая настройка UI
        self.setup_base_ui()
        self.setup_columns_ui()

        # Подключаем базовые сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

        # Подключаем сигналы чекбоксов колонок
        self.connect_column_signals()

        # Если есть данные проекта - загружаем их
        if project_data:
            self.load_project_data()
            # Загружаем сохраненные настройки колонок, если они есть
            if 'column_visibility' in project_data:
                self.load_column_visibility(project_data['column_visibility'])

    def setup_base_ui(self):
        """Базовая настройка UI"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Дата: {current_date}")

        # По умолчанию кнопка называется "Сохранить"
        self.createBtn.setText("Сохранить")

    def setup_columns_ui(self):
        """Настройка UI для колонок"""
        # Скрываем groupbox с колонками, если он не нужен
        if hasattr(self, 'columnsGroupBox'):
            # Можно добавить заголовок
            self.columnsGroupBox.setTitle("Отображаемые колонки в карточке проекта")

            # Устанавливаем тултипы для чекбоксов
            if hasattr(self, 'colNameCheckbox'):
                self.colNameCheckbox.setToolTip("Показывать название проекта в карточке")
            if hasattr(self, 'colDescriptionCheckbox'):
                self.colDescriptionCheckbox.setToolTip("Показывать описание проекта в карточке")
            if hasattr(self, 'colStatusCheckbox'):
                self.colStatusCheckbox.setToolTip("Показывать статус проекта в карточке")
            if hasattr(self, 'colCreatedDateCheckbox'):
                self.colCreatedDateCheckbox.setToolTip("Показывать дату создания в карточке")
            if hasattr(self, 'colDeadlineCheckbox'):
                self.colDeadlineCheckbox.setToolTip("Показывать дедлайн в карточке")
            if hasattr(self, 'colParticipantsCheckbox'):
                self.colParticipantsCheckbox.setToolTip("Показывать количество участников в карточке")
            if hasattr(self, 'colProgressCheckbox'):
                self.colProgressCheckbox.setToolTip("Показывать прогресс выполнения в карточке")

    def connect_column_signals(self):
        """Подключение сигналов чекбоксов колонок"""
        if hasattr(self, 'colNameCheckbox'):
            self.colNameCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('name', self.colNameCheckbox.isChecked())
            )
        if hasattr(self, 'colDescriptionCheckbox'):
            self.colDescriptionCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('description', self.colDescriptionCheckbox.isChecked())
            )
        if hasattr(self, 'colStatusCheckbox'):
            self.colStatusCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('status', self.colStatusCheckbox.isChecked())
            )
        if hasattr(self, 'colCreatedDateCheckbox'):
            self.colCreatedDateCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('created_date', self.colCreatedDateCheckbox.isChecked())
            )
        if hasattr(self, 'colDeadlineCheckbox'):
            self.colDeadlineCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('deadline', self.colDeadlineCheckbox.isChecked())
            )
        if hasattr(self, 'colParticipantsCheckbox'):
            self.colParticipantsCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('participants', self.colParticipantsCheckbox.isChecked())
            )
        if hasattr(self, 'colProgressCheckbox'):
            self.colProgressCheckbox.stateChanged.connect(
                lambda: self.on_column_changed('progress', self.colProgressCheckbox.isChecked())
            )

    def on_column_changed(self, column_name, checked):
        """Обработчик изменения состояния чекбокса колонки"""
        self.column_visibility[column_name] = checked
        print(f"📊 Колонка '{column_name}' {'показана' if checked else 'скрыта'}")

    def load_column_visibility(self, visibility_dict):
        """Загрузка состояния видимости колонок из сохраненных данных"""
        if not visibility_dict:
            return

        # Обновляем словарь
        self.column_visibility.update(visibility_dict)

        # Обновляем чекбоксы
        if hasattr(self, 'colNameCheckbox'):
            self.colNameCheckbox.setChecked(self.column_visibility.get('name', True))
        if hasattr(self, 'colDescriptionCheckbox'):
            self.colDescriptionCheckbox.setChecked(self.column_visibility.get('description', True))
        if hasattr(self, 'colStatusCheckbox'):
            self.colStatusCheckbox.setChecked(self.column_visibility.get('status', True))
        if hasattr(self, 'colCreatedDateCheckbox'):
            self.colCreatedDateCheckbox.setChecked(self.column_visibility.get('created_date', True))
        if hasattr(self, 'colDeadlineCheckbox'):
            self.colDeadlineCheckbox.setChecked(self.column_visibility.get('deadline', True))
        if hasattr(self, 'colParticipantsCheckbox'):
            self.colParticipantsCheckbox.setChecked(self.column_visibility.get('participants', True))
        if hasattr(self, 'colProgressCheckbox'):
            self.colProgressCheckbox.setChecked(self.column_visibility.get('progress', True))

    def get_column_visibility(self):
        """Получить словарь с настройками видимости колонок"""
        return self.column_visibility.copy()

    def load_project_data(self):
        """Загрузка данных проекта"""
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
        if hasattr(self.project_data, 'member_ids'):
            # Это DTO объект
            member_ids = self.project_data.member_ids
            admin_ids = self.project_data.admin_ids

            self.participants = []
            self.admins = []

            if member_ids:
                from database import get_tasks_session
                from models.employees import ExternalEmployee
                from sqlalchemy import select

                session = get_tasks_session()

                # Загружаем участников
                stmt = select(ExternalEmployee).where(ExternalEmployee.id.in_(member_ids))
                employees = session.scalars(stmt).all()

                for emp in employees:
                    emp_dict = {
                        'id': emp.id,
                        'last_name': emp.last_name,
                        'first_name': emp.first_name,
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or 'Сотрудник',
                        'phone': emp.phone_number or ''
                    }
                    self.participants.append(emp_dict)
                    if emp.id in admin_ids:
                        self.admins.append(emp_dict)

                session.close()
        else:
            # Это словарь
            participants_data = self.project_data.get('participants', [])
            self.participants = self._normalize_employee_data(participants_data)

            admins_data = self.project_data.get('admins', [])
            self.admins = self._normalize_employee_data(admins_data)

        self.update_participants_button_text()
        self.update_admins_button_text()

    def _normalize_employee_data(self, data):
        """Приведение данных сотрудников к единому формату"""
        if not data:
            return []

        if isinstance(data, str):
            ids = [int(id.strip()) for id in data.split(',') if id.strip()]
            return [self._create_employee_stub(emp_id) for emp_id in ids]

        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    if 'id' in item:
                        if 'first_name' not in item:
                            item['first_name'] = f"User{item['id']}"
                        if 'last_name' not in item:
                            item['last_name'] = f"LastName{item['id']}"
                        normalized.append(item)
                elif isinstance(item, int):
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

            if self.participants:
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
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе участников: {e}")

    def select_admins(self):
        """Открыть диалог выбора администраторов"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, mode="admins")

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
                first_name = emp.get('first_name', '')
                last_name = emp.get('last_name', '')
                if first_name and last_name:
                    short_name = f"{last_name} {first_name[0]}."
                else:
                    short_name = f"ID: {emp.get('id', '')}"
                self.participantsBtn.setText(f"Участник: {short_name}")
            else:
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
                first_name = emp.get('first_name', '')
                last_name = emp.get('last_name', '')
                if first_name and last_name:
                    short_name = f"{last_name} {first_name[0]}."
                else:
                    short_name = f"ID: {emp.get('id', '')}"
                self.adminsBtn.setText(f"Администратор: {short_name}")
            else:
                self.adminsBtn.setText(f"Администратор: ID {emp}")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def validate_input(self):
        """Проверка введенных данных"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False
        return True

    def get_common_data(self):
        """Получить общие данные проекта"""
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
            'participants': self.participants,
            'admins_ids': admins_str,
            'admins': self.admins,
            'is_active': self.activeCheckbox.isChecked(),
            'updated_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'column_visibility': self.get_column_visibility()  # 👈 Добавляем настройки колонок
        }