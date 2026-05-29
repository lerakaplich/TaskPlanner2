# windows/analytics/analytics_page.py

import os
from typing import List, Dict, Any, Optional
from PyQt6 import uic
from PyQt6.QtCore import Qt
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
        self._employees_data = []
        self._themes_data = []
        self._projects_data = []
        self._departments = []  # Список отделов для фильтра
        self._current_department_filter = "all"  # Текущий выбранный отдел
        self.department_filter = None  # Ссылка на комбобокс фильтра
        self._is_loading = False  # Флаг загрузки для предотвращения рекурсии

        # Загружаем данные
        if self.service:
            self.load_all_data()
        else:
            self._show_placeholder()

    def _setup_ui_from_file(self):
        """Настраивает UI из загруженного файла"""
        # Сначала настраиваем фильтры для сотрудников
        self._setup_employee_filters()

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

    def _setup_employee_filters(self):
        """Настраивает фильтры для вкладки сотрудников"""
        # Просто берем существующий departmentFilter_2 из UI
        if hasattr(self, 'departmentFilter_2'):
            self.department_filter = self.departmentFilter_2
            print("✅ Найден departmentFilter_2 в UI")

            # Временно отключаем сигнал, чтобы не сработал при инициализации
            self.department_filter.blockSignals(True)

            # Настраиваем комбобокс - пока только "Все отделы"
            self.department_filter.clear()
            self.department_filter.addItem("Все отделы", "all")
            self.department_filter.setEditable(True)

            # Подключаем сигнал (только после настройки)
            self.department_filter.currentTextChanged.connect(self._on_department_filter_changed)

            self.department_filter.blockSignals(False)

            print("✅ Настроен фильтр по отделам для сотрудников")
        else:
            print("❌ departmentFilter_2 не найден в UI")
            self.department_filter = None

    def _load_departments(self):
        """Загружает список отделов из БД и заполняет фильтр"""
        print("🔍 _load_departments: начало загрузки...")

        if not self.service or not self.service.base:
            print("❌ Сервис или база не доступны")
            return

        if not self.department_filter:
            print("❌ Фильтр по отделам не инициализирован")
            # Пробуем найти фильтр еще раз
            if hasattr(self, 'departmentFilter_2'):
                self.department_filter = self.departmentFilter_2
                print("✅ Найден departmentFilter_2 повторно")
            else:
                print("❌ departmentFilter_2 не найден")
                return

        try:
            from models.employees import Department

            # Получаем сессию для employees
            employees_session = self.service.base.employees_session
            departments = employees_session.query(Department).order_by(Department.name).all()

            print(f"📊 Найдено отделов в БД: {len(departments)}")

            # Блокируем сигналы при обновлении
            self.department_filter.blockSignals(True)

            # Сохраняем текущий выбранный текст для восстановления
            current_text = self.department_filter.currentText()
            if current_text == "" or current_text == "Все отделы":
                current_text = "all"

            # Очищаем и заполняем
            self.department_filter.clear()
            self.department_filter.addItem("Все отделы", "all")

            self._departments = []
            for dept in departments:
                self.department_filter.addItem(dept.name, f"dept_{dept.id}")
                self._departments.append({
                    "id": dept.id,
                    "name": dept.name
                })
                print(f"   - Добавлен отдел: {dept.name} (ID: {dept.id})")

            # Восстанавливаем выбор
            self._restore_department_filter_selection(current_text)

            self.department_filter.blockSignals(False)
            print(f"✅ Загружено отделов: {len(self._departments)}")
            print(f"📋 Теперь в фильтре {self.department_filter.count()} элементов")

        except Exception as e:
            print(f"❌ Ошибка загрузки отделов: {e}")
            import traceback
            traceback.print_exc()

    def _restore_department_filter_selection(self, current_value: str) -> None:
        """Восстанавливает выбранный фильтр отделов"""
        print(f"🔄 Восстановление выбора: current_value={current_value}")
        for i in range(self.department_filter.count()):
            item_text = self.department_filter.itemText(i)
            item_data = self.department_filter.itemData(i)
            print(f"   Элемент {i}: text='{item_text}', data={item_data}")

            if current_value == "all" and item_data == "all":
                self.department_filter.setCurrentIndex(i)
                print(f"   ✅ Выбран элемент {i} (Все отделы)")
                break
            elif item_text == current_value:
                self.department_filter.setCurrentIndex(i)
                print(f"   ✅ Выбран элемент {i} по тексту")
                break
            elif item_data == current_value:
                self.department_filter.setCurrentIndex(i)
                print(f"   ✅ Выбран элемент {i} по данным")
                break

    def _on_department_filter_changed(self, text: str) -> None:
        """Обработчик изменения фильтра по отделам"""
        # Пропускаем обработку во время загрузки
        if not hasattr(self, '_is_loading') or self._is_loading:
            print(f"⏭️ Пропуск обработки фильтра (is_loading={getattr(self, '_is_loading', 'no_attr')})")
            return

        if not self.department_filter:
            return

        print(f"🔄 Фильтр изменен: '{text}'")

        current_data = self.department_filter.currentData()
        print(f"   current_data={current_data}")

        # Определяем выбранное значение
        if current_data is None or current_data == "all":
            if text == "Все отделы" or text == "":
                self._current_department_filter = "all"
                print(f"   Выбран 'Все отделы'")
            else:
                # Ищем по тексту
                for i in range(self.department_filter.count()):
                    if self.department_filter.itemText(i) == text:
                        self._current_department_filter = self.department_filter.itemData(i)
                        print(f"   Найдено по тексту: {self._current_department_filter}")
                        break
        else:
            self._current_department_filter = current_data
            print(f"   Выбрано по данным: {self._current_department_filter}")

        # Применяем фильтр (только если данные уже загружены)
        if self._employees_data:
            self._apply_department_filter()

    def _apply_department_filter(self) -> None:
        """Применяет фильтр по отделам к отображаемым сотрудникам"""
        if not self._employees_data:
            return

        # Получаем отфильтрованные данные
        filtered_data = self._get_filtered_employees()

        print(f"📊 Фильтр по отделу '{self._current_department_filter}': "
              f"{len(filtered_data)}/{len(self._employees_data)} сотрудников")

        # Отображаем отфильтрованных сотрудников
        self._display_employees(filtered_data)

    def _get_filtered_employees(self) -> List[Dict]:
        """Возвращает отфильтрованный список сотрудников"""
        if self._current_department_filter == "all":
            return self._employees_data

        # Извлекаем ID отдела из данных фильтра
        department_id = None
        if isinstance(self._current_department_filter, str) and self._current_department_filter.startswith("dept_"):
            department_id = int(self._current_department_filter.split("_")[1])
        elif isinstance(self._current_department_filter, int):
            department_id = self._current_department_filter

        if department_id:
            return [
                emp for emp in self._employees_data
                if emp.get("department_id") == department_id
            ]

        return self._employees_data

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

        # Принудительно обновляем контейнер
        if hasattr(self, 'employeesContainer'):
            self.employeesContainer.update()
            self.employeesContainer.repaint()

        print(f"✅ Отображено {len(employees_data)} сотрудников")

    def _setup_rating_tab(self):
        """Настраивает вкладку рейтинга сотрудников"""
        if not hasattr(self, 'ratingTab'):
            print("❌ ratingTab не найден в UI")
            return

        # Получаем контейнер для рейтинга
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

        # Очищаем вкладку
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

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
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

        # Очищаем вкладку
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

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
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

        # Очищаем вкладку
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

        # Создаем ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Создаем контейнер
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # Создаем GridLayout
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

        # Заголовок
        self.titleLabel = QLabel("Аналитика / Навыки")
        self.titleLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #1B232A; padding: 10px 0;")
        layout.addWidget(self.titleLabel)

        # Tab Widget
        self.tabWidget = QTabWidget()
        self.tabWidget.setStyleSheet("""
            QTabBar::tab { background-color: white; color: #666; padding: 12px 20px;
                margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px;
                border: 1px solid #E0E0E0; border-bottom: none; font-weight: bold; font-size: 14px; }
            QTabBar::tab:selected { background-color: #1B232A; color: white; }
            QTabWidget::pane { background-color: white; border: 1px solid #E0E0E0;
                border-radius: 0px 8px 8px 8px; margin-top: -1px; }
        """)

        # Вкладки - Рейтинг ПЕРВЫЙ!
        self._add_tab("Рейтинг", "ratingTab", "ratingScroll", "ratingContainer", "ratingGrid")
        self._add_tab("Сотрудники", "employeesTab", "employeesScroll", "employeesContainer", "employeesGrid")
        self._add_tab("Темы", "themesTab", "themesScroll", "themesContainer", "themesGrid")
        self._add_tab("Проекты", "projectsTab", "projectsScroll", "projectsContainer", "projectsGrid")

        layout.addWidget(self.tabWidget)

        # Делаем Рейтинг активной вкладкой
        self.tabWidget.setCurrentIndex(0)

    def _add_tab(self, title, tab_name, scroll_name, container_name, grid_name):
        """Добавляет вкладку программно"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)

        # Для вкладки сотрудников добавляем горизонтальный layout с фильтром
        if title == "Сотрудники":
            filter_layout = QHBoxLayout()
            self.department_filter = QComboBox()
            self.department_filter.setObjectName("departmentFilter_2")
            self.department_filter.setMinimumHeight(41)
            self.department_filter.setStyleSheet("""
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
            self.department_filter.addItem("Все отделы", "all")
            self.department_filter.setEditable(True)
            self.department_filter.setPlaceholderText("Все отделы")
            self.department_filter.currentTextChanged.connect(self._on_department_filter_changed)
            filter_layout.addWidget(self.department_filter)
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
        """Очищает grid layout"""
        if not grid:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_layout(self, layout):
        """Очищает вертикальный layout"""
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        """Показывает заглушку"""
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

        self._is_loading = True  # Устанавливаем флаг загрузки

        try:
            self._employees_data = self.service.get_all_employees_with_stats()
            print(f"📊 Загружено сотрудников: {len(self._employees_data)}")

            self._themes_data = self.service.get_themes_stats()
            print(f"📊 Загружено тем: {len(self._themes_data)}")

            self._projects_data = self.service.get_projects_stats()
            print(f"📊 Загружено проектов: {len(self._projects_data)}")

            # Загружаем список отделов для фильтра (после загрузки сотрудников)
            self._load_departments()

            # Убеждаемся, что рейтинговая вкладка настроена перед заполнением
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
            self._is_loading = False  # Снимаем флаг загрузки

    def populate_employees_tab(self):
        """Заполняет вкладку сотрудников"""
        if not hasattr(self, 'employees_grid'):
            print("❌ employees_grid не найден")
            return

        # Отображаем всех сотрудников (фильтр по умолчанию - "Все отделы")
        self._display_employees(self._employees_data)

    def populate_rating_tab(self):
        """Заполняет вкладку рейтинга сотрудников (сортировка по КПД)"""
        if not hasattr(self, 'rating_layout'):
            print("❌ rating_layout не найден")
            return

        self._clear_layout(self.rating_layout)

        if not self._employees_data:
            self._show_empty_layout_message(self.rating_layout, "Нет данных о сотрудниках")
            return

        # Получаем отсортированный список сотрудников по КПД
        rating_employees = self.service.get_employees_rating()
        print(f"📊 Загружено сотрудников для рейтинга: {len(rating_employees)}")

        for position, emp_data in enumerate(rating_employees):
            try:
                card = RatingEmployeeCard(emp_data, position=position, parent=None)
                card.setMinimumHeight(80)
                card.clicked.connect(self._on_employee_clicked)
                self.rating_layout.addWidget(card)
                print(f"   ✅ Добавлена карточка рейтинга #{position + 1}: {emp_data.get('name')} "
                      f"(КПД: {emp_data.get('completed_tasks', 0)}/{emp_data.get('total_tasks', 0)})")
            except Exception as e:
                print(f"   ❌ Ошибка при создании карточки рейтинга для {emp_data.get('name')}: {e}")

        # Добавляем растяжение в конце
        self.rating_layout.addStretch()
        print(f"✅ Отображено {len(rating_employees)} сотрудников в рейтинге")

    def _on_employee_clicked(self, employee_id: int):
        """Обработчик клика по карточке сотрудника в рейтинге"""
        # Переключаемся на вкладку сотрудников (индекс 1, так как рейтинг на 0)
        if hasattr(self, 'tabWidget') and self.tabWidget.count() > 1:
            self.tabWidget.setCurrentIndex(1)  # Сотрудники на второй позиции

        QMessageBox.information(self, "Сотрудник", f"Выбран сотрудник ID: {employee_id}")

    def populate_themes_tab(self):
        """Заполняет вкладку тем"""
        if not hasattr(self, 'themesGrid'):
            return

        self._clear_grid(self.themesGrid)

        if not self._themes_data:
            self._show_empty_message(self.themesGrid, "Нет данных о темах")
            return

        row, col, max_cols = 0, 0, 3
        for theme_data in self._themes_data:
            # Подготавливаем данные через сервис
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
        """Заполняет вкладку проектов"""
        if not hasattr(self, 'projectsGrid'):
            return

        self._clear_grid(self.projectsGrid)

        if not self._projects_data:
            self._show_empty_message(self.projectsGrid, "Нет данных о проектах")
            return

        row, col, max_cols = 0, 0, 3
        for proj_data in self._projects_data:
            # Показываем только активные проекты
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
        """Показывает сообщение об отсутствии данных в grid"""
        self._clear_grid(grid)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        grid.addWidget(label, 0, 0)

    def _show_empty_layout_message(self, layout, message):
        """Показывает сообщение об отсутствии данных в layout"""
        self._clear_layout(layout)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #666; padding: 50px;")
        layout.addWidget(label)

    def refresh(self):
        """Обновляет все данные"""
        if self.service:
            self.load_all_data()