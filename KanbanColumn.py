from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton,
                             QScrollArea, QWidget, QSizePolicy)
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class KanbanColumn(QFrame):
    """Колонка канбан-доски"""

    task_add_requested = pyqtSignal(str)  # Сигнал для добавления задачи
    task_dropped = pyqtSignal(dict, str)  # Сигнал при сбросе задачи

    def __init__(self, column_id, title, color="#FFFFFF", parent=None):
        super().__init__(parent)
        self.column_id = column_id
        self.title = title
        self.color = color

        # Загружаем UI из файла
        loadUi("kanban_column.ui", self)

        self.setObjectName("kanbanColumn")
        self.setup_ui()

        # Разрешаем drop для перетаскивания задач
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Настройка UI колонки"""
        # Устанавливаем заголовок
        self.titleLabel.setText(self.title)

        # Настраиваем стиль колонки
        self.setStyleSheet(f"""
            QFrame#kanbanColumn {{
                background-color: {self.color};
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                min-width: 280px;
                margin: 5px;
            }}
            QFrame#kanbanColumn:hover {{
                border: 2px solid #E8E8E8;
            }}
        """)

        # Настройка скролла
        scroll_bar = self.scrollArea.verticalScrollBar()
        scroll_bar.setStyleSheet("""
            QScrollBar:vertical {
                background: #F5F5F7;
                width: 10px;
                margin: 10px 2px 10px 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A8A8A8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Подключаем кнопку добавления
        self.addButton.clicked.connect(self.on_add_button_clicked)

        # Получаем layout для задач
        self.tasks_layout = self.tasksContainer.layout()

    def add_task_card(self, task_card):
        """Добавить карточку задачи в колонку"""
        self.tasks_layout.addWidget(task_card)

    def remove_task_card(self, task_card):
        """Удалить карточку задачи из колонки"""
        task_card.setParent(None)
        self.tasks_layout.removeWidget(task_card)

    def clear_tasks(self):
        """Очистить все задачи в колонке"""
        for i in reversed(range(self.tasks_layout.count())):
            widget = self.tasks_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def get_task_count(self):
        """Получить количество задач в колонке"""
        return self.tasks_layout.count()

    def set_task_count(self, count):
        """Обновить заголовок с количеством задач"""
        # Извлекаем иконку из текущего заголовка
        current_text = self.titleLabel.text()
        if " " in current_text:
            icon = current_text.split(" ")[0]
        else:
            icon = "📝"

        self.titleLabel.setText(f"{icon} {self.title} ({count})")

    def on_add_button_clicked(self):
        """Обработка клика по кнопке добавления"""
        self.task_add_requested.emit(self.column_id)

    # Drag & Drop методы
    def dragEnterEvent(self, event):
        """Обработка входа перетаскиваемого объекта"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Обработка перемещения объекта над колонкой"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Обработка сброса объекта"""
        if event.mimeData().hasText():
            try:
                task_data = json.loads(event.mimeData().text())
                # Изменяем статус задачи в соответствии с колонкой
                task_data["status"] = self.column_id

                # Отправляем сигнал с данными задачи
                self.task_dropped.emit(task_data, self.column_id)

                event.acceptProposedAction()
            except:
                event.ignore()