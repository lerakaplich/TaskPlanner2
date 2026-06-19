# windows/permissions/read_only_mixin.py
from typing import Optional, Callable, Any
from PyQt6.QtWidgets import QWidget, QPushButton, QDialog
from PyQt6.QtCore import Qt


class ReadOnlyMixin:
    """
    Миксин для страниц настроек, включающий режим только просмотра
    Используется вместе с UIPermissionMixin
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_only_mode = False

    def set_read_only_mode(self, enabled: bool = True):
        """
        Включает/отключает режим только просмотра
        """
        self._read_only_mode = enabled
        self._apply_read_only_ui()

    def is_read_only(self) -> bool:
        """Возвращает True, если включен режим только просмотра"""
        return self._read_only_mode

    def _apply_read_only_ui(self):
        """
        Применяет изменения UI для режима только просмотра.
        Переопределяется в конкретных страницах.
        """
        pass

    def _setup_read_only_widget(self, widget: QWidget):
        """
        Устанавливает атрибут read-only для всех дочерних виджетов
        """
        if widget is None:
            return

        # Для QLineEdit, QTextEdit, QComboBox, QSpinBox и т.д.
        if hasattr(widget, 'setReadOnly'):
            widget.setReadOnly(True)
        elif hasattr(widget, 'setEnabled'):
            widget.setEnabled(False)

        # Рекурсивно для дочерних виджетов
        if hasattr(widget, 'children'):
            for child in widget.children():
                self._setup_read_only_widget(child)

    def _hide_add_buttons(self):
        """Скрывает кнопки добавления во всех вкладках"""
        if hasattr(self, 'employees_tab') and hasattr(self.employees_tab, 'btnAdd'):
            self.employees_tab.btnAdd.setVisible(False)
        if hasattr(self, 'departments_tab') and hasattr(self.departments_tab, 'btnAdd'):
            self.departments_tab.btnAdd.setVisible(False)
        if hasattr(self, 'divisions_tab') and hasattr(self.divisions_tab, 'btnAdd'):
            self.divisions_tab.btnAdd.setVisible(False)
        if hasattr(self, 'columns_tab') and hasattr(self.columns_tab, 'btnAdd'):
            self.columns_tab.btnAdd.setVisible(False)
        if hasattr(self, 'tags_tab') and hasattr(self.tags_tab, 'btnAdd'):
            self.tags_tab.btnAdd.setVisible(False)

    def _rename_edit_buttons_to_details(self):
        """
        Переименовывает кнопки редактирования на "Подробнее"
        """
        # Проходим по всем вкладкам и переименовываем
        tabs = ['employees_tab', 'departments_tab', 'divisions_tab', 'columns_tab', 'tags_tab']
        for tab_name in tabs:
            tab = getattr(self, tab_name, None)
            if tab and hasattr(tab, '_rename_edit_buttons'):
                tab._rename_edit_buttons()