import os
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QSpacerItem,
    QSizePolicy, QMessageBox
)

from services.analytics_service import AnalyticsService


class ArchivePage(QWidget):
    """Страница архива (UI-слой, без бизнес-логики)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("archivePage")

        # =============================
        # Загрузка UI
        # =============================
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )
        uic.loadUi(os.path.join(ui_path, "archive_page.ui"), self)

        # =============================
        # Сервис
        # =============================
        self.analytics_service = AnalyticsService()
        self.analytics_service.load_test_data()

        # =============================
        # Состояние
        # =============================
        self.current_project_id = None
        self.project_cards = []
        self.task_cards = []

        # =============================
        # Сигналы
        # =============================
        self.back_button.clicked.connect(self.show_projects_list)

        if hasattr(self, "search_input"):
            self.search_input.textChanged.connect(self.on_search)

        # =============================
        # Инициализация
        # =============================
        self.show_projects_list()

    # ==========================================================
    # Отображение проектов
    # ==========================================================

    def show_projects_list(self):
        self.current_project_id = None
        self.section_title.setText("Архивированные проекты")
        self.back_button.hide()

        self.projects_widget.show()
        self.tasks_widget.hide()

        self.clear_projects()

        projects = self.analytics_service.get_archived_projects()

        if not projects:
            self.empty_label.show()
            self.projects_widget.hide()
            return

        self.empty_label.hide()
        self.projects_widget.show()

        from windows.archive.archived_project_card import ArchivedProjectCard

        columns = self.calculate_columns()

        for i, project in enumerate(projects):
            card = ArchivedProjectCard(project, self)

            card.clicked.connect(self.on_project_clicked)
            card.restore_requested.connect(self.on_restore_project)
            card.delete_permanently_requested.connect(self.on_delete_project_permanently)

            self.project_cards.append(card)

            row = i // columns
            col = i % columns
            self.projects_layout.addWidget(card, row, col)

        rows = (len(projects) + columns - 1) // columns
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.projects_layout.addItem(spacer, rows, 0, 1, columns)

    # ==========================================================
    # Отображение задач проекта
    # ==========================================================

    def show_project_tasks(self, project_id: int):
        self.current_project_id = project_id

        project = self.analytics_service.get_project_by_id(project_id)
        if project:
            self.section_title.setText(f"Задачи проекта: {project['name']}")

        self.back_button.show()
        self.projects_widget.hide()
        self.tasks_widget.show()

        self.clear_tasks()

        tasks = self.analytics_service.get_project_tasks(project_id)

        if not tasks:
            no_tasks_label = QLabel("📭 В этом проекте нет архивированных задач")
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tasks_label.setStyleSheet("""
                color: #999999;
                font-size: 18px;
                padding: 50px;
            """)
            self.tasks_layout.addWidget(
                no_tasks_label, 0, 0, 1, self.calculate_columns()
            )
            return

        from windows.archive.archived_task_card import ArchivedTaskCard

        columns = self.calculate_columns()

        for i, task in enumerate(tasks):
            card = ArchivedTaskCard(task, self)

            card.restore_requested.connect(self.on_restore_task)
            card.delete_permanently_requested.connect(self.on_delete_task_permanently)

            self.task_cards.append(card)

            row = i // columns
            col = i % columns
            self.tasks_layout.addWidget(card, row, col)

    # ==========================================================
    # Поиск
    # ==========================================================

    def on_search(self, text: str):
        text = text.strip()

        if not text:
            if self.current_project_id is None:
                self.show_projects_list()
            else:
                self.show_project_tasks(self.current_project_id)
            return

        if self.current_project_id is None:
            projects = self.analytics_service.search_projects(text)
            self.render_projects(projects)
        else:
            tasks = self.analytics_service.search_tasks(
                self.current_project_id, text
            )
            self.render_tasks(tasks)

    # ==========================================================
    # Рендеринг
    # ==========================================================

    def render_projects(self, projects):
        self.clear_projects()

        if not projects:
            self.empty_label.setText("🔍 Ничего не найдено")
            self.empty_label.show()
            self.projects_widget.hide()
            return

        from windows.archive.archived_project_card import ArchivedProjectCard

        columns = self.calculate_columns()

        for i, project in enumerate(projects):
            card = ArchivedProjectCard(project, self)
            card.clicked.connect(self.on_project_clicked)
            card.restore_requested.connect(self.on_restore_project)
            card.delete_permanently_requested.connect(self.on_delete_project_permanently)

            row = i // columns
            col = i % columns
            self.projects_layout.addWidget(card, row, col)

    def render_tasks(self, tasks):
        self.clear_tasks()

        if not tasks:
            no_tasks_label = QLabel("🔍 Ничего не найдено")
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_layout.addWidget(
                no_tasks_label, 0, 0, 1, self.calculate_columns()
            )
            return

        from windows.archive.archived_task_card import ArchivedTaskCard

        columns = self.calculate_columns()

        for i, task in enumerate(tasks):
            card = ArchivedTaskCard(task, self)
            card.restore_requested.connect(self.on_restore_task)
            card.delete_permanently_requested.connect(self.on_delete_task_permanently)

            row = i // columns
            col = i % columns
            self.tasks_layout.addWidget(card, row, col)

    # ==========================================================
    # Действия
    # ==========================================================

    def on_project_clicked(self, project_id: int):
        self.show_project_tasks(project_id)

    def on_restore_project(self, project_id: int):
        project_name = self.analytics_service.get_project_display_name(project_id)
        if not project_name:
            return

        reply = QMessageBox.question(
            self,
            "Восстановление проекта",
            f"Восстановить проект '{project_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.analytics_service.restore_project(project_id)
            self.show_projects_list()
            QMessageBox.information(self, "Успех", "Проект восстановлен")

    def on_restore_task(self, task_id: int):
        task_name = self.analytics_service.get_task_display_name(task_id)
        if not task_name:
            return

        reply = QMessageBox.question(
            self,
            "Восстановление задачи",
            f"Восстановить задачу '{task_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.analytics_service.restore_task(task_id)
            self.show_project_tasks(self.current_project_id)
            QMessageBox.information(self, "Успех", "Задача восстановлена")

    def on_delete_project_permanently(self, project_id: int):
        reply = QMessageBox.warning(
            self,
            "Удаление проекта",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.analytics_service.delete_project_permanently(project_id)
            self.show_projects_list()
            QMessageBox.information(self, "Удалено", "Проект удалён")

    def on_delete_task_permanently(self, task_id: int):
        reply = QMessageBox.warning(
            self,
            "Удаление задачи",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.analytics_service.delete_task_permanently(task_id)
            self.show_project_tasks(self.current_project_id)
            QMessageBox.information(self, "Удалено", "Задача удалена")

    # ==========================================================
    # Вспомогательные
    # ==========================================================

    def clear_projects(self):
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.project_cards.clear()

    def clear_tasks(self):
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.task_cards.clear()

    def calculate_columns(self):
        width = self.width()
        if width > 1400:
            return 4
        elif width > 1100:
            return 3
        elif width > 800:
            return 2
        return 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_project_id is None:
            self.show_projects_list()
        else:
            self.show_project_tasks(self.current_project_id)