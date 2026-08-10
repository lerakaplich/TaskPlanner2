# chat_server.py
from datetime import datetime

import uvicorn
import socketio
import asyncio
from fastapi import FastAPI
from sqlalchemy import select

from database import get_tasks_session
from services.chat_service import ChatService
from server_app.services.tasks_service.task_data_collector import get_task_data_collector
from server_app.services.training_scheduler import get_training_scheduler  # ← ИСПРАВЛЕНО
from shared_state import pending_registrations

user_sid_map = {}

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)


def get_chat_service():
    """Получить сервис чата с автоматическим закрытием сессии"""
    session = get_tasks_session()
    return ChatService(session), session


@sio.event
async def task_completed(sid, data):
    """
    Клиент сообщает о завершении задачи.
    Сервер дообучает модель в реальном времени.
    """
    task_id = data.get('task_id')
    user_id = data.get('user_id')

    if not task_id:
        return

    try:
        # 1. Сохраняем данные задачи
        collector = get_task_data_collector()

        # Используем правильный метод для сбора данных
        task_data = collector.collect_and_save_task(task_id)

        if not task_data:
            await sio.emit("task_training_error", {
                "task_id": task_id,
                "error": "Не удалось собрать данные о задаче"
            }, to=sid)
            return

        # 2. Получаем статистику
        stats = collector.get_training_stats()

        # 3. Отправляем результат клиенту
        await sio.emit("task_training_completed", {
            "task_id": task_id,
            "status": "success" if stats.get('can_train', False) else "pending",
            "total_completed": stats.get('completed_tasks', 0),
            "min_samples": stats.get('min_samples', 10),
            "can_train": stats.get('can_train', False)
        }, to=sid)

    except Exception as e:
        print(f"❌ Ошибка обработки завершения задачи: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit("task_training_error", {
            "task_id": task_id,
            "error": str(e)
        }, to=sid)


@sio.event
async def connect(sid, environ):
    print(f"🔌 Socket connected: {sid}")


@sio.event
async def disconnect(sid):
    for uid, s in list(user_sid_map.items()):
        if s == sid:
            del user_sid_map[uid]
            print(f"🚫 Пользователь {uid} отключился")
            break


@sio.event
async def auth_user(sid, data):
    user_id = data.get("user_id")
    if not user_id:
        return

    user_sid_map[user_id] = sid
    print(f"🔑 Пользователь {user_id} привязан к сокету {sid}")

    service, session = get_chat_service()
    try:
        user_chats = service.get_user_chats(user_id)
        for chat in user_chats:
            await sio.enter_room(sid, f"chat_{chat.id}")

        await sio.emit("auth_success", {
            "user_id": user_id,
            "status": "ok",
            "chats_count": len(user_chats)
        }, to=sid)
    finally:
        session.close()


@sio.event
async def request_registration(sid, data):
    print(f"📝 Запрос на регистрацию: {data.get('last_name')} {data.get('first_name')}")
    request_id = sid
    data['request_id'] = request_id
    data['chat_id'] = None
    data['chat_id_bound'] = False
    pending_registrations[request_id] = data


@sio.event
async def create_chat(sid, data):
    service, session = get_chat_service()
    try:
        new_chat_dto = service.create_new_chat(data['creator_id'], data)
        payload = new_chat_dto.model_dump(mode='json')
        for user_id in data['participants']:
            target_sid = user_sid_map.get(user_id)
            if target_sid:
                await sio.emit("chat_created", payload, to=target_sid)
    finally:
        session.close()


@sio.event
async def delete_chat(sid, data):
    chat_id = data['chat_id']
    service, session = get_chat_service()
    try:
        if service.delete_chat(chat_id):
            await sio.emit("chat_deleted", {"chat_id": chat_id}, room=f"chat_{chat_id}")
    finally:
        session.close()


@sio.event
async def update_participants(sid, data):
    chat_id = data['chat_id']
    added = data.get('added_users', [])
    removed = data.get('removed_users', [])

    service, session = get_chat_service()
    try:
        if service.update_chat_participants(chat_id, added, removed):
            await sio.emit("participants_updated", data, room=f"chat_{chat_id}")
            for uid in added:
                target_sid = user_sid_map.get(uid)
                if target_sid:
                    await sio.enter_room(target_sid, f"chat_{chat_id}")
                    await sio.emit("chat_added_manual", {"id": chat_id}, to=target_sid)
            for uid in removed:
                target_sid = user_sid_map.get(uid)
                if target_sid:
                    await sio.emit("chat_deleted", {"chat_id": chat_id}, to=target_sid)
    finally:
        session.close()


@sio.event
async def change_participant_role(sid, data):
    chat_id = data['chat_id']
    target_uid = data['target_user_id']
    is_admin = data['is_admin']

    service, session = get_chat_service()
    try:
        if service.set_participant_admin(chat_id, target_uid, is_admin):
            await sio.emit("participant_role_changed", {
                "chat_id": chat_id,
                "user_id": target_uid,
                "is_admin": is_admin
            }, room=f"chat_{chat_id}")
    finally:
        session.close()


@sio.event
async def send_chat_msg(sid, data):
    service, session = get_chat_service()
    try:
        msg_dto = service.save_new_message(
            chat_id=data['chat_id'],
            sender_id=data['sender_id'],
            content=data['content'],
            reply_to_id=data.get('reply_to_id')
        )
        await sio.emit("new_message", msg_dto.model_dump(mode='json'), room=f"chat_{data['chat_id']}")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
    finally:
        session.close()


@sio.event
async def edit_chat_msg(sid, data):
    service, session = get_chat_service()
    try:
        if service.update_message(data['message_id'], data['content']):
            await sio.emit("message_edited", {
                "message_id": data['message_id'],
                "new_content": data['content'],
                "chat_id": data['chat_id']
            }, room=f"chat_{data['chat_id']}")
    except Exception as e:
        print(f"❌ Ошибка при правке: {e}")
    finally:
        session.close()


@sio.event
async def delete_chat_msg(sid, data):
    service, session = get_chat_service()
    try:
        mode = data.get('mode', 'everyone')
        if mode == "everyone":
            if service.delete_message_for_everyone(data['message_id']):
                await sio.emit("message_deleted", {
                    "message_id": data['message_id'],
                    "chat_id": data['chat_id'],
                    "mode": "everyone"
                }, room=f"chat_{data['chat_id']}")
        else:
            service.delete_message_for_me(data['message_id'], data['user_id'])
            await sio.emit("message_deleted", data, to=sid)
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")
    finally:
        session.close()


@sio.event
async def forward_message(sid, data):
    service, session = get_chat_service()
    try:
        new_msg_dto = service.forward_message(
            data['message_id'], data['target_chat_id'], data['user_id']
        )
        if new_msg_dto:
            await sio.emit("new_message", new_msg_dto.model_dump(mode='json'), room=f"chat_{data['target_chat_id']}")
    except Exception as e:
        print(f"❌ Ошибка при пересылке: {e}")
    finally:
        session.close()


@sio.event
async def messages_seen(sid, data):
    service, session = get_chat_service()
    try:
        service.mark_messages_as_read(data['user_id'], data['message_ids'])
        await sio.emit("messages_read_update", {
            "chat_id": data['chat_id'],
            "message_ids": data['message_ids']
        }, room=f"chat_{data['chat_id']}")
    finally:
        session.close()


@sio.event
async def join_chat(sid, data):
    await sio.enter_room(sid, f"chat_{data['chat_id']}")


@sio.event
async def leave_chat(sid, data):
    await sio.leave_room(sid, f"chat_{data['chat_id']}")


@sio.event
async def update_chat_settings(sid, data):
    await sio.emit("chat_info_updated", {
        "chat_id": data['chat_id'],
        "new_title": data['new_title']
    }, room=f"chat_{data['chat_id']}")


async def main():
    print("🚀 Запуск сокет-сервера...")

    # Запускаем планировщик обучения
    try:
        scheduler = get_training_scheduler()
        scheduler.start()
        print("✅ Планировщик обучения запущен")
    except Exception as e:
        print(f"⚠️ Ошибка запуска планировщика: {e}")

    config = uvicorn.Config(socket_app, host="0.0.0.0", port=8081, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())