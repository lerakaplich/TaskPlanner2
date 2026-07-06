# windows/overtime/overtime_page.py

import os
from typing import List, Dict, Optional

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog, QProgressDialog, QApplication
from PyQt6 import uic

from services.permissions.app_permissions import AppRole
from windows.overtime.overtime_card import OvertimeCard
from windows.overtime.add_overtime_dialog import AddOvertimeDialog
from windows.overtime.edit_overtime_dialog import EditOvertimeDialog
from windows.overtime.period_dialog import PeriodDialog
from services.overtime_service.overtime_export_service import OvertimeExportService


class OvertimePage(QWidget):
    """UI-страница переработок с поддержкой прав доступа"""

    def __init__(self, service=None, employee_service=None, permission_service=None, parent=None):
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
        self.permission_service = permission_service

        self.my_overtimes: List[Dict] = []
        self.all_overtimes: List[Dict] = []
        self._cards_cache = {}

        self.current_project_filter: Optional[str] = None
        self.current_task_filter: Optional[str] = None
        self.current_start_date: Optional[QDate] = None
        self.current_end_date: Optional[QDate] = None

        self._updating = False

        self.btnAddOvertime.clicked.connect(self.show_add_overtime)
        self.btnExport.clicked.connect(self.show_export_dialog)
        self.btnApplyFilters.clicked.connect(self.apply_filters)
        self.btnClearFilters.clicked.connect(self.clear_filters)
        self.btnSelectPeriod.clicked.connect(self.select_period)
        self.comboProject.currentIndexChanged.connect(self.on_project_changed)

        if hasattr(self, 'btnImport'):
            self.btnImport.clicked.connect(self.show_import_dialog)

        # Применяем права доступа
        self._setup_permission_ui()

        self.init_filters()
        self.load_overtimes()

    def _setup_permission_ui(self):
        """Настройка UI в зависимости от прав пользователя"""
        if not self.permission_service:
            return

        # 1. Кнопка импорта - только для админа и суперадмина
        if hasattr(self, 'btnImport'):
            can_import = self.permission_service.can_import_overtime()
            self.btnImport.setVisible(can_import)
            self.btnImport.setEnabled(can_import)
            print(f"   btnImport visible: {can_import}")

        # 2. Кнопка добавления переработки - только для админа и суперадмина
        if hasattr(self, 'btnAddOvertime'):
            can_add = self.permission_service.can_add_overtime()
            self.btnAddOvertime.setVisible(can_add)
            self.btnAddOvertime.setEnabled(can_add)
            print(f"   btnAddOvertime visible: {can_add}")

        # 3. Кнопка экспорта - только для админа и суперадмина
        if hasattr(self, 'btnExport'):
            can_export = self.permission_service.can_add_overtime()
            self.btnExport.setVisible(can_export)
            self.btnExport.setEnabled(can_export)
            print(f"   btnExport visible: {can_export}")

        # 4. Вкладка "Все переработки" - только для суперадмина, админа и начальников
        if hasattr(self, 'tabWidget'):
            # Используем app_manager для проверки прав
            role = self.permission_service.app_manager.role
            can_view_all = role in (AppRole.SUPER_ADMIN, AppRole.ADMIN)

            # ИЛИ через CombinedRole
            # combined = self.permission_service.get_combined_role()
            # can_view_all = combined.can_view_all_overtime()

            if self.tabWidget.count() > 1:
                self.tabWidget.setTabVisible(1, can_view_all)
                print(f"   Вкладка 'Все переработки' visible: {can_view_all}")

    def showEvent(self, event):
        """Срабатывает при каждом показе страницы"""
        super().showEvent(event)
        print("⏱️ OvertimePage.showEvent - обновляем содержимое")
        QTimer.singleShot(100, self.load_overtimes)

    def load_overtimes(self):
        """Загрузка переработок с оптимизацией"""
        if self.service and not self._updating:
            self._updating = True
            try:
                self.my_overtimes, self.all_overtimes = self.service.load_overtimes()
                self.init_filters()
                self.display_overtimes()
                self._update_total_hours()
            finally:
                self._updating = False

    def _update_total_hours(self):
        if hasattr(self, 'totalHoursValue') and self.service:
            total = self.service.crud.get_total_hours(self.my_overtimes)
            self.totalHoursValue.setText(f"{total:.1f}")

    def init_filters(self):
        """Инициализация фильтров (только проекты пользователя)"""
        self.comboProject.blockSignals(True)
        self.comboProject.clear()
        self.comboProject.addItem("Все проекты", None)

        if self.service and self.service.current_user_id:
            projects = self.service.get_projects(only_active=True)
            for project in projects:
                self.comboProject.addItem(project['name'], project['name'])

        self.comboProject.setCurrentIndex(0)
        self.comboProject.blockSignals(False)

        self.comboTask.blockSignals(True)
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        self.comboTask.setEnabled(False)
        self.comboTask.blockSignals(False)

    def on_project_changed(self, index):
        """Обработчик изменения проекта (с оптимизацией)"""
        project_name = self.comboProject.currentData()
        if project_name is None:
            self.comboTask.blockSignals(True)
            self.comboTask.clear()
            self.comboTask.addItem("Все задачи", None)
            self.comboTask.setEnabled(False)
            self.comboTask.blockSignals(False)
            return

        self.comboTask.blockSignals(True)
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)

        if self.service:
            project_id = self.service.get_project_id_by_name(project_name)
            if project_id:
                tasks = self.service.get_tasks_for_project(project_id)
                for task in tasks:
                    self.comboTask.addItem(task['title'], task['title'])

        self.comboTask.setEnabled(self.comboTask.count() > 1)
        self.comboTask.blockSignals(False)

    def update_tasks_from_all(self):
        """Обновляет список задач из всех переработок (для отображения в фильтре)"""
        self.comboTask.blockSignals(True)
        self.comboTask.clear()
        self.comboTask.addItem("Все задачи", None)
        tasks = set()
        for ot in self.all_overtimes:
            if ot.get('task'):
                tasks.add(ot['task'])
        for task in sorted(tasks):
            self.comboTask.addItem(task, task)
        self.comboTask.setEnabled(self.comboTask.count() > 1)
        self.comboTask.blockSignals(False)

    def clear_filters(self):
        """Сброс фильтров с оптимизацией"""
        if self._updating:
            return

        self._updating = True
        try:
            self.comboProject.blockSignals(True)
            self.comboProject.setCurrentIndex(0)
            self.comboProject.blockSignals(False)

            self.comboTask.blockSignals(True)
            self.comboTask.clear()
            self.comboTask.addItem("Все задачи", None)
            self.comboTask.setEnabled(False)
            self.comboTask.blockSignals(False)

            self.current_project_filter = None
            self.current_task_filter = None
            self.current_start_date = None
            self.current_end_date = None

            self._display_tab_optimized(self.gridLayoutMy, self.my_overtimes)
            self._display_tab_optimized(self.gridLayoutAll, self.all_overtimes)
            self._update_total_hours()

            print("[DEBUG] Фильтры сброшены")
        finally:
            self._updating = False

    def apply_filters(self):
        """Применение фильтров с оптимизацией"""
        if self._updating:
            return

        self._updating = True
        try:
            self.current_project_filter = self.comboProject.currentData()
            self.current_task_filter = self.comboTask.currentData() if self.comboTask.isEnabled() else None
            print(f"[DEBUG] Применяем фильтры: project={self.current_project_filter}, task={self.current_task_filter}")
            self.display_overtimes()
            self._update_total_hours()
        finally:
            self._updating = False

    def display_overtimes(self):
        """Отображение переработок с фильтрацией"""
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

        # Для вкладки "Мои переработки" - передаём флаг is_my_tab=True
        self._display_tab_optimized(self.gridLayoutMy, filtered_my, is_my_tab=True)
        # Для вкладки "Все переработки" - is_my_tab=False
        self._display_tab_optimized(self.gridLayoutAll, filtered_all, is_my_tab=False)
        self._update_total_hours_display(filtered_my)

    def _update_total_hours_display(self, overtimes: List[Dict]):
        if hasattr(self, 'totalHoursValue') and self.service:
            total = self.service.crud.get_total_hours(overtimes)
            self.totalHoursValue.setText(f"{total:.1f}")

    def _display_tab_optimized(self, layout, overtimes, is_my_tab=False):
        """Оптимизированное отображение карточек с переиспользованием виджетов"""
        existing_widgets = {}
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                if hasattr(widget, 'overtime_id'):
                    existing_widgets[widget.overtime_id] = widget
                else:
                    widget.deleteLater()

        for i, ot in enumerate(overtimes):
            ot_id = ot.get('id')
            is_my = ot.get('is_mine', False) or is_my_tab

            # Определяем права для этой конкретной карточки
            can_edit = False
            can_delete = False

            if self.permission_service:
                # Проверяем, может ли пользователь редактировать ЭТУ переработку
                can_edit = self._can_edit_overtime(ot)
                can_delete = self._can_delete_overtime(ot)
            else:
                can_edit = True
                can_delete = True

            if ot_id in existing_widgets:
                card = existing_widgets[ot_id]
                card.overtime_data = ot
                card.setup_data()
                card.can_edit = can_edit
                card.can_delete = can_delete
                card._apply_permissions()
                del existing_widgets[ot_id]
            else:
                card = OvertimeCard(ot, can_edit=can_edit, can_delete=can_delete)
                card.edit_clicked.connect(self.show_edit_overtime)
                card.add_details_clicked.connect(self.show_add_details_overtime)
                card.delete_clicked.connect(self.delete_overtime)

            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)

        for widget in existing_widgets.values():
            widget.deleteLater()

    def _can_edit_overtime(self, overtime: Dict) -> bool:
        """
        Проверяет, может ли пользователь редактировать конкретную переработку
        """
        if not self.permission_service:
            return True

        # Админ и суперадмин могут редактировать любые
        role = self.permission_service.app_manager.role
        if role in (AppRole.ADMIN, AppRole.SUPER_ADMIN):
            return True

        # Обычный пользователь может редактировать только свои переработки
        if role == AppRole.USER:
            return overtime.get('is_mine', False)

        return False

    def _can_delete_overtime(self, overtime: Dict) -> bool:
        """
        Проверяет, может ли пользователь удалять переработку
        """
        if not self.permission_service:
            return True

        # Только админ и суперадмин могут удалять
        role = self.permission_service.app_manager.role
        return role in (AppRole.ADMIN, AppRole.SUPER_ADMIN)

    def show_add_details_overtime(self, overtime_id: int):
        """Добавление описания к переработке (кнопка Добавить)"""
        overtime = self.service.get_overtime_by_id(overtime_id)
        if not overtime:
            QMessageBox.warning(self, "Ошибка", "Переработка не найдена")
            return

        # Проверяем права на редактирование ЭТОЙ переработки
        if not self._can_edit_overtime(overtime):
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на редактирование этой переработки")
            return

        dialog = EditOvertimeDialog(service=self.service, overtime_data=overtime, parent=self)
        if dialog.exec():
            self.load_overtimes()
            QMessageBox.information(self, "Успех", "Данные переработки добавлены")

    def show_edit_overtime(self, overtime_id: int):
        """Редактирование переработки (кнопка Редактировать)"""
        overtime = self.service.get_overtime_by_id(overtime_id)
        if not overtime:
            QMessageBox.warning(self, "Ошибка", "Переработка не найдена")
            return

        # Проверяем права на редактирование ЭТОЙ переработки
        if not self._can_edit_overtime(overtime):
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на редактирование этой переработки")
            return

        dialog = EditOvertimeDialog(service=self.service, overtime_data=overtime, parent=self)
        if dialog.exec():
            self.load_overtimes()
            QMessageBox.information(self, "Успех", "Переработка обновлена")

    def delete_overtime(self, overtime_id: int):
        """Удаление переработки"""
        overtime = self.service.get_overtime_by_id(overtime_id)
        if not overtime:
            QMessageBox.warning(self, "Ошибка", "Переработка не найдена")
            return

        # Проверяем права на удаление ЭТОЙ переработки
        if not self._can_delete_overtime(overtime):
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на удаление переработок")
            return

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
        """Создание новой переработки"""
        # Для создания новой переработки нужно право can_add_overtime (только админ/суперадмин)
        if self.permission_service and not self.permission_service.can_add_overtime():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на добавление переработок")
            return

        dialog = AddOvertimeDialog(service=self.service, parent=self)
        if dialog.exec():
            data = dialog.get_overtime_data()
            new_ot = self.service.add_overtime(
                date=data['date'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                description=data['description'],
                employee_id=data['employee_id'],
                project_id=data.get('project_id'),
                task_id=data.get('task_id')
            )
            if new_ot:
                self.load_overtimes()
                self.update_tasks_from_all()
                QMessageBox.information(self, "Успех", "Переработка добавлена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить переработку")

    def select_period(self):
        dialog = PeriodDialog(self, employee_service=self.employee_service)
        if dialog.exec():
            self.current_start_date, self.current_end_date = dialog.get_period()
            self.display_overtimes()
            self._update_total_hours()

    def show_import_dialog(self):
        if self.permission_service and not self.permission_service.can_import_overtime():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на импорт переработок")
            return

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

    def _display_tab(self, layout, overtimes):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        can_edit = self.permission_service.can_add_overtime() if self.permission_service else True

        for i, ot in enumerate(overtimes):
            card = OvertimeCard(ot, can_edit=can_edit)
            card.edit_clicked.connect(self.show_edit_overtime)
            card.add_details_clicked.connect(self.show_add_details_overtime)
            card.delete_clicked.connect(self.delete_overtime)

            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)

    def show_export_dialog(self):
        # Проверяем права на экспорт
        if self.permission_service and not self.permission_service.can_add_overtime():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на экспорт переработок")
            return

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