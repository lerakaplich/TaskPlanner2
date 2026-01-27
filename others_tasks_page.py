from PyQt6.QtWidgets import (QWidget, QTableWidgetItem, QPushButton, QFileDialog,
                             QMessageBox, QHeaderView)
from PyQt6.QtCore import QDate, Qt
from PyQt6.uic import loadUi
from create_overtime import CreateOvertimeDialog
from delete_overtime import DeleteOvertimeDialog
import csv


class OvertimePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("overtime_page.ui", self)

        # Мок-данные (в будущем замените на запросы к БД)
        self.projects = [
            {"id": 1, "name": "Разработка кабины"},
            {"id": 2, "name": "Внедрение ERP"}
        ]
        self.tasks = [
            {"id": 1, "project_id": 1, "title": "Прототипирование"},
            {"id": 2, "project_id": 1, "title": "Тестирование"},
            {"id": 3, "project_id": 2, "title": "Настройка модулей"}
        ]
        self.overtimes = [
            {"id": 1, "task_id": 1, "date": QDate(2026, 1, 10), "start": "18:00", "end": "22:00", "duration": 4.0},
            {"id": 2, "task_id": 2, "date": QDate(2026, 1, 15), "start": "19:30", "end": "23:00", "duration": 3.5}
        ]

        self.setup_ui()
        self.load_projects()
        self.load_overtimes()
        self.connect_signals()

    def setup_ui(self):
        # Корпоративные стили кнопок
        golden_style = """
            QPushButton {
                background-color: #ccab6e; color: white; border-radius: 10px;
                font-weight: bold; font-size: 18px; border: none;
            }
            QPushButton:hover { background-color: #998664; }
            QPushButton:pressed { background-color: #7a6a50; }
        """
        gray_style = """
            QPushButton {
                background-color: #1B232A; color: white; border: none;
                border-radius: 10px; padding: 8px 12px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #D9D9D6; color: black; }
            QPushButton:pressed { background-color: #B8B8B5; }
        """
        self.btnAdd.setStyleSheet(golden_style)
        self.btnApply.setStyleSheet(gray_style)
        self.btnExport.setStyleSheet(gray_style)

        # Настройка таблицы
        headers = ["Дата", "Задача", "Начало", "Конец", "Часы", ""]
        self.tableOvertimes.setColumnCount(len(headers))
        self.tableOvertimes.setHorizontalHeaderLabels(headers)

        # Правильная настройка режимов изменения размера столбцов
        header = self.tableOvertimes.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)      # по умолчанию для всех
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)       # растягиваем столбец "Задача"
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)         # фиксируем столбец с кнопкой удаления
        self.tableOvertimes.setColumnWidth(5, 50)  # ширина для иконки мусорки

    def connect_signals(self):
        self.comboProject.currentIndexChanged.connect(self.load_tasks)
        self.btnApply.clicked.connect(self.load_overtimes)
        self.btnAdd.clicked.connect(self.add_overtime)
        self.btnExport.clicked.connect(self.export_overtimes)

    def load_projects(self):
        self.comboProject.clear()
        self.comboProject.addItem("Все проекты", None)
        for proj in self.projects:
            self.comboProject.addItem(proj["name"], proj["id"])

    def load_tasks(self):
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        project_id = self.comboProject.currentData()
        if project_id is None:
            return
        for task in self.tasks:
            if task["project_id"] == project_id:
                self.comboTask.addItem(task["title"], task["id"])

    def load_overtimes(self):
        self.tableOvertimes.setRowCount(0)
        project_id = self.comboProject.currentData()
        task_id = self.comboTask.currentData()
        date_from = self.dateFrom.date()
        date_to = self.dateTo.date()

        for ov in self.overtimes:
            # Получаем project_id задачи
            task_project_id = next((t["project_id"] for t in self.tasks if t["id"] == ov["task_id"]), None)

            # Фильтры
            if project_id and task_project_id != project_id:
                continue
            if task_id and ov["task_id"] != task_id:
                continue
            if ov["date"] < date_from or ov["date"] > date_to:
                continue

            task_title = next(t["title"] for t in self.tasks if t["id"] == ov["task_id"])

            row = self.tableOvertimes.rowCount()
            self.tableOvertimes.insertRow(row)
            self.tableOvertimes.setItem(row, 0, QTableWidgetItem(ov["date"].toString("dd.MM.yyyy")))
            self.tableOvertimes.setItem(row, 1, QTableWidgetItem(task_title))
            self.tableOvertimes.setItem(row, 2, QTableWidgetItem(ov["start"]))
            self.tableOvertimes.setItem(row, 3, QTableWidgetItem(ov["end"]))
            self.tableOvertimes.setItem(row, 4, QTableWidgetItem(str(ov["duration"])))

            delete_btn = QPushButton("🗑")
            delete_btn.setStyleSheet("""
                QPushButton { background-color: #D22730; color: white; border-radius: 6px; padding: 4px; }
                QPushButton:hover { background-color: #862633; }
            """)
            delete_btn.clicked.connect(lambda checked, oid=ov["id"]: self.delete_overtime(oid))
            self.tableOvertimes.setCellWidget(row, 5, delete_btn)

    def add_overtime(self):
        dialog = CreateOvertimeDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data:
                new_id = max((o["id"] for o in self.overtimes), default=0) + 1
                self.overtimes.append({
                    "id": new_id,
                    "task_id": data["task_id"],
                    "date": data["date"],
                    "start": data["start"],
                    "end": data["end"],
                    "duration": data["duration"]
                })
                self.load_overtimes()

    def delete_overtime(self, overtime_id):
        dialog = DeleteOvertimeDialog(self, overtime_id)
        if dialog.exec():
            self.overtimes = [o for o in self.overtimes if o["id"] != overtime_id]
            self.load_overtimes()

    def export_overtimes(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Экспорт в CSV", "", "CSV (*.csv)")
        if not file_name:
            return
        with open(file_name, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Дата", "Задача", "Начало", "Конец", "Часы"])
            # Можно применить те же фильтры, что и в load_overtimes
            for ov in self.overtimes:
                task_title = next(t["title"] for t in self.tasks if t["id"] == ov["task_id"])
                writer.writerow([ov["date"].toString("dd.MM.yyyy"), task_title, ov["start"], ov["end"], ov["duration"]])
        QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы!")