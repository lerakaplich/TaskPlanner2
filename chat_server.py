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
async def forward_message(sid, data):
    # data: {"message_id": 100, "to_chat_id": 5, "current_user_id": 10}
    with TasksSessionLocal() as session:
        service = ChatService(session)
        formatted_msg = service.forward_message(
            data['message_id'],
            data['to_chat_id'],
            data['current_user_id']
        )

        if formatted_msg:
            # Рассылаем в тот чат, КУДА переслали
            await sio.emit("new_message", formatted_msg.model_dump(), room=f"chat_{data['to_chat_id']}")

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