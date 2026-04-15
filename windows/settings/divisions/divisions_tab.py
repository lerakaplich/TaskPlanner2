from windows.settings.base_tab import BaseTab
from windows.settings.divisions.division_card import DivisionCard
from windows.settings.divisions.division_dialog import DivisionDialog
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout, \
    QRadioButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt


class DivisionsTab(BaseTab):
    """Вкладка для управления подразделениями"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.divisions = []
        self.session = None
        self.employee_service = None
        self.all_employees = []

        # Скрываем фильтры (отделы и подразделения) - делаем это ДО загрузки UI
        # Но так как UI уже загружен в base_tab, используем hide_filters

        if self.btnAdd:
            self.btnAdd.setText("Добавить подразделение")
            self.btnAdd.setObjectName("btnAddDivision")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)

        # Скрываем фильтры после того, как все элементы инициализированы
        # Используем QTimer, чтобы гарантировать, что UI полностью загружен
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.hide_filters_forced)

    def hide_filters_forced(self):
        """Принудительное скрытие фильтров"""
        # Скрываем фильтры через родительский метод
        self.hide_filters()

        # Дополнительно скрываем и отключаем их
        if hasattr(self, 'filterDepartment') and self.filterDepartment:
            self.filterDepartment.setVisible(False)
            # Убираем из layout, чтобы не занимал место
            if self.filterDepartment.parent() and hasattr(self.filterDepartment.parent(), 'layout'):
                layout = self.filterDepartment.parent().layout()
                if layout:
                    layout.removeWidget(self.filterDepartment)

        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filterSubDepartment.setVisible(False)
            # Убираем из layout, чтобы не занимал место
            if self.filterSubDepartment.parent() and hasattr(self.filterSubDepartment.parent(), 'layout'):
                layout = self.filterSubDepartment.parent().layout()
                if layout:
                    layout.removeWidget(self.filterSubDepartment)

        # Также скрываем лейблы фильтров, если они есть
        if hasattr(self, 'labelDepartment') and self.labelDepartment:
            self.labelDepartment.setVisible(False)
        if hasattr(self, 'labelSubDepartment') and self.labelSubDepartment:
            self.labelSubDepartment.setVisible(False)

    def set_employees(self, employees: list):
        """Установка списка сотрудников для отображения имён"""
        self.all_employees = employees
        # Обновляем карточки, если они уже созданы
        self.refresh_cards()

    def _get_employee_name(self, employee_id: int) -> str:
        """Получить ФИО сотрудника по ID"""
        for emp in self.all_employees:
            if emp.get('id') == employee_id:
                last_name = emp.get('last_name', '')
                first_name = emp.get('first_name', '')
                middle_name = emp.get('middle_name', '')

                full_name = f"{last_name} {first_name}"
                if middle_name:
                    full_name += f" {middle_name}"
                return full_name
        return str(employee_id)

    def refresh_cards(self):
        self.clear_cards()

        for i, division in enumerate(self.divisions):
            card = DivisionCard(division, employee_resolver=self._get_employee_name)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def set_session(self, session):
        """Установка сессии БД"""
        self.session = session
        if self.session:
            from services.employee_service import EmployeeService
            self.employee_service = EmployeeService(self.session)

    def on_add_clicked(self):
        """Открытие диалога добавления подразделения"""
        dialog = DivisionDialog(parent=None, division_data=None, session=self.session)
        dialog.division_saved.connect(self.on_division_saved)
        dialog.exec()

    def on_division_saved(self, division_data: dict):
        """Обработка сохранения нового подразделения"""
        print("Новое подразделение:", division_data)

        if self.employee_service:
            # Сохраняем в БД
            new_division = self.employee_service.create_division_in_db(division_data)
            if new_division:
                # Добавляем в локальный список
                self.divisions.append(new_division)
                self.refresh_cards()
                QMessageBox.information(self, "Успех", f"Подразделение '{division_data.get('name')}' создано")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить подразделение в БД")
        else:
            # Просто добавляем в локальный список (без БД)
            self.divisions.append(division_data)
            self.refresh_cards()

    def load_data(self, divisions: list):
        self.divisions = divisions
        self.refresh_cards()

    def on_edit_clicked(self, division_id: int):
        division = next((d for d in self.divisions if d.get('id') == division_id), None)
        if division:
            dialog = DivisionDialog(parent=None, division_data=division, session=self.session)
            dialog.division_saved.connect(self.on_division_edited)
            dialog.exec()

    def on_division_edited(self, division_data: dict):
        """Обработка редактирования подразделения"""
        print("Редактирование подразделения:", division_data)

        if self.employee_service:
            # Обновляем в БД
            success = self.employee_service.update_division_in_db(
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
        else:
            # Просто обновляем локальный список
            for i, div in enumerate(self.divisions):
                if div.get('id') == division_data.get('id'):
                    self.divisions[i] = division_data
                    break
            self.refresh_cards()

    def on_delete_clicked(self, division_id: int):
        """Удаление подразделения - вызывается из карточки"""
        # Проверяем, есть ли связанные отделы и сотрудники
        has_departments = False
        has_employees = False

        if self.employee_service:
            has_departments = self.employee_service.has_departments_in_division(division_id)
            has_employees = self.employee_service.has_employees_in_division(division_id)

        if has_departments or has_employees:
            # Показываем расширенный диалог с выбором действия
            self.show_delete_with_dependencies_dialog(division_id, has_departments, has_employees)
        else:
            # Нет зависимостей - обычное удаление
            self.confirm_delete(
                title="Удаление подразделения",
                message="Вы уверены, что хотите удалить это подразделение?\nЭто действие нельзя отменить.",
                item_type="division",
                item_id=division_id
            )

    def show_delete_with_dependencies_dialog(self, division_id: int, has_departments: bool, has_employees: bool):
        """Диалог удаления подразделения с зависимостями"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Удаление подразделения")
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
        deps_text = "Это подразделение содержит:\n"
        if has_departments:
            deps_text += "• Отделы\n"
        if has_employees:
            deps_text += "• Сотрудников\n"
        deps_label = QLabel(deps_text)
        deps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(deps_label)

        layout.addSpacing(10)

        # Группа радио-кнопок для выбора действия
        radio_group = QButtonGroup(dialog)

        radio_delete_all = QRadioButton("🗑️ Удалить всё (подразделение, все отделы и сотрудников в нём)")
        radio_delete_all.setChecked(True)
        radio_group.addButton(radio_delete_all)
        layout.addWidget(radio_delete_all)

        radio_reassign = QRadioButton("🔄 Переназначить на другое подразделение")
        radio_group.addButton(radio_reassign)
        layout.addWidget(radio_reassign)

        # Комбобокс для выбора подразделения (изначально скрыт)
        reassign_layout = QVBoxLayout()
        reassign_label = QLabel("Выберите подразделение для переназначения:")
        reassign_label.setVisible(False)
        reassign_layout.addWidget(reassign_label)

        self.reassign_combo = QComboBox()
        self.reassign_combo.setVisible(False)
        # Загружаем другие подразделения (кроме текущего)
        other_divisions = [d for d in self.divisions if d.get('id') != division_id]
        self.reassign_combo.addItem("— Выберите подразделение —", None)
        for div in other_divisions:
            self.reassign_combo.addItem(f"{div.get('name', 'Без названия')} (№{div.get('number', '?')})", div.get('id'))
        reassign_layout.addWidget(self.reassign_combo)
        layout.addLayout(reassign_layout)

        # Функция показа/скрытия комбобокса
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

        # Обновляем видимость кнопок при смене радио
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

        # Обработчики
        def do_delete():
            if radio_delete_all.isChecked():
                # Каскадное удаление
                if self.employee_service:
                    success = self.employee_service.delete_division_cascade(division_id)
                    if success:
                        self.divisions = [d for d in self.divisions if d.get('id') != division_id]
                        self.refresh_cards()
                        QMessageBox.information(self, "Успех", "Подразделение и все связанные данные удалены")
                        dialog.accept()
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")
                else:
                    self.divisions = [d for d in self.divisions if d.get('id') != division_id]
                    self.refresh_cards()
                    dialog.accept()
            else:
                # Переназначение
                target_division_id = self.reassign_combo.currentData()
                if not target_division_id:
                    QMessageBox.warning(dialog, "Ошибка", "Выберите подразделение для переназначения")
                    return

                if self.employee_service:
                    success = self.employee_service.reassign_division_dependencies(division_id, target_division_id)
                    if success:
                        # Удаляем исходное подразделение
                        self.employee_service.delete_division_in_db(division_id)
                        self.divisions = [d for d in self.divisions if d.get('id') != division_id]
                        self.refresh_cards()
                        QMessageBox.information(self, "Успех",
                                                f"Все отделы и сотрудники переназначены на новое подразделение\nИсходное подразделение удалено")
                        dialog.accept()
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось выполнить переназначение")
                else:
                    self.divisions = [d for d in self.divisions if d.get('id') != division_id]
                    self.refresh_cards()
                    dialog.accept()

        btn_delete.clicked.connect(do_delete)
        btn_reassign.clicked.connect(do_delete)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления (вызывается по сигналу из BaseTab)"""
        print(f"delete_item вызван: item_type={item_type}, item_id={item_id}")

        if item_type == "division":
            if self.employee_service:
                success = self.employee_service.delete_division_in_db(item_id)
                if success:
                    # Удаляем из локального списка
                    self.divisions = [d for d in self.divisions if d.get('id') != item_id]
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех", "Подразделение удалено")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")
            else:
                # Просто удаляем из локального списка
                self.divisions = [d for d in self.divisions if d.get('id') != item_id]
                self.refresh_cards()