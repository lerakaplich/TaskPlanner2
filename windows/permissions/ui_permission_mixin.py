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

    def set_permission_service(self, permission_service):
        """Устанавливает сервис прав"""
        self._permission_service = permission_service

    @property
    def permissions(self):
        """Возвращает сервис прав"""
        return self._permission_service

    def setup_permission_ui(self):
        """
        Переопределяется в конкретных страницах
        Настраивает UI в зависимости от прав
        """
        pass