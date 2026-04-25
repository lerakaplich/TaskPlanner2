import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QColor

from windows.widgets.color_picker_dialog import ColorPickerDialog


class TagDialog(QDialog):
    """Диалог добавления/редактирования хэштега"""

    tag_saved = pyqtSignal(dict)  # Сигнал при сохранении тега (передает данные тега)

    def __init__(self, tag_data=None, parent=None):
        """
        Инициализация диалога
        """
        super().__init__(parent)

        self.tag_data = tag_data or {}
        self.is_edit_mode = bool(tag_data and tag_data.get('id'))
        self.current_color = self.tag_data.get('color', '#ccab6e')

        # === ИСПРАВЛЕННАЯ ЗАГРУЗКА UI ===
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",  # поднимаемся на 3 уровня вверх
            "ui", "settings", "tags", "tag_dialog.ui"
        )

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"Не найден UI файл:\n{ui_path}\n\nПроверь структуру папок.")

        uic.loadUi(ui_path, self)

        self.setup_ui()
        self.connect_signals()
        self.fill_data()
        self.setup_keyboard_navigation()

    def setup_ui(self):
        """Настройка UI элементов"""
        # Устанавливаем заголовок в зависимости от режима
        if self.is_edit_mode:
            self.setWindowTitle("Редактирование темы")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование темы")

        # Настройка валидации для поля ввода
        if hasattr(self, 'lineEditName'):
            self.lineEditName.setMaxLength(50)

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

    def fill_data(self):
        """Заполнение полей данными при редактировании"""
        # Название тега
        if hasattr(self, 'lineEditName'):
            name = self.tag_data.get('name', '')
            self.lineEditName.setText(name)

        # Выбор цвета
        if hasattr(self, 'comboBoxColor'):
            # Находим индекс цвета в комбобоксе
            color_index = -1
            for i in range(self.comboBoxColor.count()):
                item_text = self.comboBoxColor.itemText(i)
                if self.current_color.lower() in item_text.lower():
                    color_index = i
                    break

            if color_index >= 0:
                self.comboBoxColor.setCurrentIndex(color_index)
            else:
                # Добавляем текущий цвет в комбобокс, если его там нет
                color_name = self.get_color_name(self.current_color)
                self.comboBoxColor.addItem(f"{color_name} ({self.current_color})")
                self.comboBoxColor.setCurrentIndex(self.comboBoxColor.count() - 1)

        # Обновляем предпросмотр
        self.update_preview()
        self.update_color_indicator(self.current_color)

    def on_save_clicked(self):
        """Обработка сохранения тега"""
        # Валидация
        if not self.validate():
            return

        # Сбор данных
        tag_name = self.lineEditName.text().strip()

        # Убираем # из начала, если пользователь его ввел
        if tag_name.startswith('#'):
            tag_name = tag_name[1:]

        # Формируем данные для сохранения
        tag_data = {
            'id': self.tag_data.get('id', None),
            'name': tag_name,
            'color': self.current_color,
            'count': self.tag_data.get('count', 0)
        }

        # Отправляем сигнал
        self.tag_saved.emit(tag_data)
        self.accept()

    def validate(self):
        """Валидация введенных данных"""
        # Проверка названия
        if not hasattr(self, 'lineEditName'):
            return False

        name = self.lineEditName.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Пожалуйста, введите название темы."
            )
            return False

        # Проверка длины
        if len(name) < 1:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название темы должно содержать хотя бы 1 символ."
            )
            return False

        if len(name) > 50:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название темы не должно превышать 50 символов."
            )
            return False

        # Проверка на недопустимые символы
        invalid_chars = [' ', '#', '@', '!', '$', '%', '^', '&', '*', '(', ')', '+', '=', '{', '}', '[', ']', '|', '\\',
                         '/', '?', '<', '>', ',', '.', ';', ':', '"', "'", '`', '~']
        for char in invalid_chars:
            if char in name:
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    f"Название темы не может содержать символ '{char}'.\n"
                    "Используйте только буквы, цифры и символ подчеркивания."
                )
                return False

        # Проверка цвета
        if not self.current_color:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Пожалуйста, выберите цвет для темы."
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
                # Заменяем пробелы на подчеркивания для предпросмотра
                name = name.replace(' ', '_')

            self.previewLabel.setText(f"#{name}")
            self.previewLabel.setStyleSheet(f"""
                font-size: 18px;
                font-weight: bold;
                color: {self.current_color};
                background-color: transparent;
            """)

    def get_tag_data(self):
        """
        Получение данных тега

        Returns:
            dict: данные тега
        """
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
        """Настройка перехода между полями по стрелкам Вверх / Вниз"""

        # Список полей в порядке перехода (от первого к последнему)
        self.fields = [
            self.lineEditName,  # Название тега
            self.comboBoxColor,  # Выбор цвета из комбобокса
            # Если у тебя есть другие поля (например, дополнительные настройки), добавь их сюда
        ]

        # Подключаем eventFilter ко всем полям
        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Обработка стрелок ↑ ↓ + клик по цветному индикатору"""

        # === 1. Обработка клика по цветному индикатору (твой старый код) ===
        if hasattr(self, 'colorIndicator') and obj == self.colorIndicator:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.on_color_indicator_clicked()
                    return True

        # === 2. Навигация по стрелкам ↑ ↓ ===
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()

            try:
                current_index = self.fields.index(obj)
            except (ValueError, AttributeError):
                # Если поле не в нашем списке — пропускаем
                return super().eventFilter(obj, event)

            if key == Qt.Key.Key_Down:
                # Стрелка вниз → следующее поле
                next_index = (current_index + 1) % len(self.fields)
                next_widget = self.fields[next_index]
                if next_widget:
                    next_widget.setFocus()
                return True

            elif key == Qt.Key.Key_Up:
                # Стрелка вверх → предыдущее поле
                prev_index = (current_index - 1) % len(self.fields)
                prev_widget = self.fields[prev_index]
                if prev_widget:
                    prev_widget.setFocus()
                return True

        # Если клавиша не обработана — передаём дальше
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # === Тест создания нового тега ===
    dialog = TagDialog()

    # === Тест редактирования (раскомментируй при необходимости) ===
    # test_tag = {
    #     'id': 5,
    #     'name': 'frontend',
    #     'color': '#3498db',
    #     'count': 12
    # }
    # dialog = TagDialog(tag_data=test_tag)

    print("Открывается диалог TagDialog...")

    if dialog.exec():
        print("✅ Диалог закрыт с сохранением")
        print("Сохранённые данные:")
        print(dialog.get_tag_data())
    else:
        print("❌ Диалог отменён пользователем")

    sys.exit(app.exec())