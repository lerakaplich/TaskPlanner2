# windows/settings/tags/tags_tab.py

from services.employee_service.tag_service import TagService
from windows.settings.base_tab import BaseTab
from windows.settings.tags.tag_card import TagCard
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal

from windows.settings.tags.tag_dialog import TagDialog


class TagsTab(BaseTab):
    """Вкладка для управления темами (тегами)"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)
    item_color_changed = pyqtSignal(int, str)
    item_added = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        # Инициализируем поля ДО вызова super().__init__
        self.tags = []
        self.tag_service = None
        self.session = None

        super().__init__(parent)

        if self.btnAdd:
            self.btnAdd.setText("Добавить тему")
            self.btnAdd.setObjectName("btnAddTag")
            self.btnAdd.clicked.connect(self.on_add_clicked)

        self.item_deleted.connect(self.delete_item)

        self.filterDepartment.hide() if hasattr(self, 'filterDepartment') else None
        self.filterSubDepartment.hide() if hasattr(self, 'filterSubDepartment') else None

    def setup_permission_ui(self):
        """
        Настройка UI в зависимости от прав пользователя
        Для USER - только просмотр (read-only)
        Для ADMIN и SUPER_ADMIN - полный доступ
        """
        # Определяем режим на основе роли
        if self._permission_service:
            is_read_only = self._permission_service.is_tags_tab_read_only()
            self._read_only_mode = is_read_only

        # Применяем состояние
        self._apply_read_only_state()

        # Скрываем или показываем кнопку добавления
        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

        # Обновляем карточки только если данные уже загружены
        if self.tags:
            self.refresh_cards()

    def refresh_cards(self):
        """Обновление карточек"""
        self.clear_cards()
        for i, tag in enumerate(self.tags):
            card = TagCard(tag, parent=self, read_only=self._read_only_mode)
            # В режиме просмотра НЕ подключаем сигналы кликов
            if not self._read_only_mode:
                card.edit_clicked.connect(self.on_edit_clicked)
                card.delete_clicked.connect(self.on_delete_clicked)
                card.color_changed.connect(self.on_color_changed)
            self.add_card_to_grid(card, i)
        self.set_last_row_stretch()

    def set_session(self, session):
        """Установка сессии и создание сервиса тегов"""
        self.session = session
        if session:
            self.tag_service = TagService(session)
            self.load_tags()

    def set_tag_service(self, service):
        """Установка сервиса для работы с БД (альтернативный метод)"""
        self.tag_service = service
        if service:
            self.load_tags()

    def load_tags(self):
        """Загрузка тегов через сервис"""
        if self.tag_service:
            self.tags = self.tag_service.get_all_tags()
            self.refresh_cards()

    def load_data(self, tags: list):
        """Загрузка данных (для совместимости)"""
        self.tags = tags
        self.refresh_cards()

    def on_add_clicked(self):
        """Открытие окна добавления тега"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра добавление недоступно")
            return

        dialog = TagDialog(tag_data=None, parent=self, read_only=False)
        dialog.tag_saved.connect(self.on_tag_added)
        dialog.exec()

    def on_edit_clicked(self, tag_id: int):
        """Открытие окна редактирования/просмотра тега"""
        tag = next((t for t in self.tags if t.get('id') == tag_id), None)
        if tag:
            dialog = TagDialog(
                tag_data=tag,
                parent=self,
                read_only=self._read_only_mode
            )
            if not self._read_only_mode:
                dialog.tag_saved.connect(lambda data: self.on_tag_updated(tag_id, data))
            dialog.exec()

    def on_tag_added(self, tag_data: dict):
        """Новый тег успешно сохранён"""
        if self._read_only_mode:
            return

        if self.tag_service:
            new_tag = self.tag_service.create_tag(tag_data)
            if new_tag:
                self.load_tags()
                self.item_added.emit("tag", new_tag)
                QMessageBox.information(self, "Успех", f"Тема «{tag_data.get('name')}» добавлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить тему")
        else:
            tag_data['id'] = len(self.tags) + 1
            self.tags.append(tag_data)
            self.refresh_cards()
            self.item_added.emit("tag", tag_data)

    def on_tag_updated(self, tag_id: int, tag_data: dict):
        """Обработка редактирования тега"""
        if self._read_only_mode:
            return

        if self.tag_service:
            success = self.tag_service.update_tag(tag_id, tag_data)
            if success:
                self.load_tags()
                self.item_edited.emit("tag", tag_data)
                QMessageBox.information(self, "Успех", "Тема обновлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить тему")
        else:
            for i, tag in enumerate(self.tags):
                if tag.get('id') == tag_id:
                    tag_data['id'] = tag_id
                    self.tags[i] = tag_data
                    break
            self.refresh_cards()
            self.item_edited.emit("tag", tag_data)

    def on_delete_clicked(self, tag_id: int):
        """Удаление тега - вызывается из карточки"""
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        tag = next((t for t in self.tags if t.get('id') == tag_id), None)
        usage_count = tag.get('usage_count', 0) if tag else 0

        message = "Вы уверены, что хотите удалить эту тему?\nЭто действие нельзя отменить."
        if usage_count > 0:
            message = f"Эта тема используется в {usage_count} задачах.\n\nУдаление повлияет на существующие задачи.\n\nВы уверены?"

        self.confirm_delete(
            title="Удаление темы",
            message=message,
            item_type="tag",
            item_id=tag_id
        )

    def delete_item(self, item_type: str, item_id: int):
        """Обработка подтверждённого удаления"""
        if self._read_only_mode:
            return

        if item_type == "tag" and self.tag_service:
            success = self.tag_service.delete_tag(item_id)
            if success:
                self.load_tags()
                QMessageBox.information(self, "Успех", "Тема удалена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить тему")

    def on_color_changed(self, tag_id: int, new_color: str):
        """Изменение цвета тега"""
        if self._read_only_mode:
            return

        if self.tag_service:
            success = self.tag_service.update_tag(tag_id, {'color': new_color})
            if success:
                for tag in self.tags:
                    if tag.get('id') == tag_id:
                        tag['color'] = new_color
                        break
                self.refresh_cards()
                self.item_color_changed.emit(tag_id, new_color)

    def _get_card_search_text(self, card) -> str:
        """Возвращает текст для поиска из карточки тега"""
        if hasattr(card, 'nameLabel'):
            return card.nameLabel.text()
        return ""

    def _apply_search_to_items(self):
        """Переопределяем для тегов"""
        query = self._search_query.lower().strip() if hasattr(self, '_search_query') else ""

        for card in self.cards:
            if query:
                search_text = self._get_card_search_text(card)
                card.setVisible(query in search_text.lower())
            else:
                card.setVisible(True)