from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal, QTimer
from windows.settings.base_tab import BaseTab
from windows.settings.employees.employee_dialog import EmployeeDialog
from windows.settings.employees.employee_card import EmployeeCard


# windows/settings/employees/employees_tab.py

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal, QTimer
from windows.settings.base_tab import BaseTab
from windows.settings.employees.employee_dialog import EmployeeDialog
from windows.settings.employees.employee_card import EmployeeCard


class EmployeesTab(BaseTab):
    """Вкладка для управления сотрудниками"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    employee_added = pyqtSignal(dict)  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
    employee_updated = pyqtSignal(dict)  # ← ДОБАВЬТЕ ДЛЯ ОБНОВЛЕНИЯ

    def __init__(self, parent=None):
        super().__init__(parent)
        self.employees = []
        self.all_departments = []
        self.all_divisions = []
        self.employee_service = None  # ← ДОБАВЬТЕ

        # Показываем фильтры (они уже есть в base_tab.ui)
        self.show_filters()

        # Настраиваем кнопку "Добавить"
        if self.btnAdd:
            self.btnAdd.setText("Добавить сотрудника")
            self.btnAdd.setObjectName("btnAddEmployee")
            self.btnAdd.clicked.connect(self.on_add_clicked)

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service

    def on_add_clicked(self):
        """Открытие окна добавления сотрудника"""
        dialog = EmployeeDialog(parent=self)
        dialog.employee_saved.connect(self.on_employee_saved)
        dialog.exec()

    def on_edit_clicked(self, employee_id: int):
        """Открытие окна редактирования сотрудника"""
        employee = next((e for e in self.employees if e.get('id') == employee_id), None)
        if employee:
            dialog = EmployeeDialog(parent=self, employee_data=employee)
            dialog.employee_saved.connect(self.on_employee_updated)
            dialog.exec()

    def on_employee_updated(self, employee_data: dict):
        """Обработка редактирования сотрудника (с сохранением в БД)"""
        if self.employee_service:
            # Обновляем в БД
            success = self.employee_service.update_employee(
                employee_data.get('id'),
                employee_data
            )
            if success:
                # Обновляем локальный список
                for i, emp in enumerate(self.employees):
                    if emp.get('id') == employee_data.get('id'):
                        # Получаем свежие данные из БД
                        updated = self.employee_service.get_employee_by_id(employee_data.get('id'))
                        if updated:
                            self.employees[i] = updated
                        break
                self.refresh_cards()
                self.employee_updated.emit(employee_data)

    def on_employee_saved(self, employee_data: dict):
        """Вызывается после успешного сохранения сотрудника"""
        if self.employee_service:
            # Сохраняем в БД
            new_employee = self.employee_service.create_employee(employee_data)
            if new_employee:
                self.employees.append(new_employee)
                self.refresh_cards()
                self.employee_added.emit(new_employee)

    def on_employee_edited(self, employee_data: dict):
        """Обработка редактирования сотрудника"""
        # Обновляем данные в списке
        for i, emp in enumerate(self.employees):
            if emp.get('id') == employee_data.get('id'):
                self.employees[i] = employee_data
                break

        self.refresh_cards()  # обновляем карточки

    def setup_filters(self, departments: list, divisions: list):
        """Настройка фильтров (используем уже существующие из base_tab.ui)"""
        self.all_departments = departments
        self.all_divisions = divisions

        # Загружаем данные в существующие комбобоксы
        self.load_filter_data(departments, divisions)

        print("✅ Фильтры сотрудников успешно настроены (используются из base_tab.ui)")

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

    def refresh_cards(self, filtered_employees=None):
        employees_to_show = filtered_employees if filtered_employees is not None else self.employees
        self.clear_cards()
        for i, employee in enumerate(employees_to_show):
            card = EmployeeCard(employee)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()

    def apply_filters(self):
        # Здесь будет твоя логика фильтрации (если нужно)
        filtered = self.employees[:]
        self.refresh_cards(filtered)

    def on_delete_clicked(self, column_id: int):
        """Удаление колонки"""
        self.confirm_delete(
            title="Удаление сотрудника",
            message="Вы уверены, что хотите удалить этого сотрудника?\nЭто действие нельзя отменить.",
            item_type="column",
            item_id=column_id
        )