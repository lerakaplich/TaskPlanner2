from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QPushButton, QScrollArea, QComboBox, QHBoxLayout, QLabel, \
    QFrame
from PyQt6.QtCore import Qt, pyqtSignal
import os

from windows.settings.departments.department_card import DepartmentCard
from windows.settings.divisions.division_card import DivisionCard
from windows.settings.employees.employee_card import EmployeeCard
from windows.settings.tags.tag_card import TagCard


class SettingsPage(QWidget):
    """Страница настроек с вкладками и карточками"""

    # Сигналы для уведомления о действиях
    item_added = pyqtSignal(str, dict)
    item_edited = pyqtSignal(str, dict)
    item_deleted = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "settings", "settings_page.ui"
        )
        uic.loadUi(ui_path, self)

        # Хранение данных
        self.all_employees = []
        self.all_departments = []
        self.all_divisions = []
        self.all_tags = []

        # Текущие фильтры и сортировка
        self.current_dept_filter = None
        self.current_div_filter = None
        self.current_sort_field = None
        self.current_sort_order = Qt.SortOrder.AscendingOrder

        # Настройка интерфейса
        self.setup_ui()

        # Подключение сигналов
        self.connect_signals()

        # Загрузка тестовых данных
        self.load_sample_data()

    def setup_ui(self):
        """Дополнительная настройка интерфейса"""
        self.titleLabel.setText("Настройки системы")

        # Добавляем фильтры и сортировку на вкладку сотрудников
        self.setup_employees_filters()

        # Добавляем сортировку на остальные вкладки
        self.setup_sorting_controls()

        # Получаем scrollArea для каждой вкладки
        self.setup_scroll_areas()

    def setup_employees_filters(self):
        """Настройка фильтров для вкладки сотрудников"""
        # Создаем фрейм для фильтров
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_frame.setMaximumHeight(80)
        filter_frame.setStyleSheet("""
            QFrame#filterFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
                padding: 10px;
            }
        """)

        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)
        filter_layout.setSpacing(15)

        # Заголовок фильтров
        filter_label = QLabel("Фильтры:")
        filter_label.setStyleSheet("font-weight: bold; color: #1B232A;")
        filter_layout.addWidget(filter_label)

        # Комбобокс для отделов
        self.dept_filter = QComboBox()
        self.dept_filter.setMinimumWidth(200)
        self.dept_filter.setPlaceholderText("Все отделы")
        filter_layout.addWidget(QLabel("Отдел:"))
        filter_layout.addWidget(self.dept_filter)

        # Комбобокс для подразделений
        self.div_filter = QComboBox()
        self.div_filter.setMinimumWidth(200)
        self.div_filter.setPlaceholderText("Все подразделения")
        filter_layout.addWidget(QLabel("Подразделение:"))
        filter_layout.addWidget(self.div_filter)

        # Кнопка сброса фильтров
        reset_btn = QPushButton("Сбросить")
        reset_btn.setObjectName("btnReset")
        reset_btn.setMinimumWidth(100)
        reset_btn.setMaximumHeight(35)
        reset_btn.setStyleSheet("""
            QPushButton#btnReset {
                background-color: #1B232A;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QPushButton#btnReset:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        filter_layout.addWidget(reset_btn)
        filter_layout.addStretch()

        # Добавляем фильтры в toolsFrameEmployees
        if hasattr(self, 'toolsFrameEmployees'):
            # Сохраняем старый layout и кнопку добавления
            old_layout = self.toolsFrameEmployees.layout()
            add_btn = None
            if old_layout:
                # Ищем кнопку добавления
                for i in range(old_layout.count()):
                    item = old_layout.itemAt(i)
                    if item.widget() and item.widget().objectName() == "btnAddEmployee":
                        add_btn = item.widget()
                        break

            # Очищаем старый layout
            if old_layout:
                self.clear_layout(old_layout)

            # Создаем новый layout
            new_layout = QHBoxLayout(self.toolsFrameEmployees)
            new_layout.setContentsMargins(10, 10, 10, 10)

            # Добавляем фильтры
            new_layout.addWidget(filter_frame)

            # Добавляем кнопку добавления
            if add_btn:
                new_layout.addWidget(add_btn)
            else:
                # Создаем новую кнопку
                add_btn = QPushButton("+ Добавить сотрудника")
                add_btn.setObjectName("btnAddEmployee")
                add_btn.setMinimumSize(160, 41)
                add_btn.clicked.connect(lambda: self.add_item(1))
                new_layout.addWidget(add_btn)

        # Подключаем сигналы фильтров
        self.dept_filter.currentIndexChanged.connect(self.apply_filters)
        self.div_filter.currentIndexChanged.connect(self.apply_filters)
        reset_btn.clicked.connect(self.reset_filters)

    def clear_layout(self, layout):
        """Очистка layout от виджетов"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def setup_sorting_controls(self):
        """Настройка элементов сортировки для всех вкладок"""
        # Словарь с настройками сортировки для каждой вкладки
        sort_configs = {
            'tabEmployees': {
                'frame': 'toolsFrameEmployees',
                'fields': [
                    ('name', 'По имени'),
                    ('department', 'По отделу'),
                    ('position', 'По должности')
                ]
            },
            'tabDepartments': {
                'frame': 'toolsFrameDepartments',
                'fields': [
                    ('name', 'По названию'),
                    ('number', 'По номеру'),
                    ('division', 'По подразделению')
                ]
            },
            'tabSubdivisions': {
                'frame': 'toolsFrameSubdivisions',
                'fields': [
                    ('name', 'По названию'),
                    ('number', 'По номеру'),
                    ('workshop_code', 'По коду цеха')
                ]
            },
            'tabHashtags': {
                'frame': 'toolsFrameHashtags',
                'fields': [
                    ('name', 'По названию'),
                    ('count', 'По использованию')
                ]
            }
        }

        for tab_name, config in sort_configs.items():
            if hasattr(self, tab_name):
                tab = getattr(self, tab_name)
                if hasattr(tab, config['frame']):
                    frame = getattr(tab, config['frame'])
                    self.add_sorting_to_frame(frame, tab_name, config['fields'])

    def add_sorting_to_frame(self, frame, tab_name, sort_fields):
        """Добавляет элементы сортировки в указанный фрейм"""
        # Получаем существующий layout
        layout = frame.layout()
        if not layout:
            return

        # Создаем контейнер для сортировки
        sort_widget = QWidget()
        sort_widget.setMaximumHeight(40)
        sort_layout = QHBoxLayout(sort_widget)
        sort_layout.setContentsMargins(0, 0, 10, 0)
        sort_layout.setSpacing(10)

        # Заголовок сортировки
        sort_label = QLabel("Сортировка:")
        sort_label.setStyleSheet("font-weight: bold; color: #1B232A;")
        sort_layout.addWidget(sort_label)

        # Комбобокс выбора поля
        sort_combo = QComboBox()
        sort_combo.setMinimumWidth(150)
        for field_value, field_name in sort_fields:
            sort_combo.addItem(field_name, field_value)

        # Сохраняем комбобокс как атрибут
        setattr(self, f"{tab_name}_sort_combo", sort_combo)
        sort_layout.addWidget(sort_combo)

        # Кнопка порядка сортировки
        order_btn = QPushButton("↑ По возрастанию")
        order_btn.setCheckable(True)
        order_btn.setMinimumWidth(120)
        order_btn.setMaximumHeight(30)
        order_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #ccab6e;
                color: white;
                border-color: #ccab6e;
            }
        """)

        # Сохраняем кнопку как атрибут
        setattr(self, f"{tab_name}_order_btn", order_btn)
        sort_layout.addWidget(order_btn)

        # Добавляем в начало layout
        layout.insertWidget(0, sort_widget)

        # Подключаем сигналы
        tab_index = {
            'tabEmployees': 1,
            'tabDepartments': 2,
            'tabSubdivisions': 3,
            'tabHashtags': 0
        }.get(tab_name, 0)

        sort_combo.currentIndexChanged.connect(
            lambda idx, t=tab_index: self.apply_sorting(t)
        )
        order_btn.toggled.connect(
            lambda checked, t=tab_index: self.on_sort_order_changed(checked, t)
        )

    def setup_scroll_areas(self):
        """Настройка scrollArea для каждой вкладки"""
        # Вкладка Хэштеги
        if hasattr(self, 'scrollAreaHashtags'):
            self.scroll_area_hashtags = self.scrollAreaHashtags
            self.hashtags_container = QWidget()
            self.hashtags_layout = QVBoxLayout(self.hashtags_container)
            self.hashtags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.hashtags_layout.setSpacing(10)
            self.scroll_area_hashtags.setWidget(self.hashtags_container)
            self.scroll_area_hashtags.setWidgetResizable(True)

        # Вкладка Сотрудники
        if hasattr(self, 'scrollAreaEmployees'):
            self.scroll_area_employees = self.scrollAreaEmployees
            self.employees_container = QWidget()
            self.employees_layout = QVBoxLayout(self.employees_container)
            self.employees_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.employees_layout.setSpacing(10)
            self.scroll_area_employees.setWidget(self.employees_container)
            self.scroll_area_employees.setWidgetResizable(True)

        # Вкладка Отделы
        if hasattr(self, 'scrollAreaDepartments'):
            self.scroll_area_departments = self.scrollAreaDepartments
            self.departments_container = QWidget()
            self.departments_layout = QVBoxLayout(self.departments_container)
            self.departments_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.departments_layout.setSpacing(10)
            self.scroll_area_departments.setWidget(self.departments_container)
            self.scroll_area_departments.setWidgetResizable(True)

        # Вкладка Подразделения
        if hasattr(self, 'scrollAreaSubdivisions'):
            self.scroll_area_subdivisions = self.scrollAreaSubdivisions
            self.subdivisions_container = QWidget()
            self.subdivisions_layout = QVBoxLayout(self.subdivisions_container)
            self.subdivisions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.subdivisions_layout.setSpacing(10)
            self.scroll_area_subdivisions.setWidget(self.subdivisions_container)
            self.scroll_area_subdivisions.setWidgetResizable(True)

    def connect_signals(self):
        """Подключение сигналов к слотам"""
        # Кнопки добавления для каждой вкладки
        if hasattr(self, 'btnAddHashtag'):
            self.btnAddHashtag.clicked.connect(lambda: self.add_item(0))
        if hasattr(self, 'btnAddEmployee'):
            self.btnAddEmployee.clicked.connect(lambda: self.add_item(1))
        if hasattr(self, 'btnAddDepartment'):
            self.btnAddDepartment.clicked.connect(lambda: self.add_item(2))
        if hasattr(self, 'btnAddSubdivision'):
            self.btnAddSubdivision.clicked.connect(lambda: self.add_item(3))

        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def add_item(self, tab_index):
        """Добавление элемента в зависимости от вкладки"""
        tab_names = ["Хэштеги", "Сотрудники", "Отделы", "Подразделения"]
        display_name = tab_names[tab_index] if tab_index < len(tab_names) else "Неизвестно"

        QMessageBox.information(self, "Добавление",
                                f"Здесь будет форма добавления нового элемента в {display_name}")

    def get_current_tab_name(self):
        """Получить название текущей вкладки"""
        if not hasattr(self, 'tabWidget'):
            return "unknown"
        index = self.tabWidget.currentIndex()
        tab_names = ["hashtags", "employees", "departments", "subdivisions"]
        return tab_names[index] if index < len(tab_names) else "unknown"

    def get_current_tab_display_name(self):
        """Получить отображаемое название текущей вкладки"""
        if not hasattr(self, 'tabWidget'):
            return "Неизвестно"
        index = self.tabWidget.currentIndex()
        tab_names = ["Хэштеги", "Сотрудники", "Отделы", "Подразделения"]
        return tab_names[index] if index < len(tab_names) else "Неизвестно"

    def get_current_layout(self):
        """Получить layout текущей вкладки"""
        index = self.tabWidget.currentIndex() if hasattr(self, 'tabWidget') else 0
        layouts = [
            self.hashtags_layout,
            self.employees_layout,
            self.departments_layout,
            self.subdivisions_layout
        ]
        return layouts[index] if index < len(layouts) else None

    def apply_filters(self):
        """Применение фильтров к сотрудникам"""
        print("Применение фильтров...")  # Отладка

        dept_id = self.dept_filter.currentData()
        div_id = self.div_filter.currentData()

        print(f"Фильтр отдела: {dept_id}, фильтр подразделения: {div_id}")  # Отладка

        # Применяем фильтры к данным
        filtered_employees = self.all_employees.copy()
        print(f"Всего сотрудников: {len(filtered_employees)}")  # Отладка

        if dept_id is not None:
            filtered_employees = [e for e in filtered_employees
                                  if e.get('department_id') == dept_id]
            print(f"После фильтра по отделу {dept_id}: {len(filtered_employees)}")  # Отладка

        if div_id is not None:
            filtered_employees = [e for e in filtered_employees
                                  if e.get('division_id') == div_id]
            print(f"После фильтра по подразделению {div_id}: {len(filtered_employees)}")  # Отладка

        # Отображаем отфильтрованных сотрудников
        self.display_filtered_employees(filtered_employees)

    def reset_filters(self):
        """Сброс всех фильтров"""
        print("Сброс фильтров...")  # Отладка

        # Блокируем сигналы, чтобы не вызвать множественную фильтрацию
        self.dept_filter.blockSignals(True)
        self.div_filter.blockSignals(True)

        self.dept_filter.setCurrentIndex(0)
        self.div_filter.setCurrentIndex(0)

        self.dept_filter.blockSignals(False)
        self.div_filter.blockSignals(False)

        # Отображаем всех сотрудников
        self.display_filtered_employees(self.all_employees)

    def apply_sorting(self, tab_index):
        """Применение сортировки"""
        print(f"Применение сортировки для вкладки {tab_index}")  # Отладка

        # Получаем комбобокс для соответствующей вкладки
        tab_names = ['tabHashtags', 'tabEmployees', 'tabDepartments', 'tabSubdivisions']
        if tab_index >= len(tab_names):
            return

        tab_name = tab_names[tab_index]
        sort_combo = getattr(self, f"{tab_name}_sort_combo", None)
        order_btn = getattr(self, f"{tab_name}_order_btn", None)

        if not sort_combo or not order_btn:
            print(f"Не найдены элементы сортировки для {tab_name}")  # Отладка
            return

        field = sort_combo.currentData()
        order = Qt.SortOrder.AscendingOrder if not order_btn.isChecked() else Qt.SortOrder.DescendingOrder

        print(f"Поле сортировки: {field}, порядок: {order}")  # Отладка

        # Получаем данные для сортировки
        if tab_index == 0:  # Хэштеги
            data = self.all_tags
            layout = self.hashtags_layout
            card_class = TagCard
        elif tab_index == 1:  # Сотрудники
            # Для сотрудников используем текущие отфильтрованные данные
            data = self.get_current_filtered_employees()
            layout = self.employees_layout
            card_class = EmployeeCard
        elif tab_index == 2:  # Отделы
            data = self.all_departments
            layout = self.departments_layout
            card_class = DepartmentCard
        elif tab_index == 3:  # Подразделения
            data = self.all_divisions
            layout = self.subdivisions_layout
            card_class = DivisionCard
        else:
            return

        # Сортируем данные
        sorted_data = self.sort_data(data, field, order)
        print(f"Отсортировано элементов: {len(sorted_data)}")  # Отладка

        # Отображаем отсортированные данные
        self.clear_container(layout)
        for item in sorted_data:
            card = card_class(item)
            self.connect_card_signals(card, item)
            layout.addWidget(card)

    def get_current_filtered_employees(self):
        """Получить текущий отфильтрованный список сотрудников"""
        dept_id = self.dept_filter.currentData()
        div_id = self.div_filter.currentData()

        filtered_employees = self.all_employees.copy()

        if dept_id is not None:
            filtered_employees = [e for e in filtered_employees
                                  if e.get('department_id') == dept_id]

        if div_id is not None:
            filtered_employees = [e for e in filtered_employees
                                  if e.get('division_id') == div_id]

        return filtered_employees

    def sort_data(self, data, field, order):
        """Сортировка данных по указанному полю"""
        if not field:
            return data

        def get_sort_key(item):
            if field == 'name':
                if 'last_name' in item:  # Для сотрудников
                    return f"{item.get('last_name', '')} {item.get('first_name', '')} {item.get('middle_name', '')}"
                return item.get('name', '')
            elif field == 'department':
                dept = item.get('department', '')
                if isinstance(dept, dict):
                    return dept.get('name', '')
                return str(dept)
            elif field == 'division':
                div = item.get('division', '')
                if isinstance(div, dict):
                    return div.get('name', '')
                return str(div)
            elif field == 'position':
                return item.get('position', '')
            elif field == 'number':
                # Сортируем числа как числа, а не как строки
                try:
                    return int(item.get('number', 0))
                except (ValueError, TypeError):
                    return str(item.get('number', ''))
            elif field == 'workshop_code':
                return item.get('workshop_code', '')
            elif field == 'count':
                return item.get('count', 0)
            else:
                return str(item.get(field, ''))

        sorted_data = sorted(data, key=get_sort_key)
        if order == Qt.SortOrder.DescendingOrder:
            sorted_data.reverse()

        return sorted_data

    def on_sort_order_changed(self, checked, tab_index):
        """Обработчик изменения порядка сортировки"""
        tab_names = ['Hashtags', 'Employees', 'Departments', 'Subdivisions']
        btn = getattr(self, f"tab{tab_names[tab_index]}_order_btn")
        btn.setText("↓ По убыванию" if checked else "↑ По возрастанию")
        self.apply_sorting(tab_index)

    def display_filtered_employees(self, employees):
        """Отображение отфильтрованных сотрудников"""
        print(f"Отображение сотрудников: {len(employees)}")  # Отладка

        self.clear_container(self.employees_layout)
        for emp in employees:
            card = EmployeeCard(emp)
            self.connect_card_signals(card, emp)
            self.employees_layout.addWidget(card)

    def connect_card_signals(self, card, item_data):
        """Подключение сигналов карточки"""
        item_type = None
        if isinstance(card, TagCard):
            item_type = "tag"
        elif isinstance(card, EmployeeCard):
            item_type = "employee"
        elif isinstance(card, DepartmentCard):
            item_type = "department"
        elif isinstance(card, DivisionCard):
            item_type = "division"

        if item_type:
            card.edit_clicked.connect(lambda id, t=item_type: self.on_edit_clicked(t, id))
            card.delete_clicked.connect(lambda id, t=item_type: self.on_delete_clicked(t, id))

    def on_tab_changed(self, index):
        """Обработчик смены вкладки"""
        display_name = self.get_current_tab_display_name()
        print(f"Переключено на вкладку: {display_name}")

        # Применяем сортировку при переключении на вкладку
        self.apply_sorting(index)

    def load_sample_data(self):
        """Загрузка тестовых данных"""
        print("Загрузка тестовых данных...")  # Отладка

        # Загружаем теги
        self.all_tags = [
            {"id": 1, "name": "проект", "color": "#ccab6e", "count": 15},
            {"id": 2, "name": "срочно", "color": "#ff6b6b", "count": 8},
            {"id": 3, "name": "важно", "color": "#4ecdc4", "count": 12},
            {"id": 4, "name": "обучение", "color": "#45b7d1", "count": 5},
            {"id": 5, "name": "отчет", "color": "#96ceb4", "count": 10},
        ]

        # Загружаем отделы
        self.all_departments = [
            {
                "id": 1,
                "number": 101,
                "name": "IT отдел",
                "boss": "Иванов И.И.",
                "phone_number": "+375 (17) 123-45-67",
                "division": "Северное подразделение"
            },
            {
                "id": 2,
                "number": 102,
                "name": "HR отдел",
                "boss": "Петрова А.С.",
                "division": "Центральное подразделение"
            },
            {
                "id": 3,
                "number": 103,
                "name": "Бухгалтерия",
                "bosses": ["Сидоров П.П.", "Козлова Е.В."],
                "phone_number": "+375 (17) 234-56-78",
                "division": "Южное подразделение"
            },
        ]

        # Загружаем подразделения
        self.all_divisions = [
            {
                "id": 1,
                "number": 1,
                "name": "Северное подразделение",
                "boss": "Козлов А.А.",
                "phone_number": "+375 (17) 111-22-33",
                "workshop_code": "С-001"
            },
            {
                "id": 2,
                "number": 2,
                "name": "Южное подразделение",
                "boss": "Морозов В.В.",
                "phone_number": "+375 (17) 444-55-66",
                "workshop_code": "Ю-002"
            },
            {
                "id": 3,
                "number": 3,
                "name": "Центральное подразделение",
                "boss": "Весенний Г.Г.",
                "workshop_code": "Ц-003"
            },
        ]

        # Загружаем сотрудников
        self.all_employees = [
            {
                "id": 1,
                "last_name": "Иванов",
                "first_name": "Иван",
                "middle_name": "Иванович",
                "position": "Ведущий разработчик",
                "department": self.all_departments[0],
                "department_id": 1,
                "division": self.all_divisions[0],
                "division_id": 1,
                "phone_number": "+375 (29) 123-45-67",
                "email": "ivanov@company.com",
                "rights": "admin"
            },
            {
                "id": 2,
                "last_name": "Петрова",
                "first_name": "Анна",
                "middle_name": "Сергеевна",
                "position": "HR-менеджер",
                "department": self.all_departments[1],
                "department_id": 2,
                "division": self.all_divisions[2],
                "division_id": 3,
                "phone_number": "+375 (33) 234-56-78",
                "email": "petrova@company.com",
                "rights": "user"
            },
            {
                "id": 3,
                "last_name": "Сидоров",
                "first_name": "Петр",
                "middle_name": "Петрович",
                "position": "Системный администратор",
                "department": self.all_departments[0],
                "department_id": 1,
                "division": self.all_divisions[1],
                "division_id": 2,
                "phone_number": "+375 (29) 345-67-89",
                "rights": "superadmin"
            },
            {
                "id": 4,
                "last_name": "Козлова",
                "first_name": "Елена",
                "middle_name": "Владимировна",
                "position": "Бухгалтер",
                "department": self.all_departments[2],
                "department_id": 3,
                "division": self.all_divisions[0],
                "division_id": 1,
                "phone_number": "+375 (29) 456-78-90",
                "email": "kozlova@company.com",
                "rights": "user"
            },
            {
                "id": 5,
                "last_name": "Морозов",
                "first_name": "Дмитрий",
                "middle_name": "Александрович",
                "position": "Начальник отдела",
                "department": self.all_departments[0],
                "department_id": 1,
                "division": self.all_divisions[2],
                "division_id": 3,
                "phone_number": "+375 (33) 567-89-01",
                "email": "morozov@company.com",
                "rights": "admin"
            }
        ]

        # Заполняем комбобоксы фильтров
        self.dept_filter.blockSignals(True)
        self.dept_filter.clear()
        self.dept_filter.addItem("Все отделы", None)
        for dept in self.all_departments:
            self.dept_filter.addItem(dept['name'], dept['id'])
        self.dept_filter.blockSignals(False)

        self.div_filter.blockSignals(True)
        self.div_filter.clear()
        self.div_filter.addItem("Все подразделения", None)
        for div in self.all_divisions:
            self.div_filter.addItem(div['name'], div['id'])
        self.div_filter.blockSignals(False)

        print(f"Загружено отделов: {len(self.all_departments)}")  # Отладка
        print(f"Загружено подразделений: {len(self.all_divisions)}")  # Отладка
        print(f"Загружено сотрудников: {len(self.all_employees)}")  # Отладка

        # Отображаем все данные
        self.refresh_all_tabs()

    def refresh_all_tabs(self):
        """Обновление всех вкладок"""
        print("Обновление всех вкладок...")  # Отладка

        # Очищаем контейнеры
        self.clear_container(self.hashtags_layout)
        self.clear_container(self.employees_layout)
        self.clear_container(self.departments_layout)
        self.clear_container(self.subdivisions_layout)

        # Отображаем теги
        for tag in self.all_tags:
            card = TagCard(tag)
            self.connect_card_signals(card, tag)
            self.hashtags_layout.addWidget(card)

        # Отображаем сотрудников
        for emp in self.all_employees:
            card = EmployeeCard(emp)
            self.connect_card_signals(card, emp)
            self.employees_layout.addWidget(card)

        # Отображаем отделы
        for dept in self.all_departments:
            card = DepartmentCard(dept)
            self.connect_card_signals(card, dept)
            self.departments_layout.addWidget(card)

        # Отображаем подразделения
        for div in self.all_divisions:
            card = DivisionCard(div)
            self.connect_card_signals(card, div)
            self.subdivisions_layout.addWidget(card)

    def clear_container(self, layout):
        """Очистка контейнера от карточек"""
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_edit_clicked(self, item_type, item_id):
        """Обработчик клика по кнопке редактирования"""
        QMessageBox.information(self, "Редактирование",
                                f"Редактирование {item_type} с ID={item_id} (заглушка)")

    def on_delete_clicked(self, item_type, item_id):
        """Обработчик клика по кнопке удаления"""
        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить {item_type}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Удаление", f"{item_type} удален")
            self.item_deleted.emit(item_type, item_id)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow
    import sys

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Настройки")
    window.setGeometry(100, 100, 1487, 800)

    settings_page = SettingsPage()
    window.setCentralWidget(settings_page)

    window.show()
    sys.exit(app.exec())