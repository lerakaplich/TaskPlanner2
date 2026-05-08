# windows/profile/profile_page.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidgetItem,
                             QMessageBox, QFrame, QLabel, QProgressBar, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QDate

from services.analytics_service.analytics_service import AnalyticsService
from services.profile_service import ProfileService
from windows.profile.chart_widget import ChartWidget
from windows.profile.edit_profile import EditProfileDialog
from windows.profile.projects_page import ProjectsPage


class ProfilePage(QWidget):
    """Страница профиля сотрудника (только UI)"""

    edit_profile_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, current_user=None, service=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.main_window = parent
        self.current_user = current_user
        self.projects_page = None

        if not self.employee_id and current_user:
            self.employee_id = current_user.get('id')

        from database import get_tasks_session
        session = get_tasks_session()
        self.profile_service = service or ProfileService(session=session)

        if current_user:
            self.profile_service.set_current_user_id(current_user.get('id'))

        self.employee_data = {}

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
        uic.loadUi(os.path.join(ui_path, "profile_page.ui"), self)

        self._init_chart_widget()
        self._connect_signals()

        if self.employee_id:
            self.load_employee()

    def load_employee(self):
        """Загружает данные через сервис и обновляет UI"""
        if not self.profile_service:
            return

        # Загружаем основные данные
        self.employee_data = self.profile_service.get_employee_profile(self.employee_id)

        # Загружаем статистику и проекты
        stats = self.profile_service.get_employee_statistics(self.employee_id)
        projects = self.profile_service.get_employee_projects(self.employee_id)

        # Обогащаем данные
        self.employee_data.update(stats)
        self.employee_data["active_projects"] = projects

        analytics = AnalyticsService(self.profile_service.session)
        emp_analytics = analytics.get_employee_card_data(self.employee_id)
        self.employee_data["tag_analytics"] = emp_analytics.get("tag_analytics", [])

        # Обновляем UI
        self._update_ui()

    def _update_ui(self):
        """Обновляет UI из self.employee_data"""
        data = self.employee_data

        # ФИО
        if hasattr(self, 'labelFullName'):
            middle = f" {data.get('middle_name', '')}" if data.get('middle_name') else ""
            self.labelFullName.setText(f"{data.get('last_name', '')} {data.get('first_name', '')}{middle}")

        # Должность и отдел
        if hasattr(self, 'labelPosition'):
            self.labelPosition.setText(data.get('position', ''))
        if hasattr(self, 'labelDepartment'):
            self.labelDepartment.setText(data.get('department_name', '—'))

        # Контакты
        if hasattr(self, 'labelPhone'):
            self.labelPhone.setText(data.get('phone_number', ''))
        if hasattr(self, 'labelEmail'):
            self.labelEmail.setText(data.get('email', ''))

        # Дата рождения
        if hasattr(self, 'labelBirthDate'):
            birth = data.get('birth_date')
            if birth:
                try:
                    date = QDate.fromString(birth, "yyyy-MM-dd")
                    if date.isValid():
                        self.labelBirthDate.setText(date.toString("dd.MM.yyyy"))
                except:
                    pass

        # Статистика
        if hasattr(self, 'labelCompletedTasks'):
            self.labelCompletedTasks.setText(str(data.get('completed_tasks', 0)))
        if hasattr(self, 'labelActiveProjects'):
            self.labelActiveProjects.setText(str(data.get('projects_count', 0)))

        # Рейтинг
        rating = self.profile_service.calculate_rating(self.employee_data)
        if hasattr(self, 'labelKPD'):
            self.labelKPD.setText(f"КПД: {rating:.1f}%")
        self._update_rating_stars(rating)

        # Таблица навыков
        self._setup_skills_table()

        # Проекты
        self._create_projects_widgets()

        # График
        if hasattr(self, 'chart_widget'):
            self.chart_widget.load_data(self.employee_id)

    def _update_rating_stars(self, rating: float):
        """Обновляет звёзды рейтинга"""
        stars = self.profile_service.calculate_rating_stars(rating)
        for i in range(1, 6):
            star_attr = f"star{i}"
            if hasattr(self, star_attr):
                star = getattr(self, star_attr)
                if i <= stars:
                    star.setStyleSheet("font-size: 24px; color: #FFD700;")
                else:
                    star.setStyleSheet("font-size: 24px; color: #E0E0E0;")

    def _setup_skills_table(self):
        """Заполняет таблицу навыков"""
        skills = self.employee_data.get('tag_analytics', [])
        table = getattr(self, 'tableSkills', None)
        if not table:
            return

        table.setRowCount(len(skills))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Тема", "КПД", "Задач"])

        for row, skill in enumerate(skills):
            table.setItem(row, 0, QTableWidgetItem(skill.get("tag", "")))
            table.setItem(row, 1, QTableWidgetItem(f"{skill.get('kpd', 0):.2f}"))
            table.setItem(row, 2, QTableWidgetItem(str(skill.get("count", 0))))

        table.horizontalHeader().setStretchLastSection(True)

    def _create_projects_widgets(self):
        """Создаёт виджеты проектов"""
        projects = self.employee_data.get("active_projects", [])
        container = getattr(self, 'projectsContainer', None)
        if not container:
            return

        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            container.setLayout(layout)

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not projects:
            label = QLabel("Нет активных проектов")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px;")
            layout.addWidget(label)
            return

        for project in projects:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame { background-color: white; border-radius: 8px; border: 1px solid #E0E0E0;
                         padding: 10px; margin: 5px; }
            """)
            v = QVBoxLayout(frame)
            v.setSpacing(8)

            name = QLabel(project.get("name", "Без названия"))
            name.setStyleSheet("font-weight: bold; font-size: 14px;")

            progress = project.get("progress", 0)
            percent = QLabel(f"{progress}%")
            percent.setStyleSheet("color: #ccab6e; font-weight: bold;")

            h = QHBoxLayout()
            h.addWidget(name)
            h.addStretch()
            h.addWidget(percent)
            v.addLayout(h)

            bar = QProgressBar()
            bar.setValue(progress)
            bar.setStyleSheet("""
                QProgressBar { border: 1px solid #E0E0E0; border-radius: 4px; height: 10px; }
                QProgressBar::chunk { background-color: #D22730; border-radius: 4px; }
            """)
            v.addWidget(bar)

            tasks_label = QLabel(f"Задачи {project.get('completed_tasks', 0)}/{project.get('total_tasks', 0)}")
            tasks_label.setStyleSheet("color: #666; font-size: 12px;")
            v.addWidget(tasks_label)

            layout.addWidget(frame)

        layout.addStretch()

    def _init_chart_widget(self):
        """Инициализирует виджет графика"""
        if not hasattr(self, "frameChart"):
            return

        layout = self.frameChart.layout()
        if layout is None:
            layout = QVBoxLayout(self.frameChart)
            layout.setContentsMargins(0, 0, 0, 0)

        self.chart_widget = ChartWidget()
        self.chart_widget.set_profile_service(self.profile_service)
        layout.addWidget(self.chart_widget)

    def _connect_signals(self):
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self._open_edit_profile)
        if hasattr(self, 'btnCompletedProjects'):
            self.btnCompletedProjects.clicked.connect(self._show_completed_projects)
        if hasattr(self, 'btnRefresh'):
            self.btnRefresh.clicked.connect(self.refresh_data)

    def _open_edit_profile(self):
        """Открывает диалог редактирования профиля"""
        edit_data = {
            'id': self.employee_id,
            'last_name': self.employee_data.get('last_name', ''),
            'first_name': self.employee_data.get('first_name', ''),
            'middle_name': self.employee_data.get('middle_name', ''),
            'position': self.employee_data.get('position', ''),
            'phone_number': self.employee_data.get('phone_number', ''),
            'work_number': self.employee_data.get('work_number', ''),
            'email': self.employee_data.get('email', ''),
            'birth_date': self.employee_data.get('birth_date', ''),
            'department_id': self.employee_data.get('department_id'),
            'division_id': self.employee_data.get('division_id'),
            'role': self.employee_data.get('role', 'user')
        }

        dialog = EditProfileDialog(self, employee_data=edit_data, profile_service=self.profile_service)
        if dialog.exec():
            self.load_employee()
            QMessageBox.information(self, "Профиль обновлен", "Данные профиля успешно обновлены")

    def _show_completed_projects(self):
        """Показать окно выполненных проектов"""
        try:
            projects = self.profile_service.get_employee_projects(self.employee_id)

            if self.projects_page is None:
                self.projects_page = ProjectsPage(
                    employee_id=self.employee_id,
                    mode="all",
                    projects_data=projects,
                    profile_service=self.profile_service
                )
                self.projects_page.back_requested.connect(self._hide_completed_projects)
            else:
                self.projects_page.update_data(projects_data=projects, employee_id=self.employee_id)

            self.projects_page.show()
            self.projects_page.raise_()
            self.projects_page.activateWindow()
        except Exception as e:
            print(f"Ошибка при открытии окна проектов: {e}")

    def _hide_completed_projects(self):
        if self.projects_page:
            self.projects_page.hide()

    def refresh_data(self):
        """Обновляет данные профиля"""
        self.load_employee()