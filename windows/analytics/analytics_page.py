# windows/analytics/analytics_page.py

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QScrollArea,
    QVBoxLayout, QLabel, QFrame, QSizePolicy, QMessageBox, QComboBox, QHBoxLayout
)

from services.analytics_service.analytics_service import AnalyticsService
from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.theme.theme_card import ThemeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from windows.analytics.rating.rating_employee_card import RatingEmployeeCard


class AnalyticsPage(QWidget):
    """Страница аналитики - только отображение, логика в сервисе"""

    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        # Инициализируем сервис
        self.session = session
        self.service = AnalyticsService(session) if session else None

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "analytics", "analytics_page.ui"
        )

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._setup_ui_from_file()
        else:
            self._create_ui_programmatically()

        # Кэш для данных
        self._employees_raw_data = []  # Исходные данные сотрудников (без фильтрации)
        self._employees_data = []  # Отфильтрованные данные для отображения
        self._themes_data = []
        self._projects_data = []
        self._departments = []  # Список отделов для фильтра
        self._current_department_filter = "all"  # Текущий выбранный отдел для сотрудников
        self._current_rating_department_filter = "all"  # Текущий выбранный отдел для рейтинга
        self._current_period_filter = "all"  # Текущий выбранный период для рейтинга
        self.department_filter = None  # Ссылка на комбобокс фильтра (сотрудники)
        self.rating_department_filter = None  # Ссылка на комбобокс фильтра (рейтинг)
        self.period_filter = None  # Ссылка на комбобокс фильтра периода
        self._is_loading = False  # Флаг загрузки для предотвращения рекурсии
        self._departments_loaded = False  # Флаг загрузки отделов

        # Загружаем данные
        if self.service:
            self.load_all_data()
        else:
            self._show_placeholder()

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""
        # Настраиваем фильтры для сотрудников и рейтинга
        self._setup_employee_filters()
        self._setup_rating_filters()
        self._setup_period_filter()

        # Переупорядочиваем вкладки - делаем Рейтинг первой
        if hasattr(self, 'tabWidget'):
            # Получаем текущий порядок вкладок
            rating_widget = None
            employees_widget = None
            themes_widget = None
            projects_widget = None

            # Сохраняем существующие вкладки
            for i in range(self.tabWidget.count()):
                tab_text = self.tabWidget.tabText(i)
                if tab_text == "Рейтинг сотрудников":
                    rating_widget = self.tabWidget.widget(i)
                elif tab_text == "Сотрудники":
                    employees_widget = self.tabWidget.widget(i)
                elif tab_text == "Темы":
                    themes_widget = self.tabWidget.widget(i)
                elif tab_text == "Проекты":
                    projects_widget = self.tabWidget.widget(i)

            # Очищаем все вкладки
            self.tabWidget.clear()

            # Добавляем в нужном порядке: Рейтинг, Сотрудники, Темы, Проекты
            if rating_widget:
                self.tabWidget.addTab(rating_widget, "Рейтинг сотрудников")
            if employees_widget:
                self.tabWidget.addTab(employees_widget, "Сотрудники")
            if themes_widget:
                self.tabWidget.addTab(themes_widget, "Темы")
            if projects_widget:
                self.tabWidget.addTab(projects_widget, "Проекты")

            # Делаем Рейтинг активной вкладкой
            self.tabWidget.setCurrentIndex(0)
            print("✅ Вкладки переупорядочены: Рейтинг сотрудников теперь первая")

        # Для вкладки Рейтинг - настраиваем контейнер
        self._setup_rating_tab()

        # Для вкладки Сотрудники - используем существующие контейнеры из UI
        if hasattr(self, 'employeesContainer'):
            # Получаем существующий grid layout
            self.employees_grid = self.employeesContainer.layout()
            if self.employees_grid is None:
                # Если layout нет, создаем новый
                self.employees_grid = QGridLayout(self.employeesContainer)
                self.employees_grid.setHorizontalSpacing(15)
                self.employees_grid.setVerticalSpacing(15)
                self.employees_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.employeesContainer.setLayout(self.employees_grid)
            print("✅ Настроен employees_grid")
        else:
            print("❌ employeesContainer не найден в UI")
            # Создаем принудительно
            self._create_employees_container()

        # Для вкладки Темы - создаем контейнер принудительно
        self._setup_tab_container_force('themesTab', 'themesContainer', 'themesGrid')

        # Для вкладки Проекты - создаем контейнер принудительно
        self._setup_tab_container_force('projectsTab', 'projectsContainer', 'projectsGrid')

        # Настройка плейсхолдеров для фильтров
        self._setup_filters_placeholder()

    def _setup_filters_placeholder(self) -> None:
        """Настройка плейсхолдеров для фильтров"""
        if self.department_filter:
            self.department_filter.setEditable(True)
            self.department_filter.setEditText("Все отделы")
            line_edit = self.department_filter.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("Все отделы")
                line_edit.setReadOnly(False)
                line_edit.setSelection(0, 0)

        if self.rating_department_filter:
            self.rating_department_filter.setEditable(True)
            self.rating_department_filter.setEditText("Все отделы")
            line_edit = self.rating_department_filter.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("Все отделы")
                line_edit.setReadOnly(False)
                line_edit.setSelection(0, 0)

        if self.period_filter:
            self.period_filter.setEditable(True)
            self.period_filter.setEditText("Все время")
            line_edit = self.period_filter.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("Выберите период")
                line_edit.setReadOnly(False)
                line_edit.setSelection(0, 0)

    def _setup_employee_filters(self):
        """Настраивает фильтры для вкладки сотрудников"""
        if hasattr(self, 'departmentFilter_2'):
            self.department_filter = self.departmentFilter_2
            print("✅ Найден departmentFilter_2 в UI")

            self.department_filter.blockSignals(True)
            self.department_filter.clear()
            self.department_filter.addItem("Все отделы", "all")
            self.department_filter.setEditable(True)
            self.department_filter.currentTextChanged.connect(self._on_department_filter_changed)
            self.department_filter.blockSignals(False)

            print("✅ Настроен фильтр по отделам для сотрудников")
        else:
            print("❌ departmentFilter_2 не найден в UI")
            self.department_filter = None

    def _setup_rating_filters(self):
        """Настраивает фильтры для вкладки рейтинга сотрудников"""
        if hasattr(self, 'departmentFilter'):
            self.rating_department_filter = self.departmentFilter
            print("✅ Найден departmentFilter в UI для рейтинга")

            self.rating_department_filter.blockSignals(True)
            self.rating_department_filter.clear()
            self.rating_department_filter.addItem("Все отделы", "all")
            self.rating_department_filter.setEditable(True)
            self.rating_department_filter.currentTextChanged.connect(self._on_rating_department_filter_changed)
            self.rating_department_filter.blockSignals(False)

            print("✅ Настроен фильтр по отделам для рейтинга")
        else:
            print("❌ departmentFilter не найден в UI")
            self.rating_department_filter = None

    def _setup_period_filter(self):
        """Настраивает фильтр периода для рейтинга"""
        if hasattr(self, 'periodFilter'):
            self.period_filter = self.periodFilter
            print("✅ Найден periodFilter в UI")

            self.period_filter.blockSignals(True)
            self.period_filter.clear()

            # Добавляем варианты периодов
            self.period_filter.addItem("Все время", "all")
            self.period_filter.addItem("Текущий год", "year")
            self.period_filter.addItem("Текущий квартал", "quarter")
            self.period_filter.addItem("Текущий месяц", "month")
            self.period_filter.addItem("Последние 30 дней", "last_30_days")
            self.period_filter.addItem("Последние 90 дней", "last_90_days")

            self.period_filter.setEditable(True)
            self.period_filter.currentTextChanged.connect(self._on_period_filter_changed)
            self.period_filter.blockSignals(False)

            print("✅ Настроен фильтр периода для рейтинга")
        else:
            print("❌ periodFilter не найден в UI")
            self.period_filter = None

    def _get_date_range_for_period(self, period: str) -> tuple:
        """
        Возвращает начальную и конечную дату для выбранного периода.
        Returns: (start_date, end_date) или (None, None) для "all"
        """
        now = datetime.now()

        if period == "all":
            return None, None

        elif period == "year":
            start_date = datetime(now.year, 1, 1)
            end_date = now
            return start_date, end_date

        elif period == "quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime(now.year, start_month, 1)
            end_date = now
            return start_date, end_date

        elif period == "month":
            start_date = datetime(now.year, now.month, 1)
            end_date = now
            return start_date, end_date

        elif period == "last_30_days":
            start_date = now - timedelta(days=30)
            end_date = now
            return start_date, end_date

        elif period == "last_90_days":
            start_date = now - timedelta(days=90)
            end_date = now
            return start_date, end_date

        return None, None

    def _filter_employees_by_period(self, employees_data: List[Dict], period: str) -> List[Dict]:
        """
        Фильтрует данные сотрудников по периоду на основе дат завершения задач.
        Для каждого сотрудника пересчитывает статистику за указанный период.
        """
        if period == "all" or not employees_data:
            return employees_data

        start_date, end_date = self._get_date_range_for_period(period)
        if start_date is None:
            return employees_data

        print(f"📅 Фильтрация по периоду: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")

        # Получаем задачи сотрудников за период из сервиса
        try:
            # Получаем задачи за период из БД
            tasks_by_employee = self._get_tasks_for_period(start_date, end_date)

            # Обновляем статистику для каждого сотрудника
            filtered_employees = []
            for emp in employees_data:
                emp_id = emp.get("id")
                tasks_info = tasks_by_employee.get(emp_id, {"completed": 0, "total": 0, "overtime": 0})

                # Создаем копию данных сотрудника с обновленной статистикой
                emp_copy = emp.copy()
                completed = tasks_info["completed"]
                total = tasks_info["total"]

                emp_copy["completed_tasks"] = completed
                emp_copy["total_tasks"] = total

                # Пересчитываем КПД
                if total > 0:
                    kpd_percent = (completed / total) * 100
                else:
                    kpd_percent = 0

                emp_copy["kpd_percent"] = kpd_percent
                emp_copy["kpd"] = kpd_percent / 100 if kpd_percent > 0 else 0
                emp_copy["overtime_hours"] = tasks_info.get("overtime", 0)

                # Добавляем только сотрудников с задачами за период
                # (или всех, если нужно показывать и тех, у кого 0 задач)
                filtered_employees.append(emp_copy)

            return filtered_employees

        except Exception as e:
            print(f"❌ Ошибка фильтрации по периоду: {e}")
            return employees_data

    def _get_tasks_for_period(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Получает задачи сотрудников за указанный период.
        Возвращает словарь {employee_id: {"completed": int, "total": int, "overtime": float}}
        """
        if not self.service or not self.service.base:
            return {}

        try:
            from models.tasks import Task
            from models.employees import EmployeeNote

            tasks_session = self.service.base.session
            employees_session = self.service.base.employees_session

            # Получаем задачи, завершенные в указанный период
            tasks = tasks_session.query(Task).filter(
                Task.completed == True,
                Task.archived_at >= start_date,
                Task.archived_at <= end_date
            ).all()

            # Также получаем задачи, созданные в период (активные)
            active_tasks = tasks_session.query(Task).filter(
                Task.completed == False,
                Task.created_at >= start_date,
                Task.created_at <= end_date
            ).all()

            # Собираем статистику по сотрудникам
            result = {}

            # Обрабатываем завершенные задачи
            for task in tasks:
                if task.assigned_to:
                    emp_id = task.assigned_to
                    if emp_id not in result:
                        result[emp_id] = {"completed": 0, "total": 0, "overtime": 0}
                    result[emp_id]["completed"] += 1
                    result[emp_id]["total"] += 1

            # Обрабатываем активные задачи
            for task in active_tasks:
                if task.assigned_to:
                    emp_id = task.assigned_to
                    if emp_id not in result:
                        result[emp_id] = {"completed": 0, "total": 0, "overtime": 0}
                    result[emp_id]["total"] += 1

            # Получаем переработки за период
            overtimes = employees_session.query(EmployeeNote).filter(
                EmployeeNote.created_at >= start_date,
                EmployeeNote.created_at <= end_date
            ).all()

            for ot in overtimes:
                emp_id = ot.employee_id
                if emp_id not in result:
                    result[emp_id] = {"completed": 0, "total": 0, "overtime": 0}

                if ot.overtime_start and ot.overtime_end:
                    start = datetime.combine(datetime.today(), ot.overtime_start)
                    end = datetime.combine(datetime.today(), ot.overtime_end)
                    if end < start:
                        end = end.replace(day=end.day + 1)
                    hours = (end - start).total_seconds() / 3600
                    result[emp_id]["overtime"] += hours

            return result

        except Exception as e:
            print(f"❌ Ошибка получения задач за период: {e}")
            return {}

    def _load_departments(self):
        """Загружает список отделов из БД и заполняет оба фильтра"""
        print("🔍 _load_departments: начало загрузки...")

        if not self.service or not self.service.base:
            print("❌ Сервис или база не доступны")
            return

        try:
            from models.employees import Department

            employees_session = self.service.base.employees_session
            departments = employees_session.query(Department).order_by(Department.name).all()

            print(f"📊 Найдено отделов в БД: {len(departments)}")

            # Заполняем фильтр для сотрудников
            if self.department_filter:
                self.department_filter.blockSignals(True)
                self.department_filter.clear()
                self.department_filter.addItem("Все отделы", "all")
                for dept in departments:
                    self.department_filter.addItem(dept.name, f"dept_{dept.id}")
                self.department_filter.blockSignals(False)
                print(f"✅ Загружено отделов в фильтр сотрудников: {self.department_filter.count() - 1}")

            # Заполняем фильтр для рейтинга
            if self.rating_department_filter:
                self.rating_department_filter.blockSignals(True)
                self.rating_department_filter.clear()
                self.rating_department_filter.addItem("Все отделы", "all")
                for dept in departments:
                    self.rating_department_filter.addItem(dept.name, f"dept_{dept.id}")
                self.rating_department_filter.blockSignals(False)
                print(f"✅ Загружено отделов в фильтр рейтинга: {self.rating_department_filter.count() - 1}")

            self._departments = [{"id": dept.id, "name": dept.name} for dept in departments]
            self._departments_loaded = True

        except Exception as e:
            print(f"❌ Ошибка загрузки отделов: {e}")

    def _on_period_filter_changed(self, text: str) -> None:
        """Обработчик изменения фильтра периода для рейтинга"""
        if not hasattr(self, '_is_loading') or self._is_loading:
            return

        if not self.period_filter:
            return

        current_data = self.period_filter.currentData()
        if current_data:
            self._current_period_filter = current_data
        else:
            # Определяем по тексту
            period_map = {
                "Все время": "all",
                "Текущий год": "year",
                "Текущий квартал": "quarter",
                "Текущий месяц": "month",
                "Последние 30 дней": "last_30_days",
                "Последние 90 дней": "last_90_days"
            }
            self._current_period_filter = period_map.get(text, "all")

        print(f"📅 Период изменен: {self._current_period_filter}")

        # Обновляем рейтинг с учетом периода
        if self._employees_raw_data:
            self._apply_all_rating_filters()

    def _on_department_filter_changed(self, text: str) -> None:
        """Обработчик изменения фильтра по отделам для вкладки сотрудников"""
        if not hasattr(self, '_is_loading') or self._is_loading:
            return

        if not self.department_filter:
            return

        current_data = self.department_filter.currentData()
        if current_data is None or current_data == "all":
            if text == "Все отделы" or text == "":
                self._current_department_filter = "all"
            else:
                for i in range(self.department_filter.count()):
                    if self.department_filter.itemText(i) == text:
                        self._current_department_filter = self.department_filter.itemData(i)
                        break
        else:
            self._current_department_filter = current_data

        if self._employees_raw_data:
            self._apply_employee_filters()

    def _on_rating_department_filter_changed(self, text: str) -> None:
        """Обработчик изменения фильтра по отделам для вкладки рейтинга"""
        if not hasattr(self, '_is_loading') or self._is_loading:
            return

        if not self.rating_department_filter:
            return

        current_data = self.rating_department_filter.currentData()
        if current_data is None or current_data == "all":
            if text == "Все отделы" or text == "":
                self._current_rating_department_filter = "all"
            else:
                for i in range(self.rating_department_filter.count()):
                    if self.rating_department_filter.itemText(i) == text:
                        self._current_rating_department_filter = self.rating_department_filter.itemData(i)
                        break
        else:
            self._current_rating_department_filter = current_data

        if self._employees_raw_data:
            self._apply_all_rating_filters()

    def _apply_employee_filters(self) -> None:
        """Применяет фильтры к отображаемым сотрудникам"""
        if not self._employees_raw_data:
            return

        # Фильтруем по отделу
        filtered_data = self._get_filtered_by_department(self._employees_raw_data, self._current_department_filter)
        self._employees_data = filtered_data

        print(f"📊 Фильтр сотрудников: {len(self._employees_data)}/{len(self._employees_raw_data)} сотрудников")
        self._display_employees(self._employees_data)

    def _apply_all_rating_filters(self) -> None:
        """Применяет все фильтры (период + отдел) к рейтингу"""
        if not self._employees_raw_data:
            return

        # Сначала фильтруем по периоду
        period_filtered = self._filter_employees_by_period(self._employees_raw_data, self._current_period_filter)

        # Затем фильтруем по отделу
        filtered_data = self._get_filtered_by_department(period_filtered, self._current_rating_department_filter)

        print(f"📊 Фильтр рейтинга: {len(filtered_data)}/{len(self._employees_raw_data)} сотрудников")
        self._display_rating_employees(filtered_data)

    def _get_filtered_by_department(self, employees_data: List[Dict], filter_value) -> List[Dict]:
        """Фильтрует сотрудников по отделу"""
        if filter_value == "all":
            return employees_data

        department_id = None
        if isinstance(filter_value, str) and filter_value.startswith("dept_"):
            department_id = int(filter_value.split("_")[1])
        elif isinstance(filter_value, int):
            department_id = filter_value

        if department_id:
            return [emp for emp in employees_data if emp.get("department_id") == department_id]
        return employees_data

    def _display_employees(self, employees_data: List[Dict]):
        """Отображает сотрудников в grid"""
        if not hasattr(self, 'employees_grid'):
            print("❌ employees_grid не найден")
            return

        self._clear_grid(self.employees_grid)

        if not employees_data:
            self._show_empty_message(self.employees_grid, "Нет сотрудников в выбранном отделе")
            return

        row, col, max_cols = 0, 0, 3
        for emp_data in employees_data:
            try:
                card = EmployeeCard(emp_data)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                self.employees_grid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки для {emp_data.get('name')}: {e}")

        if hasattr(self, 'employeesContainer'):
            self.employeesContainer.update()
            self.employeesContainer.repaint()

        print(f"✅ Отображено {len(employees_data)} сотрудников")

    def _display_rating_employees(self, employees_data: List[Dict]):
        """Отображает сотрудников в рейтинге с сортировкой по КПД"""
        if not hasattr(self, 'rating_layout'):
            print("❌ rating_layout не найден")
            return

        self._clear_layout(self.rating_layout)

        if not employees_data:
            self._show_empty_layout_message(self.rating_layout, "Нет данных за выбранный период")
            return

        # Сортируем по КПД (от большего к меньшему)
        sorted_employees = sorted(employees_data, key=lambda x: x.get('kpd_percent', 0), reverse=True)

        for position, emp_data in enumerate(sorted_employees):
            try:
                card = RatingEmployeeCard(emp_data, position=position, parent=None)
                card.setMinimumHeight(80)
                card.clicked.connect(self._on_employee_clicked)
                self.rating_layout.addWidget(card)
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки рейтинга для {emp_data.get('name')}: {e}")

        self.rating_layout.addStretch()
        print(f"✅ Отображено {len(sorted_employees)} сотрудников в рейтинге")

    def _setup_rating_tab(self):
        """Настраивает вкладку рейтинга сотрудников"""
        if not hasattr(self, 'ratingTab'):
            print("❌ ratingTab не найден в UI")
            return

        if hasattr(self, 'ratingContainer'):
            self.rating_layout = self.ratingContainer.layout()
            if self.rating_layout is None:
                self.rating_layout = QVBoxLayout(self.ratingContainer)
                self.rating_layout.setSpacing(10)
                self.rating_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.ratingContainer.setLayout(self.rating_layout)
            print("✅ Настроен rating_layout")
        else:
            print("❌ ratingContainer не найден")

    def _setup_tab_container_force(self, tab_name, container_name, grid_name):
        """Принудительно создает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            print(f"❌ {tab_name} не найден")
            return

        old_layout = tab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            tab.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        setattr(self, container_name, container)
        setattr(self, grid_name, grid)
        print(f"✅ Создан контейнер для {tab_name}")

    def _create_employees_container(self):
        """Создает контейнер для сотрудников принудительно"""
        if not hasattr(self, 'employeesTab'):
            print("❌ employeesTab не найден")
            return

        old_layout = self.employeesTab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.employeesTab)
            layout.setContentsMargins(15, 15, 15, 15)
            self.employeesTab.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        self.employees_grid = QGridLayout(container)
        self.employees_grid.setHorizontalSpacing(15)
        self.employees_grid.setVerticalSpacing(15)
        self.employees_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        self.employeesTab.layout().addWidget(scroll)

        self.employeesContainer = container
        print("✅ Контейнер для сотрудников создан принудительно")

    def _setup_tab_container(self, tab_name, container_name, grid_name):
        """Настраивает контейнер для вкладки"""
        tab = getattr(self, tab_name, None)
        if not tab:
            return

        old_layout = tab.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            tab.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        grid = QGridLayout(container)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab.layout().addWidget(scroll)

        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _create_ui_programmatically(self):
        """Создает UI программно (только если UI файл не найден)"""
        self.setObjectName("AnalyticsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.titleLabel = QLabel("Аналитика / Навыки")
        self.titleLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #1B232A; padding: 10px 0;")
        layout.addWidget(self.titleLabel)

        self.tabWidget = QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabBar::tab { background-color: white; color: #666; padding: 12px 20px;
                margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px;
                border: 1px solid #E0E0E0; border-bottom: none; font-weight: bold; font-size: 14px; }
            QTabBar::tab:selected { background-color: #1B232A; color: white; }
            QTabWidget::pane { background-color: white; border: 1px solid #E0E0E0;
                border-radius: 0px 8px 8px 8px; margin-top: -1px; }
        """)

        self._add_tab("Рейтинг", "ratingTab", "ratingScroll", "ratingContainer", "ratingGrid")
        self._add_tab("Сотрудники", "employeesTab", "employeesScroll", "employeesContainer", "employeesGrid")
        self._add_tab("Темы", "themesTab", "themesScroll", "themesContainer", "themesGrid")
        self._add_tab("Проекты", "projectsTab", "projectsScroll", "projectsContainer", "projectsGrid")

        layout.addWidget(self.tabWidget)
        self.tabWidget.setCurrentIndex(0)

    def _add_tab(self, title, tab_name, scroll_name, container_name, grid_name):
        """Добавляет вкладку программно"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)

        # Для вкладки рейтинга добавляем фильтры
        if title == "Рейтинг":
            filter_layout = QHBoxLayout()

            # Фильтр периода
            self.period_filter = QComboBox()
            self.period_filter.setObjectName("periodFilter")
            self.period_filter.setMinimumHeight(41)
            self.period_filter.setStyleSheet("""
                QComboBox {
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    background-color: white;
                    min-width: 150px;
                    color: black;
                }
                QComboBox:hover {
                    border: 2px solid #ccab6e;
                }
            """)
            self.period_filter.addItem("Все время", "all")
            self.period_filter.addItem("Текущий год", "year")
            self.period_filter.addItem("Текущий квартал", "quarter")
            self.period_filter.addItem("Текущий месяц", "month")
            self.period_filter.addItem("Последние 30 дней", "last_30_days")
            self.period_filter.addItem("Последние 90 дней", "last_90_days")
            self.period_filter.setEditable(True)
            self.period_filter.currentTextChanged.connect(self._on_period_filter_changed)
            filter_layout.addWidget(self.period_filter)

            # Фильтр отдела для рейтинга
            self.rating_department_filter = QComboBox()
            self.rating_department_filter.setObjectName("departmentFilter")
            self.rating_department_filter.setMinimumHeight(41)
            self.rating_department_filter.setStyleSheet("""
                QComboBox {
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    background-color: white;
                    min-width: 150px;
                    color: black;
                }
                QComboBox:hover {
                    border: 2px solid #ccab6e;
                }
            """)
            self.rating_department_filter.addItem("Все отделы", "all")
            self.rating_department_filter.setEditable(True)
            self.rating_department_filter.currentTextChanged.connect(self._on_rating_department_filter_changed)
            filter_layout.addWidget(self.rating_department_filter)

            filter_layout.addStretch()
            tab_layout.addLayout(filter_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        if grid_name == "ratingGrid":
            grid = QVBoxLayout(container)
            grid.setSpacing(10)
            grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        else:
            grid = QGridLayout(container)
            grid.setHorizontalSpacing(15)
            grid.setVerticalSpacing(15)
            grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        self.tabWidget.addTab(tab, title)

        setattr(self, tab_name, tab)
        setattr(self, scroll_name, scroll)
        setattr(self, container_name, container)
        setattr(self, grid_name, grid)

    def _clear_grid(self, grid):
        if not grid:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        for grid_attr in ['employees_grid', 'themesGrid', 'projectsGrid']:
            grid = getattr(self, grid_attr, None)
            if grid:
                self._clear_grid(grid)
                label = QLabel("Нет данных для отображения")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
                grid.addWidget(label, 0, 0)

    def load_all_data(self):
        """Загружает все данные через сервис"""
        if not self.service:
            return

        self._is_loading = True

        try:
            self._employees_raw_data = self.service.get_all_employees_with_stats()
            self._employees_data = self._employees_raw_data.copy()
            print(f"📊 Загружено сотрудников: {len(self._employees_data)}")

            self._themes_data = self.service.get_themes_stats()
            print(f"📊 Загружено тем: {len(self._themes_data)}")

            self._projects_data = self.service.get_projects_stats()
            print(f"📊 Загружено проектов: {len(self._projects_data)}")

            self._load_departments()

            if not hasattr(self, 'rating_layout'):
                self._setup_rating_tab()

            self.populate_employees_tab()
            self.populate_rating_tab()
            self.populate_themes_tab()
            self.populate_projects_tab()

        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_loading = False

    def populate_employees_tab(self):
        if not hasattr(self, 'employees_grid'):
            print("❌ employees_grid не найден")
            return
        self._display_employees(self._employees_data)

    def populate_rating_tab(self):
        if not hasattr(self, 'rating_layout'):
            print("❌ rating_layout не найден")
            return
        self._display_rating_employees(self._employees_data)

    def _on_employee_clicked(self, employee_id: int):
        if hasattr(self, 'tabWidget') and self.tabWidget.count() > 1:
            self.tabWidget.setCurrentIndex(1)
        QMessageBox.information(self, "Сотрудник", f"Выбран сотрудник ID: {employee_id}")

    def populate_themes_tab(self):
        if not hasattr(self, 'themesGrid'):
            return

        self._clear_grid(self.themesGrid)

        if not self._themes_data:
            self._show_empty_message(self.themesGrid, "Нет данных о темах")
            return

        row, col, max_cols = 0, 0, 3
        for theme_data in self._themes_data:
            card_data = self.service.get_theme_card_data(theme_data)
            card = ThemeCard(card_data, analytics_service=self.service)
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            self.themesGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        print(f"✅ Отображено {len(self._themes_data)} тем")

    def populate_projects_tab(self):
        if not hasattr(self, 'projectsGrid'):
            return

        self._clear_grid(self.projectsGrid)

        if not self._projects_data:
            self._show_empty_message(self.projectsGrid, "Нет данных о проектах")
            return

        row, col, max_cols = 0, 0, 3
        for proj_data in self._projects_data:
            if not proj_data.get("is_archived", False):
                card_data = self.service.get_project_card_data(proj_data)
                card = ProjectCard(card_data, analytics_service=self.service)
                card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                self.projectsGrid.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        print(f"✅ Отображено проектов: {row * max_cols + col}")

    def _show_empty_message(self, grid, message):
        self._clear_grid(grid)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        grid.addWidget(label, 0, 0)

    def _show_empty_layout_message(self, layout, message):
        self._clear_layout(layout)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        layout.addWidget(label)

    def refresh(self):
        if self.service:
            self.load_all_data()