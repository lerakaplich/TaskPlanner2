# windows/projects/project_view_page.py

import os
from typing import Dict, List
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QScrollArea, QHBoxLayout, QVBoxLayout, QMessageBox, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6 import uic

from windows.other_tasks.others_task_card import OthersTaskCard
from windows.archive.archived_task_card import ArchivedTaskCard
from windows.widgets.kanban_column import KanbanColumn
from services.projects_service.project_view_service import ProjectViewService


class ProjectViewPage(QWidget):
    """Страница просмотра проекта - только UI, вся логика в сервисе"""

    projectUpdated = pyqtSignal()
    go_back = pyqtSignal()  # Сигнал для возврата

    def __init__(self, session, project_id: int, project_service, parent=None):
        super().__init__(parent)

        self.project_id = project_id
        self.columns = {}
        self.column_widgets = []
        self.parent_window = parent

        # Получаем текущего пользователя
        current_user = self._get_current_user(parent)

        # Создаём сервис
        self.view_service = ProjectViewService(session, project_service, current_user)

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "project_page.ui"), self)

        # Подключаем кнопку назад
        if hasattr(self, 'back_button'):
            self.back_button.clicked.connect(self._on_go_back)

        # Получаем данные
        self.project_data = self.view_service.get_project_data(project_id)
        self.is_archived_project = self.view_service.is_project_archived(project_id)
        self.project_columns = self.view_service.get_project_columns(project_id)

        # Настраиваем UI
        self._setup_ui()
        self.setup_kanban()
        self.load_tasks()

    def _get_current_user(self, parent) -> Dict:
        """Извлекает текущего пользователя из родительского окна"""
        if parent and hasattr(parent, 'current_user'):
            return parent.current_user
        return {"id": 1, "last_name": "Копейкина", "first_name": "Виктория"}

    def _on_go_back(self):
        """Обработчик нажатия кнопки назад"""
        self.go_back.emit()
        if self.parent_window and hasattr(self.parent_window, 'contentStack'):
            self.parent_window.contentStack.setCurrentIndex(0)

    def _setup_ui(self):
        """Настройка UI"""
        project_name = self.view_service.get_project_name(self.project_id)

        if hasattr(self, 'projectNameLabel'):
            self.projectNameLabel.setText(f"📋 {project_name}")

        if self.is_archived_project:
            status_text = "В архиве"
            status_style = "color: white; background-color: #999999; border-radius: 10px; padding: 4px 12px;"
        else:
            status_text = "Активен"
            status_style = "color: white; background-color: #4CAF50; border-radius: 10px; padding: 4px 12px;"

        if hasattr(self, 'statusLabel'):
            self.statusLabel.setText(status_text)
            self.statusLabel.setStyleSheet(status_style)

        # Ищем или создаём кнопки для участников и администраторов
        self._setup_members_buttons()

    def _setup_members_buttons(self):
        """Создаёт или находит кнопки для участников и администраторов"""
        # Ищем существующие кнопки в UI
        participants_btn = None
        admins_btn = None

        # Проверяем различные возможные имена кнопок
        btn_names_participants = ['participantsBtn', 'btnParticipants', 'btnMembers', 'membersBtn']
        btn_names_admins = ['adminsBtn', 'btnAdmins', 'btnManagers', 'managersBtn']

        for name in btn_names_participants:
            if hasattr(self, name):
                participants_btn = getattr(self, name)
                break

        for name in btn_names_admins:
            if hasattr(self, name):
                admins_btn = getattr(self, name)
                break

        # Если кнопки не найдены в UI, создаём их программно
        if participants_btn is None or admins_btn is None:
            # Ищем контейнер для кнопок (обычно это layout или frame вверху страницы)
            container = self._find_button_container()

            if container:
                # Создаём кнопки, если их нет
                if participants_btn is None:
                    participants_btn = QPushButton("👥 Участники")
                    participants_btn.setObjectName("participantsBtn")
                    participants_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #1B232A;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #2C3640;
                        }
                    """)
                    container.addWidget(participants_btn)

                if admins_btn is None:
                    admins_btn = QPushButton("👑 Администраторы")
                    admins_btn.setObjectName("adminsBtn")
                    admins_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #1B232A;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #2C3640;
                        }
                    """)
                    container.addWidget(admins_btn)

        # Подключаем сигналы
        if participants_btn:
            participants_btn.clicked.connect(self._show_participants)
        if admins_btn:
            admins_btn.clicked.connect(self._show_admins)

    def _find_button_container(self):
        """Находит контейнер для кнопок в UI"""
        # Проверяем, есть ли специальный контейнер для кнопок
        if hasattr(self, 'buttonContainer'):
            return self.buttonContainer

        # Проверяем, есть ли панель инструментов
        if hasattr(self, 'toolbar'):
            return self.toolbar

        # Проверяем, есть ли верхний layout
        if hasattr(self, 'topLayout'):
            return self.topLayout

        # Ищем первый QHBoxLayout в верхней части страницы
        for child in self.children():
            if isinstance(child, QWidget):
                layout = child.layout()
                if layout and isinstance(layout, QHBoxLayout):
                    return layout

        # Если ничего не нашли, создаём новый контейнер в верхней части страницы
        # Ищем главный layout
        main_layout = self.layout()
        if main_layout is None:
            # Создаём главный layout, если его нет
            main_layout = QVBoxLayout(self)
            self.setLayout(main_layout)

        # Создаём контейнер для кнопок
        container = QHBoxLayout()
        main_layout.insertLayout(0, container)
        return container

    def setup_kanban(self):
        """Создаёт колонки канбан-доски"""
        self._clear_layout(self.kanbanLayout)

        if not self.project_columns:
            empty_label = QLabel("Нет настроенных колонок для этого проекта")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
            self.kanbanLayout.addWidget(empty_label)
            return

        # Создаём колонки
        scroll_widget = QWidget()
        main_layout = QHBoxLayout(scroll_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        horizontal_scroll = self._create_scroll_area()

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(self.project_columns, key=lambda x: x['position']):
            column_widget = KanbanColumn(col)
            self.columns[col['name']] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        columns_layout.addStretch()
        horizontal_scroll.setWidget(columns_container)
        main_layout.addWidget(horizontal_scroll)

        # Вертикальный скролл
        vertical_scroll = self._create_scroll_area(horizontal=True)
        vertical_scroll.setWidget(scroll_widget)
        self.kanbanLayout.addWidget(vertical_scroll)

    def _create_scroll_area(self, horizontal: bool = False):
        """Создаёт область прокрутки"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        if horizontal:
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:horizontal { background: #f0f0f0; height: 10px; border-radius: 5px; }
            QScrollBar::handle:horizontal { background: #c0c0c0; border-radius: 5px; }
            QScrollBar:vertical { background: #f0f0f0; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 5px; }
        """)

        return scroll

    def load_tasks(self):
        """Загружает задачи через сервис"""
        if not self.project_id:
            return

        tasks = self.view_service.get_project_tasks(self.project_id, self.is_archived_project)

        # Очищаем колонки
        for column in self.column_widgets:
            column.clear_tasks()

        # Группируем задачи
        tasks_by_column = self.view_service.group_tasks_by_column(tasks)

        # Добавляем задачи в колонки
        all_tasks = []
        for col_data in self.project_columns:
            column_name = col_data['name']
            col_widget = self.columns.get(column_name)
            if col_widget:
                column_tasks = tasks_by_column.get(column_name, [])
                for task_dict in column_tasks:
                    card = self._create_task_card(task_dict)
                    if card:
                        col_widget.add_task(card)
                        all_tasks.append(task_dict)
                col_widget.update_count(len(column_tasks))

        self._update_statistics(all_tasks)

    def _create_task_card(self, task_data: Dict):
        """Создаёт карточку задачи"""
        is_archived = task_data.get('is_archived', False)

        if is_archived or self.is_archived_project:
            card = ArchivedTaskCard(task_data, self)
            card.restore_requested.connect(self._on_restore_task)
            card.delete_permanently_requested.connect(self._on_delete_task_permanently)
            return card
        else:
            is_creator = (task_data.get('created_by') == self.view_service.current_user_id)
            tasks_service = self.view_service.get_tasks_service()

            card = OthersTaskCard(task_data, service=tasks_service, is_creator=is_creator)
            card.editRequested.connect(self._on_edit_task)
            card.deleteRequested.connect(self._on_delete_task)
            card.archiveRequested.connect(self._on_archive_task)
            card.moveToDoneColumn.connect(self._on_move_to_done)
            return card

    def _update_statistics(self, tasks: List[Dict]):
        """Обновляет статистику"""
        stats = self.view_service.calculate_statistics(tasks)

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(stats['avg_progress'])
            self.overallProgress.setFormat(f"Общий прогресс: {stats['avg_progress']}%")

    def _on_restore_task(self, task_id: int):
        """Восстановление задачи"""
        if self.view_service.restore_task(task_id):
            self.load_tasks()

    def _on_delete_task_permanently(self, task_id: int):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self, "Удаление задачи",
            "Вы уверены, что хотите удалить задачу навсегда?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.view_service.delete_task_permanently(task_id):
                self.load_tasks()

    def _on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        print(f"✏️ Редактирование задачи {task_id}")

    def _on_delete_task(self, task_id: int):
        """Удаление задачи"""
        print(f"🗑️ Удаление задачи {task_id}")

    def _on_archive_task(self, task_id: int):
        """Архивация задачи"""
        print(f"📦 Архивация задачи {task_id}")

    def _on_move_to_done(self, task_id: int):
        """Перемещение в Done"""
        print(f"✅ Задача {task_id} отмечена как выполненная")

    def _clear_layout(self, layout):
        """Очищает layout"""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self.load_tasks)

    def _show_participants(self):
        """Показывает участников проекта в режиме просмотра"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        participants = self._get_project_participants()
        if not participants:
            QMessageBox.information(self, "Участники", "В проекте нет участников")
            return

        dialog = EmployeeSelectorDialog(self, service=self.view_service.project_service, mode="participants")
        dialog.set_preselected([p.get('id') for p in participants])
        dialog.set_readonly_mode(True)
        dialog.setWindowTitle("Участники проекта")
        dialog.exec()

    def _show_admins(self):
        """Показывает администраторов проекта в режиме просмотра"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        admins = self._get_project_admins()
        if not admins:
            QMessageBox.information(self, "Администраторы", "В проекте нет администраторов")
            return

        dialog = EmployeeSelectorDialog(self, service=self.view_service.project_service, mode="admins")
        dialog.set_preselected([a.get('id') for a in admins])
        dialog.set_readonly_mode(True)
        dialog.setWindowTitle("Администраторы проекта")
        dialog.exec()

    def _get_project_participants(self) -> List[Dict]:
        """Возвращает список участников проекта"""
        if self.project_data and hasattr(self.project_data, 'members'):
            return [
                {
                    'id': member.employee_id,
                    'full_name': member.full_name,
                    'role': member.role
                }
                for member in self.project_data.members
            ]
        return []

    def _get_project_admins(self) -> List[Dict]:
        """Возвращает список администраторов проекта"""
        if self.project_data and hasattr(self.project_data, 'members'):
            return [
                {
                    'id': member.employee_id,
                    'full_name': member.full_name,
                    'role': member.role
                }
                for member in self.project_data.members
                if member.role == 'project_manager'
            ]
        return []