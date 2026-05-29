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

        # Устанавливаем белый фон через палитру (надёжнее чем QSS)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(27, 35, 42))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Дополнительно QSS для надёжности
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
    """Карточка сотрудника для рейтинга с КПД - единый дизайн для БД"""

    clicked = pyqtSignal(int)  # Сигнал при клике на карточку

    def __init__(self, employee_data, position=0, parent=None):
        """
        Args:
            employee_data: dict с данными сотрудника из БД
            position: int (0-based) позиция в рейтинге
            parent: родительский виджет
        """
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        self.tooltip_widget = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_tooltip)

        # Загружаем UI из файла
        self._load_ui()
        # Заполняем данными
        self._setup_dynamic_ui()

        # Включаем отслеживание мыши
        self.setMouseTracking(True)

    def _load_ui(self):
        """Загрузка UI из .ui файла"""
        ui_file_path = r"../../../ui/analytics/rating/rating_employee_card.ui"

        if os.path.exists(ui_file_path):
            loadUi(ui_file_path, self)
            # Получаем ссылки на виджеты после загрузки UI
            self.position_label = self.findChild(QLabel, "positionLabel")
            self.name_label = self.findChild(QLabel, "nameLabel")
            self.dept_label = self.findChild(QLabel, "deptLabel")
            self.stats_label = self.findChild(QLabel, "statsLabel")
            self.kpd_label = self.findChild(QLabel, "kpdLabel")
            self.weighted_label = self.findChild(QLabel, "weightedLabel")
            self.progress_bar = self.findChild(QProgressBar, "progressBar")
            self.overtime_label = self.findChild(QLabel, "overtimeLabel")
        else:
            # Если UI файл не найден, создаем UI программно
            self._init_ui()

    def _init_ui(self):
        """Создание UI программно - единый стиль (fallback)"""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)

        # === ПОЗИЦИЯ ===
        self.position_label = QLabel()
        self.position_label.setFixedSize(50, 50)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.position_label)

        # === ИНФОРМАЦИЯ ===
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

        # === КПД ===
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

    def _setup_dynamic_ui(self):
        """Заполнение карточки данными из БД"""

        # === ПОЗИЦИЯ ===
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

        # === ИМЯ ===
        self.name_label.setText(self.employee_data.get('name', 'Без имени'))

        # === ДОЛЖНОСТЬ И ОТДЕЛ ===
        parts = []
        if self.employee_data.get('position'):
            parts.append(self.employee_data['position'])
        if self.employee_data.get('department'):
            parts.append(self.employee_data['department'])
        if self.employee_data.get('subdivision'):
            parts.append(self.employee_data['subdivision'])

        self.dept_label.setText(' · '.join(parts) if parts else '—')

        # === СТАТИСТИКА ===
        completed = self.employee_data.get('completed_tasks', 0)
        total = self.employee_data.get('total_tasks', 0)
        on_time = self.employee_data.get('on_time_rate', 0)

        stats = f"📊 Задач: {completed} из {total}"
        if on_time > 0:
            stats += f" · В срок: {on_time:.0f}%"
        self.stats_label.setText(stats)

        # === КПД ===
        kpd = self.employee_data.get('kpd_percent', 0)
        if kpd == 0:
            kpd = self.employee_data.get('kpd_rating', 0)
        if kpd == 0 and total > 0:
            kpd = (completed / total * 100)

        weighted = self.employee_data.get('weighted_kpd', 0)
        overtime = self.employee_data.get('overtime_hours', 0)

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
        """Создаём кастомный тултип"""
        if self.tooltip_widget:
            self._clear_tooltip()

        self.tooltip_widget = ToolTipWidget()

        data = self._tooltip_data
        kpd = data['kpd']
        weighted = data['weighted']
        overtime = data['overtime']
        completed = data['completed']
        total = data['total']
        on_time = data['on_time']

        # Имя
        name_label = QLabel(f"👤 {self.employee_data.get('name', '—')}")
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1B232A;")
        self.tooltip_widget.layout.addWidget(name_label)

        # Должность
        position_label = QLabel(f"📋 {self.employee_data.get('position', '—')}")
        position_label.setStyleSheet("color: #666; font-size: 12px;")
        self.tooltip_widget.layout.addWidget(position_label)

        # Отдел (если есть)
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
            f"✅ Выполнено: {completed} из {total}",
            f"🎯 В срок: {on_time:.1f}%",
        ]

        # КПД с цветом
        if kpd >= 80:
            kpd_color = "#2ecc71"
        elif kpd >= 60:
            kpd_color = "#f1c40f"
        elif kpd >= 40:
            kpd_color = "#e67e22"
        else:
            kpd_color = "#e74c3c"

        kpd_label = QLabel(f"⚡️ КПД: {kpd:.1f}%")
        kpd_label.setStyleSheet(f"color: #555; font-size: 12px;")
        # Для выделения КПД цветом используем HTML в QLabel
        kpd_label.setText(f'<span style="color: #555;">⚡️ КПД: </span><b style="color: {kpd_color};">{kpd:.1f}%</b>')
        kpd_label.setTextFormat(Qt.TextFormat.RichText)
        self.tooltip_widget.layout.addWidget(kpd_label)

        for stat in stats:
            stat_label = QLabel(stat)
            stat_label.setStyleSheet("color: #555; font-size: 12px;")
            self.tooltip_widget.layout.addWidget(stat_label)

        if weighted > 0:
            w_label = QLabel(f"🎯 Взвешенный: {weighted:.1f}%")
            w_label.setStyleSheet("color: #555; font-size: 12px;")
            self.tooltip_widget.layout.addWidget(w_label)

        if overtime > 0:
            if overtime > 40:
                ot_color = "#e74c3c"
            elif overtime > 20:
                ot_color = "#e67e22"
            else:
                ot_color = "#2ecc71"

            ot_label = QLabel(
                f'<span style="color: #555;">⏱️ Переработки: </span><b style="color: {ot_color};">{overtime:.1f} ч</b>')
            ot_label.setTextFormat(Qt.TextFormat.RichText)
            self.tooltip_widget.layout.addWidget(ot_label)

        self.tooltip_widget.adjustSize()

    def _clear_tooltip(self):
        """Очистка тултипа"""
        if self.tooltip_widget:
            # Удаляем все дочерние виджеты из layout
            while self.tooltip_widget.layout.count():
                item = self.tooltip_widget.layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def _show_tooltip(self):
        """Показать тултип"""
        if not self.tooltip_widget:
            self._create_tooltip()

        # Позиционируем под карточкой
        pos = self.mapToGlobal(QPoint(10, self.height() + 5))
        self.tooltip_widget.move(pos)
        self.tooltip_widget.show()

    def _hide_tooltip(self):
        """Скрыть тултип"""
        if self.tooltip_widget:
            self.tooltip_widget.hide()

    def enterEvent(self, event):
        """Показываем тултип при наведении"""
        self._hide_timer.stop()
        if hasattr(self, '_tooltip_data'):
            self._show_tooltip()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Скрываем тултип с небольшой задержкой"""
        self._hide_timer.start(100)  # 100ms задержка
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Клик по карточке"""
        self._hide_tooltip()
        self.clicked.emit(self.employee_id)
        super().mousePressEvent(event)

    def update_data(self, employee_data, position=0):
        """Обновление данных карточки"""
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        # Сбрасываем тултип, чтобы он пересоздался с новыми данными
        if self.tooltip_widget:
            self.tooltip_widget.hide()
            self.tooltip_widget.deleteLater()
            self.tooltip_widget = None
        self._setup_dynamic_ui()

    def closeEvent(self, event):
        """Очистка при закрытии"""
        if self.tooltip_widget:
            self.tooltip_widget.deleteLater()
            self.tooltip_widget = None
        super().closeEvent(event)