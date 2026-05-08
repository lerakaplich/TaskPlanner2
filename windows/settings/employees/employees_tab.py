# windows/settings/employees/employees_tab.py


from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

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
        self.all_departments = []
        self.all_divisions = []
        self.filter_department_id = None
        self.filter_division_id = None

        # Показываем фильтры
        self.show_filters()

        # Настраиваем фильтры
        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы", None)
            self.filterDepartment.currentIndexChanged.connect(self.on_filter_department_changed)

        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            self.filterSubDepartment.currentIndexChanged.connect(self.on_filter_division_changed)

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
            # Загружаем данные после инициализации сервиса
            QTimer.singleShot(100, self.load_employees)

    def load_filter_data(self, departments: list, divisions: list):
        """Загрузка данных для фильтров"""
        self.all_departments = departments
        self.all_divisions = divisions

        # Заполняем фильтр отделов
        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filterDepartment.blockSignals(True)
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы", None)
            for dept in departments:
                self.filterDepartment.addItem(dept.get('name', 'Без названия'), dept.get('id'))
            self.filterDepartment.blockSignals(False)

        # Заполняем фильтр подразделений
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.blockSignals(True)
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            for div in divisions:
                self.filterSubDepartment.addItem(div.get('name', 'Без названия'), div.get('id'))
            self.filterSubDepartment.blockSignals(False)

    def on_filter_department_changed(self, index):
        """Обработчик изменения фильтра отдела"""
        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filter_department_id = self.filterDepartment.currentData()
        self.refresh_cards()

    def on_filter_division_changed(self, index):
        """Обработчик изменения фильтра подразделения"""
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filter_division_id = self.filterSubDepartment.currentData()
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие окна добавления сотрудника"""
        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

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
            self.load_employees()
            QMessageBox.information(self, "Успех", "Сотрудник добавлен")
            self.employee_added.emit(employee_data)

    def on_edit_clicked(self, employee_id: int):
        """Открытие окна редактирования сотрудника"""
        if not self.employee_service:
            return

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
            success = self.employee_service.update_employee(employee_id, employee_data)
            if success:
                self.load_employees()
                QMessageBox.information(self, "Успех", "Сотрудник обновлён")
                self.employee_updated.emit(employee_data)
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

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if item_type == "employee" and self.employee_service:
            # Используем метод с проверкой задач
            result = self.employee_service.delete_employee_by_id_with_check(item_id)
            if result.get('success'):
                self.load_employees()
                QMessageBox.information(self, "Успех", result.get('message', "Сотрудник удалён"))
            else:
                QMessageBox.warning(self, "Ошибка", result.get('message', "Не удалось удалить сотрудника"))

    def load_employees(self):
        """Загрузка сотрудников через сервис"""
        if self.employee_service:
            employees = self.employee_service.get_employee_card_data()
            self.employees = employees if employees else []
            print(f"📊 Загружено сотрудников: {len(self.employees)}")
            self.refresh_cards()

    def load_data(self, employees: list):
        """Загрузка данных (для совместимости)"""
        self.employees = employees
        print(f"📊 load_data: сотрудников = {len(employees)}")
        self.refresh_cards()

    def get_filtered_employees(self) -> list:
        """Возвращает отфильтрованный список сотрудников"""
        filtered = self.employees.copy()

        # Фильтр по отделу
        if self.filter_department_id:
            filtered = [e for e in filtered if e.get('department_id') == self.filter_department_id]

        # Фильтр по подразделению
        if self.filter_division_id:
            filtered = [e for e in filtered if e.get('division_id') == self.filter_division_id]

        return filtered

    def refresh_cards(self):
        """Обновление карточек"""
        self.clear_cards()

        filtered_employees = self.get_filtered_employees()
        print(f"🔄 Обновление карточек: отображается {len(filtered_employees)} сотрудников")

        for i, employee in enumerate(filtered_employees):
            card = EmployeeCard(employee, self.employee_service, parent=self)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()