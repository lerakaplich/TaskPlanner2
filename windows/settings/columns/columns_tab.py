# windows/settings/columns/columns_tab.py

from windows.settings.base_tab import BaseTab
from windows.settings.columns.column_card import ColumnCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.columns.column_dialog import ColumnDialog


# windows/settings/columns/columns_tab.py

class ColumnsTab(BaseTab):
    """Вкладка для управления шаблонами колонок"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    item_color_changed = pyqtSignal(int, str)
    item_added = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = []
        self.column_service = None
        self.session = None
        self.hide_filters()

        if self.btnAdd:
            self.btnAdd.setText("Добавить колонку")
            self.btnAdd.setObjectName("btnAddColumn")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        # Подключаем сигнал удаления
        self.item_deleted.connect(self.delete_item)  # ← ДОБАВИТЬ ЭТУ СТРОКУ

    def set_session(self, session):
        """Установка сессии БД"""
        self.session = session
        from services.column_service import ColumnService
        self.column_service = ColumnService(session)

    def load_data(self, columns: list):
        """Загрузка данных (только шаблонные колонки)"""
        if self.column_service:
            # Загружаем только шаблонные колонки
            self.columns = self.column_service.get_template_columns()
        else:
            self.columns = columns
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие окна добавления шаблонной колонки"""
        dialog = ColumnDialog(column_data=None, is_template_mode=True, parent=self)
        dialog.column_saved.connect(self.on_column_added)
        dialog.exec()

    def on_edit_clicked(self, column_id: int):
        """Открытие окна редактирования шаблонной колонки"""
        column = next((c for c in self.columns if c.get('id') == column_id), None)
        if column:
            dialog = ColumnDialog(column_data=column, is_template_mode=True, parent=self)
            dialog.column_saved.connect(lambda data: self.on_column_updated(column_id, data))
            dialog.exec()

    def on_column_added(self, column_data: dict):
        """Новая шаблонная колонка успешно сохранена"""
        if self.column_service:
            # Сохраняем в БД
            new_column = self.column_service.create_template_column(column_data)
            if new_column:
                self.columns.append(new_column)
                self.refresh_cards()
                self.item_added.emit("column", new_column)
                QMessageBox.information(self, "Успех", f"Колонка «{column_data.get('name')}» добавлена в шаблоны")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить колонку")
        else:
            # Fallback для тестов
            column_data['id'] = len(self.columns) + 1
            self.columns.append(column_data)
            self.refresh_cards()
            self.item_added.emit("column", column_data)

    def on_column_updated(self, column_id: int, column_data: dict):
        """Обработка редактирования шаблонной колонки"""
        if self.column_service:
            success = self.column_service.update_template_column(column_id, column_data)
            if success:
                # Обновляем локальный список
                for i, col in enumerate(self.columns):
                    if col.get('id') == column_id:
                        column_data['id'] = column_id
                        self.columns[i] = column_data
                        break
                self.refresh_cards()
                self.item_edited.emit("column", column_data)
                QMessageBox.information(self, "Успех", "Колонка обновлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить колонку")
        else:
            # Fallback для тестов
            for i, col in enumerate(self.columns):
                if col.get('id') == column_id:
                    column_data['id'] = column_id
                    self.columns[i] = column_data
                    break
            self.refresh_cards()
            self.item_edited.emit("column", column_data)

    def on_delete_clicked(self, column_id: int):
        """Удаление шаблонной колонки - вызывается из карточки"""
        self.confirm_delete(
            title="Удаление колонки",
            message="Вы уверены, что хотите удалить эту колонку из шаблонов?\nЭто действие нельзя отменить.",
            item_type="column",
            item_id=column_id
        )

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления - вызывается из base_tab"""
        print(f"🗑️ delete_item вызван: item_type={item_type}, item_id={item_id}")

        if item_type == "column":
            if self.column_service:
                success = self.column_service.delete_template_column(item_id)
                if success:
                    self.columns = [c for c in self.columns if c.get('id') != item_id]
                    self.refresh_cards()
                    QMessageBox.information(self, "Успех", "Колонка удалена из шаблонов")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить колонку")
            else:
                self.columns = [c for c in self.columns if c.get('id') != item_id]
                self.refresh_cards()

    def on_color_changed(self, column_id: int, new_color: str):
        """Изменение цвета шаблонной колонки"""
        if self.column_service:
            self.column_service.update_template_column(column_id, {'color': new_color})

        for column in self.columns:
            if column.get('id') == column_id:
                column['color'] = new_color
                break

        self.item_color_changed.emit(column_id, new_color)
        self.refresh_cards()

    def refresh_cards(self):
        self.clear_cards()
        for i, column in enumerate(self.columns):
            card = ColumnCard(column)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            card.color_changed.connect(self.on_color_changed)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()