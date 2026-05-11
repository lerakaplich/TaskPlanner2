# windows/analytics/rating/rating_employee_card.py

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal


class RatingEmployeeCard(QFrame):
    """Карточка сотрудника для рейтинга с КПД"""

    clicked = pyqtSignal(int)

    def __init__(self, employee_data, position=0, parent=None):
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        self._init_ui()

    def _init_ui(self):
        # Стили
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                margin: 4px 0;
            }
            QFrame:hover {
                background-color: #FAFAFA;
                border-color: #ccab6e;
            }
        """)

        # Убираем фиксированную высоту, делаем自适应
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(70)  # Минимальная высота, но не фиксированная
        # self.setFixedHeight(80)  # Удаляем эту строку

        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)

        # Позиция (место)
        position_colors = {
            1: "#FFD700",  # Золото
            2: "#C0C0C0",  # Серебро
            3: "#CD7F32"  # Бронза
        }
        color = position_colors.get(self.position + 1, "#E0E0E0")
        font_size = "24px" if self.position < 3 else "18px"

        position_label = QLabel(f"{self.position + 1}")
        position_label.setFixedSize(50, 50)
        position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        position_label.setStyleSheet(f"""
            background-color: {color};
            border-radius: 25px;
            font-size: {font_size};
            font-weight: bold;
            color: {'#333' if self.position < 3 else '#666'};
        """)
        main_layout.addWidget(position_label)

        # Информация о сотруднике
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # Имя
        name_label = QLabel(self.employee_data.get('name', 'Без имени'))
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        # Должность и отдел
        position_text = self.employee_data.get('position', '—')
        department = self.employee_data.get('department', '')
        if department and department != '—':
            position_text += f" · {department}"
        subdivision = self.employee_data.get('subdivision', '')
        if subdivision and subdivision != '—':
            position_text += f" · {subdivision}"

        dept_label = QLabel(position_text)
        dept_label.setStyleSheet("color: #666; font-size: 11px;")
        dept_label.setWordWrap(True)
        info_layout.addWidget(dept_label)

        # Статистика (выполнено/всего задач)
        completed_tasks = self.employee_data.get('completed_tasks', 0)
        total_tasks = self.employee_data.get('total_tasks', 0)
        stats_label = QLabel(f"📊 Выполнено задач: {completed_tasks} из {total_tasks}")
        stats_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(stats_label)

        main_layout.addLayout(info_layout, stretch=1)

        # КПД с процентами
        kpd_layout = QVBoxLayout()
        kpd_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # КПД процент
        total_tasks = self.employee_data.get('total_tasks', 0)
        completed_tasks = self.employee_data.get('completed_tasks', 0)
        kpd_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        kpd_label = QLabel(f"{kpd_percent:.1f}%")
        kpd_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        kpd_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2ecc71;")
        kpd_layout.addWidget(kpd_label)

        # Прогресс-бар
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(kpd_percent))
        progress_bar.setFixedWidth(120)
        progress_bar.setFixedHeight(8)
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2ecc71, stop:1 #27ae60);
                border-radius: 4px;
            }
        """)
        kpd_layout.addWidget(progress_bar)

        # Количество часов переработок (если есть)
        overtime_hours = self.employee_data.get('overtime_hours', 0)
        if overtime_hours > 0:
            overtime_label = QLabel(f"⏱️ +{overtime_hours:.1f} ч")
            overtime_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            overtime_label.setStyleSheet("color: #e67e22; font-size: 11px;")
            kpd_layout.addWidget(overtime_label)

        main_layout.addLayout(kpd_layout)

        # Сделать карточку кликабельной
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit(self.employee_id)
        super().mousePressEvent(event)