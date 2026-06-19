# windows/settings/settings_factory.py

from typing import Optional
from windows.settings.settings_page import SettingsPage


class SettingsPageFactory:
    """
    Фабрика для создания страниц настроек с различными режимами
    """

    @staticmethod
    def create_read_only_settings_page(parent=None, session=None) -> SettingsPage:
        """
        Создаёт страницу настроек в режиме только просмотра
        """
        page = SettingsPage(parent, session)
        page.set_read_only_mode(True)
        return page

    @staticmethod
    def create_editable_settings_page(parent=None, session=None) -> SettingsPage:
        """
        Создаёт страницу настроек с полным доступом
        """
        page = SettingsPage(parent, session)
        page.set_read_only_mode(False)
        return page

    @staticmethod
    def create_settings_page_with_permissions(parent=None, session=None, permission_service=None) -> SettingsPage:
        """
        Создаёт страницу настроек с проверкой прав через сервис
        """
        page = SettingsPage(parent, session)
        page.set_permission_service(permission_service)

        # Определяем режим на основе прав
        if permission_service:
            read_only = not permission_service.can_edit_settings()
            page.set_read_only_mode(read_only)

        return page