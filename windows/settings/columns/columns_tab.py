# windows/settings/columns/columns_tab.py

from services.employee_service.column_service import ColumnService
from windows.settings.base_tab import BaseTab
from windows.settings.columns.column_card import ColumnCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.columns.column_dialog import ColumnDialog


class ColumnsTab(BaseTab):
    """Вкладка для управления шаблонами колонок"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    item_color_changed = pyqtSignal(int, str)
    item_added = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        # Инициализируем поля ДО вызова super().__init__
        self.columns = []
        self.column_service = None
        self.session = None

        super().__init__(parent)

        self.hide_filters()

        if self.btnAdd:
            self.btnAdd.setText("Добавить колонку")
            self.btnAdd.setObjectName("btnAddColumn")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        self.item_deleted.connect(self.delete_item)

        self.filterDepartment.hide() if hasattr(self, 'filterDepartment') else None
        self.filterSubDepartment.hide() if hasattr(self, 'filterSubDepartment') else None

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        Для USER и ADMIN - только просмотр (read-only)
        Для SUPER_ADMIN - полный доступ
        """
        # Определяем режим на основе роли
        if self._permission_service:
            is_read_only = self._permission_service.is_columns_tab_read_only()
            self._read_only_mode = is_read_only

        # Применяем состояние
        self._apply_read_only_state()

        # Скрываем или показываем кнопку добавления
        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

        # Обновляем карточки только если данные уже загружены
        if self.columns:
            self.refresh_cards()

    def refresh_cards(self):
        """Обновление карточек"""
        self.clear_cards()
        for i, column in enumerate(self.columns):
            card = ColumnCard(column, parent=self, read_only=self._read_only_mode)
            # В режиме просмотра НЕ подключаем сигналы кликов
            if not self._read_only_mode:
                card.edit_clicked.connect(self.on_edit_clicked)
                card.delete_clicked.connect(self.on_delete_clicked)
                card.color_changed.connect(self.on_color_changed)
                card.done_changed.connect(self.on_done_changed)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()

    def set_session(self, session):
        """Установка сессии и создание сервиса колонок"""
        self.session = session
        if session:
            self.column_service = ColumnService(session)
            self.load_columns()

    def set_column_service(self, service):
        """Установка сервиса для работы с БД (альтернативный метод)"""
        self.column_service = service
        if service:
            self.load_columns()

    def load_columns(self):
        """Загрузка шаблонных колонок через сервис"""
        if self.column_service:
            self.columns = self.column_service.get_template_columns()
            self.refresh_cards()

    def load_data(self, columns: list):
        """Загрузка данных (для совместимости)"""
        self.columns = columns
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие окна добавления шаблонной колонки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        dialog = ColumnDialog(column_data=None, is_template_mode=True, parent=self, read_only=False)
        dialog.column_saved.connect(self.on_column_added)
        dialog.exec()

    def on_edit_clicked(self, column_id: int):
        """Открытие окна редактирования/просмотра шаблонной колонки"""
        column = next((c for c in self.columns if c.get('id') == column_id), None)
        if column:
            dialog = ColumnDialog(
                column_data=column,
                is_template_mode=True,
                parent=self,
                read_only=self._read_only_mode
            )
            if not self._read_only_mode:
                dialog.column_saved.connect(lambda data: self.on_column_updated(column_id, data))
            dialog.exec()

    def on_column_added(self, column_data: dict):
        """Новая шаблонная колонка успешно сохранена"""
        if self._read_only_mode:
            return

        if self.column_service:
            new_column = self.column_service.create_template_column(column_data)
            if new_column:
                self.load_columns()
                self.item_added.emit("column", new_column)
                QMessageBox.information(self, "Успех", f"Колонка «{column_data.get('name')}» добавлена в шаблоны")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить колонку")
        else:
            column_data['id'] = len(self.columns) + 1
            self.columns.append(column_data)
            self.refresh_cards()
            self.item_added.emit("column", column_data)

    def on_column_updated(self, column_id: int, column_data: dict):
        """Обработка редактирования шаблонной колонки"""
        if self._read_only_mode:
            return

        if self.column_service:
            success = self.column_service.update_template_column(column_id, column_data)
            if success:
                self.load_columns()
                self.item_edited.emit("column", column_data)
                QMessageBox.information(self, "Успех", "Колонка обновлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить колонку")
        else:
            for i, col in enumerate(self.columns):
                if col.get('id') == column_id:
                    column_data['id'] = column_id
                    self.columns[i] = column_data
                    break
            self.refresh_cards()
            self.item_edited.emit("column", column_data)

    def on_delete_clicked(self, column_id: int):
        """Удаление шаблонной колонки - вызывается из карточки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        column = next((c for c in self.columns if c.get('id') == column_id), None)
        usage_count = column.get('usage_count', 0) if column else 0

        message = "Вы уверены, что хотите удалить эту колонку из шаблонов?\nЭто действие нельзя отменить."
        if usage_count > 0:
            message = f"Эта колонка используется в {usage_count} проектах.\n\nУдаление повлияет на существующие проекты.\n\nВы уверены?"

        self.confirm_delete(
            title="Удаление колонки",
            message=message,
            item_type="column",
            item_id=column_id
        )

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if self._read_only_mode:
            return

        if item_type == "column" and self.column_service:
            success = self.column_service.delete_template_column(item_id)
            if success:
                self.load_columns()
                QMessageBox.information(self, "Успех", "Колонка удалена из шаблонов")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить колонку")

    def on_color_changed(self, column_id: int, new_color: str):
        """Изменение цвета шаблонной колонки"""
        if self._read_only_mode:
            return

        if self.column_service:
            success = self.column_service.update_template_column(column_id, {'color': new_color})
            if success:
                for column in self.columns:
                    if column.get('id') == column_id:
                        column['color'] = new_color
                        break
                self.refresh_cards()
                self.item_color_changed.emit(column_id, new_color)

    def on_done_changed(self, column_id: int, is_done: bool):
        """Изменение статуса Done"""
        if self._read_only_mode:
            return

        if self.column_service:
            self.column_service.update_template_column(column_id, {'is_done_column': is_done})
            for column in self.columns:
                if column.get('id') == column_id:
                    column['is_done_column'] = is_done
                    break