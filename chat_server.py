# chat_server.py

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio
import os
import sys
from pathlib import Path

# Добавляем путь к проекту для импортов
sys.path.append(str(Path(__file__).parent))

from database import TasksSessionLocal
from services.chat_service import ChatService

# Словарь для хранения соответствия user_id -> sid
user_sid_map = {}  # {user_id: sid}

# Настройка Socket.IO сервера
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # В продакшене заменить на конкретный домен
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Создаем FastAPI приложение
app = FastAPI(title="TaskPlanner Server")

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем ASGI приложение с Socket.IO
socket_app = socketio.ASGIApp(sio, app)


# Монтируем статические файлы (если нужно)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== Socket.IO Events ====================

@sio.event
async def connect(sid, environ):
    """Обработчик подключения клиента"""
    print(f"🔌 Socket connected: {sid}")
    client_ip = environ.get('REMOTE_ADDR', 'unknown')
    print(f"   Client IP: {client_ip}")


@sio.event
async def disconnect(sid):
    """Обработчик отключения клиента"""
    # Удаляем из маппинга по sid
    for uid, s in list(user_sid_map.items()):
        if s == sid:
            del user_sid_map[uid]
            print(f"🚫 Пользователь {uid} отключился")
            break
    print(f"🔌 Socket disconnected: {sid}")
    print(f"📊 Текущие онлайн: {len(user_sid_map)} пользователей")


@sio.event
async def auth_user(sid, data):
    """Аутентификация пользователя и привязка к сокету"""
    user_id = data.get("user_id")
    if user_id:
        # Если пользователь уже был подключен с другого устройства, удаляем старую запись
        if user_id in user_sid_map:
            old_sid = user_sid_map[user_id]
            print(f"⚠️ Пользователь {user_id} уже был подключен с {old_sid}, обновляем")

        user_sid_map[user_id] = sid
        print(f"🔑 Пользователь {user_id} привязан к сокету {sid}")
        print(f"📊 Текущие онлайн: {list(user_sid_map.keys())}")

        # Отправляем подтверждение клиенту
        await sio.emit("auth_success", {"user_id": user_id, "online_count": len(user_sid_map)}, to=sid)


@sio.event
async def get_online_users(sid, data):
    """Получение списка онлайн пользователей"""
    await sio.emit("online_users", {"online_users": list(user_sid_map.keys())}, to=sid)


@sio.event
async def create_chat(sid, data):
    """Создание нового чата"""
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            new_chat_dto = service.create_new_chat(data['creator_id'], data)

            payload = new_chat_dto.model_dump(mode='json')

            # Оповещаем всех участников, кто онлайн
            notified_users = []
            for user_id in data['participants']:
                target_sid = user_sid_map.get(user_id)
                if target_sid:
                    await sio.emit("chat_created", payload, to=target_sid)
                    notified_users.append(user_id)

            print(f"✅ Чат {new_chat_dto.id} создан, уведомлены: {notified_users}")

            # Отправляем подтверждение создателю
            await sio.emit("operation_success", {
                "operation": "create_chat",
                "chat_id": new_chat_dto.id,
                "message": "Чат успешно создан"
            }, to=sid)

    except Exception as e:
        print(f"❌ Ошибка создания чата: {e}")
        await sio.emit("operation_error", {
            "operation": "create_chat",
            "error": str(e)
        }, to=sid)


@sio.event
async def delete_chat(sid, data):
    """Удаление чата"""
    try:
        chat_id = data['chat_id']
        with TasksSessionLocal() as session:
            service = ChatService(session)
            if service.delete_chat(chat_id):
                # Оповещаем всех в комнате чата
                await sio.emit("chat_deleted", {"chat_id": chat_id}, room=f"chat_{chat_id}")
                print(f"✅ Чат {chat_id} удален")

                await sio.emit("operation_success", {
                    "operation": "delete_chat",
                    "chat_id": chat_id
                }, to=sid)
            else:
                raise Exception("Чат не найден или не может быть удален")

    except Exception as e:
        print(f"❌ Ошибка удаления чата: {e}")
        await sio.emit("operation_error", {
            "operation": "delete_chat",
            "error": str(e)
        }, to=sid)


@sio.event
async def update_participants(sid, data):
    """Обновление участников чата"""
    try:
        chat_id = data['chat_id']
        added = data.get('added_users', [])
        removed = data.get('removed_users', [])

        with TasksSessionLocal() as session:
            service = ChatService(session)
            if service.update_chat_participants(chat_id, added, removed):
                # 1. Рассылаем системное уведомление в комнату чата
                await sio.emit("participants_updated", {
                    "chat_id": chat_id,
                    "added": added,
                    "removed": removed
                }, room=f"chat_{chat_id}")

                # 2. Тем, кого добавили, шлем 'chat_created'
                for uid in added:
                    target_sid = user_sid_map.get(uid)
                    if target_sid:
                        # Получаем полную информацию о чате
                        chat_info = service.get_chat_by_id(chat_id, uid)
                        if chat_info:
                            await sio.emit("chat_created", chat_info.model_dump(mode='json'), to=target_sid)

                # 3. Тем, кого удалили, шлем 'chat_deleted'
                for uid in removed:
                    target_sid = user_sid_map.get(uid)
                    if target_sid:
                        await sio.emit("chat_deleted", {"chat_id": chat_id}, to=target_sid)

                print(f"✅ Участники чата {chat_id} обновлены: +{added}, -{removed}")

                await sio.emit("operation_success", {
                    "operation": "update_participants",
                    "chat_id": chat_id
                }, to=sid)

    except Exception as e:
        print(f"❌ Ошибка обновления участников: {e}")
        await sio.emit("operation_error", {
            "operation": "update_participants",
            "error": str(e)
        }, to=sid)


@sio.event
async def send_chat_msg(sid, data):
    """Отправка сообщения в чат"""
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            # Сохраняем сообщение
            msg_dto = service.save_new_message(
                chat_id=data['chat_id'],
                sender_id=data['sender_id'],
                content=data['content'],
                reply_to_id=data.get('reply_to_id')
            )

            # Конвертируем в JSON
            formatted_data = msg_dto.model_dump(mode='json')

            print(f"📨 Новое сообщение в чат {data['chat_id']} от {data['sender_id']}")
            await sio.emit("new_message", formatted_data, room=f"chat_{data['chat_id']}")

    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        await sio.emit("operation_error", {
            "operation": "send_message",
            "error": str(e)
        }, to=sid)


@sio.event
async def edit_chat_msg(sid, data):
    """Редактирование сообщения"""
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            success = service.update_message(data['message_id'], data['content'])

            if success:
                await sio.emit("message_edited", {
                    "message_id": data['message_id'],
                    "new_content": data['content'],
                    "chat_id": data['chat_id']
                }, room=f"chat_{data['chat_id']}")

                print(f"✏️ Сообщение {data['message_id']} отредактировано")

    except Exception as e:
        print(f"❌ Ошибка редактирования: {e}")
        await sio.emit("operation_error", {
            "operation": "edit_message",
            "error": str(e)
        }, to=sid)


@sio.event
async def delete_chat_msg(sid, data):
    """Удаление сообщения"""
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            mode = data.get('mode', 'everyone')

            if mode == "everyone":
                if service.delete_message_for_everyone(data['message_id']):
                    await sio.emit("message_deleted", {
                        "message_id": data['message_id'],
                        "chat_id": data['chat_id'],
                        "mode": "everyone"
                    }, room=f"chat_{data['chat_id']}")
                    print(f"🗑️ Сообщение {data['message_id']} удалено для всех")
            else:
                service.delete_message_for_me(data['message_id'], data['user_id'])
                await sio.emit("message_deleted", data, to=sid)
                print(f"👤 Сообщение {data['message_id']} удалено для пользователя {data['user_id']}")

    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
        await sio.emit("operation_error", {
            "operation": "delete_message",
            "error": str(e)
        }, to=sid)


@sio.event
async def forward_message(sid, data):
    """Пересылка сообщения"""
    try:
        msg_id = data.get('message_id')
        target_chat_id = data.get('target_chat_id')
        user_id = data.get('user_id')

        with TasksSessionLocal() as session:
            service = ChatService(session)
            new_msg_dto = service.forward_message(msg_id, target_chat_id, user_id)

            if new_msg_dto:
                formatted_data = new_msg_dto.model_dump(mode='json')
                await sio.emit("new_message", formatted_data, room=f"chat_{target_chat_id}")
                print(f"🔄 Сообщение {msg_id} переслано в чат {target_chat_id}")

    except Exception as e:
        print(f"❌ Ошибка пересылки: {e}")
        await sio.emit("operation_error", {
            "operation": "forward_message",
            "error": str(e)
        }, to=sid)


@sio.event
async def messages_seen(sid, data):
    """Отметка о прочтении сообщений"""
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            service.mark_messages_as_read(data['user_id'], data['message_ids'])

            # Оповещаем остальных в комнате
            await sio.emit("messages_read_update", {
                "chat_id": data['chat_id'],
                "message_ids": data['message_ids'],
                "user_id": data['user_id']
            }, room=f"chat_{data['chat_id']}")

            print(f"👁️ Сообщения {data['message_ids']} прочитаны пользователем {data['user_id']}")

    except Exception as e:
        print(f"❌ Ошибка отметки прочтения: {e}")


@sio.event
async def join_chat(sid, data):
    """Присоединение к комнате чата"""
    try:
        chat_id = data.get("chat_id")
        await sio.enter_room(sid, f"chat_{chat_id}")
        print(f"👥 Клиент {sid} присоединился к комнате chat_{chat_id}")

    except Exception as e:
        print(f"❌ Ошибка присоединения к комнате: {e}")


@sio.event
async def leave_chat(sid, data):
    """Покидание комнаты чата"""
    try:
        chat_id = data.get("chat_id")
        await sio.leave_room(sid, f"chat_{chat_id}")
        print(f"👋 Клиент {sid} покинул комнату chat_{chat_id}")

    except Exception as e:
        print(f"❌ Ошибка покидания комнаты: {e}")


# ==================== HTTP Endpoints ====================

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "TaskPlanner Server",
        "status": "running",
        "online_users": len(user_sid_map),
        "socketio_path": "/socket.io/"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "online_users": len(user_sid_map),
        "database": "connected"  # Добавить реальную проверку БД
    }


@app.get("/stats")
async def get_stats():
    """Статистика сервера"""
    return {
        "online_users": len(user_sid_map),
        "online_users_list": list(user_sid_map.keys()),
        "server_uptime": "TODO"  # Можно добавить время работы
    }


# ==================== Запуск сервера ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TaskPlanner Chat Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8081, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print("=" * 50)
    print("🚀 TaskPlanner Server Starting...")
    print(f"📡 Host: {args.host}")
    print(f"🔌 Port: {args.port}")
    print(f"🔄 Auto-reload: {args.reload}")
    print("=" * 50)

    uvicorn.run(
        "chat_server:socket_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )