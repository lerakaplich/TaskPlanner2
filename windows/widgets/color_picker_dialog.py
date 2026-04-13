from PyQt6.QtWidgets import QDialog, QColorDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6 import uic
import os


class ColorPickerDialog(QDialog):
    """Диалог выбора цвета для тега"""
    color_selected = pyqtSignal(str)

    def __init__(self, current_color="#ccab6e", parent=None):
        super().__init__(parent)
        self.current_color = current_color
        self.selected_color = current_color
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "widgets", "color_picker_dialog.ui"
        )
        uic.loadUi(ui_path, self)
        # Загружаем интерфейс из .ui файла


        self.setup_connections()
        # Устанавливаем начальный цвет превью
        self.update_preview()

    def setup_connections(self):
        """Подключение всех сигналов"""
        preset_colors = [
            "#ccab6e", "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4",
            "#f9ca24", "#f0932b", "#eb4d4b", "#6ab04c", "#7ed6df",
            "#e056fd", "#686de0", "#30336b", "#95afc0", "#22a6b3",
            "#ff9ff3", "#feca57", "#ff6b6b", "#48dbfb", "#1dd1a1"
        ]

        # Подключаем все кнопки палитры
        for i in range(20):
            btn = getattr(self, f"preset_color_btn_{i}")
            color = preset_colors[i]
            btn.clicked.connect(lambda checked, c=color: self.on_color_preset_clicked(c))

        self.custom_btn.clicked.connect(self.open_color_dialog)
        self.ok_btn.clicked.connect(self.accept)

    def on_color_preset_clicked(self, color):
        """Обработчик выбора предустановленного цвета"""
        self.selected_color = color
        self.update_preview()

    def open_color_dialog(self):
        """Открывает стандартный диалог выбора цвета"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.update_preview()

    def update_preview(self):
        """Обновляет превью цвета"""
        self.preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.selected_color};
                border-radius: 8px;
                border: 2px solid #E0E0E0;
            }}
        """)

    def get_selected_color(self):
        """Возвращает выбранный цвет"""
        return self.selected_color