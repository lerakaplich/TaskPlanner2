# windows/analytics/projects/employee_project_card.py

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from PyQt6.QtCore import Qt


class EmployeeProjectCard(QFrame):
    """Карточка сотрудника в проекте - только отображение данных"""

    def __init__(self, employee_data, project_id, parent=None):
        super().__init__(parent)
        self.setObjectName("EmployeeProjectCard")
        self.setStyleSheet("""
            EmployeeProjectCard {
                background-color: white;
                border-radius: 4px;
                border: 1px solid #F0F0F0;
                padding: 8px;
                margin: 2px;
            }
            QLabel {
                font-size: 11px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Информация о сотруднике
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Получаем данные (уже подготовлены сервисом)
        name = employee_data.get("name", employee_data.get("employee_name", "Неизвестен"))
        position = employee_data.get("position", "")

        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        info_layout.addWidget(name_label)

        if position:
            position_label = QLabel(position)
            position_label.setStyleSheet("color: #666; font-size: 10px;")
            info_layout.addWidget(position_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Статистика задач
        active = employee_data.get("active_tasks", employee_data.get("active", 0))
        completed = employee_data.get("completed_tasks", employee_data.get("completed", 0))

        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(2)
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        active_label = QLabel(f"📋 Активных: {active}")
        active_label.setStyleSheet("color: #555; font-size: 10px;")
        completed_label = QLabel(f"✅ Выполнено: {completed}")
        completed_label.setStyleSheet("color: #555; font-size: 10px;")

        stats_layout.addWidget(active_label)
        stats_layout.addWidget(completed_label)

        layout.addLayout(stats_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(60)