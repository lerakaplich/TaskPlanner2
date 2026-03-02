import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QPushButton


class ArchivedProjectCard(QFrame):
    """Карточка архивированного проекта"""

    clicked = pyqtSignal(int)  # Сигнал клика по проекту (передает ID проекта)
    restore_requested = pyqtSignal(dict)  # Сигнал восстановления проекта
    delete_permanently_requested = pyqtSignal(dict)  # Сигнал полного удаления

    def __init__(self, project_id, project_data, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_data = project_data

        # Загрузка UI из файла
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )
        uic.loadUi(os.path.join(ui_path, "archived_project_card.ui"), self)

        # Подключение сигналов кнопок
        self.restore_button.clicked.connect(self.on_restore_clicked)
        self.delete_button.clicked.connect(self.on_delete_clicked)

        # Установка данных
        self.update_data(project_data)

    def mousePressEvent(self, event):
        """Обработка клика по карточке"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, не кликнули ли по кнопке
            widget_under_mouse = self.childAt(event.pos())
            if not isinstance(widget_under_mouse, QPushButton):
                self.clicked.emit(self.project_id)
        super().mousePressEvent(event)

    def on_restore_clicked(self):
        """Обработка клика по кнопке восстановления"""
        self.restore_requested.emit(self.project_data)

    def on_delete_clicked(self):
        """Обработка клика по кнопке удаления"""
        self.delete_permanently_requested.emit(self.project_data)

    def update_data(self, new_data):
        """Обновление данных карточки"""
        self.project_data.update(new_data)
        self.name_label.setText(self.project_data.get("name", "Без названия"))

        # Обновление описания
        if hasattr(self, 'desc_label'):
            description = self.project_data.get("description", "")
            self.desc_label.setText(description)
            # Скрываем метку описания, если его нет
            self.desc_label.setVisible(bool(description))

        # Обновление даты архивации
        archived_date = self.project_data.get("archived_at", "Неизвестно")
        if isinstance(archived_date, str) and len(archived_date) > 10:
            archived_date = archived_date[:10]
        self.date_label.setText(f"Архивация: {archived_date}")

        # Обновление количества задач
        tasks_count = self.project_data.get("archived_tasks_count", 0)
        self.tasks_label.setText(f"Задач: {tasks_count}")