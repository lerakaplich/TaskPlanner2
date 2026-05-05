# windows/archive/archived_project_card.py

import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QFrame, QPushButton, QWidget, QApplication


class ArchivedProjectCard(QFrame):
    """Карточка архивированного проекта (только UI)"""

    clicked = pyqtSignal(int)
    restore_requested = pyqtSignal(int)
    delete_permanently_requested = pyqtSignal(int)
    data_updated = pyqtSignal(dict)  # Сигнал для обновления данных

    def __init__(self, project_data: dict, parent=None, service=None):
        super().__init__(parent)
        self.project_id = project_data["id"]
        self.service = service
        self.project_data = project_data

        ui_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "ui", "archive", "archived_project_card.ui"
        )
        uic.loadUi(ui_path, self)

        self._apply_styles()
        self._setup_buttons()
        self._set_data(project_data)

        # Для анимации наведения
        self._original_style = self.styleSheet()

    def _apply_styles(self):
        """Применяет стили к карточке"""
        self.setStyleSheet("""
            ArchivedProjectCard {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            ArchivedProjectCard:hover {
                border: 2px solid #ccab6e;
                background-color: #fafafa;
            }
            QLabel {
                background-color: transparent;
            }
            QWidget {
                background-color: transparent;
            }
        """)

        # Убираем фон у всех QWidget внутри карточки
        for widget in self.findChildren(QWidget):
            widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            widget.setStyleSheet("background-color: transparent;")

        # Стили меток
        self.name_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1B232A;
            background-color: transparent;
        """)

        self.desc_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
            margin-top: 2px;
            background-color: transparent;
        """)

        self.date_label.setStyleSheet("""
            color: #888888;
            font-size: 11px;
            background-color: transparent;
        """)

        self.tasks_label.setStyleSheet("""
            color: #888888;
            font-size: 11px;
            background-color: transparent;
        """)

        # Убираем фон у контейнеров
        if hasattr(self, 'title_row'):
            self.title_row.setStyleSheet("background-color: transparent;")
        if hasattr(self, 'info_row'):
            self.info_row.setStyleSheet("background-color: transparent;")

    def _setup_buttons(self):
        """Настраивает кнопки"""
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
        """)

        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #862633;
            }
            QPushButton:pressed {
                background-color: #6a1e29;
            }
        """)

        self.restore_button.clicked.connect(lambda: self.restore_requested.emit(self.project_id))
        self.delete_button.clicked.connect(lambda: self.delete_permanently_requested.emit(self.project_id))

    def _set_data(self, data: dict):
        """Устанавливает данные в карточку"""
        self.name_label.setText(data.get("name", "Без названия"))

        desc = data.get("description", "")
        if desc:
            self.desc_label.setText(desc)
            self.desc_label.setVisible(True)
        else:
            self.desc_label.setVisible(False)

        self.date_label.setText(f"Архивация: {data.get('archived_at', 'Неизвестно')}")
        self.tasks_label.setText(f"Задач: {data.get('archived_tasks_count', 0)}")

    def update_data(self, new_data: dict):
        """Обновляет данные карточки"""
        self.project_data = new_data
        self._set_data(new_data)
        self.data_updated.emit(new_data)

    def set_loading(self, loading: bool):
        """Устанавливает состояние загрузки"""
        if loading:
            self.restore_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.restore_button.setText("...")
            QApplication.processEvents()
        else:
            self.restore_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.restore_button.setText("Восстановить проект")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.pos())
            if not isinstance(widget, QPushButton):
                self.clicked.emit(self.project_id)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """При наведении курсора"""
        super().enterEvent(event)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def leaveEvent(self, event):
        """При уходе курсора"""
        super().leaveEvent(event)
        self.setCursor(Qt.CursorShape.ArrowCursor)