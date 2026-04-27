# windows/analytics/employees/employee_card.py

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout, QLabel, \
    QPushButton
import os


class EmployeeCard(QFrame):
    def __init__(self, emp_data, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "analytics", "employees"
        )

        full_ui_path = os.path.join(ui_path, "employee_card.ui")
        if os.path.exists(full_ui_path):
            uic.loadUi(full_ui_path, self)
            # Удаляем старые панели из UI, если они есть
            self._remove_old_ui_panels()
        else:
            self._create_ui_programmatically()

        self.emp_data = emp_data

        # Основные данные
        if hasattr(self, 'name_btn'):
            self.name_btn.setText(emp_data.get("name", "Без имени"))

        if hasattr(self, 'info_label'):
            self.info_label.setText(
                f"{emp_data.get('position', '—')} · "
                f"{emp_data.get('department', '—')} · "
                f"{emp_data.get('subdivision', '—')}"
            )

        # Создаем новые таблицы
        active_projects = emp_data.get("active_projects", [])
        completed_projects = emp_data.get("completed_projects", [])
        tag_analytics = emp_data.get("tag_analytics", [])

        # Создаем панели и таблицы (все скрыты по умолчанию)
        self._setup_projects_section("Активные проекты", active_projects, 1)
        self._setup_projects_section("Выполненные проекты", completed_projects, 2)
        self._setup_analytics_section(tag_analytics)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(200)

    def _remove_old_ui_panels(self):
        """Удаляет старые панели из UI файла, чтобы не дублировались"""
        old_widgets = ['projects_btn', 'completed_projects_btn', 'analytics_btn',
                       'projects_panel', 'completed_projects_panel', 'analytics_panel']

        for widget_name in old_widgets:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if widget:
                    widget.deleteLater()
                    delattr(self, widget_name)

    def _setup_projects_section(self, title, projects, section_num):
        """Создает секцию с проектами - по умолчанию скрыта"""
        # Создаем кнопку-заголовок (всегда со стрелкой "▶" - скрыто)
        btn = QPushButton(f"▶ {title}", self)
        btn.setCheckable(True)
        btn.setChecked(False)  # 👈 ВСЕГДА СКРЫТО ПО УМОЛЧАНИЮ
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

        # Создаем панель - скрыта по умолчанию
        panel = QFrame(self)
        panel.setVisible(False)  # 👈 ВСЕГДА СКРЫТО ПО УМОЛЧАНИЮ
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        # Layout для панели
        panel_layout = QVBoxLayout(panel)

        if not projects:
            label = QLabel(f"Нет {title.lower()}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px;")
            panel_layout.addWidget(label)
        else:
            # Создаем таблицу с фиксированной высотой
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Название проекта", "Всего задач", "Выполнено"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setRowCount(len(projects))
            table.setFixedHeight(min(len(projects) * 35 + 30, 250))

            for i, proj in enumerate(projects):
                table.setItem(i, 0, QTableWidgetItem(proj.get("name", "Без названия")))
                table.setItem(i, 1, QTableWidgetItem(str(proj.get("tasks_total", 0))))
                table.setItem(i, 2, QTableWidgetItem(str(proj.get("tasks_done", 0))))

            panel_layout.addWidget(table)

        # Добавляем в основной layout
        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        # Сохраняем ссылки
        setattr(self, f"projects_btn_{section_num}", btn)
        setattr(self, f"projects_panel_{section_num}", panel)

        # Подключаем сигнал
        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _setup_analytics_section(self, analytics_data):
        """Создает секцию с аналитикой по темам - по умолчанию скрыта"""
        btn = QPushButton("▶ Аналитика по темам", self)
        btn.setCheckable(True)
        btn.setChecked(False)  # 👈 ВСЕГДА СКРЫТО ПО УМОЛЧАНИЮ
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

        panel = QFrame(self)
        panel.setVisible(False)  # 👈 ВСЕГДА СКРЫТО ПО УМОЛЧАНИЮ
        panel.setStyleSheet("background-color: #FAFAFA; border-radius: 6px;")
        panel.setMinimumHeight(100)

        panel_layout = QVBoxLayout(panel)

        if not analytics_data:
            label = QLabel("Нет данных по темам")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px;")
            panel_layout.addWidget(label)
        else:
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Тема (тег)", "КПД", "Выполнено задач"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setRowCount(len(analytics_data))
            table.setFixedHeight(min(len(analytics_data) * 35 + 30, 200))

            for i, row_data in enumerate(analytics_data):
                table.setItem(i, 0, QTableWidgetItem(row_data.get("tag", "")))
                kpd = row_data.get("kpd", 0)
                if isinstance(kpd, float):
                    kpd_text = f"{int(kpd * 100)}%"
                else:
                    kpd_text = str(kpd)
                table.setItem(i, 1, QTableWidgetItem(kpd_text))
                table.setItem(i, 2, QTableWidgetItem(str(row_data.get("count", 0))))

            panel_layout.addWidget(table)

        layout = self.layout()
        if layout:
            layout.addWidget(btn)
            layout.addWidget(panel)

        self.analytics_btn = btn
        self.analytics_panel = panel
        btn.toggled.connect(lambda checked, p=panel, b=btn: self._toggle_panel(checked, p, b))

    def _toggle_panel(self, checked, panel, button):
        """Переключает видимость панели и текст кнопки"""
        panel.setVisible(checked)
        current_text = button.text()
        if current_text.startswith("▼"):
            button.setText("▶" + current_text[1:])
        else:
            button.setText("▼" + current_text[1:])

    def _create_ui_programmatically(self):
        """Создает UI программно, если файл не найден"""
        self.setObjectName("EmployeeCard")
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
                margin: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.name_btn = QPushButton()
        self.name_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #1B232A; text-align: left; border: none; background-color: transparent;")
        layout.addWidget(self.name_btn)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)