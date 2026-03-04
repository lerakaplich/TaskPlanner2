import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QPushButton


class ArchivedProjectCard(QFrame):
    """Карточка архивированного проекта (чистый UI)"""

    clicked = pyqtSignal(int)
    restore_requested = pyqtSignal(int)
    delete_permanently_requested = pyqtSignal(int)

    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)

        self.project_id = project_data["id"]

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )
        uic.loadUi(os.path.join(ui_path, "archived_project_card.ui"), self)

        # Сигналы кнопок
        self.restore_button.clicked.connect(self.on_restore_clicked)
        self.delete_button.clicked.connect(self.on_delete_clicked)

        # Установка данных
        self.set_data(project_data)

    # ======================================================
    # UI logic only
    # ======================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.pos())
            if not isinstance(widget, QPushButton):
                self.clicked.emit(self.project_id)
        super().mousePressEvent(event)

    def on_restore_clicked(self):
        self.restore_requested.emit(self.project_id)

    def on_delete_clicked(self):
        self.delete_permanently_requested.emit(self.project_id)

    # ======================================================
    # Только отображение
    # ======================================================

    def set_data(self, data: dict):
        self.name_label.setText(data.get("name", "Без названия"))

        description = data.get("description", "")
        if hasattr(self, "desc_label"):
            self.desc_label.setText(description)
            self.desc_label.setVisible(bool(description))

        archived_date = data.get("archived_at", "Неизвестно")
        if isinstance(archived_date, str) and len(archived_date) > 10:
            archived_date = archived_date[:10]

        self.date_label.setText(f"Архивация: {archived_date}")

        tasks_count = data.get("archived_tasks_count", 0)
        self.tasks_label.setText(f"Задач: {tasks_count}")