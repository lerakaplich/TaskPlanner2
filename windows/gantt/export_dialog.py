# windows/gantt/export_dialog.py

from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QLabel, QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt


class ExportDialog(QDialog):
    """Диалог выбора формата экспорта диаграммы Ганта."""

    EXPORT_FORMATS = {
        "image": "📷 Изображение (PNG)",
        "excel": "📊 Excel (XLSX)",
        "docx": "📄 Word документ (DOCX)"
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт диаграммы Ганта")
        self.setMinimumSize(400, 300)
        self.setModal(True)

        self._selected_format = "image"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("📤 Экспорт диаграммы Ганта")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1B232A;")
        layout.addWidget(title_label)

        # Описание
        desc_label = QLabel(
            "Выберите формат, в котором вы хотите экспортировать данные диаграммы Ганта:"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Группа форматов
        format_group = QGroupBox("Формат экспорта")
        format_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #1B232A;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        format_layout = QVBoxLayout(format_group)
        format_layout.setSpacing(10)

        # Радиокнопки для выбора формата
        self.format_buttons = {}
        self.format_group_buttons = QButtonGroup(self)

        for format_key, format_name in self.EXPORT_FORMATS.items():
            radio = QRadioButton(format_name)
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    color: #1B232A;
                    spacing: 8px;
                    padding: 5px;
                }
                QRadioButton:hover {
                    background-color: #F5F5F5;
                    border-radius: 5px;
                }
            """)

            # Сохраняем format_key в свойстве объекта, чтобы избежать проблем с лямбдой
            radio.format_key = format_key
            radio.toggled.connect(self._on_format_selected)

            if format_key == "image":
                radio.setChecked(True)

            format_layout.addWidget(radio)
            self.format_buttons[format_key] = radio
            self.format_group_buttons.addButton(radio)

        layout.addWidget(format_group)

        # Информация о выбранном формате (создаём ДО подключения сигналов)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            background-color: #F8F9FA;
            border-radius: 8px;
            padding: 10px;
            color: #666666;
            font-size: 12px;
        """)
        layout.addWidget(self.info_label)

        # Обновляем информацию для начального выбранного формата
        self._update_info_label("image")

        layout.addStretch()

        # Кнопки действий
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        export_btn = QPushButton("Экспортировать")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 10px 20px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        export_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(export_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

    def _on_format_selected(self, checked: bool) -> None:
        """Обработчик выбора формата."""
        if not checked:
            return

        # Находим выбранную радиокнопку
        for format_key, radio in self.format_buttons.items():
            if radio.isChecked():
                self._selected_format = format_key
                self._update_info_label(format_key)
                break

    def _update_info_label(self, format_key: str) -> None:
        """Обновляет информационную метку в зависимости от выбранного формата."""
        info_texts = {
            "image": "📷 Изображение (PNG)\n\n"
                     "Сохранит текущую диаграмму Ганта как изображение.\n"
                     "Подходит для вставки в отчёты и презентации.\n\n"
                     "✓ Сохраняется точный внешний вид диаграммы\n"
                     "✓ Включает все цвета, связи и подписи\n"
                     "✓ Формат: PNG (прозрачность не сохращается)",

            "excel": "📊 Excel (XLSX)\n\n"
                     "Экспортирует данные задач в таблицу Excel.\n"
                     "Подходит для анализа, фильтрации и дальнейшей обработки.\n\n"
                     "✓ Экспортируются все данные о задачах\n"
                     "✓ Включает: названия, даты, исполнителей, приоритеты\n"
                     "✓ Можно сортировать и фильтровать данные\n"
                     "✓ Формат: XLSX (Microsoft Excel)",

            "docx": "📄 Word документ (DOCX)\n\n"
                    "Создаёт структурированный отчёт в формате Word.\n"
                    "Подходит для печати, отправки руководству и архивации.\n\n"
                    "✓ Включает статистику по задачам\n"
                    "✓ Детальная таблица всех задач\n"
                    "✓ Информация о связях между задачами\n"
                    "✓ Профессиональное оформление для отчётов\n"
                    "✓ Формат: DOCX (Microsoft Word)"
        }
        self.info_label.setText(info_texts.get(format_key, ""))

    def get_selected_format(self) -> str:
        """Возвращает выбранный формат экспорта."""
        return self._selected_format