import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsItem, QGraphicsLineItem, QGraphicsSimpleTextItem,
    QApplication, QMessageBox, QInputDialog, QTreeWidgetItem, QTreeWidget
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QLinearGradient, QWheelEvent
)

from database import get_tasks_session
from models.tasks import Task
from models.projects import Project, EmployeeProject
from models.employees import Employee

# Константы
PIXELS_PER_DAY = 40
TASK_HEIGHT = 28
TASK_VERTICAL_SPACING = 5
HEADER_HEIGHT = 50
ROW_HEIGHT = TASK_HEIGHT + TASK_VERTICAL_SPACING

# Цвета
COLOR_PRIMARY = "#D22730"
COLOR_ACCENT = "#ccab6e"
COLOR_BACKGROUND = "#1B232A"
COLOR_SECONDARY = "#2C3640"
COLOR_BORDER = "#3A4550"
COLOR_COMPLETED = "#2E8B57"
COLOR_OVERDUE = "#8B0000"
COLOR_TEXT = "#FFFFFF"
TODAY_COLOR = "#ccab6e"

TODAY = datetime.now().date()


class GanttTask:
    def __init__(self, task_id: int, title: str, start_date: str, end_date: str,
                 assignee: str = "", is_critical: bool = False, children=None,
                 project_id: int = None, status: str = "", is_completed: bool = False):
        self.id = task_id
        self.title = title
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date,
                                                                                         str) else start_date
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
        self.assignee = assignee
        self.is_critical = is_critical
        self.dependencies = []
        self.children = children or []
        self.color = COLOR_PRIMARY
        self.project_id = project_id
        self.status = status
        self._is_completed = is_completed or (self.end_date < TODAY)

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def is_overdue(self) -> bool:
        return self.end_date < TODAY and not self._is_completed

    @property
    def is_completed(self) -> bool:
        return self._is_completed or (self.end_date < TODAY)


class GanttHeaderItem(QGraphicsRectItem):
    def __init__(self, project_start: datetime.date, project_end: datetime.date, total_days: int):
        super().__init__(0, 0, total_days * PIXELS_PER_DAY, HEADER_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_SECONDARY)))
        self.setPen(QPen(QColor(COLOR_BORDER), 1))
        self.add_date_labels(project_start, total_days)

    def add_date_labels(self, project_start: datetime.date, total_days: int):
        for i in range(total_days):
            current_date = project_start + timedelta(days=i)
            x = i * PIXELS_PER_DAY
            if i > 0:
                line = QGraphicsLineItem(x, 0, x, HEADER_HEIGHT, self)
                line.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.PenStyle.DotLine))
            if i % 5 == 0 or i == total_days - 1:
                date_text = QGraphicsSimpleTextItem(current_date.strftime("%d.%m"), self)
                date_text.setPos(x + 2, 5)
                date_text.setFont(QFont("Segoe UI", 8))
                date_text.setBrush(QBrush(QColor(COLOR_TEXT)))
                day_text = QGraphicsSimpleTextItem(current_date.strftime("%a"), self)
                day_text.setPos(x + 2, 25)
                day_text.setFont(QFont("Segoe UI", 7))
                day_text.setBrush(QBrush(QColor(COLOR_ACCENT)))


class GanttResizeHandle(QGraphicsRectItem):
    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self.side = side
        self.setRect(0, 0, 12, TASK_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_ACCENT)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setOpacity(0.7)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def hoverEnterEvent(self, event):
        self.setOpacity(1.0)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setOpacity(0.7)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentItem()
            parent.old_start = parent.task.start_date
            parent.old_end = parent.task.end_date
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            parent = self.parentItem()
            width = parent.rect_item.rect().width()
            target_x = width - 12 if self.side == 'right' else 0
            delta = value.x() - target_x
            delta_days = round(delta / PIXELS_PER_DAY)
            new_duration = parent.task.duration_days + (delta_days if self.side == 'right' else -delta_days)
            if new_duration < 1:
                return QPointF(target_x, 0)
            if self.side == 'right':
                parent.task.end_date = parent.task.start_date + timedelta(days=new_duration - 1)
            else:
                parent.task.start_date = parent.task.end_date - timedelta(days=new_duration - 1)
            parent.update_position()
            value.setX(target_x)
            return value
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        parent = self.parentItem()
        if hasattr(parent, 'old_start'):
            parent.scene().task_changed.emit(parent.task.id)


class GanttTaskItem(QGraphicsItem):
    def __init__(self, task: GanttTask, project_start: datetime.date, y_position: float):
        super().__init__()
        self.task = task
        self.project_start = project_start
        self.y_position = y_position
        self._updating_position = False

        self.rect_item = QGraphicsRectItem(self)
        self.text_item = QGraphicsSimpleTextItem(task.title, self)

        self.left_handle = GanttResizeHandle('left', self)
        self.right_handle = GanttResizeHandle('right', self)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self.update_position()
        self.update_appearance()

        self.text_item.setPos(5, 4)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.text_item.setFont(font)
        self.text_item.setBrush(QBrush(QColor(COLOR_TEXT)))

    def update_position(self):
        if self._updating_position:
            return
        self._updating_position = True

        days_from_start = (self.task.start_date - self.project_start).days
        x = days_from_start * PIXELS_PER_DAY
        width = self.task.duration_days * PIXELS_PER_DAY
        self.setPos(QPointF(x, self.y_position))
        self.rect_item.setRect(0, 0, width, TASK_HEIGHT)
        self.left_handle.setPos(0, 0)
        self.right_handle.setPos(width - 12, 0)

        self._updating_position = False

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._updating_position:
                return value

            new_pos = value
            snapped_x = round(new_pos.x() / PIXELS_PER_DAY) * PIXELS_PER_DAY
            delta_days = round((new_pos.x() - self.pos().x()) / PIXELS_PER_DAY)
            new_start = self.task.start_date + timedelta(days=delta_days)
            self.task.start_date = new_start
            self.task.end_date = new_start + timedelta(days=self.task.duration_days - 1)

            self.update_position()
            new_pos.setX(snapped_x)
            new_pos.setY(self.y_position)
            return new_pos
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if hasattr(self, 'old_start'):
            self.scene().task_changed.emit(self.task.id)
            del self.old_start
            del self.old_end

    def boundingRect(self):
        return QRectF(0, 0, max(1, self.rect_item.rect().width()), TASK_HEIGHT)

    def paint(self, painter, option, widget=None):
        pass

    def update_appearance(self):
        pen = QPen(QColor(COLOR_BORDER), 1)
        self.rect_item.setPen(pen)
        color = QColor(COLOR_COMPLETED) if self.task.is_completed else QColor(
            COLOR_OVERDUE) if self.task.is_overdue else QColor(self.task.color)
        gradient = QLinearGradient(0, 0, 0, TASK_HEIGHT)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        self.rect_item.setBrush(QBrush(gradient))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_start = self.task.start_date
            self.old_end = self.task.end_date
        super().mousePressEvent(event)


class GanttDependencyItem(QGraphicsLineItem):
    def __init__(self, from_item: GanttTaskItem, to_item: GanttTaskItem, lag: int):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.lag = lag
        self.original_pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.DashLine)
        self.original_pen.setDashPattern([5, 3])
        self.setPen(self.original_pen)
        self.setAcceptHoverEvents(True)
        self.update_position()

    def update_position(self):
        if not self.from_item or not self.to_item:
            return
        start_x = self.from_item.pos().x() + self.from_item.rect_item.rect().width()
        start_y = self.from_item.pos().y() + TASK_HEIGHT / 2
        end_x = self.to_item.pos().x()
        end_y = self.to_item.pos().y() + TASK_HEIGHT / 2
        self.setLine(start_x, start_y, end_x, end_y)

    def hoverEnterEvent(self, event):
        self.setPen(QPen(QColor("red"), 3, Qt.PenStyle.DashLine))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self.original_pen)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            reply = QMessageBox.question(None, "Удалить связь", "Удалить эту зависимость?")
            if reply == QMessageBox.StandardButton.Yes:
                successor = self.to_item.task
                successor.dependencies = [d for d in successor.dependencies if
                                          not (d['id'] == self.from_item.task.id and d.get('lag', 0) == self.lag)]
                self.scene().widget.refresh_chart()
        super().mousePressEvent(event)


class GanttScene(QGraphicsScene):
    task_changed = pyqtSignal(int)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.project_start = TODAY
        self.project_end = TODAY + timedelta(days=30)
        self.tasks: List[GanttTask] = []
        self.all_tasks_dict: Dict[int, GanttTask] = {}
        self.successors = defaultdict(list)
        self.task_items: Dict[int, GanttTaskItem] = {}
        self.dependency_items: List[GanttDependencyItem] = []
        self.tree_items: Dict[int, QTreeWidgetItem] = {}
        self.setBackgroundBrush(QBrush(QColor(COLOR_BACKGROUND)))

    def collect_tasks(self):
        self.all_tasks_dict = {}

        def collect(t):
            self.all_tasks_dict[t.id] = t
            for child in t.children:
                collect(child)

        for root in self.tasks:
            collect(root)

    def build_successors(self):
        self.successors.clear()
        for task in self.all_tasks_dict.values():
            for dep in task.dependencies:
                self.successors[dep['id']].append((task.id, dep.get('lag', 0)))

    def get_earliest_start(self, task: GanttTask) -> datetime.date:
        earliest = self.project_start
        for dep in task.dependencies:
            pred = self.all_tasks_dict.get(dep['id'])
            if pred:
                candidate = pred.end_date + timedelta(days=dep.get('lag', 0) + 1)
                if candidate > earliest:
                    earliest = candidate
        return earliest

    def propagate_delay(self, task_id: int):
        task = self.all_tasks_dict[task_id]
        for succ_id, lag in self.successors[task_id]:
            succ = self.all_tasks_dict[succ_id]
            min_start = task.end_date + timedelta(days=lag + 1)
            if succ.start_date < min_start:
                duration = succ.duration_days
                succ.start_date = min_start
                succ.end_date = min_start + timedelta(days=duration - 1)
                item = self.task_items.get(succ_id)
                if item:
                    item.update_position()
                self.propagate_delay(succ_id)

    def validate_change(self, task_id: int):
        item = self.task_items.get(task_id)
        if not item or not hasattr(item, 'old_start'):
            return
        task = item.task
        if self.widget.autoPlanningCheck.isChecked():
            earliest = self.get_earliest_start(task)
            if task.start_date < earliest:
                QMessageBox.warning(None, "Ошибка", "Нарушение зависимости — изменение запрещено")
                task.start_date = item.old_start
                task.end_date = item.old_end
                item.update_position()
                del item.old_start
                del item.old_end
                self.update_dependencies()
                return
        self.propagate_delay(task_id)
        if hasattr(item, 'old_start'):
            del item.old_start
            del item.old_end
        self.update_dependencies()

    def update_dependencies(self):
        for dep in self.dependency_items:
            dep.update_position()

    def update_scene(self):
        self.clear()
        self.task_items.clear()
        self.dependency_items.clear()

        self.collect_tasks()
        self.build_successors()

        total_days = (self.project_end - self.project_start).days + 1
        header = GanttHeaderItem(self.project_start, self.project_end, total_days)
        self.addItem(header)

        y = HEADER_HEIGHT

        def add_task(task):
            nonlocal y
            item = GanttTaskItem(task, self.project_start, y)
            self.addItem(item)
            self.task_items[task.id] = item
            y += ROW_HEIGHT
            tree_item = self.tree_items.get(task.id)
            if tree_item and tree_item.isExpanded():
                for child in task.children:
                    add_task(child)

        for root in self.tasks:
            add_task(root)

        for task in self.all_tasks_dict.values():
            for dep in task.dependencies:
                pred_item = self.task_items.get(dep['id'])
                succ_item = self.task_items.get(task.id)
                if pred_item and succ_item:
                    dep_item = GanttDependencyItem(pred_item, succ_item, dep.get('lag', 0))
                    self.addItem(dep_item)
                    self.dependency_items.append(dep_item)

        if self.project_start <= TODAY <= self.project_end:
            days = (TODAY - self.project_start).days
            x = days * PIXELS_PER_DAY
            line = QGraphicsLineItem(x, 0, x, y)
            line.setPen(QPen(QColor(TODAY_COLOR), 2, Qt.PenStyle.DashLine))
            line.setZValue(10)
            self.addItem(line)
            text = QGraphicsSimpleTextItem("Сегодня")
            text.setPos(x + 5, 5)
            text.setBrush(QBrush(QColor(TODAY_COLOR)))
            text.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            text.setZValue(10)
            self.addItem(text)

        self.setSceneRect(0, 0, total_days * PIXELS_PER_DAY + 500, y + 100)


class GanttChartWidget(QWidget):
    def __init__(self, service=None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "gantt"
        )
        uic.loadUi(os.path.join(ui_path, "gantt_chart.ui"), self)

        self.service = service
        self.session = get_tasks_session()

        self.scene = GanttScene(self)
        self.ganttView.setScene(self.scene)
        self.ganttView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.ganttView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.linking_mode = False
        self.pending_pred = None
        self.ganttView.viewport().installEventFilter(self)
        self.connect_signals()

        # Загружаем реальные данные
        self.load_real_data()

    def load_real_data(self):
        """Загрузка реальных данных из БД"""
        try:
            # Получаем все проекты
            projects = self.session.query(Project).filter(Project.is_archived == False).all()

            if not projects:
                print("⚠️ Нет активных проектов для отображения на диаграмме Ганта")
                self.load_test_data()
                return

            # Берем первый проект (или можно сделать выбор проекта)
            project = projects[0]
            print(f"📊 Загружаем задачи для проекта: {project.name}")

            # Получаем все задачи проекта
            tasks = self.session.query(Task).filter(Task.project_id == project.id).all()

            if not tasks:
                print(f"⚠️ В проекте {project.name} нет задач")
                self.load_test_data()
                return

            gantt_tasks = []
            task_dict = {}

            for task in tasks:
                # Получаем исполнителя
                assignee_name = ""
                if task.assigned_to:
                    employee = self.session.query(Employee).filter(  # ← ИСПРАВЛЕНО
                        Employee.id == task.assigned_to
                    ).first()
                    if employee:
                        assignee_name = f"{employee.last_name} {employee.first_name[0] if employee.first_name else ''}."

                # Определяем статус выполнения
                is_completed = False
                if task.column and task.column.is_done_column:
                    is_completed = True

                # Определяем даты
                start_date = task.created_at.date() if task.created_at else TODAY
                end_date = task.deadline.date() if task.deadline else start_date + timedelta(days=7)

                gantt_task = GanttTask(
                    task_id=task.id,
                    title=task.title,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    assignee=assignee_name,
                    is_critical=task.priority in ["high", "critical"] if hasattr(task.priority, 'value') else task.priority in ["high", "critical"],
                    project_id=task.project_id,
                    status=task.column.name if task.column else "unknown",
                    is_completed=is_completed
                )
                gantt_tasks.append(gantt_task)
                task_dict[task.id] = gantt_task

            # Строим иерархию (если нужна)
            self.scene.tasks = gantt_tasks
            self.scene.collect_tasks()

            # Рассчитываем границы проекта
            if gantt_tasks:
                start = min(t.start_date for t in self.scene.all_tasks_dict.values())
                end = max(t.end_date for t in self.scene.all_tasks_dict.values())
                self.scene.project_start = start
                self.scene.project_end = end
                self.dateRangeLabel.setText(f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}")
            else:
                self.scene.project_start = TODAY
                self.scene.project_end = TODAY + timedelta(days=30)
                self.dateRangeLabel.setText(
                    f"{TODAY.strftime('%d.%m.%Y')} - {(TODAY + timedelta(days=30)).strftime('%d.%m.%Y')}")

            self.update_task_tree()
            self.scene.update_scene()
            self.update_statistics()
            print(f"✅ Загружено {len(gantt_tasks)} задач для диаграммы Ганта")

        except Exception as e:
            print(f"❌ Ошибка при загрузке данных для Ганта: {e}")
            import traceback
            traceback.print_exc()
            self.load_test_data()

    def connect_signals(self):
        self.btnZoomIn.clicked.connect(self.zoom_in)
        self.btnZoomOut.clicked.connect(self.zoom_out)
        self.btnRefresh.clicked.connect(self.refresh_chart)
        self.btnAddTask.clicked.connect(self.add_task_dialog)
        self.scaleCombo.currentIndexChanged.connect(self.on_scale_changed)
        self.btnToday.clicked.connect(self.center_on_today)
        self.btnCreateLink.clicked.connect(self.toggle_linking_mode)
        self.autoPlanningCheck.toggled.connect(self.refresh_chart)
        self.taskList.expanded.connect(self.refresh_chart)
        self.taskList.collapsed.connect(self.refresh_chart)
        self.scene.task_changed.connect(self.scene.validate_change)

    def eventFilter(self, obj, event):
        if obj == self.ganttView.viewport() and event.type() == QEvent.Type.MouseButtonPress and self.linking_mode:
            pos = self.ganttView.mapToScene(event.pos())
            item = self.scene.itemAt(pos, self.ganttView.transform())

            while item and not isinstance(item, GanttTaskItem):
                item = item.parentItem()
            if isinstance(item, GanttTaskItem):
                if self.pending_pred is None:
                    self.pending_pred = item.task.id
                    QMessageBox.information(self, "Связь", f"Выбрана предыдущая задача: {item.task.title}")
                else:
                    lag, ok = QInputDialog.getInt(self, "Лаг", "Задержка (дней):", 0, 0, 30)
                    if ok:
                        successor = item.task
                        successor.dependencies.append({'id': self.pending_pred, 'lag': lag})
                        self.refresh_chart()
                    self.pending_pred = None
                    self.toggle_linking_mode()
            return True
        return super().eventFilter(obj, event)

    def toggle_linking_mode(self):
        self.linking_mode = not self.linking_mode
        self.btnCreateLink.setText("Отмена" if self.linking_mode else "Создать связь")
        cursor = Qt.CursorShape.PointingHandCursor if self.linking_mode else Qt.CursorShape.ArrowCursor
        self.ganttView.viewport().setCursor(cursor)

    def center_on_today(self):
        days = (TODAY - self.scene.project_start).days
        x = days * PIXELS_PER_DAY
        self.ganttView.centerOn(x, self.ganttView.height() / 2)

    def load_test_data(self):
        """Тестовые данные для демонстрации"""
        task1 = GanttTask(1, "Проектирование архитектуры", "2026-02-01", "2026-02-05", "Иванов И.И.", True)
        task2 = GanttTask(2, "Проектирование UI/UX", "2026-02-01", "2026-02-10", "Петрова А.С.")
        sub1 = GanttTask(31, "Backend API", "2026-02-06", "2026-02-12", "Сидоров П.В.")
        sub2 = GanttTask(32, "Интеграция БД", "2026-02-13", "2026-02-18", "Сидоров П.В.")
        task3 = GanttTask(3, "Разработка бэкенда", "2026-02-06", "2026-02-18", "Сидоров П.В.", True)
        task3.children = [sub1, sub2]
        task3.dependencies = [{'id': 1, 'lag': 0}]
        task4 = GanttTask(4, "Разработка фронтенда", "2026-02-11", "2026-02-22", "Козлова Е.Н.")
        task4.dependencies = [{'id': 2, 'lag': 0}, {'id': 3, 'lag': 2}]
        task5 = GanttTask(5, "Тестирование", "2026-02-23", "2026-02-28", "Морозов Д.В.")
        task5.dependencies = [{'id': 4, 'lag': 0}]
        self.scene.tasks = [task1, task2, task3, task4, task5]
        self.scene.collect_tasks()
        self.update_task_tree()
        start = min(t.start_date for t in self.scene.all_tasks_dict.values())
        end = max(t.end_date for t in self.scene.all_tasks_dict.values())
        self.scene.project_start = start
        self.scene.project_end = end
        self.dateRangeLabel.setText(f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}")
        self.scene.update_scene()
        self.update_statistics()

    def update_task_tree(self):
        self.taskList.blockSignals(True)
        self.taskList.clear()
        self.scene.tree_items.clear()

        def add_item(task, parent_item=None):
            status_emoji = "✅" if task.is_completed else "⚠️" if task.is_overdue else "🔄"
            date_str = f"{task.start_date.strftime('%d.%m')}–{task.end_date.strftime('%d.%m')}"
            text = f"{status_emoji} {task.title} | {date_str} | {task.assignee}"
            item = QTreeWidgetItem()
            item.setText(0, text)
            item.setData(0, Qt.ItemDataRole.UserRole, task.id)
            self.scene.tree_items[task.id] = item
            if parent_item is None:
                self.taskList.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            item.setExpanded(True)
            for child in task.children:
                add_item(child, item)

        for task in self.scene.tasks:
            add_item(task)

        self.taskList.blockSignals(False)

    def refresh_chart(self):
        self.scene.update_scene()
        self.update_task_tree()
        self.update_statistics()

    def update_statistics(self):
        total = len(self.scene.all_tasks_dict)
        completed = sum(1 for t in self.scene.all_tasks_dict.values() if t.is_completed)
        overdue = sum(1 for t in self.scene.all_tasks_dict.values() if t.is_overdue)
        self.statusLabel.setText(f"✅ Завершено: {completed} | ⚠️ Просрочено: {overdue} | 📊 Всего: {total}")

    def zoom_in(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = min(80, PIXELS_PER_DAY + 10)
        self.refresh_chart()

    def zoom_out(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = max(15, PIXELS_PER_DAY - 10)
        self.refresh_chart()

    def on_scale_changed(self, index):
        global PIXELS_PER_DAY
        text = self.scaleCombo.currentText()
        scale_map = {"Дни": 40, "Недели": 20, "Месяцы": 10}
        PIXELS_PER_DAY = scale_map.get(text, 40)
        self.refresh_chart()

    def add_task_dialog(self):
        title, ok = QInputDialog.getText(self, "Новая задача", "Название:")
        if ok and title:
            self.scene.collect_tasks()
            new_id = max((t.id for t in self.scene.all_tasks_dict.values()), default=0) + 1
            start = TODAY.strftime("%Y-%m-%d")
            end = (TODAY + timedelta(days=7)).strftime("%Y-%m-%d")
            new_task = GanttTask(new_id, title, start, end, "Новый")
            self.scene.tasks.append(new_task)
            self.refresh_chart()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def closeEvent(self, event):
        if hasattr(self, 'session'):
            self.session.close()
        super().closeEvent(event)