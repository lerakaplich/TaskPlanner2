import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTableWidgetItem,
                             QSizePolicy, QMessageBox, QFrame, QLabel, QProgressBar,
                             QHBoxLayout, QSpacerItem, QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QPixmap

from windows.profile.chart_widget import ChartWidget
from windows.profile.edit_profile import EditProfileDialog
from windows.profile.projects_page import ProjectsPage


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

        # Ссылка на родительское окно/виджет для навигации
        self.main_window = parent

        # Данные сотрудника
        self.employee_data = {}

        # Создаем страницу выполненных проектов (но не показываем)
        self.projects_page = None

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "profile"
        )
        uic.loadUi(os.path.join(ui_path, "profile_page.ui"), self)

        # Инициализация графика
        self.init_chart_widget()

        # Инициализация
        self.connect_signals()

        # Загружаем тестовые данные
        self.load_test_data()

    def init_chart_widget(self):
        """Инициализация виджета графика"""
        if ChartWidget is None:
            print("ChartWidget не доступен, пропускаем инициализацию")
            return

        try:
            if hasattr(self, 'frameChart'):
                self.chart_widget = ChartWidget()
                self.chart_widget.setMinimumHeight(350)
                self.chart_widget.setMaximumHeight(400)

                layout = self.frameChart.layout()
                if layout is None:
                    layout = QVBoxLayout()
                    self.frameChart.setLayout(layout)

                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

                if hasattr(self, 'labelChartPlaceholder'):
                    self.labelChartPlaceholder.hide()

                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

                layout.addWidget(self.chart_widget)

                if hasattr(self.chart_widget, 'refresh_clicked'):
                    self.chart_widget.refresh_clicked.connect(self.on_chart_refresh)
                if hasattr(self.chart_widget, 'export_clicked'):
                    self.chart_widget.export_clicked.connect(self.on_chart_export)

        except Exception as e:
            print(f"Ошибка инициализации графика: {e}")
            import traceback
            traceback.print_exc()

    def connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self.open_edit_profile)
        if hasattr(self, 'btnCompletedProjects'):
            self.btnCompletedProjects.clicked.connect(self.show_completed_projects)

    def open_edit_profile(self):
        """Открытие диалога редактирования профиля"""
        if EditProfileDialog is None:
            QMessageBox.warning(self, "Ошибка", "Модуль редактирования профиля не найден")
            return
        dialog = EditProfileDialog(self, self.employee_data)
        dialog.exec()

    def show_completed_projects(self):
        """Показать окно выполненных проектов"""
        if ProjectsPage is None:
            print("Ошибка: ProjectsPage не импортирован")
            return

        try:
            if self.projects_page is None:
                self.projects_page = ProjectsPage(
                    employee_id=self.employee_id
                )
                self.projects_page.back_requested.connect(self.hide_completed_projects)

            self.projects_page.set_employee_id(self.employee_id)
            self.projects_page.refresh_data()
            self.projects_page.show()
            self.projects_page.raise_()
            self.projects_page.activateWindow()

        except Exception as e:
            print(f"Ошибка при открытии окна выполненных проектов: {e}")
            import traceback
            traceback.print_exc()

    def hide_completed_projects(self):
        """Скрыть окно выполненных проектов"""
        if self.projects_page:
            self.projects_page.hide()

    def load_test_data(self):
        """Загрузка тестовых данных"""
        try:
            # Тестовые данные сотрудника с 10 проектами
            self.employee_data = {
                'id': 1,
                'last_name': 'Иванов',
                'first_name': 'Иван',
                'middle_name': 'Иванович',
                'position': 'Старший инженер-программист',
                'department': 'Отдел разработки ПО',
                'phone_number': '+7 (123) 456-78-90',
                'email': 'ivanov@maz.by',
                'birth_date': '1990-05-15',
                'photo_path': None,
                'completed_tasks': 156,
                'active_projects': 10,
                'rating': 0.75,
                'skills': [
                    {'topic': 'Программирование', 'kpd': 0.8, 'tasks_completed': 45},
                    {'topic': 'Дизайн', 'kpd': 0.2, 'tasks_completed': 18},
                    {'topic': 'Аналитика', 'kpd': 0.5, 'tasks_completed': 22},
                    {'topic': 'Тестирование', 'kpd': 0.1, 'tasks_completed': 32},
                    {'topic': 'Документация', 'kpd': 0.9, 'tasks_completed': 12},
                    {'topic': 'Координация', 'kpd': 0.3, 'tasks_completed': 15},
                    {'topic': 'Оптимизация', 'kpd': 0.7, 'tasks_completed': 8},
                    {'topic': 'Управление', 'kpd': 0.6, 'tasks_completed': 20},
                    {'topic': 'Исследование', 'kpd': 0.4, 'tasks_completed': 10},
                    {'topic': 'Внедрение', 'kpd': 0.55, 'tasks_completed': 14},
                ],
                'projects': [
                    {
                        'name': 'Разработка новой кабины',
                        'progress': 75,
                        'tasks_completed': 12,
                        'tasks_total': 16
                    },
                    {
                        'name': 'Модернизация конвейера',
                        'progress': 90,
                        'tasks_completed': 9,
                        'tasks_total': 10
                    },
                    {
                        'name': 'Внедрение ERP-системы',
                        'progress': 45,
                        'tasks_completed': 18,
                        'tasks_total': 40
                    },
                    {
                        'name': 'Автоматизация складского учета',
                        'progress': 30,
                        'tasks_completed': 6,
                        'tasks_total': 20
                    },
                    {
                        'name': 'Разработка мобильного приложения',
                        'progress': 60,
                        'tasks_completed': 15,
                        'tasks_total': 25
                    },
                    {
                        'name': 'Обновление серверного оборудования',
                        'progress': 85,
                        'tasks_completed': 17,
                        'tasks_total': 20
                    },
                    {
                        'name': 'Внедрение системы контроля качества',
                        'progress': 25,
                        'tasks_completed': 5,
                        'tasks_total': 20
                    },
                    {
                        'name': 'Оптимизация производственных процессов',
                        'progress': 55,
                        'tasks_completed': 11,
                        'tasks_total': 20
                    },
                    {
                        'name': 'Разработка документации',
                        'progress': 95,
                        'tasks_completed': 19,
                        'tasks_total': 20
                    },
                    {
                        'name': 'Обучение персонала',
                        'progress': 40,
                        'tasks_completed': 8,
                        'tasks_total': 20
                    }
                ]
            }

            # Заполняем UI данными
            self.update_ui_from_data()

        except Exception as e:
            print(f"Ошибка загрузки тестовых данных: {e}")

    def update_ui_from_data(self):
        """Обновление UI из данных сотрудника"""
        data = self.employee_data

        # Основная информация
        if hasattr(self, 'labelFullName'):
            middle = data.get('middle_name', '')
            if middle:
                middle = f" {middle}"
            self.labelFullName.setText(
                f"{data.get('last_name', '')} {data.get('first_name', '')}{middle}"
            )

        if hasattr(self, 'labelPosition'):
            self.labelPosition.setText(data.get('position', ''))

        if hasattr(self, 'labelDepartment'):
            self.labelDepartment.setText(data.get('department', ''))

        if hasattr(self, 'labelPhone'):
            self.labelPhone.setText(data.get('phone_number', ''))

        if hasattr(self, 'labelEmail'):
            self.labelEmail.setText(data.get('email', ''))

        # Дата рождения
        if hasattr(self, 'labelBirthDate'):
            birth = data.get('birth_date')
            if birth:
                date = QDate.fromString(birth, "yyyy-MM-dd")
                if date.isValid():
                    self.labelBirthDate.setText(date.toString("dd.MM.yyyy"))
                else:
                    self.labelBirthDate.setText("Не указана")
            else:
                self.labelBirthDate.setText("Не указана")

        # Статистика
        if hasattr(self, 'labelCompletedTasks'):
            self.labelCompletedTasks.setText(str(data.get('completed_tasks', 0)))

        if hasattr(self, 'labelActiveProjects'):
            self.labelActiveProjects.setText(str(data.get('active_projects', 0)))

        # Рейтинг
        self.update_rating(data.get('rating', 0.0))

        # Таблица навыков
        self.setup_skills_table()

        # Проекты - динамическое создание
        self.create_projects_widgets()

    def setup_skills_table(self):
        """Настройка таблицы с навыками"""
        try:
            skills_data = self.employee_data.get('skills', [])

            if not hasattr(self, 'tableSkills'):
                return

            table = self.tableSkills
            table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            header = table.horizontalHeader()
            header.setSectionResizeMode(header.ResizeMode.Stretch)
            table.setMinimumWidth(400)
            table.setRowCount(len(skills_data))
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(['Тема', 'КПД по теме', 'Задач выполнено'])

            for row, skill in enumerate(skills_data):
                # Тема
                topic_item = QTableWidgetItem(skill['topic'])
                topic_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 0, topic_item)

                # КПД
                kpd = skill['kpd']
                kpd_item = QTableWidgetItem(f"{kpd:.2f}")
                kpd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                if kpd >= 2.0:
                    kpd_item.setForeground(QColor(0, 128, 0))
                elif kpd >= 1.5:
                    kpd_item.setForeground(QColor(0, 100, 0))
                elif kpd >= 1.0:
                    kpd_item.setForeground(QColor(218, 165, 32))
                else:
                    kpd_item.setForeground(QColor(220, 39, 48))

                table.setItem(row, 1, kpd_item)

                # Задачи
                tasks_item = QTableWidgetItem(str(skill['tasks_completed']))
                tasks_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 2, tasks_item)

            table.resizeColumnsToContents()
            header.setSectionResizeMode(2, header.ResizeMode.Stretch)

            total_height = table.horizontalHeader().height() + 2
            for row in range(table.rowCount()):
                total_height += table.rowHeight(row)
            table.setMinimumHeight(min(total_height + 10, 300))

        except Exception as e:
            print(f"Ошибка настройки таблицы навыков: {e}")

    def update_rating(self, kpd_value):
        """Обновление рейтинга сотрудника"""
        try:
            if hasattr(self, 'labelKPD'):
                self.labelKPD.setText(f"КПД: {kpd_value:.2f}")

            # Обновляем звезды
            if kpd_value >= 1.0:
                filled_stars = 5
            else:
                filled_stars = int(kpd_value * 5)

            for i in range(1, 6):
                star_attr = f'star{i}'
                if hasattr(self, star_attr):
                    star = getattr(self, star_attr)
                    if i <= filled_stars:
                        star.setStyleSheet("font-size: 24px; color: #FFD700;")
                    else:
                        star.setStyleSheet("font-size: 24px; color: #E0E0E0;")

        except Exception as e:
            print(f"Ошибка обновления рейтинга: {e}")

    def create_projects_widgets(self):
        """Динамическое создание виджетов проектов с ограничением высоты"""
        try:
            projects_data = self.employee_data.get('projects', [])

            if not hasattr(self, 'projectsContainer') or not hasattr(self, 'scrollAreaProjects'):
                return

            # Получаем контейнер для проектов
            container = self.projectsContainer
            layout = container.layout()

            # Очищаем контейнер
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Добавляем проекты
            for i, project in enumerate(projects_data):
                # Создаем фрейм для проекта
                project_frame = QFrame()
                project_frame.setObjectName(f"project_{i}")
                project_frame.setProperty("class", "projectCard")
                project_frame.setStyleSheet("""
                    QFrame[class="projectCard"] {
                        background-color: white;
                        border-radius: 10px;
                        border: 1px solid #E0E0E0;
                        padding: 15px;
                    }
                    QFrame[class="projectCard"]:hover {
                        border: 2px solid #ccab6e;
                        background-color: #FFFDF6;
                    }
                """)

                # Layout для проекта
                project_layout = QVBoxLayout(project_frame)

                # Верхняя строка с названием и процентом
                top_layout = QHBoxLayout()

                # Название проекта
                name_label = QLabel(project['name'])
                name_label.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #1B232A;
                    }
                """)

                # Процент выполнения
                progress_label = QLabel(f"{project['progress']}%")
                progress_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        color: #D22730;
                    }
                """)

                top_layout.addWidget(name_label)
                top_layout.addStretch()
                top_layout.addWidget(progress_label)

                # Прогресс бар
                progress_bar = QProgressBar()
                progress_bar.setValue(project['progress'])
                progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #E0E0E0;
                        border-radius: 6px;
                        text-align: center;
                        background-color: #F5F5F7;
                        height: 12px;
                    }
                    QProgressBar::chunk {
                        background-color: #D22730;
                        border-radius: 6px;
                    }
                """)

                # Информация о задачах
                tasks_label = QLabel(
                    f"Задачи: {project['tasks_completed']}/{project['tasks_total']} выполнено"
                )
                tasks_label.setStyleSheet("""
                    QLabel {
                        font-size: 12px;
                        color: #666;
                    }
                """)

                # Добавляем все в layout проекта
                project_layout.addLayout(top_layout)
                project_layout.addWidget(progress_bar)
                project_layout.addWidget(tasks_label)

                # Добавляем проект в контейнер
                layout.addWidget(project_frame)

            # Добавляем растяжение в конце
            layout.addStretch()

        except Exception as e:
            print(f"Ошибка создания виджетов проектов: {e}")
            import traceback
            traceback.print_exc()

    def on_chart_refresh(self):
        """Обработчик обновления графика"""
        print("График обновлен")
        if hasattr(self, 'chart_widget'):
            self.chart_widget.refresh_data()

    def on_chart_export(self):
        """Обработчик экспорта графика"""
        print("Экспорт графика")
        if hasattr(self, 'chart_widget'):
            self.chart_widget.export_chart()

    def set_employee_id(self, employee_id):
        """Установка ID сотрудника"""
        self.employee_id = employee_id
        self.load_test_data()
        if self.projects_page:
            self.projects_page.set_employee_id(employee_id)

    def refresh_data(self):
        """Обновление всех данных"""
        self.load_test_data()
        if hasattr(self, 'chart_widget'):
            self.chart_widget.refresh_data()
        if self.projects_page and self.projects_page.isVisible():
            self.projects_page.refresh_data()


if __name__ == "__main__":
    # Тестовый запуск
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ProfilePage(employee_id=1)
    window.setWindowTitle("Профиль сотрудника - МАЗ")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())