from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal
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
        self.employee_service = None
        self.employees = []

        # Показываем фильтры
        self.show_filters()

        # Настраиваем кнопку "Добавить"
        if self.btnAdd:
            self.btnAdd.setText("Добавить сотрудника")
            self.btnAdd.setObjectName("btnAddEmployee")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service
        if service:
            self.setup_filters_from_service()

    def setup_filters_from_service(self):
        """Настройка фильтров через сервис"""
        if self.employee_service:
            filter_data = self.employee_service.get_filter_data()
            departments = filter_data.get('departments', [])
            divisions = filter_data.get('divisions', [])

            self.all_departments = departments
            self.all_divisions = divisions

            if hasattr(self, 'filterDepartment') and self.filterDepartment:
                self.filterDepartment.clear()
                self.filterDepartment.addItem("Все отделы")
                for dept in departments:
                    self.filterDepartment.addItem(dept.get('name', 'Без названия'))

            if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
                self.filterSubDepartment.clear()
                self.filterSubDepartment.addItem("Все подразделения")
                for div in divisions:
                    self.filterSubDepartment.addItem(div.get('name', 'Без названия'))

    def on_add_clicked(self):
        """Открытие окна добавления сотрудника"""
        dialog = EmployeeDialog(
            parent=self,
            employee_data=None,
            employee_service=self.employee_service,
            is_registration_mode=False
        )
        dialog.employee_saved.connect(self.on_employee_saved)
        dialog.exec()

    def on_employee_saved(self, employee_data: dict):
        """Вызывается после успешного сохранения сотрудника"""
        if self.employee_service:
            # Перезагружаем список сотрудников
            self.load_employees()
            self.refresh_cards()
            self.employee_added.emit(employee_data)
            QMessageBox.information(self, "Успех", "Сотрудник добавлен")
        else:
            self.employees.append(employee_data)
            self.refresh_cards()
            self.employee_added.emit(employee_data)

    def on_edit_clicked(self, employee_id: int):
        """Открытие окна редактирования сотрудника"""
        if self.employee_service:
            # Получаем свежие данные через сервис
            employee = self.employee_service.get_employee_full_info(employee_id)
            if employee:
                dialog = EmployeeDialog(
                    parent=self,
                    employee_data=employee,
                    employee_service=self.employee_service,
                    is_registration_mode=False
                )
                dialog.employee_saved.connect(lambda data: self.on_employee_updated(employee_id, data))
                dialog.exec()

    def on_employee_updated(self, employee_id: int, employee_data: dict):
        """Обработка редактирования сотрудника"""
        if self.employee_service:
            # Обновляем через сервис
            success = self.employee_service.update_employee(employee_id, employee_data)
            if success:
                # Перезагружаем список сотрудников
                self.load_employees()
                self.refresh_cards()
                self.employee_updated.emit(employee_data)
                QMessageBox.information(self, "Успех", "Сотрудник обновлён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить сотрудника")

    def on_delete_clicked(self, employee_id: int):
        """Удаление сотрудника - вызывается из карточки"""
        self.confirm_delete(
            title="Удаление сотрудника",
            message="Вы уверены, что хотите удалить этого сотрудника?\nЭто действие нельзя отменить.",
            item_type="employee",
            item_id=employee_id
        )

    def load_filter_data(self, departments: list, divisions: list):
        """Заполнение фильтров (для совместимости со старым кодом)"""
        self.all_departments = departments
        self.all_divisions = divisions

        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы")
            for dept in departments:
                self.filterDepartment.addItem(dept.get('name', 'Без названия'))

        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения")
            for div in divisions:
                self.filterSubDepartment.addItem(div.get('name', 'Без названия'))

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if item_type == "employee" and self.employee_service:
            success = self.employee_service.delete_employee_by_id(item_id)
            if success:
                self.load_employees()
                self.refresh_cards()
                QMessageBox.information(self, "Успех", "Сотрудник удалён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить сотрудника")

    def load_employees(self):
        """Загрузка сотрудников через сервис"""
        if self.employee_service:
            employees = self.employee_service.get_employee_card_data()
            if employees:
                self.employees = employees
            else:
                self.employees = []

    def load_data(self, employees: list):
        """Загрузка данных (для совместимости)"""
        self.employees = employees
        self.refresh_cards()

    def get_department_name(self, department_id: int) -> str:
        """Получить название отдела по ID"""
        for dept in getattr(self, 'all_departments', []):
            if dept.get('id') == department_id:
                return dept.get('name', '—')
        return '—'

    def get_division_name(self, division_id: int) -> str:
        """Получить название подразделения по ID"""
        for div in getattr(self, 'all_divisions', []):
            if div.get('id') == division_id:
                return div.get('name', '—')
        return '—'

    def refresh_cards(self, filtered_employees=None):
        """Обновление карточек"""
        employees_to_show = filtered_employees if filtered_employees is not None else self.employees
        self.clear_cards()

        for i, employee in enumerate(employees_to_show):
            # Данные уже должны содержать все нужные поля от сервиса
            card = EmployeeCard(employee, self.employee_service, parent=self)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def apply_filters(self):
        """Применение фильтров"""
        filtered = self.employees[:]
        # Здесь можно добавить логику фильтрации
        self.refresh_cards(filtered)