import os
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6 import uic
from datetime import datetime, timedelta
import random

from PyQt6.uic import loadUi

from windows.add_overtime_dialog import AddOvertimeDialog
from windows.overtime_card import OvertimeCard
from windows.period_dialog import PeriodDialog


class OvertimePage(QWidget):
    def __init__(self):
        super().__init__()
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")
        loadUi(os.path.join(self.ui_path, "overtime_page.ui"), self)

        # Заголовок
        self.titleLabel.setText("Переработки")

        # Инициализация фильтров
        self.init_filters()

        # Подключаем кнопки
        self.btnAddOvertime.clicked.connect(self.show_add_overtime)
        self.btnExport.clicked.connect(self.show_export_dialog)
        self.btnApplyFilters.clicked.connect(self.apply_filters)
        self.btnClearFilters.clicked.connect(self.clear_filters)
        self.btnSelectPeriod.clicked.connect(self.select_period)

        # Подключаем изменение проекта для обновления задач
        self.comboProject.currentIndexChanged.connect(self.update_tasks)

        # Загружаем тестовые данные
        self.load_test_data()

        # Применяем фильтры по умолчанию
        self.apply_filters()

    def init_filters(self):
        """Инициализация фильтров"""
        self.comboProject.clear()

        projects = ["Проект А", "Проект Б", "Проект В", "Проект Г"]
        for project in projects:
            self.comboProject.addItem(project, project)

        # Специальный пункт для переработок без проекта
        self.comboProject.addItem("Без проекта", None)

        # По умолчанию показываем placeholder «Выберите проект»
        self.comboProject.setCurrentIndex(-1)

        # Задачи изначально пустые и отключены
        self.comboTask.clear()
        self.comboTask.setCurrentIndex(-1)
        self.comboTask.setEnabled(False)

    def update_tasks(self):
        """Обновление списка задач при выборе проекта"""
        self.comboTask.clear()
        self.comboTask.setCurrentIndex(-1)

        current_idx = self.comboProject.currentIndex()
        if current_idx == -1:
            self.comboTask.setEnabled(False)
            return

        project = self.comboProject.currentData()
        if project is None:  # «Без проекта»
            self.comboTask.setEnabled(False)
            return

        # Реальный проект выбран — загружаем задачи
        tasks = []
        if project == "Проект А":
            tasks = ["Задача А1", "Задача А2", "Задача А3"]
        elif project == "Проект Б":
            tasks = ["Задача Б1", "Задача Б2"]
        elif project == "Проект В":
            tasks = ["Задача В1", "Задача В2", "Задача В3"]
        elif project == "Проект Г":
            tasks = ["Задача Г1"]

        if tasks:
            for task in tasks:
                self.comboTask.addItem(task, task)

        self.comboTask.setCurrentIndex(-1)  # Показываем placeholder «Выберите задачу»
        self.comboTask.setEnabled(True)

    def clear_filters(self):
        """Сброс фильтров"""
        self.comboProject.setCurrentIndex(-1)
        # update_tasks автоматически вызовется через сигнал и сбросит comboTask
        self.display_overtimes()

    def filter_overtimes(self, overtimes):
        """Фильтрация переработок по выбранным критериям"""
        filtered = []

        for overtime in overtimes:
            # Фильтр по проекту (только если что-то выбрано)
            if self.comboProject.currentIndex() != -1:
                selected_project = self.comboProject.currentData()
                if overtime.get('project') != selected_project:
                    continue

            # Фильтр по задаче (только если что-то выбрано)
            if self.comboTask.currentIndex() != -1:
                selected_task = self.comboTask.currentData()
                if overtime.get('task') != selected_task:
                    continue

            filtered.append(overtime)

        return filtered


    def load_test_data(self):
        """Загрузка тестовых данных"""
        self.all_overtimes = []
        self.my_overtimes = []

        # Генерируем тестовые данные
        users = ["Иван Иванов", "Петр Петров", "Анна Сидорова", "Мария Ковалева"]
        projects = ["Проект А", "Проект Б", "Проект В", "Проект Г", None]
        tasks = ["Задача А1", "Задача А2", "Задача Б1", "Задача В1", "Задача Г1", None]

        # Мои переработки
        for i in range(8):
            has_project = random.choice([True, False])
            project = random.choice(projects) if has_project else None
            task = random.choice(tasks) if project else None

            date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%d.%m.%Y")
            start_hour = random.randint(18, 22)
            end_hour = start_hour + random.randint(1, 4)
            time_period = f"{start_hour}:00 - {end_hour}:00"

            overtime = {
                'id': i + 1,
                'date': date,
                'time_period': time_period,
                'duration': f"{end_hour - start_hour}.{random.randint(0, 5)}",
                'project': project,
                'task': task if project else None,
                'description': "Работа над срочным заданием" if not project else "",
                'user': "Я",
                'is_mine': True
            }
            self.my_overtimes.append(overtime)

        # Все переработки (включая чужие)
        for i in range(15):
            has_project = random.choice([True, False])
            project = random.choice(projects) if has_project else None
            task = random.choice(tasks) if project else None

            date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%d.%m.%Y")
            start_hour = random.randint(18, 22)
            end_hour = start_hour + random.randint(1, 4)
            time_period = f"{start_hour}:00 - {end_hour}:00"

            overtime = {
                'id': i + 101,
                'date': date,
                'time_period': time_period,
                'duration': f"{end_hour - start_hour}.{random.randint(0, 5)}",
                'project': project,
                'task': task if project else None,
                'description': "Работа в нерабочее время" if not project else "",
                'user': random.choice(users),
                'is_mine': random.choice([True, False])
            }
            self.all_overtimes.append(overtime)

    def apply_filters(self):
        """Применение фильтров"""
        self.display_overtimes()



    def select_period(self):
        """Выбор периода"""
        dialog = PeriodDialog(self)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            QMessageBox.information(
                self,
                "Фильтр",
                f"Фильтр данных за период:\n"
                f"с {start_date.toString('dd.MM.yyyy')} "
                f"по {end_date.toString('dd.MM.yyyy')}"
            )
        # В будущем можно добавить диалог для выбора периода

    def display_overtimes(self):
        """Отображение переработок в соответствующих вкладках"""
        self.display_my_overtimes()
        self.display_all_overtimes()

    def display_my_overtimes(self):
        """Отображение моих переработок"""
        # Очищаем контейнер
        while self.gridLayoutMy.count():
            item = self.gridLayoutMy.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Фильтруем мои переработки
        filtered = self.filter_overtimes(self.my_overtimes)

        # Отображаем в две колонки
        for i, overtime in enumerate(filtered):
            card = OvertimeCard(overtime)
            row = i // 2
            col = i % 2
            self.gridLayoutMy.addWidget(card, row, col)

    def display_all_overtimes(self):
        """Отображение всех переработок"""
        # Очищаем контейнер
        while self.gridLayoutAll.count():
            item = self.gridLayoutAll.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Фильтруем все переработки
        filtered = self.filter_overtimes(self.all_overtimes)

        # Отображаем в две колонки
        for i, overtime in enumerate(filtered):
            card = OvertimeCard(overtime)
            row = i // 2
            col = i % 2
            self.gridLayoutAll.addWidget(card, row, col)

    def show_add_overtime(self):
        """Показ окна добавления переработки"""
        dialog = AddOvertimeDialog(self)
        if dialog.exec():
            overtime_data = dialog.get_overtime_data()
            # Добавляем новую переработку в список
            new_overtime = {
                'id': len(self.my_overtimes) + 1,
                'date': overtime_data['date'],
                'time_period': f"{overtime_data['start_time']} - {overtime_data['end_time']}",
                'duration': overtime_data['duration'],
                'project': overtime_data['project'] if overtime_data['project'] != "Без проекта" else None,
                'task': overtime_data['task'],
                'description': overtime_data['description'],
                'user': "Я",
                'is_mine': True
            }
            self.my_overtimes.append(new_overtime)
            self.all_overtimes.append(new_overtime)
            self.display_overtimes()

    def show_export_dialog(self):
        """Показ диалога экспорта"""
        dialog = PeriodDialog(self)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            QMessageBox.information(
                self,
                "Экспорт",
                f"Экспорт данных за период:\n"
                f"с {start_date.toString('dd.MM.yyyy')} "
                f"по {end_date.toString('dd.MM.yyyy')}"
            )
            # Здесь будет код для экспорта в Excel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система учета переработок")
        self.setGeometry(100, 100, 1500, 850)

        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Создаем layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Добавляем страницу переработок
        self.overtime_page = OvertimePage()
        layout.addWidget(self.overtime_page)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())