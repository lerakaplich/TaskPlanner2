# windows/settings/divisions/divisions_tab.py

from windows.settings.base_tab import BaseTab
from windows.settings.divisions.division_card import DivisionCard
from windows.settings.divisions.division_dialog import DivisionDialog
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout, \
    QRadioButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtCore import QTimer


class DivisionsTab(BaseTab):
    """Вкладка для управления подразделениями"""

    item_deleted = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.divisions = []
        self.employee_service = None

        # Скрываем фильтры
        QTimer.singleShot(0, self.hide_filters_forced)

        if self.btnAdd:
            self.btnAdd.setText("Добавить подразделение")
            self.btnAdd.setObjectName("btnAddDivision")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        self.item_deleted.connect(self.delete_item)

        self.filterDepartment.hide() if hasattr(self, 'filterDepartment') else None
        self.filterSubDepartment.hide() if hasattr(self, 'filterSubDepartment') else None

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service
        if service:
            self.load_divisions()

    def hide_filters_forced(self):
        """Принудительное скрытие фильтров"""
        self.hide_filters()

        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filterDepartment.setVisible(False)
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.setVisible(False)

    def load_divisions(self):
        """Загрузка подразделений через сервис"""
        if self.employee_service:
            # ИСПРАВЛЕНО: используем get_division_card_data вместо get_division_display_data
            self.divisions = self.employee_service.get_division_card_data()
            self.refresh_cards()

    def refresh_cards(self):
        """Обновление карточек"""
        self.clear_cards()

        for i, division in enumerate(self.divisions):
            card = DivisionCard(division, parent=self)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def on_add_clicked(self):
        """Открытие диалога добавления подразделения"""
        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        dialog = DivisionDialog(parent=self, division_data=None, employee_service=self.employee_service)
        dialog.division_saved.connect(self.on_division_saved)
        dialog.exec()

    def on_division_saved(self, division_data: dict):
        """Обработка сохранения подразделения"""
        if self.employee_service:
            self.load_divisions()
            QMessageBox.information(self, "Успех", f"Подразделение сохранено")

    def on_edit_clicked(self, division_id: int):
        """Открытие окна редактирования подразделения"""
        if not self.employee_service:
            return

        # ИСПРАВЛЕНО: используем get_division_card_data вместо get_division_edit_data
        division = self.employee_service.get_division_card_data(division_id)
        if division:
            # ИСПРАВЛЕНО: используем prepare_division_for_dialog для получения данных для диалога
            dialog_data = self.employee_service.prepare_division_for_dialog(division_id)
            if dialog_data:
                dialog = DivisionDialog(parent=self, division_data=dialog_data, employee_service=self.employee_service)
                dialog.division_saved.connect(lambda data: self.on_division_updated(division_id, data))
                dialog.exec()

    def on_division_updated(self, division_id: int, division_data: dict):
        """Обработка редактирования подразделения"""
        if self.employee_service:
            success = self.employee_service.update_division(division_id, division_data)
            if success:
                self.load_divisions()
                QMessageBox.information(self, "Успех", "Подразделение обновлено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить подразделение")

    def on_delete_clicked(self, division_id: int):
        """Удаление подразделения - вызывается из карточки"""
        if not self.employee_service:
            return

        # ИСПРАВЛЕНО: используем существующие методы для проверки зависимостей
        has_departments = self.employee_service.has_departments_in_division(division_id)
        has_employees = self.employee_service.has_employees_in_division(division_id)

        if has_departments or has_employees:
            self.show_delete_with_dependencies_dialog(division_id, has_departments, has_employees)
        else:
            self.confirm_delete(
                title="Удаление подразделения",
                message="Вы уверены, что хотите удалить это подразделение?\nЭто действие нельзя отменить.",
                item_type="division",
                item_id=division_id
            )

    def show_delete_with_dependencies_dialog(self, division_id: int, has_departments: bool, has_employees: bool):
        """Диалог удаления подразделения с зависимостями"""
        if not self.employee_service:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Удаление подразделения")
        dialog.setFixedSize(500, 350)
        dialog.setStyleSheet(self._get_delete_dialog_stylesheet())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        # Предупреждение
        warning_label = QLabel("⚠️ ВНИМАНИЕ!")
        warning_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #D22730;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning_label)

        # Описание зависимостей
        deps_text = "Это подразделение содержит:\n"
        if has_departments:
            deps_text += "• Отделы\n"
        if has_employees:
            deps_text += "• Сотрудников\n"
        deps_label = QLabel(deps_text)
        deps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(deps_label)

        layout.addSpacing(10)

        # Группа радио-кнопок
        radio_group = QButtonGroup(dialog)

        radio_delete_all = QRadioButton("🗑️ Удалить всё (подразделение, все отделы и сотрудников в нём)")
        radio_delete_all.setChecked(True)
        radio_group.addButton(radio_delete_all)
        layout.addWidget(radio_delete_all)

        radio_reassign = QRadioButton("🔄 Переназначить на другое подразделение")
        radio_group.addButton(radio_reassign)
        layout.addWidget(radio_reassign)

        # Комбобокс для выбора подразделения
        reassign_layout = QVBoxLayout()
        reassign_label = QLabel("Выберите подразделение для переназначения:")
        reassign_label.setVisible(False)
        reassign_layout.addWidget(reassign_label)

        self.reassign_combo = QComboBox()
        self.reassign_combo.setVisible(False)

        # Загружаем другие подразделения через сервис - ИСПРАВЛЕНО: используем get_other_divisions
        other_divisions = self.employee_service.get_other_divisions(exclude_division_id=division_id)
        self.reassign_combo.addItem("— Выберите подразделение —", None)
        for div in other_divisions:
            self.reassign_combo.addItem(f"{div.get('name', 'Без названия')} (№{div.get('number', '?')})", div.get('id'))

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
                # ИСПРАВЛЕНО: используем delete_division_by_id
                success = self.employee_service.delete_division_by_id(division_id, delete_departments=True)
                if success:
                    self.load_divisions()
                    QMessageBox.information(self, "Успех", "Подразделение и все связанные данные удалены")
                    dialog.accept()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")
            else:
                target_division_id = self.reassign_combo.currentData()
                if not target_division_id:
                    QMessageBox.warning(dialog, "Ошибка", "Выберите подразделение для переназначения")
                    return

                # ИСПРАВЛЕНО: используем delete_division_by_id с переназначением
                success = self.employee_service.delete_division_by_id(
                    division_id,
                    delete_departments=True,
                    target_division_id=target_division_id
                )
                if success:
                    self.load_divisions()
                    QMessageBox.information(self, "Успех",
                                            "Все отделы и сотрудники переназначены на новое подразделение\nИсходное подразделение удалено")
                    dialog.accept()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось выполнить переназначение")

        btn_delete.clicked.connect(do_delete)
        btn_reassign.clicked.connect(do_delete)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def _get_delete_dialog_stylesheet(self) -> str:
        """Возвращает стили для диалога удаления"""
        return """
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
        """

    def load_data(self, divisions: list):
        """Загрузка данных (для совместимости со старым кодом)"""
        self.divisions = divisions
        self.refresh_cards()

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if item_type == "division" and self.employee_service:
            success = self.employee_service.delete_division_with_options(item_id)
            if success:
                self.load_divisions()
                QMessageBox.information(self, "Успех", "Подразделение удалено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")