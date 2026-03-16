import socketio

# Создаем экземпляр клиента
sio = socketio.Client(
    reconnection=True,
    logger=True, # Включи, чтобы увидеть детали ошибки в консоли
    engineio_logger=True
)

def connect_to_server(url="http://localhost:8081"):
    try:
        if not sio.connected:
            # Попробуй сначала только websocket или убери это, если не поможет
            sio.connect(url, transports=['websocket', 'polling'])
            print(f"✅ Успешное подключение к Socket.IO: {url}")
    except Exception as e:
        print(f"❌ Ошибка подключения к сокету: {e}")

# Можно сразу навесить базовые обработчики для отладки
@sio.event
def connect():
    print("Соединение установлено!")

@sio.event
def disconnect():
    print("Соединение разорвано!")