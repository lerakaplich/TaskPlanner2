from windows.settings.base_tab import BaseTab
from windows.settings.tags.tag_card import TagCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.tags.tag_dialog import TagDialog  # ← уже импортировано


class TagsTab(BaseTab):
    """Вкладка для управления тегами"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)  # оставляем для совместимости (если где-то используется)
    item_color_changed = pyqtSignal(int, str)
    tag_added = pyqtSignal(dict)  # лучше использовать этот сигнал для добавления

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []

        # Скрываем фильтры
        self.hide_filters()

        # Настраиваем кнопку добавления
        if self.btnAdd:
            self.btnAdd.setText("Добавить тег")
            self.btnAdd.setObjectName("btnAddTag")
            self.btnAdd.clicked.connect(self.on_add_clicked)

    def on_add_clicked(self):
        """Добавление нового тега"""
        dialog = TagDialog(parent=self)  # tag_data=None → режим добавления
        dialog.tag_saved.connect(self.on_tag_saved)
        dialog.exec()

    def on_edit_clicked(self, tag_id: int):
        """Обработчик кнопки Редактировать на карточке"""
        # Находим тег по id
        tag = next((t for t in self.tags if t.get('id') == tag_id), None)
        if not tag:
            QMessageBox.warning(self, "Ошибка", "Тег не найден")
            return

        # Открываем диалог в режиме редактирования
        dialog = TagDialog(tag_data=tag, parent=self)  # ← передаём tag_data
        dialog.tag_saved.connect(lambda updated_data: self.on_tag_updated(tag_id, updated_data))

        if dialog.exec():
            pass  # вся обработка происходит в on_tag_updated

    def on_tag_saved(self, tag_data: dict):
        """Сохранение нового тега (при добавлении)"""
        self.tag_added.emit(tag_data)

    def on_tag_updated(self, old_tag_id: int, updated_data: dict):
        """Сохранение изменений после редактирования"""
        # Обновляем данные в локальном списке
        for i, tag in enumerate(self.tags):
            if tag.get('id') == old_tag_id:
                # Сохраняем старый id, если новый не пришёл
                if 'id' not in updated_data or updated_data['id'] is None:
                    updated_data['id'] = old_tag_id
                self.tags[i] = updated_data
                break

        # Обновляем все карточки
        self.refresh_cards()

        # Сообщаем родителю об изменении (если нужно)
        self.item_edited.emit("tag", updated_data)

        QMessageBox.information(
            self,
            "Успешно",
            f"Тег «{updated_data.get('name', '')}» успешно обновлён"
        )

    def on_delete_clicked(self, column_id: int):
        """Удаление колонки"""
        self.confirm_delete(
            title="Удаление тега",
            message="Вы уверены, что хотите удалить этот тег?\nЭто действие нельзя отменить.",
            item_type="column",
            item_id=column_id
        )

    def on_color_changed(self, tag_id: int, new_color: str):
        """Изменение цвета тега"""
        for tag in self.tags:
            if tag.get('id') == tag_id:
                tag['color'] = new_color
                break
        self.item_color_changed.emit(tag_id, new_color)
        self.refresh_cards()  # обновляем карточки, чтобы цвет сразу отобразился

    def load_data(self, tags: list):
        self.tags = tags
        self.refresh_cards()

    def refresh_cards(self):
        self.clear_cards()

        for i, tag in enumerate(self.tags):
            card = TagCard(tag)
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            card.color_changed.connect(self.on_color_changed)

            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()