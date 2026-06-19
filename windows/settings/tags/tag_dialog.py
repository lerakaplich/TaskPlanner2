# windows/settings/tags/tag_dialog.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent

from windows.widgets.color_picker_dialog import ColorPickerDialog


class TagDialog(QDialog):
    """Диалог добавления/редактирования хэштега"""
    tag_saved = pyqtSignal(dict)

    def __init__(self, tag_data=None, parent=None, read_only=False):
        super().__init__(parent)

        self.tag_data = tag_data or {}
        self.is_edit_mode = bool(tag_data and tag_data.get('id'))
        self.read_only = read_only
        self.current_color = self.tag_data.get('color', '#ccab6e')
        self.fields = []

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "tags", "tag_dialog.ui"
        )

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"Не найден UI файл:\n{ui_path}")

        uic.loadUi(ui_path, self)

        self.setup_ui()
        self.connect_signals()
        self.fill_data()
        self.setup_keyboard_navigation()
        self._apply_read_only_state()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра к диалогу"""
        if self.read_only:
            # Скрываем кнопку сохранения
            if hasattr(self, 'btnSave'):
                self.btnSave.setVisible(False)
                self.btnSave.hide()

            # Блокируем поле ввода
            if hasattr(self, 'lineEditName'):
                self.lineEditName.setReadOnly(True)

            # Скрываем кнопку выбора цвета
            if hasattr(self, 'btnCustomColor'):
                self.btnCustomColor.setVisible(False)

            # Блокируем комбобокс цвета
            if hasattr(self, 'comboBoxColor'):
                self.comboBoxColor.setEnabled(False)

            # Отключаем клик по цветному индикатору
            if hasattr(self, 'colorIndicator'):
                self.colorIndicator.setCursor(Qt.CursorShape.ArrowCursor)
                self.colorIndicator.setToolTip("Изменение цвета недоступно в режиме просмотра")

    def setup_ui(self):
        """Настройка UI элементов"""
        if self.read_only:
            self.setWindowTitle("Просмотр темы")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Просмотр темы")
        elif self.is_edit_mode:
            self.setWindowTitle("Редактирование темы")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование темы")
        else:
            self.setWindowTitle("Добавление темы")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление новой темы")

        if hasattr(self, 'lineEditName'):
            self.lineEditName.setMaxLength(50)

        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setFixedSize(32, 32)
            self.colorIndicator.setMinimumSize(32, 32)
            self.colorIndicator.setMaximumSize(32, 32)
            self.colorIndicator.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed
            )
            self.colorIndicator.setCursor(Qt.CursorShape.PointingHandCursor)
            self.colorIndicator.setToolTip("Нажмите для изменения цвета")
            self.colorIndicator.installEventFilter(self)

    def connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'btnSave'):
            self.btnSave.clicked.connect(self.on_save_clicked)

        if hasattr(self, 'btnCancel'):
            self.btnCancel.clicked.connect(self.reject)

        if hasattr(self, 'btnCustomColor'):
            self.btnCustomColor.clicked.connect(self.on_custom_color_clicked)

        if hasattr(self, 'comboBoxColor'):
            self.comboBoxColor.currentTextChanged.connect(self.on_color_changed)

        if hasattr(self, 'lineEditName'):
            self.lineEditName.textChanged.connect(self.update_preview)

    def fill_data(self):
        """Заполнение полей данными при редактировании"""
        if hasattr(self, 'lineEditName'):
            name = self.tag_data.get('name', '')
            self.lineEditName.setText(name)

        if hasattr(self, 'comboBoxColor'):
            color_index = -1
            for i in range(self.comboBoxColor.count()):
                item_text = self.comboBoxColor.itemText(i)
                if self.current_color.lower() in item_text.lower():
                    color_index = i
                    break

            if color_index >= 0:
                self.comboBoxColor.setCurrentIndex(color_index)
            else:
                color_name = self.get_color_name(self.current_color)
                self.comboBoxColor.addItem(f"{color_name} ({self.current_color})")
                self.comboBoxColor.setCurrentIndex(self.comboBoxColor.count() - 1)

        self.update_preview()
        self.update_color_indicator(self.current_color)

    def on_save_clicked(self):
        """Обработка сохранения тега"""
        if self.read_only:
            QMessageBox.information(self, "Информация", "В режиме просмотра редактирование недоступно")
            return

        if not hasattr(self, 'lineEditName'):
            return

        name = self.lineEditName.text().strip()
        if name.startswith('#'):
            name = name[1:]

        if not name:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите название темы.")
            return

        tag_data = {
            'id': self.tag_data.get('id', None),
            'name': name,
            'color': self.current_color,
            'count': self.tag_data.get('count', 0)
        }

        self.tag_saved.emit(tag_data)
        self.accept()

    def on_color_indicator_clicked(self):
        """Открываем диалог выбора цвета по клику на кружочек"""
        if self.read_only:
            return
        dialog = ColorPickerDialog(self.current_color, self)

        if dialog.exec():
            new_color = dialog.get_selected_color()
            if new_color and new_color != self.current_color:
                self.update_color(new_color)

    def on_color_changed(self, color_text):
        """Обработка изменения цвета из комбобокса"""
        import re
        match = re.search(r'\(#([A-Fa-f0-9]{6})\)', color_text)
        if match:
            color_code = f"#{match.group(1)}"
            self.update_color(color_code)

    def on_custom_color_clicked(self):
        """Открытие диалога выбора пользовательского цвета"""
        if self.read_only:
            return
        dialog = ColorPickerDialog(self.current_color, self)

        if dialog.exec():
            new_color = dialog.get_selected_color()
            if new_color and new_color != self.current_color:
                self.update_color(new_color)

                if hasattr(self, 'comboBoxColor'):
                    color_exists = False
                    for i in range(self.comboBoxColor.count()):
                        if new_color in self.comboBoxColor.itemText(i):
                            color_exists = True
                            self.comboBoxColor.setCurrentIndex(i)
                            break

                    if not color_exists:
                        color_name = self.get_color_name(new_color)
                        self.comboBoxColor.addItem(f"{color_name} ({new_color})")
                        self.comboBoxColor.setCurrentIndex(self.comboBoxColor.count() - 1)

    def update_color(self, new_color: str):
        """Обновление цвета во всех элементах"""
        self.current_color = new_color
        self.update_color_indicator(new_color)
        self.update_preview()

    def get_color_name(self, color_code):
        """Получение названия цвета по его коду"""
        color_names = {
            '#D22730': 'Красный',
            '#ccab6e': 'Золотой',
            '#3498db': 'Синий',
            '#2ecc71': 'Зеленый',
            '#9b59b6': 'Фиолетовый',
            '#e67e22': 'Оранжевый'
        }
        return color_names.get(color_code.lower(), 'Пользовательский')

    def update_color_indicator(self, color_code):
        """Обновление цветного кружочка"""
        if hasattr(self, 'colorIndicator'):
            self.colorIndicator.setStyleSheet(f"""
                border-radius: 16px;
                background-color: {color_code};
                border: 2px solid #E0E0E0;
            """)

    def update_preview(self):
        """Обновление текстового предпросмотра"""
        if hasattr(self, 'previewLabel') and hasattr(self, 'lineEditName'):
            name = self.lineEditName.text().strip()
            if not name:
                name = "название_темы"
            else:
                name = name.replace(' ', '_')

            self.previewLabel.setText(f"#{name}")
            self.previewLabel.setStyleSheet(f"""
                font-size: 18px;
                font-weight: bold;
                color: {self.current_color};
                background-color: transparent;
            """)

    def get_tag_data(self):
        """Получение данных тега"""
        if not hasattr(self, 'lineEditName'):
            return {}

        name = self.lineEditName.text().strip()
        if name.startswith('#'):
            name = name[1:]

        return {
            'id': self.tag_data.get('id', None),
            'name': name,
            'color': self.current_color,
            'count': self.tag_data.get('count', 0)
        }

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями по стрелкам"""
        self.fields = []
        if hasattr(self, 'lineEditName'):
            self.fields.append(self.lineEditName)
        if hasattr(self, 'comboBoxColor'):
            self.fields.append(self.comboBoxColor)

        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Обработка стрелок ↑ ↓ + клик по цветному индикатору"""
        if hasattr(self, 'colorIndicator') and obj == self.colorIndicator:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.on_color_indicator_clicked()
                    return True

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()

            try:
                current_index = self.fields.index(obj)
            except (ValueError, AttributeError):
                return super().eventFilter(obj, event)

            if key == Qt.Key.Key_Down:
                next_index = (current_index + 1) % len(self.fields)
                if self.fields[next_index]:
                    self.fields[next_index].setFocus()
                return True

            elif key == Qt.Key.Key_Up:
                prev_index = (current_index - 1) % len(self.fields)
                if self.fields[prev_index]:
                    self.fields[prev_index].setFocus()
                return True

        return super().eventFilter(obj, event)