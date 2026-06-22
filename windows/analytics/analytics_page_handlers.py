# windows/analytics/analytics_page_handlers.py

from typing import Optional
from PyQt6.QtWidgets import QMessageBox

from windows.profile.profile_page import ProfilePage


class AnalyticsPageHandlers:
    """Обработчики событий для AnalyticsPage"""

    def __init__(self, page):
        self.page = page

    def open_employee_profile(self, employee_id: int):
        """Открывает профиль сотрудника"""
        if not employee_id:
            return

        employee_data = self._find_employee(employee_id)
        if not employee_data:
            QMessageBox.warning(self.page, "Ошибка", "Сотрудник не найден")
            return

        self._show_profile(employee_id, employee_data)

    def _find_employee(self, employee_id: int) -> Optional[dict]:
        """Находит сотрудника в данных"""
        for emp in self.page._employees_raw_data:
            if emp.get('id') == employee_id:
                return emp
        return None

    def _show_profile(self, employee_id: int, employee_data: dict):
        """Показывает профиль сотрудника"""
        try:
            main_window = self._find_main_window()
            if main_window and hasattr(main_window, 'navigation'):
                self._show_profile_in_main_window(main_window, employee_id, employee_data)
            else:
                self._show_profile_dialog(employee_id, employee_data)
        except Exception as e:
            print(f"❌ Ошибка открытия профиля: {e}")
            QMessageBox.warning(self.page, "Ошибка", f"Не удалось открыть профиль: {e}")

    def _find_main_window(self):
        """Находит главное окно"""
        main_window = self.page.window()
        while main_window and not hasattr(main_window, 'navigation'):
            main_window = main_window.parent()
        return main_window

    def _show_profile_in_main_window(self, main_window, employee_id: int, employee_data: dict):
        """Показывает профиль внутри главного окна"""
        if hasattr(main_window.navigation, 'pages'):
            profile_page = main_window.navigation.get_profile_page()
            profile_page.employee_id = employee_id
            profile_page.current_user = employee_data
            profile_page.load_employee()
            if hasattr(profile_page, 'chart_widget'):
                profile_page.chart_widget.load_data(employee_id)
            main_window.contentStack.setCurrentWidget(profile_page)

    def _show_profile_dialog(self, employee_id: int, employee_data: dict):
        """Показывает профиль в отдельном диалоге"""
        profile_dialog = ProfilePage(
            employee_id=employee_id,
            current_user=employee_data,
            parent=self.page
        )
        profile_dialog.setWindowTitle(f"Профиль: {employee_data.get('name', 'Сотрудник')}")
        profile_dialog.resize(800, 600)
        profile_dialog.show()