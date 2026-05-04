# windows/gantt/gantt_task_item.py

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QBrush, QPen, QColor, QFont, QLinearGradient
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsSimpleTextItem

from windows.gantt.gantt_chart import (
    TASK_HEIGHT, PIXELS_PER_DAY, COLOR_BORDER, COLOR_TEXT,
    COLOR_COMPLETED, COLOR_OVERDUE, COLOR_PRIMARY, COLOR_ACCENT
)


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


class GanttTaskItem(QGraphicsItem):
    def __init__(self, task, project_start, y_position: float):
        super().__init__()
        self.task = task
        self.project_start = project_start
        self.y_position = y_position

        self.rect_item = QGraphicsRectItem(self)
        self.text_item = QGraphicsSimpleTextItem(task.title, self)

        self.left_handle = GanttResizeHandle('left', self)
        self.right_handle = GanttResizeHandle('right', self)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        self._update_position()
        self._update_appearance()

        self.text_item.setPos(5, 4)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.text_item.setFont(font)
        self.text_item.setBrush(QBrush(QColor(COLOR_TEXT)))

    def _update_position(self):
        days_from_start = (self.task.start_date - self.project_start).days
        x = days_from_start * PIXELS_PER_DAY
        width = self.task.duration_days * PIXELS_PER_DAY
        self.setPos(QPointF(x, self.y_position))
        self.rect_item.setRect(0, 0, width, TASK_HEIGHT)
        self.left_handle.setPos(0, 0)
        self.right_handle.setPos(width - 12, 0)

    def _update_appearance(self):
        pen = QPen(QColor(COLOR_BORDER), 1)
        self.rect_item.setPen(pen)
        if self.task.is_completed:
            color = QColor(COLOR_COMPLETED)
        elif self.task.is_overdue:
            color = QColor(COLOR_OVERDUE)
        else:
            color = QColor(COLOR_PRIMARY)
        gradient = QLinearGradient(0, 0, 0, TASK_HEIGHT)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        self.rect_item.setBrush(QBrush(gradient))

    def boundingRect(self):
        return QRectF(0, 0, max(1, self.rect_item.rect().width()), TASK_HEIGHT)

    def paint(self, painter, option, widget=None):
        pass