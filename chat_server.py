import uvicorn
from fastapi import FastAPI
import socketio
from database import TasksSessionLocal
from services.chat_service import ChatService

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True, # Включи логгер для отладки
    engineio_logger=True
)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)


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


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8081)