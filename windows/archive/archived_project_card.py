import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QLabel, QWidget


class ArchivedProjectCard(QFrame):
    """Карточка архивированного проекта"""

    clicked = pyqtSignal(int)  # Сигнал клика по проекту (передает ID проекта)
    restore_requested = pyqtSignal(dict)  # Сигнал восстановления проекта
    delete_permanently_requested = pyqtSignal(dict)  # Сигнал полного удаления

    def __init__(self, project_id, project_data, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_data = project_data

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        """Настройка интерфейса карточки проекта"""
        # Основной вертикальный layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Верхняя строка с иконкой, названием и кнопками
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)

        # Первая строка: название и кнопки
        title_row = QWidget()
        title_layout = QVBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        # Название проекта
        self.name_label = QLabel(self.project_data.get("name", "Без названия"))
        self.name_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1B232A;
        """)
        title_layout.addWidget(self.name_label)

        # Описание проекта (если есть)
        if self.project_data.get("description"):
            self.desc_label = QLabel(self.project_data["description"])
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet("""
                color: #666666;
                font-size: 13px;
                margin-top: 2px;
            """)
            title_layout.addWidget(self.desc_label)

        header_layout.addWidget(title_row)

        # Вторая строка: метка "В архиве" и кнопки
        info_row = QWidget()
        info_layout = QVBoxLayout(info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        # Информация о дате архивации
        archived_date = self.project_data.get("archived_at", "Неизвестно")
        if isinstance(archived_date, str) and len(archived_date) > 10:
            archived_date = archived_date[:10]

        self.date_label = QLabel(f"Архивация: {archived_date}")
        self.date_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(self.date_label)

        # Количество задач
        tasks_count = self.project_data.get("archived_tasks_count", 0)
        self.tasks_label = QLabel(f"Задач: {tasks_count}")
        self.tasks_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(self.tasks_label)

        header_layout.addWidget(info_row)

        self.main_layout.addLayout(header_layout)

        # Кнопки действий
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)

        # Кнопка восстановления
        self.restore_button = QPushButton("Восстановить проект")
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
        self.restore_button.clicked.connect(self.on_restore_clicked)
        buttons_layout.addWidget(self.restore_button)

        # Кнопка удаления
        self.delete_button = QPushButton("Удалить навсегда")
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
        self.delete_button.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(self.delete_button)

        self.main_layout.addLayout(buttons_layout)

        # Устанавливаем курсор
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def apply_styles(self):
        """Применение стилей к карточке"""
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
        """)

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
        if hasattr(self, 'desc_label'):
            self.desc_label.setText(self.project_data.get("description", ""))