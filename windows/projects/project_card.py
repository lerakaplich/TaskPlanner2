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
        # 👈 ИСПРАВЛЕНО: используем прямой доступ к атрибутам вместо .get()
        self.projectTitle.setText(project_data.name if project_data.name else '')

        # Прогресс вычисляем из задач
        if project_data.tasks_total > 0:
            progress = int((project_data.tasks_done / project_data.tasks_total) * 100)
        else:
            progress = 0
        self.progressBar.setValue(progress)

        # Владелец - пока нет в DTO, можно добавить позже или показывать заглушку
        owner = getattr(project_data, 'owner', 'Не назначен')
        self.projectInfo.setText(f"Владелец: {owner}")

        # Дата старта - пока нет в DTO
        start_date = getattr(project_data, 'start_date', '')
        if start_date:
            self.startDate.setText(f"Старт: {start_date}")
        else:
            self.startDate.setText("")

        # Отображение участников - пока нет в DTO
        participants_text = "👥 Участники: 0 чел."
        self.participants.setText(participants_text)

        # Отображение администраторов
        admins_text = "👑 Админы: 0 чел."
        self.admins.setText(admins_text)

        # Дедлайн
        deadline = project_data.deadline
        if deadline:
            # Форматируем time объект в строку
            deadline_str = deadline.strftime("%H:%M") if hasattr(deadline, 'strftime') else str(deadline)
            self.deadline.setText(f"До {deadline_str}")

            # Подсветка критических дедлайнов
            is_critical = getattr(project_data, 'is_critical', False)
            if is_critical:
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
        else:
            self.deadline.setText("")