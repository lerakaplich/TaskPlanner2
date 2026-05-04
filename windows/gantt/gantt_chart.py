# windows/gantt/gantt_chart.py

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsItem, QGraphicsLineItem, QGraphicsSimpleTextItem,
    QMessageBox, QInputDialog, QTreeWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QLinearGradient, QWheelEvent, QPixmap
)

from services.gantt_service import GanttService


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
    """Модель задачи для Ганта"""
    def __init__(self, task_data: dict):
        self.id = task_data["id"]
        self.title = task_data["title"]
        self.description = task_data.get("description", "")
        self.start_date = task_data["start_date"]
        self.end_date = task_data["end_date"]
        self.assignee = task_data.get("assignee", "")
        self.assignee_id = task_data.get("assignee_id")
        self.is_critical = task_data.get("is_critical", False)
        self.dependencies = task_data.get("dependencies", [])
        self.children = task_data.get("children", [])
        self.color = COLOR_PRIMARY
        self.project_id = task_data.get("project_id")
        self.status = task_data.get("status", "")
        self._is_completed = task_data.get("is_completed", False)
        self.priority = task_data.get("priority", "medium")

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
    def __init__(self, project_start: datetime.date, total_days: int):
        super().__init__(0, 0, total_days * PIXELS_PER_DAY, HEADER_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_SECONDARY)))
        self.setPen(QPen(QColor(COLOR_BORDER), 1))
        self._add_date_labels(project_start, total_days)

    def _add_date_labels(self, project_start: datetime.date, total_days: int):
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


class GanttDependencyItem(QGraphicsLineItem):
    def __init__(self, from_item, to_item, lag: int):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.lag = lag
        self.original_pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.DashLine)
        self.original_pen.setDashPattern([5, 3])
        self.setPen(self.original_pen)
        self.update_position()

    def update_position(self):
        if not self.from_item or not self.to_item:
            return
        start_x = self.from_item.pos().x() + self.from_item.rect_item.rect().width()
        start_y = self.from_item.pos().y() + TASK_HEIGHT / 2
        end_x = self.to_item.pos().x()
        end_y = self.to_item.pos().y() + TASK_HEIGHT / 2
        self.setLine(start_x, start_y, end_x, end_y)


class GanttScene(QGraphicsScene):
    task_changed = pyqtSignal(int)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.project_start = TODAY
        self.project_end = TODAY + timedelta(days=30)
        self.tasks: List[GanttTask] = []
        self.task_items: Dict[int, 'GanttTaskItem'] = {}
        self.dependency_items: List[GanttDependencyItem] = []
        self.setBackgroundBrush(QBrush(QColor(COLOR_BACKGROUND)))

    def update_scene(self):
        self.clear()
        self.task_items.clear()
        self.dependency_items.clear()

        total_days = (self.project_end - self.project_start).days + 1
        header = GanttHeaderItem(self.project_start, total_days)
        self.addItem(header)

        y = HEADER_HEIGHT
        for task in self.tasks:
            from windows.gantt.gantt_task_item import GanttTaskItem
            item = GanttTaskItem(task, self.project_start, y)
            self.addItem(item)
            self.task_items[task.id] = item
            y += ROW_HEIGHT

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

    def scroll_to_today(self, view):
        days = (TODAY - self.project_start).days
        if 0 <= days <= (self.project_end - self.project_start).days:
            x = days * PIXELS_PER_DAY
            view.centerOn(x, view.height() / 2)


class GanttChartWidget(QWidget):
    def __init__(self, service: GanttService = None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "gantt", "gantt_chart.ui")
        uic.loadUi(ui_path, self)

        self.gantt_service = service
        self.current_project_id = None
        self.linking_mode = False
        self.pending_pred = None

        self.scene = GanttScene(self)
        self.ganttView.setScene(self.scene)
        self.ganttView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.ganttView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ganttView.viewport().installEventFilter(self)

        self._connect_signals()
        self._load_projects()

    def _connect_signals(self):
        self.btnZoomIn.clicked.connect(self.zoom_in)
        self.btnZoomOut.clicked.connect(self.zoom_out)
        self.btnRefresh.clicked.connect(self.refresh_chart)
        self.btnToday.clicked.connect(self.center_on_today)
        self.btnExport.clicked.connect(self.export_chart)
        self.btnAddTask.clicked.connect(self.add_task_dialog)
        self.btnCreateLink.clicked.connect(self.toggle_linking_mode)
        self.autoPlanningCheck.toggled.connect(self.refresh_chart)
        self.projectCombo.currentIndexChanged.connect(self.on_project_changed)
        self.searchTasks.textChanged.connect(self.on_search)
        self.filterMyTasks.toggled.connect(self.on_filter_changed)
        self.filterOverdue.toggled.connect(self.on_filter_changed)
        self.filterInProgress.toggled.connect(self.on_filter_changed)
        self.filterCompleted.toggled.connect(self.on_filter_changed)

    def _load_projects(self):
        if not self.gantt_service:
            return
        projects = self.gantt_service.get_projects_for_gantt()
        self.projectCombo.clear()
        self.projectCombo.addItem("-- Выберите проект --", None)
        for proj in projects:
            self.projectCombo.addItem(proj["name"], proj["id"])

    def on_project_changed(self, index):
        if index <= 0:
            return
        self.current_project_id = self.projectCombo.currentData()
        self.load_real_data()

    def on_search(self, text):
        self.load_real_data()

    def on_filter_changed(self):
        self.load_real_data()

    def load_real_data(self):
        if not self.gantt_service or not self.current_project_id:
            return

        filters = {
            'my_tasks': self.filterMyTasks.isChecked(),
            'overdue': self.filterOverdue.isChecked(),
            'in_progress': self.filterInProgress.isChecked(),
            'completed': self.filterCompleted.isChecked(),
            'search': self.searchTasks.text()
        }

        try:
            result = self.gantt_service.get_project_tasks_for_gantt(self.current_project_id, filters)

            if not result["tasks"]:
                self._show_empty_message(result["project_name"])
                return

            self.scene.tasks = [GanttTask(task_data) for task_data in result["tasks"]]
            self.scene.project_start = result["project_start"]
            self.scene.project_end = result["project_end"]

            self.dateRangeLabel.setText(
                f"{result['project_start'].strftime('%d.%m.%Y')} - {result['project_end'].strftime('%d.%m.%Y')}"
            )
            self.statusLabel.setText(
                f"✅ Завершено: {result['completed_tasks']} | "
                f"🔄 В работе: {result['in_progress_tasks']} | "
                f"⚠️ Просрочено: {result['overdue_tasks']} | "
                f"📊 Всего: {result['total_tasks']}"
            )

            self._update_task_tree()
            self.scene.update_scene()
            print(f"✅ Загружено {len(result['tasks'])} задач")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            self._show_empty_message()

    def _update_task_tree(self):
        self.taskList.blockSignals(True)
        self.taskList.clear()

        def add_task_to_tree(task, parent_item=None):
            status_emoji = "✅" if task.is_completed else "⚠️" if task.is_overdue else "🔄"
            date_str = f"{task.start_date.strftime('%d.%m')}–{task.end_date.strftime('%d.%m')}"
            item = QTreeWidgetItem()
            item.setText(0, f"{status_emoji} {task.title} | {date_str} | {task.assignee}")
            item.setData(0, Qt.ItemDataRole.UserRole, task.id)
            if parent_item is None:
                self.taskList.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            item.setExpanded(True)
            for child in task.children:
                add_task_to_tree(child, item)

        for task in self.scene.tasks:
            add_task_to_tree(task)

        self.taskList.blockSignals(False)

    def _show_empty_message(self, project_name=""):
        self.dateRangeLabel.setText("Нет данных")
        if project_name:
            self.statusLabel.setText(f"В проекте '{project_name}' нет задач")
        else:
            self.statusLabel.setText("Задачи не найдены")
        self.scene.tasks = []
        self.scene.update_scene()

    def refresh_chart(self):
        self.load_real_data()

    def zoom_in(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = min(80, PIXELS_PER_DAY + 10)
        self.refresh_chart()

    def zoom_out(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = max(15, PIXELS_PER_DAY - 10)
        self.refresh_chart()

    def center_on_today(self):
        days = (TODAY - self.scene.project_start).days
        if 0 <= days <= (self.scene.project_end - self.scene.project_start).days:
            x = days * PIXELS_PER_DAY
            self.ganttView.centerOn(x, self.ganttView.height() / 2)

    def export_chart(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы Ганта", "", "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if filepath:
            if self.gantt_service.export_to_image(self.scene, filepath):
                QMessageBox.information(self, "Успех", f"Диаграмма экспортирована в {filepath}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать диаграмму")

    def add_task_dialog(self):
        title, ok = QInputDialog.getText(self, "Новая задача", "Название задачи:")
        if ok and title:
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=7)
            task_id = self.gantt_service.add_task(
                self.current_project_id, title, start_date, end_date
            )
            if task_id:
                QMessageBox.information(self, "Успех", f"Задача '{title}' создана")
                self.refresh_chart()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать задачу")

    def toggle_linking_mode(self):
        self.linking_mode = not self.linking_mode
        self.btnCreateLink.setText("Отмена" if self.linking_mode else "Создать связь")
        cursor = Qt.CursorShape.PointingHandCursor if self.linking_mode else Qt.CursorShape.ArrowCursor
        self.ganttView.viewport().setCursor(cursor)

    def eventFilter(self, obj, event):
        if obj == self.ganttView.viewport() and event.type() == QEvent.Type.MouseButtonPress and self.linking_mode:
            pos = self.ganttView.mapToScene(event.pos())
            item = self.scene.itemAt(pos, self.ganttView.transform())
            while item and not hasattr(item, 'task'):
                item = item.parentItem()
            if hasattr(item, 'task'):
                if self.pending_pred is None:
                    self.pending_pred = item.task.id
                    QMessageBox.information(self, "Связь", f"Выбрана задача: {item.task.title}")
                else:
                    lag, ok = QInputDialog.getInt(self, "Лаг", "Задержка (дней):", 0, 0, 30)
                    if ok:
                        # Здесь нужно сохранить зависимость
                        QMessageBox.information(self, "Связь", f"Связь создана с задержкой {lag} дней")
                    self.pending_pred = None
                    self.toggle_linking_mode()
            return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)