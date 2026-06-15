# windows/other_tasks/others_tasks_page.py

import os
from typing import Dict, List

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import (QWidget, QScrollArea,
                             QMessageBox, QSizePolicy, QHBoxLayout)

from database import get_tasks_session
from services.permissions.app_permissions import AppRole
from services.tasks_service.tasks_service import TasksService
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog
from windows.widgets.kanban_column import KanbanColumn


class OthersTasksPage(QWidget):
    taskUpdated = pyqtSignal()
    open_project_requested = pyqtSignal(int)

    def __init__(self, parent=None, current_user=None, project_id=None, column_service=None, permission_service=None):
        super().__init__(parent)

        self._is_loading = False
        self._is_refreshing = False
        self._first_show = True
        self.permission_service = permission_service

        self.current_user = current_user or {"id": 1, "last_name": "Копейкина", "first_name": "Виктория",
                                             "middle_name": "Анатольевна"}

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        self.columns = {}
        self.column_widgets = []
        self._all_projects = []

        self.db_session = get_tasks_session()
        self.service = TasksService(
            db_session=self.db_session,
            current_user=self.current_user,
            mode="others",
            column_service=column_service
        )

        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setup_kanban()
        self._load_projects_for_filter()
        self.connect_signals()

        # Настройка UI в зависимости от прав
        self._setup_permission_ui()

    def _can_edit_or_delete_task(self) -> bool:
        """Проверяет, может ли пользователь редактировать/удалять задачи в чужих задачах"""
        if not self.permission_service:
            return True  # По умолчанию разрешаем, если нет сервиса прав

        # Только суперадмин может
        app_role = self.permission_service.app_manager.role
        return app_role == AppRole.SUPER_ADMIN

    def _can_create_task(self) -> bool:
        """Проверяет, может ли пользователь создавать задачи в чужих задачах"""
        if not self.permission_service:
            return True

        # Только суперадмин может создавать задачи в чужих задачах
        app_role = self.permission_service.app_manager.role
        return app_role == AppRole.SUPER_ADMIN

    def _can_archive_task(self) -> bool:
        """Проверяет, может ли пользователь архивировать задачи в чужих задачах"""
        if not self.permission_service:
            return True

        # Только суперадмин может архивировать чужие задачи
        app_role = self.permission_service.app_manager.role
        return app_role == AppRole.SUPER_ADMIN

    def _setup_permission_ui(self):
        """Настраивает UI в зависимости от прав пользователя"""
        # Кнопка создания задачи
        if hasattr(self, 'btnCreateTask'):
            can_create = self._can_create_task()
            self.btnCreateTask.setVisible(can_create)
            print(f"   btnCreateTask visible (Чужие задачи): {can_create}")

    def connect_signals(self):
        """Подключает сигналы UI."""
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)

        # Подключаем кнопку создания только если она видима
        if hasattr(self, 'btnCreateTask') and self.btnCreateTask.isVisible():
            self.btnCreateTask.clicked.connect(self.create_new_task)

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи с учётом прав."""
        is_creator = (task_data.get('created_by') == self.current_user.get('id'))

        # Определяем, какие действия доступны
        can_edit_delete = self._can_edit_or_delete_task()
        can_archive = self._can_archive_task()

        card = OthersTaskCard(
            task_data,
            service=self.service,
            is_creator=is_creator,
            can_edit_delete=can_edit_delete,
            can_archive=can_archive
        )
        return card

    def connect_task_card_signals(self, card):
        """Подключает сигналы карточки."""
        card.editRequested.connect(self.edit_task)
        card.deleteRequested.connect(self.delete_task)
        card.archiveRequested.connect(self.archive_task)
        card.approveRequested.connect(self.approve_task)
        card.returnToWorkRequested.connect(self.return_to_work)
        card.moveToDoneColumn.connect(self.move_to_done)
        card.project_clicked.connect(self._on_project_clicked)

        card.duplicateRequested.connect(self.duplicate_task)
        card.pauseRequested.connect(self.pause_task)
        card.resumeRequested.connect(self.resume_task)

        card.drag_started.connect(self._on_drag_started)

    def showEvent(self, event):
        """Показываем задачи при каждом отображении страницы"""
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            # При первом показе - откладываем загрузку
            QTimer.singleShot(10, self.load_tasks)
        else:
            # При повторном показе - перезагружаем полностью
            print("🔄 Повторный показ страницы Чужие задачи - перезагружаем")
            QTimer.singleShot(10, self.full_reload)

    def _on_project_filter_changed(self):
        """Обработчик изменения фильтра по проекту - перестраиваем доску"""
        project_id = self.projectFilter.currentData()
        self._current_project_id = project_id

        # Перестраиваем колонки под выбранный проект
        self._rebuild_board_for_project(project_id)

        # Загружаем задачи заново (с учётом фильтра по проекту)
        self._load_tasks_for_current_project()

    def _load_tasks_for_current_project(self):
        """Загружает задачи для текущего выбранного проекта"""
        if self._is_loading:
            return

        self._is_loading = True

        try:
            # Сбрасываем кэш колонок
            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            # Очищаем все колонки
            self.clear_all_columns()

            # Получаем все задачи (с учётом mode=others)
            all_tasks = self.service.load_tasks()

            # Фильтруем по проекту, если выбран конкретный проект
            if self._current_project_id:
                filtered_tasks = [t for t in all_tasks if t.get("project_id") == self._current_project_id]
            else:
                filtered_tasks = all_tasks

            print(f"📊 Загрузка задач для проекта {self._current_project_id}: {len(filtered_tasks)} из {len(all_tasks)}")

            # Отключаем обновления UI
            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            # Добавляем задачи в колонки
            for task in filtered_tasks:
                column_name = task.get("status")
                if column_name and column_name in self.columns:
                    card = self.create_task_card(task)
                    self.connect_task_card_signals(card)
                    column = self.columns[column_name]
                    if card.parent() != column.tasks_container:
                        card.setParent(column.tasks_container)
                    column.add_task(card)

            # Включаем обновления UI
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            # Обновляем статистику
            self.update_statistics()

            # Обновляем геометрию
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка загрузки задач для проекта: {e}")
            import traceback
            traceback.print_exc()
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    def _rebuild_board_for_project(self, project_id: int = None):
        """Перестраивает канбан-доску для выбранного проекта"""
        print(f"🔄 Перестроение доски для проекта (Чужие задачи): {project_id}")

        # Сбрасываем кэш колонок в сервисе
        if hasattr(self.service.crud, '_column_cache'):
            self.service.crud._column_cache = None

        # Получаем колонки для выбранного проекта
        if project_id:
            column_ids = self._get_project_column_ids(project_id)
            column_data = self._get_columns_by_ids(column_ids)
        else:
            column_data = self.service.get_column_data()

        # Перестраиваем UI колонок
        self._rebuild_columns_ui(column_data)

    def full_reload(self):
        """Полная перезагрузка страницы"""
        print("🔄 Полная перезагрузка страницы Чужие задачи")

        # Сбрасываем кэш колонок в сервисе
        if hasattr(self.service.crud, '_column_cache'):
            self.service.crud._column_cache = None

        # Пересоздаем доску
        self.setup_kanban()

        # Загружаем проекты заново
        self._load_projects_for_filter()

        # Загружаем задачи
        self.load_tasks()

    def _get_project_column_ids(self, project_id: int) -> List[int]:
        """Получает ID колонок выбранного проекта"""
        try:
            from models.projects import Project
            from sqlalchemy import select

            stmt = select(Project).where(Project.id == project_id)
            project = self.db_session.scalar(stmt)

            if project and project.selected_column_ids:
                ids_str = project.selected_column_ids
                if ids_str:
                    return [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
        except Exception as e:
            print(f"⚠️ Ошибка получения колонок проекта {project_id}: {e}")

        # Возвращаем ID шаблонных колонок по умолчанию
        return [24, 25, 26, 27]

    def _get_columns_by_ids(self, column_ids: List[int]) -> List[Dict]:
        """Получает данные колонок по их ID"""
        try:
            from models.projects import BoardColumn
            from sqlalchemy import select

            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids)).order_by(BoardColumn.position)
            columns = self.db_session.scalars(stmt).all()

            result = []
            for col in columns:
                result.append({
                    "id": col.id,
                    "name": col.name,
                    "color": col.color,
                    "position": col.position,
                    "is_done": col.is_done_column
                })
            return result
        except Exception as e:
            print(f"⚠️ Ошибка загрузки колонок по ID: {e}")
            return []

    def _rebuild_columns_ui(self, column_data: List[Dict]):
        """Перестраивает UI колонок"""
        self.clear_layout(self.kanbanLayout)

        if not column_data:
            print("⚠️ Нет колонок для отображения")
            return

        # Вертикальный скролл
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        # Горизонтальный скролл
        horizontal_scroll = QScrollArea()
        horizontal_scroll.setWidgetResizable(True)
        horizontal_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        horizontal_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        horizontal_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                background: #f0f0f0;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)
        columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)
            column_widget.task_dropped.connect(self._on_task_dropped)

        horizontal_scroll.setWidget(columns_container)
        main_scroll.setWidget(horizontal_scroll)
        self.kanbanLayout.addWidget(main_scroll)

        print(f"🔧 Перестроено {len(column_data)} колонок (Чужие задачи)")

    def setup_kanban(self):
        """Создает колонки канбан-доски (стандартные, для всех проектов)"""
        self._rebuild_columns_ui(self.service.get_column_data())

    def _load_projects_for_filter(self):
        """Загружает проекты для выпадающего списка (только где пользователь участник/админ/куратор/создатель)"""
        try:
            from sqlalchemy import select
            from models.projects import Project, EmployeeProject

            user_id = self.current_user.get("id") if self.current_user else None
            if not user_id:
                print("⚠️ Не удалось получить ID пользователя")
                return

            # Получаем ID проектов, где пользователь является участником (EmployeeProject)
            # или создателем проекта (Project.created_by)
            stmt = select(Project).where(
                (Project.is_archived == False) & (
                        (Project.id.in_(
                            select(EmployeeProject.project_id).where(EmployeeProject.employee_id == user_id)
                        )) |
                        (Project.created_by == user_id)
                )
            ).order_by(Project.name)

            projects = self.db_session.scalars(stmt).all()

            # Дополнительно: загружаем проекты, где пользователь является куратором
            # (если есть поле curator_id в модели Project)
            if hasattr(Project, 'curato r_id'):
                stmt_curator = select(Project).where(
                    Project.is_archived == False,
                    Project.curator_id == user_id
                )
                curator_projects = self.db_session.scalars(stmt_curator).all()
                # Объединяем без дубликатов
                all_project_ids = {p.id for p in projects}
                for p in curator_projects:
                    if p.id not in all_project_ids:
                        projects = list(projects) + [p]
                        all_project_ids.add(p.id)

            self._all_projects = [{"id": p.id, "name": p.name} for p in projects]

            # Обновляем combo box
            self.projectFilter.clear()
            self.projectFilter.addItem("Все проекты", None)
            for project in self._all_projects:
                self.projectFilter.addItem(project["name"], project["id"])

            print(f"📁 Загружено проектов для фильтра (Чужие задачи): {len(self._all_projects)}")

        except Exception as e:
            print(f"⚠️ Ошибка загрузки проектов для фильтра: {e}")
            import traceback
            traceback.print_exc()

    def connect_signals(self):
        """Подключает сигналы UI."""
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)
        self.btnCreateTask.clicked.connect(self.create_new_task)

    def clear_layout(self, layout):
        """Очищает layout."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def load_tasks(self):
        """Загружает задачи (только чужие) с защитой от повторных вызовов"""
        if self._is_loading:
            print("⚠️ Загрузка чужих задач уже выполняется, пропускаем")
            return

        self._is_loading = True

        try:
            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            self.clear_all_columns()

            tasks = self.service.load_tasks()

            print(f"\n📊 Загрузка чужих задач: {len(tasks)}")

            # Отключаем обновления UI
            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            for task in tasks:
                column_name = task.get("status")
                if column_name not in self.columns:
                    print(f"  ❌ Колонка '{column_name}' не найдена!")
                    continue

                card = self.create_task_card(task)
                self.connect_task_card_signals(card)

                column = self.columns[column_name]
                if card.parent() != column.tasks_container:
                    card.setParent(column.tasks_container)
                column.add_task(card)

            # Включаем обновления UI
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            # Обновляем геометрию
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

            self.update_statistics()

        except Exception as e:
            print(f"❌ Ошибка при загрузке задач: {e}")
            import traceback
            traceback.print_exc()
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    def _on_task_dropped(self, task_id: int, target_column_id: int):
        """Обработчик drop из KanbanColumn"""
        print(f"🔄 Получен drop в others_tasks_page: задача {task_id} → колонка ID={target_column_id}")

        target_column = None
        for col in self.column_widgets:
            if col.column_id == target_column_id:
                target_column = col
                break

        if not target_column:
            print("❌ Колонка не найдена по ID")
            return

        new_status = target_column.column_name
        print(f"🎯 Целевая колонка: '{new_status}' (ID={target_column_id})")

        task = self.service.get_task_by_id(task_id)
        if not task:
            print("❌ Задача не найдена в БД")
            return

        old_status = task.get("status")
        if old_status == new_status:
            print("ℹ️ Уже в этой колонке")
            return

        result = self.service.move_task_to_column(task_id, target_column_id)

        if result:
            self.update_task_card(result)
            self.update_statistics()
            self.taskUpdated.emit()

            from PyQt6.QtCore import QTimer
            QTimer.singleShot(150, self.load_tasks)

            print("✅ Задача успешно перемещена")
        else:
            print("❌ Не удалось переместить задачу")

    def add_task_card(self, task_data: Dict):
        """Добавляет карточку задачи в колонку."""
        card = self.create_task_card(task_data)
        self.connect_task_card_signals(card)

        column_name = task_data.get("status")
        if column_name in self.columns:
            column = self.columns[column_name]

            if card.parent() != column.tasks_container:
                card.setParent(column.tasks_container)

            column.add_task(card)
            column.updateGeometry()
            if column.parent():
                column.parent().updateGeometry()

            print(f"  ✅ Добавлено в колонку '{column_name}'")
        else:
            print(f"  ❌ Колонка '{column_name}' не найдена!")
            card.deleteLater()

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи."""
        is_creator = (task_data.get('created_by') == self.current_user.get('id'))
        return OthersTaskCard(task_data, service=self.service, is_creator=is_creator)

    def connect_task_card_signals(self, card):
        """Подключает сигналы карточки."""
        card.editRequested.connect(self.edit_task)
        card.deleteRequested.connect(self.delete_task)
        card.archiveRequested.connect(self.archive_task)
        card.approveRequested.connect(self.approve_task)
        card.returnToWorkRequested.connect(self.return_to_work)
        card.moveToDoneColumn.connect(self.move_to_done)
        card.project_clicked.connect(self._on_project_clicked)

        card.duplicateRequested.connect(self.duplicate_task)
        card.pauseRequested.connect(self.pause_task)
        card.resumeRequested.connect(self.resume_task)

        card.drag_started.connect(self._on_drag_started)

    def _on_drag_started(self, task_data: dict):
        """Начало перетаскивания задачи"""
        print(f"🖱️ Начато перетаскивание задачи {task_data.get('id')} из чужих задач")

    def duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        print(f"📋 Дублирование задачи {task_id}")
        new_task = self.service.duplicate_task(task_id)
        if new_task:
            self.add_task_card(new_task)
            self.update_statistics()
            self.taskUpdated.emit()
            QMessageBox.information(self, "Успех", f"Задача '{new_task.get('title')}' дублирована")

    def pause_task(self, task_id: int):
        """Поставить задачу на паузу"""
        print(f"⏸️ Пауза задачи {task_id}")
        updated_task = self.service.pause_task(task_id)
        if updated_task:
            self._update_existing_task_card(task_id, updated_task)
            self.update_statistics()
            self.taskUpdated.emit()
            QMessageBox.information(self, "Пауза", f"Задача поставлена на паузу")

    def resume_task(self, task_id: int):
        """Возобновить задачу"""
        print(f"▶️ Возобновление задачи {task_id}")
        updated_task = self.service.resume_task(task_id)
        if updated_task:
            self._update_existing_task_card(task_id, updated_task)
            self.update_statistics()
            self.taskUpdated.emit()
            QMessageBox.information(self, "Возобновление", f"Задача возобновлена")

    def _update_existing_task_card(self, task_id: int, updated_task: Dict):
        """Обновляет существующую карточку без пересоздания"""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data.get("id") == task_id:
                    card.task_data.update(updated_task)
                    card._update_pause_indicator()
                    if card.task_data.get("is_paused") != updated_task.get("is_paused"):
                        card._update_pause_indicator()
                    return

    def _on_project_clicked(self, project_id: int):
        """Обработчик клика по названию проекта"""
        print(f"📁 Запрошено открытие проекта {project_id} из чужих задач")
        self.open_project_requested.emit(project_id)

    def clear_all_columns(self):
        """Очищает все колонки от карточек."""
        for column in self.column_widgets:
            column.clear_tasks()

    def refresh_columns(self):
        """Обновляет колонки (после добавления/удаления) с защитой от повторных вызовов"""
        if self._is_refreshing:
            print("⚠️ Обновление колонок уже выполняется, пропускаем")
            return

        self._is_refreshing = True

        try:
            print("🔄 ОБНОВЛЕНИЕ КОЛОНОК на странице Чужие задачи")

            # Сбрасываем кэш колонок
            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            # Пересоздаем доску с НОВЫМИ колонками
            self.setup_kanban()

            # Загружаем проекты заново
            self._load_projects_for_filter()

            # ОЧИЩАЕМ ВСЕ КОЛОНКИ перед добавлением задач
            self.clear_all_columns()

            # ПЕРЕЗАГРУЖАЕМ ЗАДАЧИ заново из сервиса
            tasks = self.service.load_tasks()

            print(f"   - Загружено задач из БД: {len(tasks)}")

            # Отключаем обновления UI для массового добавления
            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            for task in tasks:
                card = self.create_task_card(task)
                self.connect_task_card_signals(card)

                column_name = task.get("status")
                if column_name in self.columns:
                    column = self.columns[column_name]
                    if card.parent() != column.tasks_container:
                        card.setParent(column.tasks_container)
                    column.add_task(card)
                    print(f"   - Добавлена задача '{task.get('title')}' в колонку '{column_name}'")
                else:
                    print(f"   - ⚠️ Колонка '{column_name}' не найдена для задачи '{task.get('title')}'")
                    card.deleteLater()

            # Включаем обновления UI
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            self.update_statistics()

            # Обновляем геометрию
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

            print("✅ Обновление колонок на странице Чужие задачи завершено")

        except Exception as e:
            print(f"❌ Ошибка при обновлении колонок: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_refreshing = False

    def create_new_task(self):
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: Создание новой задачи ===")

        dialog = TaskDialog(self, mode="create", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_saved)

        dialog.exec()

    def edit_task(self, task_id: int):
        """Редактирует задачу."""
        task = self.service.get_task_by_id(task_id)
        if not task:
            return

        dialog = TaskDialog(self, task_data=task, mode="edit", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_updated)

        dialog.exec()

    def on_task_saved(self, task_id, form_data):
        """Обработчик создания задачи."""
        print("\n=== ОТЛАДКА: Создание задачи ===")
        print(f"Данные из диалога: {form_data}")

        try:
            new_task = self.service.create_task(form_data)
            print(f"✅ Задача создана: {new_task}")

            self.add_task_card(new_task)
            self.update_statistics()
            self.taskUpdated.emit()
            print("✅ Задача добавлена в UI")

        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {str(e)}")

    def on_task_updated(self, task_id, form_data):
        """Обработчик обновления задачи."""
        print("\n=== ОТЛАДКА: Обновление задачи ===")
        print(f"ID задачи: {task_id}")
        print(f"Данные из диалога: {form_data}")

        try:
            updated_task = self.service.update_task(task_id, form_data)
            if updated_task:
                print(f"✅ Задача обновлена: {updated_task}")
                print(f"   Новый статус: {updated_task.get('status')}")

                self.update_task_card(updated_task)
                self.update_statistics()
                self.taskUpdated.emit()
                print("✅ Задача обновлена в UI")
            else:
                print("❌ Задача не найдена")

        except Exception as e:
            print(f"❌ ОШИБКА при обновлении задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить задачу: {str(e)}")

    def delete_task(self, task_id: int):
        """Удаляет задачу."""
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.service.delete_task(task_id)
            self.remove_task_card(task_id)
            self.update_statistics()
            self.taskUpdated.emit()

    def update_task_card(self, updated_task: Dict):
        """Обновляет карточку задачи (перемещает если изменился статус)"""
        task_id = updated_task.get("id")
        new_status = updated_task.get("status")

        print(f"🔄 update_task_card: задача {task_id}, новый статус {new_status}")

        found_card = None
        found_column = None

        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data.get("id") == task_id:
                    found_card = card
                    found_column = column
                    break
            if found_card:
                break

        if not found_card:
            print(f"⚠️ Карточка {task_id} не найдена в UI, перезагружаем")
            self.load_tasks()
            return

        old_status = found_card.task_data.get("status")

        if old_status != new_status:
            print(f"   - Перемещаем из {old_status} в {new_status}")

            found_column.remove_task(found_card)
            found_card.deleteLater()

            new_column = self.columns.get(new_status)
            if new_column:
                new_card = self.create_task_card(updated_task)
                self.connect_task_card_signals(new_card)
                new_column.add_task(new_card)
                print(f"   ✅ Перемещено в колонку '{new_status}'")
            else:
                print(f"   - ⚠️ Колонка {new_status} не найдена, создаём карточку заново")
                found_card.update_task_data(updated_task)
                found_column.add_task(found_card)
        else:
            found_card.update_task_data(updated_task)

        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

        self.update_statistics()

        for column in self.column_widgets:
            column.update_count(len(column.get_tasks()))
            column.updateGeometry()

    def remove_task_card(self, task_id: int):
        """Удаляет карточку из UI."""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data["id"] == task_id:
                    column.remove_task(card)
                    return

    def move_to_done(self, task_id: int):
        """Перемещает задачу в колонку 'Готово' и устанавливает прогресс 100%"""
        print(f"✅ Перемещение задачи {task_id} в Готово")

        target_column_name = "Готово"
        target_column = None
        for col in self.column_widgets:
            if col.column_name == target_column_name:
                target_column = col
                break

        if not target_column:
            QMessageBox.warning(self, "Ошибка", f"Колонка '{target_column_name}' не найдена")
            return

        result = self.service.move_task_to_column(task_id, target_column.column_id)

        if result:
            old_column = None
            old_card = None

            for column in self.column_widgets:
                for card in column.get_tasks():
                    if card.task_data.get("id") == task_id:
                        old_column = column
                        old_card = card
                        break
                if old_card:
                    break

            if old_column and old_card:
                old_column.remove_task(old_card)

            new_card = self.create_task_card(result)
            self.connect_task_card_signals(new_card)

            target_column.add_task(new_card)
            target_column.update_count(len(target_column.get_tasks()))

            self.update_statistics()
            self.taskUpdated.emit()

            QMessageBox.information(self, "Успех", "Задача отмечена как выполненная")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось отметить задачу как выполненную")

    def archive_task(self, task_id: int):
        """Архивирование задачи"""
        print(f"📦 Архивирование задачи {task_id}")

        reply = QMessageBox.question(
            self, "Архивирование",
            "Вы уверены, что хотите архивировать задачу?\nОна будет перемещена в архив.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.service.archive_task_by_id(task_id):
                self.remove_task_card(task_id)
                self.update_statistics()
                self.taskUpdated.emit()
                QMessageBox.information(self, "Успех", "Задача архивирована")
                print(f"📦 Задача {task_id} архивирована и удалена из UI")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось архивировать задачу")

    def approve_task(self, task_id: int):
        print(f"Одобрение задачи {task_id}")

    def return_to_work(self, task_id: int):
        print(f"Возврат на доработку задачи {task_id}")

    def update_statistics(self):
        """Обновляет статистику (Всего, В работе, Просрочено, Прогресс)"""
        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        total = len(all_tasks)

        # Подсчёт "В работе" - задачи не в Done колонке
        in_progress = 0
        done_columns = ["Готово", "Done", "Выполнено"]
        for task in all_tasks:
            status = task.get("status", "")
            completed = task.get("completed", False)
            if status not in done_columns and not completed:
                in_progress += 1

        # Подсчёт просроченных задач
        from datetime import datetime
        overdue = 0
        today = datetime.now().date()
        for task in all_tasks:
            deadline_str = task.get("deadline")
            completed = task.get("completed", False)
            if deadline_str and not completed:
                try:
                    deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
                    if deadline_date < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        # ===== ИСПРАВЛЕНИЕ: расчёт среднего прогресса (сумма прогрессов / количество задач) =====
        if total > 0:
            total_progress = sum(task.get("progress_percent", 0) for task in all_tasks)
            avg_progress = int(total_progress / total)
        else:
            avg_progress = 0

        # Обновляем UI
        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {total}")

        if hasattr(self, 'inProgressLabel'):
            self.inProgressLabel.setText(f"🔧 В работе: {in_progress}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {overdue}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(avg_progress)
            self.overallProgress.setFormat(f"Общий прогресс: {avg_progress}%")

        # Обновляем счетчики в колонках
        for column in self.column_widgets:
            tasks_count = len(column.get_tasks())
            column.update_count(tasks_count)

    def filter_tasks(self):
        """Фильтрует задачи по приоритету и проекту"""
        priority = self.priorityFilter.currentText()
        project_id = self.projectFilter.currentData()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = all_tasks

        # Фильтр по приоритету
        if priority != "Все приоритеты":
            filtered = self.service.filter_tasks_by_priority(filtered, priority)

        # Фильтр по проекту
        if project_id:
            filtered = self.service.filter_tasks_by_project(filtered, project_id)

        filtered_ids = {t["id"] for t in filtered}

        # Применяем фильтр к карточкам
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_data["id"] in filtered_ids:
                    card.show()
                else:
                    card.hide()

    def get_target_column(self, pos: QPoint):
        for column in self.column_widgets:
            if column.geometry().contains(pos):
                return column
        return None

    def closeEvent(self, event):
        self.db_session.close()
        super().closeEvent(event)

    def move_task_card(self, task_id: int, from_column: str, to_column: str):
        """Перемещает карточку между колонками."""
        card = None
        source_column = None

        for col in self.column_widgets:
            layout = col.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data') and w.task_data["id"] == task_id:
                    card = w
                    source_column = col
                    layout.takeAt(i)
                    break
            if card:
                break

        target_column = None
        for col in self.column_widgets:
            if col.column_name == to_column:
                target_column = col
                break

        if card and target_column:
            target_column.tasks_layout.insertWidget(
                target_column.tasks_layout.count() - 1,
                card
            )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка входа drag в страницу"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Обработка движения drag над страницей"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Обработка сброса drag на страницу (запасной вариант)"""
        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-task"):
            event.ignore()
            return

        data = self.service.deserialize_task_from_drag(
            mime_data.data("application/x-task")
        )
        if not data:
            event.ignore()
            return

        task_id = data.get("id")
        if not task_id:
            event.ignore()
            return

        global_pos = self.mapToGlobal(event.position().toPoint())

        target_column = None
        for column in self.column_widgets:
            column_pos = column.mapFromGlobal(global_pos)
            if column.rect().contains(column_pos):
                target_column = column
                break

        if not target_column:
            print("⚠️ Не удалось определить целевую колонку")
            event.ignore()
            return

        new_status = target_column.column_name
        old_status = data.get("status")

        if old_status == new_status:
            event.ignore()
            return

        print(f"🔄 Перемещение задачи {task_id}: {old_status} -> {new_status}")

        result = self.service.move_task_to_column(task_id, target_column.column_id)

        if result:
            self.update_task_card(result)
            self.update_statistics()
            self.taskUpdated.emit()
            event.acceptProposedAction()
        else:
            print("❌ Сервис не смог переместить задачу")
            event.ignore()