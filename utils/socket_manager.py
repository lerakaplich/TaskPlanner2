# utils/socket_manager.py

import socketio
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocketClient(QObject):
    """Клиент для работы с Socket.IO сервером с поддержкой сигналов PyQt"""

    # Сигналы для связи с GUI
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)

    # Сигналы чата
    chat_created = pyqtSignal(dict)
    chat_deleted = pyqtSignal(dict)
    new_message = pyqtSignal(dict)
    message_edited = pyqtSignal(dict)
    message_deleted = pyqtSignal(dict)
    participants_updated = pyqtSignal(dict)
    messages_read = pyqtSignal(dict)

    # Сигналы аутентификации
    auth_success = pyqtSignal(dict)
    online_users = pyqtSignal(dict)

    # Сигналы операций
    operation_success = pyqtSignal(dict)
    operation_error = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # Создаем экземпляр Socket.IO клиента
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # бесконечные попытки
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=True,
            engineio_logger=True
        )

        self.connected_flag = False
        self.user_id = None
        self.server_url = None

        # Таймер для переподключения
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(5000)  # 5 секунд
        self.reconnect_timer.timeout.connect(self._try_reconnect)

        # Настройка обработчиков
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка всех обработчиков событий"""

        # ===== Базовые события =====
        @self.sio.event
        def connect():
            """Обработчик подключения к серверу"""
            logger.info("✅ Соединение с сервером установлено!")
            self.connected_flag = True
            self.reconnect_timer.stop()
            self.connected.emit()

            # Если есть user_id, авторизуемся
            if self.user_id:
                self.authenticate(self.user_id)

        @self.sio.event
        def disconnect():
            """Обработчик отключения от сервера"""
            logger.info("❌ Соединение с сервером разорвано")
            self.connected_flag = False
            self.disconnected.emit()

            # Запускаем попытки переподключения
            if self.server_url:
                self.reconnect_timer.start()

        @self.sio.event
        def connect_error(data):
            """Обработчик ошибки подключения"""
            logger.error(f"❌ Ошибка подключения: {data}")
            self.connection_error.emit(str(data))
            self.reconnect_timer.start()

        # ===== Аутентификация =====
        @self.sio.on('auth_success')
        def on_auth_success(data):
            """Успешная аутентификация"""
            logger.info(f"✅ Аутентификация успешна для пользователя {data.get('user_id')}")
            self.auth_success.emit(data)

        # ===== События чатов =====
        @self.sio.on('chat_created')
        def on_chat_created(data):
            """Создан новый чат"""
            logger.info(f"📢 Создан новый чат: {data.get('id')}")
            self.chat_created.emit(data)

        @self.sio.on('chat_deleted')
        def on_chat_deleted(data):
            """Чат удален"""
            logger.info(f"🗑️ Чат удален: {data.get('chat_id')}")
            self.chat_deleted.emit(data)

        # ===== События сообщений =====
        @self.sio.on('new_message')
        def on_new_message(data):
            """Новое сообщение"""
            logger.info(f"📨 Новое сообщение в чате {data.get('chat_id')} от {data.get('sender_id')}")
            self.new_message.emit(data)

        @self.sio.on('message_edited')
        def on_message_edited(data):
            """Сообщение отредактировано"""
            logger.info(f"✏️ Сообщение {data.get('message_id')} отредактировано")
            self.message_edited.emit(data)

        @self.sio.on('message_deleted')
        def on_message_deleted(data):
            """Сообщение удалено"""
            logger.info(f"🗑️ Сообщение {data.get('message_id')} удалено")
            self.message_deleted.emit(data)

        # ===== События участников =====
        @self.sio.on('participants_updated')
        def on_participants_updated(data):
            """Обновлен список участников"""
            logger.info(f"👥 Участники чата {data.get('chat_id')} обновлены")
            self.participants_updated.emit(data)

        # ===== События прочтения =====
        @self.sio.on('messages_read_update')
        def on_messages_read(data):
            """Сообщения прочитаны"""
            logger.info(f"👁️ Сообщения прочитаны в чате {data.get('chat_id')}")
            self.messages_read.emit(data)

        # ===== События онлайн статуса =====
        @self.sio.on('online_users')
        def on_online_users(data):
            """Список онлайн пользователей"""
            self.online_users.emit(data)

        # ===== События операций =====
        @self.sio.on('operation_success')
        def on_operation_success(data):
            """Успешное выполнение операции"""
            logger.info(f"✅ Операция успешна: {data.get('operation')}")
            self.operation_success.emit(data)

        @self.sio.on('operation_error')
        def on_operation_error(data):
            """Ошибка выполнения операции"""
            logger.error(f"❌ Ошибка операции: {data.get('error')}")
            self.operation_error.emit(data)

    def connect_to_server(self, url="http://localhost:8082"):
        """
        Подключение к серверу

        Args:
            url (str): URL сервера (например, "http://localhost:8081")
        """
        self.server_url = url

        if self.sio.connected:
            logger.info("⚠️ Уже подключен к серверу")
            return

        try:
            logger.info(f"🔄 Подключение к серверу {url}...")
            # Пробуем подключиться с поддержкой WebSocket и polling
            self.sio.connect(
                url,
                transports=['websocket', 'polling'],
                wait_timeout=10,
                wait=True
            )
            logger.info(f"✅ Успешное подключение к Socket.IO: {url}")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к сокету: {e}")
            self.connection_error.emit(str(e))
            self.reconnect_timer.start()

    def disconnect_from_server(self):
        """Отключение от сервера"""
        self.reconnect_timer.stop()
        if self.sio.connected:
            self.sio.disconnect()
            logger.info("🔌 Отключение от сервера")

    def _try_reconnect(self):
        """Попытка переподключения к серверу"""
        if not self.sio.connected and self.server_url:
            logger.info("🔄 Попытка переподключения...")
            try:
                self.sio.connect(
                    self.server_url,
                    transports=['websocket', 'polling'],
                    wait_timeout=5
                )
            except Exception as e:
                logger.debug(f"Переподключение не удалось: {e}")

    def authenticate(self, user_id):
        """
        Аутентификация пользователя на сервере

        Args:
            user_id (int): ID пользователя
        """
        self.user_id = user_id
        if self.sio.connected:
            logger.info(f"🔑 Аутентификация пользователя {user_id}")
            self.sio.emit('auth_user', {'user_id': user_id})
        else:
            logger.warning("⚠️ Не удалось аутентифицироваться: нет подключения к серверу")

    def emit(self, event, data):
        """
        Отправка события на сервер

        Args:
            event (str): Название события
            data (dict): Данные для отправки

        Returns:
            bool: Успешность отправки
        """
        if self.sio.connected:
            self.sio.emit(event, data)
            logger.debug(f"📤 Отправлено событие {event}")
            return True
        else:
            logger.warning(f"⚠️ Не удалось отправить {event}: нет подключения к серверу")
            self.connection_error.emit(f"Невозможно отправить {event}: нет подключения")
            return False

    def join_chat_room(self, chat_id):
        """
        Присоединиться к комнате чата

        Args:
            chat_id (int): ID чата
        """
        if self.sio.connected:
            self.sio.emit('join_chat', {'chat_id': chat_id})
            logger.info(f"👥 Присоединение к комнате чата {chat_id}")

    def leave_chat_room(self, chat_id):
        """
        Покинуть комнату чата

        Args:
            chat_id (int): ID чата
        """
        if self.sio.connected:
            self.sio.emit('leave_chat', {'chat_id': chat_id})
            logger.info(f"👋 Выход из комнаты чата {chat_id}")

    def send_message(self, chat_id, sender_id, content, reply_to_id=None):
        """
        Отправка сообщения в чат

        Args:
            chat_id (int): ID чата
            sender_id (int): ID отправителя
            content (str): Текст сообщения
            reply_to_id (int, optional): ID сообщения для ответа
        """
        data = {
            'chat_id': chat_id,
            'sender_id': sender_id,
            'content': content
        }
        if reply_to_id:
            data['reply_to_id'] = reply_to_id

        self.emit('send_chat_msg', data)

    def edit_message(self, message_id, chat_id, content):
        """
        Редактирование сообщения

        Args:
            message_id (int): ID сообщения
            chat_id (int): ID чата
            content (str): Новый текст
        """
        self.emit('edit_chat_msg', {
            'message_id': message_id,
            'chat_id': chat_id,
            'content': content
        })

    def delete_message(self, message_id, chat_id, user_id, mode='everyone'):
        """
        Удаление сообщения

        Args:
            message_id (int): ID сообщения
            chat_id (int): ID чата
            user_id (int): ID пользователя
            mode (str): 'everyone' или 'me'
        """
        self.emit('delete_chat_msg', {
            'message_id': message_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'mode': mode
        })

    def forward_message(self, message_id, target_chat_id, user_id):
        """
        Пересылка сообщения

        Args:
            message_id (int): ID сообщения
            target_chat_id (int): ID целевого чата
            user_id (int): ID пользователя
        """
        self.emit('forward_message', {
            'message_id': message_id,
            'target_chat_id': target_chat_id,
            'user_id': user_id
        })

    def mark_messages_as_read(self, chat_id, user_id, message_ids):
        """
        Отметить сообщения как прочитанные

        Args:
            chat_id (int): ID чата
            user_id (int): ID пользователя
            message_ids (list): Список ID сообщений
        """
        self.emit('messages_seen', {
            'chat_id': chat_id,
            'user_id': user_id,
            'message_ids': message_ids
        })

    def create_chat(self, creator_id, title, chat_type, participants):
        """
        Создание нового чата

        Args:
            creator_id (int): ID создателя
            title (str): Название чата
            chat_type (str): 'private' или 'group'
            participants (list): Список ID участников
        """
        self.emit('create_chat', {
            'creator_id': creator_id,
            'title': title,
            'type': chat_type,
            'participants': participants
        })

    def delete_chat(self, chat_id):
        """
        Удаление чата

        Args:
            chat_id (int): ID чата
        """
        self.emit('delete_chat', {'chat_id': chat_id})

    def update_participants(self, chat_id, added_users=None, removed_users=None):
        """
        Обновление участников чата

        Args:
            chat_id (int): ID чата
            added_users (list): Список ID добавляемых пользователей
            removed_users (list): Список ID удаляемых пользователей
        """
        data = {'chat_id': chat_id}
        if added_users:
            data['added_users'] = added_users
        if removed_users:
            data['removed_users'] = removed_users

        self.emit('update_participants', data)

    def get_online_users(self):
        """Запрос списка онлайн пользователей"""
        self.emit('get_online_users', {})

    def is_connected(self):
        """
        Проверка состояния подключения

        Returns:
            bool: True если подключен
        """
        return self.sio.connected

    def get_socket_id(self):
        """
        Получение ID сокета

        Returns:
            str: ID сокета или None
        """
        return self.sio.sid if self.sio.connected else None


# ===== Глобальный экземпляр для использования во всем приложении =====
_socket_client_instance = None


def get_socket_client():
    """
    Получить глобальный экземпляр SocketClient (синглтон)

    Returns:
        SocketClient: Экземпляр клиента
    """
    global _socket_client_instance
    if _socket_client_instance is None:
        _socket_client_instance = SocketClient()
    return _socket_client_instance

# Для обратной совместимости - создаем глобальный экземпляр sio
sio = get_socket_client().sio if get_socket_client() else None