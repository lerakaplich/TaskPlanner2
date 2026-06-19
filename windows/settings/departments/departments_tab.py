# windows/settings/departments/departments_tab.py

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QButtonGroup, QRadioButton, QComboBox, \
    QHBoxLayout, QPushButton, QLineEdit

from windows.settings.base_tab import BaseTab
from windows.settings.departments.department_card import DepartmentCard
from windows.settings.departments.department_dialog import DepartmentDialog


class DepartmentsTab(BaseTab):
    """Вкладка для управления отделами"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        # Инициализируем поля ДО вызова super().__init__
        self.departments = []
        self.all_divisions = []
        self.employee_service = None
        self.filter_division_id = None
        self.filter_search_text = ""

        super().__init__(parent)

        # Показываем фильтры
        self.show_filters()

        # Настраиваем фильтры
        if hasattr(self, 'filterDepartment'):
            if isinstance(self.filterDepartment, QLineEdit):
                self.filterDepartment.setPlaceholderText("Поиск по названию...")
                self.filterDepartment.textChanged.connect(self.on_filter_text_changed)
            else:
                self.filterDepartment.setEditable(True)
                self.filterDepartment.setPlaceholderText("Поиск по названию...")
                self.filterDepartment.lineEdit().textChanged.connect(self.on_filter_text_changed)

        if hasattr(self, 'filterSubDepartment'):
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            self.filterSubDepartment.currentIndexChanged.connect(self.on_filter_division_changed)

        if self.btnAdd:
            self.btnAdd.setText("Добавить отдел")
            self.btnAdd.setObjectName("btnAddDepartment")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        self.item_deleted.connect(self.delete_item)

        self.filterDepartment.hide() if hasattr(self, 'filterDepartment') else None

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        Для USER - только просмотр (read-only)
        Для ADMIN и SUPER_ADMIN - полный доступ
        """
        # Определяем режим на основе роли
        if self._permission_service:
            is_read_only = self._permission_service.is_departments_tab_read_only()
            self._read_only_mode = is_read_only

        # Применяем состояние
        self._apply_read_only_state()

        # Скрываем или показываем кнопку добавления
        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

        # Блокируем фильтры в режиме просмотра
        if self._read_only_mode:
            if hasattr(self, 'filterDepartment') and self.filterDepartment:
                self.filterDepartment.setEnabled(False)
            if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
                self.filterSubDepartment.setEnabled(False)

        # Если режим просмотра - переименовываем кнопки
        if self._read_only_mode:
            self._rename_edit_buttons()

        # Обновляем карточки только если данные уже загружены
        if self.departments:
            self.refresh_cards()

    def set_employee_service(self, service):
        """Установка сервиса для работы с БД"""
        self.employee_service = service
        if service:
            # Загружаем данные для фильтров
            self.load_filter_data()
            # Загружаем отделы
            QTimer.singleShot(100, self.load_departments)

    def set_session(self, session):
        """Установка сессии БД (для совместимости)"""
        self.session = session

    def load_filter_data(self):
        """Загрузка данных для фильтров через сервис"""
        if self.employee_service:
            divisions = self.employee_service.get_all_divisions()
            self.all_divisions = divisions if divisions else []
            print(f"📊 Загружено подразделений для фильтра: {len(self.all_divisions)}")

            if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
                self.filterSubDepartment.blockSignals(True)
                self.filterSubDepartment.clear()
                self.filterSubDepartment.addItem("Все подразделения", None)
                for div in self.all_divisions:
                    self.filterSubDepartment.addItem(div.get('name', 'Без названия'), div.get('id'))
                self.filterSubDepartment.blockSignals(False)

    def on_filter_text_changed(self, text):
        """Обработчик изменения текста поиска"""
        self.filter_search_text = text if text else ""
        self.refresh_cards()

    def on_filter_division_changed(self, index):
        """Обработчик изменения выбранного подразделения"""
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment:
            self.filter_division_id = self.filterSubDepartment.currentData()
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие диалога добавления отдела"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        dialog = DepartmentDialog(parent=self, department_data=None, employee_service=self.employee_service, read_only=False)
        dialog.department_saved.connect(self.on_department_saved)
        dialog.exec()

    def on_department_saved(self, department_data: dict):
        """Обработка сохранения отдела"""
        if self.employee_service:
            self.load_departments()
            QMessageBox.information(self, "Успех", f"Отдел сохранён")

    def load_departments(self):
        """Загрузка отделов через сервис"""
        if self.employee_service:
            departments = self.employee_service.get_department_card_data()
            self.departments = departments if departments else []
            print(f"📊 Загружено отделов: {len(self.departments)}")
            self.refresh_cards()

    def load_data(self, departments: list):
        """Загрузка данных (для совместимости)"""
        self.departments = departments
        print(f"📊 load_data: отделов = {len(departments)}")
        self.refresh_cards()

    def load_division_filters(self):
        """Загрузка подразделений в фильтр (для совместимости)"""
        if hasattr(self, 'filterSubDepartment') and self.filterSubDepartment and hasattr(self, 'all_divisions'):
            self.filterSubDepartment.clear()
            self.filterSubDepartment.addItem("Все подразделения", None)
            for div in self.all_divisions:
                self.filterSubDepartment.addItem(div.get('name', ''), div.get('id'))

    def refresh_cards(self):
        """Обновление карточек с применением фильтров"""
        self.clear_cards()

        filtered_departments = self.get_filtered_departments()
        print(f"🔄 Обновление карточек отделов: отображается {len(filtered_departments)} из {len(self.departments)}")

        for i, department in enumerate(filtered_departments):
            card = DepartmentCard(
                department,
                self.employee_service,
                parent=self,
                read_only=self._read_only_mode
            )
            card.edit_clicked.connect(self.on_edit_clicked)
            if not self._read_only_mode:
                card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def get_filtered_departments(self) -> list:
        """Возвращает отфильтрованный список отделов"""
        filtered = self.departments.copy()

        # Фильтр по подразделению
        if self.filter_division_id:
            filtered = [d for d in filtered if d.get('division_id') == self.filter_division_id]

        # Поиск по названию
        if self.filter_search_text:
            search_lower = self.filter_search_text.lower()
            filtered = [d for d in filtered if search_lower in d.get('name', '').lower()]

        return filtered

    def on_edit_clicked(self, department_id: int):
        """Открытие окна редактирования/просмотра отдела"""
        if not self.employee_service:
            return

        department = self.employee_service.get_department_card_data(department_id)
        if department:
            dialog = DepartmentDialog(
                parent=self,
                department_data=department,
                employee_service=self.employee_service,
                read_only=self._read_only_mode
            )
            if not self._read_only_mode:
                dialog.department_saved.connect(lambda data: self.on_department_updated(department_id, data))
            dialog.exec()

    def on_department_updated(self, department_id: int, department_data: dict):
        """Обработка редактирования отдела"""
        if self._read_only_mode:
            return

        if self.employee_service:
            success = self.employee_service.update_department(department_id, department_data)
            if success:
                self.load_departments()
                QMessageBox.information(self, "Успех", "Отдел обновлён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить отдел")

    def on_delete_clicked(self, department_id: int):
        """Удаление отдела - вызывается из карточки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        if not self.employee_service:
            return

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

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if self._read_only_mode:
            return

        if item_type == "department" and self.employee_service:
            success = self.employee_service.delete_department_by_id(item_id)
            if success:
                self.load_departments()
                QMessageBox.information(self, "Успех", "Отдел удалён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить отдел")

    def show_delete_with_dependencies_dialog(self, department_id: int):
        """Диалог удаления отдела с сотрудниками"""
        if not self.employee_service:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Удаление отдела")
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
        deps_label = QLabel("В этом отделе есть сотрудники.\nЧто вы хотите сделать?")
        deps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(deps_label)

        layout.addSpacing(10)

        # Группа радио-кнопок
        radio_group = QButtonGroup(dialog)

        radio_delete_all = QRadioButton("🗑️ Удалить всё (отдел и всех сотрудников в нём)")
        radio_delete_all.setChecked(True)
        radio_group.addButton(radio_delete_all)
        layout.addWidget(radio_delete_all)

        radio_reassign = QRadioButton("🔄 Переназначить сотрудников в другой отдел")
        radio_group.addButton(radio_reassign)
        layout.addWidget(radio_reassign)

        # Комбобокс для выбора отдела
        reassign_layout = QVBoxLayout()
        reassign_label = QLabel("Выберите отдел для переназначения сотрудников:")
        reassign_label.setVisible(False)
        reassign_layout.addWidget(reassign_label)

        self.reassign_combo = QComboBox()
        self.reassign_combo.setVisible(False)

        # Загружаем другие отделы через сервис
        other_departments = self.employee_service.get_other_departments(department_id)
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
                success = self.employee_service.delete_department_by_id(department_id, delete_employees=True)
                if success:
                    self.load_departments()
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех", "Отдел и все сотрудники удалены")
                    dialog.accept()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить отдел")
            else:
                target_department_id = self.reassign_combo.currentData()
                if not target_department_id:
                    QMessageBox.warning(dialog, "Ошибка", "Выберите отдел для переназначения")
                    return

                success = self.employee_service.delete_department_by_id(
                    department_id,
                    delete_employees=True,
                    target_department_id=target_department_id
                )
                if success:
                    self.load_departments()
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех",
                                            "Все сотрудники переназначены в новый отдел\nИсходный отдел удалён")
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