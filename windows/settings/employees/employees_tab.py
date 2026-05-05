from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal, QTimer
from windows.settings.base_tab import BaseTab
from windows.settings.employees.employee_dialog import EmployeeDialog
from windows.settings.employees.employee_card import EmployeeCard


class EmployeesTab(BaseTab):
    """Вкладка для управления сотрудниками"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    employee_added = pyqtSignal(dict)
    employee_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.employees = []
        self.all_departments = []
        self.all_divisions = []
        self.employee_service = None
        self.session = None

        # Показываем фильтры
        self.show_filters()

        # Настраиваем кнопку "Добавить"
        if self.btnAdd:
            self.btnAdd.setText("Добавить сотрудника")
            self.btnAdd.setObjectName("btnAddEmployee")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)

    def set_session(self, session):
        """Установка сессии БД"""
        self.session = session

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service

    def on_add_clicked(self):
        """Открытие окна добавления сотрудника"""
        dialog = EmployeeDialog(parent=self, employee_data=None, session=self.session)
        dialog.employee_saved.connect(self.on_employee_saved)
        dialog.exec()

    def on_employee_saved(self, employee_data: dict):
        """Вызывается после успешного сохранения сотрудника"""
        print("Новый сотрудник:", employee_data)

        if self.employee_service:
            # Сохраняем в БД - ИСПРАВЛЯЕМ НАЗВАНИЕ МЕТОДА
            new_employee = self.employee_service.create_employee(employee_data)  # ← было create_employee_in_db
            if new_employee:
                # ЗАГРУЖАЕМ СВЕЖИЕ ДАННЫЕ ИЗ БД (с названиями отдела и подразделения)
                fresh_employee = self.employee_service.get_employee_by_id(new_employee['id'])
                if fresh_employee:
                    self.employees.append(fresh_employee)
                else:
                    self.employees.append(new_employee)
                self.refresh_cards()
                self.employee_added.emit(new_employee)
                QMessageBox.information(self, "Успех",
                                        f"Сотрудник '{employee_data['last_name']} {employee_data['first_name']}' добавлен")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить сотрудника в БД")
        else:
            self.employees.append(employee_data)
            self.refresh_cards()
            self.employee_added.emit(employee_data)

    def on_edit_clicked(self, employee_id: int):
        """Открытие окна редактирования сотрудника"""
        employee = next((e for e in self.employees if e.get('id') == employee_id), None)
        if employee:
            dialog = EmployeeDialog(parent=self, employee_data=employee, session=self.session)
            dialog.employee_saved.connect(lambda data: self.on_employee_updated(employee_id, data))
            dialog.exec()

    def on_employee_updated(self, employee_id: int, employee_data: dict):
        """Обработка редактирования сотрудника"""
        print("Редактирование сотрудника:", employee_data)

        if self.employee_service:
            # Обновляем в БД
            success = self.employee_service.update_employee(employee_id, employee_data)
            if success:
                # Обновляем локальный список - ЗАГРУЖАЕМ СВЕЖИЕ ДАННЫЕ ИЗ БД
                # Перезагружаем всех сотрудников
                fresh_employees = self.employee_service.get_all_employees(active_only=False)
                if fresh_employees:
                    self.employees = fresh_employees
                else:
                    # Fallback: обновляем только одного
                    updated_employee = self.employee_service.get_employee_by_id(employee_id)
                    if updated_employee:
                        for i, emp in enumerate(self.employees):
                            if emp.get('id') == employee_id:
                                self.employees[i] = updated_employee
                                break

                self.refresh_cards()
                self.employee_updated.emit(employee_data)
                QMessageBox.information(self, "Успех", "Сотрудник обновлён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить сотрудника в БД")
        else:
            # Fallback для тестовых данных
            for i, emp in enumerate(self.employees):
                if emp.get('id') == employee_id:
                    employee_data['id'] = employee_id
                    self.employees[i] = employee_data
                    break
            self.refresh_cards()
            self.employee_updated.emit(employee_data)

    def on_delete_clicked(self, employee_id: int):
        """Удаление сотрудника - вызывается из карточки"""
        self.confirm_delete(
            title="Удаление сотрудника",
            message="Вы уверены, что хотите удалить этого сотрудника?\nЭто действие нельзя отменить.",
            item_type="employee",
            item_id=employee_id
        )

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        print(f"delete_item вызван: item_type={item_type}, item_id={item_id}")
        if item_type == "employee":
            if self.employee_service:
                success = self.employee_service.delete_employee(item_id)  # ← было delete_employee_in_db
                if success:
                    self.employees = [e for e in self.employees if e.get('id') != item_id]
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех", "Сотрудник удалён")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить сотрудника")
            else:
                self.employees = [e for e in self.employees if e.get('id') != item_id]
                self.refresh_cards()
                QMessageBox.information(self, "Успех", "Сотрудник удалён")

    def setup_filters(self, departments: list, divisions: list):
        """Настройка фильтров"""
        self.all_departments = departments
        self.all_divisions = divisions
        self.load_filter_data(departments, divisions)
        print("✅ Фильтры сотрудников успешно настроены")

    def load_filter_data(self, departments: list, divisions: list):
        """Заполняем существующие фильтры"""
        self.all_departments = departments
        self.all_divisions = divisions

        if self.filterDepartment:
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы")
            for dept in departments:
                self.filterDepartment.addItem(dept.get('name', 'Без названия'))

        if self.filterSubDepartment:
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения")
            for div in divisions:
                self.filterSubDepartment.addItem(div.get('name', 'Без названия'))

    def load_data(self, employees: list):
        self.employees = employees
        self.refresh_cards()

    def get_department_name(self, department_id: int) -> str:
        """Получить название отдела по ID"""
        for dept in self.all_departments:
            if dept.get('id') == department_id:
                return dept.get('name', '—')
        return '—'

    def get_division_name(self, division_id: int) -> str:
        """Получить название подразделения по ID"""
        for div in self.all_divisions:
            if div.get('id') == division_id:
                return div.get('name', '—')
        return '—'

    def refresh_cards(self, filtered_employees=None):
        employees_to_show = filtered_employees if filtered_employees is not None else self.employees
        self.clear_cards()
        for i, employee in enumerate(employees_to_show):
            # Данные уже содержат department_name и division_name из сервиса
            employee_with_names = employee.copy() if isinstance(employee, dict) else {}

            # Используем уже полученные названия из employee, если они есть
            if employee.get('department_name') and employee.get('department_name') != '—':
                employee_with_names['department_name'] = employee.get('department_name')
                print(f"  Отдел из данных: '{employee.get('department_name')}'")
            else:
                employee_with_names['department_name'] = '—'

            if employee.get('division_name') and employee.get('division_name') != '—':
                employee_with_names['division_name'] = employee.get('division_name')
                print(f"  Подразделение из данных: '{employee.get('division_name')}'")
            else:
                employee_with_names['division_name'] = '—'

            # Копируем остальные поля
            for key, value in employee.items():
                if key not in employee_with_names:
                    employee_with_names[key] = value

            card = EmployeeCard(employee_with_names, parent=self)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()

    def apply_filters(self):
        filtered = self.employees[:]
        self.refresh_cards(filtered)