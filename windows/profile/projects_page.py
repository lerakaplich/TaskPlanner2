# windows/profile/projects_page.py

import os
from typing import List, Dict, Any

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QLabel, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal

from windows.analytics.task_card_analytics import TaskCard


class ProjectsPage(QWidget):
    """Страница проектов (только UI)"""

    back_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, mode="completed", compact=False,
                 projects_data=None, profile_service=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.mode = mode
        self.compact = compact
        self.projects_data = projects_data
        self.profile_service = profile_service

        if not self.compact:
            self.setMinimumSize(800, 4000)
            self.resize(900, 700)

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        """Настраивает UI"""
        if not self.compact:
            ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
            ui_file = os.path.join(ui_path, "projects_page.ui")
            if os.path.exists(ui_file):
                uic.loadUi(ui_file, self)
                self.projects_layout = self.findChild(QVBoxLayout, "projectsLayout")
                if hasattr(self, 'btnClose'):
                    self.btnClose.clicked.connect(self.close)
            else:
                self.setLayout(QVBoxLayout())
                self.projects_layout = self.layout()
        else:
            self.setLayout(QVBoxLayout())
            self.projects_layout = self.layout()
            self.projects_layout.setContentsMargins(10, 10, 10, 10)
            self.projects_layout.setSpacing(10)

    def set_employee_id(self, employee_id):
        self.employee_id = employee_id
        self.projects_data = None

    def update_data(self, projects_data=None, employee_id=None):
        """Обновляет данные и перерисовывает UI"""
        if projects_data is not None:
            self.projects_data = projects_data
        if employee_id is not None:
            self.employee_id = employee_id
        self.refresh_data()

    def refresh_data(self):
        """Обновляет отображение проектов через сервис"""
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projects = self._load_projects()

        if not projects:
            empty_texts = {"active": "Нет активных проектов",
                           "completed": "Нет выполненных проектов",
                           "all": "Нет проектов"}
            label = QLabel(empty_texts.get(self.mode, "Нет проектов"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 18px; color: #666666; margin: 50px; border: none;")
            self.projects_layout.addWidget(label)
        else:
            for project in projects:
                self._add_project_section(project)

        self.projects_layout.addStretch()

    def _load_projects(self) -> List[Dict]:
        """Загружает проекты через сервис"""
        if self.projects_data is not None:
            projects = self.projects_data
        elif self.profile_service and self.employee_id:
            all_projects = self.profile_service.get_employee_projects(self.employee_id)
            projects = self._filter_projects_by_mode(all_projects)
        else:
            projects = []

        return projects

    def _filter_projects_by_mode(self, projects: List[Dict]) -> List[Dict]:
        """Фильтрует проекты по режиму"""
        filtered = []
        for project in projects:
            is_archived = project.get("is_archived", False)
            if self.mode == "active" and not is_archived:
                filtered.append(project)
            elif self.mode == "completed" and is_archived:
                filtered.append(project)
            elif self.mode == "all":
                filtered.append(project)
        return filtered

    def _load_project_tasks(self, project_id: int) -> List[Dict]:
        """
        Загружает задачи проекта через сервис профиля.
        Возвращает список задач в формате, понятном TaskCard.
        """
        try:
            if self.profile_service and hasattr(self.profile_service, 'get_project_tasks'):
                tasks = self.profile_service.get_project_tasks(project_id, self.employee_id)
                if tasks:
                    return tasks
            return []
        except Exception as e:
            print(f"❌ Ошибка загрузки задач для проекта {project_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _add_project_section(self, project: Dict):
        """Добавляет секцию проекта с задачами, используя TaskCard"""
        project_id = project.get("id")
        project_name = project.get("name", "Без названия")
        total_tasks = project.get("total_tasks", 0)
        completed_tasks = project.get("completed_tasks", 0)

        # Загружаем задачи проекта
        tasks = self._load_project_tasks(project_id)

        header_style = f"""
            QPushButton {{ background-color: #D22730; color: white; border-radius: {10 if not self.compact else 6}px;
                          font-weight: bold; font-size: {18 if not self.compact else 14}px;
                          border: none; text-align: left; padding: {15 if not self.compact else 8}px 15px; }}
            QPushButton:hover {{ background-color: #862633; }}
        """

        header_btn = QPushButton(f"{project_name} ({completed_tasks}/{total_tasks}) ►")
        header_btn.setCheckable(True)
        header_btn.setStyleSheet(header_style)

        project_panel = QFrame()
        project_panel.setVisible(False)
        project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
        panel_layout = QVBoxLayout(project_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)

        if tasks:
            if len(tasks) > 5:
                tasks_scroll = QScrollArea()
                tasks_scroll.setWidgetResizable(True)
                tasks_scroll.setMaximumHeight(400)
                tasks_scroll.setStyleSheet("border: none; background-color: transparent;")

                tasks_container = QWidget()
                tasks_container.setStyleSheet("background-color: transparent;")
                tasks_container_layout = QVBoxLayout(tasks_container)
                tasks_container_layout.setContentsMargins(0, 0, 0, 0)
                tasks_container_layout.setSpacing(8)

                for task in tasks:
                    try:
                        # Преобразуем задачу в формат для TaskCard
                        task_data = self._format_task_for_card(task)
                        task_card = TaskCard(
                            task_data=task_data,
                            compact=True,
                            show_theme=True,
                            show_project=False
                        )
                        tasks_container_layout.addWidget(task_card)
                    except Exception as e:
                        print(f"❌ Ошибка создания карточки задачи: {e}")

                tasks_scroll.setWidget(tasks_container)
                panel_layout.addWidget(tasks_scroll)
            else:
                for task in tasks:
                    try:
                        task_data = self._format_task_for_card(task)
                        task_card = TaskCard(
                            task_data=task_data,
                            compact=True,
                            show_theme=True,
                            show_project=False
                        )
                        panel_layout.addWidget(task_card)
                    except Exception as e:
                        print(f"❌ Ошибка создания карточки задачи: {e}")
        else:
            no_tasks_label = QLabel("📭 Нет задач в этом проекте")
            no_tasks_label.setStyleSheet("color: #999; font-size: 12px; padding: 10px;")
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            panel_layout.addWidget(no_tasks_label)

        self.projects_layout.addWidget(header_btn)
        self.projects_layout.addWidget(project_panel)

        def toggle_panel(checked):
            project_panel.setVisible(checked)
            arrow = " ▼" if checked else " ►"
            header_btn.setText(f"{project_name} ({completed_tasks}/{total_tasks}){arrow}")

        header_btn.toggled.connect(toggle_panel)

    def _format_task_for_card(self, task: Dict) -> Dict:
        """
        Форматирует задачу для отображения в TaskCard.
        Приводит к единому формату, который ожидает TaskCard.
        """
        # Определяем статус
        status = task.get("status", "").lower()
        if not status:
            if task.get("is_archived", False):
                status = "archived"
            elif task.get("completed", False) or task.get("is_done", False):
                status = "completed"
            else:
                status = "in_progress"

        # Определяем просрочена ли задача
        is_overdue = False
        deadline = task.get("deadline")
        if deadline and not task.get("is_done", False):
            try:
                from datetime import datetime
                if isinstance(deadline, str):
                    deadline = datetime.strptime(deadline, "%Y-%m-%d")
                if deadline and datetime.now() > deadline:
                    is_overdue = True
            except:
                pass

        # Получаем приоритет
        priority = task.get("priority", "medium")
        if isinstance(priority, str):
            priority = priority.lower()

        # Формируем словарь для TaskCard
        return {
            "id": task.get("id"),
            "title": task.get("title", "Без названия"),
            "description": task.get("description", ""),
            "status": status,
            "priority": priority,
            "deadline": task.get("deadline"),
            "created_at": task.get("created_at"),
            "created_at_str": self._format_date(task.get("created_at")),
            "completed_at": task.get("completed_at"),
            "completed_at_str": self._format_date(task.get("completed_at")),
            "due_date_str": self._format_date(task.get("deadline")),
            "is_overdue": is_overdue,
            "tags_list": task.get("tags", []),
            "project_name": task.get("project_name", ""),
            "creator_name": task.get("creator_name", ""),
            "kpi_value": task.get("kpd_score"),
            "kpd_score": task.get("kpd_score"),
            "themes": task.get("themes", []),
            "employee_id": task.get("assigned_to"),
            "assignee_name": task.get("assignee_name", ""),
            "is_done": task.get("is_done", False)
        }

    def _format_date(self, date_value) -> str:
        """Форматирует дату для отображения"""
        if not date_value:
            return "—"
        try:
            from datetime import datetime
            if isinstance(date_value, str):
                # Пробуем разные форматы
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y"]:
                    try:
                        dt = datetime.strptime(date_value, fmt)
                        return dt.strftime("%d.%m.%Y")
                    except:
                        continue
                return date_value[:10] if len(date_value) > 10 else date_value
            elif hasattr(date_value, 'strftime'):
                return date_value.strftime("%d.%m.%Y")
            else:
                return str(date_value)
        except:
            return "—"