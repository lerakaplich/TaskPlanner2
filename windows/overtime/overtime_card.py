import os
from PyQt6.QtWidgets import QFrame
from PyQt6 import uic


class OvertimeCard(QFrame):
    """UI карточка переработки. Только отображение, без логики"""

    def __init__(self, overtime_data, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "overtime_card.ui"), self)

        self.overtime_data = overtime_data
        self.setObjectName("OvertimeCard")
        self.setup_data()

    def setup_data(self):
        """Заполняем виджеты данными из словаря"""
        data = self.overtime_data

        # Описание (если нет проекта и задачи)
        if data.get('project') and data.get('task'):
            description = f"{data['project']} - {data['task']}"
        else:
            description = data.get('description', 'Без описания')
        self.descriptionLabel.setText(description)

        # Дата
        self.dateLabel.setText(f"📅 {data.get('date', '-')}")
        # Период времени
        self.timeLabel.setText(f"⏰ {data.get('time_period', '-')}")
        # Продолжительность
        self.durationLabel.setText(f"⏱️ {data.get('duration', '-') } ч.")
        # Проект
        self.projectLabel.setText(f"🏢 Проект: {data.get('project', 'Не указан')}")
        # Задача
        self.taskLabel.setText(f"📝 Задача: {data.get('task', 'Не указана')}")
        # Пользователь
        self.userLabel.setText(f"👤 Пользователь: {data.get('user', 'Неизвестный')}")