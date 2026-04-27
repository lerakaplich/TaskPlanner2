# windows/analytics/employees/employee_card.py

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
import os

from windows.profile.projects_page import ProjectsPage


class EmployeeCard(QFrame):
    def __init__(self, emp_data, parent=None):
        super().__init__(parent)

        # Определяем путь к папке с UI-файлом
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..", "..",  # поднимаемся до корня проекта
            "ui", "analytics", "employees"  # спускаемся в нужную подпапку ui
        )

        # Проверяем существование UI файла
        full_ui_path = os.path.join(ui_path, "employee_card.ui")
        if os.path.exists(full_ui_path):
            uic.loadUi(full_ui_path, self)
        else:
            # Создаем UI программно, если файл не найден
            self._create_ui_programmatically()

        self.emp_data = emp_data

        print(f"📊 Сотрудник: {emp_data.get('name')}")
        print(f"   Активных проектов: {len(emp_data.get('active_projects', []))}")
        print(f"   Завершенных проектов: {len(emp_data.get('completed_projects', []))}")
        print(f"   Аналитика по темам: {len(emp_data.get('tag_analytics', []))}")

        # Детальный вывод активных проектов
        if emp_data.get('active_projects'):
            print(f"   Детали активных проектов:")
            for proj in emp_data.get('active_projects', []):
                print(
                    f"      - {proj.get('name')} (задач: {proj.get('tasks_total', 0)}, выполнено: {proj.get('tasks_done', 0)})")

        # Основные данные
        if hasattr(self, 'name_btn'):
            self.name_btn.setText(emp_data.get("name", "Без имени"))

        if hasattr(self, 'info_label'):
            self.info_label.setText(
                f"{emp_data.get('position', '—')} · "
                f"{emp_data.get('department', '—')} · "
                f"{emp_data.get('subdivision', '—')}"
            )

        # windows/analytics/employees/employee_card.py

        # В методе __init__, после создания ProjectsPage, нужно принудительно обновить данные:

        # Активные проекты
        if hasattr(self, 'projects_panel'):
            active_projects = emp_data.get("active_projects", [])
            self.active_projects_view = ProjectsPage(
                employee_id=emp_data.get("id"),
                parent=self.projects_panel,
                mode="active",
                compact=True,
                projects_data=active_projects
            )
            if self.projects_panel.layout():
                self.projects_panel.layout().addWidget(self.active_projects_view)
                # 🔧 ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ДАННЫЕ
                self.active_projects_view.refresh_data()

        # Выполненные проекты
        if hasattr(self, 'completed_projects_panel'):
            completed_projects = emp_data.get("completed_projects", [])
            self.completed_projects_view = ProjectsPage(
                employee_id=emp_data.get("id"),
                parent=self.completed_projects_panel,
                mode="completed",
                compact=True,
                projects_data=completed_projects
            )
            if self.completed_projects_panel.layout():
                self.completed_projects_panel.layout().addWidget(self.completed_projects_view)
                # 🔧 ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ДАННЫЕ
                self.completed_projects_view.refresh_data()

        # Аналитика по темам
        if hasattr(self, 'analytics_panel'):
            self._setup_analytics_table(emp_data.get("tag_analytics", []))

        # Подключение сигналов
        if hasattr(self, 'projects_btn'):
            self.projects_btn.toggled.connect(self.toggle_projects_panel)
        if hasattr(self, 'completed_projects_btn'):
            self.completed_projects_btn.toggled.connect(self.toggle_completed_projects_panel)
        if hasattr(self, 'analytics_btn'):
            self.analytics_btn.toggled.connect(self.toggle_analytics_panel)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("EmployeeCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }
        """)

        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QFrame
        from PyQt6.QtCore import Qt

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Имя
        self.name_btn = QPushButton()
        self.name_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #1B232A; text-align: left; border: none;")
        layout.addWidget(self.name_btn)

        # Информация
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)

        # Активные проекты
        self.projects_btn = QPushButton("▶ Активные проекты")
        self.projects_btn.setCheckable(True)
        self.projects_btn.setStyleSheet(
            "background-color: #F0F0F0; border-radius: 6px; padding: 8px; text-align: left;")
        layout.addWidget(self.projects_btn)

        self.projects_panel = QFrame()
        self.projects_panel.setVisible(False)
        self.projects_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        proj_layout = QVBoxLayout(self.projects_panel)
        proj_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.projects_panel)

        # Выполненные проекты
        self.completed_projects_btn = QPushButton("▶ Выполненные проекты")
        self.completed_projects_btn.setCheckable(True)
        self.completed_projects_btn.setStyleSheet(
            "background-color: #F0F0F0; border-radius: 6px; padding: 8px; text-align: left;")
        layout.addWidget(self.completed_projects_btn)

        self.completed_projects_panel = QFrame()
        self.completed_projects_panel.setVisible(False)
        self.completed_projects_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        comp_layout = QVBoxLayout(self.completed_projects_panel)
        comp_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.completed_projects_panel)

        # Аналитика
        self.analytics_btn = QPushButton("▶ Аналитика по темам")
        self.analytics_btn.setCheckable(True)
        self.analytics_btn.setStyleSheet(
            "background-color: #F0F0F0; border-radius: 6px; padding: 8px; text-align: left;")
        layout.addWidget(self.analytics_btn)

        self.analytics_panel = QFrame()
        self.analytics_panel.setVisible(False)
        self.analytics_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        anal_layout = QVBoxLayout(self.analytics_panel)
        anal_layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.analytics_panel)

    def _setup_analytics_table(self, data_list):
        """Метод для отрисовки таблицы аналитики."""
        if not hasattr(self, 'analytics_panel'):
            return

        # Очищаем панель
        layout = self.analytics_panel.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        if not data_list:
            from PyQt6.QtWidgets import QLabel
            label = QLabel("Нет данных по темам")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 10px;")
            if layout:
                layout.addWidget(label)
            return

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Тема (тег)", "КПД", "Выполнено задач"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setRowCount(len(data_list))

        for i, row_data in enumerate(data_list):
            table.setItem(i, 0, QTableWidgetItem(row_data.get("tag", "")))

            kpi_item = QTableWidgetItem()
            kpi_item.setData(Qt.ItemDataRole.DisplayRole, row_data.get("kpd", 0))
            table.setItem(i, 1, kpi_item)

            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.DisplayRole, row_data.get("count", 0))
            table.setItem(i, 2, count_item)

        if layout:
            layout.addWidget(table)

    def toggle_projects_panel(self, checked):
        if hasattr(self, 'projects_panel'):
            self.projects_panel.setVisible(checked)
        if hasattr(self, 'projects_btn'):
            self.projects_btn.setText(f"{'▼' if checked else '▶'} Активные проекты")

    def toggle_completed_projects_panel(self, checked):
        if hasattr(self, 'completed_projects_panel'):
            self.completed_projects_panel.setVisible(checked)
        if hasattr(self, 'completed_projects_btn'):
            self.completed_projects_btn.setText(f"{'▼' if checked else '▶'} Выполненные проекты")

    def toggle_analytics_panel(self, checked):
        if hasattr(self, 'analytics_panel'):
            self.analytics_panel.setVisible(checked)
        if hasattr(self, 'analytics_btn'):
            self.analytics_btn.setText(f"{'▼' if checked else '▶'} Аналитика по темам")