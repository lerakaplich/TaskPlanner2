# windows/overtime/overtime_page.py

import os
from typing import List, Dict, Optional

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog
from PyQt6 import uic

from windows.overtime.overtime_card import OvertimeCard
from windows.overtime.add_overtime_dialog import AddOvertimeDialog
from windows.overtime.period_dialog import PeriodDialog
from services.excel_export_service import ExcelExportService  # 👈 ДОБАВЛЯЕМ ИМПОРТ


class OvertimePage(QWidget):
    """UI-страница переработок"""

    def __init__(self, service=None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "overtime_page.ui"), self)

        # Сервис с бизнес-логикой
        self.service = service
        # 👇 СОЗДАЕМ СЕРВИС ЭКСПОРТА
        self.excel_export = ExcelExportService()

        # Данные
        self.my_overtimes: List[Dict] = []
        self.all_overtimes: List[Dict] = []

        # Текущие фильтры
        self.current_project_filter: Optional[str] = None
        self.current_task_filter: Optional[str] = None
        self.current_start_date: Optional[QDate] = None
        self.current_end_date: Optional[QDate] = None

        # Подключаем кнопки
        self.btnAddOvertime.clicked.connect(self.show_add_overtime)
        self.btnExport.clicked.connect(self.show_export_dialog)
        self.btnApplyFilters.clicked.connect(self.apply_filters)
        self.btnClearFilters.clicked.connect(self.clear_filters)
        self.btnSelectPeriod.clicked.connect(self.select_period)
        self.comboProject.currentIndexChanged.connect(self.on_project_changed)

        # Инициализация фильтров и загрузка данных
        self.init_filters()
        self.load_overtimes()

    # ========================
    # Загрузка данных
    # ========================
    def load_overtimes(self):
        """Загружает переработки из БД через сервис"""
        if self.service:
            self.my_overtimes, self.all_overtimes = self.service.load_overtimes()
            self.display_overtimes()
            print(f"✅ Загружено переработок: моих {len(self.my_overtimes)}, всего {len(self.all_overtimes)}")

    # ========================
    # UI функции
    # ========================
    def init_filters(self):
        """Инициализация фильтров"""
        self.comboProject.clear()
        self.comboProject.addItem("Все переработки", None)

        if self.service:
            projects = self.service.get_projects()
            for project in projects:
                self.comboProject.addItem(project['name'], project['name'])

        self.comboProject.setCurrentIndex(0)
        self.comboProject.setEnabled(True)

        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        self.comboTask.setEnabled(False)

    def on_project_changed(self, index):
        """Обработчик изменения выбранного проекта"""
        project_name = self.comboProject.currentData()

        if project_name is None:
            # Если выбран "Все переработки"
            self.comboTask.setEnabled(False)
            self.comboTask.clear()
            self.comboTask.addItem("Все задачи", None)
            return

        # Загружаем уникальные задачи для выбранного проекта из переработок
        self.load_project_tasks(project_name)

    def load_project_tasks(self, project_name: str):
        """Загружает задачи для выбранного проекта из существующих переработок"""
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)

        # Собираем уникальные задачи из переработок этого проекта
        tasks = set()
        for ot in self.all_overtimes:
            if ot.get('project') == project_name and ot.get('task'):
                tasks.add(ot['task'])

        for task in sorted(tasks):
            self.comboTask.addItem(task, task)

        self.comboTask.setEnabled(True)
        self.comboTask.setCurrentIndex(0)

    def update_tasks_from_all(self):
        """Обновляет список задач из всех переработок"""
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)

        # Собираем все уникальные задачи
        tasks = set()
        for ot in self.all_overtimes:
            if ot.get('task'):
                tasks.add(ot['task'])

        for task in sorted(tasks):
            self.comboTask.addItem(task, task)

    def clear_filters(self):
        """Сбрасывает все фильтры"""
        self.comboProject.setCurrentIndex(0)
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        self.comboTask.setEnabled(False)
        self.current_start_date = None
        self.current_end_date = None
        self.display_overtimes()

    def apply_filters(self):
        """Применяет выбранные фильтры"""
        self.current_project_filter = self.comboProject.currentData()
        self.current_task_filter = self.comboTask.currentData() if self.comboTask.isEnabled() else None
        self.display_overtimes()

    def display_overtimes(self):
        """Отображает переработки с учетом фильтров"""
        filters = {}

        if self.current_project_filter:
            filters['project_name'] = self.current_project_filter
        if self.current_task_filter:
            filters['task_title'] = self.current_task_filter
        if self.current_start_date and self.current_end_date:
            filters['start_date'] = self.current_start_date
            filters['end_date'] = self.current_end_date

        # Фильтруем переработки
        filtered_my = self.service.filter_overtimes(self.my_overtimes, **filters) if self.service else self.my_overtimes
        filtered_all = self.service.filter_overtimes(self.all_overtimes,
                                                     **filters) if self.service else self.all_overtimes

        self.display_tab(self.gridLayoutMy, filtered_my)
        self.display_tab(self.gridLayoutAll, filtered_all)

    def display_tab(self, layout, overtimes):
        """Отображает переработки в указанном layout"""
        # Очистка
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Отображение карточек
        for i, ot in enumerate(overtimes):
            card = OvertimeCard(ot)
            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)

    def show_add_overtime(self):
        """Показывает диалог добавления переработки"""
        dialog = AddOvertimeDialog(service=self.service, parent=self)
        if dialog.exec():
            # Получаем данные из диалога
            data = dialog.get_overtime_data()

            # Добавляем через сервис
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
                # Перезагружаем данные
                self.load_overtimes()
                # Обновляем фильтры
                self.update_tasks_from_all()
                QMessageBox.information(self, "Успех", "Переработка добавлена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить переработку")

    # windows/overtime/overtime_page.py

    def show_export_dialog(self):
        """Показывает диалог экспорта"""
        dialog = PeriodDialog(self)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            filters = dialog.get_filters()

            department = filters.get('department')
            division = filters.get('division')

            # Предлагаем путь для сохранения
            default_filename = self.excel_export.generate_filename(
                start_date, end_date, department, division
            )

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчет",
                default_filename,
                "Excel files (*.xlsx)"
            )

            if file_path:
                # Фильтруем переработки по периоду
                filtered_overtimes = self.service.filter_overtimes(
                    self.all_overtimes,
                    start_date=start_date,
                    end_date=end_date
                )

                # Здесь можно добавить фильтрацию по отделу/подразделению
                # если в данных есть информация о сотрудниках

                try:
                    # Экспортируем
                    saved_path = self.excel_export.export_overtimes(
                        overtimes=filtered_overtimes,
                        start_date=start_date,
                        end_date=end_date,
                        file_path=file_path,
                        department=department,
                        division=division
                    )

                    # Показываем сообщение с путем и статистикой
                    total_hours = sum(
                        float(ot['duration'].replace(',', '.'))
                        for ot in filtered_overtimes
                    )

                    QMessageBox.information(
                        self,
                        "Экспорт завершен",
                        f"Файл сохранен:\n{saved_path}\n\n"
                        f"Период: {start_date.toString('dd.MM.yyyy')} - {end_date.toString('dd.MM.yyyy')}\n"
                        f"Отдел: {department if department else 'Все'}\n"
                        f"Подразделение: {division if division else 'Все'}\n"
                        f"Всего переработок: {len(filtered_overtimes)}\n"
                        f"Общее количество часов: {total_hours:.1f}"
                    )

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка экспорта",
                        f"Не удалось сохранить файл:\n{str(e)}"
                    )

    def select_period(self):
        """Выбор периода для фильтрации"""
        dialog = PeriodDialog(self)
        if dialog.exec():
            self.current_start_date, self.current_end_date = dialog.get_period()
            self.display_overtimes()