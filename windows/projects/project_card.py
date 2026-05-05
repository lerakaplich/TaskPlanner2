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

    def __init__(self, project_id, project_data, parent=None, service=None):
        super().__init__(parent)

        self.service = service
        self.project_id = project_id
        self.project_data = project_data

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_card.ui"), self)

        # Создаем дополнительные метки
        self._setup_additional_labels()

        # Заполняем данными
        self.update_data(project_data)

        # Подключаем сигналы
        self._connect_signals()

    def _setup_additional_labels(self):
        """Создает и добавляет дополнительные метки в UI"""
        # Метка для задач
        self.tasksLabel = QLabel()
        self.tasksLabel.setStyleSheet("""
            QLabel {
                font-size: 11px;
                padding: 1px 0px;
                font-weight: bold;
            }
        """)

        # Метка для колонок
        self.columnsLabel = QLabel()
        self.columnsLabel.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #D22730;
                padding: 1px 0px;
                font-weight: bold;
            }
        """)

        # Вставляем метки в layout
        layout = self.layout()
        if layout:
            admins_index = layout.indexOf(self.admins)
            if admins_index >= 0:
                layout.insertWidget(admins_index + 1, self.tasksLabel)
                layout.insertWidget(admins_index + 2, self.columnsLabel)
            else:
                btn_index = layout.count() - 1
                layout.insertWidget(btn_index, self.tasksLabel)
                layout.insertWidget(btn_index + 1, self.columnsLabel)

    def _connect_signals(self):
        """Подключает сигналы кнопок"""
        self.btnOpen.clicked.connect(lambda: self.open_clicked.emit(self.project_id))
        self.btnEdit.clicked.connect(lambda: self.edit_clicked.emit(self.project_id))

        if hasattr(self, 'menuButton'):
            self.menuButton.clicked.connect(self.show_context_menu)

        # Настройка размеров
        self.setSizePolicy(
            self.sizePolicy().Policy.Expanding,
            self.sizePolicy().Policy.Minimum
        )
        self.setMinimumHeight(285)
        self.setMaximumHeight(285)

    def show_context_menu(self):
        """Показывает контекстное меню с действиями"""
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
        archive_action.triggered.connect(lambda: self.archive_clicked.emit(self.project_id))
        menu.addAction(archive_action)

        menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

    def update_data(self, project_data):
        """Обновление данных карточки через сервис"""
        self.project_data = project_data

        if self.service:
            card_data = self.service.get_project_card_data(project_data)
        else:
            # Fallback если нет сервиса
            card_data = self._fallback_format_data(project_data)

        # Применяем данные к UI
        self._apply_card_data(card_data)

    def _fallback_format_data(self, project_data):
        """Форматирование данных без сервиса (fallback)"""
        # Прогресс
        if project_data.tasks_total > 0:
            progress = int((project_data.tasks_done / project_data.tasks_total) * 100)
        else:
            progress = 0

        # Информационная строка
        owner_name = getattr(project_data, 'owner_name', 'Не назначен')
        manager_name = getattr(project_data, 'manager_name', None)
        if manager_name:
            info_text = f"Владелец: {owner_name} | Куратор: {manager_name}"
        else:
            info_text = f"Владелец: {owner_name}"

        # Дата создания
        created_at = getattr(project_data, 'created_at', None)
        start_date_text = f"Создан: {created_at}" if created_at else ""

        # Участники
        member_count = getattr(project_data, 'member_count', 0)
        participants_text = f"Участники: {member_count} чел."

        # Администраторы
        admin_count = getattr(project_data, 'admin_count', 0)
        admins_text = f"Админы: {admin_count} чел."

        # Задачи
        tasks_total = getattr(project_data, 'tasks_total', 0)
        tasks_done = getattr(project_data, 'tasks_done', 0)

        if tasks_total > 0:
            tasks_text = f"Задачи: {tasks_done} / {tasks_total} выполнено"
        else:
            tasks_text = "Задачи: 0"

        tasks_style = "color: #4CAF50;" if (tasks_total > 0 and tasks_done == tasks_total) else "color: #1B232A;"

        # Колонки
        columns_count = getattr(project_data, 'columns_count', 0)
        columns_text = f"Колонок: {columns_count}"

        return {
            'name': project_data.name if project_data.name else '',
            'progress': progress,
            'info_text': info_text,
            'start_date_text': start_date_text,
            'participants_text': participants_text,
            'admins_text': admins_text,
            'tasks_text': tasks_text,
            'tasks_style': tasks_style,
            'columns_text': columns_text
        }

    def _apply_card_data(self, card_data: dict):
        """Применяет отформатированные данные к UI"""
        # Название проекта
        self.projectTitle.setText(card_data['name'])

        # Прогресс
        self.progressBar.setValue(card_data['progress'])

        # Информация о владельце/кураторе
        self.projectInfo.setText(card_data['info_text'])

        # Дата создания
        self.startDate.setText(card_data['start_date_text'])

        # Участники и администраторы
        self.participants.setText(card_data['participants_text'])
        self.admins.setText(card_data['admins_text'])

        # Задачи
        self.tasksLabel.setText(card_data['tasks_text'])
        self.tasksLabel.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                {card_data['tasks_style']}
                padding: 1px 0px;
                font-weight: bold;
            }}
        """)

        # Колонки
        self.columnsLabel.setText(card_data['columns_text'])