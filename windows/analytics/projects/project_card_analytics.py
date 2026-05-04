# windows/analytics/projects/project_card_analytics.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy, QPushButton, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, \
    QHeaderView
from PyQt6.QtCore import Qt

from windows.analytics.projects.employee_project_card import EmployeeProjectCard
from windows.analytics.task_card_analytics import TaskCard


class ProjectCard(QFrame):
    def __init__(self, project_data, parent=None, analytics_service=None):
        super().__init__(parent)

        self.analytics_service = analytics_service
        self.data = project_data

        # Определяем путь к UI-файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "projects", "project_card_analytics.ui"
        )

        # Проверяем существование UI файла
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            self._remove_old_ui_panels()
        else:
            self._create_ui_programmatically()

        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # Основная информация
        self._setup_basic_info()

        # Создаем секции (все скрыты по умолчанию)
        self._setup_tasks_section()
        self._setup_employees_section()

    def _setup_basic_info(self):
        """Заполняет основную информацию о проекте"""
        if hasattr(self, 'name_btn'):
            self.name_btn.setText(self.data.get("name", "Без названия"))

        if hasattr(self, 'info_label'):
            start_date = self.data.get('created_at_str', self.data.get('created_at', '—'))
            status = self.data.get('status_display', 'Активный')
            emp_count = self.data.get('member_count', self.data.get('emp_count', 0))

            self.info_label.setText(
                f"Старт: {start_date} · "
                f"Статус: {status} · "
                f"Сотрудников: {emp_count}"
            )

    def _remove_old_ui_panels(self):
        """Удаляет старые панели из UI файла"""
        old_widgets = ['tasks_btn', 'employees_btn', 'tasks_panel', 'employees_panel']
        for widget_name in old_widgets:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if widget:
                    widget.deleteLater()
                    delattr(self, widget_name)

    def _setup_tasks_section(self):
        """Создает секцию с задачами - по умолчанию скрыта"""
        grouped_tasks = self.data.get("grouped_tasks", {})
        has_tasks = any(tasks for tasks in grouped_tasks.values())

        # Кнопка-заголовок
        btn = QPushButton(f"▶ Задачи", self)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px;
                text-align: left;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:checked {
                background-color: #E0E0E0;
            }
        """)

        # Панель задач
        panel = QFrame(self)
        panel.setVisible(False)
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        panel_layout = QVBoxLayout(panel)

        if not has_tasks:
            label = QLabel("📭 Нет задач в этом проекте")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px;")
            panel_layout.addWidget(label)
        else:
            # Создаем группы задач по статусам
            for status_key, tasks in grouped_tasks.items():
                if not tasks:
                    continue

                status_name = self.analytics_service.get_status_name(
                    status_key) if self.analytics_service else status_key
                status_btn = QPushButton(f"▶ {status_name} ({len(tasks)})")
                status_btn.setCheckable(True)
                status_btn.setChecked(False)
                status_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1B232A;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 10px;
                        font-size: 12px;
                        font-weight: bold;
                        text-align: left;
                        margin: 2px;
                    }
                    QPushButton:hover {
                        background-color: #D9D9D6;
                        color: black;
                    }
                """)
                panel_layout.addWidget(status_btn)

                tasks_panel = QFrame()
                tasks_panel.setVisible(False)
                tasks_panel.setStyleSheet("background-color: white; border-radius: 4px;")
                tasks_layout = QVBoxLayout(tasks_panel)
                tasks_layout.setContentsMargins(8, 8, 8, 8)
                tasks_layout.setSpacing(4)

                for task_dto in tasks:
                    try:
                        card = TaskCard(task_data=task_dto, compact=True, show_project=False)
                        tasks_layout.addWidget(card)
                    except Exception as e:
                        print(f"❌ Ошибка создания карточки задачи: {e}")

                panel_layout.addWidget(tasks_panel)

                # Подключаем сигнал для статусной кнопки
                status_btn.toggled.connect(
                    lambda checked, p=tasks_panel, b=status_btn: self._toggle_subpanel(checked, p, b)
                )

        # Добавляем в основной layout
        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        self.tasks_btn = btn
        self.tasks_panel = panel

        # Подключаем сигнал для основной кнопки
        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _setup_employees_section(self):
        """Создает секцию с сотрудниками - по умолчанию скрыта"""
        employees = self.data.get("employees", [])

        # Кнопка-заголовок
        btn = QPushButton(f"▶ Сотрудники ({len(employees)})", self)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px;
                text-align: left;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:checked {
                background-color: #E0E0E0;
            }
        """)

        # Панель сотрудников
        panel = QFrame(self)
        panel.setVisible(False)
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        panel_layout = QVBoxLayout(panel)

        if not employees:
            label = QLabel("👥 Нет сотрудников в этом проекте")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px;")
            panel_layout.addWidget(label)
        else:
            # Создаем таблицу сотрудников
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Сотрудник", "Активных задач", "Выполнено"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setRowCount(len(employees))
            table.setFixedHeight(min(len(employees) * 35 + 30, 200))

            for i, emp in enumerate(employees):
                name = emp.get("name", emp.get("employee_name", "Неизвестен"))
                active = emp.get("active_tasks", emp.get("active", 0))
                completed = emp.get("completed_tasks", emp.get("completed", 0))

                table.setItem(i, 0, QTableWidgetItem(name))
                table.setItem(i, 1, QTableWidgetItem(str(active)))
                table.setItem(i, 2, QTableWidgetItem(str(completed)))

            panel_layout.addWidget(table)

        # Добавляем в основной layout
        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        self.employees_btn = btn
        self.employees_panel = panel

        # Подключаем сигнал
        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _toggle_panel(self, checked, panel, button):
        """Переключает видимость панели и текст кнопки"""
        panel.setVisible(checked)
        current_text = button.text()
        if current_text.startswith("▼"):
            button.setText("▶" + current_text[1:])
        else:
            button.setText("▼" + current_text[1:])

    def _toggle_subpanel(self, checked, panel, button):
        """Переключает видимость подпанели (для статусов задач)"""
        panel.setVisible(checked)
        current_text = button.text()
        if current_text.startswith("▼"):
            button.setText("▶" + current_text[1:])
        else:
            button.setText("▼" + current_text[1:])

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("ProjectCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
                margin: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Название проекта
        self.name_btn = QPushButton()
        self.name_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                color: #1B232A;
                text-align: left;
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                color: #D22730;
            }
        """)
        layout.addWidget(self.name_btn)

        # Информационная строка
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)