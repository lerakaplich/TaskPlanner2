# windows/settings/tags/tags_tab.py

from windows.settings.base_tab import BaseTab
from windows.settings.tags.tag_card import TagCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.tags.tag_dialog import TagDialog
from services.tag_service import TagService


class TagsTab(BaseTab):
    """Вкладка для управления глобальными тегами (темами)"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    item_color_changed = pyqtSignal(int, str)
    tag_added = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []
        self.session = None
        self.tag_service = None

        # Скрываем фильтры (теги глобальные)
        self.hide_filters()

        if self.btnAdd:
            self.btnAdd.setText("Добавить тему")
            self.btnAdd.setObjectName("btnAddTag")
            self.btnAdd.clicked.connect(self.on_add_clicked)

    def set_session(self, session):
        self.session = session
        self.tag_service = TagService(session)
        self.load_tags_from_db()

    def load_tags_from_db(self):
        if not self.tag_service:
            print("⚠️ TagService не инициализирован")
            return

        tags = self.tag_service.get_all_tags()
        self.load_data(tags)

    def on_add_clicked(self):
        if not self.tag_service:
            QMessageBox.warning(self, "Ошибка", "Сервис тем не инициализирован")
            return

        dialog = TagDialog(parent=self)
        dialog.tag_saved.connect(self.on_tag_saved)
        dialog.exec()

    def on_tag_saved(self, tag_data: dict):
        if not self.tag_service:
            return

        result = self.tag_service.create_tag({
            'name': tag_data.get('name'),
            'color': tag_data.get('color', '#ccab6e')
        })

        if result:
            self.tags.append(result)
            self.refresh_cards()
            self.tag_added.emit(result)
            QMessageBox.information(self, "Успех", f"Тема «{result.get('name')}» создана")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось создать тему")

    def on_edit_clicked(self, tag_id: int):
        if not self.tag_service:
            return

        tag = next((t for t in self.tags if t.get('id') == tag_id), None)
        if not tag:
            QMessageBox.warning(self, "Ошибка", "Тема не найдена")
            return

        dialog = TagDialog(tag_data=tag, parent=self)
        dialog.tag_saved.connect(lambda updated_data: self.on_tag_updated(tag_id, updated_data))
        dialog.exec()

    def on_tag_updated(self, old_tag_id: int, updated_data: dict):
        if not self.tag_service:
            return

        success = self.tag_service.update_tag(old_tag_id, {
            'name': updated_data.get('name'),
            'color': updated_data.get('color')
        })

        if success:
            for i, tag in enumerate(self.tags):
                if tag.get('id') == old_tag_id:
                    updated_data['id'] = old_tag_id
                    updated_data['usage_count'] = tag.get('usage_count', 0)
                    self.tags[i] = updated_data
                    break

            self.refresh_cards()
            self.item_edited.emit("tag", updated_data)
            QMessageBox.information(self, "Успех", f"Тема «{updated_data.get('name')}» обновлена")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось обновить тему")

    def on_delete_clicked(self, tag_id: int):
        if not self.tag_service:
            return

        tag = next((t for t in self.tags if t.get('id') == tag_id), None)
        usage_count = tag.get('usage_count', 0) if tag else 0

        message = "Вы уверены, что хотите удалить эту тему?\nЭто действие нельзя отменить."
        if usage_count > 0:
            message = f"Эта тема используется в {usage_count} задачах.\n\nУдаление темы удалит её из всех задач.\n\nВы уверены?"

        self.confirm_delete(
            title="Удаление темы",
            message=message,
            item_type="tag",
            item_id=tag_id
        )

    def on_color_changed(self, tag_id: int, new_color: str):
        if not self.tag_service:
            return

        success = self.tag_service.update_tag(tag_id, {'color': new_color})

        if success:
            for tag in self.tags:
                if tag.get('id') == tag_id:
                    tag['color'] = new_color
                    break
            self.item_color_changed.emit(tag_id, new_color)
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить цвет темы")

    def load_data(self, tags: list):
        self.tags = tags
        self.refresh_cards()

    def refresh_cards(self):
        self.clear_cards()

        for i, tag in enumerate(self.tags):
            card = TagCard(tag)
            card.tag_id = tag.get('id')
            card.edit_clicked.connect(self.on_edit_clicked)
            card.delete_clicked.connect(self.on_delete_clicked)
            card.color_changed.connect(self.on_color_changed)

            self.add_card_to_grid(card, i)

        self.set_last_row_stretch()