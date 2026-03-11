import uvicorn
from fastapi import FastAPI
import socketio
from database import TasksSessionLocal
from services.chat_service import ChatService

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)


@sio.event
async def join_room(sid, data):
    project_id = data.get("project_id")
    sio.enter_room(sid, f"project_{project_id}")


@sio.event
async def send_chat_msg(sid, data):
    # data: {"project_id": 1, "sender_id": 10, "content": "Привет!"}
    with TasksSessionLocal() as session:
        service = ChatService(session)
        formatted_msg = service.save_new_message(
            data['project_id'],
            data['sender_id'],
            data['content']
        )

        # Рассылаем всем в комнате проекта
        await sio.emit("new_message", formatted_msg, room=f"project_{data['project_id']}")


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8080)