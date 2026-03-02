import os

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtWidgets import QMenu

from windows.my_tasks.task_card import TaskCard


class ArchivedTaskCard(TaskCard):
    """Карточка архивированной задачи (наследуется от TaskCard)"""

    restore_requested = pyqtSignal(dict)  # Сигнал восстановления задачи
    delete_permanently_requested = pyqtSignal(dict)  # Сигнал полного удаления

    def __init__(self, task_data, parent=None):
        super().__init__(task_data, parent)

        # Дополнительная загрузка UI для архивированной карточки
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )

        # Загружаем дополнительные стили из UI файла
        # Примечание: мы не перезагружаем полностью виджет,
        # а применяем дополнительные стили и настройки
        self.load_ui_styles(ui_path)

        # Изменяем внешний вид для архивированных задач
        self.setProperty("archived", True)

        # Модифицируем контекстное меню
        self.modify_context_menu()

    def load_ui_styles(self, ui_path):
        """Загрузка стилей из UI файла"""
        try:
            # Создаем временный виджет для загрузки стилей
            temp_widget = uic.loadUi(os.path.join(ui_path, "archived_task_card.ui"))

            # Копируем стили
            archived_style = temp_widget.styleSheet()
            current_style = self.styleSheet()

            # Объединяем стили (стили архива имеют приоритет для определенных свойств)
            self.setStyleSheet(current_style + "\n" + archived_style)

            # Удаляем временный виджет
            temp_widget.deleteLater()
        except Exception as e:
            print(f"Не удалось загрузить стили из UI: {e}")

    def modify_context_menu(self):
        """Изменение контекстного меню для архивированных задач"""
        # Отключаем стандартное меню и подключаем своё
        try:
            self.menuButton.clicked.disconnect()
        except TypeError:
            pass  # Если не было подключений, игнорируем

        self.menuButton.clicked.connect(self.show_archived_context_menu)

    def show_archived_context_menu(self):
        """Показать контекстное меню для архивированной задачи"""
        menu = QMenu(self)

        # Копируем стиль из родительского класса для единообразия
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 6px 0;
                font-size: 14px;
            }
            QMenu::item {
                padding: 10px 30px 10px 15px;
                color: #1B232A;
            }
            QMenu::item:selected {
                background-color: #ccab6e;
                color: white;
                border-radius: 6px;
                margin: 2px 6px;
            }
        """)

        # Действие восстановления (ВМЕСТО архивирования)
        restore_action = menu.addAction("Восстановить")
        restore_action.triggered.connect(lambda: self.restore_requested.emit(self.task_data))

        # Редактирование (оставляем как есть)
        edit_action = menu.addAction("Редактировать")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_data))

        # Дублирование (оставляем как есть)
        duplicate_action = menu.addAction("Дублировать")
        duplicate_action.triggered.connect(lambda: self.duplicate_requested.emit(self.task_data))

        # Действие полного удаления (вместо обычного удаления)
        delete_action = menu.addAction("Удалить навсегда")
        delete_action.triggered.connect(lambda: self.delete_permanently_requested.emit(self.task_data))

        # Показываем меню под кнопкой
        menu.exec(
            self.menuButton.mapToGlobal(
                QPoint(0, self.menuButton.height())
            )
        )

    def update_data(self, task_data):
        """Обновление данных карточки"""
        super().update_data(task_data)

        # Дополнительная настройка для архивированных задач
        # Например, можно добавить метку "В архиве" или изменить цвет
        if not hasattr(self, 'archive_badge'):
            from PyQt6.QtWidgets import QLabel
            self.archive_badge = QLabel("📦 В архиве", self)
            self.archive_badge.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 10px;
                    font-style: italic;
                    padding: 2px 5px;
                    background-color: #f0f0f0;
                    border-radius: 3px;
                }
            """)
            # Добавляем бейдж в нижнюю часть карточки
            if hasattr(self, 'footer_layout'):
                self.footer_layout.insertWidget(0, self.archive_badge)