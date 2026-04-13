from windows.settings.base_tab import BaseTab
from windows.settings.departments.department_card import DepartmentCard
from windows.settings.departments.department_dialog import DepartmentDialog
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal


class DepartmentsTab(BaseTab):
    """Вкладка для управления отделами"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.departments = []
        self.session = None  # ← ДОБАВЛЯЕМ

        self.hide_filters()

        if self.btnAdd:
            self.btnAdd.setText("Добавить отдел")
            self.btnAdd.setObjectName("btnAddDepartment")
            self.btnAdd.clicked.connect(self.on_add_clicked)

    def set_session(self, session):
        """Установка сессии БД"""
        self.session = session

    def on_add_clicked(self):
        """Открытие диалога добавления отдела"""
        dialog = DepartmentDialog(parent=None, department_data=None, session=self.session)
        dialog.department_saved.connect(self.on_department_saved)
        dialog.exec()

    def on_department_saved(self, department_data: dict):
        """Обработка сохранения отдела"""
        print("Новый отдел:", department_data)
        self.departments.append(department_data)
        self.refresh_cards()

    def load_data(self, departments: list):
        self.departments = departments
        self.refresh_cards()

    def refresh_cards(self):
        self.clear_cards()

        for i, department in enumerate(self.departments):
            card = DepartmentCard(department)
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

    def on_division_saved(self, division_data: dict):
        """Обработка сохранения подразделения"""
        print("Новое подразделение:", division_data)

        # Сохраняем в БД
        if self.session:
            from services.employee_service import EmployeeService
            employee_service = EmployeeService(self.session)

            # Создаём в БД
            new_division = employee_service.create_division_in_db(division_data)
            if new_division:
                self.divisions.append(new_division)
                self.refresh_cards()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить подразделение в БД")

    def on_division_edited(self, division_data: dict):
        """Обработка редактирования подразделения"""
        # Обновляем в БД
        if self.session:
            from services.employee_service import EmployeeService
            employee_service = EmployeeService(self.session)

            success = employee_service.update_division_in_db(
                division_data.get('id'),
                division_data
            )

            if success:
                # Обновляем локальный список
                for i, div in enumerate(self.divisions):
                    if div.get('id') == division_data.get('id'):
                        self.divisions[i] = division_data
                        break
                self.refresh_cards()
                QMessageBox.information(self, "Успех", "Подразделение обновлено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить подразделение в БД")

    def on_delete_clicked(self, division_id: int):
        """Удаление подразделения"""
        self.confirm_delete(
            title="Удаление подразделения",
            message="Вы уверены, что хотите удалить это подразделение?\nЭто действие нельзя отменить.",
            item_type="division",  # Измените на division
            item_id=division_id
        )

    def on_department_edited(self, department_data: dict):
        """Обработка редактирования отдела"""
        for i, dept in enumerate(self.departments):
            if dept.get('id') == department_data.get('id'):
                self.departments[i] = department_data
                break
        self.refresh_cards()

    def on_delete_clicked(self, column_id: int):
        """Удаление колонки"""
        self.confirm_delete(
            title="Удаление отдела",
            message="Вы уверены, что хотите удалить этот отдел?\nЭто действие нельзя отменить.",
            item_type="column",
            item_id=column_id
        )