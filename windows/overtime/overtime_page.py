# windows/overtime/overtime_page.py

import os
from typing import List, Dict, Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog, QProgressDialog, QApplication
from PyQt6 import uic

from windows.overtime.overtime_card import OvertimeCard
from windows.overtime.add_overtime_dialog import AddOvertimeDialog
from windows.overtime.edit_overtime_dialog import EditOvertimeDialog
from windows.overtime.period_dialog import PeriodDialog
from services.overtime_service.overtime_export_service import OvertimeExportService


class OvertimePage(QWidget):
    """UI-страница переработок"""

    def __init__(self, service=None, employee_service=None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "overtime_page.ui"), self)

        self.service = service
        self.excel_export = OvertimeExportService()
        self.employee_service = employee_service

        self.my_overtimes: List[Dict] = []
        self.all_overtimes: List[Dict] = []

        self.current_project_filter: Optional[str] = None
        self.current_task_filter: Optional[str] = None
        self.current_start_date: Optional[QDate] = None
        self.current_end_date: Optional[QDate] = None

        self.btnAddOvertime.clicked.connect(self.show_add_overtime)
        self.btnExport.clicked.connect(self.show_export_dialog)
        self.btnApplyFilters.clicked.connect(self.apply_filters)
        self.btnClearFilters.clicked.connect(self.clear_filters)
        self.btnSelectPeriod.clicked.connect(self.select_period)
        self.comboProject.currentIndexChanged.connect(self.on_project_changed)

        if hasattr(self, 'btnImport'):
            self.btnImport.clicked.connect(self.show_import_dialog)

        self.init_filters()
        self.load_overtimes()

    def load_overtimes(self):
        if self.service:
            self.my_overtimes, self.all_overtimes = self.service.load_overtimes()
            self.display_overtimes()
            self._update_total_hours()

    def _update_total_hours(self):
        if hasattr(self, 'totalHoursValue') and self.service:
            total = self.service.crud.get_total_hours(self.my_overtimes)
            self.totalHoursValue.setText(f"{total:.1f}")

    def show_import_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл для импорта переработок", "", "Excel files (*.xlsx *.xls)"
        )
        if not file_path:
            return

        progress = QProgressDialog("Импорт переработок...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(True)
        progress.show()

        def update_progress(value, text):
            progress.setValue(value)
            progress.setLabelText(text)
            QApplication.processEvents()

        try:
            result = self.service.import_overtimes_from_file(file_path, update_progress)
            progress.setValue(100)

            if result['imported'] > 0:
                QMessageBox.information(self, "Импорт завершён",
                                        f"✅ Импортировано: {result['imported']}\n"
                                        f"⚠️ Дубликатов: {result['duplicates']}\n"
                                        f"⏭️ Пропущено: {result['skipped']}\n"
                                        f"❌ Ошибок: {result['errors']}")
                self.load_overtimes()
            else:
                error_msg = "\n".join(result['error_details'][:5])
                QMessageBox.warning(self, "Импорт не выполнен", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            progress.close()

    def init_filters(self):
        self.comboProject.clear()
        self.comboProject.addItem("Все переработки", None)
        if self.service:
            projects = self.service.get_projects()
            for project in projects:
                self.comboProject.addItem(project['name'], project['name'])
        self.comboProject.setCurrentIndex(0)

        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        self.comboTask.setEnabled(False)

    def on_project_changed(self, index):
        project_name = self.comboProject.currentData()
        if project_name is None:
            self.comboTask.setEnabled(False)
            self.comboTask.clear()
            self.comboTask.addItem("Все задачи", None)
            return
        self.load_project_tasks(project_name)

    def load_project_tasks(self, project_name: str):
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        tasks = set()
        for ot in self.all_overtimes:
            if ot.get('project') == project_name and ot.get('task'):
                tasks.add(ot['task'])
        for task in sorted(tasks):
            self.comboTask.addItem(task, task)
        self.comboTask.setEnabled(True)
        self.comboTask.setCurrentIndex(0)

    def update_tasks_from_all(self):
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        tasks = set()
        for ot in self.all_overtimes:
            if ot.get('task'):
                tasks.add(ot['task'])
        for task in sorted(tasks):
            self.comboTask.addItem(task, task)

    def clear_filters(self):
        self.comboProject.setCurrentIndex(0)
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        self.comboTask.setEnabled(False)
        self.current_start_date = None
        self.current_end_date = None
        self.display_overtimes()
        self._update_total_hours()

    def apply_filters(self):
        self.current_project_filter = self.comboProject.currentData()
        self.current_task_filter = self.comboTask.currentData() if self.comboTask.isEnabled() else None
        self.display_overtimes()
        self._update_total_hours()

    def display_overtimes(self):
        filters = {}
        if self.current_project_filter:
            filters['project_name'] = self.current_project_filter
        if self.current_task_filter:
            filters['task_title'] = self.current_task_filter
        if self.current_start_date and self.current_end_date:
            filters['start_date'] = self.current_start_date
            filters['end_date'] = self.current_end_date

        filtered_my = self.service.filter_overtimes(self.my_overtimes, **filters) if self.service else self.my_overtimes
        filtered_all = self.service.filter_overtimes(self.all_overtimes,
                                                     **filters) if self.service else self.all_overtimes

        self._display_tab(self.gridLayoutMy, filtered_my)
        self._display_tab(self.gridLayoutAll, filtered_all)
        self._update_total_hours_display(filtered_my)

    def _update_total_hours_display(self, overtimes: List[Dict]):
        if hasattr(self, 'totalHoursValue') and self.service:
            total = self.service.crud.get_total_hours(overtimes)
            self.totalHoursValue.setText(f"{total:.1f}")

    def _display_tab(self, layout, overtimes):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, ot in enumerate(overtimes):
            card = OvertimeCard(ot)
            card.edit_clicked.connect(self.show_edit_overtime)
            card.add_details_clicked.connect(self.show_add_details_overtime)
            card.delete_clicked.connect(self.delete_overtime)
            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)

    def show_add_details_overtime(self, overtime_id: int):
        overtime = self.service.get_overtime_by_id(overtime_id)
        if not overtime:
            QMessageBox.warning(self, "Ошибка", "Переработка не найдена")
            return

        dialog = EditOvertimeDialog(service=self.service, overtime_data=overtime, parent=self)
        if dialog.exec():
            self.load_overtimes()
            QMessageBox.information(self, "Успех", "Данные переработки добавлены")

    def show_edit_overtime(self, overtime_id: int):
        overtime = self.service.get_overtime_by_id(overtime_id)
        if not overtime:
            QMessageBox.warning(self, "Ошибка", "Переработка не найдена")
            return

        dialog = EditOvertimeDialog(service=self.service, overtime_data=overtime, parent=self)
        if dialog.exec():
            self.load_overtimes()
            QMessageBox.information(self, "Успех", "Переработка обновлена")

    def delete_overtime(self, overtime_id: int):
        reply = QMessageBox.question(
            self, "Удаление переработки",
            "Вы уверены, что хотите удалить эту переработку?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.service.delete_overtime(overtime_id):
                self.load_overtimes()
                QMessageBox.information(self, "Успех", "Переработка удалена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить переработку")

    def show_add_overtime(self):
        dialog = AddOvertimeDialog(service=self.service, parent=self)
        if dialog.exec():
            data = dialog.get_overtime_data()
            new_ot = self.service.add_overtime(
                date=data['date'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                description=data['description'],
                employee_id=data['employee_id'],
                project_id=data['project_id'],
                task_id=data['task_id']
            )
            if new_ot:
                self.load_overtimes()
                self.update_tasks_from_all()
                QMessageBox.information(self, "Успех", "Переработка добавлена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить переработку")

    def show_export_dialog(self):
        dialog = PeriodDialog(self, employee_service=self.employee_service)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            filters = dialog.get_filters()
            department = filters.get('department')
            division = filters.get('division')

            filename = self.excel_export.generate_filename(start_date, end_date, department, division)
            file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", filename, "Excel files (*.xlsx)")

            if file_path:
                all_notes = self.service.load_overtimes()[1] if self.service else []
                filtered = self.service.crud.get_filtered_overtimes_for_export(
                    all_notes, start_date, end_date, division, department, self.employee_service
                )

                try:
                    self.excel_export.export_overtimes(filtered, start_date, end_date, file_path, department, division)
                    total_hours = sum(float(ot['duration'].replace(',', '.')) for ot in filtered)
                    QMessageBox.information(self, "Экспорт завершен",
                                            f"Файл сохранен:\n{file_path}\n\n"
                                            f"Период: {start_date.toString('dd.MM.yyyy')} - {end_date.toString('dd.MM.yyyy')}\n"
                                            f"Отдел: {department if department else 'Все'}\n"
                                            f"Подразделение: {division if division else 'Все'}\n"
                                            f"Всего переработок: {len(filtered)}\n"
                                            f"Общее количество часов: {total_hours:.1f}")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить файл:\n{str(e)}")

    def select_period(self):
        dialog = PeriodDialog(self, employee_service=self.employee_service)
        if dialog.exec():
            self.current_start_date, self.current_end_date = dialog.get_period()
            self.display_overtimes()
            self._update_total_hours()