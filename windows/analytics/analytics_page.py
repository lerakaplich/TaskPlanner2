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
from windows.profile.profile_page import ProfilePage
from services.analytics_service.analytics_service import AnalyticsService
from windows.analytics.employees.employee_card import EmployeeCard
from windows.analytics.theme.theme_card import ThemeCard
from windows.analytics.projects.project_card_analytics import ProjectCard
from windows.analytics.rating.rating_employee_card import RatingEmployeeCard
from models.employees import Employee


class AnalyticsPage(QWidget):
    """Страница аналитики - только отображение, логика в сервисе"""

    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        # Инициализируем сервис
        self.session = session
        self.service = AnalyticsService(session) if session else None

        # Инициализируем атрибуты ДО загрузки UI
        self._employees_raw_data = []
        self._employees_data = []
        self._themes_data = []
        self._projects_data = []
        self._departments = []
        self._current_department_filter = "all"
        self._current_rating_department_filter = "all"
        self._current_period_filter = "all"
        self.department_filter = None
        self.rating_department_filter = None
        self.period_filter = None
        self._is_loading = False
        self._departments_loaded = False

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
        """Возвращает начальную и конечную дату для выбранного периода."""
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
        """Фильтрует данные сотрудников по периоду, используя правильный расчет КПД."""
        print(f"\n🔍 _filter_employees_by_period вызван с period={period}")

        if period == "all" or not employees_data:
            print(f"📊 РЕЙТИНГ: Период 'Все время' - без фильтрации, сотрудников: {len(employees_data)}")
            return employees_data

        start_date, end_date = self._get_date_range_for_period(period)
        if start_date is None:
            return employees_data

        print(f"\n{'=' * 80}")
        print(f"📊 РЕЙТИНГ: Начало расчета КПД за период")
        print(f"   Период: {period}")
        print(f"   Диапазон: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
        print(f"   Всего сотрудников в БД: {len(employees_data)}")
        print(f"{'=' * 80}")

        try:
            tasks_by_employee = self._get_tasks_for_period(start_date, end_date)

            filtered_employees = []
            for emp in employees_data:
                emp_id = emp.get("id")
                emp_name = emp.get("name", "Неизвестный")
                tasks_info = tasks_by_employee.get(emp_id, {
                    "completed": 0, "total": 0, "kpd_percent": 0, "weighted_kpd": 0, "overtime": 0
                })

                emp_copy = emp.copy()
                emp_copy["completed_tasks"] = tasks_info["completed"]
                emp_copy["total_tasks"] = tasks_info["total"]
                emp_copy["kpd_percent"] = tasks_info["kpd_percent"]
                emp_copy["weighted_kpd"] = tasks_info["weighted_kpd"]
                emp_copy["kpd"] = tasks_info["kpd_percent"] / 100 if tasks_info["kpd_percent"] > 0 else 0
                emp_copy["overtime_hours"] = tasks_info.get("overtime", 0)

                filtered_employees.append(emp_copy)

                print(f"\n👤 Сотрудник: {emp_name} (ID: {emp_id})")
                print(f"   📋 Всего задач за период: {tasks_info['total']}")
                print(f"   ✅ Выполнено: {tasks_info['completed']}")
                print(f"   📊 Итоговый КПД: {tasks_info['kpd_percent']:.1f}%")
                print(f"   ⚖️ Взвешенный КПД: {tasks_info['weighted_kpd']:.1f}%")
                print(f"   ⏱️ Переработки: {tasks_info.get('overtime', 0):.1f} ч")

            print(f"\n{'=' * 80}")
            print(f"📊 РЕЙТИНГ: Итоги за период {period}")
            print(f"   Обработано сотрудников: {len(filtered_employees)}")

            sorted_by_kpd = sorted(filtered_employees, key=lambda x: x.get('kpd_percent', 0), reverse=True)
            print(f"\n   🏆 ТОП-5 сотрудников за период:")
            for i, emp in enumerate(sorted_by_kpd[:5]):
                print(f"      {i + 1}. {emp.get('name', 'Неизвестный')}: {emp.get('kpd_percent', 0):.1f}% "
                      f"({emp.get('completed_tasks', 0)}/{emp.get('total_tasks', 0)} задач)")

            print(f"{'=' * 80}\n")
            return filtered_employees

        except Exception as e:
            print(f"❌ Ошибка фильтрации по периоду: {e}")
            import traceback
            traceback.print_exc()
            return employees_data

    def _get_tasks_for_period(self, start_date: datetime, end_date: datetime) -> Dict:
        """Получает задачи сотрудников за указанный период и рассчитывает КПД."""
        if not self.service or not self.service.base:
            return {}

        try:
            from models.tasks import Task
            from models.employees import EmployeeNote
            from services.analytics_service.kpd_calculator import KPDCalculator

            tasks_session = self.service.base.session
            employees_session = self.service.base.employees_session

            print(f"\n{'─' * 60}")
            print(f"🔍 ПОЛУЧЕНИЕ ЗАДАЧ ЗА ПЕРИОД")
            print(f"   Начало: {start_date.strftime('%d.%m.%Y %H:%M:%S')}")
            print(f"   Конец: {end_date.strftime('%d.%m.%Y %H:%M:%S')}")
            print(f"{'─' * 60}")

            # Получаем задачи, завершенные в указанный период
            completed_tasks = tasks_session.query(Task).filter(
                Task.completed == True,
                Task.completed_at >= start_date,
                Task.completed_at <= end_date
            ).all()
            # В _get_tasks_for_period после получения completed_tasks
            print(f"📋 Завершенных задач в период: {len(completed_tasks)}")
            for task in completed_tasks:
                print(
                    f"   - Задача {task.id}: '{task.title[:30]}', assigned_to={task.assigned_to}, completed_at={task.completed_at}")
                if task.assigned_to:
                    emp = employees_session.query(Employee).filter(Employee.id == task.assigned_to).first()
                    print(
                        f"     Исполнитель: {emp.last_name} {emp.first_name} (ID: {emp.id})" if emp else "     Исполнитель не найден в БД")

            # Получаем задачи, созданные в период (активные, еще не завершенные)
            active_tasks = tasks_session.query(Task).filter(
                Task.completed == False,
                Task.created_at >= start_date,
                Task.created_at <= end_date
            ).all()
            print(f"📋 Активных задач (созданных в период): {len(active_tasks)}")

            all_relevant_tasks = completed_tasks + active_tasks
            print(f"📋 Всего релевантных задач: {len(all_relevant_tasks)}")

            result = {}

            for task in all_relevant_tasks:
                if not task.assigned_to:
                    continue

                emp_id = task.assigned_to
                if emp_id not in result:
                    result[emp_id] = {
                        "tasks": [], "completed_count": 0, "total_count": 0, "overtime": 0.0
                    }

                result[emp_id]["tasks"].append(task)
                result[emp_id]["total_count"] += 1

                if task.completed:
                    result[emp_id]["completed_count"] += 1

            print(f"\n{'─' * 40}")
            print(f"📊 РАСЧЕТ КПД ДЛЯ КАЖДОГО СОТРУДНИКА")
            print(f"{'─' * 40}")

            for emp_id, data in result.items():
                emp = employees_session.query(Employee).filter(Employee.id == emp_id).first()
                emp_name = f"{emp.last_name} {emp.first_name}" if emp else f"ID:{emp_id}"

                print(f"\n👤 Сотрудник: {emp_name}")
                print(f"   Всего задач за период: {len(data['tasks'])}")
                print(f"   Выполнено: {data['completed_count']}")
                print(f"   Не выполнено: {data['total_count'] - data['completed_count']}")

                if data["tasks"]:
                    kpd_result = KPDCalculator.calculate_employee_kpd(data["tasks"])
                    print(f"\n   🔢 РАСЧЕТ КПД:")
                    print(f"      Суммарный КПД: {kpd_result['total_kpd']:.2f}%")
                    print(f"      Взвешенный КПД: {kpd_result['weighted_kpd']:.2f}%")
                    print(f"      Выполнено задач: {kpd_result['completed_tasks_count']}")
                    print(f"      Всего задач: {kpd_result['total_tasks_count']}")

                    print(f"\n   📋 Задачи сотрудника:")
                    for i, task in enumerate(data["tasks"]):
                        status = "✅" if task.completed else "⏳"
                        task_kpd = task.kpd_score if task.completed else 0
                        print(f"      {status} {i + 1}. {task.title[:50]} - КПД: {task_kpd:.1f}%")
                        if task.completed:
                            print(f"         Эффективность: {task.efficiency_factor:.2f}")
                            print(f"         Приоритет: {task.priority_factor:.2f}")
                            print(f"         Сложность: {task.difficulty}")

                    data["kpd_percent"] = kpd_result["total_kpd"]
                    data["weighted_kpd"] = kpd_result["weighted_kpd"]
                    data["completed"] = data["completed_count"]
                    data["total"] = data["total_count"]
                else:
                    data["kpd_percent"] = 0
                    data["weighted_kpd"] = 0
                    data["completed"] = 0
                    data["total"] = 0

            # Получаем переработки за период
            print(f"\n{'─' * 40}")
            print(f"⏱️ ПЕРЕРАБОТКИ ЗА ПЕРИОД")
            print(f"{'─' * 40}")

            # ИСПРАВЛЕНО: используем overtime_date вместо created_at
            overtimes = employees_session.query(EmployeeNote).filter(
                EmployeeNote.overtime_date >= start_date.date(),
                EmployeeNote.overtime_date <= end_date.date()
            ).all()

            print(f"   Найдено записей о переработках: {len(overtimes)}")

            for ot in overtimes:
                emp_id = ot.employee_id
                if emp_id not in result:
                    result[emp_id] = {
                        "tasks": [], "completed_count": 0, "total_count": 0, "overtime": 0.0,
                        "kpd_percent": 0, "weighted_kpd": 0, "completed": 0, "total": 0
                    }

                if ot.overtime_start and ot.overtime_end:
                    # Используем overtime_date для создания datetime
                    start = datetime.combine(ot.overtime_date, ot.overtime_start)
                    end = datetime.combine(ot.overtime_date, ot.overtime_end)
                    if end < start:
                        # Если время окончания меньше времени начала, добавляем день
                        end = end.replace(day=end.day + 1)
                    hours = (end - start).total_seconds() / 3600
                    result[emp_id]["overtime"] += hours

                    emp = employees_session.query(Employee).filter(Employee.id == emp_id).first()
                    emp_name = f"{emp.last_name} {emp.first_name}" if emp else f"ID:{emp_id}"
                    print(f"   👤 {emp_name}: {ot.overtime_date.strftime('%d.%m.%Y')} +{hours:.1f} ч переработок")

            return result

        except Exception as e:
            print(f"❌ Ошибка получения задач за период: {e}")
            import traceback
            traceback.print_exc()
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
            for dept in departments:
                print(f"   - {dept.name} (ID: {dept.id})")

            if self.department_filter:
                self.department_filter.blockSignals(True)
                self.department_filter.clear()
                self.department_filter.addItem("Все отделы", "all")
                for dept in departments:
                    self.department_filter.addItem(dept.name, f"dept_{dept.id}")
                self.department_filter.blockSignals(False)
                print(f"✅ Загружено отделов в фильтр сотрудников: {self.department_filter.count() - 1}")

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
            import traceback
            traceback.print_exc()

    def _on_period_filter_changed(self, text: str) -> None:
        """Обработчик изменения фильтра периода для рейтинга"""
        # Проверяем существование атрибута
        if not hasattr(self, '_is_loading'):
            return

        print(f"\n🔄 _on_period_filter_changed: text='{text}', _is_loading={self._is_loading}")

        if self._is_loading:
            print("   ⏭️ Пропуск: идет загрузка")
            return

        if not self.period_filter:
            print("   ❌ period_filter is None")
            return

        current_data = self.period_filter.currentData()
        if current_data:
            self._current_period_filter = current_data
        else:
            period_map = {
                "Все время": "all",
                "Текущий год": "year",
                "Текущий квартал": "quarter",
                "Текущий месяц": "month",
                "Последние 30 дней": "last_30_days",
                "Последние 90 дней": "last_90_days"
            }
            self._current_period_filter = period_map.get(text, "all")

        print(f"📅 Период изменен на: {self._current_period_filter}")

        if self._employees_raw_data:
            print(f"📊 Применяем фильтр периода к {len(self._employees_raw_data)} сотрудникам")
            self._apply_all_rating_filters()
        else:
            print("⚠️ _employees_raw_data пуст, фильтр не применен")

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

        print(f"📋 Фильтр отдела рейтинга изменен: {self._current_rating_department_filter}")

        if self._employees_raw_data:
            self._apply_all_rating_filters()

    def _apply_employee_filters(self) -> None:
        """Применяет фильтры к отображаемым сотрудникам"""
        if not self._employees_raw_data:
            return

        filtered_data = self._get_filtered_by_department(self._employees_raw_data, self._current_department_filter)
        self._employees_data = filtered_data

        print(f"📊 Фильтр сотрудников: {len(self._employees_data)}/{len(self._employees_raw_data)} сотрудников")
        self._display_employees(self._employees_data)

    def _apply_all_rating_filters(self) -> None:
        """Применяет все фильтры (период + отдел) к рейтингу"""
        print(f"\n🔧 _apply_all_rating_filters вызван")
        print(f"   _current_period_filter = {self._current_period_filter}")
        print(f"   _employees_raw_data размер = {len(self._employees_raw_data)}")

        if not self._employees_raw_data:
            print("   ❌ _employees_raw_data пуст")
            return

        print(f"📊 Шаг 1: Фильтрация по периоду '{self._current_period_filter}'...")
        period_filtered = self._filter_employees_by_period(self._employees_raw_data, self._current_period_filter)

        print(f"📊 Шаг 2: Фильтрация по отделу '{self._current_rating_department_filter}'...")
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
                card.clicked.connect(self._open_employee_profile)  # Подключаем сигнал
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

    def _open_employee_profile(self, employee_id: int):
        """Открывает профиль сотрудника"""
        if not employee_id:
            return

        # Получаем данные сотрудника
        employee_data = None
        for emp in self._employees_raw_data:
            if emp.get('id') == employee_id:
                employee_data = emp
                break

        if not employee_data:
            QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
            return

        # Создаем и показываем страницу профиля
        try:
            # Ищем главное окно
            main_window = self.window()
            while main_window and not hasattr(main_window, 'navigation'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'navigation'):
                # Если есть главное окно с навигацией, используем его
                if hasattr(main_window.navigation, 'pages'):
                    profile_page = main_window.navigation.get_profile_page()
                    profile_page.employee_id = employee_id
                    profile_page.current_user = employee_data
                    profile_page.load_employee()
                    if hasattr(profile_page, 'chart_widget'):
                        profile_page.chart_widget.load_data(employee_id)
                    main_window.contentStack.setCurrentWidget(profile_page)
            else:
                # Создаем отдельное окно профиля
                from windows.profile.profile_page import ProfilePage
                profile_dialog = ProfilePage(
                    employee_id=employee_id,
                    current_user=employee_data,
                    parent=self
                )
                profile_dialog.setWindowTitle(f"Профиль: {employee_data.get('name', 'Сотрудник')}")
                profile_dialog.resize(800, 600)
                profile_dialog.show()
        except Exception as e:
            print(f"❌ Ошибка открытия профиля: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть профиль: {e}")

    def _on_employee_card_clicked(self, employee_id: int):
        """Обработчик клика по карточке сотрудника"""
        self._open_employee_profile(employee_id)

    def _display_rating_employees(self, employees_data: List[Dict]):
        """Отображает сотрудников в рейтинге с сортировкой по КПД"""
        print(f"\n🎯 _display_rating_employees: получено {len(employees_data)} сотрудников")

        if not hasattr(self, 'rating_layout'):
            print("❌ rating_layout не найден")
            return

        self._clear_layout(self.rating_layout)

        if not employees_data:
            self._show_empty_layout_message(self.rating_layout, "Нет данных за выбранный период")
            return

        sorted_employees = sorted(employees_data, key=lambda x: x.get('kpd_percent', 0), reverse=True)

        print("   Отсортированный рейтинг:")
        for i, emp in enumerate(sorted_employees):
            print(f"      {i + 1}. {emp.get('name', '?')}: КПД={emp.get('kpd_percent', 0):.1f}%")

        for position, emp_data in enumerate(sorted_employees):
            try:
                card = RatingEmployeeCard(emp_data, position=position, parent=None)
                card.setMinimumHeight(80)
                # ИСПРАВЛЕНО: вызываем _open_employee_profile вместо _on_employee_clicked
                card.clicked.connect(self._open_employee_profile)
                self.rating_layout.addWidget(card)
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки рейтинга для {emp_data.get('name')}: {e}")

        self.rating_layout.addStretch()
        print(f"✅ Отображено {len(sorted_employees)} сотрудников в рейтинге\n")

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

        if title == "Рейтинг":
            filter_layout = QHBoxLayout()

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
            print("📊 Данные сотрудников:")
            for emp in self._employees_raw_data:
                print(f"   - {emp.get('name')}: КПД={emp.get('kpd_percent', 0)}%, задач={emp.get('total_tasks', 0)}")

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
        """Заполняет вкладку рейтинга - применяет фильтр периода при первом показе"""
        if not hasattr(self, 'rating_layout'):
            print("❌ rating_layout не найден")
            return

        print("\n🌟 populate_rating_tab: первая загрузка рейтинга")

        if self._current_period_filter != "all":
            print(f"   Применяем фильтр периода '{self._current_period_filter}' при загрузке")
            self._apply_all_rating_filters()
        else:
            print("   Отображаем рейтинг без фильтра (Все время)")
            self._display_rating_employees(self._employees_data)

    # Удалите этот метод или измените его:
    def _on_employee_clicked(self, employee_id: int):
        self._open_employee_profile(employee_id)  # теперь вызывает открытие профиля

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