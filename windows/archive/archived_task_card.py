from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtWidgets import QMenu

from windows.my_tasks.task_card import TaskCard


class ArchivedTaskCard(TaskCard):
    """Карточка архивированной задачи (наследуется от TaskCard)"""

    restore_requested = pyqtSignal(dict)  # Сигнал восстановления задачи
    delete_permanently_requested = pyqtSignal(dict)  # Сигнал полного удаления

    def __init__(self, task_data, parent=None):
        super().__init__(task_data, parent)

        # Изменяем внешний вид для архивированных задач
        self.setProperty("archived", True)

        # Модифицируем контекстное меню
        self.modify_context_menu()

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