from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QDialog
from PyQt6.QtCore import pyqtSignal
import os

# windows/projects/project_card.py

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
        self.projectTitle.setText(project_data.name if project_data.name else '')

        # Прогресс вычисляем из задач
        if project_data.tasks_total > 0:
            progress = int((project_data.tasks_done / project_data.tasks_total) * 100)
        else:
            progress = 0
        self.progressBar.setValue(progress)

        # 👇 ИСПРАВЛЕНО: отображаем владельца
        owner_name = getattr(project_data, 'owner_name', 'Не назначен')
        self.projectInfo.setText(f"👤 Владелец: {owner_name}")

        # 👇 ДОБАВЛЯЕМ дату создания проекта
        created_at = getattr(project_data, 'created_at', None)
        if created_at:
            self.startDate.setText(f"📅 Создан: {created_at}")
        else:
            self.startDate.setText("")

        # Отображаем участников
        member_count = getattr(project_data, 'member_count', 0)
        participants_text = f"👥 Участники: {member_count} чел."
        self.participants.setText(participants_text)

        # Отображаем администраторов
        admin_count = getattr(project_data, 'admin_count', 0)
        admins_text = f"👑 Админы: {admin_count} чел."
        self.admins.setText(admins_text)