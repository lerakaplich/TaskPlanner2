# windows/profile/chart_widget.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from services.profile_service import ProfileService


class BarChartWidget(QWidget):
    """Виджет для отрисовки столбчатой диаграммы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setMinimumWidth(550)

        self.topics = []
        self.kpd_values = []
        self.colors = ['#D22730', '#ccab6e', '#1B232A', '#862633', '#A26D03',
                       '#088136', '#1C6971', '#D9D9D6']

        self.bar_width = 40
        self.bar_spacing = 60
        self.margin_left = 60
        self.margin_right = 30
        self.margin_top = 40
        self.margin_bottom = 70

    def set_data(self, topics, kpd_values):
        """Установка данных для графика"""
        self.topics = topics
        self.kpd_values = kpd_values
        self.update()

    def paintEvent(self, event):
        """Отрисовка графика"""
        if not self.topics or not self.kpd_values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        painter.fillRect(0, 0, width, height, QBrush(QColor(255, 255, 255)))

        chart_width = width - self.margin_left - self.margin_right
        chart_height = height - self.margin_top - self.margin_bottom

        if chart_width <= 0 or chart_height <= 0:
            return

        n_bars = len(self.topics)
        if n_bars == 0:
            return

        total_width = n_bars * self.bar_width + (n_bars - 1) * self.bar_spacing
        start_x = self.margin_left + (chart_width - total_width) / 2

        painter.setPen(QPen(QColor('#E0E0E0'), 1, Qt.PenStyle.SolidLine))

        for i in range(0, 11):
            y = self.margin_top + chart_height - (i * chart_height / 10)
            if y > self.margin_top and y < height - self.margin_bottom:
                painter.drawLine(self.margin_left - 5, int(y), width - self.margin_right, int(y))
                painter.setPen(QPen(QColor('#666'), 1))
                painter.setFont(QFont('Segoe UI', 8))
                painter.drawText(5, int(y + 3), f"{i / 10:.1f}")
                painter.setPen(QPen(QColor('#E0E0E0'), 1))

        painter.setPen(QPen(QColor('#999'), 1))
        painter.drawLine(self.margin_left, self.margin_top,
                         self.margin_left, height - self.margin_bottom)
        painter.drawLine(self.margin_left, height - self.margin_bottom,
                         width - self.margin_right, height - self.margin_bottom)

        for i, (topic, kpd) in enumerate(zip(self.topics, self.kpd_values)):
            x = int(start_x + i * (self.bar_width + self.bar_spacing))
            bar_height = int(min(kpd * chart_height, chart_height))
            y = int(height - self.margin_bottom - bar_height)

            color = QColor(self.colors[i % len(self.colors)])

            painter.fillRect(x, y, self.bar_width, bar_height, QBrush(color))
            painter.setPen(QPen(QColor('#CCCCCC'), 1))
            painter.drawRect(x, y, self.bar_width, bar_height)

            painter.setPen(QPen(QColor('#1B232A'), 1))
            painter.setFont(QFont('Segoe UI', 10))

            painter.save()
            center_x = x + self.bar_width // 2
            text_y = height - self.margin_bottom + 15
            painter.translate(center_x, text_y)
            painter.rotate(-25)
            painter.drawText(QRect(-150, -15, 300, 40),
                             Qt.AlignmentFlag.AlignCenter,
                             topic)
            painter.restore()


class ChartWidget(QWidget):
    """Виджет с кнопками управления и графиком"""

    refresh_clicked = pyqtSignal()
    export_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.profile_service = None
        self.employee_id = None

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "profile"
        )

        uic.loadUi(os.path.join(ui_path, "chart_widget.ui"), self)

        self.init_chart()
        self.connect_signals()

    def set_profile_service(self, service):
        """Устанавливает сервис профиля"""
        self.profile_service = service

    def set_employee_id(self, employee_id):
        """Устанавливает ID сотрудника"""
        self.employee_id = employee_id

    def load_data(self, employee_id=None):
        """Загружает данные для графика"""
        if employee_id:
            self.employee_id = employee_id

        if self.profile_service and self.employee_id:
            topics, kpd = self.profile_service.get_kpd_chart_data(self.employee_id)
            self.update_chart(topics, kpd)

    # ---------- UI ----------

    def init_chart(self):
        """Инициализирует график"""
        if hasattr(self, "chartContainer"):
            self.bar_chart = BarChartWidget()
            layout = self.chartContainer.layout()

            if layout is None:
                from PyQt6.QtWidgets import QVBoxLayout
                layout = QVBoxLayout()
                self.chartContainer.setLayout(layout)

            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            layout.addWidget(self.bar_chart)

    def connect_signals(self):
        """Подключает сигналы"""
        if hasattr(self, "btnRefresh"):
            self.btnRefresh.clicked.connect(self.on_refresh_clicked)

        if hasattr(self, "btnExport"):
            self.btnExport.clicked.connect(self.on_export_clicked)

    # ---------- CHART ----------

    def update_chart(self, topics, kpd_values):
        """Обновляет данные графика"""
        if hasattr(self, "bar_chart"):
            self.bar_chart.set_data(topics, kpd_values)

    # ---------- ACTIONS ----------

    def on_refresh_clicked(self):
        """Обработчик нажатия на кнопку обновления"""
        if self.profile_service:
            topics, values = self.profile_service.generate_random_kpd_data()
            self.update_chart(topics, values)

            if hasattr(self, "titleLabel"):
                self.titleLabel.setText(self.profile_service.get_chart_updated_title())
                QTimer.singleShot(2000, self.restore_title)

            self.refresh_clicked.emit()

    def restore_title(self):
        """Восстанавливает заголовок графика"""
        if hasattr(self, "titleLabel") and self.profile_service:
            self.titleLabel.setText(self.profile_service.get_chart_title())

    def on_export_clicked(self):
        """Обработчик нажатия на кнопку экспорта"""
        QMessageBox.information(
            self,
            "Экспорт графика",
            "Функция экспорта будет доступна в следующей версии."
        )
        self.export_clicked.emit()