# windows/profile/profile_page.py

import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidgetItem,
    QSizePolicy, QMessageBox, QFrame, QLabel,
    QProgressBar, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor

from services.profile_service import ProfileService

from windows.profile.chart_widget import ChartWidget
from windows.profile.edit_profile import EditProfileDialog
from windows.profile.projects_page import ProjectsPage


# windows/profile/profile_page.py - исправленный фрагмент

class ProfilePage(QWidget):
    """Страница профиля сотрудника"""

    edit_profile_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, current_user=None, service=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.main_window = parent
        self.current_user = current_user

        # Если employee_id не передан, пытаемся взять из current_user
        if not self.employee_id and current_user:
            self.employee_id = current_user.get('id')

        # Создаем сервис профиля (с правильной сессией)
        from database import get_tasks_session
        session = get_tasks_session()
        self.profile_service = ProfileService(session=session)

        # Если передан current_user, устанавливаем его в сервис
        if current_user:
            self.profile_service.set_current_user(current_user)

        self.employee_data = {}
        self.projects_page = None

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "profile"
        )

        uic.loadUi(os.path.join(ui_path, "profile_page.ui"), self)

        self.init_chart_widget()
        self.connect_signals()

        if self.employee_id:
            self.load_employee()
        else:
            print("⚠️ Не указан ID сотрудника")

    def load_employee(self):
        """Загрузка данных сотрудника через сервис"""
        if self.employee_id:
            print(f"📊 Загрузка профиля для сотрудника ID: {self.employee_id}")
            self.employee_data = self.profile_service.get_employee_profile(
                self.employee_id
            )
            print(f"📊 Получены данные: {self.employee_data.get('last_name')} {self.employee_data.get('first_name')}")
            self.update_ui_from_data()
        else:
            print("⚠️ Не указан ID сотрудника для загрузки профиля")

    # ---------- UI ----------

    def connect_signals(self):
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self.open_edit_profile)

        if hasattr(self, 'btnCompletedProjects'):
            self.btnCompletedProjects.clicked.connect(self.show_completed_projects)

        if hasattr(self, 'btnRefresh'):
            self.btnRefresh.clicked.connect(self.refresh_data)

    def update_ui_from_data(self):
        """Обновляет UI данными из employee_data"""
        data = self.employee_data

        # ФИО
        if hasattr(self, 'labelFullName'):
            middle = data.get('middle_name', '')
            if middle:
                middle = f" {middle}"
            self.labelFullName.setText(
                f"{data.get('last_name')} {data.get('first_name')}{middle}"
            )

        # Должность и отдел
        if hasattr(self, 'labelPosition'):
            self.labelPosition.setText(data.get('position', ''))

        if hasattr(self, 'labelDepartment'):
            self.labelDepartment.setText(data.get('department', ''))

        # Контактная информация
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
                    self.labelBirthDate.setText("")

        # Статистика
        if hasattr(self, 'labelCompletedTasks'):
            self.labelCompletedTasks.setText(
                str(data.get('completed_tasks', 0))
            )

        if hasattr(self, 'labelActiveProjects'):
            self.labelActiveProjects.setText(
                str(data.get('active_projects', 0))
            )

        # Рейтинг и навыки
        self.update_rating_ui(data.get('rating', 0))
        self.setup_skills_table()

        # Проекты
        self.create_projects_widgets()

        # Обновляем график
        if hasattr(self, 'chart_widget'):
            self.chart_widget.load_data(self.employee_id)

    # ---------- RATING ----------

    def update_rating_ui(self, rating):
        if hasattr(self, 'labelKPD'):
            self.labelKPD.setText(f"КПД: {rating:.2f}")

        stars = self.profile_service.calculate_rating_stars(rating)

        for i in range(1, 6):
            star_attr = f"star{i}"
            if hasattr(self, star_attr):
                star = getattr(self, star_attr)
                if i <= stars:
                    star.setStyleSheet("font-size: 24px; color: #FFD700;")
                else:
                    star.setStyleSheet("font-size: 24px; color: #E0E0E0;")

    # ---------- TABLE ----------

    def setup_skills_table(self):
        """Заполняет таблицу навыков"""
        skills = self.employee_data.get('skills', [])
        table = self.tableSkills

        table.setRowCount(len(skills))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Тема", "КПД", "Задач"])

        for row, skill in enumerate(skills):
            table.setItem(row, 0, QTableWidgetItem(skill["topic"]))
            table.setItem(row, 1, QTableWidgetItem(f"{skill['kpd']:.2f}"))
            table.setItem(row, 2, QTableWidgetItem(str(skill["tasks_completed"])))

    # ---------- PROJECTS ----------

    def create_projects_widgets(self):
        """Создает виджеты проектов"""
        projects = self.employee_data.get("projects", [])
        container = self.projectsContainer
        layout = container.layout()

        # Очищаем контейнер
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавляем проекты
        for project in projects:
            frame = QFrame()
            frame.setProperty("class", "projectCard")
            frame.setStyleSheet("""
                QFrame.projectCard {
                    background-color: white;
                    border-radius: 8px;
                    border: 1px solid #E0E0E0;
                    padding: 10px;
                    margin: 5px;
                }
            """)

            v = QVBoxLayout(frame)
            v.setSpacing(8)

            # Заголовок проекта и процент
            name = QLabel(project["name"])
            name.setStyleSheet("font-weight: bold; font-size: 14px;")

            percent = QLabel(f"{project['progress']}%")
            percent.setStyleSheet("color: #ccab6e; font-weight: bold;")

            h = QHBoxLayout()
            h.addWidget(name)
            h.addStretch()
            h.addWidget(percent)
            v.addLayout(h)

            # Прогресс-бар
            bar = QProgressBar()
            bar.setValue(project["progress"])
            bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    height: 10px;
                }
                QProgressBar::chunk {
                    background-color: #D22730;
                    border-radius: 4px;
                }
            """)
            v.addWidget(bar)

            # Задачи
            tasks = QLabel(
                f"Задачи {project['tasks_completed']}/{project['tasks_total']}"
            )
            tasks.setStyleSheet("color: #666; font-size: 12px;")
            v.addWidget(tasks)

            layout.addWidget(frame)

        layout.addStretch()

    # ---------- ACTIONS ----------

    def open_edit_profile(self):
        """Открывает диалог редактирования профиля"""
        dialog = EditProfileDialog(
            self,
            employee_data=self.employee_data,
            profile_service=self.profile_service
        )

        if dialog.exec():
            # Обновляем данные в UI
            self.employee_data = dialog.employee_data
            self.update_ui_from_data()
            QMessageBox.information(
                self,
                "Профиль обновлен",
                "Данные профиля успешно обновлены"
            )

    # windows/profile/profile_page.py

    def show_completed_projects(self):
        """Показать окно выполненных проектов"""
        if ProjectsPage is None:
            print("Ошибка: ProjectsPage не импортирован")
            return

        try:
            # Получаем все проекты с задачами
            all_projects = self.profile_service.get_all_employee_projects_with_tasks(
                self.employee_id
            )

            if self.projects_page is None:
                self.projects_page = ProjectsPage(
                    employee_id=self.employee_id,
                    mode="all",
                    projects_data=all_projects
                )
                self.projects_page.back_requested.connect(self.hide_completed_projects)
            else:
                self.projects_page.set_employee_id(self.employee_id)
                self.projects_page.projects_data = all_projects
                self.projects_page.refresh_data()

            self.projects_page.show()
            self.projects_page.raise_()
            self.projects_page.activateWindow()

        except Exception as e:
            print(f"Ошибка при открытии окна выполненных проектов: {e}")
            import traceback
            traceback.print_exc()

    # ---------- CHART ----------

    def init_chart_widget(self):
        """Инициализирует виджет графика"""
        if not hasattr(self, "frameChart"):
            return

        self.chart_widget = ChartWidget()
        self.chart_widget.set_profile_service(self.profile_service)

        layout = QVBoxLayout()
        self.frameChart.setLayout(layout)
        layout.addWidget(self.chart_widget)

    # ---------- REFRESH ----------

    def refresh_data(self):
        """Обновляет данные профиля"""
        self.load_employee()
        if hasattr(self, 'chart_widget'):
            self.chart_widget.load_data(self.employee_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProfilePage(employee_id=1)
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())