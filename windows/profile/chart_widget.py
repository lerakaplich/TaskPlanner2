import os
import sys
import random

from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PyQt6.uic import loadUi


class BarChartWidget(QWidget):
    """Виджет для отрисовки столбчатой диаграммы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)  # Увеличено
        self.setMinimumWidth(550)  # Увеличено

        # Данные для графика
        self.topics = []
        self.kpd_values = []

        # Цвета в стиле МАЗ
        self.colors = ['#D22730', '#ccab6e', '#1B232A', '#862633', '#A26D03',
                       '#088136', '#1C6971', '#D9D9D6']

        # Настройки отображения - УВЕЛИЧЕННОЕ РАССТОЯНИЕ
        self.bar_width = 40  # Ширина столбца (было 35)
        self.bar_spacing = 60  # РАССТОЯНИЕ МЕЖДУ СТОЛБЦАМИ (было 25, теперь 60)
        self.margin_left = 60  # Отступ слева (увеличено)
        self.margin_right = 30  # Отступ справа
        self.margin_top = 40  # Отступ сверху (увеличено)
        self.margin_bottom = 70  # Отступ снизу (увеличено для подписей)

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

        # Рисуем фон
        painter.fillRect(0, 0, width, height, QBrush(QColor(255, 255, 255)))

        # Определяем область отрисовки
        chart_width = width - self.margin_left - self.margin_right
        chart_height = height - self.margin_top - self.margin_bottom

        if chart_width <= 0 or chart_height <= 0:
            return

        # Рассчитываем позиции баров
        n_bars = len(self.topics)
        if n_bars == 0:
            return

        total_width = n_bars * self.bar_width + (n_bars - 1) * self.bar_spacing
        start_x = self.margin_left + (chart_width - total_width) / 2

        # Рисуем оси и сетку
        painter.setPen(QPen(QColor('#E0E0E0'), 1, Qt.PenStyle.SolidLine))

        # Горизонтальные линии сетки
        for i in range(0, 11):
            y = self.margin_top + chart_height - (i * chart_height / 10)
            if y > self.margin_top and y < height - self.margin_bottom:
                painter.drawLine(self.margin_left - 5, int(y), width - self.margin_right, int(y))

                # Подписи значений
                painter.setPen(QPen(QColor('#666'), 1))
                painter.setFont(QFont('Segoe UI', 8))
                painter.drawText(5, int(y + 3), f"{i / 10:.1f}")
                painter.setPen(QPen(QColor('#E0E0E0'), 1))

        # Вертикальная ось
        painter.setPen(QPen(QColor('#999'), 1))
        painter.drawLine(self.margin_left, self.margin_top,
                         self.margin_left, height - self.margin_bottom)

        # Горизонтальная ось
        painter.drawLine(self.margin_left, height - self.margin_bottom,
                         width - self.margin_right, height - self.margin_bottom)

        # Рисуем столбцы
        for i, (topic, kpd) in enumerate(zip(self.topics, self.kpd_values)):
            x = int(start_x + i * (self.bar_width + self.bar_spacing))
            bar_height = int(min(kpd * chart_height, chart_height))
            y = int(height - self.margin_bottom - bar_height)

            # Выбираем цвет
            color = QColor(self.colors[i % len(self.colors)])

            # Рисуем столбец
            painter.fillRect(x, y, self.bar_width, bar_height, QBrush(color))

            # Обводка
            painter.setPen(QPen(QColor('#CCCCCC'), 1))
            painter.drawRect(x, y, self.bar_width, bar_height)

            # Подпись темы (с поворотом на -45° для длинных названий)
            painter.setPen(QPen(QColor('#1B232A'), 1))
            painter.setFont(QFont('Segoe UI', 10))

            painter.save()  # Сохраняем состояние painter

            # Центр столбца по X
            center_x = x + self.bar_width // 2
            # Позиция текста чуть ниже горизонтальной оси
            text_y = height - self.margin_bottom + 15

            # Перемещаем начало координат и поворачиваем
            painter.translate(center_x, text_y)
            painter.rotate(-25)

            # Рисуем полный текст без обрезки, в прямоугольнике достаточного размера
            # QRect(-150, -15, 300, 40) — подберите размеры под ваши названия
            painter.drawText(QRect(-150, -15, 300, 40),
                             Qt.AlignmentFlag.AlignCenter,
                             topic)  # используем полное topic, без обрезки!

            painter.restore()  # Восстанавливаем состояние painter


class ChartWidget(QWidget):
    """Виджет с графиком, загруженный из UI"""

    # Сигналы
    refresh_clicked = pyqtSignal()
    export_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)


        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "profile"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "chart_widget.ui"), self)

        # Инициализация
        self.init_chart()
        self.connect_signals()

        # Загружаем тестовые данные
        self.load_test_data()

    def setup_basic_ui(self):
        """Создание простого UI если файл не найден"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("График (UI файл не найден)"))
        self.setLayout(layout)

    def init_chart(self):
        """Инициализация кастомного графика"""
        if hasattr(self, 'chartContainer'):
            # Создаем виджет графика
            self.bar_chart = BarChartWidget()

            # Получаем layout контейнера
            layout = self.chartContainer.layout()
            if layout is None:
                # Если layout нет, создаем новый
                layout = QVBoxLayout()
                self.chartContainer.setLayout(layout)

            # Удаляем placeholder если есть
            if hasattr(self, 'placeholderLabel'):
                self.placeholderLabel.hide()

            # Очищаем layout
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Добавляем график
            layout.addWidget(self.bar_chart)

    def connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'btnRefresh'):
            self.btnRefresh.clicked.connect(self.on_refresh_clicked)
        if hasattr(self, 'btnExport'):
            self.btnExport.clicked.connect(self.on_export_clicked)

    def on_refresh_clicked(self):
        """Обработчик кнопки обновления"""
        self.refresh_data()
        self.refresh_clicked.emit()

    def on_export_clicked(self):
        """Обработчик кнопки экспорта"""
        self.export_chart()
        self.export_clicked.emit()

    def load_test_data(self):
        """Загрузка тестовых данных"""
        topics = ['Программирование', 'Документация', 'Оптимизация',
                  'Управление', 'Аналитика', 'Тестирование', 'Дизайн', 'Координация']
        kpd_values = [0.85, 0.92, 0.78, 0.65, 0.58, 0.45, 0.38, 0.72]

        self.update_chart(topics, kpd_values)

    def update_chart(self, topics, kpd_values):
        """Обновление данных графика"""
        if hasattr(self, 'bar_chart'):
            self.bar_chart.set_data(topics, kpd_values)

    def refresh_data(self):
        """Обновление с случайными данными"""
        topics = ['Программирование', 'Документация', 'Оптимизация',
                  'Управление', 'Аналитика', 'Тестирование', 'Дизайн', 'Координация']
        kpd_values = [round(random.uniform(0.3, 0.95), 2) for _ in topics]

        self.update_chart(topics, kpd_values)

        # Обновляем заголовок
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("📊 КПД по темам (обновлено)")
            QTimer.singleShot(2000, self.restore_title)

    def restore_title(self):
        """Восстановление заголовка"""
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("📊 КПД по темам (нормированный)")

    def export_chart(self):
        """Экспорт графика"""
        QMessageBox.information(
            self,
            "Экспорт графика",
            "Функция экспорта будет доступна в следующей версии.",
            QMessageBox.StandardButton.Ok
        )


if __name__ == "__main__":
    # Тестовый запуск
    app = QApplication(sys.argv)

    # Создаем окно для тестирования
    window = QWidget()
    window.setWindowTitle("Тест графика")
    window.resize(600, 300)

    layout = QVBoxLayout()
    chart = ChartWidget()
    layout.addWidget(chart)
    window.setLayout(layout)

    window.show()
    sys.exit(app.exec())