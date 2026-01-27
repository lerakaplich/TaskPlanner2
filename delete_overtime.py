from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi


class DeleteOvertimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("delete_overtime.ui", self)

        # Устанавливаем флаг для сохранения геометрии
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Настраиваем кнопки
        self.setup_buttons()

    def setup_buttons(self):
        """Настройка кнопок"""
        # Кнопка OK (Удалить) - красная
        ok_button = self.buttonBox.button(self.buttonBox.StandardButton.Ok)
        ok_button.setText("Удалить")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #862633;
            }
            QPushButton:pressed {
                background-color: #6a1e29;
            }
        """)

        # Кнопка Cancel - серая
        cancel_button = self.buttonBox.button(self.buttonBox.StandardButton.Cancel)
        cancel_button.setText("Отмена")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
            QPushButton:pressed {
                background-color: #B8B8B5;
            }
        """)