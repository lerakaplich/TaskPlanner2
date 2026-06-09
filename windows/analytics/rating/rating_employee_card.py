# windows/analytics/rating/rating_employee_card.py

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.uic import loadUi
import os


class ToolTipWidget(QFrame):
    """Кастомный тултип с белым фоном"""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(27, 35, 42))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(4)


class RatingEmployeeCard(QFrame):
    """Карточка сотрудника для рейтинга с КПД - только UI"""

    clicked = pyqtSignal(int)

    def __init__(self, employee_data, position=0, parent=None):
        super().__init__(parent)

        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position

        # UI элементы
        self.position_label = None
        self.name_label = None
        self.dept_label = None
        self.stats_label = None
        self.kpd_label = None
        self.weighted_label = None
        self.progress_bar = None
        self.overtime_label = None

        self.tooltip_widget = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_tooltip)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """Создание UI карточки"""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(70)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)

        # Позиция
        self.position_label = QLabel()
        self.position_label.setFixedSize(50, 50)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.position_label)

        # Информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
        self.name_label.setWordWrap(True)
        info_layout.addWidget(self.name_label)

        self.dept_label = QLabel()
        self.dept_label.setStyleSheet("color: #666; font-size: 11px;")
        self.dept_label.setWordWrap(True)
        info_layout.addWidget(self.dept_label)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(self.stats_label)

        main_layout.addLayout(info_layout, stretch=1)

        # КПД блок
        kpd_layout = QVBoxLayout()
        kpd_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.kpd_label = QLabel()
        self.kpd_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        kpd_layout.addWidget(self.kpd_label)

        self.weighted_label = QLabel()
        self.weighted_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.weighted_label.setStyleSheet("color: #888; font-size: 10px;")
        self.weighted_label.setVisible(False)
        kpd_layout.addWidget(self.weighted_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        kpd_layout.addWidget(self.progress_bar)

        self.overtime_label = QLabel()
        self.overtime_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.overtime_label.setVisible(False)
        kpd_layout.addWidget(self.overtime_label)

        main_layout.addLayout(kpd_layout)

    def _update_display(self):
        """Обновляет отображение данных"""
        data = self.employee_data

        # Позиция
        colors = {0: "#FFD700", 1: "#C0C0C0", 2: "#CD7F32"}
        color = colors.get(self.position, "#E0E0E0")
        font_size = "24px" if self.position < 3 else "18px"
        text_color = '#333' if self.position < 3 else '#666'

        self.position_label.setText(str(self.position + 1))
        self.position_label.setStyleSheet(f"""
            background-color: {color};
            border-radius: 25px;
            font-size: {font_size};
            font-weight: bold;
            color: {text_color};
        """)

        # Имя
        self.name_label.setText(data.get('name', 'Без имени'))

        # Должность и отдел
        parts = []
        if data.get('position'):
            parts.append(data['position'])
        if data.get('department'):
            parts.append(data['department'])
        if data.get('subdivision'):
            parts.append(data['subdivision'])
        self.dept_label.setText(' · '.join(parts) if parts else '—')

        # Статистика
        completed = data.get('completed_tasks', 0)
        total = data.get('total_tasks', 0)
        on_time = data.get('on_time_rate', 0)

        stats = f"📊 Задач: {completed} из {total}"
        if on_time > 0:
            stats += f" · В срок: {on_time:.0f}%"
        self.stats_label.setText(stats)

        sub_count = data.get('subordinates_count', 0)
        if sub_count > 0:
            self.stats_label.setText(f"📊 Задач: {completed} из {total} · 👥 {sub_count} подчинённых")

        # КПД
        kpd = data.get('kpd_percent', 0)
        if kpd == 0 and total > 0:
            kpd = (completed / total * 100) if total > 0 else 0

        weighted = data.get('weighted_kpd', 0)
        overtime = data.get('overtime_hours', 0)

        # Цвет КПД
        if kpd >= 80:
            kpd_color = "#2ecc71"
        elif kpd >= 60:
            kpd_color = "#f1c40f"
        elif kpd >= 40:
            kpd_color = "#e67e22"
        else:
            kpd_color = "#e74c3c"


        self.kpd_label.setText(f"{kpd:.1f}%")
        self.kpd_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {kpd_color};")

        # Взвешенный КПД
        if weighted > 0 and weighted != kpd:
            self.weighted_label.setText(f"взв: {weighted:.1f}%")
            self.weighted_label.setVisible(True)

        # Прогресс-бар
        self.progress_bar.setValue(int(kpd))

        # Градиент для прогресс-бара
        if kpd >= 80:
            gradient = "stop:0 #2ecc71, stop:1 #27ae60"
        elif kpd >= 60:
            gradient = "stop:0 #f1c40f, stop:1 #f39c12"
        elif kpd >= 40:
            gradient = "stop:0 #e67e22, stop:1 #d35400"
        else:
            gradient = "stop:0 #e74c3c, stop:1 #c0392b"

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, {gradient});
                border-radius: 4px;
            }}
        """)

        # Переработки
        if overtime > 0:
            if overtime > 40:
                ot_color = "#e74c3c"
            elif overtime > 20:
                ot_color = "#e67e22"
            else:
                ot_color = "#2ecc71"

            self.overtime_label.setText(f"⏱️ +{overtime:.1f} ч")
            self.overtime_label.setStyleSheet(f"color: {ot_color}; font-size: 11px;")
            self.overtime_label.setVisible(True)

        # Сохраняем данные для тултипа
        self._tooltip_data = {
            'kpd': kpd,
            'weighted': weighted,
            'overtime': overtime,
            'total': total,
            'completed': completed,
            'on_time': on_time
        }

    def _create_tooltip(self):
        """Создаёт тултип"""
        if self.tooltip_widget:
            self._clear_tooltip()

        self.tooltip_widget = ToolTipWidget()
        data = self._tooltip_data

        # Имя
        name_label = QLabel(f"👤 {self.employee_data.get('name', '—')}")
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1B232A;")
        self.tooltip_widget.layout.addWidget(name_label)

        # Должность
        position_label = QLabel(f"📋 {self.employee_data.get('position', '—')}")
        position_label.setStyleSheet("color: #666; font-size: 12px;")
        self.tooltip_widget.layout.addWidget(position_label)

        # Отдел
        dept = self.employee_data.get('department', '')
        if dept:
            dept_label = QLabel(f"🏢 {dept}")
            dept_label.setStyleSheet("color: #888; font-size: 11px;")
            self.tooltip_widget.layout.addWidget(dept_label)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #eee; max-height: 1px;")
        self.tooltip_widget.layout.addWidget(separator)

        # Статистика
        stats = [
            f"✅ Выполнено: {data['completed']} из {data['total']}",
            f"🎯 В срок: {data['on_time']:.1f}%",
        ]

        # КПД с цветом
        if data['kpd'] >= 80:
            kpd_color = "#2ecc71"
        elif data['kpd'] >= 60:
            kpd_color = "#f1c40f"
        elif data['kpd'] >= 40:
            kpd_color = "#e67e22"
        else:
            kpd_color = "#e74c3c"

        kpd_label = QLabel(f'⚡️ КПД: <b style="color: {kpd_color};">{data["kpd"]:.1f}%</b>')
        kpd_label.setTextFormat(Qt.TextFormat.RichText)
        self.tooltip_widget.layout.addWidget(kpd_label)

        for stat in stats:
            stat_label = QLabel(stat)
            stat_label.setStyleSheet("color: #555; font-size: 12px;")
            self.tooltip_widget.layout.addWidget(stat_label)

        if data['weighted'] > 0:
            w_label = QLabel(f"🎯 Взвешенный: {data['weighted']:.1f}%")
            w_label.setStyleSheet("color: #555; font-size: 12px;")
            self.tooltip_widget.layout.addWidget(w_label)

        if data['overtime'] > 0:
            if data['overtime'] > 40:
                ot_color = "#e74c3c"
            elif data['overtime'] > 20:
                ot_color = "#e67e22"
            else:
                ot_color = "#2ecc71"
            ot_label = QLabel(f'⏱️ Переработки: <b style="color: {ot_color};">{data["overtime"]:.1f} ч</b>')
            ot_label.setTextFormat(Qt.TextFormat.RichText)
            self.tooltip_widget.layout.addWidget(ot_label)

        self.tooltip_widget.adjustSize()

    def _clear_tooltip(self):
        """Очистка тултипа"""
        if self.tooltip_widget:
            while self.tooltip_widget.layout.count():
                item = self.tooltip_widget.layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def _show_tooltip(self):
        """Показать тултип"""
        if not self.tooltip_widget:
            self._create_tooltip()
        pos = self.mapToGlobal(QPoint(10, self.height() + 5))
        self.tooltip_widget.move(pos)
        self.tooltip_widget.show()

    def _hide_tooltip(self):
        """Скрыть тултип"""
        if self.tooltip_widget:
            self.tooltip_widget.hide()

    def enterEvent(self, event):
        self._hide_timer.stop()
        if hasattr(self, '_tooltip_data'):
            self._show_tooltip()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_timer.start(100)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._hide_tooltip()
        if self.employee_id:
            self.clicked.emit(self.employee_id)
        super().mousePressEvent(event)

    def update_data(self, employee_data, position=0):
        """Обновление данных карточки"""
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        if self.tooltip_widget:
            self.tooltip_widget.hide()
            self.tooltip_widget.deleteLater()
            self.tooltip_widget = None
        self._update_display()

    def closeEvent(self, event):
        if self.tooltip_widget:
            self.tooltip_widget.deleteLater()
            self.tooltip_widget = None
        super().closeEvent(event)