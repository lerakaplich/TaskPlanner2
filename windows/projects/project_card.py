# windows/projects/project_card.py

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtGui import QAction
import os

from PyQt6.QtWidgets import QFrame, QLabel, QMenu


class ProjectCard(QFrame):
    """Карточка проекта с кнопкой редактирования и отображением участников"""

    edit_clicked = pyqtSignal(int)  # Сигнал для редактирования
    open_clicked = pyqtSignal(int)  # Сигнал для открытия
    archive_clicked = pyqtSignal(int)  # Сигнал для архивации

    def __init__(self, project_id, project_data, parent=None):
        super().__init__(parent)

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_card.ui"), self)

        self.project_id = project_id
        self.project_data = project_data

        # 👇 СОЗДАЕМ МЕТКУ ДЛЯ ЗАДАЧ
        self.tasksLabel = QLabel()
        self.tasksLabel.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #1B232A;
                padding: 1px 0px;
                font-weight: bold;
            }
        """)

        # 👇 СОЗДАЕМ МЕТКУ ДЛЯ КОЛОНОК
        self.columnsLabel = QLabel()
        self.columnsLabel.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #D22730;
                padding: 1px 0px;
                font-weight: bold;
            }
        """)

        # Вставляем метки после admins
        layout = self.layout()
        if layout:
            # Находим индекс виджета admins
            admins_index = layout.indexOf(self.admins)
            if admins_index >= 0:
                # Вставляем задачи после admins
                layout.insertWidget(admins_index + 1, self.tasksLabel)
                # Вставляем колонки после задач
                layout.insertWidget(admins_index + 2, self.columnsLabel)
            else:
                # Если не нашли, добавляем в конец перед кнопками
                btn_index = layout.count() - 1
                layout.insertWidget(btn_index, self.tasksLabel)
                layout.insertWidget(btn_index + 1, self.columnsLabel)

        # Заполняем данными
        self.update_data(project_data)

        # Подключаем сигналы
        self.btnOpen.clicked.connect(lambda: self.open_clicked.emit(self.project_id))
        self.btnEdit.clicked.connect(lambda: self.edit_clicked.emit(self.project_id))

        # Обработчик для кнопки меню
        if hasattr(self, 'menuButton'):
            self.menuButton.clicked.connect(self.show_context_menu)

        # Настройка размеров
        self.setSizePolicy(self.sizePolicy().Policy.Expanding,
                           self.sizePolicy().Policy.Minimum)

    def show_context_menu(self):
        """Показывает контекстное меню с действиями (только архивирование)"""
        print(f"🔍 MENU: Показываем меню для проекта {self.project_id}")

        menu = QMenu(self)

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

        archive_action = QAction("Архивировать", self)
        archive_action.triggered.connect(lambda: self._on_archive_clicked())
        menu.addAction(archive_action)

        menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

    def _on_archive_clicked(self):
        """Обработчик нажатия на пункт меню 'Архивировать'"""
        print(f"🔍 MENU: Нажат пункт 'Архивировать' для проекта {self.project_id}")
        self.archive_clicked.emit(self.project_id)

    def update_data(self, project_data):
        """Обновление данных карточки"""
        self.projectTitle.setText(project_data.name if project_data.name else '')

        # Прогресс
        if project_data.tasks_total > 0:
            progress = int((project_data.tasks_done / project_data.tasks_total) * 100)
        else:
            progress = 0
        self.progressBar.setValue(progress)

        # Владелец
        owner_name = getattr(project_data, 'owner_name', 'Не назначен')
        self.projectInfo.setText(f"Владелец: {owner_name}")

        # Дата создания
        created_at = getattr(project_data, 'created_at', None)
        if created_at:
            self.startDate.setText(f"Создан: {created_at}")
        else:
            self.startDate.setText("")

        # Участники
        member_count = getattr(project_data, 'member_count', 0)
        participants_text = f"Участники: {member_count} чел."
        self.participants.setText(participants_text)

        # Администраторы
        admin_count = getattr(project_data, 'admin_count', 0)
        admins_text = f"Админы: {admin_count} чел."
        self.admins.setText(admins_text)

        # 👇 ЗАДАЧИ
        tasks_total = getattr(project_data, 'tasks_total', 0)
        tasks_done = getattr(project_data, 'tasks_done', 0)

        if tasks_total > 0:
            tasks_text = f"Задачи: {tasks_done} / {tasks_total} выполнено"
        else:
            tasks_text = "Задачи: 0"

        self.tasksLabel.setText(tasks_text)

        # Меняем цвет если все задачи выполнены
        if tasks_total > 0 and tasks_done == tasks_total:
            self.tasksLabel.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #4CAF50;
                    padding: 1px 0px;
                    font-weight: bold;
                }
            """)
        else:
            self.tasksLabel.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #1B232A;
                    padding: 1px 0px;
                    font-weight: bold;
                }
            """)

        # 👇 КОЛОНКИ
        columns_count = getattr(project_data, 'columns_count', 0)
        columns_text = f"Колонок: {columns_count}"
        self.columnsLabel.setText(columns_text)


        # Увеличиваем высоту карточки
        self.setMinimumHeight(285)
        self.setMaximumHeight(285)