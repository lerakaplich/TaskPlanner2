import os
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
                             QProgressBar, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.uic import loadUi

# Импортируем виджет графика
try:
    from chart_widget import ChartWidget
except ImportError:
    import sys

    sys.path.append(os.path.dirname(__file__))
    try:
        from chart_widget import ChartWidget
    except ImportError:
        ChartWidget = None
        print("ВНИМАНИЕ: Не удалось импортировать ChartWidget")

# Импортируем страницу выполненных проектов
try:
    from completed_projects_page import CompletedProjectsPage
except ImportError:
    CompletedProjectsPage = None
    print("ВНИМАНИЕ: Не удалось импортировать CompletedProjectsPage")


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

        # Создаем страницу выполненных проектов (но не показываем)
        self.completed_projects_page = None

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")
        if not os.path.exists(ui_path):
            ui_path = os.path.dirname(__file__)

        ui_file = os.path.join(ui_path, "profile_page.ui")

        if os.path.exists(ui_file):
            loadUi(ui_file, self)
        else:
            self.setup_basic_ui()

        # Устанавливаем политику размера для scrollArea
        if hasattr(self, 'scrollArea'):
            self.scrollArea.setWidgetResizable(True)
            self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Инициализация графика
        self.init_chart_widget()

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

    def connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self.edit_profile_requested.emit)
        if hasattr(self, 'btnCompletedProjects'):
            # Подключаем кнопку к методу открытия окна
            self.btnCompletedProjects.clicked.connect(self.show_completed_projects)

    # Добавьте этот метод в класс ProfilePage

    def show_completed_projects(self):
        """Показать окно выполненных проектов"""
        if CompletedProjectsPage is None:
            print("Ошибка: CompletedProjectsPage не импортирован")
            return

        try:
            # Если окно уже создано, просто показываем его
            if self.completed_projects_page is None:
                # Создаем новое окно
                self.completed_projects_page = CompletedProjectsPage(
                    employee_id=self.employee_id
                )
                # Подключаем сигнал возврата
                self.completed_projects_page.back_requested.connect(self.hide_completed_projects)

            # Устанавливаем ID сотрудника
            self.completed_projects_page.set_employee_id(self.employee_id)

            # Обновляем данные
            self.completed_projects_page.refresh_data()

            # Показываем окно
            self.completed_projects_page.show()
            self.completed_projects_page.raise_()
            self.completed_projects_page.activateWindow()

            # Если это отдельное окно, можно скрыть текущее
            # self.hide()

        except Exception as e:
            print(f"Ошибка при открытии окна выполненных проектов: {e}")
            import traceback
            traceback.print_exc()

    def hide_completed_projects(self):
        """Скрыть окно выполненных проектов"""
        if self.completed_projects_page:
            self.completed_projects_page.hide()
            # Если скрывали текущее окно, показываем его снова
            # self.show()

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
                'rating': 0.75
            }

            # Устанавливаем данные в UI
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

            # Настраиваем таблицу навыков
            if hasattr(self, 'tableSkills'):
                self.setup_skills_table()

            # Загружаем данные проектов
            if hasattr(self, 'progressBar1'):
                self.load_projects_data()

        except Exception as e:
            print(f"Ошибка загрузки тестовых данных: {e}")

    def setup_skills_table(self):
        """Настройка таблицы с навыками"""
        try:
            skills_data = [
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
            ]

            table = self.tableSkills
            table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            header = table.horizontalHeader()
            header.setSectionResizeMode(header.ResizeMode.Stretch)
            table.setMinimumWidth(400)
            table.setRowCount(len(skills_data))
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(['Тема', 'КПД по теме', 'Задач выполнено'])

            for row, skill in enumerate(skills_data):
                topic_item = QTableWidgetItem(skill['topic'])
                topic_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 0, topic_item)

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
            self.update_rating_stars(kpd_value)
        except Exception as e:
            print(f"Ошибка обновления рейтинга: {e}")

    def update_rating_stars(self, kpd_value):
        """Обновление отображения звезд рейтинга"""
        try:
            if kpd_value >= 1.0:
                filled_stars = 5
            else:
                filled_stars = int(kpd_value * 5)

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
        """Загрузка данных по проектам"""
        try:
            projects_data = [
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
                }
            ]

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
        """Установка ID сотрудника"""
        self.employee_id = employee_id
        self.load_test_data()
        # Обновляем ID в окне выполненных проектов, если оно создано
        if self.completed_projects_page:
            self.completed_projects_page.set_employee_id(employee_id)

    def refresh_data(self):
        """Обновление всех данных"""
        self.load_test_data()
        if hasattr(self, 'chart_widget'):
            self.chart_widget.refresh_data()
        # Обновляем данные в окне выполненных проектов, если оно открыто
        if self.completed_projects_page and self.completed_projects_page.isVisible():
            self.completed_projects_page.refresh_data()


if __name__ == "__main__":
    # Тестовый запуск
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ProfilePage(employee_id=1)
    window.setWindowTitle("Профиль сотрудника - МАЗ")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())