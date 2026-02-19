from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt


class EmployeeProjectCard(QFrame):
    def __init__(self, employee_data, project_id, parent=None):
        super().__init__(parent)
        self.setObjectName("EmployeeProjectCard")
        self.setStyleSheet("""
            EmployeeProjectCard {
                background-color: white;
                border-radius: 4px;
                border: 1px solid #F0F0F0;
                padding: 4px;
            }
            QLabel {
                font-size: 11px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        name_label = QLabel(employee_data.get("name", ""))
        name_label.setStyleSheet("font-weight: bold;")

        active = employee_data.get("active_tasks", 0)
        completed = employee_data.get("completed_tasks", 0)

        stats_label = QLabel(f"Активных: {active}  Выполнено: {completed}")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(stats_label)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)