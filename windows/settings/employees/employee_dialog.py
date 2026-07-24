# windows/settings/employees/employee_dialog.py

import os
from datetime import date
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6 import uic, QtCore
from PyQt6.QtCore import QDate, pyqtSignal, QTimer
from PyQt6.QtGui import QValidator


class PhoneValidator(QValidator):
    """Валидатор для номера телефона (только цифры, максимум 9)"""

    def validate(self, input_str, pos):
        filtered = ''.join([c for c in input_str if c.isdigit()])
        if len(filtered) > 9:
            filtered = filtered[:9]

        if input_str != filtered:
            return QValidator.State.Invalid, filtered, len(filtered)

        if len(filtered) <= 9:
            return QValidator.State.Acceptable, filtered, pos

        return QValidator.State.Invalid, filtered[:9], 9


class EmployeeDialog(QDialog):
    """Диалоговое окно для добавления/редактирования сотрудника"""
    employee_saved = pyqtSignal(dict)

    def __init__(self, parent=None, employee_data=None, employee_service=None,
                 is_registration_mode=False, read_only=False, permission_service=None):
        super().__init__(parent)

        self.employee_service = employee_service
        self.employee_data = employee_data
        self.is_registration_mode = is_registration_mode
        self.read_only = read_only
        self.permission_service = permission_service
        self._can_view_contacts = self._check_contact_permission()

        # Флаги для редактирования себя
        self.is_self_editing = False
        self.department_read_only = False
        self.division_read_only = False

        # ID для предустановки (для начальника отдела)
        self._preset_division_id = None
        self._preset_department_id = None
        self.allowed_department_ids = None  # Список ID отделов, которые может выбирать начальник

        # Сохраняем данные сотрудника для восстановления после загрузки комбобоксов
        self._saved_division_id = None
        self._saved_department_id = None

        # Определяем путь к UI файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "employees", "employee_dialog.ui"
        )

        # Загружаем UI
        uic.loadUi(ui_path, self)

        # Загружаем данные через сервис
        self.load_data_from_service()

        # Настраиваем поле телефона
        self.setup_phone_field()

        # Определяем режим
        self.is_edit_mode = employee_data is not None and employee_data.get('id') is not None

        # Сохраняем ID отдела и подразделения из данных сотрудника
        if self.is_edit_mode and employee_data:
            self._saved_division_id = employee_data.get('division_id')
            self._saved_department_id = employee_data.get('department_id')

        # Настраиваем UI в зависимости от режима
        self.setup_ui_mode()

        # Настраиваем клавиатуру
        self.setup_keyboard_navigation()

        # Применяем режим только просмотра
        self._apply_read_only_state()

        # Подключаем сигналы
        self.btnSave.clicked.connect(self.save_employee)
        self.btnAddDivision.clicked.connect(self.add_division)
        self.btnAddDepartment.clicked.connect(self.add_department)
        self.comboBoxDivision.currentIndexChanged.connect(self.on_division_changed)

        self.dateEditBirthDate.setMaximumDate(QDate.currentDate())

        # Применяем предустановленные значения
        QTimer.singleShot(200, self._apply_preset_values)

    def _apply_preset_values(self):
        """
        Применяет предустановленные значения подразделения и отдела
        Вызывается после полной загрузки комбобоксов
        """
        print(f"🔍 _apply_preset_values: saved_division_id={self._saved_division_id}, saved_department_id={self._saved_department_id}")
        print(f"   preset_division_id={self._preset_division_id}, preset_department_id={self._preset_department_id}")
        print(f"   allowed_department_ids={self.allowed_department_ids}")

        # Определяем, что устанавливать: сохранённые данные или предустановленные
        division_id = self._preset_division_id or self._saved_division_id
        department_id = self._preset_department_id or self._saved_department_id

        # 1. Устанавливаем подразделение
        if division_id and hasattr(self, 'comboBoxDivision'):
            for i in range(self.comboBoxDivision.count()):
                if self.comboBoxDivision.itemData(i) == division_id:
                    self.comboBoxDivision.setCurrentIndex(i)
                    print(f"✅ Установлено подразделение: {self.comboBoxDivision.currentText()}")
                    break

        # 2. Устанавливаем отдел (после загрузки списка отделов)
        if department_id and hasattr(self, 'comboBoxDepartment'):
            QTimer.singleShot(150, lambda: self._apply_preset_department(department_id))

        # 3. Применяем ограничения для начальника отдела
        self._apply_department_restriction()

    def _filter_departments_by_allowed(self):
        """Фильтрует список отделов, оставляя только разрешённые для начальника"""
        if not self.allowed_department_ids or not hasattr(self, 'comboBoxDepartment'):
            return

        current_text = self.comboBoxDepartment.currentText()
        current_data = self.comboBoxDepartment.currentData()

        # Сохраняем текущий индекс
        self.comboBoxDepartment.blockSignals(True)
        self.comboBoxDepartment.clear()
        self.comboBoxDepartment.addItem("Выберите отдел", None)

        # Добавляем только разрешённые отделы
        current_division_id = self.comboBoxDivision.currentData()
        if current_division_id and current_division_id in self.departments_by_division:
            for dept in self.departments_by_division[current_division_id]:
                dept_id = dept.get('id')
                if dept_id in self.allowed_department_ids:
                    self.comboBoxDepartment.addItem(dept.get("name", "Без названия"), dept_id)

        # Восстанавливаем выбор
        for i in range(self.comboBoxDepartment.count()):
            if self.comboBoxDepartment.itemData(i) == current_data:
                self.comboBoxDepartment.setCurrentIndex(i)
                break

        self.comboBoxDepartment.blockSignals(False)
        print(f"✅ Отфильтрованы отделы: разрешены только {self.allowed_department_ids}")

    def _apply_preset_department(self, department_id):
        """Применяет предустановленный отдел и блокирует комбобоксы"""
        if not department_id:
            return

        if hasattr(self, 'comboBoxDepartment'):
            # Проверяем, загружены ли отделы
            if self.comboBoxDepartment.count() <= 1:
                # Отделы ещё не загружены, повторяем попытку
                print("⏳ Отделы ещё не загружены, повторяем попытку...")
                QTimer.singleShot(100, lambda: self._apply_preset_department(department_id))
                return

            for i in range(self.comboBoxDepartment.count()):
                if self.comboBoxDepartment.itemData(i) == department_id:
                    self.comboBoxDepartment.setCurrentIndex(i)
                    print(f"✅ Установлен отдел: {self.comboBoxDepartment.currentText()}")
                    break

    def _check_contact_permission(self) -> bool:
        """Проверяет, может ли пользователь видеть контакты этого сотрудника"""
        if not self.permission_service:
            return True

        employee_id = self.employee_data.get('id') if self.employee_data else None
        if not employee_id:
            return True

        return self.permission_service.can_view_contacts(employee_id)

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра к диалогу"""
        if self.read_only:
            # Скрываем кнопку сохранения
            if hasattr(self, 'btnSave'):
                self.btnSave.setVisible(False)
                self.btnSave.hide()

            # Скрываем кнопки добавления подразделения и отдела
            if hasattr(self, 'btnAddDivision'):
                self.btnAddDivision.setVisible(False)
                self.btnAddDivision.hide()
            if hasattr(self, 'btnAddDepartment'):
                self.btnAddDepartment.setVisible(False)
                self.btnAddDepartment.hide()

            # Блокируем все поля ввода
            self._set_all_fields_read_only()

            # Скрываем комбобокс ролей (если есть)
            if hasattr(self, 'comboBoxRole'):
                self.comboBoxRole.setEnabled(False)

            # Если пользователь не может видеть контакты - скрываем телефон и email
            if not self._can_view_contacts:
                # Скрываем поля телефона и email
                if hasattr(self, 'lineEditMobilePhone'):
                    self.lineEditMobilePhone.setVisible(False)
                if hasattr(self, 'lineEditWorkPhone'):
                    self.lineEditWorkPhone.setVisible(False)
                if hasattr(self, 'lineEditEmail'):
                    self.lineEditEmail.setVisible(False)

                # Скрываем соответствующие метки
                for label_name in ['labelMobilePhone', 'labelWorkPhone', 'labelEmail']:
                    if hasattr(self, label_name):
                        getattr(self, label_name).setVisible(False)

                # Добавляем пояснение
                if hasattr(self, 'infoLabel'):
                    self.infoLabel.setText("🔒 Контактная информация недоступна")
                    self.infoLabel.setStyleSheet("color: #999; font-size: 12px;")
                    self.infoLabel.setVisible(True)
        else:
            # Если это редактирование себя - блокируем отдел и подразделение
            if self.is_self_editing:
                if hasattr(self, 'comboBoxDepartment') and self.department_read_only:
                    self.comboBoxDepartment.setEnabled(False)
                if hasattr(self, 'comboBoxDivision') and self.division_read_only:
                    self.comboBoxDivision.setEnabled(False)
                # Добавляем пояснение
                if hasattr(self, 'infoLabel'):
                    self.infoLabel.setText("ℹ️ Отдел и подразделение нельзя изменить")
                    self.infoLabel.setStyleSheet("color: #666; font-size: 11px;")
                    self.infoLabel.setVisible(True)

    def _set_all_fields_read_only(self):
        """Блокирует все поля ввода"""
        read_only_fields = [
            self.lineEditLastName,
            self.lineEditFirstName,
            self.lineEditMiddleName,
            self.dateEditBirthDate,
            self.comboBoxDivision,
            self.comboBoxDepartment,
            self.lineEditPosition,
            self.lineEditMobilePhone,
            self.lineEditWorkPhone,
            self.lineEditEmail,
        ]

        for field in read_only_fields:
            if field:
                if hasattr(field, 'setReadOnly'):
                    field.setReadOnly(True)
                elif hasattr(field, 'setEnabled'):
                    field.setEnabled(False)

    def load_data_from_service(self):
        """Загружает данные через сервис"""
        if self.employee_service:
            filter_data = self.employee_service.get_filter_data()
            self.all_divisions = filter_data.get('divisions', [])
            self.all_departments = filter_data.get('departments', [])

            # Группируем отделы по подразделениям
            self.departments_by_division = {}
            for dept in self.all_departments:
                div_id = dept.get('division_id')
                if div_id not in self.departments_by_division:
                    self.departments_by_division[div_id] = []
                self.departments_by_division[div_id].append(dept)

            # Загружаем роли если нужно
            if hasattr(self, 'comboBoxRole'):
                self.comboBoxRole.clear()
                for role in self.employee_service.get_roles_list():
                    self.comboBoxRole.addItem(role)
        else:
            self.all_divisions = []
            self.all_departments = []
            self.departments_by_division = {}

    def setup_phone_field(self):
        """Настройка поля телефона"""
        validator = PhoneValidator()
        self.lineEditMobilePhone.setValidator(validator)
        self.lineEditMobilePhone.setText("")

        def on_phone_edit(text):
            digits = ''.join([c for c in text if c.isdigit()])
            if len(digits) > 9:
                digits = digits[:9]

            if digits != text:
                self.lineEditMobilePhone.blockSignals(True)
                self.lineEditMobilePhone.setText(digits)
                self.lineEditMobilePhone.blockSignals(False)

        self.lineEditMobilePhone.textChanged.connect(on_phone_edit)
        self.lineEditMobilePhone.setPlaceholderText("Введите 9 цифр (29XXXXXXX)")

    def setup_ui_mode(self):
        """Настройка UI в зависимости от режима"""
        # Загружаем подразделения в комбобокс
        self.load_divisions_combo()

        if self.read_only:
            self.setWindowTitle("Просмотр сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Просмотр сотрудника")
            if self.employee_data:
                self._load_employee_personal_data()
            return

        if self.is_edit_mode:
            self.setWindowTitle("Редактирование сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование сотрудника")
            self._load_employee_personal_data()
            if hasattr(self, 'comboBoxRole'):
                self.comboBoxRole.setEnabled(True)
            self.btnAddDivision.setVisible(True)
            self.btnAddDepartment.setVisible(True)

        elif self.is_registration_mode:
            self.setWindowTitle("Регистрация нового сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Регистрация нового сотрудника")
            if hasattr(self, 'comboBoxRole'):
                self.comboBoxRole.setCurrentText("Пользователь")
                self.comboBoxRole.setEnabled(False)
            self.btnAddDivision.setVisible(False)
            self.btnAddDepartment.setVisible(False)
            self.btnSave.setText("Отправить заявку администратору")

        else:
            self.setWindowTitle("Добавление нового сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление нового сотрудника")
            if hasattr(self, 'comboBoxRole'):
                self.comboBoxRole.setEnabled(True)
            self.btnAddDivision.setVisible(True)
            self.btnAddDepartment.setVisible(True)

    def _load_employee_personal_data(self):
        """Загружает только личные данные сотрудника (без отделов)"""
        if not self.employee_data:
            return

        self.lineEditLastName.setText(self.employee_data.get("last_name", ""))
        self.lineEditFirstName.setText(self.employee_data.get("first_name", ""))
        self.lineEditMiddleName.setText(self.employee_data.get("middle_name", ""))

        birth_date = self.employee_data.get("birth_date")
        if birth_date:
            if isinstance(birth_date, date):
                self.dateEditBirthDate.setDate(QDate(birth_date.year, birth_date.month, birth_date.day))
            elif isinstance(birth_date, str):
                try:
                    birth_parts = birth_date.split('-')
                    if len(birth_parts) == 3:
                        self.dateEditBirthDate.setDate(
                            QDate(int(birth_parts[0]), int(birth_parts[1]), int(birth_parts[2])))
                except:
                    pass

        self.lineEditPosition.setText(self.employee_data.get("position", ""))

        if not self.is_registration_mode and hasattr(self, 'comboBoxRole'):
            rights = self.employee_data.get("rights", "user")
            role_map = {
                "user": "Пользователь",
                "admin": "Администратор",
                "superadmin": "Суперадминистратор"
            }
            role_text = role_map.get(rights, "Пользователь")
            self.comboBoxRole.setCurrentText(role_text)

        phone = self.employee_data.get("phone_number", "")
        if phone.startswith("375"):
            phone = phone[3:]
        self.lineEditMobilePhone.setText(phone)

        self.lineEditWorkPhone.setText(self.employee_data.get("work_number", ""))
        self.lineEditEmail.setText(self.employee_data.get("email", ""))

    def load_divisions_combo(self):
        """Загрузка подразделений в комбобокс"""
        self.comboBoxDivision.clear()
        self.comboBoxDivision.addItem("Выберите подразделение", None)

        for division in self.all_divisions:
            self.comboBoxDivision.addItem(division.get("name", "Без названия"), division.get("id"))

    def on_division_changed(self, index):
        """Обработчик изменения выбранного подразделения"""
        if index <= 0:
            self.comboBoxDepartment.clear()
            self.comboBoxDepartment.addItem("Выберите отдел", None)
            return

        division_id = self.comboBoxDivision.currentData()
        self._load_departments_for_division(division_id)

        # После загрузки отделов применяем фильтрацию для начальника
        if self.allowed_department_ids:
            QTimer.singleShot(50, self._filter_departments_by_allowed)

    def _load_departments_for_division(self, division_id):
        """Загружает отделы для указанного подразделения"""
        self.comboBoxDepartment.clear()
        self.comboBoxDepartment.addItem("Выберите отдел", None)

        if division_id in self.departments_by_division:
            for department in self.departments_by_division[division_id]:
                self.comboBoxDepartment.addItem(department.get("name", "Без названия"), department.get("id"))

    def _apply_department_restriction(self):
        """
        Применяет ограничение по отделам для начальника.
        Если начальник управляет только одним отделом - блокируем выбор.
        Если несколькими - оставляем выбор только между ними.
        """
        if not self.allowed_department_ids:
            return

        # Проверяем, загружены ли комбобоксы
        if hasattr(self, 'comboBoxDepartment') and self.comboBoxDepartment.count() <= 1:
            # Данные ещё не загружены, повторяем попытку
            QTimer.singleShot(100, self._apply_department_restriction)
            return

        # Если только один отдел - блокируем полностью
        if len(self.allowed_department_ids) == 1:
            dept_id = self.allowed_department_ids[0]
            # Устанавливаем этот отдел и блокируем
            if hasattr(self, 'comboBoxDepartment'):
                for i in range(self.comboBoxDepartment.count()):
                    if self.comboBoxDepartment.itemData(i) == dept_id:
                        self.comboBoxDepartment.setCurrentIndex(i)
                        self.comboBoxDepartment.setEnabled(False)
                        break
            if hasattr(self, 'comboBoxDivision'):
                self.comboBoxDivision.setEnabled(False)
            print(f"🔒 Начальник одного отдела: отдел {dept_id} заблокирован")
        else:
            # Несколько отделов - фильтруем список отделов
            print(f"🔓 Начальник нескольких отделов: доступны {self.allowed_department_ids}")
            self._filter_departments_by_allowed()

    def add_division(self):
        """Открытие диалога добавления подразделения"""
        if self.read_only:
            return

        from windows.settings.divisions.division_dialog import DivisionDialog

        dialog = DivisionDialog(parent=self, division_data=None)
        if hasattr(dialog, 'division_saved'):
            dialog.division_saved.connect(self.on_division_saved)
        dialog.exec()

    def on_division_saved(self, division_data):
        """Обработка сохранения подразделения"""
        self.load_data_from_service()
        self.load_divisions_combo()

        new_id = division_data.get('id')
        for i in range(self.comboBoxDivision.count()):
            if self.comboBoxDivision.itemData(i) == new_id:
                self.comboBoxDivision.setCurrentIndex(i)
                break

        QMessageBox.information(self, "Успешно", f"Подразделение добавлено")

    def add_department(self):
        """Открытие диалога добавления отдела"""
        if self.read_only:
            return

        from windows.settings.departments.department_dialog import DepartmentDialog

        division_id = self.comboBoxDivision.currentData()
        if not division_id:
            QMessageBox.warning(self, "Внимание", "Сначала выберите подразделение!")
            return

        dialog = DepartmentDialog(parent=self, department_data=None)
        if hasattr(dialog, 'department_saved'):
            dialog.department_saved.connect(self.on_department_saved)
        dialog.exec()

    def on_department_saved(self, department_data):
        """Обработка сохранения отдела"""
        self.load_data_from_service()
        division_id = self.comboBoxDivision.currentData()
        self.on_division_changed(self.comboBoxDivision.currentIndex())

        new_id = department_data.get('id')
        for i in range(self.comboBoxDepartment.count()):
            if self.comboBoxDepartment.itemData(i) == new_id:
                self.comboBoxDepartment.setCurrentIndex(i)
                break

        QMessageBox.information(self, "Успешно", f"Отдел добавлен")

    def get_employee_data(self):
        """Получение данных из формы через сервис"""
        rights_map = {
            "Пользователь": "user",
            "Администратор": "admin",
            "Суперадминистратор": "superadmin"
        }

        if self.is_registration_mode:
            rights = "user"
            generated_password = self.employee_service.generate_registration_password() if self.employee_service else "temp123"
        else:
            role_text = self.comboBoxRole.currentText() if hasattr(self, 'comboBoxRole') else "Пользователь"
            rights = rights_map.get(role_text, "user")
            generated_password = None

        division_id = self.comboBoxDivision.currentData()
        department_id = self.comboBoxDepartment.currentData()

        birth_date = self.dateEditBirthDate.date().toPyDate()
        birth_date_str = birth_date.isoformat() if birth_date else None

        phone_digits = ''.join([c for c in self.lineEditMobilePhone.text().strip() if c.isdigit()])
        full_phone = f"375{phone_digits}" if phone_digits else ""

        result = {
            "id": self.employee_data.get('id') if self.employee_data else None,
            "last_name": self.lineEditLastName.text().strip(),
            "first_name": self.lineEditFirstName.text().strip(),
            "middle_name": self.lineEditMiddleName.text().strip() or None,
            "birth_date": birth_date_str,
            "division_id": division_id,
            "department_id": department_id,
            "position": self.lineEditPosition.text().strip(),
            "rights": rights,
            "phone_number": full_phone,
            "work_number": self.lineEditWorkPhone.text().strip() or None,
            "email": self.lineEditEmail.text().strip() or None,
        }

        if generated_password:
            result["generated_password"] = generated_password

        return result

    def save_employee(self):
        """Сохранение сотрудника"""
        if self.read_only:
            QMessageBox.information(self, "Информация", "В режиме просмотра редактирование недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        employee_data = self.get_employee_data()

        # Валидация через сервис
        is_valid, error_msg = self.employee_service.validate_employee_form(employee_data)

        if not is_valid:
            QMessageBox.warning(self, "Внимание", error_msg)
            return

        # Сохраняем через сервис
        result = self.employee_service.save_employee_from_dialog(employee_data)

        if result:
            self.employee_saved.emit(result)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить сотрудника")

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями"""
        self.fields = [
            self.lineEditLastName,
            self.lineEditFirstName,
            self.lineEditMiddleName,
            self.dateEditBirthDate,
            self.comboBoxDivision,
            self.comboBoxDepartment,
            self.lineEditPosition,
        ]

        if hasattr(self, 'comboBoxRole'):
            self.fields.append(self.comboBoxRole)

        self.fields.extend([
            self.lineEditMobilePhone,
            self.lineEditWorkPhone,
            self.lineEditEmail,
        ])

        for widget in self.fields:
            widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            try:
                current_index = self.fields.index(obj)
            except ValueError:
                return super().eventFilter(obj, event)

            if key == QtCore.Qt.Key.Key_Down:
                next_index = (current_index + 1) % len(self.fields)
                self.fields[next_index].setFocus()
                return True
            elif key == QtCore.Qt.Key.Key_Up:
                prev_index = (current_index - 1) % len(self.fields)
                self.fields[prev_index].setFocus()
                return True

        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        event.accept()