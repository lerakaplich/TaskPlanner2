from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import (
    Qt, pyqtSignal, QRectF, QPointF
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QPainterPath, QMouseEvent, QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from services.gantt_service import GanttService, TaskGanttData


class GanttCanvas(QWidget):
    """
    Холст для отрисовки диаграммы Ганта.
    Поддерживает перетаскивание полос задач и отображение связей.
    """
    task_moved = pyqtSignal(int, datetime, datetime)

    def __init__(self, gantt_service: GanttService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._service = gantt_service
        self._start_date: datetime = datetime(2026, 5, 1)
        self._end_date: datetime = datetime(2026, 6, 30)
        self._day_width: int = self._service.DAY_WIDTH
        self._row_height: int = self._service.ROW_HEIGHT
        self._header_height: int = self._service.HEADER_HEIGHT
        self._left_padding: int = self._service.LEFT_PADDING

        self._dragging_task: Optional[TaskGanttData] = None
        self._drag_start_x: int = 0
        self._original_start: Optional[datetime] = None
        self._original_end: Optional[datetime] = None
        self._links: Dict[int, List[int]] = self._service.get_all_links()

        self.setMouseTracking(True)
        self.setMinimumSize(800, 600)

        # Устанавливаем фон явно
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#FFFFFF"))
        self.setPalette(p)

    def set_date_range(self, start: datetime, end: datetime) -> None:
        """Установить диапазон дат."""
        self._start_date = start
        self._end_date = end
        self.update()

    def set_links(self, links: Dict[int, List[int]]) -> None:
        """Установить связи между задачами."""
        self._links = links
        self.update()

    def _get_total_days(self) -> int:
        """Получить общее количество дней в диапазоне."""
        return max(1, (self._end_date - self._start_date).days + 1)

    def _get_total_width(self) -> int:
        """Получить общую ширину диаграммы."""
        return self._left_padding + self._get_total_days() * self._day_width + 100

    def _get_total_height(self) -> int:
        """Получить общую высоту диаграммы."""
        tasks_count = len(self._service.get_all_tasks())
        return self._header_height + tasks_count * self._row_height + 100

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовка диаграммы Ганта."""
        painter = QPainter(self)

        # Всегда устанавливаем шрифт по умолчанию
        default_font = QFont("Arial", 10)
        painter.setFont(default_font)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tasks = self._service.get_all_tasks()
        if not tasks:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Нет данных для отображения"
            )
            painter.end()
            return

        total_width = self._get_total_width()
        total_height = self._get_total_height()

        # Рисуем фон
        painter.fillRect(0, 0, total_width, total_height, QColor("#FFFFFF"))

        try:
            self._draw_header(painter)
            self._draw_grid(painter, tasks)
            self._draw_task_bars(painter, tasks)
            self._draw_links(painter, tasks)
        except Exception as e:
            print(f"Ошибка отрисовки: {e}")
            import traceback
            traceback.print_exc()

        painter.end()

    def _draw_header(self, painter: QPainter) -> None:
        """Отрисовка шапки с месяцами и днями."""
        total_days = self._get_total_days()

        # Фон шапки
        painter.fillRect(
            0, 0, self._get_total_width(), self._header_height,
            QColor("#F8F9FA")
        )

        # Шрифт для месяцев
        month_font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(month_font)
        painter.setPen(QColor("#1B232A"))

        # Рисуем месяцы и годы
        current_month = -1
        month_start_x = self._left_padding
        month_width = 0
        year = self._start_date.year

        month_names = [
            "", "Январь", "Февраль", "Март", "Апрель",
            "Май", "Июнь", "Июль", "Август",
            "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

        for day_offset in range(total_days):
            date = self._start_date + timedelta(days=day_offset)
            if date.month != current_month:
                if current_month != -1 and 0 < current_month <= 12:
                    month_rect = QRectF(month_start_x, 0, month_width, 30)
                    month_text = f"{month_names[current_month]} {year}"
                    painter.drawText(month_rect, Qt.AlignmentFlag.AlignCenter, month_text)

                current_month = date.month
                year = date.year
                month_start_x = self._left_padding + day_offset * self._day_width
                month_width = self._day_width
            else:
                month_width += self._day_width

        # Рисуем последний месяц
        if current_month != -1 and 0 < current_month <= 12:
            month_rect = QRectF(month_start_x, 0, month_width, 30)
            month_text = f"{month_names[current_month]} {year}"
            painter.drawText(month_rect, Qt.AlignmentFlag.AlignCenter, month_text)

        # Рисуем числа
        day_font = QFont("Arial", 8)
        painter.setFont(day_font)
        painter.setPen(QColor("#666666"))

        for day_offset in range(total_days):
            date = self._start_date + timedelta(days=day_offset)
            x = self._left_padding + day_offset * self._day_width
            day_rect = QRectF(x, 30, self._day_width, 25)
            painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, str(date.day))

    def _draw_grid(self, painter: QPainter, tasks: List[TaskGanttData]) -> None:
        """Отрисовка сетки."""
        total_days = self._get_total_days()
        total_height = self._get_total_height()

        pen = QPen(QColor("#E8E8E8"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        for day_offset in range(total_days + 1):
            x = self._left_padding + day_offset * self._day_width
            painter.drawLine(x, self._header_height, x, total_height)

        for i in range(len(tasks) + 1):
            y = self._header_height + i * self._row_height
            painter.drawLine(self._left_padding, y, self._get_total_width(), y)

    def _draw_task_bars(self, painter: QPainter, tasks: List[TaskGanttData]) -> None:
        """Отрисовка полос задач."""
        for index, task in enumerate(tasks):
            y = self._header_height + index * self._row_height + 5
            x, width = self._service.calculate_bar_position(task, self._start_date)

            if width <= 0:
                continue

            # Создаём скруглённый прямоугольник
            path = QPainterPath()
            bar_rect = QRectF(x, y, max(1, width), max(1, self._row_height - 10))
            path.addRoundedRect(bar_rect, 8.0, 8.0)

            # Заливка цветом приоритета
            color = QColor(task.color)
            painter.fillPath(path, QBrush(color))

            # Текст названия задачи
            if width > 50:  # Рисуем текст только если полоса достаточно широкая
                painter.setPen(QColor("#FFFFFF"))
                font = QFont("Arial", 8, QFont.Weight.Bold)
                painter.setFont(font)
                text_rect = QRectF(x + 5, y, width - 30, self._row_height - 10)
                elided_text = painter.fontMetrics().elidedText(
                    task.name, Qt.TextElideMode.ElideRight, width - 35
                )
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    elided_text
                )

            # Кружок с инициалом
            if width > 30:
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

    def _draw_links(self, painter: QPainter, tasks: List[TaskGanttData]) -> None:
        """Отрисовка стрелок связей."""
        if not self._links:
            return

        task_map: Dict[int, int] = {}
        for index, task in enumerate(tasks):
            task_map[task.id] = index

        arrow_pen = QPen(QColor("#D22730"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(arrow_pen)

        for from_id, to_ids in self._links.items():
            if from_id not in task_map:
                continue
            for to_id in to_ids:
                if to_id not in task_map:
                    continue

                from_task = tasks[task_map[from_id]]
                to_task = tasks[task_map[to_id]]

                from_x, from_width = self._service.calculate_bar_position(from_task, self._start_date)
                from_y = self._header_height + task_map[from_id] * self._row_height + self._row_height // 2

                to_x, _ = self._service.calculate_bar_position(to_task, self._start_date)
                to_y = self._header_height + task_map[to_id] * self._row_height + self._row_height // 2

                start_point = QPointF(from_x + from_width + 5, from_y)
                end_point = QPointF(to_x - 5, to_y)

                mid_x = (start_point.x() + end_point.x()) // 2

                # Рисуем путь
                path = QPainterPath()
                path.moveTo(start_point)
                path.lineTo(QPointF(mid_x, from_y))
                path.lineTo(QPointF(mid_x, to_y))
                path.lineTo(end_point)
                painter.drawPath(path)

                # Стрелка
                if end_point.x() > start_point.x():
                    arrow_size = 6
                    painter.setBrush(QBrush(QColor("#D22730")))
                    arrow = QPainterPath()
                    arrow.moveTo(end_point)
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() - arrow_size))
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() + arrow_size))
                    arrow.closeSubpath()
                    painter.drawPath(arrow)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Обработка нажатия мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            task = self._get_task_at_position(event.pos())
            if task:
                self._dragging_task = task
                self._drag_start_x = int(event.position().x())
                self._original_start = task.start_date
                self._original_end = task.end_date
                self.setCursor(Qt.CursorShape.SizeHorCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Обработка перемещения мыши."""
        if self._dragging_task:
            delta_x = event.position().x() - self._drag_start_x
            days_delta = round(delta_x / self._day_width)

            if days_delta != 0 and self._original_start and self._original_end:
                new_start = self._original_start + timedelta(days=days_delta)
                duration = (self._original_end - self._original_start).days
                new_end = new_start + timedelta(days=duration)

                self._dragging_task.start_date = new_start
                self._dragging_task.end_date = new_end

                linked_ids = self._service.get_linked_tasks_for_update(self._dragging_task.id)
                all_tasks = self._service.get_all_tasks()
                for tid in linked_ids:
                    for t in all_tasks:
                        if t.id == tid and t != self._dragging_task:
                            t.start_date = t.start_date + timedelta(days=days_delta)
                            t.end_date = t.end_date + timedelta(days=days_delta)

                self._drag_start_x = int(event.position().x())
                self.update()
        else:
            task = self._get_task_at_position(event.pos())
            self.setCursor(Qt.CursorShape.PointingHandCursor if task else Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Обработка отпускания мыши."""
        if self._dragging_task:
            self.task_moved.emit(
                self._dragging_task.id,
                self._dragging_task.start_date,
                self._dragging_task.end_date
            )
            self._dragging_task = None
            self._original_start = None
            self._original_end = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _get_task_at_position(self, pos: QPointF) -> Optional[TaskGanttData]:
        """Получить задачу по позиции указателя."""
        tasks = self._service.get_all_tasks()
        for index, task in enumerate(tasks):
            y = self._header_height + index * self._row_height + 5
            x, width = self._service.calculate_bar_position(task, self._start_date)

            if x <= pos.x() <= x + width and y <= pos.y() <= y + self._row_height - 10:
                return task
        return None