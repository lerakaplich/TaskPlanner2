# windows/archive/archived_task_card.py

import os
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtWidgets import QMenu, QLabel

from windows.my_tasks.task_card import TaskCard


class ArchivedTaskCard(TaskCard):
    """Карточка архивированной задачи - только UI"""

    restore_requested = pyqtSignal(int)
    delete_permanently_requested = pyqtSignal(int)

    def __init__(self, task_data: dict, parent=None):
        super().__init__(task_data, parent)
        self.task_id = task_data["id"]
        self._apply_archive_styles()
        self._override_context_menu()

    def _apply_archive_styles(self):
        self.setProperty("archived", True)
        if not hasattr(self, "archive_badge"):
            self.archive_badge = QLabel("📦 В архиве", self)
            self.archive_badge.setStyleSheet("""
                QLabel { color: #888888; font-size: 10px; font-style: italic;
                padding: 2px 6px; background-color: #f0f0f0; border-radius: 4px; }
            """)
            if hasattr(self, "footer_layout"):
                self.footer_layout.insertWidget(0, self.archive_badge)

    def _override_context_menu(self):
        try:
            self.menuButton.clicked.disconnect()
        except TypeError:
            pass
        self.menuButton.clicked.connect(self._show_archive_menu)

    def _show_archive_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #ffffff; border: 1px solid #e0e0e0;
            border-radius: 10px; padding: 6px 0; font-size: 14px; }
            QMenu::item { padding: 10px 30px 10px 15px; color: #1B232A; }
            QMenu::item:selected { background-color: #ccab6e; color: white;
            border-radius: 6px; margin: 2px 6px; }
        """)
        restore_action = menu.addAction("Восстановить")
        restore_action.triggered.connect(lambda: self.restore_requested.emit(self.task_id))
        delete_action = menu.addAction("Удалить навсегда")
        delete_action.triggered.connect(lambda: self.delete_permanently_requested.emit(self.task_id))
        menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

    def update_data(self, task_data: dict):
        super().update_data(task_data)
        self.task_id = task_data["id"]