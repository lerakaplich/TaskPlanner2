# windows/widgets/kanban_column.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent


class KanbanColumn(QFrame):
    """Универсальная колонка канбан-доски - только UI"""

    # Сигналы для передачи событий в сервис
    task_dropped = pyqtSignal(int, int)  # task_id, column_id
    task_position_changed = pyqtSignal(int, int)  # task_id, new_position
    column_cleared = pyqtSignal(int)  # column_id

    def __init__(self, column_data: dict, parent=None):
        super().__init__(parent)

        self.column_id = column_data["id"]
        self.column_name = column_data["name"]
        self.column_color = column_data.get("color", "#2196F3")
        self.is_done_column = column_data.get("is_done", False)

        self.task_cards = []  # Список UI карточек в колонке
        self._drag_over_index = -1

        self.setup_ui()
        self.setAcceptDrops(True)

    # ==========================================================
    # Настройка UI
    # ==========================================================

    def setup_ui(self):
        """Настройка UI колонки"""
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
        """)

        self.setMinimumWidth(280)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        self._setup_header(main_layout)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        main_layout.addWidget(line)

        # Область задач с прокруткой
        self._setup_tasks_area(main_layout)

        self.setLayout(main_layout)

        # Для обратной совместимости
        self.tasksLayout = self.tasks_layout
        self.countLabel = self.count_label
        self.titleLabel = self.title_label

    def _setup_header(self, parent_layout):
        """Настраивает заголовок колонки"""
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self.column_name)
        self.title_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
                padding: 5px;
            }
        """)
        header_layout.addWidget(self.title_label)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("""
            QLabel {
                background-color: #ccab6e;
                color: white;
                border-radius: 12px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 30px;
            }
        """)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()

        header_widget.setLayout(header_layout)
        parent_layout.addWidget(header_widget)

    def _setup_tasks_area(self, parent_layout):
        """Настраивает область с задачами"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 3px;
            }
        """)

        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background-color: transparent;")

        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 2)
        self.tasks_layout.addStretch()
        self.tasks_container.setLayout(self.tasks_layout)

        scroll.setWidget(self.tasks_container)
        parent_layout.addWidget(scroll)

    # ==========================================================
    # Управление карточками
    # ==========================================================

    def add_task(self, task_card):
        """Добавляет карточку задачи в колонку"""
        if task_card is None:
            return

        # Вставляем перед растяжением
        stretch_index = self.tasks_layout.count() - 1
        self.tasks_layout.insertWidget(stretch_index, task_card)
        self.task_cards.append(task_card)

    def remove_task(self, task_card):
        """Удаляет карточку задачи из колонки"""
        if task_card in self.task_cards:
            self.task_cards.remove(task_card)
        self.tasks_layout.removeWidget(task_card)

    def clear_tasks(self):
        """Очищает все карточки из колонки"""
        for card in self.task_cards[:]:
            self.tasks_layout.removeWidget(card)
            card.deleteLater()
        self.task_cards.clear()

    def get_tasks(self):
        """Возвращает список всех карточек в колонке"""
        return self.task_cards[:]

    def get_task_count(self):
        """Возвращает количество карточек в колонке"""
        return len(self.task_cards)

    def update_count(self, count):
        """Обновляет счетчик задач"""
        self.count_label.setText(str(count))

    def reorder_tasks(self, task_widgets_order: list):
        """Переупорядочивает карточки согласно переданному порядку"""
        # Удаляем все карточки из layout
        for card in self.task_cards:
            self.tasks_layout.removeWidget(card)

        # Добавляем в новом порядке
        for card in task_widgets_order:
            stretch_index = self.tasks_layout.count() - 1
            self.tasks_layout.insertWidget(stretch_index, card)

        self.task_cards = task_widgets_order

    # ==========================================================
    # Drag & Drop
    # ==========================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка входа перетаскивания"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Обработка движения перетаскивания"""
        if not event.mimeData().hasFormat("application/x-task"):
            event.ignore()
            return

        # Вычисляем позицию вставки
        pos = event.position().toPoint()
        self._drag_over_index = self._get_drop_index(pos)
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Обработка сброса задачи"""
        if not event.mimeData().hasFormat("application/x-task"):
            event.ignore()
            return

        try:
            import json
            task_data = json.loads(event.mimeData().data("application/x-task").data().decode())
            task_id = task_data.get("id")

            if task_id:
                self.task_dropped.emit(task_id, self.column_id)
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception as e:
            print(f"❌ Ошибка обработки drop: {e}")
            event.ignore()

    def _get_drop_index(self, pos) -> int:
        """Вычисляет индекс вставки по позиции мыши"""
        # Простая логика - добавляем в конец
        return len(self.task_cards)

    # ==========================================================
    # Подсветка при перетаскивании
    # ==========================================================

    def _highlight(self):
        """Подсвечивает колонку при наведении"""
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 8px;
                border: 2px solid #ccab6e;
            }
        """)

    def _unhighlight(self):
        """Убирает подсветку"""
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
        """)

    # ==========================================================
    # Вспомогательные методы
    # ==========================================================

    def sizeHint(self):
        return QSize(300, 500)