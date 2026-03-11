# windows/overtime/overtime_page.py

import os
from typing import List, Dict
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6 import uic

from windows.overtime.overtime_card import OvertimeCard
from windows.overtime.add_overtime_dialog import AddOvertimeDialog
from windows.overtime.period_dialog import PeriodDialog


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

        # Данные
        self.my_overtimes: List[Dict] = []
        self.all_overtimes: List[Dict] = []

        # Подключаем кнопки
        self.btnAddOvertime.clicked.connect(self.show_add_overtime)
        self.btnExport.clicked.connect(self.show_export_dialog)
        self.btnApplyFilters.clicked.connect(self.apply_filters)
        self.btnClearFilters.clicked.connect(self.clear_filters)
        self.btnSelectPeriod.clicked.connect(self.select_period)
        self.comboProject.currentIndexChanged.connect(self.update_tasks)

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
        self.comboProject.clear()
        # В employee_notes пока нет проектов, поэтому фильтр отключен
        self.comboProject.addItem("Все переработки", None)
        self.comboProject.setCurrentIndex(0)
        self.comboProject.setEnabled(False)

        self.comboTask.clear()
        self.comboTask.setCurrentIndex(-1)
        self.comboTask.setEnabled(False)

    def update_tasks(self):
        # Заглушка, т.к. в employee_notes нет задач
        pass

    def clear_filters(self):
        # Сбрасываем фильтры
        self.comboProject.setCurrentIndex(0)
        self.display_overtimes()

    def apply_filters(self):
        self.display_overtimes()

    def display_overtimes(self):
        """Отображает переработки с учетом фильтров"""
        # Получаем выбранный период из диалога (если есть)
        # В реальном приложении нужно хранить выбранные даты
        filtered_my = self.service.filter_overtimes(self.my_overtimes) if self.service else self.my_overtimes
        filtered_all = self.service.filter_overtimes(self.all_overtimes) if self.service else self.all_overtimes

        self.display_tab(self.gridLayoutMy, filtered_my)
        self.display_tab(self.gridLayoutAll, filtered_all)

    def display_tab(self, layout, overtimes):
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

    # windows/overtime/overtime_page.py

    def show_add_overtime(self):
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
                QMessageBox.information(self, "Успех", "Переработка добавлена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить переработку")

    def show_export_dialog(self):
        dialog = PeriodDialog(self)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            QMessageBox.information(
                self,
                "Экспорт",
                f"Экспорт данных за период:\nс {start_date.toString('dd.MM.yyyy')} "
                f"по {end_date.toString('dd.MM.yyyy')}"
            )

    def select_period(self):
        dialog = PeriodDialog(self)
        if dialog.exec():
            start_date, end_date = dialog.get_period()
            # Фильтруем данные по периоду
            if self.service:
                filtered_my = self.service.filter_overtimes(
                    self.my_overtimes,
                    start_date=start_date,
                    end_date=end_date
                )
                filtered_all = self.service.filter_overtimes(
                    self.all_overtimes,
                    start_date=start_date,
                    end_date=end_date
                )
                self.display_tab(self.gridLayoutMy, filtered_my)
                self.display_tab(self.gridLayoutAll, filtered_all)