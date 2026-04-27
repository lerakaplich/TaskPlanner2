# windows/analytics/projects/project_card_analytics.py

import os
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QSizePolicy, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from windows.analytics.projects.employee_project_card import EmployeeProjectCard
from windows.analytics.task_card_analytics import TaskCard


class ProjectCard(QFrame):
    def __init__(self, project_data, parent=None):
        super().__init__(parent)

        # Определяем путь к UI-файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "projects", "project_card_analytics.ui"
        )

        # Проверяем существование UI файла
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            # Создаем UI программно, если файл не найден
            self._create_ui_programmatically()

        self.data = project_data
        self.is_tasks_visible = True  # По умолчанию задачи показаны
        self.is_employees_visible = False  # По умолчанию сотрудники скрыты

        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Основная информация
        if hasattr(self, 'name_btn'):
            self.name_btn.setText(self.data.get("name", "Без названия"))

        if hasattr(self, 'info_label'):
            start_date = self.data.get('created_at_str', self.data.get('created_at', '—'))
            status = self.data.get('status_display',
                                   'Активный' if not self.data.get('is_archived', False) else 'Архивный')
            emp_count = self.data.get('member_count', self.data.get('emp_count', 0))

            self.info_label.setText(
                f"Старт: {start_date} · "
                f"Статус: {status} · "
                f"Сотрудников: {emp_count}"
            )

        # 🔧 СНАЧАЛА ЗАПОЛНЯЕМ ЗАДАЧИ И СОТРУДНИКОВ
        if hasattr(self, 'tasks_panel'):
            self._populate_tasks()

        if hasattr(self, 'employees_panel'):
            self._populate_employees()

        # 🔧 ПОТОМ ПОДКЛЮЧАЕМ СИГНАЛЫ
        if hasattr(self, 'tasks_btn'):
            self.tasks_btn.toggled.connect(self._toggle_tasks_panel)

        if hasattr(self, 'employees_btn'):
            self.employees_btn.toggled.connect(self._toggle_employees_panel)

        # 🔧 ПРИНУДИТЕЛЬНО УСТАНАВЛИВАЕМ ВИДИМОСТЬ
        # Задачи показываем, сотрудников скрываем
        if hasattr(self, 'tasks_btn') and hasattr(self, 'tasks_panel'):
            self.tasks_btn.blockSignals(True)
            self.tasks_btn.setChecked(True)
            self.tasks_btn.setText("▼ Задачи")
            self.tasks_panel.setVisible(True)
            self.tasks_btn.blockSignals(False)

        if hasattr(self, 'employees_btn') and hasattr(self, 'employees_panel'):
            self.employees_btn.blockSignals(True)
            self.employees_btn.setChecked(False)
            self.employees_btn.setText("▶ Сотрудники")
            self.employees_panel.setVisible(False)
            self.employees_btn.blockSignals(False)

        # Принудительно обновляем геометрию
        self.updateGeometry()

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("ProjectCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
                margin: 2px;
            }
        """)

        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QFrame

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

        # Кнопка задач
        self.tasks_btn = QPushButton("▼ Задачи")
        self.tasks_btn.setCheckable(True)
        self.tasks_btn.setChecked(True)
        self.tasks_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        layout.addWidget(self.tasks_btn)

        # Панель задач
        self.tasks_panel = QFrame()
        self.tasks_panel.setVisible(True)
        self.tasks_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        tasks_layout = QVBoxLayout(self.tasks_panel)
        tasks_layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.tasks_panel)

        # Кнопка сотрудников
        self.employees_btn = QPushButton("▶ Сотрудники")
        self.employees_btn.setCheckable(True)
        self.employees_btn.setChecked(False)
        self.employees_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        layout.addWidget(self.employees_btn)

        # Панель сотрудников
        self.employees_panel = QFrame()
        self.employees_panel.setVisible(False)
        self.employees_panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        employees_layout = QVBoxLayout(self.employees_panel)
        employees_layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.employees_panel)

    def _toggle_tasks_panel(self, checked):
        """Переключение видимости панели задач"""
        if hasattr(self, 'tasks_panel'):
            self.tasks_panel.setVisible(checked)
            self.tasks_panel.updateGeometry()

        if hasattr(self, 'tasks_btn'):
            self.tasks_btn.setText(f"{'▼' if checked else '▶'} Задачи")

        # Принудительно обновляем геометрию всей карточки
        self.updateGeometry()

        # Обновляем родительские виджеты
        if self.parent():
            self.parent().updateGeometry()

    def _toggle_employees_panel(self, checked):
        """Переключение видимости панели сотрудников"""
        if hasattr(self, 'employees_panel'):
            self.employees_panel.setVisible(checked)
            self.employees_panel.updateGeometry()

        if hasattr(self, 'employees_btn'):
            self.employees_btn.setText(f"{'▼' if checked else '▶'} Сотрудники")

        # Принудительно обновляем геометрию всей карточки
        self.updateGeometry()

        # Обновляем родительские виджеты
        if self.parent():
            self.parent().updateGeometry()

    def _populate_tasks(self):
        """Заполняет панель задач с группировкой по статусам."""
        if not hasattr(self, 'tasks_panel'):
            return

        layout = self.tasks_panel.layout()
        if not layout:
            layout = QVBoxLayout(self.tasks_panel)
            self.tasks_panel.setLayout(layout)

        self._clear_layout(layout)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        grouped_tasks = self.data.get("grouped_tasks", {})
        display_names = TaskCard.STATUS_MAP

        has_tasks = False
        for status_key, tasks in grouped_tasks.items():
            if not tasks:
                continue

            has_tasks = True

            status_container = QFrame()
            container_layout = QVBoxLayout(status_container)
            container_layout.setSpacing(4)
            container_layout.setContentsMargins(0, 0, 0, 0)

            status_btn = QPushButton(f"▶ {display_names.get(status_key, status_key)} ({len(tasks)})")
            status_btn.setCheckable(True)
            status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1B232A;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #D9D9D6;
                    color: black;
                }
            """)
            container_layout.addWidget(status_btn)

            tasks_panel = QFrame()
            tasks_panel.setVisible(False)
            tasks_panel.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 4px;
                    margin-top: 2px;
                }
            """)
            tasks_layout = QVBoxLayout(tasks_panel)
            tasks_layout.setContentsMargins(8, 8, 8, 8)
            tasks_layout.setSpacing(6)

            for task_dto in tasks:
                try:
                    card = TaskCard(task_data=task_dto, compact=True, show_project=False)
                    tasks_layout.addWidget(card)
                except Exception as e:
                    print(f"❌ Ошибка создания карточки задачи: {e}")

            container_layout.addWidget(tasks_panel)
            layout.addWidget(status_container)

            # Связываем кнопку с панелью
            status_btn.toggled.connect(
                lambda checked, p=tasks_panel, b=status_btn: self._update_status_btn(checked, p, b)
            )

            # 🔧 РАСКРЫВАЕМ ПАНЕЛЬ ДЛЯ ПЕРВОГО СТАТУСА (to_do)
            if status_key == "to_do":
                status_btn.setChecked(True)
                tasks_panel.setVisible(True)
                # Обновляем текст кнопки
                status_btn.setText(f"▼ {display_names.get(status_key, status_key)} ({len(tasks)})")

        if not has_tasks:
            no_tasks_label = QLabel("📭 Нет задач в этом проекте")
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tasks_label.setStyleSheet("color: #999; padding: 20px;")
            layout.addWidget(no_tasks_label)

        layout.addStretch()
        self.tasks_panel.updateGeometry()

    def _update_status_btn(self, checked, panel, button):
        """Обновление состояния кнопки статуса"""
        panel.setVisible(checked)
        current_text = button.text()
        # Извлекаем текст после стрелки
        if len(current_text) > 1:
            content = current_text[1:]
        else:
            content = ""
        arrow = "▼" if checked else "▶"
        button.setText(arrow + content)
        panel.updateGeometry()
        # Обновляем родительскую карточку
        self.updateGeometry()

    def _populate_employees(self):
        """Заполняет панель сотрудников."""
        if not hasattr(self, 'employees_panel'):
            return

        layout = self.employees_panel.layout()
        if not layout:
            layout = QVBoxLayout(self.employees_panel)
            self.employees_panel.setLayout(layout)

        self._clear_layout(layout)

        employees = self.data.get("employees", [])

        if not employees:
            no_emp_label = QLabel("👥 Нет сотрудников в этом проекте")
            no_emp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_emp_label.setStyleSheet("color: #999; padding: 20px;")
            layout.addWidget(no_emp_label)
        else:
            for emp in employees:
                try:
                    card = EmployeeProjectCard(emp, self.data.get("id", ""))
                    layout.addWidget(card)
                except Exception as e:
                    print(f"❌ Ошибка создания карточки сотрудника: {e}")

        layout.addStretch()
        self.employees_panel.updateGeometry()

    def _clear_layout(self, layout):
        """Очищает layout рекурсивно"""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())