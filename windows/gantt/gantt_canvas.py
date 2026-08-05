# windows/gantt/gantt_canvas.py

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    Qt, pyqtSignal, QRectF, QPointF, QEvent, QPoint
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QPainterPath, QMouseEvent
)
from PyQt6.QtWidgets import QWidget, QMessageBox, QApplication

from services.gantt_service.gantt_base_service import TaskGanttData
from services.gantt_service.gantt_service import GanttService


# windows/gantt/gantt_canvas.py

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    Qt, pyqtSignal, QRectF, QPointF, QEvent, QPoint
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QPainterPath, QMouseEvent
)
from PyQt6.QtWidgets import QWidget, QMessageBox, QApplication, QMenu

from services.gantt_service.gantt_base_service import TaskGanttData
from services.gantt_service.gantt_service import GanttService


class GanttCanvas(QWidget):
    """Холст для отрисовки диаграммы Ганта - только отображение и UI события"""

    # Сигналы для передачи действий в сервис
    task_moved_signal = pyqtSignal(int, datetime, datetime)
    link_created_signal = pyqtSignal(int, int)
    link_deleted_signal = pyqtSignal(int, int)  # <-- ДОБАВЛЕНО

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
        self._selected_link = None  # <-- Для хранения выбранной связи

        self.setMouseTracking(True)
        self.setMinimumSize(800, 600)
        self.setAutoFillBackground(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Устанавливаем фон
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#FFFFFF"))
        self.setPalette(p)

    def _get_link_at_position(self, pos: QPointF) -> Optional[Tuple[int, int, str]]:
        """
        Определяет, есть ли связь в указанной позиции.
        Возвращает (predecessor_id, successor_id, link_type) или None.
        """
        if not self._links:
            return None

        task_map = {task.id: idx for idx, task in enumerate(self._tasks)}

        for from_id, deps in self._links.items():
            if from_id not in task_map:
                continue

            from_task = self._tasks[task_map[from_id]]
            from_x, from_width = self._service.calculate_bar_position(from_task, self._start_date)
            from_y = self._header_height + task_map[from_id] * self._row_height + self._row_height // 2

            for dep in deps:
                if isinstance(dep, dict):
                    to_id = dep.get("successor_id")
                    link_type = dep.get("type", "FS")
                else:
                    to_id = dep
                    link_type = "FS"

                if to_id not in task_map:
                    continue

                to_task = self._tasks[task_map[to_id]]
                to_x, _ = self._service.calculate_bar_position(to_task, self._start_date)
                to_y = self._header_height + task_map[to_id] * self._row_height + self._row_height // 2

                start_point = QPointF(from_x + from_width + 5, from_y)
                end_point = QPointF(to_x - 5, to_y)

                # Проверяем, находится ли позиция мыши рядом с линией
                if self._is_point_near_link(pos, start_point, end_point, from_y, to_y):
                    return (from_id, to_id, link_type)

        return None

    def _is_point_near_link(self, pos: QPointF, start: QPointF, end: QPointF, from_y: float, to_y: float,
                            threshold: float = 10.0) -> bool:
        """
        Проверяет, находится ли точка рядом с линией связи.
        """
        # Если линия с изгибом (FS, FF)
        if abs(to_y - from_y) > 30:
            mid_x = (start.x() + end.x()) // 2
            # Проверяем три сегмента: горизонтальный от start до mid, вертикальный, горизонтальный от mid до end
            # Сегмент 1: от start до (mid_x, from_y)
            if self._point_near_segment(pos, start, QPointF(mid_x, from_y), threshold):
                return True
            # Сегмент 2: вертикальный от (mid_x, from_y) до (mid_x, to_y)
            if self._point_near_segment(pos, QPointF(mid_x, from_y), QPointF(mid_x, to_y), threshold):
                return True
            # Сегмент 3: от (mid_x, to_y) до end
            if self._point_near_segment(pos, QPointF(mid_x, to_y), end, threshold):
                return True
        else:
            # Прямая линия (SS, SF)
            if self._point_near_segment(pos, start, end, threshold):
                return True

        return False

    def _point_near_segment(self, point: QPointF, seg_start: QPointF, seg_end: QPointF, threshold: float) -> bool:
        """
        Проверяет, находится ли точка рядом с отрезком.
        """
        # Вектор от seg_start к seg_end
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()

        # Длина отрезка
        length = (dx * dx + dy * dy) ** 0.5
        if length < 0.001:
            return False

        # Нормализованный вектор
        ux = dx / length
        uy = dy / length

        # Вектор от seg_start к point
        vx = point.x() - seg_start.x()
        vy = point.y() - seg_start.y()

        # Проекция v на u
        proj = vx * ux + vy * uy

        # Ближайшая точка на отрезке
        if proj < 0:
            closest = seg_start
        elif proj > length:
            closest = seg_end
        else:
            closest = QPointF(seg_start.x() + proj * ux, seg_start.y() + proj * uy)

        # Расстояние от point до closest
        dist = ((point.x() - closest.x()) ** 2 + (point.y() - closest.y()) ** 2) ** 0.5

        return dist < threshold

    def _show_context_menu(self, pos: QPoint) -> None:
        """Показывает контекстное меню в позиции курсора."""
        # Проверяем, есть ли связь в этой позиции
        link_info = self._get_link_at_position(pos)

        if not link_info:
            # Если связи нет, возможно показываем меню для задачи
            task = self._get_task_at_position(pos)
            if task:
                self._show_task_context_menu(pos, task)
            return

        pred_id, succ_id, link_type = link_info
        self._selected_link = (pred_id, succ_id)

        # Создаём контекстное меню
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px 0;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 25px 8px 15px;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #ccab6e;
                color: white;
                border-radius: 4px;
                margin: 2px 6px;
            }
        """)

        # Получаем названия задач
        pred_task = self._service.get_task_by_id(pred_id)
        succ_task = self._service.get_task_by_id(succ_id)
        pred_name = pred_task.name if pred_task else f"Задача {pred_id}"
        succ_name = succ_task.name if succ_task else f"Задача {succ_id}"

        # Добавляем информацию о связи (неактивный пункт)
        link_type_names = {
            "FS": "Финиш-Старт",
            "SS": "Старт-Старт",
            "FF": "Финиш-Финиш",
            "SF": "Старт-Финиш",
        }
        type_name = link_type_names.get(link_type, link_type)

        info_action = menu.addAction(f"{pred_name} → {succ_name} ({type_name})")
        info_action.setEnabled(False)
        menu.addSeparator()

        # Кнопка удаления
        delete_action = menu.addAction("Удалить связь")
        delete_action.triggered.connect(lambda: self._on_delete_link(pred_id, succ_id))

        # Показываем меню
        menu.exec(self.mapToGlobal(pos))

    def _show_task_context_menu(self, pos: QPoint, task: TaskGanttData) -> None:
        """Показывает контекстное меню для задачи."""
        # Можно добавить меню для задачи, но пока оставим пустым
        pass

    def _on_delete_link(self, pred_id: int, succ_id: int) -> None:
        """Обработчик удаления связи."""
        # Спрашиваем подтверждение
        pred_task = self._service.get_task_by_id(pred_id)
        succ_task = self._service.get_task_by_id(succ_id)
        pred_name = pred_task.name if pred_task else f"Задача {pred_id}"
        succ_name = succ_task.name if succ_task else f"Задача {succ_id}"

        reply = QMessageBox.question(
            self,
            "Удаление связи",
            f"Вы уверены, что хотите удалить связь между задачами:\n"
            f"«{pred_name}» → «{succ_name}»?\n\n"
            f"Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Отправляем сигнал для удаления связи
            self.link_deleted_signal.emit(pred_id, succ_id)
            self._selected_link = None

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

    def set_links(self, links: Dict[int, List[Dict]]) -> None:
        """Установить связи между задачами (с типами)"""
        self._links = links
        # Добавляем отладку
        print(f"🔗 GanttCanvas.set_links: получено {len(links)} связей")
        for from_id, deps in links.items():
            for dep in deps:
                if isinstance(dep, dict):
                    print(f"   {from_id} -> {dep.get('successor_id')} type={dep.get('type', 'FS')}")
                else:
                    print(f"   {from_id} -> {dep} (не словарь!)")
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
        """Отрисовка стрелок связей с типами."""
        if not self._links:
            return

        task_map = {task.id: idx for idx, task in enumerate(self._tasks)}

        # Цвета для разных типов связей
        link_colors = {
            "FS": QColor("#D22730"),  # Красный
            "SS": QColor("#2196F3"),  # Синий
            "FF": QColor("#4CAF50"),  # Зелёный
            "SF": QColor("#FF9800"),  # Оранжевый
        }

        # Символы для разных типов связей
        link_symbols = {
            "FS": "→",
            "SS": "⇉",
            "FF": "⇇",
            "SF": "↩",
        }

        for from_id, deps in self._links.items():
            if from_id not in task_map:
                print(f"   ⚠️ Задача {from_id} не найдена в task_map")
                continue

            from_task = self._tasks[task_map[from_id]]
            from_x, from_width = self._service.calculate_bar_position(from_task, self._start_date)
            from_y = self._header_height + task_map[from_id] * self._row_height + self._row_height // 2

            for dep in deps:
                # Проверяем, является ли dep словарем или просто числом
                if isinstance(dep, dict):
                    to_id = dep.get("successor_id")
                    link_type = dep.get("type", "FS")
                    lag = dep.get("lag", 0)
                else:
                    to_id = dep
                    link_type = "FS"
                    lag = 0
                    print(f"   ⚠️ {from_id} -> {to_id}: dep НЕ словарь! type=FS (по умолчанию)")

                if to_id not in task_map:
                    print(f"   ⚠️ Задача {to_id} не найдена в task_map")
                    continue

                # Получаем цвет для типа связи
                color = link_colors.get(link_type, QColor("#D22730"))

                to_task = self._tasks[task_map[to_id]]
                to_x, _ = self._service.calculate_bar_position(to_task, self._start_date)
                to_y = self._header_height + task_map[to_id] * self._row_height + self._row_height // 2

                start_point = QPointF(from_x + from_width + 5, from_y)
                end_point = QPointF(to_x - 5, to_y)

                # Рисуем линию связи в зависимости от типа
                painter.setPen(QPen(color, 2.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)

                # Разная логика отрисовки для разных типов связей
                if link_type in ("FS", "FF"):
                    # Финиш-Старт или Финиш-Финиш - с изгибом
                    mid_x = (start_point.x() + end_point.x()) // 2
                    path = QPainterPath()
                    path.moveTo(start_point)
                    path.lineTo(QPointF(mid_x, from_y))
                    path.lineTo(QPointF(mid_x, to_y))
                    path.lineTo(end_point)
                    painter.drawPath(path)
                else:
                    # Старт-Старт или Старт-Финиш - прямая линия
                    painter.drawLine(start_point, end_point)

                # Рисуем стрелку на конце
                if end_point.x() > start_point.x():
                    arrow_size = 5
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color, 1))

                    arrow = QPainterPath()
                    arrow.moveTo(end_point)
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() - arrow_size))
                    arrow.lineTo(QPointF(end_point.x() - arrow_size, end_point.y() + arrow_size))
                    arrow.closeSubpath()
                    painter.drawPath(arrow)

                    # Рисуем символ типа связи
                    symbol = link_symbols.get(link_type, "→")
                    # Вычисляем позицию для символа
                    if abs(to_y - from_y) > 30:
                        symbol_x = mid_x - 10
                        symbol_y = (from_y + to_y) // 2 - 10
                    else:
                        symbol_x = (start_point.x() + end_point.x()) // 2 - 10
                        symbol_y = from_y - 15

                    painter.setPen(QPen(QColor("#1B232A"), 1))
                    font = QFont("Arial", 9, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.drawText(
                        QRectF(symbol_x, symbol_y, 20, 20),
                        Qt.AlignmentFlag.AlignCenter,
                        symbol
                    )
                    print(f"   🔤 {from_id}->{to_id}: символ '{symbol}'")

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