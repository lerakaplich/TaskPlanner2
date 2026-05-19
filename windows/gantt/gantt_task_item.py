# windows/gantt/gantt_task_item.py

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QBrush, QPen, QColor, QFont, QLinearGradient
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsSceneMouseEvent

from windows.gantt.gantt_constants import (
    TASK_HEIGHT, PIXELS_PER_DAY, COLOR_BORDER, COLOR_TEXT,
    COLOR_COMPLETED, COLOR_OVERDUE, COLOR_PRIMARY, COLOR_ACCENT
)

from datetime import timedelta


class GanttResizeHandle(QGraphicsRectItem):
    """Хендл для изменения размера задачи (влево/вправо)"""

    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self.side = side
        self.setRect(0, 0, 12, TASK_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_ACCENT)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setOpacity(0.7)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def hoverEnterEvent(self, event):
        self.setOpacity(1.0)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setOpacity(0.7)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            parent = self.parentItem()
            if parent and hasattr(parent, '_start_resize'):
                parent._start_resize(self.side, event.scenePos())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            event.accept()
            parent = self.parentItem()
            if parent and hasattr(parent, '_update_resize'):
                parent._update_resize(self.side, event.scenePos())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            parent = self.parentItem()
            if parent and hasattr(parent, '_end_resize'):
                parent._end_resize()
        else:
            super().mouseReleaseEvent(event)


class GanttTaskItem(QGraphicsItem):
    """Визуальное представление задачи на диаграмме Ганта"""

    def __init__(self, task, project_start, y_position: float, parent_widget=None):
        super().__init__()
        self.task = task
        self.project_start = project_start
        self.y_position = y_position
        self.parent_widget = parent_widget

        # Состояния
        self._drag_start_scene_pos = None
        self._original_start_date = None
        self._original_end_date = None
        self._is_resizing = False
        self._resize_side = None
        self._resize_start_date = None
        self._resize_start_scene_x = None

        # Создаем графические элементы
        self.rect_item = QGraphicsRectItem(self)
        self.text_item = QGraphicsSimpleTextItem(task.title, self)

        # Хендлы
        self.left_handle = GanttResizeHandle('left', self)
        self.right_handle = GanttResizeHandle('right', self)

        # Настройки
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        self._update_position()
        self._update_appearance()

        # Настройка текста
        self.text_item.setPos(15, 4)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.text_item.setFont(font)
        self.text_item.setBrush(QBrush(QColor(COLOR_TEXT)))

        # Исполнитель
        if task.assignee:
            self.assignee_text = QGraphicsSimpleTextItem(task.assignee, self)
            self.assignee_text.setPos(15, 18)
            font_small = QFont("Segoe UI", 7)
            self.assignee_text.setFont(font_small)
            self.assignee_text.setBrush(QBrush(QColor(COLOR_ACCENT)))
        else:
            self.assignee_text = None

    def _get_task_color(self):
        """
        Определяет цвет задачи на основе статуса:
        - Завершено: зеленый (COLOR_COMPLETED)
        - Просрочено: темно-красный (COLOR_OVERDUE)
        - В работе: красный (COLOR_PRIMARY)
        """
        print(f"🎨 Задача '{self.task.title}': is_completed={self.task.is_completed}, is_overdue={self.task.is_overdue}")

        if self.task.is_completed:
            print(f"   -> Зеленый (завершена)")
            return QColor(COLOR_COMPLETED)
        elif self.task.is_overdue:
            print(f"   -> Темно-красный (просрочена)")
            return QColor(COLOR_OVERDUE)
        else:
            print(f"   -> Красный (в работе)")
            return QColor(COLOR_PRIMARY)

    def _update_position(self):
        """Обновляет позицию и размер задачи"""
        days_from_start = (self.task.start_date - self.project_start).days
        x = days_from_start * PIXELS_PER_DAY
        width = max(20, self.task.duration_days * PIXELS_PER_DAY)

        self.setPos(QPointF(x, self.y_position))
        self.rect_item.setRect(0, 0, width, TASK_HEIGHT)
        self.left_handle.setPos(-6, 0)
        self.right_handle.setPos(width - 6, 0)

    def _update_appearance(self):
        """Обновляет внешний вид задачи с правильными цветами"""
        pen = QPen(QColor(COLOR_BORDER), 1)
        self.rect_item.setPen(pen)

        color = self._get_task_color()

        # Создаем градиент для объема
        gradient = QLinearGradient(0, 0, 0, TASK_HEIGHT)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        self.rect_item.setBrush(QBrush(gradient))

    def boundingRect(self):
        return QRectF(-10, 0, max(30, self.rect_item.rect().width() + 20), TASK_HEIGHT)

    def paint(self, painter, option, widget=None):
        pass

    def _save_to_database(self):
        """Сохраняет изменения в БД и обновляет UI"""
        try:
            if self.parent_widget and hasattr(self.parent_widget, 'gantt_service'):
                service = self.parent_widget.gantt_service
                if service:
                    print(f"💾 Сохраняем задачу {self.task.id}: {self.task.start_date} - {self.task.end_date}")
                    success = service.update_task_dates(
                        self.task.id,
                        self.task.start_date,
                        self.task.end_date
                    )
                    if success:
                        print(f"✅ Задача '{self.task.title}' сохранена")
                        # Обновляем дерево задач
                        if hasattr(self.parent_widget, 'update_task_in_tree'):
                            self.parent_widget.update_task_in_tree(self.task.id)
                        # Обновляем цвет задачи (если статус изменился)
                        self._update_appearance()
                    else:
                        print(f"❌ Ошибка сохранения задачи '{self.task.title}'")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            import traceback
            traceback.print_exc()

    def _start_resize(self, side, scene_pos):
        """Начать изменение размера"""
        print(f"🔄 Начало изменения размера: {side}")
        self._is_resizing = True
        self._resize_side = side
        if side == 'left':
            self._resize_start_date = self.task.start_date
        else:
            self._resize_start_date = self.task.end_date
        self._resize_start_scene_x = scene_pos.x()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def _update_resize(self, side, scene_pos):
        """Обновить изменение размера"""
        if not self._is_resizing:
            return

        delta_x = scene_pos.x() - self._resize_start_scene_x
        days_delta = round(delta_x / PIXELS_PER_DAY)

        if days_delta == 0:
            return

        if side == 'left':
            new_start = self._resize_start_date + timedelta(days=days_delta)
            if new_start < self.task.end_date:
                self.task.start_date = new_start
                self._update_position()
                print(f"📅 Новая дата начала: {new_start}")
        else:
            new_end = self._resize_start_date + timedelta(days=days_delta)
            if new_end > self.task.start_date:
                self.task.end_date = new_end
                self._update_position()
                print(f"📅 Новая дата окончания: {new_end}")

    def _end_resize(self):
        """Завершить изменение размера"""
        if self._is_resizing:
            print(f"✅ Завершение изменения размера, сохранение в БД")
            self._save_to_database()
            self._is_resizing = False
            self._resize_side = None
            self._resize_start_date = None
            self._resize_start_scene_x = None
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        """Нажатие для перемещения всей задачи"""
        if (event.button() == Qt.MouseButton.LeftButton and
                not self.left_handle.isUnderMouse() and
                not self.right_handle.isUnderMouse()):
            self._drag_start_scene_pos = event.scenePos()
            self._original_start_date = self.task.start_date
            self._original_end_date = self.task.end_date
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        """Перемещение задачи"""
        if (event.buttons() & Qt.MouseButton.LeftButton and
                self._drag_start_scene_pos is not None and
                not self._is_resizing):
            delta_x = event.scenePos().x() - self._drag_start_scene_pos.x()
            days_delta = round(delta_x / PIXELS_PER_DAY)

            if days_delta != 0:
                new_start = self._original_start_date + timedelta(days=days_delta)
                new_end = self._original_end_date + timedelta(days=days_delta)

                self.task.start_date = new_start
                self.task.end_date = new_end
                self._update_position()

                self._original_start_date = new_start
                self._original_end_date = new_end
                self._drag_start_scene_pos = event.scenePos()
                print(f"📅 Перемещение задачи: {new_start} - {new_end}")

            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        """Отпускание - сохранение"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_start_scene_pos is not None:
                print(f"💾 Сохранение после перемещения")
                self._save_to_database()

            self._drag_start_scene_pos = None
            self._original_start_date = None
            self._original_end_date = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self.rect_item.setOpacity(0.85)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.rect_item.setOpacity(1.0)
        super().hoverLeaveEvent(event)