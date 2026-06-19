# windows/settings/employees/employees_tab.py

from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from services.permissions.app_permissions import AppRole
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
        # Инициализируем поля ДО вызова super().__init__
        # чтобы они были доступны в setup_permission_ui
        self.employee_service = None
        self.employees = []
        self.all_departments = []
        self.all_divisions = []
        self.filter_department_id = None
        self.filter_division_id = None

        # Вызываем super() - теперь поля уже инициализированы
        super().__init__(parent)

        # Показываем фильтры
        self.show_filters()

        # Принудительно показываем toolsFrame
        if self.tools_frame:
            self.tools_frame.setVisible(True)
            self.tools_frame.show()

        # Настраиваем фильтры (ОБА - QComboBox)
        if self.filterDepartment is not None:
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы", None)
            self.filterDepartment.currentIndexChanged.connect(self.on_filter_department_changed)
            self.filterDepartment.setVisible(True)

        if self.filterSubDepartment is not None:
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            self.filterSubDepartment.currentIndexChanged.connect(self.on_filter_division_changed)
            self.filterSubDepartment.setVisible(True)

        # Настраиваем кнопку "Добавить"
        if self.btnAdd:
            self.btnAdd.setText("Добавить сотрудника")
            self.btnAdd.setObjectName("btnAddEmployee")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        Для USER - только просмотр (read-only)
        Для ADMIN и SUPER_ADMIN - полный доступ
        """
        # Определяем режим на основе роли
        if self._permission_service:
            is_read_only = self._permission_service.is_employee_tab_read_only()
            self._read_only_mode = is_read_only

        # Применяем состояние
        self._apply_read_only_state()

        # Скрываем или показываем кнопку добавления
        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

        # Если режим просмотра - переименовываем кнопки
        if self._read_only_mode:
            self._rename_edit_buttons()

        # Обновляем карточки только если данные уже загружены
        if self.employees:
            self.refresh_cards()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра"""
        super()._apply_read_only_state()

        # Блокируем фильтры в режиме просмотра
        if self._read_only_mode:
            for combo in (self.filterDepartment, self.filterSubDepartment):
                if combo:
                    combo.setEnabled(False)

    def _rename_edit_buttons(self):
        """
        Переименовывает кнопки редактирования во всех карточках на "Подробнее"
        """
        for card in self.cards:
            if hasattr(card, 'editButton'):
                card.editButton.setText("Подробнее")

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service
        if service:
            self.load_filter_data()
            QTimer.singleShot(100, self.load_employees)

    def load_filter_data(self):
        """Загрузка данных для фильтров из сервиса"""
        if not self.employee_service:
            return

        filter_data = self.employee_service.get_filter_data()
        self.all_departments = filter_data.get('departments', [])
        self.all_divisions = filter_data.get('divisions', [])

        if self.filterDepartment is not None:
            self.filterDepartment.blockSignals(True)
            self.filterDepartment.clear()
            self.filterDepartment.addItem("Все отделы", None)
            for dept in self.all_departments:
                self.filterDepartment.addItem(dept.get('name', 'Без названия'), dept.get('id'))
            self.filterDepartment.blockSignals(False)

        if self.filterSubDepartment is not None:
            self.filterSubDepartment.blockSignals(True)
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            for div in self.all_divisions:
                self.filterSubDepartment.addItem(div.get('name', 'Без названия'), div.get('id'))
            self.filterSubDepartment.blockSignals(False)

        if self.tools_frame:
            self.tools_frame.show()
            self.tools_frame.setVisible(True)
            self.tools_frame.update()

        self.updateGeometry()

    def on_filter_department_changed(self, index):
        """Обработчик изменения фильтра отдела"""
        if self.filterDepartment is not None:
            self.filter_department_id = self.filterDepartment.currentData()
        self.refresh_cards()

    def on_filter_division_changed(self, index):
        """Обработчик изменения фильтра подразделения"""
        if self.filterSubDepartment is not None:
            self.filter_division_id = self.filterSubDepartment.currentData()
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие окна добавления сотрудника"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        dialog = EmployeeDialog(
            parent=self,
            employee_data=None,
            employee_service=self.employee_service,
            is_registration_mode=False,
            read_only=False
        )
        dialog.employee_saved.connect(self.on_employee_saved)
        dialog.exec()

    def on_employee_saved(self, employee_data: dict):
        """Вызывается после успешного сохранения сотрудника"""
        if self.employee_service:
            self.load_employees()
            self.load_filter_data()
            QMessageBox.information(self, "Успех", "Сотрудник добавлен")
            self.employee_added.emit(employee_data)

    def on_edit_clicked(self, employee_id: int):
        """Открытие окна редактирования/просмотра сотрудника"""
        if not self.employee_service:
            return

        employee = self.employee_service.get_employee_full_info(employee_id)
        if employee:
            dialog = EmployeeDialog(
                parent=self,
                employee_data=employee,
                employee_service=self.employee_service,
                is_registration_mode=False,
                read_only=self._read_only_mode  # Передаём режим просмотра
            )
            if not self._read_only_mode:
                dialog.employee_saved.connect(lambda data: self.on_employee_updated(employee_id, data))
            dialog.exec()

    def on_employee_updated(self, employee_id: int, employee_data: dict):
        """Обработка редактирования сотрудника"""
        if self._read_only_mode:
            return

        if self.employee_service:
            success = self.employee_service.update_employee(employee_id, employee_data)
            if success:
                self.load_employees()
                self.load_filter_data()
                QMessageBox.information(self, "Успех", "Сотрудник обновлён")
                self.employee_updated.emit(employee_data)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить сотрудника")

    def on_delete_clicked(self, employee_id: int):
        """Удаление сотрудника - вызывается из карточки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        self.confirm_delete(
            title="Удаление сотрудника",
            message="Вы уверены, что хотите удалить этого сотрудника?\nЭто действие нельзя отменить.",
            item_type="employee",
            item_id=employee_id
        )

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if self._read_only_mode:
            return

        if item_type == "employee" and self.employee_service:
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
            self.refresh_cards()

    def load_data(self, employees: list):
        """Загрузка данных (для совместимости)"""
        self.employees = employees
        self.refresh_cards()

    def get_filtered_employees(self) -> list:
        """Возвращает отфильтрованный список сотрудников"""
        filtered = self.employees.copy()

        if self.filter_department_id:
            filtered = [e for e in filtered if e.get('department_id') == self.filter_department_id]

        if self.filter_division_id:
            filtered = [e for e in filtered if e.get('division_id') == self.filter_division_id]

        return filtered

    def refresh_cards(self):
        """Обновление карточек"""
        self.clear_cards()

        filtered_employees = self.get_filtered_employees()

        for i, employee in enumerate(filtered_employees):
            card = EmployeeCard(
                employee,
                self.employee_service,
                parent=self,
                read_only=self._read_only_mode
            )
            card.edit_clicked.connect(self.on_edit_clicked)
            if not self._read_only_mode:
                card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()