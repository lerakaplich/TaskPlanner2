# services/navigation_service.py
from typing import Dict, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal


class NavigationService(QObject):
    """Сервис для управления навигацией в приложении"""

    page_changed = pyqtSignal(int, str)  # index, page_name

    # Константы страниц
    PAGE_PROJECTS = 0
    PAGE_MY_TASKS = 1
    PAGE_OTHER_TASKS = 2
    PAGE_GANTT = 3
    PAGE_ANALYTICS = 4
    PAGE_CHAT = 5
    PAGE_OVERTIME = 6
    PAGE_SETTINGS = 7
    PAGE_ARCHIVE = 8
    PAGE_PROFILE = 9

    PAGE_NAMES = {
        PAGE_PROJECTS: "Проекты",
        PAGE_MY_TASKS: "Мои задачи",
        PAGE_OTHER_TASKS: "Чужие задачи",
        PAGE_GANTT: "Гант",
        PAGE_ANALYTICS: "Аналитика",
        PAGE_CHAT: "Чат",
        PAGE_OVERTIME: "Переработки",
        PAGE_SETTINGS: "Настройки",
        PAGE_ARCHIVE: "Архив",
        PAGE_PROFILE: "Профиль"
    }

    def __init__(self, project_service, session, current_user_id: int):
        super().__init__()
        self.project_service = project_service
        self.session = session
        self.current_user_id = current_user_id
        self.current_user = None

        self._is_switching = False
        self._pending_switch = None

    def set_current_user(self, user: Dict):
        """Устанавливает текущего пользователя"""
        self.current_user = user

    def get_page_name(self, index: int) -> str:
        """Возвращает название страницы по индексу"""
        return self.PAGE_NAMES.get(index, f"Неизвестная({index})")

    def can_switch_to_page(self, index: int) -> bool:
        """Проверяет, можно ли переключиться на страницу"""
        # Здесь можно добавить проверки прав
        return True

    def should_recreate_page(self, index: int) -> bool:
        """Определяет, нужно ли пересоздавать страницу"""
        # Страницы, которые всегда пересоздаём для свежих данных
        recreate_pages = {
            self.PAGE_GANTT,
            self.PAGE_ANALYTICS,
            self.PAGE_ARCHIVE,
            self.PAGE_OTHER_TASKS
        }
        return index in recreate_pages

    def get_page_creation_params(self, index: int) -> Dict:
        """Возвращает параметры для создания страницы"""
        params = {
            'session': self.session,
            'current_user_id': self.current_user_id,
            'current_user': self.current_user
        }

        if index == self.PAGE_GANTT:
            params['project_service'] = self.project_service
        elif index == self.PAGE_CHAT:
            params['chat_service'] = None  # будет установлено извне
            params['projects_service'] = self.project_service
        elif index == self.PAGE_OVERTIME:
            params['overtime_service'] = None  # будет установлено извне
        elif index == self.PAGE_ARCHIVE:
            params['archive_service'] = None  # будет установлено извне
        elif index == self.PAGE_PROFILE:
            params['employee_id'] = self.current_user_id

        return params

    def get_tab_visibility(self, user_id: int) -> Dict[str, bool]:
        """Возвращает видимость вкладок для пользователя"""
        # Здесь будет логика из permission_service
        return {
            'projects': True,
            'my_tasks': True,
            'other_tasks': True,
            'gantt': True,
            'analytics': True,
            'chat': True,
            'overtime': True,
            'settings': True,
            'archive': True
        }