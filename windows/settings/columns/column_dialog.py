# windows/settings/columns/column_dialog.py

import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QSizePolicy, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QColor
from windows.widgets.color_picker_dialog import ColorPickerDialog


class ColumnDialog(QDialog):
    """Диалог добавления/редактирования колонки доски задач"""
    column_saved = pyqtSignal(dict)  # Сигнал при сохранении колонки

    def __init__(self, column_data=None, project_id=None, is_template_mode=True, parent=None):
        """
        Args:
            column_data: данные колонки (для редактирования)
            project_id: ID проекта (только для режима проекта)
            is_template_mode: True - работа с шаблонами, False - работа с колонками проекта
        """
        super().__init__(parent)
        self.column_data = column_data or {}
        self.project_id = project_id or self.column_data.get('project_id')
        self.is_template_mode = is_template_mode
        self.is_edit_mode = bool(column_data and column_data.get('id'))
        self.current_color = self.column_data.get('color', '#ccab6e')
        self.is_done_column = self.column_data.get('is_done_column', False)

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

    def setup_ui(self):
        """Настройка UI элементов"""
        # Устанавливаем заголовок в зависимости от режима
        if self.is_edit_mode:
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

        # Скрываем/показываем элементы в зависимости от режима
        if self.is_template_mode:
            # В режиме шаблона не показываем привязку к проекту
            if hasattr(self, 'projectFrame'):
                self.projectFrame.hide()
        else:
            # В режиме проекта показываем информацию о проекте
            if hasattr(self, 'projectFrame'):
                self.projectFrame.show()
            if hasattr(self, 'projectLabel') and self.project_id:
                # Здесь можно подставить название проекта
                self.projectLabel.setText(f"Проект ID: {self.project_id}")

        # Настройка валидации для поля ввода
        if hasattr(self, 'lineEditName'):
            self.lineEditName.setMaxLength(100)

        # Настройка цветного кружочка
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
        if hasattr(self, 'checkBoxIsDone'):
            self.checkBoxIsDone.stateChanged.connect(self.on_done_checkbox_changed)

    def fill_data(self):
        """Заполнение полей данными при редактировании"""
        # Название колонки
        if hasattr(self, 'lineEditName'):
            name = self.column_data.get('name', '')
            self.lineEditName.setText(name)

        # Выбор цвета
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

        # Чекбокс "Готовая колонка"
        if hasattr(self, 'checkBoxIsDone'):
            self.checkBoxIsDone.setChecked(self.is_done_column)

        # Обновляем предпросмотр
        self.update_preview()
        self.update_color_indicator(self.current_color)
        self.update_done_badge(self.is_done_column)

    def on_save_clicked(self):
        """Обработка сохранения колонки"""
        # Валидация
        if not self.validate():
            return

        # Сбор данных
        column_name = self.lineEditName.text().strip()

        # В режиме проекта проверяем, что проект выбран
        if not self.is_template_mode and not self.project_id:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не выбран проект для колонки."
            )
            return

        # Формируем данные для сохранения
        column_data = {
            'id': self.column_data.get('id', None),
            'name': column_name,
            'color': self.current_color,
            'is_done_column': self.is_done_column,
            'position': self.column_data.get('position', 0)
        }

        # Добавляем project_id только если это не режим шаблона
        if not self.is_template_mode:
            column_data['project_id'] = self.project_id

        # Отправляем сигнал
        self.column_saved.emit(column_data)
        self.accept()

    def validate(self):
        """Валидация введенных данных"""
        if not hasattr(self, 'lineEditName'):
            return False

        name = self.lineEditName.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Пожалуйста, введите название колонки."
            )
            return False

        if len(name) < 1:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название колонки должно содержать хотя бы 1 символ."
            )
            return False

        if len(name) > 100:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название колонки не должно превышать 100 символов."
            )
            return False

        if not self.current_color:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Пожалуйста, выберите цвет для колонки."
            )
            return False

        return True

    def on_color_indicator_clicked(self):
        """Открываем диалог выбора цвета по клику на кружочек"""
        dialog = ColorPickerDialog(self.current_color, self)
        if dialog.exec():
            new_color = dialog.get_selected_color()
            if new_color and new_color != self.current_color:
                self.update_color(new_color)
    def on_color_changed(self, color_text):
        """Обработка изменения цвета из комбобокса"""
        # Извлекаем цвет из текста (формат: "Название (#цвет)")
        import re
        match = re.search(r'\(#([A-Fa-f0-9]{6})\)', color_text)
        if match:
            color_code = f"#{match.group(1)}"
            self.update_color(color_code)
    def on_custom_color_clicked(self):
        """Открытие диалога выбора пользовательского цвета"""
        dialog = ColorPickerDialog(self.current_color, self)
        if dialog.exec():
            new_color = dialog.get_selected_color()
            if new_color and new_color != self.current_color:
                self.update_color(new_color)
                # Добавляем цвет в комбобокс, если его там нет
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
    def on_done_checkbox_changed(self, state):
        """Обработка изменения состояния чекбокса 'Готовая колонка'"""
        self.is_done_column = bool(state == Qt.CheckState.Checked.value)
        self.update_done_badge(self.is_done_column)
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
    def update_done_badge(self, is_done):
        """Обновление отображения бейджа 'Готовая'"""
        if hasattr(self, 'previewBadgeLabel'):
            self.previewBadgeLabel.setVisible(is_done)
        # Если колонка готовая, добавляем дополнительный стиль в предпросмотр
        if hasattr(self, 'previewFrame') and is_done:
            self.previewFrame.setStyleSheet("""
                QFrame {
                    background-color: #f0f9f0;
                    border: 2px solid #2ecc71;
                    border-radius: 10px;
                    padding: 15px;
                }
            """)
        elif hasattr(self, 'previewFrame'):
            self.previewFrame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #e9ecef;
                    border-radius: 10px;
                    padding: 15px;
                }
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
        # Обновляем цвет маленького индикатора в предпросмотре
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
            'project_id': self.project_id,
            'name': name,
            'color': self.current_color,
            'is_done_column': self.is_done_column,
            'position': self.column_data.get('position', 0)
        }

    @staticmethod
    def get_test_projects():
        return ColumnDialog.TEST_PROJECTS

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями по стрелкам Вверх / Вниз"""

        # Список всех интерактивных полей в логическом порядке
        self.fields = [
            self.lineEditName,  # Название колонки
            self.comboBoxColor,  # Выбор цвета (комбобокс)
            self.checkBoxIsDone,  # Чекбокс "Готовая колонка"
            # Добавляй сюда новые поля по мере появления
        ]

        # Устанавливаем обработчик событий клавиатуры для каждого поля
        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка нажатия стрелок Вверх/Вниз + клик по цветному индикатору"""

        # === Обработка клика по цветному индикатору (старый код) ===
        if hasattr(self, 'colorIndicator') and obj == self.colorIndicator:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.on_color_indicator_clicked()
                    return True

        # === НОВАЯ ЛОГИКА: переход по стрелкам ↑ ↓ ===
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()

            # Проверяем, есть ли obj в нашем списке полей
            try:
                current_index = self.fields.index(obj)
            except (ValueError, AttributeError):
                return super().eventFilter(obj, event)

            if key == Qt.Key.Key_Down:  # ← ИСПРАВЛЕНО
                # Переход к следующему полю
                next_index = (current_index + 1) % len(self.fields)
                next_widget = self.fields[next_index]
                if next_widget:
                    next_widget.setFocus()
                return True

            elif key == Qt.Key.Key_Up:  # ← ИСПРАВЛЕНО
                # Переход к предыдущему полю
                prev_index = (current_index - 1) % len(self.fields)
                prev_widget = self.fields[prev_index]
                if prev_widget:
                    prev_widget.setFocus()
                return True

        # Если клавиша не обработана — передаём дальше
        return super().eventFilter(obj, event)