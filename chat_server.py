import uvicorn
from fastapi import FastAPI
import socketio
from database import TasksSessionLocal
from services.chat_service import ChatService

user_sid_map = {}  # {user_id: sid}

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True, # Включи логгер для отладки
    engineio_logger=True
)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)

@sio.event
async def connect(sid, environ):
    # На сервере sid и environ ОБЯЗАТЕЛЬНЫ
    print(f"Socket connected: {sid}")


@sio.event
async def auth_user(sid, data):
    user_id = data.get("user_id")
    if user_id:
        user_sid_map[user_id] = sid
        print(f"🔑 Пользователь {user_id} привязан к сокету {sid}")

        with TasksSessionLocal() as session:
            service = ChatService(session)
            user_chats = service.get_user_chats(user_id)
            print(f"📋 Найдено чатов для пользователя {user_id}: {len(user_chats)}")

            for chat in user_chats:
                room_name = f"chat_{chat.id}"
                await sio.enter_room(sid, room_name)
                print(f"  └─ User {user_id} авто-вход в {room_name}")

        # 👇 ОТПРАВЛЯЕМ ПОДТВЕРЖДЕНИЕ
        await sio.emit("auth_success", {
            "user_id": user_id,
            "status": "ok",
            "chats_count": len(user_chats)
        }, to=sid)
        print(f"✅ Отправлен auth_success для пользователя {user_id}")

        print(f"Текущие онлайн: {user_sid_map}")

@sio.event
async def disconnect(sid):
    # Удаляем из маппинга по sid
    for uid, s in list(user_sid_map.items()):
        if s == sid:
            del user_sid_map[uid]
            print(f"🚫 Пользователь {uid} отключился")
            break


@sio.event
async def create_chat(sid, data):
    # data = {"title": "...", "type": "group", "participants": [1, 5], "creator_id": 1}
    with TasksSessionLocal() as session:
        service = ChatService(session)
        new_chat_dto = service.create_new_chat(data['creator_id'], data)

        payload = new_chat_dto.model_dump(mode='json')

        # Оповещаем всех, кто онлайн
        for user_id in data['participants']:
            target_sid = user_sid_map.get(user_id)
            if target_sid:
                await sio.emit("chat_created", payload, to=target_sid)

@sio.event
async def delete_chat(sid, data):
    chat_id = data['chat_id']
    with TasksSessionLocal() as session:
        service = ChatService(session)
        if service.delete_chat(chat_id):
            await sio.emit("chat_deleted", {"chat_id": chat_id}, room=f"chat_{chat_id}")
            # После этого все клиенты в этой комнате должны принудительно выйти из чата


@sio.event
async def update_participants(sid, data):
    chat_id = data['chat_id']
    added = data.get('added_users', [])
    removed = data.get('removed_users', [])

    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            if service.update_chat_participants(chat_id, added, removed):
                # 1. Рассылаем уведомление тем, кто уже в чате
                await sio.emit("participants_updated", data, room=f"chat_{chat_id}")

                # 2. Тем, кого добавили: отправляем 'chat_created' с данными чата
                if added:
                    for uid in added:
                        target_sid = user_sid_map.get(uid)
                        if target_sid:
                            await sio.enter_room(target_sid, f"chat_{chat_id}")
                            # Шлем ему сигнал обновить список чатов
                            await sio.emit("chat_added_manual", {"id": chat_id}, to=target_sid)

                # 3. Тем, кого удалили: шлем сигнал на удаление из списка
                for uid in removed:
                    target_sid = user_sid_map.get(uid)
                    if target_sid:
                        await sio.emit("chat_deleted", {"chat_id": chat_id}, to=target_sid)
    except Exception as e:
        print(f"❌ Ошибка в update_participants: {e}")


@sio.event
async def change_participant_role(sid, data):
    chat_id = data['chat_id']
    target_uid = data['target_user_id']
    is_admin = data['is_admin']

    with TasksSessionLocal() as session:
        service = ChatService(session)
        if service.set_participant_admin(chat_id, target_uid, is_admin):
            # Рассылаем ВСЕМ в комнату чата
            await sio.emit("participant_role_changed", {
                "chat_id": chat_id,
                "user_id": target_uid,
                "is_admin": is_admin
            }, room=f"chat_{chat_id}")

@sio.event
async def send_chat_msg(sid, data):
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

            # МОМЕНТ ИСТИНЫ:
            # Используем mode='json', чтобы Pydantic сам превратил datetime в строку
            formatted_data = msg_dto.model_dump(mode='json')

            print(f"Emitting to room chat_{data['chat_id']}")
            await sio.emit("new_message", formatted_data, room=f"chat_{data['chat_id']}")

    except Exception as e:
        print(f"❌ Server Error in send_chat_msg: {e}")


@sio.event
async def edit_chat_msg(sid, data):
    # data: {"message_id": 123, "content": "текст", "chat_id": 5}
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            # Вызываем твой метод из ChatService
            success = service.update_message(data['message_id'], data['content'])

            if success:
                # Оповещаем ВСЕХ в комнате чата
                await sio.emit("message_edited", {
                    "message_id": data['message_id'],
                    "new_content": data['content'],
                    "chat_id": data['chat_id']
                }, room=f"chat_{data['chat_id']}")
    except Exception as e:
        print(f"❌ Ошибка сервера при правке: {e}")


@sio.event
async def delete_chat_msg(sid, data):
    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            mode = data.get('mode', 'everyone')

            if mode == "everyone":
                if service.delete_message_for_everyone(data['message_id']):
                    # Рассылаем ВСЕМ в комнате
                    await sio.emit("message_deleted", {
                        "message_id": data['message_id'],
                        "chat_id": data['chat_id'],
                        "mode": "everyone"
                    }, room=f"chat_{data['chat_id']}")
            else:
                service.delete_message_for_me(data['message_id'], data['user_id'])
                # Подтверждаем только отправителю
                await sio.emit("message_deleted", data, to=sid)
    except Exception as e:
        print(f"❌ Server Error: {e}")


@sio.event
async def forward_message(sid, data):
    # data: {"message_id": 100, "target_chat_id": 5, "user_id": 10}
    msg_id = data.get('message_id')
    target_chat_id = data.get('target_chat_id')
    user_id = data.get('user_id')

    try:
        with TasksSessionLocal() as session:
            service = ChatService(session)
            # Вызываем метод пересылки в ChatService
            new_msg_dto = service.forward_message(msg_id, target_chat_id, user_id)

            if new_msg_dto:
                # ВАЖНО: mode='json' превращает datetime в строку, иначе сокет упадет
                formatted_data = new_msg_dto.model_dump(mode='json')

                print(f"🚀 Сообщение переслано в комнату chat_{target_chat_id}")
                await sio.emit("new_message", formatted_data, room=f"chat_{target_chat_id}")
    except Exception as e:
        print(f"❌ Ошибка сервера при пересылке: {e}")

@sio.event
async def messages_seen(sid, data):
    # data = {"chat_id": 1, "user_id": 3, "message_ids": [101, 102]}
    with TasksSessionLocal() as session:
        service = ChatService(session)
        service.mark_messages_as_read(data['user_id'], data['message_ids'])

        # Оповещаем остальных в комнате, что сообщения прочитаны
        await sio.emit("messages_read_update", {
            "chat_id": data['chat_id'],
            "message_ids": data['message_ids']
        }, room=f"chat_{data['chat_id']}")

@sio.event
async def join_chat(sid, data):
    chat_id = data.get("chat_id")
    # ОБЯЗАТЕЛЬНО await!
    await sio.enter_room(sid, f"chat_{chat_id}")
    print(f"User {sid} joined room chat_{chat_id}")

@sio.event
async def leave_chat(sid, data):
    chat_id = data.get("chat_id")
    # ОБЯЗАТЕЛЬНО await!
    await sio.leave_room(sid, f"chat_{chat_id}")


@sio.event
async def update_chat_settings(sid, data):
    chat_id = data.get('chat_id')
    new_title = data.get('new_title')

    # Рассылаем всем в комнате f"chat_{chat_id}"
    await sio.emit("chat_info_updated", {
        "chat_id": chat_id,
        "new_title": new_title
    }, room=f"chat_{chat_id}")


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8082)