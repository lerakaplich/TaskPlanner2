# windows/settings/columns/column_card.py

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
import os


class ColumnCard(QFrame):
    """Карточка колонки доски (board_columns) — цвет как в тегах"""

    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    color_changed = pyqtSignal(int, str)

    # ===== СТАТИЧЕСКИЕ ДАННЫЕ ДЛЯ НАЗНАЧЕНИЙ =====
    ASSIGNMENT_DATA = {
        'execution': {
            'label': 'Выполнение',
            'color': '#1565C0',
            'bg_color': '#E3F2FD'
        },
        'review': {
            'label': 'Проверка',
            'color': '#E65100',
            'bg_color': '#FFF3E0'
        },
        'completion': {
            'label': 'Готово',
            'color': '#2E7D32',
            'bg_color': '#E8F5E9'
        }
    }

    def __init__(self, column_data: dict, parent=None, read_only=False):
        super().__init__(parent)
        self.column_data = column_data
        self.column_id = column_data.get('id', 0)
        self.read_only = read_only

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "columns", "column_card.ui"
        )
        uic.loadUi(ui_path, self)

        # Делаем цветной индикатор
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setFixedSize(20, 20)
            self.colorIndicator.setMinimumSize(20, 20)
            self.colorIndicator.setMaximumSize(20, 20)
            self.colorIndicator.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed
            )
            self.colorIndicator.setCursor(Qt.CursorShape.PointingHandCursor)
            self.colorIndicator.setToolTip("Нажмите для изменения цвета")

        self.fill_data()
        self.connect_signals()
        self._apply_read_only_state()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра"""
        if self.read_only:
            if hasattr(self, 'editButton'):
                self.editButton.setVisible(False)
                self.editButton.hide()

            if hasattr(self, 'deleteButton'):
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()

            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.setCursor(Qt.CursorShape.ArrowCursor)
                self.colorIndicator.setToolTip("Изменение цвета недоступно в режиме просмотра")

    def connect_signals(self):
        """Подключение сигналов"""
        if not self.read_only:
            self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.column_id))
            self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.column_id))
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        if self.read_only:
            return super().eventFilter(obj, event)
        if obj == self.colorIndicator and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.color_changed.emit(self.column_id, self.column_data.get('color', '#ccab6e'))
                return True
        return super().eventFilter(obj, event)

    def update_color(self, new_color: str):
        """Обновляем цвет + красим название колонки"""
        self.column_data['color'] = new_color

        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {new_color};
                border: 1px solid #E0E0E0;
            """)

        if hasattr(self, 'nameLabel'):
            self.nameLabel.setStyleSheet(f"""
                color: {new_color};
                font-size: 18px;
                font-weight: bold;
            """)

    def fill_data(self):
        """Заполняем данные"""
        # Название
        if hasattr(self, 'nameLabel'):
            name = self.column_data.get('name', 'Колонка')
            self.nameLabel.setText(name)
            color = self.column_data.get('color', '#ccab6e')
            self.nameLabel.setStyleSheet(f"""
                color: {color};
                font-size: 18px;
                font-weight: bold;
            """)

        # Позиция
        if hasattr(self, 'positionLabel'):
            pos = self.column_data.get('position', 0)
            self.positionLabel.setText(f"Позиция: {pos}")

        # ===== НАЗНАЧЕНИЕ КОЛОНКИ =====
        if hasattr(self, 'assignmentLabel'):
            stage = self.column_data.get('stage', 'execution')
            self._update_assignment_label(stage)

        # Цветной кружок
        color = self.column_data.get('color', '#ccab6e')
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {color};
                border: 1px solid #E0E0E0;
            """)

    def _update_assignment_label(self, stage: str):
        """Обновляет метку назначения колонки"""
        if not hasattr(self, 'assignmentLabel'):
            return

        assignment = self.ASSIGNMENT_DATA.get(stage, self.ASSIGNMENT_DATA['execution'])
        display_text = f"{assignment['label']}"

        self.assignmentLabel.setText(display_text)
        self.assignmentLabel.setStyleSheet(f"""
            QLabel#assignmentLabel {{
                font-size: 13px;
                font-weight: 500;
                padding: 4px 12px;
                border-radius: 12px;
                background-color: {assignment['bg_color']};
                color: {assignment['color']};
            }}
        """)

    def update_assignment(self, stage: str):
        """Обновляет назначение колонки (вызывается извне)"""
        self.column_data['stage'] = stage
        self._update_assignment_label(stage)