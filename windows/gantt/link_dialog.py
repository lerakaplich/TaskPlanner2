# windows/gantt/link_dialog.py

from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QLabel, QDialog, QVBoxLayout, QHBoxLayout,
    QCheckBox, QPushButton, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt


class LinkDialog(QDialog):
    """Диалог для создания связи между задачами с выбором типа связи."""

    # Типы связей
    LINK_TYPES = {
        "FS": "Финиш-Старт (FS) — Задача B начинается после завершения задачи A",
        "SS": "Старт-Старт (SS) — Задача B начинается одновременно с задачей A",
        "FF": "Финиш-Финиш (FF) — Задача B завершается одновременно с задачей A",
        "SF": "Старт-Финиш (SF) — Задача B завершается после начала задачи A",
    }

    # Описания типов для подсказок
    LINK_DESCRIPTIONS = {
        "FS": "Наиболее распространённый тип. Задача-последователь начинается только после завершения задачи-предшественника.",
        "SS": "Обе задачи начинаются одновременно. Используется для параллельных работ.",
        "FF": "Обе задачи завершаются одновременно. Используется для синхронизации финишей.",
        "SF": "Редко используемый тип. Задача-последователь завершается после начала задачи-предшественника.",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        predecessor_name: str = "",
        successor_name: str = "",
        show_instruction: bool = True
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создание связи между задачами")
        self.setMinimumSize(550, 450)
        self._predecessor_name = predecessor_name
        self._successor_name = successor_name
        self._show_instruction = show_instruction
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("🔗 Создание связи между задачами")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1B232A;
            padding-bottom: 10px;
        """)
        layout.addWidget(title_label)

        # Информация о задачах
        info_group = QGroupBox("Задачи")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
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
        info_layout = QVBoxLayout(info_group)

        # Задача-предшественник
        pred_label = QLabel(f"📌 Предшественник: <b>{self._predecessor_name or 'Не выбрана'}</b>")
        pred_label.setStyleSheet("font-size: 13px; padding: 5px;")
        pred_label.setWordWrap(True)
        pred_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(pred_label)

        # Стрелка между задачами
        arrow_label = QLabel("  ⬇  (влияет на)")
        arrow_label.setStyleSheet("font-size: 16px; color: #998664; padding: 2px 0;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(arrow_label)

        # Задача-последователь
        succ_label = QLabel(f"📌 Последователь: <b>{self._successor_name or 'Не выбрана'}</b>")
        succ_label.setStyleSheet("font-size: 13px; padding: 5px;")
        succ_label.setWordWrap(True)
        succ_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(succ_label)

        layout.addWidget(info_group)

        # Выбор типа связи
        type_group = QGroupBox("Тип связи")
        type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
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
        type_layout = QVBoxLayout(type_group)

        # Комбобокс с типами связей
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #ccab6e;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #1B232A;
                margin-right: 8px;
            }
        """)

        for key, description in self.LINK_TYPES.items():
            self.type_combo.addItem(description, key)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)

        # Описание текущего типа связи
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("""
            background-color: #F8F9FA;
            border-radius: 6px;
            padding: 10px;
            color: #666666;
            font-size: 12px;
            margin-top: 5px;
        """)
        type_layout.addWidget(self.description_label)

        layout.addWidget(type_group)

        # Инструкция (опционально)
        if self._show_instruction:
            instruction_group = QGroupBox("💡 Как это работает")
            instruction_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 12px;
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
            instruction_layout = QVBoxLayout(instruction_group)

            instruction_text = QLabel(
                "1. Выберите тип связи из выпадающего списка\n"
                "2. Нажмите «Создать связь» для подтверждения\n\n"
                "💡 Связь означает, что изменение дат задачи-предшественника\n"
                "   автоматически повлияет на даты задачи-последователя."
            )
            instruction_text.setStyleSheet("font-size: 12px; color: #666666; padding: 5px;")
            instruction_text.setWordWrap(True)
            instruction_layout.addWidget(instruction_text)

            layout.addWidget(instruction_group)

        # Чекбокс "Больше не показывать"
        self.dont_show_checkbox = QCheckBox("Больше не показывать это окно")
        self.dont_show_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #1B232A;
                spacing: 8px;
                padding: 5px 0;
            }
        """)
        layout.addWidget(self.dont_show_checkbox)

        layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        create_button = QPushButton("✅ Создать связь")
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 12px 24px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        create_button.clicked.connect(self.accept)

        cancel_button = QPushButton("Отмена")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(create_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        # Инициализация описания
        self._on_type_changed(0)

    def _on_type_changed(self, index: int) -> None:
        """Обновление описания при выборе типа связи."""
        if index < 0:
            return
        key = self.type_combo.itemData(index)
        description = self.LINK_DESCRIPTIONS.get(key, "")
        self.description_label.setText(f"📖 {description}")

    def get_link_type(self) -> str:
        """Возвращает выбранный тип связи."""
        return self.type_combo.currentData()

    def get_dont_show(self) -> bool:
        """Возвращает состояние чекбокса 'Больше не показывать'."""
        return self.dont_show_checkbox.isChecked()

    def get_link_info(self) -> Tuple[str, str]:
        """Возвращает информацию о связи."""
        link_type = self.get_link_type()
        link_name = self.LINK_TYPES.get(link_type, "").split(" — ")[0]
        return link_type, link_name


class SimpleLinkDialog(QDialog):
    """Упрощённый диалог для быстрого создания связи (без инструкции)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        predecessor_name: str = "",
        successor_name: str = ""
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создание связи")
        self.setMinimumSize(450, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title_label = QLabel("🔗 Выберите тип связи")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
        layout.addWidget(title_label)

        # Информация о задачах
        info_label = QLabel(
            f"<b>Предшественник:</b> {predecessor_name or 'Не выбрана'}<br>"
            f"<b>Последователь:</b> {successor_name or 'Не выбрана'}"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet("font-size: 13px; padding: 10px 0;")
        layout.addWidget(info_label)

        # Выбор типа связи
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        for key, description in LinkDialog.LINK_TYPES.items():
            self.type_combo.addItem(description, key)
        layout.addWidget(self.type_combo)

        layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()
        create_button = QPushButton("Создать")
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        create_button.clicked.connect(self.accept)

        cancel_button = QPushButton("Отмена")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(create_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def get_link_type(self) -> str:
        """Возвращает выбранный тип связи."""
        return self.type_combo.currentData()