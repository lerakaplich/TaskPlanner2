
from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi
import os


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

        # Загружаем UI из файла
        self._load_ui()
        # Заполняем данными
        self._setup_dynamic_ui()

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
            color = "#2ecc71"
        elif kpd >= 60:
            color = "#f1c40f"
        elif kpd >= 40:
            color = "#e67e22"
        else:
            color = "#e74c3c"

        self.kpd_label.setText(f"{kpd:.1f}%")
        self.kpd_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")

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

        # Тултип
        self.setToolTip(self._generate_tooltip(kpd, weighted, overtime, total, completed, on_time))

    def _generate_tooltip(self, kpd, weighted, overtime, total, completed, on_time):
        """Генерация всплывающей подсказки"""
        return f"""
        <div style="background-color: white; margin: 0; padding: 8px;">
            <p style="margin: 0 0 8px 0;"><b>👤 {self.employee_data.get('name', '—')}</b></p>
            <p style="margin: 0 0 8px 0;">📋 {self.employee_data.get('position', '—')}</p>
            <p style="margin: 4px 0;">✅ Выполнено: {completed} из {total}</p>
            <p style="margin: 4px 0;">🎯 В срок: {on_time:.1f}%</p>
            <p style="margin: 4px 0;">⚡️ КПД: {kpd:.1f}%</p>
            {f'<p style="margin: 4px 0;">🎯 Взвешенный: {weighted:.1f}%</p>' if weighted > 0 else ''}
            {f'<p style="margin: 4px 0;">⏱️ Переработки: {overtime:.1f} ч</p>' if overtime > 0 else ''}
        </div>
        """


    def mousePressEvent(self, event):
        """Клик по карточке"""
        self.clicked.emit(self.employee_id)
        super().mousePressEvent(event)

    def update_data(self, employee_data, position=0):
        """Обновление данных карточки"""
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        self._setup_dynamic_ui()