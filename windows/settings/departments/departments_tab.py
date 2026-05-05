from windows.settings.base_tab import BaseTab
from windows.settings.departments.department_card import DepartmentCard
from windows.settings.departments.department_dialog import DepartmentDialog
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout, \
    QRadioButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt


class DepartmentsTab(BaseTab):
    """Вкладка для управления отделами"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.departments = []
        self.session = None
        self.all_employees = []
        self.all_divisions = []
        self.employee_service = None

        # Показываем фильтры для отделов
        self.show_filters()

        # Настраиваем фильтры
        if hasattr(self, 'filterDepartment'):
            self.filterDepartment.setVisible(True)
            self.filterDepartment.currentTextChanged.connect(self.filter_by_department)

        if hasattr(self, 'filterSubDepartment'):
            self.filterSubDepartment.setVisible(True)
            self.filterSubDepartment.currentTextChanged.connect(self.filter_by_division)

        if self.btnAdd:
            self.btnAdd.setText("Добавить отдел")
            self.btnAdd.setObjectName("btnAddDepartment")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)

    def set_session(self, session):
        """Установка сессии БД"""
        self.session = session
        if self.session:
            from services.employee_service import EmployeeService
            self.employee_service = EmployeeService(self.session)
            self.all_divisions = self.employee_service.get_all_divisions()
            self.load_division_filters()

    def load_division_filters(self):
        """Загрузка подразделений в фильтр"""
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            for div in self.all_divisions:
                self.filterSubDepartment.addItem(div.get('name', ''), div.get('id'))

    def set_employees(self, employees: list):
        """Установка списка сотрудников для отображения имён"""
        self.all_employees = employees
        self.refresh_cards()

    def filter_by_department(self):
        """Фильтрация по названию отдела"""
        self.refresh_cards()

    def filter_by_division(self):
        """Фильтрация по подразделению"""
        self.refresh_cards()

    def _get_filtered_departments(self):
        """Возвращает отфильтрованный список отделов"""
        filter_text = ""
        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            filter_text = self.filterDepartment.currentText().lower().strip()

        division_id = None
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            division_id = self.filterSubDepartment.currentData()

        filtered = []
        for dept in self.departments:
            # Фильтр по названию
            if filter_text and filter_text not in dept.get('name', '').lower():
                continue
            # Фильтр по подразделению
            if division_id and dept.get('division_id') != division_id:
                continue
            filtered.append(dept)
        return filtered

    def _get_division_name(self, division_id: int) -> str:
        """Получить название подразделения по ID"""
        for div in self.all_divisions:
            if div.get('id') == division_id:
                return div.get('name', '')
        return ''

    def _get_employee_name(self, employee_id: int) -> str:
        """Получить ФИО сотрудника по ID в кратком формате Фамилия И.О."""
        for emp in self.all_employees:
            if emp.get('id') == employee_id:
                last_name = emp.get('last_name', '')
                first_name = emp.get('first_name', '')
                middle_name = emp.get('middle_name', '')

                # Формируем краткое ФИО: Фамилия И.О.
                initials = ""
                if first_name:
                    initials += first_name[0] + "."
                if middle_name:
                    initials += middle_name[0] + "."

                return f"{last_name} {initials}".strip()
        return str(employee_id)

    def on_add_clicked(self):
        """Открытие диалога добавления отдела"""
        dialog = DepartmentDialog(parent=None, department_data=None, session=self.session)
        dialog.department_saved.connect(self.on_department_saved)
        dialog.exec()

    def on_department_saved(self, department_data: dict):
        """Обработка сохранения отдела"""
        print("Новый отдел:", department_data)

        if self.employee_service:
            # Исправляем: create_department_in_db -> create_department
            new_department = self.employee_service.create_department(department_data)
            if new_department:
                new_department['division'] = self._get_division_name(new_department.get('division_id'))
                self.departments.append(new_department)
                self.refresh_cards()
                QMessageBox.information(self, "Успех", f"Отдел '{department_data.get('name')}' создан")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить отдел в БД")
        else:
            self.departments.append(department_data)
            self.refresh_cards()

    def load_data(self, departments: list):
        self.departments = departments
        self.refresh_cards()

    def refresh_cards(self):
        self.clear_cards()

        filtered_departments = self._get_filtered_departments()

        for i, department in enumerate(filtered_departments):
            if 'division' not in department and department.get('division_id'):
                department['division'] = self._get_division_name(department.get('division_id'))

            card = DepartmentCard(department, employee_resolver=self._get_employee_name)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def on_edit_clicked(self, department_id: int):
        department = next((d for d in self.departments if d.get('id') == department_id), None)
        if department:
            dialog = DepartmentDialog(parent=None, department_data=department, session=self.session)
            dialog.department_saved.connect(self.on_department_edited)
            dialog.exec()

    def on_department_edited(self, department_data: dict):
        """Обработка редактирования отдела"""
        print("Редактирование отдела:", department_data)

        if self.employee_service:
            # Исправляем: update_department_in_db -> update_department
            success = self.employee_service.update_department(
                department_data.get('id'),
                department_data
            )
            if success:
                for i, dept in enumerate(self.departments):
                    if dept.get('id') == department_data.get('id'):
                        updated_dept = {
                            'id': department_data.get('id'),
                            'number': department_data.get('number'),
                            'name': department_data.get('name'),
                            'boss': department_data.get('boss', ''),
                            'phone_number': department_data.get('phone', ''),
                            'division_id': department_data.get('division_id'),
                            'division': self._get_division_name(department_data.get('division_id'))
                        }
                        self.departments[i] = updated_dept
                        break
                self.refresh_cards()
                QMessageBox.information(self, "Успех", "Отдел обновлён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить отдел в БД")
        else:
            # Fallback для тестовых данных
            for i, dept in enumerate(self.departments):
                if dept.get('id') == department_data.get('id'):
                    self.departments[i] = department_data
                    break
            self.refresh_cards()

    def on_delete_clicked(self, department_id: int):
        """Удаление отдела - вызывается из карточки"""
        # Проверяем, есть ли связанные сотрудники
        has_employees = False
        if self.employee_service:
            has_employees = self.employee_service.has_employees_in_department(department_id)

        if has_employees:
            self.show_delete_with_dependencies_dialog(department_id)
        else:
            self.confirm_delete(
                title="Удаление отдела",
                message="Вы уверены, что хотите удалить этот отдел?\nЭто действие нельзя отменить.",
                item_type="department",
                item_id=department_id
            )

    def show_delete_with_dependencies_dialog(self, department_id: int):
        """Диалог удаления отдела с сотрудниками"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Удаление отдела")
        dialog.setFixedSize(500, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 12px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }
            QRadioButton {
                color: #2c3e50;
                font-size: 13px;
                padding: 5px;
            }
            QComboBox {
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                min-width: 200px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnDelete {
                background-color: #D22730;
                color: white;
                border: none;
            }
            QPushButton#btnDelete:hover {
                background-color: #862633;
            }
            QPushButton#btnReassign {
                background-color: #ccab6e;
                color: white;
                border: none;
            }
            QPushButton#btnReassign:hover {
                background-color: #998664;
            }
            QPushButton#btnCancel {
                background-color: #6c757d;
                color: white;
                border: none;
            }
            QPushButton#btnCancel:hover {
                background-color: #5a6268;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        # Предупреждение
        warning_label = QLabel("⚠️ ВНИМАНИЕ!")
        warning_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #D22730;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning_label)

        # Описание зависимостей
        deps_label = QLabel("В этом отделе есть сотрудники.\nЧто вы хотите сделать?")
        deps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(deps_label)

        layout.addSpacing(10)

        # Группа радио-кнопок для выбора действия
        radio_group = QButtonGroup(dialog)

        radio_delete_all = QRadioButton("🗑️ Удалить всё (отдел и всех сотрудников в нём)")
        radio_delete_all.setChecked(True)
        radio_group.addButton(radio_delete_all)
        layout.addWidget(radio_delete_all)

        radio_reassign = QRadioButton("🔄 Переназначить сотрудников в другой отдел")
        radio_group.addButton(radio_reassign)
        layout.addWidget(radio_reassign)

        # Комбобокс для выбора отдела (изначально скрыт)
        reassign_layout = QVBoxLayout()
        reassign_label = QLabel("Выберите отдел для переназначения сотрудников:")
        reassign_label.setVisible(False)
        reassign_layout.addWidget(reassign_label)

        self.reassign_combo = QComboBox()
        self.reassign_combo.setVisible(False)
        # Загружаем другие отделы (кроме текущего)
        other_departments = [d for d in self.departments if d.get('id') != department_id]
        self.reassign_combo.addItem("— Выберите отдел —", None)
        for dept in other_departments:
            self.reassign_combo.addItem(f"{dept.get('name', 'Без названия')} (№{dept.get('number', '?')})",
                                        dept.get('id'))
        reassign_layout.addWidget(self.reassign_combo)
        layout.addLayout(reassign_layout)

        def on_radio_changed():
            is_reassign = radio_reassign.isChecked()
            reassign_label.setVisible(is_reassign)
            self.reassign_combo.setVisible(is_reassign)

        radio_delete_all.toggled.connect(lambda: on_radio_changed())
        radio_reassign.toggled.connect(lambda: on_radio_changed())

        layout.addSpacing(10)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        btn_delete = QPushButton("Удалить")
        btn_delete.setObjectName("btnDelete")
        btn_delete.setFixedHeight(35)

        btn_reassign = QPushButton("Переназначить")
        btn_reassign.setObjectName("btnReassign")
        btn_reassign.setFixedHeight(35)
        btn_reassign.setVisible(False)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedHeight(35)

        def update_buttons():
            is_reassign = radio_reassign.isChecked()
            btn_delete.setVisible(not is_reassign)
            btn_reassign.setVisible(is_reassign)

        radio_delete_all.toggled.connect(lambda: update_buttons())
        radio_reassign.toggled.connect(lambda: update_buttons())

        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_reassign)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        def do_delete():
            if radio_delete_all.isChecked():
                if self.employee_service:
                    success = self.employee_service.delete_department_cascade(department_id)  # если есть такой метод
                    # или просто delete_department если каскадное удаление настроено в БД
                    if success:
                        self.departments = [d for d in self.departments if d.get('id') != department_id]
                        self.refresh_cards()
                        QMessageBox.information(self, "Успех", "Отдел и все сотрудники удалены")
                        dialog.accept()
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось удалить отдел")
                else:
                    self.departments = [d for d in self.departments if d.get('id') != department_id]
                    self.refresh_cards()
                    dialog.accept()
            else:
                target_department_id = self.reassign_combo.currentData()
                if not target_department_id:
                    QMessageBox.warning(dialog, "Ошибка", "Выберите отдел для переназначения")
                    return

                if self.employee_service:
                    success = self.employee_service.reassign_department_employees(department_id, target_department_id)
                    if success:
                        self.employee_service.delete_department(department_id)  # исправлено
                        self.departments = [d for d in self.departments if d.get('id') != department_id]
                        self.refresh_cards()
                        QMessageBox.information(self, "Успех",
                                                f"Все сотрудники переназначены в новый отдел\nИсходный отдел удалён")
                        dialog.accept()
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось выполнить переназначение")
                else:
                    self.departments = [d for d in self.departments if d.get('id') != department_id]
                    self.refresh_cards()
                    dialog.accept()

        btn_delete.clicked.connect(do_delete)
        btn_reassign.clicked.connect(do_delete)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления (вызывается по сигналу из BaseTab)"""
        print(f"delete_item вызван: item_type={item_type}, item_id={item_id}")

        if item_type == "department":
            if self.employee_service:
                # Исправляем: delete_department_in_db -> delete_department
                success = self.employee_service.delete_department(item_id)
                if success:
                    self.departments = [d for d in self.departments if d.get('id') != item_id]
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех", "Отдел удалён")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить отдел")
            else:
                self.departments = [d for d in self.departments if d.get('id') != item_id]
                self.refresh_cards()