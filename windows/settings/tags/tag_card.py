from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
import os


class TagCard(QFrame):
    """Карточка тега на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id тега
    delete_clicked = pyqtSignal(int)  # id тега

    def __init__(self, tag_data, parent=None):
        super().__init__(parent)
        self.tag_data = tag_data
        self.tag_id = tag_data.get('id', 0)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "tags", "tag_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.fill_data()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.tag_id))
        self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.tag_id))

    def fill_data(self):
        """Заполнение данными"""
        # Название тега
        name = self.tag_data.get('name', 'тег')
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(f"#{name}")

        # Цвет тега
        color = self.tag_data.get('color', '#ccab6e')
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {color};
                border: 1px solid #E0E0E0;
            """)

        if hasattr(self, 'nameLabel'):
            self.nameLabel.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Количество использований
        count = self.tag_data.get('count', 0)
        if hasattr(self, 'countLabel'):
            self.countLabel.setText(f"использований: {count}")