"""
Диаграмма Ганта для системы управления проектами МАЗ
Современный UI с поддержкой иерархии задач, drag & drop, масштабированием
ИСПРАВЛЕННАЯ ВЕРСИЯ С РАБОЧИМ КАЛЕНДАРЕМ
"""

import sys
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QScrollArea, QApplication, QMainWindow, QComboBox, QMessageBox,
    QSplitter, QSizePolicy, QToolButton, QMenu, QLineEdit, QDateEdit
)
from PyQt6.QtCore import Qt, QRect, QPoint, QDate, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient, QMouseEvent, QFontDatabase

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.schemas.tasks_dto import TaskDTO, TaskPriority
from services.projects_service import ProjectsService


class ScaleType(Enum):
    """Типы масштаба временной шкалы"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"


@dataclass
class GanttTaskNode:
    """Узел задачи для диаграммы Ганта с поддержкой иерархии"""
    id: int
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    priority: TaskPriority = TaskPriority.medium
    progress: int = 0
    is_milestone: bool = False
    parent_id: Optional[int] = None
    children: List['GanttTaskNode'] = field(default_factory=list)
    is_expanded: bool = True
    level: int = 0
    assigned_to_name: Optional[str] = None
    assigned_to_id: Optional[int] = None
    description: Optional[str] = None

    @property
    def duration_days(self) -> int:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 1

    @property
    def color(self) -> str:
        """Цвет задачи в зависимости от приоритета"""
        colors = {
            TaskPriority.critical: "#EF4444",  # Красный
            TaskPriority.high: "#F97316",      # Оранжевый
            TaskPriority.medium: "#F59E0B",    # Желтый
            TaskPriority.low: "#10B981"        # Зеленый
        }
        return colors.get(self.priority, "#6366F1")  # Индиго по умолчанию


class ModernScrollArea(QScrollArea):
    """Современная скролл-область с гладким скроллингом"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #F1F5F9;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #F1F5F9;
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)


class TaskItemWidget(QFrame):
    """Виджет для отображения задачи в левой панели"""

    task_clicked = pyqtSignal(int)
    task_double_clicked = pyqtSignal(int)
    toggle_expand = pyqtSignal(int)

    def __init__(self, task_node: GanttTaskNode, parent=None):
        super().__init__(parent)
        self.task_node = task_node

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(10)

        # Отступ для уровня вложенности
        if self.task_node.level > 0:
            indent = QWidget()
            indent.setFixedSize(self.task_node.level * 20, 1)
            layout.addWidget(indent)

        # Кнопка раскрытия для родительских задач
        if self.task_node.children:
            self.expand_btn = QPushButton("▼" if self.task_node.is_expanded else "▶")
            self.expand_btn.setFixedSize(22, 22)
            self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.expand_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: #F1F5F9;
                    border-radius: 6px;
                    font-size: 10px;
                    color: #475569;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #0F172A;
                }
            """)
            self.expand_btn.clicked.connect(lambda: self.toggle_expand.emit(self.task_node.id))
            layout.addWidget(self.expand_btn)
        else:
            spacer = QWidget()
            spacer.setFixedSize(22, 22)
            layout.addWidget(spacer)

        # Иконка задачи
        icon_label = QLabel(self.get_task_icon())
        icon_label.setFixedWidth(28)
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        # Название задачи
        self.title_label = QLabel(self.task_node.title)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #1E293B;
            }
        """)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label, 1)

        # Назначено
        if self.task_node.assigned_to_name:
            assigned_label = QLabel(f"👤 {self.task_node.assigned_to_name[:20]}")
            assigned_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #64748B;
                    background-color: #F1F5F9;
                    padding: 2px 8px;
                    border-radius: 12px;
                }
            """)
            layout.addWidget(assigned_label)

        # Приоритет (цветной бейдж)
        priority_label = QLabel(self.get_priority_text())
        priority_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.task_node.color}20;
                color: {self.task_node.color};
                font-size: 10px;
                font-weight: 600;
                padding: 2px 8px;
                border-radius: 12px;
            }}
        """)
        layout.addWidget(priority_label)

        # Прогресс
        if self.task_node.progress > 0:
            progress_label = QLabel(f"{self.task_node.progress}%")
            progress_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #475569;
                    font-weight: 500;
                    background-color: #F1F5F9;
                    padding: 2px 8px;
                    border-radius: 12px;
                }
            """)
            layout.addWidget(progress_label)

        # Даты
        if self.task_node.start_date and self.task_node.end_date:
            dates_label = QLabel(
                f"📅 {self.task_node.start_date.strftime('%d.%m')} → {self.task_node.end_date.strftime('%d.%m')}"
            )
            dates_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #94A3B8;
                }
            """)
            layout.addWidget(dates_label)

    def get_task_icon(self) -> str:
        """Возвращает иконку в зависимости от типа задачи"""
        if self.task_node.children:
            return "📁"
        elif self.task_node.is_milestone:
            return "⛳"
        else:
            return "📝"

    def get_priority_text(self) -> str:
        """Возвращает текст приоритета"""
        priority_map = {
            TaskPriority.critical: "КРИТ",
            TaskPriority.high: "ВЫС",
            TaskPriority.medium: "СР",
            TaskPriority.low: "НИЗ"
        }
        return priority_map.get(self.task_node.priority, "СР")

    def apply_styles(self):
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #F1F5F9;
            }
            QFrame:hover {
                background-color: #F8FAFC;
            }
        """)

    def mouseDoubleClickEvent(self, event):
        self.task_double_clicked.emit(self.task_node.id)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.task_clicked.emit(self.task_node.id)


class GanttBarWidget(QFrame):
    """Виджет для отображения полосы задачи на диаграмме"""

    bar_clicked = pyqtSignal(int)
    bar_moved = pyqtSignal(int, date, date)
    bar_resized = pyqtSignal(int, date, date)

    def __init__(self, task_node: GanttTaskNode, start_date: date, end_date: date,
                 x_pos: int, width: int, parent=None):
        super().__init__(parent)
        self.task_node = task_node
        self.start_date = start_date
        self.end_date = end_date
        self.dragging = False
        self.resizing_left = False
        self.resizing_right = False
        self.drag_start_x = 0
        self.original_start = start_date
        self.original_end = end_date
        self.resize_margin = 8

        self.setGeometry(x_pos, 5, max(width, 30), 40)
        self.setToolTip(self.get_tooltip_text())
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.apply_styles()

    def apply_styles(self):
        """Применение стилей к полосе с градиентом прогресса"""
        progress = min(100, max(0, self.task_node.progress))
        color = self.task_node.color

        # Создаем стиль с градиентом для прогресса
        self.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:{progress / 100} {color}, 
                    stop:{progress / 100} #E2E8F0, stop:1 #E2E8F0);
                border-radius: 8px;
                border: 1px solid {color};
            }}
            QFrame:hover {{
                border: 2px solid {color};
            }}
        """)

    def get_tooltip_text(self) -> str:
        """Возвращает HTML-подсказку с информацией о задаче"""
        return f"""
        <div style="padding: 8px;">
            <b style="font-size: 14px;">{self.task_node.title}</b><br>
            <hr style="margin: 5px 0;">
            <b>📅 Начало:</b> {self.start_date.strftime('%d.%m.%Y')}<br>
            <b>📅 Окончание:</b> {self.end_date.strftime('%d.%m.%Y')}<br>
            <b>⏱ Длительность:</b> {self.task_node.duration_days} дн.<br>
            <b>📊 Прогресс:</b> {self.task_node.progress}%<br>
            <b>🎯 Приоритет:</b> {self.get_priority_text()}
        </div>
        """

    def get_priority_text(self) -> str:
        priority_map = {
            TaskPriority.critical: "🔴 Критичный",
            TaskPriority.high: "🟠 Высокий",
            TaskPriority.medium: "🟡 Средний",
            TaskPriority.low: "🟢 Низкий"
        }
        return priority_map.get(self.task_node.priority, "Средний")

    def check_resize_zone(self, x: int) -> str:
        """Проверяет, в какой зоне находится курсор"""
        if x <= self.resize_margin:
            return "left"
        elif x >= self.width() - self.resize_margin:
            return "right"
        return "move"

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            local_x = int(event.position().x())
            zone = self.check_resize_zone(local_x)

            if zone == "left":
                self.resizing_left = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif zone == "right":
                self.resizing_right = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

            self.drag_start_x = int(event.globalPosition().x())
            self.original_start = self.start_date
            self.original_end = self.end_date

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging or self.resizing_left or self.resizing_right:
            delta_x = int(event.globalPosition().x()) - self.drag_start_x
            self.update_position_from_drag(delta_x)

    def update_position_from_drag(self, delta_x: int):
        """Обновление позиции при перетаскивании (60px = 1 день)"""
        if abs(delta_x) < 5:
            return

        days_delta = round(delta_x / 60)

        if days_delta == 0:
            return

        if self.dragging:
            new_start = self.original_start + timedelta(days=days_delta)
            new_end = self.original_end + timedelta(days=days_delta)
            self.bar_moved.emit(self.task_node.id, new_start, new_end)
        elif self.resizing_left:
            new_start = self.original_start + timedelta(days=days_delta)
            if new_start < self.original_end:
                self.bar_resized.emit(self.task_node.id, new_start, self.original_end)
        elif self.resizing_right:
            new_end = self.original_end + timedelta(days=days_delta)
            if new_end > self.original_start:
                self.bar_resized.emit(self.task_node.id, self.original_start, new_end)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing_left = False
        self.resizing_right = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseDoubleClickEvent(self, event):
        self.bar_clicked.emit(self.task_node.id)


class TimelineHeader(QWidget):
    """Виджет заголовка временной шкалы с современным дизайном"""

    def __init__(self, scale: ScaleType, start_date: date, end_date: date, parent=None):
        super().__init__(parent)
        self.scale = scale
        self.start_date = start_date
        self.end_date = end_date
        self.setMinimumHeight(64)
        self.setMaximumHeight(64)
        self.setStyleSheet("""
            background-color: white;
            border-bottom: 1px solid #E2E8F0;
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total_width = self.width()
        date_range = (self.end_date - self.start_date).days + 1

        if date_range <= 0:
            return

        cell_width = total_width / date_range

        # Цвета для разных масштабов
        bg_color = "#FFFFFF"
        line_color = "#E2E8F0"
        text_color = "#1E293B"

        # Шрифты
        main_font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
        sub_font = QFont("Segoe UI", 10)

        painter.fillRect(0, 0, self.width(), self.height(), QColor(bg_color))

        # Рисуем сетку и заголовки
        for i in range(date_range + 1):
            x = int(i * cell_width)
            current_date = self.start_date + timedelta(days=i)

            # Вертикальная линия сетки
            painter.setPen(QPen(QColor(line_color), 1))
            painter.drawLine(x, 0, x, self.height())

            # Текст заголовка
            if i < date_range:
                if self.scale == ScaleType.DAY:
                    # День: показываем число и день недели
                    painter.setPen(QPen(QColor(text_color), 1))
                    painter.setFont(main_font)
                    painter.drawText(QRect(x + 6, 10, int(cell_width) - 12, 22),
                                     Qt.AlignmentFlag.AlignLeft,
                                     current_date.strftime("%d"))

                    painter.setFont(sub_font)
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    painter.drawText(QRect(x + 6, 34, int(cell_width) - 12, 20),
                                     Qt.AlignmentFlag.AlignLeft,
                                     self.get_weekday_name(current_date))

                elif self.scale == ScaleType.WEEK:
                    # Неделя: показываем диапазон дат
                    week_start = current_date - timedelta(days=current_date.weekday())
                    week_end = week_start + timedelta(days=6)

                    painter.setFont(main_font)
                    painter.setPen(QPen(QColor(text_color), 1))
                    date_range_text = f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m')}"
                    painter.drawText(QRect(x + 6, 12, int(cell_width) - 12, 24),
                                     Qt.AlignmentFlag.AlignLeft,
                                     date_range_text)

                    painter.setFont(sub_font)
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    week_num = current_date.isocalendar()[1]
                    painter.drawText(QRect(x + 6, 38, int(cell_width) - 12, 20),
                                     Qt.AlignmentFlag.AlignLeft,
                                     f"Неделя {week_num}, {current_date.year}")

                elif self.scale == ScaleType.MONTH:
                    # Месяц: название месяца и год
                    painter.setFont(main_font)
                    painter.setPen(QPen(QColor(text_color), 1))
                    painter.drawText(QRect(x + 6, 12, int(cell_width) - 12, 30),
                                     Qt.AlignmentFlag.AlignLeft,
                                     current_date.strftime("%B %Y"))

                    painter.setFont(sub_font)
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    # Показываем количество дней в месяце
                    if current_date.month == 12:
                        next_month = date(current_date.year + 1, 1, 1)
                    else:
                        next_month = date(current_date.year, current_date.month + 1, 1)
                    days_in_month = (next_month - date(current_date.year, current_date.month, 1)).days
                    painter.drawText(QRect(x + 6, 42, int(cell_width) - 12, 20),
                                     Qt.AlignmentFlag.AlignLeft,
                                     f"{days_in_month} дней")

                else:  # QUARTER
                    quarter = (current_date.month - 1) // 3 + 1
                    painter.setFont(main_font)
                    painter.setPen(QPen(QColor(text_color), 1))
                    painter.drawText(QRect(x + 6, 12, int(cell_width) - 12, 30),
                                     Qt.AlignmentFlag.AlignLeft,
                                     f"Q{quarter} {current_date.year}")

                    painter.setFont(sub_font)
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    # Показываем месяцы квартала
                    quarter_months = {
                        1: "Янв-Мар", 2: "Апр-Июн", 3: "Июл-Сен", 4: "Окт-Дек"
                    }
                    painter.drawText(QRect(x + 6, 42, int(cell_width) - 12, 20),
                                     Qt.AlignmentFlag.AlignLeft,
                                     quarter_months.get(quarter, ""))

        # Рисуем линию сегодняшней даты (красная)
        today = date.today()
        if self.start_date <= today <= self.end_date:
            days_from_start = (today - self.start_date).days
            today_x = int(days_from_start * cell_width)

            painter.setPen(QPen(QColor("#EF4444"), 2))
            painter.drawLine(today_x, 0, today_x, self.height())

            # Подпись "Сегодня"
            painter.setPen(QPen(QColor("#EF4444"), 1))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRect(today_x + 6, 20, 80, 24),
                             Qt.AlignmentFlag.AlignLeft, "📅 Сегодня")

    def get_weekday_name(self, date_obj: date) -> str:
        """Возвращает название дня недели"""
        weekdays = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        return weekdays[date_obj.weekday()]


class GanttChartWidget(QWidget):
    """Основной виджет диаграммы Ганта"""

    task_selected = pyqtSignal(int)
    task_updated = pyqtSignal(int, dict)

    def __init__(self, service: ProjectsService, project_id: int = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.project_id = project_id

        self.tasks: List[GanttTaskNode] = []
        self.flat_tasks: List[GanttTaskNode] = []
        self.scale = ScaleType.WEEK
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=60)

        self.setup_ui()
        self.connect_signals()

        if project_id:
            self.load_project_tasks(project_id)
        else:
            self.load_sample_data()

        # Инициализируем таймер для обновления при изменении размера
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.refresh_display)

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)

        # Основной сплиттер
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E2E8F0;
                width: 1px;
            }
        """)

        # Левая панель с задачами
        self.tasks_panel = self.create_tasks_panel()
        splitter.addWidget(self.tasks_panel)

        # Правая панель с диаграммой
        self.chart_panel = self.create_chart_panel()
        splitter.addWidget(self.chart_panel)

        splitter.setSizes([400, 1000])

        main_layout.addWidget(splitter)

    def create_toolbar(self) -> QFrame:
        """Создание панели инструментов"""
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #E2E8F0;
            }
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("📊 Диаграмма Ганта")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        layout.addWidget(title)

        layout.addStretch()

        # Масштаб
        scale_container = QFrame()
        scale_layout = QHBoxLayout(scale_container)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(8)

        scale_label = QLabel("Масштаб:")
        scale_label.setStyleSheet("color: #64748B; font-size: 13px;")
        scale_layout.addWidget(scale_label)

        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["День", "Неделя", "Месяц", "Квартал"])
        self.scale_combo.setCurrentIndex(1)
        self.scale_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scale_combo.setStyleSheet("""
            QComboBox {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #CBD5E1;
                background-color: #F1F5F9;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        scale_layout.addWidget(self.scale_combo)
        layout.addWidget(scale_container)

        # Разделитель
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(separator)

        # Кнопки управления
        btn_style = """
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
                color: #1E293B;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #CBD5E1;
            }
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """

        self.btn_zoom_out = QPushButton("🔍 Уменьшить")
        self.btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_out.setStyleSheet(btn_style)
        layout.addWidget(self.btn_zoom_out)

        self.btn_zoom_in = QPushButton("🔍 Увеличить")
        self.btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_in.setStyleSheet(btn_style)
        layout.addWidget(self.btn_zoom_in)

        self.btn_fit = QPushButton("⟷ Вписать")
        self.btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fit.setStyleSheet(btn_style)
        layout.addWidget(self.btn_fit)

        self.btn_today = QPushButton("📅 Сегодня")
        self.btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_today.setStyleSheet(btn_style)
        layout.addWidget(self.btn_today)

        self.btn_expand_all = QPushButton("📂 Развернуть всё")
        self.btn_expand_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand_all.setStyleSheet(btn_style)
        layout.addWidget(self.btn_expand_all)

        self.btn_collapse_all = QPushButton("📁 Свернуть всё")
        self.btn_collapse_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse_all.setStyleSheet(btn_style)
        layout.addWidget(self.btn_collapse_all)

        return toolbar

    def create_tasks_panel(self) -> QWidget:
        """Создание панели со списком задач"""
        panel = QWidget()
        panel.setStyleSheet("background-color: white;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Заголовок
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("border-bottom: 1px solid #E2E8F0; background-color: white;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        header_title = QLabel("📋 Список задач")
        header_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #475569;")

        header_subtitle = QLabel("Двойной клик для редактирования")
        header_subtitle.setStyleSheet("font-size: 11px; color: #94A3B8;")

        header_layout.addWidget(header_title)
        header_layout.addWidget(header_subtitle)

        layout.addWidget(header)

        # Scroll area для задач
        self.tasks_scroll = ModernScrollArea()
        self.tasks_scroll.setWidgetResizable(True)

        self.tasks_content = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_content)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(0)
        self.tasks_layout.addStretch()

        self.tasks_scroll.setWidget(self.tasks_content)
        layout.addWidget(self.tasks_scroll)

        return panel

    def create_chart_panel(self) -> QWidget:
        """Создание панели с диаграммой"""
        panel = QWidget()
        panel.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Заголовок временной шкалы
        self.timeline_header_container = QWidget()
        self.timeline_header_container.setFixedHeight(64)
        layout.addWidget(self.timeline_header_container)

        # Scroll area для диаграммы
        self.chart_scroll = ModernScrollArea()
        self.chart_scroll.setWidgetResizable(True)

        # Контейнер для содержимого диаграммы
        self.chart_content_container = QWidget()
        self.chart_content_layout = QVBoxLayout(self.chart_content_container)
        self.chart_content_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_content_layout.setSpacing(0)

        # Скроллируемая область для полос задач
        self.chart_scroll_area = QWidget()
        self.chart_scroll_layout = QVBoxLayout(self.chart_scroll_area)
        self.chart_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_scroll_layout.setSpacing(0)
        self.chart_scroll_layout.addStretch()

        self.chart_content_layout.addWidget(self.chart_scroll_area)
        self.chart_scroll.setWidget(self.chart_content_container)

        layout.addWidget(self.chart_scroll)

        return panel

    def connect_signals(self):
        """Подключение сигналов"""
        self.scale_combo.currentTextChanged.connect(self.on_scale_changed)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_fit.clicked.connect(self.fit_to_screen)
        self.btn_today.clicked.connect(self.go_to_today)
        self.btn_expand_all.clicked.connect(self.expand_all)
        self.btn_collapse_all.clicked.connect(self.collapse_all)

        # Синхронизация прокрутки
        self.tasks_scroll.verticalScrollBar().valueChanged.connect(
            self.chart_scroll.verticalScrollBar().setValue
        )
        self.chart_scroll.verticalScrollBar().valueChanged.connect(
            self.tasks_scroll.verticalScrollBar().setValue
        )

    def load_project_tasks(self, project_id: int):
        """Загрузка задач проекта из сервиса"""
        try:
            from services.tasks_service import TasksService
            tasks_service = TasksService(self.service.session)
            db_tasks = tasks_service.get_project_tasks(project_id)

            self.tasks = self.convert_to_gantt_nodes(db_tasks)
            self.build_hierarchy()
            self.calculate_date_range()
            self.refresh_display()

        except Exception as e:
            print(f"Ошибка загрузки задач проекта: {e}")
            self.load_sample_data()

    def convert_to_gantt_nodes(self, db_tasks: List[TaskDTO]) -> List[GanttTaskNode]:
        """Конвертация TaskDTO в GanttTaskNode"""
        nodes = []
        for task in db_tasks:
            node = GanttTaskNode(
                id=task.id,
                title=task.title,
                start_date=task.deadline.date() if task.deadline else None,
                end_date=task.deadline.date() if task.deadline else None,
                priority=task.priority,
                progress=0,
                parent_id=None,
                assigned_to_id=task.assigned_to if hasattr(task, 'assigned_to') else None,
                description=task.description if hasattr(task, 'description') else None
            )
            nodes.append(node)
        return nodes

    def build_hierarchy(self):
        """Построение иерархии задач"""
        if not self.tasks:
            return

        task_dict = {task.id: task for task in self.tasks}
        root_tasks = []

        for task in self.tasks:
            if task.parent_id and task.parent_id in task_dict:
                parent = task_dict[task.parent_id]
                parent.children.append(task)
            else:
                root_tasks.append(task)

        self.tasks = root_tasks

    def load_sample_data(self):
        """Загрузка демонстрационных данных с красивым дизайном"""
        today = date.today()

        self.tasks = [
            GanttTaskNode(
                id=1,
                title="🚀 Запуск проекта",
                start_date=today,
                end_date=today + timedelta(days=2),
                priority=TaskPriority.critical,
                progress=100,
                is_milestone=True,
                assigned_to_name="Алексей Смирнов"
            ),
            GanttTaskNode(
                id=2,
                title="📋 Анализ требований",
                start_date=today,
                end_date=today + timedelta(days=7),
                priority=TaskPriority.high,
                progress=80,
                assigned_to_name="Мария Иванова",
                children=[
                    GanttTaskNode(
                        id=3, title="Сбор требований",
                        start_date=today, end_date=today + timedelta(days=3),
                        priority=TaskPriority.high, progress=100,
                        assigned_to_name="Мария Иванова", parent_id=2
                    ),
                    GanttTaskNode(
                        id=4, title="Анализ рынка",
                        start_date=today + timedelta(days=1), end_date=today + timedelta(days=5),
                        priority=TaskPriority.medium, progress=60,
                        assigned_to_name="Дмитрий Петров", parent_id=2
                    ),
                    GanttTaskNode(
                        id=5, title="Составление ТЗ",
                        start_date=today + timedelta(days=4), end_date=today + timedelta(days=7),
                        priority=TaskPriority.high, progress=40,
                        assigned_to_name="Мария Иванова", parent_id=2
                    )
                ]
            ),
            GanttTaskNode(
                id=6,
                title="🎨 Дизайн",
                start_date=today + timedelta(days=3),
                end_date=today + timedelta(days=12),
                priority=TaskPriority.medium,
                progress=50,
                assigned_to_name="Анна Соколова",
                children=[
                    GanttTaskNode(
                        id=7, title="UI/UX дизайн",
                        start_date=today + timedelta(days=3), end_date=today + timedelta(days=9),
                        priority=TaskPriority.medium, progress=60,
                        assigned_to_name="Анна Соколова", parent_id=6
                    ),
                    GanttTaskNode(
                        id=8, title="Создание макетов",
                        start_date=today + timedelta(days=7), end_date=today + timedelta(days=12),
                        priority=TaskPriority.low, progress=30,
                        assigned_to_name="Павел Новиков", parent_id=6
                    )
                ]
            ),
            GanttTaskNode(
                id=9,
                title="💻 Разработка",
                start_date=today + timedelta(days=8),
                end_date=today + timedelta(days=28),
                priority=TaskPriority.critical,
                progress=20,
                assigned_to_name="Олег Козлов",
                children=[
                    GanttTaskNode(
                        id=10, title="Backend API",
                        start_date=today + timedelta(days=8), end_date=today + timedelta(days=20),
                        priority=TaskPriority.high, progress=25,
                        assigned_to_name="Олег Козлов", parent_id=9
                    ),
                    GanttTaskNode(
                        id=11, title="Frontend",
                        start_date=today + timedelta(days=10), end_date=today + timedelta(days=24),
                        priority=TaskPriority.high, progress=15,
                        assigned_to_name="Екатерина Волкова", parent_id=9
                    ),
                    GanttTaskNode(
                        id=12, title="База данных",
                        start_date=today + timedelta(days=8), end_date=today + timedelta(days=16),
                        priority=TaskPriority.high, progress=40,
                        assigned_to_name="Игорь Морозов", parent_id=9
                    )
                ]
            ),
            GanttTaskNode(
                id=13,
                title="🧪 Тестирование",
                start_date=today + timedelta(days=22),
                end_date=today + timedelta(days=32),
                priority=TaskPriority.high,
                progress=0,
                assigned_to_name="Светлана Орлова",
                children=[
                    GanttTaskNode(
                        id=14, title="Unit тесты",
                        start_date=today + timedelta(days=22), end_date=today + timedelta(days=27),
                        priority=TaskPriority.medium, progress=0,
                        assigned_to_name="Светлана Орлова", parent_id=13
                    ),
                    GanttTaskNode(
                        id=15, title="Интеграционное тестирование",
                        start_date=today + timedelta(days=27), end_date=today + timedelta(days=32),
                        priority=TaskPriority.high, progress=0,
                        assigned_to_name="Андрей Белов", parent_id=13
                    )
                ]
            ),
            GanttTaskNode(
                id=16,
                title="🚀 Релиз продукта",
                start_date=today + timedelta(days=35),
                end_date=today + timedelta(days=35),
                priority=TaskPriority.critical,
                progress=0,
                is_milestone=True,
                assigned_to_name="Алексей Смирнов"
            )
        ]

        self.calculate_date_range()
        self.refresh_display()

    def flatten_tasks(self, tasks: List[GanttTaskNode], level: int = 0) -> List[GanttTaskNode]:
        """Разворачивает иерархию задач в плоский список"""
        flat = []
        for task in tasks:
            task.level = level
            flat.append(task)

            if task.children and task.is_expanded:
                flat.extend(self.flatten_tasks(task.children, level + 1))
        return flat

    def calculate_date_range(self):
        """Расчет диапазона дат на основе задач"""
        all_tasks = self.flatten_tasks(self.tasks)

        if not all_tasks:
            self.start_date = date.today()
            self.end_date = date.today() + timedelta(days=30)
            return

        min_date = None
        max_date = None

        for task in all_tasks:
            if task.start_date:
                if min_date is None or task.start_date < min_date:
                    min_date = task.start_date
            if task.end_date:
                if max_date is None or task.end_date > max_date:
                    max_date = task.end_date

        if min_date:
            self.start_date = min_date - timedelta(days=5)
        else:
            self.start_date = date.today()

        if max_date:
            self.end_date = max_date + timedelta(days=5)
        else:
            self.end_date = date.today() + timedelta(days=30)

    def refresh_display(self):
        """Обновление отображения диаграммы"""
        self.flat_tasks = self.flatten_tasks(self.tasks)

        self.update_tasks_panel()
        self.update_chart()
        self.update_timeline_header()

    def update_tasks_panel(self):
        """Обновление панели со списком задач"""
        # Очищаем существующие виджеты
        while self.tasks_layout.count() > 1:
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавляем задачи
        for task in self.flat_tasks:
            task_widget = TaskItemWidget(task)
            task_widget.task_clicked.connect(self.on_task_clicked)
            task_widget.task_double_clicked.connect(self.on_task_double_clicked)
            task_widget.toggle_expand.connect(self.toggle_task_expand)
            self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, task_widget)

    def update_chart(self):
        """Обновление диаграммы"""
        # Очищаем существующие виджеты
        while self.chart_scroll_layout.count() > 1:
            item = self.chart_scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Получаем ширину контейнера
        chart_width = self.chart_scroll_area.width()
        if chart_width <= 0:
            chart_width = 800

        date_range = (self.end_date - self.start_date).days + 1
        if date_range <= 0:
            return

        # Рассчитываем пиксели на день
        pixels_per_day = chart_width / date_range

        # Для каждой задачи создаем полосу
        for i, task in enumerate(self.flat_tasks):
            if task.start_date and task.end_date:
                days_from_start = (task.start_date - self.start_date).days
                duration = task.duration_days

                x_pos = int(days_from_start * pixels_per_day)
                width = int(duration * pixels_per_day)

                if width < 30:
                    width = 30

                # Создаем контейнер для полосы задачи
                task_row = QWidget()
                task_row.setFixedHeight(60)
                task_row_layout = QVBoxLayout(task_row)
                task_row_layout.setContentsMargins(0, 5, 0, 5)
                task_row_layout.setSpacing(0)

                bar_widget = GanttBarWidget(task, task.start_date, task.end_date, x_pos, width)
                bar_widget.bar_clicked.connect(self.on_task_clicked)
                bar_widget.bar_moved.connect(self.on_task_moved)
                bar_widget.bar_resized.connect(self.on_task_resized)

                task_row_layout.addWidget(bar_widget)
                self.chart_scroll_layout.insertWidget(self.chart_scroll_layout.count() - 1, task_row)

        # Обновляем минимальную ширину для скроллинга
        self.chart_scroll_area.setMinimumWidth(int(date_range * pixels_per_day) + 100)

    def update_timeline_header(self):
        """Обновление заголовка временной шкалы"""
        # Очищаем существующие виджеты
        for child in self.timeline_header_container.findChildren(QWidget):
            child.deleteLater()

        layout = QVBoxLayout(self.timeline_header_container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Устанавливаем размер заголовка в соответствии с шириной диаграммы
        timeline_header = TimelineHeader(self.scale, self.start_date, self.end_date)

        # Устанавливаем минимальную ширину заголовка
        chart_width = self.chart_scroll_area.width()
        if chart_width > 0:
            date_range = (self.end_date - self.start_date).days + 1
            if date_range > 0:
                timeline_header.setMinimumWidth(int(date_range * (chart_width / date_range)) + 100)

        layout.addWidget(timeline_header)

    def on_scale_changed(self, scale_text: str):
        """Обработчик изменения масштаба"""
        scale_map = {
            "День": ScaleType.DAY,
            "Неделя": ScaleType.WEEK,
            "Месяц": ScaleType.MONTH,
            "Квартал": ScaleType.QUARTER
        }
        self.scale = scale_map.get(scale_text, ScaleType.WEEK)

        # Корректируем диапазон дат в зависимости от масштаба
        if self.scale == ScaleType.DAY:
            # Для дней показываем 30 дней
            center_date = self.start_date + (self.end_date - self.start_date) / 2
            self.start_date = center_date - timedelta(days=15)
            self.end_date = center_date + timedelta(days=15)
        elif self.scale == ScaleType.WEEK:
            # Для недель показываем 12 недель
            center_date = self.start_date + (self.end_date - self.start_date) / 2
            self.start_date = center_date - timedelta(days=42)
            self.end_date = center_date + timedelta(days=42)
        elif self.scale == ScaleType.MONTH:
            # Для месяцев показываем 6 месяцев
            center_date = self.start_date + (self.end_date - self.start_date) / 2
            self.start_date = center_date - timedelta(days=90)
            self.end_date = center_date + timedelta(days=90)
        else:  # QUARTER
            # Для кварталов показываем 8 кварталов
            center_date = self.start_date + (self.end_date - self.start_date) / 2
            self.start_date = center_date - timedelta(days=365)
            self.end_date = center_date + timedelta(days=365)

        self.refresh_display()

    def zoom_in(self):
        """Увеличение масштаба"""
        center_date = self.start_date + (self.end_date - self.start_date) / 2
        days_range = (self.end_date - self.start_date).days

        # Уменьшаем диапазон на 20%
        new_days_range = int(days_range * 0.8)

        self.start_date = center_date - timedelta(days=int(new_days_range / 2))
        self.end_date = center_date + timedelta(days=int(new_days_range / 2))

        # Гарантируем минимальный диапазон
        if (self.end_date - self.start_date).days < 1:
            self.end_date = self.start_date + timedelta(days=1)

        self.refresh_display()

    def zoom_out(self):
        """Уменьшение масштаба"""
        center_date = self.start_date + (self.end_date - self.start_date) / 2
        days_range = (self.end_date - self.start_date).days

        # Увеличиваем диапазон на 20%
        new_days_range = int(days_range * 1.2)

        self.start_date = center_date - timedelta(days=int(new_days_range / 2))
        self.end_date = center_date + timedelta(days=int(new_days_range / 2))

        self.refresh_display()

    def fit_to_screen(self):
        """Вписать диаграмму в окно"""
        self.calculate_date_range()
        # Добавляем небольшой отступ
        self.start_date = self.start_date - timedelta(days=3)
        self.end_date = self.end_date + timedelta(days=3)
        self.refresh_display()

    def go_to_today(self):
        """Переход к сегодняшней дате"""
        today = date.today()
        days_range = (self.end_date - self.start_date).days

        # Центрируем на сегодняшней дате
        self.start_date = today - timedelta(days=int(days_range / 2))
        self.end_date = today + timedelta(days=int(days_range / 2))

        self.refresh_display()

    def expand_all(self):
        """Развернуть все задачи"""
        def expand_recursive(tasks):
            for task in tasks:
                task.is_expanded = True
                if task.children:
                    expand_recursive(task.children)

        expand_recursive(self.tasks)
        self.refresh_display()

    def collapse_all(self):
        """Свернуть все задачи"""
        def collapse_recursive(tasks):
            for task in tasks:
                task.is_expanded = False
                if task.children:
                    collapse_recursive(task.children)

        collapse_recursive(self.tasks)
        self.refresh_display()

    def toggle_task_expand(self, task_id: int):
        """Переключение раскрытия задачи"""
        def find_and_toggle(tasks):
            for task in tasks:
                if task.id == task_id:
                    task.is_expanded = not task.is_expanded
                    return True
                if task.children and find_and_toggle(task.children):
                    return True
            return False

        find_and_toggle(self.tasks)
        self.refresh_display()

    def on_task_clicked(self, task_id: int):
        """Обработчик клика по задаче"""
        self.task_selected.emit(task_id)
        print(f"Выбрана задача ID: {task_id}")

    def on_task_double_clicked(self, task_id: int):
        """Обработчик двойного клика по задаче"""
        QMessageBox.information(self, "Редактирование задачи",
                                f"✏️ Открыть задачу {task_id} для редактирования\n\n"
                                "Здесь можно будет изменить название, даты, приоритет и ответственного.")

    def on_task_moved(self, task_id: int, new_start: date, new_end: date):
        """Обработчик перемещения задачи"""
        print(f"Перемещена задача {task_id}: {new_start} - {new_end}")
        self.task_updated.emit(task_id, {
            'start_date': new_start,
            'end_date': new_end
        })

    def on_task_resized(self, task_id: int, new_start: date, new_end: date):
        """Обработчик изменения размера задачи"""
        print(f"Изменен размер задачи {task_id}: {new_start} - {new_end}")
        self.task_updated.emit(task_id, {
            'start_date': new_start,
            'end_date': new_end
        })

    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        # Используем таймер для debouncing обновлений
        self.resize_timer.start(100)


# Для тестирования отдельно
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Стиль приложения
    app.setStyle("Fusion")

    # Создаем тестовый сервис
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    mock_service = ProjectsService(mock_session)

    # Создаем виджет
    gantt_widget = GanttChartWidget(mock_service, project_id=None)

    # Создаем главное окно
    window = QMainWindow()
    window.setCentralWidget(gantt_widget)
    window.setWindowTitle("📊 Диаграмма Ганта - МАЗ Project Management")
    window.setMinimumSize(1200, 700)
    window.resize(1400, 900)
    window.setStyleSheet("""
        QMainWindow {
            background-color: #F8FAFC;
        }
    """)
    window.show()

    sys.exit(app.exec())