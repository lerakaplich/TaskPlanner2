# windows/settings/employees/employees_tab.py

from PyQt6.QtCore import pyqtSignal, QTimer, Qt
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

    def apply_search_filter(self, query: str):
        """Применяет фильтр поиска к сотрудникам (работает с карточками)"""
        self._search_query = query
        self._apply_search_to_items()

    def clear_search_filter(self):
        """Очищает фильтр поиска"""
        self._search_query = ""
        self._apply_search_to_items()

    def get_filtered_count(self) -> int:
        """Возвращает количество видимых сотрудников (работает с карточками)"""
        count = 0
        for card in self.cards:
            if card.isVisible():
                count += 1
        return count

    def _get_card_search_text(self, card) -> str:
        """Возвращает текст для поиска из карточки сотрудника"""
        search_parts = []

        # ФИО
        if hasattr(card, 'nameLabel'):
            search_parts.append(card.nameLabel.text())

        # Должность
        if hasattr(card, 'positionValue'):
            search_parts.append(card.positionValue.text())

        # Отдел
        if hasattr(card, 'departmentValue'):
            search_parts.append(card.departmentValue.text())

        # Подразделение
        if hasattr(card, 'divisionValue'):
            search_parts.append(card.divisionValue.text())

        # Мобильный телефон - ДОБАВЛЯЕМ
        if hasattr(card, 'mobilePhoneValue'):
            phone_text = card.mobilePhoneValue.text()
            if phone_text and phone_text != '—':
                search_parts.append(phone_text)

        # Рабочий телефон - ДОБАВЛЯЕМ
        if hasattr(card, 'workPhoneValue'):
            work_phone = card.workPhoneValue.text()
            if work_phone and work_phone != '—':
                search_parts.append(work_phone)

        # Email - ДОБАВЛЯЕМ
        if hasattr(card, 'emailValue'):
            email = card.emailValue.text()
            if email and email != '—':
                search_parts.append(email)

        return " ".join(search_parts)

    def _apply_search_to_items(self):
        """Переопределяем для сотрудников - поиск по ФИО, должности, отделу, подразделению"""
        query = self._search_query.lower().strip() if hasattr(self, '_search_query') else ""

        for card in self.cards:
            if query:
                search_text = self._get_card_search_text(card)
                card.setVisible(query in search_text.lower())
            else:
                card.setVisible(True)

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        """
        # ПРЯМАЯ ПРОВЕРКА: проверяем, является ли пользователь начальником отдела
        is_department_head = False
        if self._permission_service and self.employee_service:
            from services.permissions.system_permissions import SystemRole
            try:
                system_role = self.employee_service.get_system_role(self._permission_service.user_id)
                is_department_head = (system_role == SystemRole.DEPARTMENT_HEAD)
                print(f"🔍 Прямая проверка (сотрудники): is_department_head = {is_department_head}")
            except Exception as e:
                print(f"⚠️ Ошибка проверки: {e}")

        # Если пользователь начальник отдела - НЕ включаем read-only режим
        if is_department_head:
            self._read_only_mode = False
            print(f"   ✅ Начальник отдела - режим редактирования сотрудников включен")
        else:
            # Обычная проверка через permission_service
            if self._permission_service:
                is_read_only = self._permission_service.is_employee_tab_read_only()
                self._read_only_mode = is_read_only
            else:
                self._read_only_mode = False

        # Применяем состояние
        self._apply_read_only_state()

        # Скрываем или показываем кнопку добавления
        if self.btnAdd:
            # Начальник отдела может добавлять сотрудников
            if is_department_head:
                self.btnAdd.setVisible(True)
            else:
                self.btnAdd.setVisible(self._should_show_add_buttons())

        # Если режим просмотра - переименовываем кнопки
        if self._read_only_mode:
            self._rename_edit_buttons()

        # Обновляем карточки только если данные уже загружены
        if self.employees:
            self.refresh_cards()

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
        """Открытие окна добавления сотрудника с ограничением по отделам"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        # Проверяем права на добавление
        can_add = False
        user_department_ids = []
        user_division_id = None
        is_department_head = False

        if self._permission_service and self.employee_service:
            from services.permissions.system_permissions import SystemRole
            try:
                user_id = self._permission_service.user_id
                system_role = self.employee_service.get_system_role(user_id)

                if system_role == SystemRole.DEPARTMENT_HEAD:
                    # Начальник отдела может добавлять сотрудников
                    can_add = True
                    is_department_head = True
                    # Получаем ID его отделов и подразделение
                    departments = self.employee_service.get_department_card_data()
                    for dept in departments:
                        boss_ids = dept.get('boss_ids', [])
                        if user_id in boss_ids:
                            user_department_ids.append(dept.get('id'))
                            # Получаем подразделение этого отдела
                            if dept.get('division_id'):
                                user_division_id = dept.get('division_id')
                    print(
                        f"🔍 Начальник отдела: может добавлять в отделы {user_department_ids}, подразделение {user_division_id}")
                elif self._permission_service.can_show_add_buttons_in_settings():
                    can_add = True
            except Exception as e:
                print(f"⚠️ Ошибка проверки: {e}")
                if self._permission_service.can_show_add_buttons_in_settings():
                    can_add = True
        elif self._permission_service and self._permission_service.can_show_add_buttons_in_settings():
            can_add = True

        if not can_add:
            QMessageBox.information(self, "Доступ запрещён", "У вас нет прав на добавление сотрудников")
            return

        # Открываем диалог с ограничением по отделам
        dialog = EmployeeDialog(
            parent=self,
            employee_data=None,
            employee_service=self.employee_service,
            is_registration_mode=False,
            read_only=False,
            permission_service=self._permission_service
        )

        # Если начальник отдела - передаём ID его отделов и подразделения для ограничения
        if user_department_ids:
            dialog.allowed_department_ids = user_department_ids

            # Сохраняем данные для установки после загрузки комбобоксов
            dialog._preset_division_id = user_division_id
            dialog._preset_department_id = user_department_ids[0] if user_department_ids else None

            # Устанавливаем значения после загрузки UI
            # Используем несколько таймеров для гарантии загрузки
            QTimer.singleShot(100,
                              lambda: self._set_department_for_dialog(dialog, user_department_ids[0], user_division_id))

        dialog.employee_saved.connect(self.on_employee_saved)
        dialog.exec()

    def _set_department_for_dialog(self, dialog, department_id, division_id=None):
        """
        Устанавливает подразделение и отдел в диалоге и блокирует их
        """
        try:
            print(f"🔍 _set_department_for_dialog: department_id={department_id}, division_id={division_id}")

            # Проверяем, загружены ли данные в комбобоксы
            if hasattr(dialog, 'comboBoxDivision') and dialog.comboBoxDivision.count() <= 1:
                # Данные ещё не загружены, повторяем попытку через 100 мс
                print("⏳ Данные ещё не загружены, повторяем попытку...")
                QTimer.singleShot(100, lambda: self._set_department_for_dialog(dialog, department_id, division_id))
                return

            # 1. Устанавливаем подразделение
            if division_id and hasattr(dialog, 'comboBoxDivision'):
                for i in range(dialog.comboBoxDivision.count()):
                    if dialog.comboBoxDivision.itemData(i) == division_id:
                        dialog.comboBoxDivision.setCurrentIndex(i)
                        print(f"✅ Установлено подразделение: {dialog.comboBoxDivision.currentText()}")
                        break

            # 2. Ждём загрузки отделов и устанавливаем отдел
            if hasattr(dialog, 'comboBoxDepartment'):
                # Даём время на загрузку отделов после выбора подразделения
                QTimer.singleShot(150, lambda: self._select_and_lock_department(dialog, department_id))

        except Exception as e:
            print(f"⚠️ Ошибка установки отдела: {e}")

    def _select_and_lock_department(self, dialog, department_id):
        """Выбирает и блокирует отдел в диалоге"""
        try:
            print(f"🔍 _select_and_lock_department: department_id={department_id}")

            if hasattr(dialog, 'comboBoxDepartment'):
                # Проверяем, загружены ли отделы
                if dialog.comboBoxDepartment.count() <= 1:
                    # Отделы ещё не загружены, повторяем попытку через 100 мс
                    print("⏳ Отделы ещё не загружены, повторяем попытку...")
                    QTimer.singleShot(100, lambda: self._select_and_lock_department(dialog, department_id))
                    return

                for i in range(dialog.comboBoxDepartment.count()):
                    if dialog.comboBoxDepartment.itemData(i) == department_id:
                        dialog.comboBoxDepartment.setCurrentIndex(i)
                        dialog.comboBoxDepartment.setEnabled(False)
                        print(f"✅ Установлен и заблокирован отдел: {dialog.comboBoxDepartment.currentText()}")
                        break

            # Также блокируем подразделение
            if hasattr(dialog, 'comboBoxDivision'):
                dialog.comboBoxDivision.setEnabled(False)

            print(f"✅ Отдел {department_id} установлен и заблокирован")
        except Exception as e:
            print(f"⚠️ Ошибка блокировки отдела: {e}")

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
            from services.permissions.system_permissions import SystemRole
            can_edit = False
            read_only = True
            user_department_ids = []
            user_division_id = None
            user_division_only = False

            if self._permission_service and self.employee_service:
                try:
                    user_id = self._permission_service.user_id
                    system_role = self.employee_service.get_system_role(user_id)

                    # Если пользователь - начальник отдела
                    if system_role == SystemRole.DEPARTMENT_HEAD:
                        departments = self.employee_service.get_department_card_data()
                        user_department_ids = []
                        for dept in departments:
                            boss_ids = dept.get('boss_ids', [])
                            if user_id in boss_ids:
                                user_department_ids.append(dept.get('id'))
                                if dept.get('division_id'):
                                    user_division_id = dept.get('division_id')

                        employee_dept_id = employee.get('department_id')

                        if employee_id == user_id:
                            can_edit = True
                            read_only = False
                        elif employee_dept_id in user_department_ids:
                            can_edit = True
                            read_only = False

                    # Блок для начальника подразделения
                    elif system_role == SystemRole.DIVISION_HEAD:
                        divisions = self.employee_service.get_divisions_for_selector()
                        for div in divisions:
                            boss_ids = div.get('boss_ids', [])
                            if user_id in boss_ids:
                                user_division_id = div.get('id')
                                break

                        employee_division_id = employee.get('division_id')

                        if employee_id == user_id:
                            can_edit = True
                            read_only = False
                        elif employee_division_id == user_division_id:
                            can_edit = True
                            read_only = False
                            user_division_only = True
                            print(f"🔍 Начальник подразделения редактирует сотрудника из своего подразделения")

                except Exception as e:
                    print(f"⚠️ Ошибка: {e}")

            # Если пользователь не начальник отдела - используем стандартную проверку
            if not read_only and not can_edit:
                if self._permission_service:
                    can_edit = self._permission_service.can_edit_employee(employee_id)
                    read_only = not can_edit

            dialog = EmployeeDialog(
                parent=self,
                employee_data=employee,
                employee_service=self.employee_service,
                is_registration_mode=False,
                read_only=read_only,
                permission_service=self._permission_service
            )

            # Если пользователь - начальник отдела, передаём ID его отделов для ограничения
            if can_edit and user_department_ids:
                dialog.allowed_department_ids = user_department_ids
                # Если только один отдел - устанавливаем его как предустановленный
                if len(user_department_ids) == 1:
                    dialog._preset_department_id = user_department_ids[0]
                    dialog._preset_division_id = user_division_id
                    # Применяем ограничение
                    QTimer.singleShot(100, lambda: dialog._apply_department_restriction())
                else:
                    # Несколько отделов - просто применяем фильтрацию
                    QTimer.singleShot(100, lambda: dialog._filter_departments_by_allowed())

            # Передаём флаг, что это редактирование самого себя (для блокировки отдела/подразделения)
            if employee_id == self._permission_service.user_id:
                dialog.is_self_editing = True
                dialog.department_read_only = True
                dialog.division_read_only = True

            if not read_only and can_edit:
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

        user_id = self._permission_service.user_id if self._permission_service else None

        if employee_id == user_id:
            QMessageBox.warning(self, "Доступ запрещён", "Вы не можете удалить самого себя")
            return

        if self._permission_service and self.employee_service:
            from services.permissions.system_permissions import SystemRole

            can_delete = False
            system_role = self.employee_service.get_system_role(user_id)

            # Проверяем, является ли пользователь начальником отдела
            if system_role == SystemRole.DEPARTMENT_HEAD:
                departments = self.employee_service.get_department_card_data()
                user_department_ids = []
                for dept in departments:
                    boss_ids = dept.get('boss_ids', [])
                    if user_id in boss_ids:
                        user_department_ids.append(dept.get('id'))

                employee = self.employee_service.get_employee_full_info(employee_id)
                if employee:
                    employee_dept_id = employee.get('department_id')
                    can_delete = employee_dept_id in user_department_ids

            # Блок для начальника подразделения
            elif system_role == SystemRole.DIVISION_HEAD:
                divisions = self.employee_service.get_divisions_for_selector()
                user_division_id = None
                for div in divisions:
                    boss_ids = div.get('boss_ids', [])
                    if user_id in boss_ids:
                        user_division_id = div.get('id')
                        break

                employee = self.employee_service.get_employee_full_info(employee_id)
                if employee:
                    employee_division_id = employee.get('division_id')
                    can_delete = (employee_division_id == user_division_id)
                    print(
                        f"🔍 Начальник подразделения: can_delete={can_delete}, emp_div={employee_division_id}, user_div={user_division_id}")

            else:
                can_delete = self._permission_service.can_delete_employee(employee_id)
        else:
            can_delete = True

        if not can_delete:
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на удаление этого сотрудника")
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
        """Загрузка всех сотрудников (без фильтрации)"""
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
        """Обновление карточек с проверкой прав для каждого сотрудника"""
        self.clear_cards()

        # Получаем ID отделов и подразделений, которыми управляет пользователь
        is_department_head = False
        is_division_head = False
        user_id = None
        user_department_ids = []
        user_division_id = None

        if self._permission_service and self.employee_service:
            from services.permissions.system_permissions import SystemRole
            try:
                user_id = self._permission_service.user_id
                system_role = self.employee_service.get_system_role(user_id)
                is_department_head = (system_role == SystemRole.DEPARTMENT_HEAD)
                is_division_head = (system_role == SystemRole.DIVISION_HEAD)

                if is_department_head:
                    departments = self.employee_service.get_department_card_data()
                    for dept in departments:
                        boss_ids = dept.get('boss_ids', [])
                        if user_id in boss_ids:
                            user_department_ids.append(dept.get('id'))
                    print(f"🔍 Начальник отдела: управляет отделами {user_department_ids}")

                # Блок для начальника подразделения
                if is_division_head:
                    divisions = self.employee_service.get_divisions_for_selector()
                    for div in divisions:
                        boss_ids = div.get('boss_ids', [])
                        if user_id in boss_ids:
                            user_division_id = div.get('id')
                            break
                    print(f"🔍 Начальник подразделения: управляет подразделением {user_division_id}")

            except Exception as e:
                print(f"⚠️ Ошибка проверки: {e}")

        filtered_employees = self.get_filtered_employees()
        print(f"🔄 Обновление карточек сотрудников: отображается {len(filtered_employees)}")

        for i, employee in enumerate(filtered_employees):
            print(
                f"   Сотрудник: {employee.get('full_name')}, department_id={employee.get('department_id')}, division_id={employee.get('division_id')}")

            # Проверяем, может ли пользователь редактировать ЭТОГО сотрудника
            can_edit = self._can_edit_employee(
                employee,
                is_department_head,
                is_division_head,
                user_id,
                user_department_ids,
                user_division_id
            )

            card = EmployeeCard(
                employee,
                self.employee_service,
                parent=self,
                read_only=not can_edit,
                permission_service=self._permission_service
            )
            card.edit_clicked.connect(self.on_edit_clicked)
            card.open_clicked.connect(self.on_open_clicked)
            if can_edit:
                card.delete_clicked.connect(self.on_delete_clicked)
            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()

    def _can_edit_employee(self, employee: dict, is_department_head: bool, is_division_head: bool,
                           user_id: int, user_department_ids: list, user_division_id: int = None) -> bool:
        """
        Проверяет, может ли пользователь редактировать сотрудника
        """
        if self._read_only_mode:
            return False

        if not self._permission_service:
            return True

        employee_id = employee.get('id')

        # Начальник может редактировать себя
        if user_id and employee_id == user_id:
            return True

        # Если пользователь - начальник отдела
        if is_department_head and user_id:
            employee_department_id = employee.get('department_id')
            can_edit = employee_department_id in user_department_ids
            if can_edit:
                print(f"   ✅ Начальник отдела может редактировать сотрудника {employee.get('full_name')}")
            else:
                print(f"   🔍 Только просмотр для сотрудника {employee.get('full_name')}")
            return can_edit

        # Блок для начальника подразделения
        if is_division_head and user_id and user_division_id:
            employee_division_id = employee.get('division_id')
            can_edit = (employee_division_id == user_division_id)
            if can_edit:
                print(f"   ✅ Начальник подразделения может редактировать сотрудника {employee.get('full_name')}")
            else:
                print(f"   🔍 Только просмотр для сотрудника {employee.get('full_name')} (чужое подразделение)")
            return can_edit

        return False

    def on_open_clicked(self, employee_id: int):
        """Открытие профиля сотрудника (кнопка Открыть)"""
        from windows.profile.profile_page import ProfilePage

        employee = self.employee_service.get_employee_full_info(employee_id)
        if employee:
            main_window = self.window()
            if hasattr(main_window, 'navigation'):
                # Получаем текущего пользователя из главного окна
                current_user = getattr(main_window, 'current_user', None)

                profile_page = ProfilePage(
                    employee_id=employee_id,
                    current_user=current_user,
                    parent=main_window
                )
                main_window.contentStack.addWidget(profile_page)
                main_window.contentStack.setCurrentWidget(profile_page)