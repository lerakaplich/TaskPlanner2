from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class OvertimeCard(QFrame):
    """Карточка переработки в списке"""

    overtime_deleted = pyqtSignal(int)

    def __init__(self, overtime_data, parent=None):
        super().__init__(parent)
        self.overtime_data = overtime_data
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса карточки"""
        self.setObjectName("overtimeCard")
        self.setStyleSheet("""
            #overtimeCard {
                background-color: white;
                border-radius: 12px;
                padding: 20px;
                border-left: 5px solid #D22730;
            }
            #overtimeCard:hover {
                background-color: #F8F9FA;
            }
        """)

        layout = QHBoxLayout(self)

        # Основная информация
        info_layout = QVBoxLayout()

        # Проект и задача
        project_label = QLabel(f"<b>{self.overtime_data['project']}</b>")
        project_label.setStyleSheet("font-size: 16px; color: #1B232A;")

        task_label = QLabel(f"Задача: {self.overtime_data['task']}")
        task_label.setStyleSheet("font-size: 14px; color: #666; margin-top: 5px;")

        # Дата и время
        datetime_label = QLabel(
            f"📅 {self.overtime_data['date']} | "
            f"🕐 {self.overtime_data['start']} - {self.overtime_data['end']} "
            f"(<b>{self.overtime_data['duration']} ч</b>)"
        )
        datetime_label.setStyleSheet("font-size: 14px; color: #1B232A; margin-top: 8px;")

        # Примечание
        if self.overtime_data.get('note'):
            note_label = QLabel(f"📝 {self.overtime_data['note']}")
            note_label.setStyleSheet("""
                font-size: 13px;
                color: #666;
                margin-top: 8px;
                padding: 8px;
                background-color: #F0F0F0;
                border-radius: 6px;
            """)
            note_label.setWordWrap(True)
            info_layout.addWidget(note_label)

        info_layout.addWidget(project_label)
        info_layout.addWidget(task_label)
        info_layout.addWidget(datetime_label)

        # Добавляем растягивающийся спейсер
        info_layout.addStretch()

        layout.addLayout(info_layout)
        layout.addStretch()

        # Кнопка удаления
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Удалить переработку")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #D22730;
                font-size: 18px;
                border: none;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FFEEEE;
            }
        """)
        delete_btn.clicked.connect(self.delete_overtime)

        layout.addWidget(delete_btn)

    def delete_overtime(self):
        """Удаление переработки"""
        from delete_overtime_dialog import DeleteOvertimeDialog
        dialog = DeleteOvertimeDialog(self.overtime_data, self)
        if dialog.exec():
            self.overtime_deleted.emit(self.overtime_data['id'])