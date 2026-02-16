import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from PyQt6.QtWidgets import QGraphicsObject

from PyQt6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsSimpleTextItem,
    QListWidgetItem, QApplication, QMessageBox, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QDateTime, QDate
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QLinearGradient,
    QAction, QWheelEvent, QMouseEvent
)
from PyQt6.uic import loadUi

# Константы для визуализации
PIXELS_PER_DAY = 40  # Базовое значение пикселей на день
TASK_HEIGHT = 28
TASK_VERTICAL_SPACING = 5
HEADER_HEIGHT = 30
ROW_HEIGHT = TASK_HEIGHT + TASK_VERTICAL_SPACING

# Корпоративные цвета
COLOR_PRIMARY = "#D22730"  # Красный - основной акцент
COLOR_ACCENT = "#ccab6e"  # Золотой - прогресс
COLOR_BACKGROUND = "#1B232A"  # Темно-серый фон
COLOR_SECONDARY = "#2C3640"  # Вторичный серый
COLOR_BORDER = "#3A4550"  # Цвет границ
COLOR_COMPLETED = "#2E8B57"  # Зеленый для завершенных
COLOR_OVERDUE = "#8B0000"  # Темно-красный для просроченных
COLOR_TEXT = "#FFFFFF"  # Белый текст


class GanttTask:
    """Модель задачи для диаграммы Ганта"""

    def __init__(self, task_id: int, title: str, start_date: str, end_date: str,
                 progress: int = 0, dependencies: List[int] = None,
                 assignee: str = "", is_critical: bool = False):
        self.id = task_id
        self.title = title
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        self.progress = progress  # 0-100
        self.dependencies = dependencies or []
        self.assignee = assignee
        self.is_critical = is_critical
        self.color = COLOR_PRIMARY

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def is_overdue(self) -> bool:
        return self.end_date < datetime.now().date() and self.progress < 100

    @property
    def is_completed(self) -> bool:
        return self.progress == 100

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start_date.strftime("%Y-%m-%d"),
            "end": self.end_date.strftime("%Y-%m-%d"),
            "progress": self.progress,
            "dependencies": self.dependencies,
            "assignee": self.assignee,
            "is_critical": self.is_critical
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            task_id=data["id"],
            title=data["title"],
            start_date=data["start"],
            end_date=data["end"],
            progress=data.get("progress", 0),
            dependencies=data.get("dependencies", []),
            assignee=data.get("assignee", ""),
            is_critical=data.get("is_critical", False)
        )


from PyQt6.QtWidgets import QGraphicsObject  # Добавьте этот импорт наверху

class GanttTaskItem(QGraphicsObject):
    """Визуальный элемент задачи на диаграмме Ганта"""
    task_moved = pyqtSignal(int, QDate)  # id задачи, новая дата начала

    def __init__(self, task: GanttTask, project_start: datetime.date, y_position: int, parent=None):
        super().__init__(parent)
        self.task = task
        self.project_start = project_start
        self.y_position = y_position
        self.dragging = False
        self.original_pos = None

        # Дочерние элементы
        self.rect_item = QGraphicsRectItem(self)
        self.text_item = QGraphicsSimpleTextItem(task.title, self)
        self.progress_item = None

        # Настройка флагов на родителе (самом GanttTaskItem)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # Инициализация внешнего вида и позиции
        self.update_position()
        self.update_appearance()
        self.update_progress()

        # Текст
        self.text_item.setPos(5, 5)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.text_item.setFont(font)
        self.text_item.setBrush(QBrush(QColor(COLOR_TEXT)))

    def boundingRect(self):
        """Обязательно реализуем для корректной обработки событий"""
        if self.rect_item.rect().isEmpty():
            return QRectF()
        return QRectF(0, 0, self.rect_item.rect().width(), TASK_HEIGHT)

    def paint(self, painter, option, widget=None):
        """Дети рисуют сами — ничего не делаем"""
        pass

    def update_position(self):
        """Обновление позиции и размера"""
        days_from_start = (self.task.start_date - self.project_start).days
        x = days_from_start * PIXELS_PER_DAY
        width = self.task.duration_days * PIXELS_PER_DAY

        # Позиция всего блока
        self.setPos(QPointF(x, self.y_position))
        # Размер основного прямоугольника (относительно 0,0)
        self.rect_item.setRect(QRectF(0, 0, width, TASK_HEIGHT))

        # Обновляем прогресс (чтобы ширина была правильной)
        self.update_progress()

    def update_appearance(self):
        """Внешний вид основного прямоугольника"""
        pen = QPen(QColor(COLOR_BORDER), 1)
        self.rect_item.setPen(pen)

        if self.task.is_completed:
            color = QColor(COLOR_COMPLETED)
        elif self.task.is_overdue:
            color = QColor(COLOR_OVERDUE)
        else:
            color = QColor(self.task.color)

        gradient = QLinearGradient(0, 0, 0, TASK_HEIGHT)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        self.rect_item.setBrush(QBrush(gradient))

    def update_progress(self):
        """Прогресс-бар"""
        if self.progress_item:
            self.progress_item.setParentItem(None)
            self.progress_item = None

        if self.task.progress > 0:
            width = self.rect_item.rect().width() * (self.task.progress / 100)
            if width > 0:
                progress_rect = QRectF(0, 0, width, TASK_HEIGHT)
                self.progress_item = QGraphicsRectItem(progress_rect, self)
                progress_color = QColor(COLOR_ACCENT)
                progress_color.setAlpha(180)
                self.progress_item.setBrush(QBrush(progress_color))
                self.progress_item.setPen(QPen(Qt.PenStyle.NoPen))

    def hoverEnterEvent(self, event):
        self.setOpacity(0.9)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setOpacity(1.0)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.original_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            if self.original_pos and self.pos() != self.original_pos:
                delta_days = int(round(self.pos().x() / PIXELS_PER_DAY))
                new_start = self.project_start + timedelta(days=delta_days)
                self.task_moved.emit(self.task.id, QDate(new_start))
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = value
            new_pos.setY(self.y_position)  # Запрет вертикального перемещения
            return new_pos
        return super().itemChange(change, value)


class GanttDependencyItem(QGraphicsLineItem):
    """Линия зависимости между задачами"""

    def __init__(self, from_item: GanttTaskItem, to_item: GanttTaskItem, parent=None):
        super().__init__(parent)
        self.from_item = from_item
        self.to_item = to_item
        self.update_position()

        # Настройка внешнего вида
        pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.DashLine)
        pen.setDashPattern([5, 3])
        self.setPen(pen)

    def update_position(self):
        """Обновление позиции линии"""
        if not self.from_item or not self.to_item:
            return

        # Позиция правого края исходной задачи
        start_x = self.from_item.pos().x() + self.from_item.rect_item.rect().width()
        start_y = self.from_item.pos().y() + TASK_HEIGHT / 2

        # Позиция левого края целевой задачи
        end_x = self.to_item.pos().x()
        end_y = self.to_item.pos().y() + TASK_HEIGHT / 2

        self.setLine(start_x, start_y, end_x, end_y)

    def mousePressEvent(self, event):
        """Обработка нажатия мыши на сцене"""
        item = self.itemAt(event.scenePos(), QPainter())
        # Ищем родителя типа GanttTaskItem
        while item and not isinstance(item, GanttTaskItem):
            item = item.parentItem()
        if item:
            self.task_selected.emit(item.task.id)
        super().mousePressEvent(event)

class GanttHeaderItem(QGraphicsRectItem):
    """Заголовок диаграммы с датами"""

    def __init__(self, project_start: datetime.date, project_end: datetime.date, width: int, parent=None):
        super().__init__(parent)
        self.project_start = project_start
        self.project_end = project_end
        self.total_days = (project_end - project_start).days + 1

        # Настройка заголовка
        self.setRect(0, 0, width * PIXELS_PER_DAY, HEADER_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_SECONDARY)))
        self.setPen(QPen(QColor(COLOR_BORDER), 1))

        # Добавление меток дат
        self.add_date_labels()

    def add_date_labels(self):
        """Добавление меток дат на заголовок"""
        for i in range(self.total_days):
            current_date = self.project_start + timedelta(days=i)
            x = i * PIXELS_PER_DAY

            # Добавление разделительной линии
            if i > 0:
                line = QGraphicsLineItem(x, 0, x, HEADER_HEIGHT, self)
                line.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.PenStyle.DotLine))

            # Добавление текста с датой (каждый 5-й день или первый)
            if i % 5 == 0 or i == self.total_days - 1:
                date_text = QGraphicsSimpleTextItem(
                    current_date.strftime("%d.%m"), self
                )
                date_text.setPos(x + 2, 5)
                font = QFont("Segoe UI", 8)
                date_text.setFont(font)
                date_text.setBrush(QBrush(QColor(COLOR_TEXT)))

                # Добавление дня недели
                day_text = QGraphicsSimpleTextItem(
                    current_date.strftime("%a"), self
                )
                day_text.setPos(x + 2, 16)
                font = QFont("Segoe UI", 7)
                day_text.setFont(font)
                day_text.setBrush(QBrush(QColor(COLOR_ACCENT)))


class GanttScene(QGraphicsScene):
    """Сцена для диаграммы Ганта"""

    task_selected = pyqtSignal(int)
    task_moved = pyqtSignal(int, QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_start = datetime.now().date()
        self.project_end = self.project_start + timedelta(days=30)
        self.tasks: List[GanttTask] = []
        self.task_items: Dict[int, GanttTaskItem] = {}
        self.dependency_items: List[GanttDependencyItem] = []
        self.header = None
        self.setBackgroundBrush(QBrush(QColor(COLOR_BACKGROUND)))

    def set_project_dates(self, start_date: datetime.date, end_date: datetime.date):
        """Установка дат проекта"""
        self.project_start = start_date
        self.project_end = end_date
        self.update_scene()

    def set_tasks(self, tasks: List[GanttTask]):
        """Установка списка задач"""
        self.tasks = tasks
        self.update_scene()

    def update_scene(self):
        """Обновление всей сцены"""
        self.clear()
        self.task_items.clear()
        self.dependency_items.clear()

        if not self.tasks:
            return

        # Сортировка задач по дате начала
        sorted_tasks = sorted(self.tasks, key=lambda t: (t.start_date, t.id))

        # Создание заголовка
        total_days = (self.project_end - self.project_start).days + 1
        self.header = GanttHeaderItem(
            self.project_start, self.project_end, total_days
        )
        self.addItem(self.header)

        # Создание элементов задач
        for i, task in enumerate(sorted_tasks):
            y_pos = HEADER_HEIGHT + i * ROW_HEIGHT
            task_item = GanttTaskItem(task, self.project_start, y_pos)
            task_item.task_moved.connect(self.on_task_moved)
            self.addItem(task_item)
            self.task_items[task.id] = task_item

        # Создание зависимостей
        for task in self.tasks:
            from_item = self.task_items.get(task.id)
            if from_item and task.dependencies:
                for dep_id in task.dependencies:
                    to_item = self.task_items.get(dep_id)
                    if to_item:
                        dep_item = GanttDependencyItem(from_item, to_item)
                        self.addItem(dep_item)
                        self.dependency_items.append(dep_item)

        # Установка размера сцены
        scene_width = total_days * PIXELS_PER_DAY + 100
        scene_height = HEADER_HEIGHT + len(self.tasks) * ROW_HEIGHT + 50
        self.setSceneRect(0, 0, scene_width, scene_height)

    def on_task_moved(self, task_id: int, new_start: QDate):
        """Обработка перемещения задачи"""
        if task_id in self.task_items:
            task_item = self.task_items[task_id]
            task = task_item.task

            # Преобразование QDate в datetime.date
            new_start_date = datetime(new_start.year(), new_start.month(), new_start.day()).date()

            # Проверка зависимостей
            can_move = True
            for dep_id in task.dependencies:
                if dep_id in self.task_items:
                    dep_task = self.task_items[dep_id].task
                    if new_start_date < dep_task.end_date:
                        can_move = False
                        QMessageBox.warning(
                            None, "Ошибка",
                            f"Нельзя переместить задачу. Она зависит от задачи '{dep_task.title}'"
                        )
                        break

            if can_move:
                # Обновление дат задачи
                duration = task.duration_days
                task.start_date = new_start_date
                task.end_date = new_start_date + timedelta(days=duration - 1)

                # Обновление позиции
                task_item.update_position()

                # Обновление зависимостей
                self.update_dependencies()

                # Сигнал о перемещении
                self.task_moved.emit(task_id, QDate(task.start_date))

    def update_dependencies(self):
        """Обновление линий зависимостей"""
        for dep_item in self.dependency_items:
            dep_item.update_position()

    def mousePressEvent(self, event):
        """Обработка нажатия мыши на сцене"""
        item = self.itemAt(event.scenePos(), QPainter())
        if isinstance(item, GanttTaskItem):
            self.task_selected.emit(item.task.id)
        super().mousePressEvent(event)


class GanttChartWidget(QWidget):
    """Основной виджет диаграммы Ганта"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "gantt_chart.ui"), self)

        # Инициализация сцены и вида
        self.scene = GanttScene(self)
        self.ganttView.setScene(self.scene)
        self.ganttView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.ganttView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ganttView.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Подключение сигналов
        self.connect_signals()

        # Загрузка тестовых данных
        self.load_test_data()

        # Обновление статистики
        self.update_statistics()

    def connect_signals(self):
        """Подключение сигналов к слотам"""
        self.btnZoomIn.clicked.connect(self.zoom_in)
        self.btnZoomOut.clicked.connect(self.zoom_out)
        self.btnRefresh.clicked.connect(self.refresh_chart)
        self.btnAddTask.clicked.connect(self.add_task_dialog)
        self.projectCombo.currentIndexChanged.connect(self.on_project_changed)
        self.scaleCombo.currentIndexChanged.connect(self.on_scale_changed)
        self.searchTasks.textChanged.connect(self.filter_tasks)
        self.filterMyTasks.toggled.connect(self.apply_filters)
        self.filterOverdue.toggled.connect(self.apply_filters)
        self.filterInProgress.toggled.connect(self.apply_filters)
        self.filterCompleted.toggled.connect(self.apply_filters)
        self.scene.task_moved.connect(self.on_task_moved)

    def load_test_data(self):
        """Загрузка тестовых данных для демонстрации"""
        tasks_data = [
            {
                "id": 1,
                "title": "Проектирование архитектуры",
                "start": "2026-02-01",
                "end": "2026-02-05",
                "progress": 100,
                "assignee": "Иванов И.И.",
                "is_critical": True
            },
            {
                "id": 2,
                "title": "Проектирование UI/UX",
                "start": "2026-02-01",
                "end": "2026-02-07",
                "progress": 100,
                "assignee": "Петрова А.С.",
                "dependencies": [1]
            },
            {
                "id": 3,
                "title": "Разработка бэкенда",
                "start": "2026-02-06",
                "end": "2026-02-15",
                "progress": 75,
                "assignee": "Сидоров П.В.",
                "dependencies": [1],
                "is_critical": True
            },
            {
                "id": 4,
                "title": "Разработка фронтенда",
                "start": "2026-02-08",
                "end": "2026-02-18",
                "progress": 60,
                "assignee": "Козлова Е.Н.",
                "dependencies": [2, 3]
            },
            {
                "id": 5,
                "title": "Тестирование",
                "start": "2026-02-16",
                "end": "2026-02-22",
                "progress": 30,
                "assignee": "Морозов Д.В.",
                "dependencies": [3, 4]
            },
            {
                "id": 6,
                "title": "Документация",
                "start": "2026-02-10",
                "end": "2026-02-20",
                "progress": 20,
                "assignee": "Волкова М.И.",
                "dependencies": [2]
            },
            {
                "id": 7,
                "title": "Деплой",
                "start": "2026-02-23",
                "end": "2026-02-25",
                "progress": 0,
                "assignee": "Соколов А.А.",
                "dependencies": [5, 6],
                "is_critical": True
            }
        ]

        tasks = [GanttTask.from_dict(data) for data in tasks_data]
        self.scene.set_tasks(tasks)

        # Обновление списка задач
        self.update_task_list(tasks)

        # Обновление дат проекта
        project_start = min(t.start_date for t in tasks)
        project_end = max(t.end_date for t in tasks)
        self.scene.set_project_dates(project_start, project_end)

        # Обновление дат в статусной строке
        self.dateRangeLabel.setText(
            f"{project_start.strftime('%d.%m.%Y')} - {project_end.strftime('%d.%m.%Y')}"
        )

    def update_task_list(self, tasks: List[GanttTask]):
        """Обновление списка задач слева"""
        self.taskList.clear()

        for task in sorted(tasks, key=lambda t: t.start_date):
            item_text = f"{task.title}\n"
            item_text += f"  📅 {task.start_date.strftime('%d.%m')} - {task.end_date.strftime('%d.%m')}\n"
            item_text += f"  👤 {task.assignee}  📊 {task.progress}%"

            item = QListWidgetItem(item_text)

            # Установка цвета в зависимости от состояния
            if task.is_completed:
                item.setForeground(QColor(COLOR_COMPLETED))
            elif task.is_overdue:
                item.setForeground(QColor(COLOR_OVERDUE))
            elif task.is_critical:
                item.setForeground(QColor(COLOR_PRIMARY))
            else:
                item.setForeground(QColor(COLOR_TEXT))

            item.setData(Qt.ItemDataRole.UserRole, task.id)
            self.taskList.addItem(item)

    def update_statistics(self):
        """Обновление статистики в статусной строке"""
        tasks = self.scene.tasks
        if not tasks:
            self.statusLabel.setText("Нет задач")
            return

        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        in_progress = sum(1 for t in tasks if not t.is_completed and not t.is_overdue)
        overdue = sum(1 for t in tasks if t.is_overdue)

        self.statusLabel.setText(
            f"✅ Завершено: {completed} | "
            f"🔄 В работе: {in_progress} | "
            f"⚠️ Просрочено: {overdue} | "
            f"📊 Всего: {total}"
        )

    def zoom_in(self):
        """Увеличение масштаба"""
        global PIXELS_PER_DAY
        if PIXELS_PER_DAY < 80:
            PIXELS_PER_DAY += 5
            self.refresh_chart()

    def zoom_out(self):
        """Уменьшение масштаба"""
        global PIXELS_PER_DAY
        if PIXELS_PER_DAY > 20:
            PIXELS_PER_DAY -= 5
            self.refresh_chart()

    def refresh_chart(self):
        """Обновление диаграммы"""
        self.scene.update_scene()
        self.update_statistics()

    def on_project_changed(self, index: int):
        """Обработка смены проекта"""
        # Здесь должна быть загрузка данных выбранного проекта
        print(f"Проект изменен: {self.projectCombo.currentText()}")
        self.load_test_data()  # Временное решение

    def on_scale_changed(self, index: int):
        """Обработка смены масштаба"""
        scale_text = self.scaleCombo.currentText()
        global PIXELS_PER_DAY

        if scale_text == "Дни":
            PIXELS_PER_DAY = 40
        elif scale_text == "Недели":
            PIXELS_PER_DAY = 20
        elif scale_text == "Месяцы":
            PIXELS_PER_DAY = 10

        self.refresh_chart()

    def filter_tasks(self, text: str):
        """Фильтрация задач по тексту"""
        for i in range(self.taskList.count()):
            item = self.taskList.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def apply_filters(self):
        """Применение фильтров к задачам"""
        show_my_tasks = self.filterMyTasks.isChecked()
        show_overdue = self.filterOverdue.isChecked()
        show_in_progress = self.filterInProgress.isChecked()
        show_completed = self.filterCompleted.isChecked()

        # Если все фильтры сняты, показываем все
        if not any([show_overdue, show_in_progress, show_completed]):
            show_overdue = show_in_progress = show_completed = True

        tasks = self.scene.tasks
        for i in range(self.taskList.count()):
            item = self.taskList.item(i)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            task = next((t for t in tasks if t.id == task_id), None)

            if task:
                visible = True
                if show_my_tasks and task.assignee != "Иванов И.И.":  # Пример проверки
                    visible = False
                if show_overdue and not task.is_overdue:
                    visible = False
                if show_in_progress and (task.is_completed or task.is_overdue):
                    visible = False
                if show_completed and not task.is_completed:
                    visible = False

                item.setHidden(not visible)

    def add_task_dialog(self):
        """Диалог добавления новой задачи"""
        # Здесь должен быть полноценный диалог, но для демо упростим
        title, ok = QInputDialog.getText(self, "Новая задача", "Название задачи:")
        if ok and title:
            # Создание новой задачи
            new_id = max([t.id for t in self.scene.tasks], default=0) + 1
            start_date = datetime.now().date().strftime("%Y-%m-%d")
            end_date = (datetime.now().date() + timedelta(days=7)).strftime("%Y-%m-%d")

            new_task = GanttTask(
                task_id=new_id,
                title=title,
                start_date=start_date,
                end_date=end_date,
                progress=0,
                assignee="Новый исполнитель"
            )

            # Добавление задачи
            self.scene.tasks.append(new_task)
            self.refresh_chart()
            self.update_task_list(self.scene.tasks)

            QMessageBox.information(self, "Успех", f"Задача '{title}' создана!")

    def on_task_moved(self, task_id: int, new_start: QDate):
        """Обработка перемещения задачи на диаграмме"""
        print(f"Задача {task_id} перемещена на {new_start.toString('dd.MM.yyyy')}")
        self.update_statistics()

    def wheelEvent(self, event: QWheelEvent):
        """Обработка колесика мыши для масштабирования"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


def main():
    """Точка входа для тестирования виджета"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    widget = GanttChartWidget()
    widget.show()
    widget.resize(1400, 900)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()