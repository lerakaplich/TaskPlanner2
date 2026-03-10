# Проверка текущего пользователя, его прав (admin/user) при запуске.

class UserSession:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSession, cls).__new__(cls)
            cls._instance.user_id = None
            cls._instance.username = None
            cls._instance.role = None
        return cls._instance

    def set_user(self, user_id, username, role):
        self.user_id = user_id
        self.username = username
        self.role = role

    def is_authenticated(self):
        return self.user_id is not None