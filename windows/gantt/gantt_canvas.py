# windows/gantt/gantt_canvas.py

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    Qt, pyqtSignal, QRectF, QPointF, QEvent
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QPainterPath, QMouseEvent
)
from PyQt6.QtWidgets import QWidget, QMessageBox, QApplication

from services.gantt_service import GanttService, TaskGanttData


class GanttCanvas(QWidget):
    """Холст для отрисовки диаграммы Ганта - только отображение и UI события"""

    # Сигналы для передачи действий в сервис
    task_moved_signal = pyqtSignal(int, datetime, datetime)
    link_created_signal = pyqtSignal(int, int)

    def __init__(self, gantt_service: GanttService, parent=None):
        super().__init__(parent)
        self._service = gantt_service
        self._start_date: datetime = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._end_date: datetime = self._start_date + timedelta(days=60)
        self._day_width: int = GanttService.DAY_WIDTH
        self._row_height: int = GanttService.ROW_HEIGHT
        self._header_height: int = GanttService.HEADER_HEIGHT
        self._left_padding: int = GanttService.LEFT_PADDING

        self._dragging_task: Optional[TaskGanttData] = None
        self._drag_start_x: int = 0
        self._original_start: Optional[datetime] = None
        self._original_end: Optional[datetime] = None
        self._links: Dict[int, List[int]] = {}
        self._tasks: List[TaskGanttData] = []

        # Для создания связей (Ctrl+клик)
        self._selected_for_link: Optional[TaskGanttData] = None

        self.setMouseTracking(True)
        self.setMinimumSize(800, 600)
        self.setAutoFillBackground(True)

        # Устанавливаем фон
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#FFFFFF"))
        self.setPalette(p)

    # ==================== Публичные методы для UI ====================

    def set_tasks(self, tasks: List[TaskGanttData]) -> None:
        """Устанавливает задачи для отображения"""
        self._tasks = tasks
        self.update()

    def set_date_range(self, start: datetime, end: datetime) -> None:
        """Установить диапазон дат"""
        self._start_date = start
        self._end_date = end
        self.update()

    def set_links(self, links: Dict[int, List[int]]) -> None:
        """Установить связи между задачами"""
        self._links = links
        self.update()

    def clear_selection(self) -> None:
        """Очищает выделение для связи"""
        self._selected_for_link = None
        self.update()

    def refresh_view(self) -> None:
        """Обновляет отображение"""
        self.update()

    # ==================== Внутренние методы отрисовки ====================

    def _get_total_days(self) -> int:
        """Получить общее количество дней в диапазоне"""
        return max(1, (self._end_date - self._start_date).days + 1)

    def _get_total_width(self) -> int:
        """Получить общую ширину диаграммы"""
        return self._left_padding + self._get_total_days() * self._day_width + 100

    def _get_total_height(self) -> int:
        """Получить общую высоту диаграммы"""
        return self._header_height + len(self._tasks) * self._row_height + 100

    def paintEvent(self, event) -> None:
        """Отрисовка диаграммы Ганта"""
        try:
            painter = QPainter(self)
        except Exception as e:
            print(f"Не удалось создать QPainter: {e}")
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._tasks:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Нет данных для отображения.\nСоздайте задачи в проектах."
            )
            painter.end()
            return

        total_width = self._get_total_width()
        total_height = self._get_total_height()
        self.setFixedSize(total_width, total_height)

        painter.fillRect(0, 0, total_width, total_height, QColor("#FFFFFF"))

        try:
            self._draw_header(painter)
            self._draw_grid(painter)
            self._draw_task_bars(painter)
            self._draw_links(painter)

            if self._selected_for_link:
                self._draw_selection_highlight(painter)
        except Exception as e:
            print(f"Ошибка отрисовки: {e}")
            import traceback
            traceback.print_exc()

        painter.end()

    def _draw_header(self, painter: QPainter) -> None:
        """Отрисовка шапки"""
        total_days = self._get_total_days()

        painter.fillRect(0, 0, self._get_total_width(), self._header_height, QColor("#F8F9FA"))

        month_font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(month_font)
        painter.setPen(QColor("#1B232A"))

        current_month = -1
        month_start_x = self._left_padding
        month_width = 0
        year = self._start_date.year

        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

        for day_offset in range(total_days):
            date = self._start_date + timedelta(days=day_offset)
            if date.month != current_month:
                if current_month != -1:
                    month_rect = QRectF(month_start_x, 0, month_width, 30)
                    painter.drawText(month_rect, Qt.AlignmentFlag.AlignCenter,
                                     f"{month_names[current_month]} {year}")
                current_month = date.month
                year = date.year
                month_start_x = self._left_padding + day_offset * self._day_width
                month_width = self._day_width
            else:
                month_width += self._day_width

        if current_month != -1:
            month_rect = QRectF(month_start_x, 0, month_width, 30)
            painter.drawText(month_rect, Qt.AlignmentFlag.AlignCenter,
                             f"{month_names[current_month]} {year}")

        day_font = QFont("Arial", 8)
        painter.setFont(day_font)
        painter.setPen(QColor("#666666"))

        for day_offset in range(total_days):
            date = self._start_date + timedelta(days=day_offset)
            x = self._left_padding + day_offset * self._day_width
            day_rect = QRectF(x, 30, self._day_width, 25)
            painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, str(date.day))

    def _draw_grid(self, painter: QPainter) -> None:
        """Отрисовка сетки"""
        total_days = self._get_total_days()
        total_height = self._get_total_height()

        pen = QPen(QColor("#E8E8E8"), 1)
        painter.setPen(pen)

        for day_offset in range(total_days + 1):
            x = self._left_padding + day_offset * self._day_width
            painter.drawLine(x, self._header_height, x, total_height)

        for i in range(len(self._tasks) + 1):
            y = self._header_height + i * self._row_height
            painter.drawLine(self._left_padding, y, self._get_total_width(), y)

    def _draw_task_bars(self, painter: QPainter) -> None:
        """Отрисовка полос задач"""
        for index, task in enumerate(self._tasks):
            y = self._header_height + index * self._row_height + 5
            x, width = self._service.calculate_bar_position(task, self._start_date)

            if width <= 0:
                continue

            path = QPainterPath()
            bar_rect = QRectF(x, y, max(1.0, width), max(1.0, self._row_height - 10))
            path.addRoundedRect(bar_rect, 8.0, 8.0)

            color = QColor(task.color)
            painter.fillPath(path, QBrush(color))

            if width > 50:
                painter.setPen(QColor("#FFFFFF"))
                font = QFont("Arial", 8, QFont.Weight.Bold)
                painter.setFont(font)
                text_rect = QRectF(x + 5, y, width - 30, self._row_height - 10)
                text_width = int(width) - 35
                if text_width > 10:
                    elided_text = painter.fontMetrics().elidedText(
                        task.name, Qt.TextElideMode.ElideRight, text_width
                    )
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_text)

            if width > 30 and task.executor_initials:
                circle_x = x + width - 20
                circle_y = y + (self._row_height - 10) // 2 - 10
                circle_rect = QRectF(circle_x, circle_y, 20, 20)

                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.setPen(QPen(color, 2))
                painter.drawEllipse(circle_rect)

                painter.setPen(QColor(task.color))
                init_font = QFont("Arial", 8, QFont.Weight.Bold)
                painter.setFont(init_font)
                painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, task.executor_initials)

    def _draw_links(self, painter: QPainter) -> None:
        """Отрисовка стрелок связей"""
        if not self._links:
            return

        task_map = {task.id: idx for idx, task in enumerate(self._tasks)}

        arrow_pen = QPen(QColor("#D22730"), 2)
        painter.setPen(arrow_pen)

        for from_id, to_ids in self._links.items():
            if from_id not in task_map:
                continue
            from_task = self._tasks[task_map[from_id]]
            from_x, from_width = self._service.calculate_bar_position(from_task, self._start_date)
            from_y = self._header_height + task_map[from_id] * self._row_height + self._row_height // 2

            for to_id in to_ids:
                if to_id not in task_map:
                    continue
                to_task = self._tasks[task_map[to_id]]
                to_x, _ = self._service.calculate_bar_position(to_task, self._start_date)
                to_y = self._header_height + task_map[to_id] * self._row_height + self._row_height // 2

                start_point = QPointF(from_x + from_width + 5, from_y)
                end_point = QPointF(to_x - 5, to_y)
                mid_x = (start_point.x() + end_point.x()) // 2

                path = QPainterPath()
                path.moveTo(start_point)
                path.lineTo(QPointF(mid_x, from_y))
                path.lineTo(QPointF(mid_x, to_y))
                path.lineTo(end_point)
                painter.drawPath(path)

                if end_point.x() > start_point.x():
                    arrow_size = 6
                    painter.setBrush(QBrush(QColor("#D22730")))
                    arrow = QPainterPath()
                    arrow.moveTo(end_point)
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() - arrow_size))
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() + arrow_size))
                    arrow.closeSubpath()
                    painter.drawPath(arrow)

    def _draw_selection_highlight(self, painter: QPainter) -> None:
        """Рисует подсветку выбранной задачи для связи"""
        for index, task in enumerate(self._tasks):
            if task.id == self._selected_for_link.id:
                y = self._header_height + index * self._row_height + 5
                x, width = self._service.calculate_bar_position(task, self._start_date)

                pen = QPen(QColor("#ccab6e"), 3)
                painter.setPen(pen)
                painter.setBrush(QBrush())
                bar_rect = QRectF(x, y, width, self._row_height - 10)
                painter.drawRoundedRect(bar_rect, 8.0, 8.0)
                break

    # ==================== Обработка событий мыши ====================

    def _get_task_at_position(self, pos: QPointF) -> Optional[TaskGanttData]:
        """Получить задачу по позиции"""
        for index, task in enumerate(self._tasks):
            y = self._header_height + index * self._row_height + 5
            x, width = self._service.calculate_bar_position(task, self._start_date)
            if x <= pos.x() <= x + width and y <= pos.y() <= y + self._row_height - 10:
                return task
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Обработка нажатия мыши"""
        modifiers = QApplication.keyboardModifiers()

        if event.button() == Qt.MouseButton.LeftButton:
            task = self._get_task_at_position(event.position())

            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+клик для создания связи
                if task:
                    if self._selected_for_link is None:
                        self._selected_for_link = task
                        self.update()
                    else:
                        if self._selected_for_link.id != task.id:
                            # Передаём в сервис через сигнал
                            self.link_created_signal.emit(self._selected_for_link.id, task.id)
                        self._selected_for_link = None
                        self.update()
                else:
                    self._selected_for_link = None
                    self.update()
            else:
                # Обычный клик - перетаскивание
                if task:
                    self._dragging_task = task
                    self._drag_start_x = int(event.position().x())
                    self._original_start = task.start_date
                    self._original_end = task.end_date
                    self.setCursor(Qt.CursorShape.SizeHorCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Обработка перемещения мыши"""
        if self._dragging_task:
            delta_x = event.position().x() - self._drag_start_x
            days_delta = round(delta_x / self._day_width)

            if days_delta != 0 and self._original_start and self._original_end:
                new_start = self._original_start + timedelta(days=days_delta)
                duration = (self._original_end - self._original_start).days
                new_end = new_start + timedelta(days=duration)

                # Обновляем задачу в памяти для отображения
                self._dragging_task.start_date = new_start
                self._dragging_task.end_date = new_end

                # Отправляем сигнал для сохранения в БД
                self.task_moved_signal.emit(self._dragging_task.id, new_start, new_end)

                self._drag_start_x = int(event.position().x())
                self.update()
        else:
            task = self._get_task_at_position(event.position())
            self.setCursor(Qt.CursorShape.PointingHandCursor if task else Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Обработка отпускания мыши"""
        self._dragging_task = None
        self._original_start = None
        self._original_end = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)