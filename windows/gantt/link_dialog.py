# windows/gantt/link_dialog.py

import os
from typing import Optional, Tuple, List
from PyQt6.QtWidgets import (
    QWidget, QDialog, QMessageBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6 import uic

from services.gantt_service.gantt_base_service import TaskGanttData


class LinkDialog(QDialog):
    """Диалог для создания связи между задачами с выбором задач и типа связи."""

    # Типы связей
    LINK_TYPES = {
        "FS": "Финиш-Старт (FS) — Задача B начинается после завершения задачи A",
        "SS": "Старт-Старт (SS) — Задача B начинается одновременно с задачей A",
        "FF": "Финиш-Финиш (FF) — Задача B завершается одновременно с задачей A",
        "SF": "Старт-Финиш (SF) — Задача B завершается после начала задачи A",
    }

    # Сигнал при создании связи
    link_created = pyqtSignal(int, int, str)  # predecessor_id, successor_id, link_type

    def __init__(
            self,
            parent: Optional[QWidget] = None,
            tasks: List[TaskGanttData] = None,
            predecessor_id: Optional[int] = None,
            successor_id: Optional[int] = None,
            link_type: str = "FS",
            show_instruction: bool = True
    ) -> None:
        super().__init__(parent)
        self._tasks = tasks or []
        self._predecessor_id = predecessor_id
        self._successor_id = successor_id
        self._link_type = link_type
        self._show_instruction = show_instruction

        # Словари для быстрого доступа к задачам по ID
        self._task_by_id = {task.id: task for task in self._tasks}

        # Загружаем UI
        self._load_ui()
        self._populate_type_combo()
        self._populate_task_combos()
        self._restore_selected_values()
        self._setup_connections()

    def _load_ui(self) -> None:
        """Загружает UI из файла."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        ui_path = os.path.join(project_root, "ui", "gantt", "link_dialog.ui")

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            # Если UI файл не найден, создаем UI программно (fallback)
            self._create_ui_fallback()

    def _create_ui_fallback(self) -> None:
        """Создает UI программно (если файл не найден)."""
        from PyQt6.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
            QPushButton, QGroupBox
        )

        self.setWindowTitle("Создание связи между задачами")
        self.setMinimumSize(550, 450)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        self.titleLabel = QLabel("Создание связи между задачами")
        self.titleLabel.setStyleSheet("font-size: 18px; font-weight: bold; color: #1B232A; padding-bottom: 10px;")
        layout.addWidget(self.titleLabel)

        # Предшественник
        self.predecessorGroup = QGroupBox("Задача-предшественник (влияет на)")
        self.predecessorGroup.setStyleSheet("""
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
        pred_layout = QVBoxLayout(self.predecessorGroup)

        self.predecessorCombo = QComboBox()
        self.predecessorCombo.setStyleSheet("""
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
        """)
        pred_layout.addWidget(self.predecessorCombo)

        layout.addWidget(self.predecessorGroup)

        # Последователь
        self.successorGroup = QGroupBox("Задача-последователь (зависит от)")
        self.successorGroup.setStyleSheet(self.predecessorGroup.styleSheet())
        succ_layout = QVBoxLayout(self.successorGroup)

        self.successorCombo = QComboBox()
        self.successorCombo.setStyleSheet(self.predecessorCombo.styleSheet())
        succ_layout.addWidget(self.successorCombo)

        layout.addWidget(self.successorGroup)

        # Тип связи
        self.typeGroup = QGroupBox("Тип связи")
        self.typeGroup.setStyleSheet(self.predecessorGroup.styleSheet())
        type_layout = QVBoxLayout(self.typeGroup)

        self.typeCombo = QComboBox()
        self.typeCombo.setStyleSheet(self.predecessorCombo.styleSheet())
        type_layout.addWidget(self.typeCombo)

        layout.addWidget(self.typeGroup)

        # Инструкция
        self.instructionGroup = QGroupBox("💡 Как это работает")
        self.instructionGroup.setStyleSheet("""
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
        inst_layout = QVBoxLayout(self.instructionGroup)

        self.instructionText = QLabel(
            "Связь между задачами означает, что изменение дат задачи-предшественника\n"
            "автоматически повлияет на даты задачи-последователя.\n\n"
            "📌 Выберите две задачи и тип связи, затем нажмите «Создать связь»."
        )
        self.instructionText.setWordWrap(True)
        self.instructionText.setStyleSheet("font-size: 12px; color: #666666; padding: 5px;")
        inst_layout.addWidget(self.instructionText)

        layout.addWidget(self.instructionGroup)

        # Чекбокс
        self.dontShowCheckbox = QCheckBox("Больше не показывать это окно")
        self.dontShowCheckbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #1B232A;
                spacing: 8px;
                padding: 5px 0;
            }
        """)
        layout.addWidget(self.dontShowCheckbox)

        layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.createButton = QPushButton("Создать связь")
        self.createButton.setStyleSheet("""
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
        buttons_layout.addWidget(self.createButton)

        self.cancelButton = QPushButton("Отмена")
        self.cancelButton.setStyleSheet("""
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
        buttons_layout.addWidget(self.cancelButton)

        layout.addLayout(buttons_layout)

    def _populate_type_combo(self) -> None:
        """Заполняет комбобокс типами связей."""
        if not hasattr(self, 'typeCombo'):
            return

        self.typeCombo.clear()
        for key, description in self.LINK_TYPES.items():
            self.typeCombo.addItem(description, key)

    def _populate_task_combos(self) -> None:
        """Заполняет комбобоксы списком задач."""
        if not hasattr(self, 'predecessorCombo') or not hasattr(self, 'successorCombo'):
            return

        # Сортируем задачи по названию
        sorted_tasks = sorted(self._tasks, key=lambda t: t.name)

        for combo in [self.predecessorCombo, self.successorCombo]:
            combo.clear()
            combo.addItem("Выберите задачу", None)

            for task in sorted_tasks:
                # Формируем отображаемое имя с дополнительной информацией
                display_text = task.name
                if task.executor_name:
                    display_text += f" ({task.executor_name})"
                if task.project_name:
                    display_text += f" — {task.project_name}"
                combo.addItem(display_text, task.id)

    def _restore_selected_values(self) -> None:
        """Восстанавливает предустановленные значения."""
        # Восстанавливаем предшественника
        if hasattr(self, 'predecessorCombo'):
            if self._predecessor_id and self._predecessor_id in self._task_by_id:
                index = self.predecessorCombo.findData(self._predecessor_id)
                if index >= 0:
                    self.predecessorCombo.setCurrentIndex(index)

        # Восстанавливаем последователя
        if hasattr(self, 'successorCombo'):
            if self._successor_id and self._successor_id in self._task_by_id:
                index = self.successorCombo.findData(self._successor_id)
                if index >= 0:
                    self.successorCombo.setCurrentIndex(index)

        # Восстанавливаем тип связи
        if hasattr(self, 'typeCombo'):
            index = self.typeCombo.findData(self._link_type)
            if index >= 0:
                self.typeCombo.setCurrentIndex(index)

        # Показываем/скрываем инструкцию
        if hasattr(self, 'instructionGroup'):
            self.instructionGroup.setVisible(self._show_instruction)

    def _setup_connections(self) -> None:
        """Настраивает соединения сигналов."""
        if hasattr(self, 'createButton'):
            self.createButton.clicked.connect(self._on_create_link)
        if hasattr(self, 'cancelButton'):
            self.cancelButton.clicked.connect(self.reject)

    def _on_create_link(self) -> None:
        """Обработка создания связи."""
        if not hasattr(self, 'predecessorCombo') or not hasattr(self, 'successorCombo'):
            return

        pred_id = self.predecessorCombo.currentData()
        succ_id = self.successorCombo.currentData()

        # Проверка: выбраны ли задачи
        if not pred_id:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите задачу-предшественник.")
            return

        if not succ_id:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите задачу-последователь.")
            return

        # Проверка: не совпадают ли задачи
        if pred_id == succ_id:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Задача-предшественник и задача-последователь не могут быть одной и той же задачей."
            )
            return

        # Проверка: существуют ли задачи
        if pred_id not in self._task_by_id:
            QMessageBox.warning(self, "Ошибка", "Задача-предшественник не найдена.")
            return

        if succ_id not in self._task_by_id:
            QMessageBox.warning(self, "Ошибка", "Задача-последователь не найдена.")
            return

        # Получаем тип связи
        link_type = self.typeCombo.currentData()

        # Отправляем сигнал
        self.link_created.emit(pred_id, succ_id, link_type)

        # Закрываем диалог
        self.accept()

    def get_selected_tasks(self) -> Tuple[Optional[int], Optional[int]]:
        """Возвращает ID выбранных задач."""
        if hasattr(self, 'predecessorCombo') and hasattr(self, 'successorCombo'):
            return self.predecessorCombo.currentData(), self.successorCombo.currentData()
        return None, None

    def get_link_type(self) -> str:
        """Возвращает выбранный тип связи."""
        if hasattr(self, 'typeCombo'):
            return self.typeCombo.currentData()
        return "FS"

    def get_dont_show(self) -> bool:
        """Возвращает состояние чекбокса 'Больше не показывать'."""
        if hasattr(self, 'dontShowCheckbox'):
            return self.dontShowCheckbox.isChecked()
        return False