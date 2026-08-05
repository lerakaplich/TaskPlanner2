# windows/gantt/calendar_widget.py

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QScrollArea, QMessageBox, QSizePolicy,
    QApplication
)

from services.gantt_service.gantt_base_service import TaskGanttData
from services.gantt_service.gantt_service import GanttService


class CalendarWidget(QWidget):
    """Виджет календаря для отображения задач"""

    # Сигнал при клике на задачу
    task_clicked = pyqtSignal(int)

    def __init__(self, gantt_service: GanttService, parent=None):
        super().__init__(parent)
        self._service = gantt_service
        self._current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._tasks: List[TaskGanttData] = []
        self._day_widgets: List[CalendarDayWidget] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Панель навигации
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(15)

        self.prev_month_btn = QPushButton("◀")
        self.prev_month_btn.setFixedSize(40, 40)
        self.prev_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ccab6e;
            }
        """)
        self.prev_month_btn.clicked.connect(self._prev_month)

        self.current_month_label = QLabel()
        self.current_month_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1B232A;
            padding: 10px;
        """)
        self.current_month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_month_btn = QPushButton("▶")
        self.next_month_btn.setFixedSize(40, 40)
        self.next_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ccab6e;
            }
        """)
        self.next_month_btn.clicked.connect(self._next_month)

        self.today_btn = QPushButton("Сегодня")
        self.today_btn.setFixedSize(100, 40)
        self.today_btn.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        self.today_btn.clicked.connect(self._go_to_today)

        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.current_month_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.today_btn)
        nav_layout.addWidget(self.next_month_btn)

        main_layout.addLayout(nav_layout)

        # Заголовки дней недели
        days_layout = QHBoxLayout()
        days_layout.setSpacing(1)

        weekdays = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for day in weekdays:
            label = QLabel(day)
            label.setStyleSheet("""
                background-color: #1B232A;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
            """)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            days_layout.addWidget(label)

        main_layout.addLayout(days_layout)

        # Сетка календаря
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(2)
        self.calendar_grid.setContentsMargins(0, 0, 0, 0)

        main_layout.addLayout(self.calendar_grid)

        # Применяем общий стиль
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

    def set_tasks(self, tasks: List[TaskGanttData]) -> None:
        """Устанавливает задачи для отображения"""
        self._tasks = tasks
        print(f"📅 CalendarWidget: установлено {len(tasks)} задач")
        if tasks:
            print(f"   Первая задача: {tasks[0].name} ({tasks[0].start_date.date()} - {tasks[0].end_date.date()})")
        self._update_calendar()

    def _update_calendar(self) -> None:
        """Обновляет отображение календаря"""
        print(f"📅 Обновление календаря: {self._current_date.strftime('%B %Y')}, задач: {len(self._tasks)}")

        # Очищаем сетку и отключаем сигналы от старых виджетов
        for widget in self._day_widgets:
            try:
                widget.task_clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            widget.deleteLater()

        self._day_widgets.clear()

        # Очищаем сетку
        for i in reversed(range(self.calendar_grid.count())):
            item = self.calendar_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                self.calendar_grid.removeItem(item)

        # Обновляем заголовок месяца
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.current_month_label.setText(f"{month_names[self._current_date.month - 1]} {self._current_date.year}")

        # Определяем первый день месяца и количество дней
        first_day = self._current_date.replace(day=1)
        start_weekday = first_day.weekday()  # 0 = понедельник

        # Количество дней в месяце
        if self._current_date.month == 12:
            next_month = self._current_date.replace(year=self._current_date.year + 1, month=1, day=1)
        else:
            next_month = self._current_date.replace(month=self._current_date.month + 1, day=1)
        days_in_month = (next_month - first_day).days

        # Определяем границы календаря (показываем 6 недель)
        total_cells = 42  # 6 недель * 7 дней
        start_offset = start_weekday

        # Создаём ячейки календаря
        tasks_found = 0
        for i in range(total_cells):
            row = i // 7
            col = i % 7

            day_number = i - start_offset + 1

            # Создаём контейнер для дня
            day_widget = CalendarDayWidget()
            day_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            if 1 <= day_number <= days_in_month:
                # День текущего месяца
                current_day = self._current_date.replace(day=day_number)
                day_widget.set_day(day_number, current_day)

                # Находим задачи на этот день
                day_tasks = self._get_tasks_for_date(current_day)
                tasks_found += len(day_tasks)
                day_widget.set_tasks(day_tasks, self._service)

                # Подключаем сигнал клика
                day_widget.task_clicked.connect(self._on_task_clicked)

                # Подсветка текущего дня
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if current_day.date() == today.date():
                    day_widget.set_today(True)
            else:
                # День другого месяца (серый)
                day_widget.set_empty()

            self.calendar_grid.addWidget(day_widget, row, col)
            self._day_widgets.append(day_widget)

        # Настраиваем растяжение колонок и строк
        for i in range(7):
            self.calendar_grid.setColumnStretch(i, 1)
        for i in range(6):
            self.calendar_grid.setRowStretch(i, 1)

        print(f"📅 Создано {total_cells} ячеек, найдено задач: {tasks_found}")

    def _on_task_clicked(self, task_id: int) -> None:
        """Обработчик клика по задаче - единая точка входа для сигнала"""
        self.task_clicked.emit(task_id)

    def showEvent(self, event) -> None:
        """Обновляет календарь при показе"""
        super().showEvent(event)
        self._update_calendar()

    def _get_tasks_for_date(self, target_date: datetime) -> List[TaskGanttData]:
        """Возвращает задачи на указанную дату"""
        tasks_on_date = []
        for task in self._tasks:
            if task.start_date <= target_date <= task.end_date:
                tasks_on_date.append(task)
        return tasks_on_date

    def _prev_month(self) -> None:
        """Предыдущий месяц"""
        if self._current_date.month == 1:
            self._current_date = self._current_date.replace(year=self._current_date.year - 1, month=12)
        else:
            self._current_date = self._current_date.replace(month=self._current_date.month - 1)
        self._update_calendar()

    def _next_month(self) -> None:
        """Следующий месяц"""
        if self._current_date.month == 12:
            self._current_date = self._current_date.replace(year=self._current_date.year + 1, month=1)
        else:
            self._current_date = self._current_date.replace(month=self._current_date.month + 1)
        self._update_calendar()

    def _go_to_today(self) -> None:
        """Перейти к текущему месяцу"""
        self._current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._update_calendar()


class CalendarDayWidget(QFrame):
    """Виджет для отображения одного дня в календаре"""

    task_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_number = 0
        self._date = None
        self._tasks = []
        self._service = None
        self._is_today = False
        self._task_widgets = []
        self._is_expanded = False
        self._all_tasks_visible = False
        self._more_label = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(70, 70)
        self.setMaximumSize(16777215, 16777215)

        # Основной вертикальный layout
        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(5, 5, 5, 5)

        # Верхняя панель с номером дня
        self.day_label = QLabel()
        self.day_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            padding: 2px;
        """)
        self.day_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.day_label)

        # Контейнер для задач
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background-color: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(3)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self.tasks_container)
        layout.addStretch()

        # Стиль рамки
        self.setStyleSheet("""
            CalendarDayWidget {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
            CalendarDayWidget:hover {
                background-color: #F8F9FA;
                border-color: #ccab6e;
            }
        """)

    def set_day(self, day_number: int, date: datetime) -> None:
        """Устанавливает номер дня и дату"""
        self._day_number = day_number
        self._date = date
        self.day_label.setText(str(day_number))

    def set_tasks(self, tasks: List[TaskGanttData], service: GanttService) -> None:
        """Устанавливает задачи для отображения"""
        self._tasks = tasks
        self._service = service
        self._all_tasks_visible = False
        self._is_expanded = False

        # Отключаем сигналы от старых карточек
        for widget in self._task_widgets:
            try:
                widget.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            widget.deleteLater()

        self._task_widgets.clear()

        # Очищаем контейнер
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not tasks:
            return

        # Показываем максимум 2 задачи, остальные сворачиваем
        visible_tasks = tasks[:2]
        remaining = len(tasks) - 2

        for task in visible_tasks:
            task_widget = TaskMiniCard(task, self._service)
            task_widget.clicked.connect(self._on_task_clicked)
            self.tasks_layout.addWidget(task_widget)
            self._task_widgets.append(task_widget)

        # Добавляем метку "+N задач" если есть скрытые
        if remaining > 0:
            self._more_label = QLabel(f"+{remaining} задач")
            self._more_label.setStyleSheet("""
                font-size: 10px;
                color: #998664;
                padding: 4px 2px;
                background-color: #F0F0F0;
                border-radius: 4px;
            """)
            self._more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._more_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._more_label.mousePressEvent = self._on_more_label_clicked
            self.tasks_layout.addWidget(self._more_label)

        # Добавляем растяжение в конец
        self.tasks_layout.addStretch()

    def _on_more_label_clicked(self, event) -> None:
        """Обработчик клика по метке +N задач - раскрывает все задачи"""
        if not self._tasks:
            return

        self._all_tasks_visible = True
        self._update_task_display()

    def _update_task_display(self) -> None:
        """Обновляет отображение задач (свёрнуто/развёрнуто)"""
        # Очищаем контейнер
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._task_widgets.clear()

        if self._all_tasks_visible:
            # Показываем все задачи - просто добавляем их без изменения размера карточек
            for task in self._tasks:
                task_widget = TaskMiniCard(task, self._service)
                task_widget.clicked.connect(self._on_task_clicked)
                self.tasks_layout.addWidget(task_widget)
                self._task_widgets.append(task_widget)

            # Добавляем кнопку "Скрыть"
            hide_label = QLabel("▲ Скрыть задачи")
            hide_label.setStyleSheet("""
                font-size: 10px;
                color: #ccab6e;
                padding: 4px 2px;
                background-color: #F5F0EA;
                border-radius: 4px;
            """)
            hide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hide_label.setCursor(Qt.CursorShape.PointingHandCursor)
            hide_label.mousePressEvent = self._on_hide_label_clicked
            self.tasks_layout.addWidget(hide_label)

            # Добавляем растяжение
            self.tasks_layout.addStretch()

            # Увеличиваем размер виджета, чтобы все задачи поместились
            # Расчёт высоты: (количество задач * 28px) + отступы + заголовок
            task_height = len(self._tasks) * 28 + 40
            self.setMinimumHeight(max(120, task_height))
        else:
            # Показываем только 2 задачи
            visible_tasks = self._tasks[:2]
            remaining = len(self._tasks) - 2

            for task in visible_tasks:
                task_widget = TaskMiniCard(task, self._service)
                task_widget.clicked.connect(self._on_task_clicked)
                self.tasks_layout.addWidget(task_widget)
                self._task_widgets.append(task_widget)

            if remaining > 0:
                self._more_label = QLabel(f"+{remaining} задач")
                self._more_label.setStyleSheet("""
                    font-size: 10px;
                    color: #998664;
                    padding: 4px 2px;
                    background-color: #F0F0F0;
                    border-radius: 4px;
                """)
                self._more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._more_label.setCursor(Qt.CursorShape.PointingHandCursor)
                self._more_label.mousePressEvent = self._on_more_label_clicked
                self.tasks_layout.addWidget(self._more_label)

            self.tasks_layout.addStretch()

            # Возвращаем обычный размер
            self.setMinimumHeight(80)

    def _on_hide_label_clicked(self, event) -> None:
        """Обработчик клика по кнопке 'Скрыть задачи'"""
        self._all_tasks_visible = False
        self._update_task_display()

    def _on_task_clicked(self, task_id: int) -> None:
        """Промежуточный обработчик клика по карточке задачи"""
        self.task_clicked.emit(task_id)

    def set_empty(self) -> None:
        """Устанавливает пустой день (другого месяца)"""
        self.day_label.setText("")
        self.setStyleSheet("""
            CalendarDayWidget {
                background-color: #F8F9FA;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
        """)
        # Отключаем сигналы и очищаем задачи
        for widget in self._task_widgets:
            try:
                widget.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            widget.deleteLater()

        self._task_widgets.clear()

        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.setMinimumHeight(80)

    def set_today(self, is_today: bool = True) -> None:
        """Подсвечивает текущий день"""
        self._is_today = is_today
        if is_today:
            self.day_label.setStyleSheet("""
                font-size: 13px;
                font-weight: bold;
                padding: 2px;
                color: #ccab6e;
            """)
            self.setStyleSheet("""
                CalendarDayWidget {
                    background-color: #FFF8F0;
                    border: 2px solid #ccab6e;
                    border-radius: 8px;
                }
                CalendarDayWidget:hover {
                    background-color: #FFF0E0;
                }
            """)


class TaskMiniCard(QFrame):
    """Мини-карточка задачи для отображения в календаре"""

    clicked = pyqtSignal(int)

    def __init__(self, task: TaskGanttData, service: GanttService, parent=None):
        super().__init__(parent)
        self._task = task
        self._service = service

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка UI мини-карточки"""
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(20)
        self.setMaximumHeight(28)

        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 2, 4, 2)

        # Цветовая индикация приоритета
        color_indicator = QLabel()
        color_indicator.setFixedSize(6, 6)
        color_indicator.setStyleSheet(f"""
            background-color: {self._task.color};
            border-radius: 3px;
        """)
        color_indicator.setMinimumWidth(6)

        # Название задачи
        name_label = QLabel(self._task.name)
        name_label.setStyleSheet("""
            font-size: 10px;
            color: #1B232A;
            font-weight: normal;
        """)
        name_label.setWordWrap(False)
        name_label.setMinimumWidth(15)

        # Инициалы исполнителя
        if self._task.executor_initials:
            executor_label = QLabel(self._task.executor_initials)
            executor_label.setStyleSheet("""
                font-size: 8px;
                color: #998664;
                font-weight: bold;
            """)
            executor_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            executor_label.setMinimumWidth(14)
        else:
            executor_label = None

        layout.addWidget(color_indicator)
        layout.addWidget(name_label, 1)
        if executor_label:
            layout.addWidget(executor_label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            TaskMiniCard {
                background-color: #F5F5F5;
                border-radius: 4px;
            }
            TaskMiniCard:hover {
                background-color: #E8E8E8;
            }
        """)

    def mousePressEvent(self, event) -> None:
        """Обработка нажатия на карточку"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._task.id)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """Подсветка при наведении"""
        self.setStyleSheet("""
            TaskMiniCard {
                background-color: #E8E8E8;
                border-radius: 3px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Сброс подсветки"""
        self.setStyleSheet("""
            TaskMiniCard {
                background-color: #F5F5F5;
                border-radius: 3px;
            }
        """)
        super().leaveEvent(event)