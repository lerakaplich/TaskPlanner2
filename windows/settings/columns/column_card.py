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
    done_changed = pyqtSignal(int, bool)

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
            # Скрываем кнопку удаления
            if hasattr(self, 'deleteButton'):
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()

            # Переименовываем кнопку редактирования
            if hasattr(self, 'editButton'):
                self.editButton.setText("Подробнее")

            # Блокируем чекбокс Done
            if hasattr(self, 'doneCheckBox'):
                self.doneCheckBox.setEnabled(False)

            # Отключаем клик по цветному индикатору
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.setCursor(Qt.CursorShape.ArrowCursor)
                self.colorIndicator.setToolTip("Изменение цвета недоступно в режиме просмотра")

    def connect_signals(self):
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.column_id))
        if not self.read_only:
            self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.column_id))
            self.doneCheckBox.stateChanged.connect(self._on_done_changed)
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.installEventFilter(self)

    def _on_done_changed(self, state: int):
        is_done = bool(state)
        self.column_data['is_done_column'] = is_done
        self.done_changed.emit(self.column_id, is_done)

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
                font-size: 15px;
                font-weight: bold;
            """)

    def update_done_status(self, is_done: bool):
        """Обновляет статус Done"""
        self.column_data['is_done_column'] = is_done
        if hasattr(self, 'doneCheckBox'):
            self.doneCheckBox.blockSignals(True)
            self.doneCheckBox.setChecked(is_done)
            self.doneCheckBox.blockSignals(False)

    def fill_data(self):
        """Заполняем данные"""
        # Название
        if hasattr(self, 'nameLabel'):
            name = self.column_data.get('name', 'Колонка')
            self.nameLabel.setText(name)
            color = self.column_data.get('color', '#ccab6e')
            self.nameLabel.setStyleSheet(f"""
                color: {color};
                font-size: 15px;
                font-weight: bold;
            """)

        # Позиция
        if hasattr(self, 'positionLabel'):
            pos = self.column_data.get('position', 0)
            self.positionLabel.setText(f"Позиция: {pos}")

        # Чекбокс «Готово»
        if hasattr(self, 'doneCheckBox'):
            self.doneCheckBox.setChecked(self.column_data.get('is_done_column', False))

        # Цветной кружок
        color = self.column_data.get('color', '#ccab6e')
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {color};
                border: 1px solid #E0E0E0;
            """)