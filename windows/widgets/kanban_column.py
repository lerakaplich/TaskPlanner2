# windows/widgets/kanban_column.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent


class KanbanColumn(QFrame):
    """Универсальная колонка канбан-доски - только UI"""

    task_dropped = pyqtSignal(int, int)
    task_position_changed = pyqtSignal(int, int)
    column_cleared = pyqtSignal(int)

    def __init__(self, column_data: dict, parent=None):
        super().__init__(parent)

        self.column_id = column_data["id"]
        self.column_name = column_data["name"]
        self.column_color = column_data.get("color", "#2196F3")
        self.is_done_column = column_data.get("is_done", False)

        self.task_cards = []
        self._drag_over_index = -1
        self._stretch = None  # Сохраняем ссылку на растяжение

        self.setup_ui()
        self.setAcceptDrops(True)

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

        self._setup_header(main_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        main_layout.addWidget(line)

        self._setup_tasks_area(main_layout)

        self.setLayout(main_layout)

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

        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 2)

        # Сохраняем ссылку на растяжение
        self._stretch = self.tasks_layout.addStretch()

        scroll.setWidget(self.tasks_container)
        parent_layout.addWidget(scroll)

    # ==========================================================
    # Управление карточками
    # ==========================================================

    def add_task(self, task_card):
        """Добавляет карточку задачи в колонку"""
        if task_card is None:
            return

        # Получаем индекс растяжения
        stretch_index = -1
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() == self._stretch:
                stretch_index = i
                break

        # Вставляем перед растяжением
        if stretch_index >= 0:
            self.tasks_layout.insertWidget(stretch_index, task_card)
        else:
            self.tasks_layout.addWidget(task_card)

        self.task_cards.append(task_card)

        # Принудительно обновляем
        task_card.show()
        task_card.updateGeometry()
        self.tasks_container.updateGeometry()

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
        """Переупорядочивает карточки"""
        # Очищаем layout от карточек, но сохраняем растяжение
        for card in self.task_cards:
            self.tasks_layout.removeWidget(card)

        # Добавляем в новом порядке
        stretch_index = -1
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() == self._stretch:
                stretch_index = i
                break

        for i, card in enumerate(task_widgets_order):
            if stretch_index >= 0:
                self.tasks_layout.insertWidget(stretch_index + i, card)
            else:
                self.tasks_layout.addWidget(card)

        self.task_cards = task_widgets_order

    # ==========================================================
    # Drag & Drop
    # ==========================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if not event.mimeData().hasFormat("application/x-task"):
            event.ignore()
            return
        self._drag_over_index = len(self.task_cards)
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
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

    def sizeHint(self):
        return QSize(300, 500)