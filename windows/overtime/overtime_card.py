import os
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6 import uic
from datetime import datetime, timedelta
import random

from PyQt6.uic import loadUi


class OvertimeCard(QFrame):
    def __init__(self, overtime_data, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "overtime"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "overtime_card.ui"), self)


        self.overtime_data = overtime_data
        self.setObjectName("OvertimeCard")
        self.setup_data()

    def setup_data(self):
        """Заполняем карточку данными"""
        data = self.overtime_data

        # Описание (если нет проекта и задачи)
        if data.get('project') and data.get('task'):
            description = f"{data['project']} - {data['task']}"
        else:
            description = data.get('description', 'Без описания')
        self.descriptionLabel.setText(description)

        # Дата
        self.dateLabel.setText(f"📅 {data['date']}")

        # Период времени
        self.timeLabel.setText(f"⏰ {data['time_period']}")

        # Время переработки
        self.durationLabel.setText(f"⏱️ {data['duration']} ч.")

        # Проект
        project = data.get('project', 'Не указан')
        self.projectLabel.setText(f"🏢 Проект: {project}")

        # Задача
        task = data.get('task', 'Не указана')
        self.taskLabel.setText(f"📝 Задача: {task}")

        # Пользователь
        user = data.get('user', 'Неизвестный')
        self.userLabel.setText(f"👤 Пользователь: {user}")
