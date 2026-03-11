from database import get_tasks_session


class AnalyticsService:
    """
    Сервис аналитики.
    Только аналитика, никакой логики архива!
    """

    def __init__(self, session=None):
        self.session = session or get_tasks_session()
        self.current_user_id = None

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id

    # Здесь только методы аналитики, например:
    # def get_project_statistics(self):
    # def get_task_completion_rate(self):
    # и т.д.