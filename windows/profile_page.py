
import os
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
                             QProgressBar, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.uic import loadUi


class ProfilePage(QWidget):
    """Страница профиля сотрудника"""

    # Сигналы для навигации
    edit_profile_requested = pyqtSignal()
    show_all_skills_requested = pyqtSignal()
    show_completed_projects_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None):
        super().__init__(parent)

        # ID сотрудника (если передан)
        self.employee_id = employee_id

        # Загружаем UI
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")
        ui_file = os.path.join(self.ui_path, "profile_page.ui")

        if os.path.exists(ui_file):
            loadUi(ui_file, self)
        else:
            # Создаем простой интерфейс если файл не найден
            self.setup_basic_ui()

        # Инициализация
        self.connect_signals()
        self.load_test_data()

    def setup_basic_ui(self):
        """Создание простого интерфейса если файл UI не найден"""
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                font-family: 'Segoe UI', Arial;
            }
            QLabel {
                color: #1B232A;
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Профиль сотрудника (UI файл не найден)"))
        self.setLayout(layout)

    def connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self.edit_profile_requested.emit)
        if hasattr(self, 'btnShowAllSkills'):
            self.btnShowAllSkills.clicked.connect(self.show_all_skills_requested.emit)
        if hasattr(self, 'btnCompletedProjects'):
            self.btnCompletedProjects.clicked.connect(self.show_completed_projects_requested.emit)

    def load_test_data(self):
        """Загрузка тестовых данных"""
        try:
            # Тестовые данные сотрудника
            employee_data = {
                'id': 1,
                'last_name': 'Иванов',
                'first_name': 'Иван',
                'middle_name': 'Иванович',
                'position': 'Старший инженер-программист',
                'department': 'Отдел разработки ПО',
                'phone_number': '+7 (123) 456-78-90',
                'email': 'ivanov@maz.by',
                'completed_tasks': 156,
                'active_projects': 5,
                'rating': 0.75  # Средний КПД
            }

            # Устанавливаем данные в UI если элементы существуют
            if hasattr(self, 'labelFullName'):
                self.labelFullName.setText(
                    f"{employee_data['last_name']} {employee_data['first_name']} {employee_data['middle_name']}"
                )
            if hasattr(self, 'labelPosition'):
                self.labelPosition.setText(employee_data['position'])
            if hasattr(self, 'labelDepartment'):
                self.labelDepartment.setText(employee_data['department'])
            if hasattr(self, 'labelPhone'):
                self.labelPhone.setText(employee_data['phone_number'])
            if hasattr(self, 'labelEmail'):
                self.labelEmail.setText(employee_data['email'])
            if hasattr(self, 'labelCompletedTasks'):
                self.labelCompletedTasks.setText(str(employee_data['completed_tasks']))
            if hasattr(self, 'labelActiveProjects'):
                self.labelActiveProjects.setText(str(employee_data['active_projects']))

            # Обновляем рейтинг
            self.update_rating(employee_data['rating'])

            # Устанавливаем аватар (первая буква фамилии)
            if hasattr(self, 'labelAvatar'):
                first_letter = employee_data['last_name'][0].upper()
                self.labelAvatar.setText(f"{first_letter}")

            # Настраиваем таблицу навыков
            if hasattr(self, 'tableSkills'):
                self.setup_skills_table()

            # Загружаем данные проектов
            if hasattr(self, 'progressBar1'):
                self.load_projects_data()

        except Exception as e:
            print(f"Ошибка загрузки тестовых данных: {e}")

    def setup_skills_table(self):
        """Настройка таблицы с навыками (тестовые данные)"""
        try:
            # Тестовые данные по навыкам
            skills_data = [
                {'topic': 'Программирование', 'kpd': 0.8, 'tasks_completed': 45},
                {'topic': 'Дизайн', 'kpd': 0.2, 'tasks_completed': 18},
                {'topic': 'Аналитика', 'kpd': 0.5, 'tasks_completed': 22},
                {'topic': 'Тестирование', 'kpd': 0.1, 'tasks_completed': 32},
                {'topic': 'Документация', 'kpd': 0.9, 'tasks_completed': 12},
                {'topic': 'Координация', 'kpd': 0.3, 'tasks_completed': 15},
                {'topic': 'Оптимизация', 'kpd': 0.7, 'tasks_completed': 8},
                {'topic': 'Документация', 'kpd': 0.9, 'tasks_completed': 12},
                {'topic': 'Координация', 'kpd': 0.3, 'tasks_completed': 15},
                {'topic': 'Оптимизация', 'kpd': 0.7, 'tasks_completed': 8},
            ]

            table = self.tableSkills
            table.setRowCount(len(skills_data))
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(['Тема', 'КПД по теме', 'Задач выполнено'])

            # Заполняем данными
            for row, skill in enumerate(skills_data):
                # Тема
                topic_item = QTableWidgetItem(skill['topic'])
                topic_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 0, topic_item)

                # КПД
                kpd = skill['kpd']
                kpd_item = QTableWidgetItem(f"{kpd:.2f}")
                kpd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                # Раскрашиваем КПД в зависимости от значения
                if kpd >= 2.0:
                    kpd_item.setForeground(QColor(0, 128, 0))  # Зеленый
                elif kpd >= 1.5:
                    kpd_item.setForeground(QColor(0, 100, 0))  # Темно-зеленый
                elif kpd >= 1.0:
                    kpd_item.setForeground(QColor(218, 165, 32))  # Золотой
                else:
                    kpd_item.setForeground(QColor(220, 39, 48))  # Красный

                table.setItem(row, 1, kpd_item)

                # Количество задач
                tasks_item = QTableWidgetItem(str(skill['tasks_completed']))
                tasks_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 2, tasks_item)

            # Настройка внешнего вида таблицы
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.resizeColumnsToContents()

            # Рассчитываем и обновляем средний рейтинг
            avg_kpd = sum(s['kpd'] for s in skills_data) / len(skills_data)
            self.update_rating(avg_kpd)

        except Exception as e:
            print(f"Ошибка настройки таблицы навыков: {e}")

    def update_rating(self, kpd_value):
        """Обновление рейтинга сотрудника"""
        try:
            # Обновляем значение КПД
            if hasattr(self, 'labelKPD'):
                self.labelKPD.setText(f"КПД: {kpd_value:.2f}")

            # Обновляем звезды
            self.update_rating_stars(kpd_value)

        except Exception as e:
            print(f"Ошибка обновления рейтинга: {e}")

    def update_rating_stars(self, kpd_value):
        """Обновление отображения звезд рейтинга"""
        try:
            # Рассчитываем количество заполненных звезд
            if kpd_value >= 1.0:
                filled_stars = 5
            else:
                # Линейная интерполяция для значений < 1.0
                filled_stars = int(kpd_value * 5)

            # Обновляем стили звезд если они существуют
            stars = []
            for i in range(1, 6):
                star_attr = f'star{i}'
                if hasattr(self, star_attr):
                    stars.append(getattr(self, star_attr))

            for i, star in enumerate(stars):
                if i < filled_stars:
                    star.setStyleSheet("font-size: 24px; color: #FFD700;")
                else:
                    star.setStyleSheet("font-size: 24px; color: #E0E0E0;")

        except Exception as e:
            print(f"Ошибка обновления звезд рейтинга: {e}")

    def load_projects_data(self):
        """Загрузка данных по проектам (тестовые данные)"""
        try:
            projects_data = [
                {
                    'name': 'Разработка новой кабины',
                    'progress': 75,
                    'tasks_completed': 12,
                    'tasks_total': 16,
                    'is_critical': True
                },
                {
                    'name': 'Модернизация конвейера',
                    'progress': 90,
                    'tasks_completed': 9,
                    'tasks_total': 10,
                    'is_critical': True
                },
                {
                    'name': 'Внедрение ERP-системы',
                    'progress': 45,
                    'tasks_completed': 18,
                    'tasks_total': 40,
                    'is_critical': False
                },
                {
                    'name': 'аррррр новой кабины',
                    'progress': 75,
                    'tasks_completed': 12,
                    'tasks_total': 16,
                    'is_critical': True
                },
                {
                    'name': 'Модернизация конвейера',
                    'progress': 90,
                    'tasks_completed': 9,
                    'tasks_total': 10,
                    'is_critical': True
                },
                {
                    'name': 'Внедрение ERP-системы',
                    'progress': 45,
                    'tasks_completed': 18,
                    'tasks_total': 40,
                    'is_critical': False
                }
            ]

            # Обновляем прогресс-бары если они существуют
            for i in range(1, 4):
                progress_attr = f'progressBar{i}'
                tasks_label_attr = f'labelTasks{i}'
                project_label_attr = f'labelProject{i}'

                if (hasattr(self, progress_attr) and
                        hasattr(self, tasks_label_attr) and
                        hasattr(self, project_label_attr)):

                    if i - 1 < len(projects_data):
                        project = projects_data[i - 1]

                        getattr(self, progress_attr).setValue(project['progress'])
                        getattr(self, tasks_label_attr).setText(
                            f"Задачи: {project['tasks_completed']}/{project['tasks_total']} выполнено"
                        )
                        getattr(self, project_label_attr).setText(project['name'])

        except Exception as e:
            print(f"Ошибка загрузки данных проектов: {e}")

    def set_employee_id(self, employee_id):
        """Установка ID сотрудника для загрузки данных"""
        self.employee_id = employee_id
        self.load_test_data()

    def refresh_data(self):
        """Обновление всех данных на странице"""
        self.load_test_data()


# Простая версия интеграции для main_window.py
def integrate_profile_page():
    """Простая функция для интеграции страницы профиля"""
    # 1. Сохраните файл profile_page.ui в папку ui
    # 2. Сохраните файл profile_page.py в папку windows
    # 3. В main_window.py добавьте импорт:
    #    from profile_page import ProfilePage
    # 4. В методе init_pages добавьте:
    #    self.profile_page_instance = ProfilePage()
    #    old_page = self.findChild(QWidget, "analyticsPage")
    #    if old_page:
    #        index = self.contentStack.indexOf(old_page)
    #        old_page.deleteLater()
    #        self.contentStack.insertWidget(index, self.profile_page_instance)
    #        self.analyticsPage = self.profile_page_instance
    pass


if __name__ == "__main__":
    # Тестовый запуск страницы профиля
    app = QApplication(sys.argv)

    # Устанавливаем глобальные стили
    app.setStyle("Fusion")

    # Создаем и показываем страницу профиля
    window = ProfilePage(employee_id=1)
    window.setWindowTitle("Профиль сотрудника - МАЗ")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())