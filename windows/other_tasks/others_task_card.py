import json

from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QAction, QPixmap, QPainter, QDrag

from windows.my_tasks.task_card import TaskCard  # Импортируем базовый класс


class OthersTaskCard(TaskCard):
    """Карточка задачи для Создателя (с возможностями редактирования)"""
    moveToDoneColumn = pyqtSignal(int)
    editRequested = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    archiveRequested = pyqtSignal(int)
    approveRequested = pyqtSignal(int)
    returnToWorkRequested = pyqtSignal(int)

    def __init__(self, task_data, is_creator=False, parent=None):
        # Вызываем конструктор родительского класса
        super().__init__(task_data, parent)

        self.is_creator = is_creator

        # Безопасно отключаем сигналы родительского класса (если они подключены)
        try:
            self.edit_requested.disconnect()
        except TypeError:
            pass  # Сигнал не был подключен

        try:
            self.delete_requested.disconnect()
        except TypeError:
            pass

        try:
            self.archive_requested.disconnect()
        except TypeError:
            pass

        try:
            self.duplicate_requested.disconnect()
        except TypeError:
            pass

        # Настраиваем контекстное меню для создателя
        self.setup_creator_context_menu()

        # Обновляем UI с дополнительными данными
        self.setup_creator_ui()

    def setup_creator_ui(self):
        """Дополнительная настройка UI для создателя"""
        # Исполнитель (уже есть в базовом классе, но обновляем если нужно)
        assignee = self.task_data.get("assignee", "")
        if assignee:
            if isinstance(assignee, dict):
                last_name = assignee.get("last_name", "")
                first_name = assignee.get("first_name", "")
                middle_name = assignee.get("middle_name", "")

                if first_name and middle_name:
                    initials = f"{first_name[0]}.{middle_name[0]}."
                elif first_name:
                    initials = f"{first_name[0]}."
                else:
                    initials = ""

                assignee_text = f"{last_name} {initials}".strip()
                if not assignee_text:
                    assignee_text = "Неизвестен"
            else:
                assignee_text = str(assignee)

            self.executorLabel.setText(f"Исполнитель: {assignee_text}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        # Обновляем цвет дедлайна с учетом статуса задачи
        self.update_deadline_color()

    def update_deadline_color(self):
        """Обновление цвета дедлайна с учетом статуса задачи"""
        deadline = self.task_data.get("deadline", "")
        if deadline and not self.task_data.get("completed", False):
            from PyQt6.QtCore import QDate
            current_date = QDate.currentDate()
            try:
                deadline_date = QDate.fromString(deadline, "dd.MM.yyyy")
                if deadline_date and deadline_date < current_date:
                    self.deadlineLabel.setStyleSheet("""
                        QLabel {
                            font-size: 11px;
                            color: #D22730;
                            font-weight: bold;
                        }
                    """)
            except:
                pass

    def setup_creator_context_menu(self):
        """Настройка контекстного меню для создателя"""
        # Безопасно отключаем стандартное меню из родительского класса
        try:
            self.menuButton.clicked.disconnect()
        except TypeError:
            pass  # Сигнал не был подключен

        # Подключаем наше меню
        self.menuButton.clicked.connect(self.show_creator_context_menu)

    def show_creator_context_menu(self):
        """Показать контекстное меню создателя"""
        if not self.is_creator:
            return

        menu = QMenu(self)

        # Разные действия в зависимости от статуса задачи
        status = self.task_data.get("status", "todo")

        # Общие действия
        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(lambda: self.editRequested.emit(self.task_data["id"]))
        menu.addAction(edit_action)

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.task_data["id"]))
        menu.addAction(delete_action)

        menu.addSeparator()

        # Действия для задач "На проверке"
        if status == "review":
            approve_action = QAction("Одобрить выполнение", self)
            approve_action.triggered.connect(lambda: self.approveRequested.emit(self.task_data["id"]))
            menu.addAction(approve_action)

            return_action = QAction("Вернуть на доработку", self)
            return_action.triggered.connect(lambda: self.returnToWorkRequested.emit(self.task_data["id"]))
            menu.addAction(return_action)

        # Действия для выполненных задач
        elif status == "done":
            archive_action = QAction("Архивировать", self)
            archive_action.triggered.connect(lambda: self.archiveRequested.emit(self.task_data["id"]))
            menu.addAction(archive_action)

        # Действия для других статусов
        else:
            mark_done_action = QAction("✓ Отметить выполненной", self)
            mark_done_action.triggered.connect(self.mark_as_done)
            menu.addAction(mark_done_action)

        # Применяем стиль к меню
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

        # Показываем меню под кнопкой
        menu.exec(self.menuButton.mapToGlobal(
            self.menuButton.rect().bottomLeft()
        ))

    def mark_as_done(self):
        """Отметить задачу как выполненную"""
        # Отправляем сигнал с ID задачи
        self.moveToDoneColumn.emit(self.task_data["id"])

    def update_task_data(self, new_data):
        """Обновление данных задачи"""
        self.task_data.update(new_data)
        self.setup_ui()  # Переиспользуем метод родителя для обновления UI
        self.setup_creator_ui()  # Добавляем специфичные для создателя обновления

        # Добавьте эти методы в класс OthersTaskCard (остальной код оставьте без изменений)

    def mousePressEvent(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши для drag&drop"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Создаем перетаскивание
        drag = QDrag(self)
        mime_data = QMimeData()

        # Сохраняем данные задачи в JSON
        task_json = json.dumps(self.task_data, ensure_ascii=False)
        mime_data.setText(task_json)
        mime_data.setData("application/x-task", task_json.encode('utf-8'))

        drag.setMimeData(mime_data)

        # Создаем полупрозрачное изображение для перетаскивания
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        # Выполняем перетаскивание
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        """Обработка входа перетаскивания"""
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Обработка перемещения над карточкой"""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Обработка сброса на карточку"""
        event.acceptProposedAction()