import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QPushButton


class ArchivedProjectCard(QFrame):
    """Карточка архивированного проекта (только UI)"""

    clicked = pyqtSignal(int)
    restore_requested = pyqtSignal(int)
    delete_permanently_requested = pyqtSignal(int)

    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)

        self.project_id = project_data["id"]

        # ============================
        # Загрузка UI
        # ============================

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )

        uic.loadUi(
            os.path.join(ui_path, "archived_project_card.ui"),
            self
        )

        # ============================
        # Сигналы
        # ============================

        self.restore_button.clicked.connect(
            lambda: self.restore_requested.emit(self.project_id)
        )

        self.delete_button.clicked.connect(
            lambda: self.delete_permanently_requested.emit(self.project_id)
        )

        # ============================
        # Отображение данных
        # ============================

        self.set_data(project_data)

    # ======================================================
    # UI interaction
    # ======================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:

            widget = self.childAt(event.pos())

            if not isinstance(widget, QPushButton):
                self.clicked.emit(self.project_id)

        super().mousePressEvent(event)

    # ======================================================
    # Отображение данных
    # ======================================================

    def set_data(self, data: dict):

        self.name_label.setText(data["name"])

        if hasattr(self, "desc_label"):

            description = data["description"]

            self.desc_label.setText(description)
            self.desc_label.setVisible(bool(description))

        self.date_label.setText(f"Архивация: {data['archived_at']}")

        self.tasks_label.setText(
            f"Задач: {data['archived_tasks_count']}"
        )