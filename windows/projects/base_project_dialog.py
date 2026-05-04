# windows/projects/base_project_dialog.py

import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtCore import QDate, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов создания и редактирования проектов"""

    columns_changed = pyqtSignal(dict)

    def __init__(self, parent=None, title="Проект", project_data=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        self.project_data = project_data or {}
        self.participants = []
        self.admins = []

        # Хранение выбранных колонок
        self.selected_columns_data = []
        self.selected_columns_keys = []

        # Сначала загружаем шаблонные колонки
        self.template_columns = self._load_template_columns()

        # Базовая настройка UI
        self.setup_base_ui()

        # Подключаем базовые сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

        # Подключаем кнопку колонок из UI
        if hasattr(self, 'columnBtn'):
            self.columnBtn.clicked.connect(self.select_columns)
            self.columnBtn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update_columns_button_text()

        # Добавляем выбор куратора в UI (до загрузки данных!)
        if hasattr(self, 'comboManagers') or hasattr(self, 'comboManager'):
            self.setup_manager_selector()

        # Теперь загружаем данные проекта (после инициализации комбобокса!)
        if project_data:
            self.load_project_data()
            if 'selected_columns_data' in project_data:
                self.selected_columns_data = project_data['selected_columns_data']
                self.selected_columns_keys = [col.get('col_key', '') for col in self.selected_columns_data]
                self.update_columns_button_text()

        # Скрываем старый GroupBox с чекбоксами (если есть)
        if hasattr(self, 'columnsGroupBox'):
            self.columnsGroupBox.hide()

    def _load_template_columns(self) -> List[Dict]:
        """Загружает шаблонные колонки из БД"""
        try:
            from services.column_service import ColumnService
            from database import get_tasks_session

            session = get_tasks_session()
            column_service = ColumnService(session)
            template_columns = column_service.get_template_columns()
            session.close()

            print(f"📊 Загружено шаблонных колонок: {len(template_columns)}")
            return template_columns
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок: {e}")
            return []

    def setup_base_ui(self):
        """Базовая настройка UI"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")
        self.createBtn.setText("Создать проект")

    def update_columns_button_text(self):
        """Обновляет текст на кнопке выбора колонок"""
        if not hasattr(self, 'columnBtn'):
            return

        count = len(self.selected_columns_data)
        if count != 0:
            self.columnBtn.setText(f"Выбрано колонок: {count}")

    def select_columns(self):
        """Открыть диалог выбора колонок"""
        try:
            from windows.projects.column_selector import ColumnSelectorDialog

            dialog = ColumnSelectorDialog(
                self,
                template_columns=self.template_columns,
                preselected_keys=self.selected_columns_keys
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.selected_columns_data = dialog.get_selected_columns_data()
                self.selected_columns_keys = dialog.get_selected_keys()
                self.update_columns_button_text()
                print(f"📊 Выбрано колонок: {len(self.selected_columns_data)}")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе колонок: {e}")
            import traceback
            traceback.print_exc()

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

    def validate_input(self):
        """Проверка введенных данных"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False

        if not self.selected_columns_data:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну колонку для отображения в проекте!")
            return False

        return True

    def load_project_data(self):
        """Загрузка данных проекта"""
        self.nameInput.setText(self.project_data.get('name', ''))
        self.descInput.setPlainText(self.project_data.get('description', ''))

        is_active = self.project_data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        self.activeCheckbox.setChecked(is_active)

        # 👇 ИСПРАВЛЯЕМ: загружаем куратора СИНХРОННО
        manager_id = self.project_data.get('manager_id')
        if manager_id:
            # Заполняем комбобокс ПЕРЕД установкой значения
            self._ensure_manager_combo_filled()
            self._set_manager_by_id(manager_id)

        # Загружаем колонки, если они есть
        if 'selected_columns_data' in self.project_data and self.project_data['selected_columns_data']:
            self.selected_columns_data = self.project_data['selected_columns_data']
            self.selected_columns_keys = [col.get('col_key', '') for col in self.selected_columns_data]
            self.update_columns_button_text()
            print(f"📊 Загружено {len(self.selected_columns_data)} колонок")

        self.load_participants_and_admins()

    def _ensure_manager_combo_filled(self):
        """Гарантирует, что комбобокс куратора заполнен"""
        combo = self._get_manager_combo()
        if combo is None:
            print("⚠️ Не найден comboManager/comboManagers в UI")
            return

        # Если уже заполнен (есть хотя бы один сотрудник + "Выберите куратора")
        if combo.count() > 1:
            return

        combo.clear()
        combo.addItem("Выберите куратора", None)

        from database import get_employees_session
        from models.employees import Employee
        from sqlalchemy import select

        emp_session = get_employees_session()
        if emp_session:
            stmt = select(Employee).order_by(Employee.last_name)
            employees = emp_session.scalars(stmt).all()

            for emp in employees:
                full_name = f"{emp.last_name} {emp.first_name}"
                if emp.middle_name:
                    full_name += f" {emp.middle_name}"
                combo.addItem(full_name, emp.id)

            emp_session.close()
            print(f"✅ Загружено {combo.count() - 1} сотрудников в комбобокс куратора")

    def _set_manager_by_id(self, manager_id: int):
        """Устанавливает куратора по ID"""
        combo = self._get_manager_combo()
        if combo is None:
            return

        for i in range(combo.count()):
            if combo.itemData(i) == manager_id:
                combo.setCurrentIndex(i)
                print(f"✅ Установлен куратор с ID={manager_id}, индекс={i}, текст={combo.currentText()}")
                return

        print(f"⚠️ Куратор с ID={manager_id} не найден в списке. Доступно {combo.count()} вариантов")

    def _get_manager_combo(self):
        """Возвращает комбобокс куратора"""
        if hasattr(self, 'comboManager'):
            return self.comboManager
        elif hasattr(self, 'comboManagers'):
            return self.comboManagers
        return None

    def load_participants_and_admins(self):
        """Загрузка участников и администраторов из project_data"""
        if hasattr(self.project_data, 'member_ids'):
            member_ids = self.project_data.member_ids
            admin_ids = self.project_data.admin_ids

            self.participants = []
            self.admins = []

            if member_ids:
                from database import get_tasks_session
                from models.employees import Employee
                from sqlalchemy import select

                session = get_tasks_session()
                stmt = select(Employee).where(Employee.id.in_(member_ids))  # ← ИСПРАВЛЕНО
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
                preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.participants = dialog.get_selected_employees()
                self.update_participants_button_text()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе участников: {e}")

    def setup_manager_selector(self):
        """Настройка выбора куратора проекта"""
        combo = self._get_manager_combo()
        if combo is None:
            print("⚠️ Не найден comboManager/comboManagers в UI")
            return

        # Если уже заполнен, не заполняем заново
        if combo.count() > 1:
            return

        combo.clear()
        combo.addItem("Выберите куратора", None)

        from database import get_employees_session
        from models.employees import Employee
        from sqlalchemy import select

        emp_session = get_employees_session()
        if emp_session:
            stmt = select(Employee).order_by(Employee.last_name)
            employees = emp_session.scalars(stmt).all()

            for emp in employees:
                full_name = f"{emp.last_name} {emp.first_name}"
                if emp.middle_name:
                    full_name += f" {emp.middle_name}"
                combo.addItem(full_name, emp.id)

            emp_session.close()
            print(f"✅ Загружено {combo.count() - 1} сотрудников в комбобокс куратора")

    def get_manager_id(self) -> Optional[int]:
        """Возвращает ID выбранного куратора"""
        combo = self._get_manager_combo()
        if combo:
            return combo.currentData()
        return None

    def get_manager_name(self) -> Optional[str]:
        """Возвращает имя выбранного куратора"""
        combo = self._get_manager_combo()
        if combo:
            return combo.currentText()
        return None

    def select_admins(self):
        """Открыть диалог выбора администраторов"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, mode="admins")

            if self.admins:
                preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
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

    def get_common_data(self):
        """Получить общие данные проекта"""
        participants_ids = [str(p.get('id', '')) if isinstance(p, dict) else str(p) for p in self.participants]
        admins_ids = [str(a.get('id', '')) if isinstance(a, dict) else str(a) for a in self.admins]

        return {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'participants_ids': ','.join(participants_ids) if participants_ids else '',
            'participants': self.participants,
            'admins_ids': ','.join(admins_ids) if admins_ids else '',
            'admins': self.admins,
            'is_active': self.activeCheckbox.isChecked(),
            'updated_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'manager_id': self.get_manager_id(),  # ← ДОЛЖНО БЫТЬ
        }