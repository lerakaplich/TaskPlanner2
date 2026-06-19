# windows/permissions/ui_permission_mixin.py
from typing import Optional


class UIPermissionMixin:
    """
    Миксин для страниц, добавляющий поддержку прав
    Используется для унификации проверок прав в UI
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permission_service = None
        self._read_only_mode = False

    def set_permission_service(self, permission_service):
        """Устанавливает сервис прав"""
        self._permission_service = permission_service

    @property
    def permissions(self):
        """Возвращает сервис прав"""
        return self._permission_service

    def set_read_only_mode(self, enabled: bool = True):
        """
        Включает режим только просмотра на странице
        """
        self._read_only_mode = enabled
        self.setup_permission_ui()

    def is_read_only(self) -> bool:
        """Возвращает True, если включен режим только просмотра"""
        return self._read_only_mode

    def setup_permission_ui(self):
        """
        Переопределяется в конкретных страницах
        Настраивает UI в зависимости от прав
        """
        pass

    def _should_enable_edit(self) -> bool:
        """
        Определяет, можно ли редактировать элементы
        """
        if self._read_only_mode:
            return False
        if self._permission_service:
            return self._permission_service.can_edit_settings()
        return True

    def _should_show_add_buttons(self) -> bool:
        """
        Определяет, нужно ли показывать кнопки добавления
        """
        if self._read_only_mode:
            return False
        if self._permission_service:
            return self._permission_service.can_show_add_buttons_in_settings()
        return True

    def _should_show_delete_buttons(self) -> bool:
        """
        Определяет, нужно ли показывать кнопки удаления
        """
        if self._read_only_mode:
            return False
        if self._permission_service:
            return self._permission_service.can_show_delete_buttons_in_settings()
        return True

    def _get_button_text(self) -> str:
        """
        Возвращает текст кнопки: "Редактировать" или "Подробнее"
        """
        if self._read_only_mode:
            return "Подробнее"
        if self._permission_service:
            return self._permission_service.get_settings_button_text()
        return "Редактировать"

    def _get_user_role(self):
        """
        Возвращает роль пользователя в приложении
        """
        if self._permission_service and hasattr(self._permission_service, 'app_manager'):
            return self._permission_service.app_manager.role
        return None