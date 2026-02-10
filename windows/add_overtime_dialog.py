import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QPushButton, QHBoxLayout
)
from PyQt6 import uic
from PyQt6.uic import loadUi


class AddOvertimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)


        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "add_overtime_dialog.ui"), self)


        # Подключаем сигналы
        self.btnSave.clicked.connect(self.accept)  # Сохранить → закрыть с QDialog.Accepted

        # Создаём горизонтальный layout для двух кнопок внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()  # отодвигает кнопки вправо
        buttons_layout.addWidget(self.btnSave)

        # Находим основной вертикальный layout и добавляем в него кнопки
        main_layout = self.layout()  # это QVBoxLayout из UI
        main_layout.addLayout(buttons_layout)


# Для тестирования диалога отдельно
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AddOvertimeDialog()
    dialog.exec()