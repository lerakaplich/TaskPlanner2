# windows/settings/columns/column_dialog.py

import os
import re

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent

from windows.widgets.color_picker_dialog import ColorPickerDialog


class ColumnDialog(QDialog):
    """Диалог добавления/редактирования колонки доски задач"""
    column_saved = pyqtSignal(dict)

    def __init__(self, column_data=None, is_template_mode=True, parent=None, read_only=False):
        super().__init__(parent)
        self.column_data = column_data or {}
        self.is_template_mode = is_template_mode
        self.is_edit_mode = bool(column_data and column_data.get('id'))
        self.read_only = read_only
        self.current_color = self.column_data.get('color', '#ccab6e')
        self.is_done_column = self.column_data.get('is_done_column', False)
        self.fields = []

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "columns", "column_dialog.ui"
        )
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

            # Блокируем все поля ввода
            self._set_all_fields_read_only()

            # Скрываем кнопку выбора цвета (если есть)
            if hasattr(self, 'btnCustomColor'):
                self.btnCustomColor.setVisible(False)

            # Блокируем комбобокс цвета
            if hasattr(self, 'comboBoxColor'):
                self.comboBoxColor.setEnabled(False)

            # Блокируем комбобокс назначения (если есть)
            if hasattr(self, 'comboBoxAssigment'):
                self.comboBoxAssigment.setEnabled(False)

    def _set_all_fields_read_only(self):
        """Блокирует все поля ввода"""
        if hasattr(self, 'lineEditName'):
            self.lineEditName.setReadOnly(True)
        if hasattr(self, 'comboBoxColor'):
            self.comboBoxColor.setEnabled(False)
        if hasattr(self, 'comboBoxAssigment'):
            self.comboBoxAssigment.setEnabled(False)

    def setup_ui(self):
        """Настройка UI элементов"""
        if self.read_only:
            if self.is_template_mode:
                self.setWindowTitle("Просмотр шаблона колонки")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Просмотр шаблона колонки")
            else:
                self.setWindowTitle("Просмотр колонки проекта")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Просмотр колонки проекта")
        elif self.is_edit_mode:
            if self.is_template_mode:
                self.setWindowTitle("Редактирование шаблона колонки")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Редактирование шаблона колонки")
            else:
                self.setWindowTitle("Редактирование колонки проекта")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Редактирование колонки проекта")
        else:
            if self.is_template_mode:
                self.setWindowTitle("Добавление шаблона колонки")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Добавление шаблона колонки")
            else:
                self.setWindowTitle("Добавление колонки в проект")
                if hasattr(self, 'titleLabel'):
                    self.titleLabel.setText("Добавление колонки в проект")

        if hasattr(self, 'lineEditName'):
            self.lineEditName.setMaxLength(100)

        # Настройка индикатора цвета
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
            name = self.column_data.get('name', '')
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
        """Обработка сохранения колонки"""
        if self.read_only:
            QMessageBox.information(self, "Информация", "В режиме просмотра редактирование недоступно")
            return

        if not self.validate():
            return

        column_name = self.lineEditName.text().strip()

        column_data = {
            'id': self.column_data.get('id', None),
            'name': column_name,
            'color': self.current_color,
            'is_done_column': self.is_done_column,
            'position': self.column_data.get('position', 0)
        }

        self.column_saved.emit(column_data)
        self.accept()

    def validate(self):
        """Валидация введенных данных"""
        if not hasattr(self, 'lineEditName'):
            return False

        name = self.lineEditName.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите название колонки.")
            return False

        if len(name) < 1:
            QMessageBox.warning(self, "Ошибка", "Название колонки должно содержать хотя бы 1 символ.")
            return False

        if len(name) > 100:
            QMessageBox.warning(self, "Ошибка", "Название колонки не должно превышать 100 символов.")
            return False

        if not self.current_color:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите цвет для колонки.")
            return False

        return True

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
        """Обновление предпросмотра колонки"""
        if hasattr(self, 'previewTitleLabel') and hasattr(self, 'lineEditName'):
            name = self.lineEditName.text().strip()
            if not name:
                name = "Название колонки"
            self.previewTitleLabel.setText(name)
            self.previewTitleLabel.setStyleSheet(f"""
                font-size: 16px;
                font-weight: bold;
                color: {self.current_color};
            """)

        if hasattr(self, 'previewColorIndicator'):
            self.previewColorIndicator.setStyleSheet(f"""
                border-radius: 10px;
                background-color: {self.current_color};
                border: 1px solid #E0E0E0;
            """)

    def get_column_data(self):
        """Получение данных колонки"""
        if not hasattr(self, 'lineEditName'):
            return {}
        name = self.lineEditName.text().strip()
        return {
            'id': self.column_data.get('id', None),
            'name': name,
            'color': self.current_color,
            'is_done_column': self.is_done_column,
            'position': self.column_data.get('position', 0)
        }

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями по стрелкам"""
        self.fields = []
        if hasattr(self, 'lineEditName'):
            self.fields.append(self.lineEditName)
        if hasattr(self, 'comboBoxColor'):
            self.fields.append(self.comboBoxColor)
        if hasattr(self, 'comboBoxAssigment'):
            self.fields.append(self.comboBoxAssigment)

        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка нажатия стрелок + клик по цветному индикатору"""
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