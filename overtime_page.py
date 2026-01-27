import sys
from datetime import datetime, date, time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QDateEdit, QTableView,
    QListWidget, QStackedWidget, QFrame, QMessageBox,
    QHeaderView, QListWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.uic import loadUi
from create_overtime import CreateOvertimeDialog
from delete_overtime import DeleteOvertimeDialog


class OvertimePage(QWidget):
    data_changed = pyqtSignal()  # Сигнал при изменении данных

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("overtime_page.ui", self)

        # Инициализация
        self.setup_ui()
        self.load_overtime_data()
        self.connect_signals()

        # Устанавливаем текущую дату по умолчанию
        today = QDate.currentDate()
        self.dateStart.setDate(today.addMonths(-1))
        self.dateEnd.setDate(today)

        # Создаем группу для кнопок режима просмотра
        self.view_mode_group = [self.btnTableView, self.btnListView]
        self.btnTableView.toggled.connect(self.on_view_mode_changed)
        self.btnListView.toggled.connect(self.on_view_mode_changed)

        # Устанавливаем табличный вид по умолчанию
        self.btnTableView.setChecked(True)

    def setup_ui(self):
        """Настройка интерфейса"""
        # Стили для кнопок
        red_style = """
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #862633;
            }
            QPushButton:pressed {
                background-color: #6a1e29;
            }
        """

        golden_style = """
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
        """

        gray_style = """
            QPushButton {
                background-color: #1B232A;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
            QPushButton:pressed {
                background-color: #B8B8B5;
            }
        """

        # Применяем стили
        self.btnApply.setStyleSheet(red_style)
        self.btnExport.setStyleSheet(golden_style)
        self.btnAddOvertime.setStyleSheet(gray_style)

        # Стиль для кнопок режима просмотра
        view_mode_style = """
            QPushButton {
                background-color: #F0F0F0;
                color: #1B232A;
                border-radius: 5px;
                border: 1px solid #CCCCCC;
                padding: 5px 15px;
                font-size: 13px;
            }
            QPushButton:checked {
                background-color: #1B232A;
                color: white;
                border: 1px solid #1B232A;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """
        self.btnTableView.setStyleSheet(view_mode_style)
        self.btnListView.setStyleSheet(view_mode_style)

        # Настраиваем таблицу
        self.model = QStandardItemModel(0, 7)
        self.model.setHorizontalHeaderLabels([
            "Дата", "Проект", "Задача", "Начало", "Окончание", "Часы", ""
        ])
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableView.setColumnWidth(6, 50)  # Для кнопки удаления
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Настраиваем список
        self.listWidget.setSpacing(5)

        # Настраиваем комбобоксы
        self.comboProject.addItem("Все проекты", None)
        self.comboTask.addItem("Все задачи", None)

        # Загружаем тестовые проекты
        self.load_test_projects()

    def load_test_projects(self):
        """Загрузка тестовых данных проектов и задач"""
        projects = [
            {"id": 1, "name": "Разработка новой кабины"},
            {"id": 2, "name": "Внедрение ERP-системы"},
            {"id": 3, "name": "Модернизация конвейера"},
            {"id": 4, "name": "Разработка сайта"}
        ]

        tasks = {
            1: ["Дизайн интерфейса", "Разработка API", "Тестирование"],
            2: ["Анализ требований", "Настройка серверов", "Миграция данных"],
            3: ["Закупка оборудования", "Монтаж", "Пуско-наладочные работы"],
            4: ["Верстка", "Бэкенд", "Деплой"]
        }

        for project in projects:
            self.comboProject.addItem(project["name"], project["id"])

        self.comboProject.currentIndexChanged.connect(self.update_tasks_combo)
        self.update_tasks_combo()

    def update_tasks_combo(self):
        """Обновление списка задач при выборе проекта"""
        project_id = self.comboProject.currentData()
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)

        if project_id:
            tasks = {
                1: ["Дизайн интерфейса", "Разработка API", "Тестирование"],
                2: ["Анализ требований", "Настройка серверов", "Миграция данных"],
                3: ["Закупка оборудования", "Монтаж", "Пуско-наладочные работы"],
                4: ["Верстка", "Бэкенд", "Деплой"]
            }.get(project_id, [])

            for i, task in enumerate(tasks):
                self.comboTask.addItem(task, f"{project_id}_{i}")

    def load_overtime_data(self):
        """Загрузка данных переработок"""
        # Тестовые данные
        test_data = [
            {
                "id": 1,
                "date": date(2024, 1, 15),
                "project": "Разработка новой кабины",
                "task": "Дизайн интерфейса",
                "start": time(18, 0),
                "end": time(21, 30),
                "hours": 3.5,
                "note": "Доработка UI компонентов"
            },
            {
                "id": 2,
                "date": date(2024, 1, 16),
                "project": "Внедрение ERP-системы",
                "task": "Миграция данных",
                "start": time(19, 0),
                "end": time(23, 0),
                "hours": 4.0,
                "note": "Перенос данных клиентов"
            },
            {
                "id": 3,
                "date": date(2024, 1, 18),
                "project": "Модернизация конвейера",
                "task": "Пуско-наладочные работы",
                "start": time(17, 30),
                "end": time(22, 0),
                "hours": 4.5,
                "note": "Наладка оборудования"
            }
        ]

        self.overtime_data = test_data
        self.update_display()

    def update_display(self):
        """Обновление отображения данных"""
        self.update_table_view()
        self.update_list_view()
        self.update_total_hours()

    def update_table_view(self):
        """Обновление табличного представления"""
        self.model.removeRows(0, self.model.rowCount())

        for item in self.get_filtered_data():
            row = [
                QStandardItem(item["date"].strftime("%d.%m.%Y")),
                QStandardItem(item["project"]),
                QStandardItem(item["task"]),
                QStandardItem(item["start"].strftime("%H:%M")),
                QStandardItem(item["end"].strftime("%H:%M")),
                QStandardItem(str(item["hours"])),
                QStandardItem("🗑️")
            ]

            for i, cell in enumerate(row):
                cell.setEditable(False)
                if i == 6:  # Кнопка удаления
                    cell.setData(item["id"], Qt.ItemDataRole.UserRole)

            self.model.appendRow(row)

    def update_list_view(self):
        """Обновление спискового представления"""
        self.listWidget.clear()

        for item in self.get_filtered_data():
            list_item = QListWidgetItem()
            widget = self.create_list_item_widget(item)
            list_item.setSizeHint(widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.listWidget.addItem(list_item)
            self.listWidget.setItemWidget(list_item, widget)

    def create_list_item_widget(self, item):
        """Создание виджета для элемента списка"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)

        # Информация
        info_label = QLabel(
            f"{item['date'].strftime('%d.%m.%Y')} | "
            f"{item['project']} - {item['task']} | "
            f"{item['start'].strftime('%H:%M')}-{item['end'].strftime('%H:%M')} | "
            f"{item['hours']} часов"
        )
        info_label.setStyleSheet("font-size: 14px;")

        # Кнопка удаления
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #862633;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_overtime(item["id"]))

        layout.addWidget(info_label)
        layout.addStretch()
        layout.addWidget(delete_btn)

        widget.setLayout(layout)
        return widget

    def get_filtered_data(self):
        """Получение отфильтрованных данных"""
        filtered_data = self.overtime_data.copy()

        # Фильтр по проекту
        project_id = self.comboProject.currentData()
        if project_id:
            project_name = self.comboProject.currentText()
            filtered_data = [d for d in filtered_data if d["project"] == project_name]

        # Фильтр по задаче
        task_id = self.comboTask.currentData()
        if task_id and project_id:
            task_name = self.comboTask.currentText()
            filtered_data = [d for d in filtered_data if d["task"] == task_name]

        # Фильтр по дате
        start_date = self.dateStart.date().toPyDate()
        end_date = self.dateEnd.date().toPyDate()
        filtered_data = [
            d for d in filtered_data
            if start_date <= d["date"] <= end_date
        ]

        return filtered_data

    def update_total_hours(self):
        """Обновление общего количества часов"""
        total = sum(item["hours"] for item in self.get_filtered_data())
        self.labelTotal.setText(f"Итого за период: {total} часов")

    def connect_signals(self):
        """Подключение сигналов"""
        self.btnApply.clicked.connect(self.apply_filters)
        self.btnExport.clicked.connect(self.export_data)
        self.btnAddOvertime.clicked.connect(self.add_overtime)
        self.tableView.clicked.connect(self.on_table_clicked)

    def on_view_mode_changed(self, checked):
        """Обработка изменения режима просмотра"""
        if not checked:
            return

        if self.btnTableView.isChecked():
            self.stackedWidget.setCurrentIndex(0)
        else:
            self.stackedWidget.setCurrentIndex(1)

    def on_table_clicked(self, index):
        """Обработка клика по таблице"""
        if index.column() == 6:  # Колонка удаления
            item_id = self.model.item(index.row(), 6).data(Qt.ItemDataRole.UserRole)
            self.delete_overtime(item_id)

    def apply_filters(self):
        """Применение фильтров"""
        self.update_display()

    def export_data(self):
        """Экспорт данных"""
        from datetime import datetime
        import csv
        from PyQt6.QtWidgets import QFileDialog

        # Выбор файла для сохранения
        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт данных", "", "CSV Files (*.csv)"
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['Дата', 'Проект', 'Задача', 'Начало', 'Окончание', 'Часы', 'Примечание'])

                    for item in self.get_filtered_data():
                        writer.writerow([
                            item["date"].strftime("%d.%m.%Y"),
                            item["project"],
                            item["task"],
                            item["start"].strftime("%H:%M"),
                            item["end"].strftime("%H:%M"),
                            item["hours"],
                            item.get("note", "")
                        ])

                QMessageBox.information(self, "Успех", "Данные успешно экспортированы!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать данные: {str(e)}")

    def add_overtime(self):
        """Добавление новой переработки"""
        dialog = CreateOvertimeDialog(self)
        if dialog.exec():
            new_overtime = dialog.get_overtime_data()
            new_overtime["id"] = len(self.overtime_data) + 1
            self.overtime_data.append(new_overtime)
            self.update_display()
            self.data_changed.emit()

    def delete_overtime(self, overtime_id):
        """Удаление переработки"""
        dialog = DeleteOvertimeDialog(self)
        if dialog.exec():
            # Удаляем из данных
            self.overtime_data = [d for d in self.overtime_data if d["id"] != overtime_id]
            self.update_display()
            self.data_changed.emit()

    def refresh_data(self):
        """Обновление данных"""
        self.load_overtime_data()