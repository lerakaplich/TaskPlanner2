from windows.settings.base_tab import BaseTab
from windows.settings.columns.column_card import ColumnCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.columns.column_dialog import ColumnDialog


class ColumnsTab(BaseTab):
    """Вкладка для управления колонками"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)      # оставляем для совместимости
    item_color_changed = pyqtSignal(int, str)
    item_added = pyqtSignal(str, dict)       # сигнал для добавления

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.columns = []
        self.hide_filters()

        if self.btnAdd:
            self.btnAdd.setText("Добавить колонку")
            self.btnAdd.setObjectName("btnAddColumn")
            self.btnAdd.clicked.connect(self.on_add_clicked)

    def load_data(self, columns: list):
        self.columns = columns

        if not self.project_id and columns:
            self.project_id = columns[0].get('project_id')

        self.refresh_cards()

    # ==================== ДОБАВЛЕНИЕ ====================
    def on_add_clicked(self):
        if self.project_id is None:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить ID проекта для добавления колонки."
            )
            return

        dialog = ColumnDialog(project_id=self.project_id, parent=self)
        dialog.column_saved.connect(self.on_column_added)
        dialog.exec()

    def on_column_added(self, column_data: dict):
        """Новая колонка успешно сохранена"""
        self.item_added.emit("column", column_data)

    # ==================== РЕДАКТИРОВАНИЕ ====================
    def on_edit_clicked(self, column_id: int):
        """Открытие диалога редактирования колонки"""
        # Находим колонку по ID
        column = next((c for c in self.columns if c.get('id') == column_id), None)
        if not column:
            QMessageBox.warning(self, "Ошибка", "Колонка не найдена")
            return

        # Открываем диалог в режиме редактирования
        dialog = ColumnDialog(
            column_data=column,      # ← передаём данные для редактирования
            project_id=self.project_id,
            parent=self
        )

        # Подключаем сигнал сохранения
        dialog.column_saved.connect(lambda updated_data: self.on_column_updated(column_id, updated_data))

        dialog.exec()

    def on_column_updated(self, old_column_id: int, updated_data: dict):
        """Обработка результата редактирования"""
        # Обновляем данные в локальном списке
        for i, col in enumerate(self.columns):
            if col.get('id') == old_column_id:
                # Сохраняем старый id, если в данных его нет
                if updated_data.get('id') is None:
                    updated_data['id'] = old_column_id
                self.columns[i] = updated_data
                break

        # Перерисовываем все карточки
        self.refresh_cards()

        # Уведомляем родительское окно (если нужно обновить БД)
        self.item_edited.emit("column", updated_data)

        QMessageBox.information(
            self,
            "Успешно",
            f"Колонка «{updated_data.get('name', '')}» успешно обновлена"
        )

    # ==================== УДАЛЕНИЕ И ИЗМЕНЕНИЕ ЦВЕТА ====================
    def on_delete_clicked(self, column_id: int):
        """Удаление колонки"""
        self.confirm_delete(
            title="Удаление колонки",
            message="Вы уверены, что хотите удалить эту колонку?\nЭто действие нельзя отменить.",
            item_type="column",
            item_id=column_id
        )

    def on_color_changed(self, column_id: int, new_color: str):
        """Изменение цвета колонки"""
        for column in self.columns:
            if column.get('id') == column_id:
                column['color'] = new_color
                break

        self.item_color_changed.emit(column_id, new_color)
        self.refresh_cards()   # сразу обновляем вид карточек

    def refresh_cards(self):
        self.clear_cards()
        for i, column in enumerate(self.columns):
            card = ColumnCard(column)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            card.color_changed.connect(self.on_color_changed)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()