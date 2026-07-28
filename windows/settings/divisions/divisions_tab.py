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
        # Инициализируем поля ДО вызова super().__init__
        self.divisions = []
        self.employee_service = None
        self.reassign_combo = None

        super().__init__(parent)

        # Скрываем фильтры
        QTimer.singleShot(0, self.hide_filters_forced)

        if self.btnAdd:
            self.btnAdd.setText("Добавить подразделение")
            self.btnAdd.setObjectName("btnAddDivision")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        self.item_deleted.connect(self.delete_item)

        self.filterDepartment.hide() if hasattr(self, 'filterDepartment') else None
        self.filterSubDepartment.hide() if hasattr(self, 'filterSubDepartment') else None

    def showEvent(self, event):
        """Обновляет данные при показе вкладки"""
        super().showEvent(event)
        if self.employee_service:
            QTimer.singleShot(50, self.load_divisions)

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        """
        if self._permission_service:
            can_edit = self._permission_service.can_edit_settings()

            if not can_edit:
                try:
                    user_id = self._permission_service.user_id
                    if user_id:
                        editable_divisions = self._permission_service.get_editable_division_ids(user_id)
                        can_edit = len(editable_divisions) > 0
                    else:
                        can_edit = False
                except Exception as e:
                    print(f"⚠️ Ошибка получения редактируемых подразделений: {e}")
                    can_edit = False

            self._read_only_mode = not can_edit

        self._apply_read_only_state()

        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

        if self._read_only_mode:
            self._rename_edit_buttons()
        else:
            self._rename_edit_buttons_to_edit()

        if self.divisions:
            self.refresh_cards()
        else:
            self.load_divisions()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра"""
        super()._apply_read_only_state()

        if self._read_only_mode:
            for combo in (self.filterDepartment, self.filterSubDepartment):
                if combo:
                    combo.setEnabled(False)

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
            try:
                from models.employees import Division
                all_divs = self.employee_service.session.query(Division).all()
                print(f"📊 ПРЯМАЯ ПРОВЕРКА БД: найдено {len(all_divs)} подразделений")
                for div in all_divs:
                    print(f"   - ID={div.id}, name={div.name}, boss='{div.boss}'")

                self.divisions = self.employee_service.get_division_card_data()
                print(f"📊 Загружено подразделений: {len(self.divisions)}")
                self.refresh_cards()
            except Exception as e:
                print(f"❌ Ошибка загрузки подразделений: {e}")
                import traceback
                traceback.print_exc()

    def on_add_clicked(self):
        """Открытие диалога добавления подразделения"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        dialog = DivisionDialog(parent=self, division_data=None, employee_service=self.employee_service, read_only=False)
        dialog.division_saved.connect(self.on_division_saved)
        dialog.exec()

    def on_division_saved(self, division_data: dict):
        """Обработка сохранения подразделения"""
        if self.employee_service:
            self.load_divisions()
            QMessageBox.information(self, "Успех", f"Подразделение сохранено")

    def on_division_updated(self, division_id: int, division_data: dict):
        """Обработка редактирования подразделения"""
        if self._read_only_mode:
            return

        if self.employee_service:
            success = self.employee_service.update_division(division_id, division_data)
            if success:
                self.load_divisions()
                QMessageBox.information(self, "Успех", "Подразделение обновлено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить подразделение")

    def on_delete_clicked(self, division_id: int):
        """Удаление подразделения - вызывается из карточки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        if not self.employee_service:
            return

        # Проверяем, может ли пользователь удалять это подразделение
        if self._permission_service and not self._permission_service.can_delete_division(division_id):
            QMessageBox.warning(self, "Ошибка", "У вас нет прав на удаление этого подразделения")
            return

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

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if self._read_only_mode:
            return

        if item_type == "division" and self.employee_service:
            success = self.employee_service.delete_division_by_id(item_id, delete_departments=True)
            if success:
                self.load_divisions()
                QMessageBox.information(self, "Успех", "Подразделение удалено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")

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

        warning_label = QLabel("⚠️ ВНИМАНИЕ!")
        warning_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #D22730;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning_label)

        deps_text = "Это подразделение содержит:\n"
        if has_departments:
            deps_text += "• Отделы\n"
        if has_employees:
            deps_text += "• Сотрудников\n"
        deps_label = QLabel(deps_text)
        deps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(deps_label)

        layout.addSpacing(10)

        radio_group = QButtonGroup(dialog)

        radio_delete_all = QRadioButton("🗑️ Удалить всё (подразделение, все отделы и сотрудников в нём)")
        radio_delete_all.setChecked(True)
        radio_group.addButton(radio_delete_all)
        layout.addWidget(radio_delete_all)

        radio_reassign = QRadioButton("🔄 Переназначить на другое подразделение")
        radio_group.addButton(radio_reassign)
        layout.addWidget(radio_reassign)

        reassign_layout = QVBoxLayout()
        reassign_label = QLabel("Выберите подразделение для переназначения:")
        reassign_label.setVisible(False)
        reassign_layout.addWidget(reassign_label)

        self.reassign_combo = QComboBox()
        self.reassign_combo.setVisible(False)

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

    def _rename_edit_buttons_to_edit(self):
        """Переименовывает кнопки редактирования на 'Редактировать'"""
        for card in self.cards:
            if hasattr(card, 'editButton'):
                card.editButton.setText("Редактировать")

    def refresh_cards(self):
        """Обновление карточек с учётом прав - ПОКАЗЫВАЕМ ВСЕ ПОДРАЗДЕЛЕНИЯ"""
        print(f"🔄 refresh_cards: divisions count = {len(self.divisions)}")
        print(f"🔄 refresh_cards: self._read_only_mode = {self._read_only_mode}")
        print(f"🔄 refresh_cards: self._permission_service = {self._permission_service}")

        if self._permission_service:
            print(f"🔄 refresh_cards: user_id = {self._permission_service.user_id}")

        self.clear_cards()
        if not self.divisions:
            return

        # Получаем ID подразделений, которые пользователь может редактировать
        editable_ids = set()
        user_id = None
        if self._permission_service:
            user_id = self._permission_service.user_id

        if self._permission_service and user_id:
            try:
                editable_ids = set(self._permission_service.get_editable_division_ids(user_id))
                print(f"🔍 editable_ids (можно редактировать): {editable_ids}")
            except Exception as e:
                print(f"⚠️ Ошибка получения редактируемых подразделений: {e}")

        # ✅ ПОКАЗЫВАЕМ ВСЕ ПОДРАЗДЕЛЕНИЯ, а не только те, которые можно редактировать
        for i, division in enumerate(self.divisions):
            division_id = division.get('id')

            # Определяем, может ли пользователь редактировать это подразделение
            can_edit_this = division_id in editable_ids

            # ✅ НЕ ИСПОЛЬЗУЕМ can_edit_settings для фильтрации подразделений
            # Если пользователь может редактировать настройки в целом - может редактировать все
            if self._permission_service and self._permission_service.can_edit_settings():
                can_edit_this = True

            card_read_only = not can_edit_this

            print(f"   📋 Подразделение: {division.get('name')} (ID={division_id}), can_edit={can_edit_this}")

            card = DivisionCard(division, parent=self, read_only=card_read_only)
            card.edit_clicked.connect(self.on_edit_clicked)

            # ✅ КНОПКА УДАЛЕНИЯ: только если пользователь может удалять это подразделение
            can_delete = False
            if self._permission_service:
                can_delete = self._permission_service.can_delete_division(division_id)

            if hasattr(card, 'deleteButton'):
                card.deleteButton.setVisible(can_delete)
                if can_delete:
                    card.deleteButton.clicked.connect(lambda checked, did=division_id: self.on_delete_clicked(did))

            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def on_edit_clicked(self, division_id: int):
        """Открытие окна редактирования/просмотра подразделения"""
        if not self.employee_service:
            return

        can_edit = False
        if self._permission_service:
            can_edit = self._permission_service.can_edit_division(division_id)

        division = self.employee_service.get_division_card_data(division_id)
        if division:
            dialog_data = self.employee_service.prepare_division_for_dialog(division_id)
            if dialog_data:
                dialog = DivisionDialog(
                    parent=self,
                    division_data=dialog_data,
                    employee_service=self.employee_service,
                    read_only=not can_edit
                )
                if can_edit:
                    dialog.division_saved.connect(lambda data: self.on_division_updated(division_id, data))
                dialog.exec()