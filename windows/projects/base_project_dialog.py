# windows/projects/base_project_dialog.py

import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtCore import QDate, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QComboBox, QCheckBox, QVBoxLayout, QWidget, QLabel

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов создания и редактирования проектов с поддержкой прав"""

    columns_changed = pyqtSignal(dict)

    def __init__(self, parent=None, title="Проект", project_data=None, service=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        self.service = service
        self.project_data = project_data or {}
        self.participants = []
        self.admins = []
        self.all_columns = []
        self.column_checkboxes = {}
        self.selected_columns_data = []

        # Инициализация сервиса прав
        self.permission_service = None
        self._init_permission_service(parent)

        self.setup_base_ui()
        self.connect_signals()
        self.setup_manager_selector()
        self.hide_field_checkboxes()
        self.load_columns()

        if project_data:
            self.load_project_data()

    def _init_permission_service(self, parent):
        """Инициализирует сервис прав из родительского окна"""
        if parent and hasattr(parent, 'current_user_id') and hasattr(parent, 'permission_service'):
            self.permission_service = parent.permission_service
        elif parent and hasattr(parent, 'current_user_id') and self.service:
            from services.permissions.permission_service import PermissionService
            self.permission_service = PermissionService(
                user_id=parent.current_user_id,
                app_service=self.service,
                project_service=self.service
            )

    def connect_signals(self):
        """Подключает сигналы"""
        # Не подключаем здесь - подключим позже в зависимости от режима
        pass

    def connect_edit_signals(self):
        """Подключает сигналы для режима редактирования"""
        try:
            self.participantsBtn.clicked.disconnect()
        except:
            pass
        try:
            self.adminsBtn.clicked.disconnect()
        except:
            pass
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

    def connect_view_signals(self):
        """Подключает сигналы для режима просмотра"""
        try:
            self.participantsBtn.clicked.disconnect()
        except:
            pass
        try:
            self.adminsBtn.clicked.disconnect()
        except:
            pass
        self.participantsBtn.clicked.connect(self.view_participants)
        self.adminsBtn.clicked.connect(self.view_admins)

    def setup_base_ui(self):
        """Базовая настройка UI"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")
        self.createBtn.setText("Создать проект")

        # Подключаем сигналы для режима редактирования (по умолчанию)
        self.connect_edit_signals()

        if hasattr(self, 'columnsGroupBox'):
            self.columnsGroupBox.setTitle("Выбор канбан-колонок для проекта")

    def view_participants(self):
        """Просмотр участников проекта (режим только для чтения)"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="participants")

            # Устанавливаем предвыбранных участников
            if self.participants:
                preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
                dialog.set_preselected(preselected_ids)

            # Делаем диалог только для чтения - отключаем возможность выбора
            # Для этого переопределяем поведение чекбоксов в диалоге
            dialog.set_readonly_mode(True)

            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при просмотре участников: {e}")

    def view_admins(self):
        """Просмотр администраторов проекта (режим только для чтения)"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="admins")

            # Устанавливаем предвыбранных администраторов
            if self.admins:
                preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
                dialog.set_preselected(preselected_ids)

            # Делаем диалог только для чтения - отключаем возможность выбора
            dialog.set_readonly_mode(True)

            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при просмотре администраторов: {e}")

    def hide_field_checkboxes(self):
        """Скрывает ненужные чекбоксы полей проекта"""
        field_checkboxes = [
            'colNameCheckbox', 'colDescriptionCheckbox', 'colStatusCheckbox',
            'colCreatedDateCheckbox', 'colDeadlineCheckbox',
            'colParticipantsCheckbox', 'colProgressCheckbox'
        ]
        for cb_name in field_checkboxes:
            if hasattr(self, cb_name):
                getattr(self, cb_name).hide()

    def setup_edit_mode(self, project_id: int):
        """
        Настраивает диалог в зависимости от прав пользователя
        Вызывается в ProjectEditDialog после загрузки данных
        """
        if not self.permission_service:
            self.connect_edit_signals()
            return

        can_edit = self.permission_service.can_edit_project(project_id)

        if not can_edit:
            # Режим только для просмотра
            self._setup_readonly_mode(project_id)
            self.connect_view_signals()
        else:
            # Режим редактирования - оставляем кнопку видимой
            self.createBtn.setText("Сохранить изменения")
            self.createBtn.show()
            self.connect_edit_signals()

    def _setup_readonly_mode(self, project_id: int):
        """
        Настраивает режим только для просмотра
        """
        # Меняем заголовок окна
        project_name = self.project_data.get('name', '')
        self.setWindowTitle(f"Информация о проекте: {project_name}")

        # Меняем текст заголовка в UI
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Информация о проекте")

        # Скрываем кнопку сохранения
        self.createBtn.hide()

        # Делаем все поля только для чтения
        if hasattr(self, 'nameInput'):
            self.nameInput.setReadOnly(True)
            self.nameInput.setStyleSheet("background-color: #f5f5f5;")

        if hasattr(self, 'descInput'):
            self.descInput.setReadOnly(True)
            self.descInput.setStyleSheet("background-color: #f5f5f5;")

        if hasattr(self, 'activeCheckbox'):
            self.activeCheckbox.setEnabled(False)

        # Кнопки выбора участников/админов - НЕ отключаем, а меняем поведение
        if hasattr(self, 'participantsBtn'):
            try:
                self.participantsBtn.clicked.disconnect()
            except:
                pass
            self.participantsBtn.clicked.connect(self.view_participants)

        if hasattr(self, 'adminsBtn'):
            try:
                self.adminsBtn.clicked.disconnect()
            except:
                pass
            self.adminsBtn.clicked.connect(self.view_admins)

        # Проверяем, может ли пользователь управлять колонками
        if hasattr(self, 'permission_service'):
            can_manage_columns = self.permission_service.can_show_project_columns_selector(project_id)
            if not can_manage_columns:
                for checkbox in self.column_checkboxes.values():
                    checkbox.setEnabled(False)

        # Отключаем выбор куратора
        combo = self._get_manager_combo()
        if combo:
            combo.setEnabled(False)
            combo.setStyleSheet("background-color: #f5f5f5;")

    def load_columns(self):
        """Загружает доступные канбан-колонки и создает чекбоксы"""
        if not self.service:
            return

        self.all_columns = self.service.get_template_columns_for_selector()

        if not hasattr(self, 'columnsGroupBox'):
            return

        columns_layout = self.columnsGroupBox.layout()
        if columns_layout is None:
            columns_layout = QVBoxLayout(self.columnsGroupBox)
            self.columnsGroupBox.setLayout(columns_layout)

        for checkbox in self.column_checkboxes.values():
            if checkbox and checkbox.parent():
                checkbox.deleteLater()
        self.column_checkboxes.clear()

        for col in self.all_columns:
            col_id = col.get('id')
            col_name = col.get('name', 'Без названия')
            col_key = col.get('col_key', col_name.lower().replace(' ', '_'))
            col_color = "#D22730"

            checkbox = QCheckBox(col_name)
            checkbox.setProperty('col_id', col_id)
            checkbox.setProperty('col_key', col_key)
            checkbox.setProperty('col_data', col)
            checkbox.setChecked(False)

            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    font-size: 13px;
                    color: #1B232A;
                    padding: 5px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid #1B232A;
                    border-radius: 4px;
                    background-color: white;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {col_color};
                    border: 2px solid {col_color};
                }}
                QCheckBox::indicator:hover {{
                    border-color: #D22730;
                }}
            """)

            checkbox.stateChanged.connect(lambda checked, key=col_key: self._on_column_checkbox_changed(key, checked))
            self.column_checkboxes[col_key] = checkbox
            columns_layout.addWidget(checkbox)

        columns_layout.addStretch()

    def _on_column_checkbox_changed(self, col_key: str, state):
        """Обработчик изменения состояния чекбокса колонки"""
        col = None
        for c in self.all_columns:
            if c.get('col_key', c.get('name', '').lower().replace(' ', '_')) == col_key:
                col = c
                break

        if not col:
            return

        if state == Qt.CheckState.Checked.value:
            if col not in self.selected_columns_data:
                self.selected_columns_data.append(col)
        else:
            if col in self.selected_columns_data:
                self.selected_columns_data.remove(col)

    def get_selected_column_keys(self) -> List[str]:
        """Возвращает список ключей выбранных колонок"""
        return [col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                for col in self.selected_columns_data]

    def setup_manager_selector(self):
        """Настройка комбобокса куратора"""
        combo = self._get_manager_combo()
        if combo is None:
            return

        combo.clear()
        combo.addItem("Выберите куратора", None)

        if self.service:
            managers = self.service.load_employees_for_manager_combo()
            for manager in managers:
                combo.addItem(manager['display_name'], manager['id'])
            print(f"✅ Загружено {len(managers)} сотрудников в комбобокс куратора")

    def _get_manager_combo(self) -> Optional[QComboBox]:
        """Возвращает комбобокс куратора"""
        if hasattr(self, 'comboManager'):
            return self.comboManager
        elif hasattr(self, 'comboManagers'):
            return self.comboManagers
        return None

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

    def select_participants(self):
        """Выбор участников проекта"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="participants")

            if self.participants:
                preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.participants = dialog.get_selected_employees()
                self.update_participants_button_text()
                print(f"✅ Выбрано участников: {len(self.participants)}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе участников: {e}")
            import traceback
            traceback.print_exc()

    def select_admins(self):
        """Выбор администраторов проекта"""
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="admins")

            if self.admins:
                preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.admins = dialog.get_selected_employees()
                self.update_admins_button_text()
                print(f"✅ Выбрано администраторов: {len(self.admins)}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе администраторов: {e}")
            import traceback
            traceback.print_exc()

    def update_participants_button_text(self):
        """Обновить текст на кнопке участников"""
        count = len(self.participants)
        if count == 0:
            self.participantsBtn.setText("Выбрать участников")
        elif count == 1:
            emp = self.participants[0]
            if isinstance(emp, dict) and self.service:
                name = self.service.get_employee_display_name(emp['id'])
                self.participantsBtn.setText(f"Участник: {name}")
            else:
                self.participantsBtn.setText(f"Участник: 1 чел.")
        else:
            self.participantsBtn.setText(f"Участники ({count} чел.)")

    def update_admins_button_text(self):
        """Обновить текст на кнопке администраторов"""
        count = len(self.admins)
        if count == 0:
            self.adminsBtn.setText("Выбрать администраторов")
        elif count == 1:
            emp = self.admins[0]
            if isinstance(emp, dict) and self.service:
                name = self.service.get_employee_display_name(emp['id'])
                self.adminsBtn.setText(f"Администратор: {name}")
            else:
                self.adminsBtn.setText(f"Администратор: 1 чел.")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def load_project_data(self):
        """Загрузка данных проекта"""
        if hasattr(self, 'nameInput'):
            self.nameInput.setText(self.project_data.get('name', ''))

        if hasattr(self, 'descInput'):
            self.descInput.setPlainText(self.project_data.get('description', ''))

        is_active = self.project_data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'

        if hasattr(self, 'activeCheckbox'):
            self.activeCheckbox.setChecked(is_active)

        manager_id = self.project_data.get('manager_id')
        if manager_id:
            combo = self._get_manager_combo()
            if combo:
                for i in range(combo.count()):
                    if combo.itemData(i) == manager_id:
                        combo.setCurrentIndex(i)
                        break

        self.selected_columns_data = []
        selected_keys = []

        if 'selected_columns_data' in self.project_data and self.project_data['selected_columns_data']:
            self.selected_columns_data = self.project_data['selected_columns_data']
            selected_keys = [col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                             for col in self.selected_columns_data]
        elif self.project_data.get('selected_columns'):
            selected_keys = self.project_data.get('selected_columns', [])
            self._restore_columns_from_keys(selected_keys)

        for col_key, checkbox in self.column_checkboxes.items():
            checkbox.setChecked(col_key in selected_keys)

        self._load_participants_and_admins()

    def _restore_columns_from_keys(self, column_keys: List[str]):
        """Восстанавливает выбранные колонки из ключей"""
        if not self.service or not column_keys:
            return

        all_columns = self.service.get_template_columns_for_selector()
        self.selected_columns_data = []
        for col in all_columns:
            col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
            if col_key in column_keys:
                self.selected_columns_data.append(col)

    def _load_participants_and_admins(self):
        """Загрузка участников и администраторов через сервис"""
        member_ids = []
        admin_ids = []

        if hasattr(self.project_data, 'member_ids'):
            member_ids = self.project_data.member_ids or []
            admin_ids = self.project_data.admin_ids or []
        else:
            member_ids = self.project_data.get('member_ids', [])
            admin_ids = self.project_data.get('admin_ids', [])

        if member_ids and self.service:
            employees = self.service.load_employees_by_ids(member_ids)
            self.participants = employees
            self.admins = [emp for emp in employees if emp['id'] in admin_ids]
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
            return [{'id': emp_id, 'last_name': f"User{emp_id}", 'first_name': f"User{emp_id}"} for emp_id in ids]
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
                    normalized.append({'id': item, 'first_name': f"User{item}", 'last_name': f"LastName{item}"})
            return normalized
        return []

    def get_project_data(self):
        """Получить данные нового проекта"""
        participants_ids = set()
        for p in self.participants:
            emp_id = p.get('id') if isinstance(p, dict) else p
            if emp_id:
                participants_ids.add(str(emp_id))

        for a in self.admins:
            emp_id = a.get('id') if isinstance(a, dict) else a
            if emp_id:
                participants_ids.add(str(emp_id))

        manager_id = self.get_manager_id()
        if manager_id:
            participants_ids.add(str(manager_id))

        admins_ids = set()
        for a in self.admins:
            emp_id = a.get('id') if isinstance(a, dict) else a
            if emp_id:
                admins_ids.add(str(emp_id))

        data = {
            'name': self.nameInput.text() if hasattr(self, 'nameInput') else '',
            'description': self.descInput.toPlainText() if hasattr(self, 'descInput') else '',
            'participants_ids': ','.join(participants_ids) if participants_ids else '',
            'participants': self.participants,
            'admins_ids': ','.join(admins_ids) if admins_ids else '',
            'admins': self.admins,
            'is_active': self.activeCheckbox.isChecked() if hasattr(self, 'activeCheckbox') else True,
            'created_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'updated_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'selected_columns_data': self.selected_columns_data,
            'selected_columns': self.get_selected_column_keys(),
            'manager_id': manager_id,
        }

        if self.project_data and self.project_data.get('id'):
            data['id'] = self.project_data.get('id')

        return data

    def validate_input(self):
        """Проверка введенных данных"""
        if hasattr(self, 'nameInput') and not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False

        if not self.selected_columns_data:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну колонку для отображения в проекте!")
            return False

        return True

    def _create_employee_stub(self, emp_id: int) -> Dict:
        """Создает заглушку для сотрудника"""
        return {
            'id': emp_id,
            'last_name': f"User{emp_id}",
            'first_name': f"User{emp_id}",
            'middle_name': '',
            'position': 'Сотрудник'
        }

    def showEvent(self, event):
        """Срабатывает при показе диалога"""
        super().showEvent(event)
        # Если это диалог редактирования с ID проекта, настраиваем режим
        project_id = self.project_data.get('id') if self.project_data else None
        if project_id and hasattr(self, 'setup_edit_mode'):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self.setup_edit_mode(project_id))