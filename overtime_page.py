import sys
from PyQt6.QtWidgets import QWidget, QTableWidgetItem
from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.uic import loadUi
from datetime import datetime

# Мок-данные (замените на реальные запросы к БД)
MOCK_PROJECTS = [
    {"id": 1, "name": "Разработка новой кабины"},
    {"id": 2, "name": "Внедрение ERP-системы"},
    {"id": 3, "name": "Модернизация конвейера"},
]

MOCK_TASKS = {
    1: [{"id": 101, "name": "Проектирование каркаса"}, {"id": 102, "name": "Тестирование прототипа"}],
    2: [{"id": 201, "name": "Настройка модулей"}, {"id": 202, "name": "Миграция данных"}],
    3: [{"id": 301, "name": "Замена оборудования"}, {"id": 302, "name": "Калибровка"}],
}

class OvertimePage(QWidget):
    def __init__(self):
        super().__init__()
        loadUi("overtime_page.ui", self)

        self.projects = MOCK_PROJECTS
        self.tasks_by_project = MOCK_TASKS
        self.overtimes = []  # Здесь будут записи

        self.setup_ui()
        self.connect_signals()
        self.populate_projects()
        self.populate_filter_projects()
        self.load_overtimes()

    def setup_ui(self):
        # Начальные значения
        self.dateEdit.setDate(QDate.currentDate())
        self.startTime.setTime(QTime(18, 0))
        self.endTime.setTime(QTime(20, 0))
        self.filterFromDate.setDate(QDate.currentDate().addMonths(-1))
        self.filterToDate.setDate(QDate.currentDate())

        # Настройка таблицы
        headers = ["ID", "Дата", "Проект", "Задача", "Начало", "Конец", "Часы", "Описание"]
        self.overtimeTable.setColumnCount(len(headers))
        self.overtimeTable.setHorizontalHeaderLabels(headers)
        self.overtimeTable.horizontalHeader().setStretchLastSection(True)

    def connect_signals(self):
        self.projectCombo.currentIndexChanged.connect(self.on_project_changed)
        self.filterProjectCombo.currentIndexChanged.connect(self.on_filter_project_changed)
        self.addButton.clicked.connect(self.add_overtime)
        self.applyFilterButton.clicked.connect(self.load_overtimes)

    def populate_projects(self):
        self.projectCombo.clear()
        self.projectCombo.addItem("— Выберите проект —", None)
        for p in self.projects:
            self.projectCombo.addItem(p["name"], p["id"])

    def populate_filter_projects(self):
        self.filterProjectCombo.clear()
        self.filterProjectCombo.addItem("Все проекты", None)
        for p in self.projects:
            self.filterProjectCombo.addItem(p["name"], p["id"])

    def on_project_changed(self):
        project_id = self.projectCombo.currentData()
        self.taskCombo.clear()
        if project_id:
            self.taskCombo.addItem("— Выберите задачу —", None)
            for t in self.tasks_by_project.get(project_id, []):
                self.taskCombo.addItem(t["name"], t["id"])
        else:
            self.taskCombo.addItem("Сначала выберите проект", None)

    def on_filter_project_changed(self):
        project_id = self.filterProjectCombo.currentData()
        self.filterTaskCombo.clear()
        self.filterTaskCombo.addItem("Все задачи", None)
        if project_id:
            for t in self.tasks_by_project.get(project_id, []):
                self.filterTaskCombo.addItem(t["name"], t["id"])

    def add_overtime(self):
        project_id = self.projectCombo.currentData()
        task_id = self.taskCombo.currentData()
        if not (project_id and task_id):
            return  # Можно добавить QMessageBox

        # Расчёт часов
        start = self.startTime.time()
        end = self.endTime.time()
        seconds = start.secsTo(end)
        if seconds < 0:
            seconds += 24 * 3600
        hours = round(seconds / 3600.0, 2)

        project_name = self.projectCombo.currentText()
        task_name = self.taskCombo.currentText()

        new_record = {
            "id": len(self.overtimes) + 1,
            "date": self.dateEdit.date().toString("dd.MM.yyyy"),
            "project": project_name,
            "project_id": project_id,
            "task": task_name,
            "task_id": task_id,
            "start": start.toString("HH:mm"),
            "end": end.toString("HH:mm"),
            "hours": hours,
            "note": self.noteEdit.toPlainText() or "—"
        }

        self.overtimes.append(new_record)
        self.noteEdit.clear()
        self.load_overtimes()

    def load_overtimes(self):
        self.overtimeTable.setRowCount(0)

        f_project = self.filterProjectCombo.currentData()
        f_task = self.filterTaskCombo.currentData()
        f_from = self.filterFromDate.date().toPyDate()
        f_to = self.filterToDate.date().toPyDate()

        for ot in self.overtimes:
            ot_date = datetime.strptime(ot["date"], "%d.%m.%Y").date()

            if f_project and ot["project_id"] != f_project:
                continue
            if f_task and ot["task_id"] != f_task:
                continue
            if not (f_from <= ot_date <= f_to):
                continue

            row = self.overtimeTable.rowCount()
            self.overtimeTable.insertRow(row)
            self.overtimeTable.setItem(row, 0, QTableWidgetItem(str(ot["id"])))
            self.overtimeTable.setItem(row, 1, QTableWidgetItem(ot["date"]))
            self.overtimeTable.setItem(row, 2, QTableWidgetItem(ot["project"]))
            self.overtimeTable.setItem(row, 3, QTableWidgetItem(ot["task"]))
            self.overtimeTable.setItem(row, 4, QTableWidgetItem(ot["start"]))
            self.overtimeTable.setItem(row, 5, QTableWidgetItem(ot["end"]))
            self.overtimeTable.setItem(row, 6, QTableWidgetItem(str(ot["hours"])))
            self.overtimeTable.setItem(row, 7, QTableWidgetItem(ot["note"]))

        if self.overtimeTable.rowCount() == 0:
            row = self.overtimeTable.rowCount()
            self.overtimeTable.insertRow(row)
            item = QTableWidgetItem("Нет записей по выбранным фильтрам")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.overtimeTable.setItem(row, 0, item)
            self.overtimeTable.setSpan(row, 0, 1, 8)