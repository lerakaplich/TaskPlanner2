import os
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem,
    QMessageBox, QDialog
)
from PyQt6.QtCore import QDate, QTime
from PyQt6.uic import loadUi
from openpyxl import Workbook


class OvertimePage(QWidget):

    def __init__(self, current_user="Иванов И.И.", parent=None):
        super().__init__(parent)

        self.current_user = current_user
        self.overtimes = []

        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "overtime_page.ui"), self)
        self.btnAdd.clicked.connect(self.open_add_dialog)
        self.btnExportExcel.clicked.connect(self.open_export_dialog)

    # ---------------- ADD -----------------

    def open_add_dialog(self):
        dlg = QDialog(self)

        loadUi(os.path.join(self.ui_path, "add_dialog.ui"), dlg)

        dlg.projectBox.addItems(["CRM", "ERP", "Website"])
        dlg.taskBox.addItems(["Авторизация", "Отчеты", "Дизайн"])

        dlg.dateEdit.setDate(QDate.currentDate())
        dlg.startTime.setTime(QTime.currentTime())
        dlg.endTime.setTime(QTime.currentTime().addSecs(3600))

        dlg.btnCancel.clicked.connect(dlg.reject)
        dlg.btnSave.clicked.connect(lambda: self.save_from_dialog(dlg))

        dlg.exec()

    def save_from_dialog(self, dlg):
        start = dlg.startTime.time()
        end = dlg.endTime.time()

        if end <= start:
            QMessageBox.warning(self, "Ошибка", "Неверное время")
            return

        hours = round(start.secsTo(end) / 3600, 2)

        self.overtimes.append({
            "user": self.current_user,
            "project": dlg.projectBox.currentText(),
            "task": dlg.taskBox.currentText(),
            "date": dlg.dateEdit.date().toString("dd.MM.yyyy"),
            "start": start.toString("HH:mm"),
            "end": end.toString("HH:mm"),
            "hours": hours,
            "description": dlg.descEdit.text()
        })

        dlg.accept()
        self.refresh_table()

    # ---------------- TABLE -----------------

    def refresh_table(self):
        self.overtimeTable.setRowCount(0)

        for r in self.overtimes:
            row = self.overtimeTable.rowCount()
            self.overtimeTable.insertRow(row)

            self.overtimeTable.setItem(row,0,QTableWidgetItem(r["user"]))
            self.overtimeTable.setItem(row,1,QTableWidgetItem(r["project"]))
            self.overtimeTable.setItem(row,2,QTableWidgetItem(r["task"]))
            self.overtimeTable.setItem(row,3,QTableWidgetItem(r["date"]))
            self.overtimeTable.setItem(row,4,QTableWidgetItem(r["start"]))
            self.overtimeTable.setItem(row,5,QTableWidgetItem(r["end"]))
            self.overtimeTable.setItem(row,6,QTableWidgetItem(str(r["hours"])))
            self.overtimeTable.setItem(row,7,QTableWidgetItem(r["description"]))

    # ---------------- EXPORT -----------------

    def open_export_dialog(self):
        dlg = QDialog(self)

        loadUi(os.path.join(self.ui_path, "export_period_dialog.ui"), dlg)

        dlg.dateFrom.setDate(QDate.currentDate().addDays(-30))
        dlg.dateTo.setDate(QDate.currentDate())

        dlg.btnCancel.clicked.connect(dlg.reject)
        dlg.btnOk.clicked.connect(lambda: self.export_excel(dlg))

        dlg.exec()

    def export_excel(self, dlg):

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", "", "Excel (*.xlsx)"
        )

        if not path:
            return

        date_from = dlg.dateFrom.date()
        date_to = dlg.dateTo.date()

        wb = Workbook()
        ws = wb.active

        ws.append(["Сотрудник","Проект","Задача",
                   "Дата","Начало","Конец","Часы","Описание"])

        for r in self.overtimes:
            d = QDate.fromString(r["date"], "dd.MM.yyyy")
            if d < date_from or d > date_to:
                continue

            ws.append([
                r["user"], r["project"], r["task"],
                r["date"], r["start"], r["end"],
                r["hours"], r["description"]
            ])

        wb.save(path)
        dlg.accept()

        QMessageBox.information(self,"Готово","Экспорт завершен")
