from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QDialog
from PyQt6.QtCore import pyqtSignal
import os


class ProjectCard(QFrame):
    """Карточка проекта с кнопкой редактирования и отображением участников"""

    edit_clicked = pyqtSignal(int)  # Сигнал для редактирования
    open_clicked = pyqtSignal(int)  # Сигнал для открытия

    def __init__(self, project_id, project_data, parent=None):
        super().__init__(parent)

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_card.ui"), self)

        self.project_id = project_id
        self.project_data = project_data

        # Заполняем данными
        self.update_data(project_data)

        # Подключаем сигналы
        self.btnOpen.clicked.connect(lambda: self.open_clicked.emit(self.project_id))
        self.btnEdit.clicked.connect(lambda: self.edit_clicked.emit(self.project_id))

        # Настройка размеров
        self.setSizePolicy(self.sizePolicy().Policy.Expanding,
                           self.sizePolicy().Policy.Fixed)

    def update_data(self, project_data):
        """Обновление данных карточки"""
        self.projectTitle.setText(project_data.get('name', ''))
        self.progressBar.setValue(project_data.get('progress', 0))

        owner = project_data.get('owner', 'Не назначен')
        self.projectInfo.setText(f"Владелец: {owner}")

        start_date = project_data.get('start_date', '')
        if start_date:
            self.startDate.setText(f"Старт: {start_date}")

        # Отображение участников
        participants = project_data.get('participants', [])
        if participants:
            if isinstance(participants, list):
                participants_text = f"👥 Участники: {len(participants)} чел."
            else:
                participants_text = f"👥 Участники: {participants}"
        else:
            participants_text = "👥 Участники: 0 чел."
        self.participants.setText(participants_text)

        # Отображение администраторов
        admins = project_data.get('admins', [])
        if admins:
            if isinstance(admins, list):
                admins_text = f"👑 Админы: {len(admins)} чел."
            else:
                admins_text = f"👑 Админы: {admins}"
        else:
            admins_text = "👑 Админы: 0 чел."
        self.admins.setText(admins_text)

        # Дедлайн
        deadline = project_data.get('deadline', '')
        if deadline:
            self.deadline.setText(f"До {deadline}")

            # Подсветка критических дедлайнов
            if project_data.get('is_critical', False):
                self.deadline.setStyleSheet(
                    "font-size: 11px; color: #D22730; "
                    "padding: 4px 8px; background-color: #FFEEEE; "
                    "border-radius: 4px;"
                )
            else:
                self.deadline.setStyleSheet(
                    "font-size: 11px; color: #666; "
                    "padding: 4px 8px; background-color: #F0F0F0; "
                    "border-radius: 4px;"
                )