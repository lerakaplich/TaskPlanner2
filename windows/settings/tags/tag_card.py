# windows/settings/tags/tag_card.py

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
import os


class TagCard(QFrame):
    """Карточка тега с маленьким цветным кружочком"""
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    color_changed = pyqtSignal(int, str)   # id тега, новый цвет

    def __init__(self, tag_data, parent=None, read_only=False):
        super().__init__(parent)
        self.tag_data = tag_data
        self.tag_id = tag_data.get('id', 0)
        self.read_only = read_only

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "tags", "tag_card.ui"
        )
        uic.loadUi(ui_path, self)

        # Фиксируем кружочек цвета
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
            # Скрываем ВСЕ кнопки
            if hasattr(self, 'editButton'):
                self.editButton.setVisible(False)
                self.editButton.hide()

            if hasattr(self, 'deleteButton'):
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()

            # Отключаем клик по цветному индикатору
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.setCursor(Qt.CursorShape.ArrowCursor)
                self.colorIndicator.setToolTip("Изменение цвета недоступно в режиме просмотра")

    def connect_signals(self):
        """Подключение сигналов"""
        if not self.read_only:
            self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.tag_id))
            self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.tag_id))
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Ловим клик по цветному индикатору"""
        if self.read_only:
            return super().eventFilter(obj, event)
        if obj == self.colorIndicator and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.color_changed.emit(self.tag_id, self.tag_data.get('color', '#ccab6e'))
                return True
        return super().eventFilter(obj, event)

    def update_color(self, new_color: str):
        """Меняет цвет на карточке"""
        self.tag_data['color'] = new_color

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
        """Заполняем карточку при создании"""
        name = self.tag_data.get('name', 'тема')
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(f"#{name}")

        color = self.tag_data.get('color', '#ccab6e')
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {color};
                border: 1px solid #E0E0E0;
            """)

        if hasattr(self, 'nameLabel'):
            self.nameLabel.setStyleSheet(f"""
                color: {color};
                font-size: 18px;
                font-weight: bold;
            """)

        usage_count = self.tag_data.get('usage_count', 0)
        if hasattr(self, 'countLabel'):
            self.countLabel.setText(f"использований: {usage_count}")