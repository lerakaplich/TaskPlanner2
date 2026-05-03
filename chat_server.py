# chat_server.py
import uvicorn
from PyQt6.QtWidgets import QMessageBox
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI
from sqlalchemy import select
import socketio
import asyncio
from database import get_tasks_session, get_employees_session  # Исправлено
from services.chat_service import ChatService
from services.employee_service import EmployeeService  # Добавлен новый сервис

# Удаляем импорт sync_service
# from sync_service import sync_service
from shared_state import pending_registrations
from telegram_bot import telegram_bot, start_bot

user_sid_map = {}  # {user_id: sid}

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)


async def send_telegram_message(chat_id: int, text: str, reply_markup=None):
    """Быстрая отправка сообщения в Telegram"""
    try:
        await telegram_bot.bot.send_message(
            chat_id, text, parse_mode="Markdown", reply_markup=reply_markup
        )
        print(f"✅ Сообщение отправлено в чат {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки администратору {chat_id}: {e}")
        return False


@sio.event
async def connect(sid, environ):
    print(f"Socket connected: {sid}")


@sio.event
async def auth_user(sid, data):
    user_id = data.get("user_id")
    if user_id:
        user_sid_map[user_id] = sid
        print(f"🔑 Пользователь {user_id} привязан к сокету {sid}")

        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
            user_chats = service.get_user_chats(user_id)
            print(f"📋 Найдено чатов для пользователя {user_id}: {len(user_chats)}")

            for chat in user_chats:
                room_name = f"chat_{chat.id}"
                await sio.enter_room(sid, room_name)
                print(f"  └─ User {user_id} авто-вход в {room_name}")

        await sio.emit("auth_success", {
            "user_id": user_id,
            "status": "ok",
            "chats_count": len(user_chats)
        }, to=sid)
        print(f"✅ Отправлен auth_success для пользователя {user_id}")
        print(f"Текущие онлайн: {user_sid_map}")


@sio.event
async def disconnect(sid):
    for uid, s in list(user_sid_map.items()):
        if s == sid:
            del user_sid_map[uid]
            print(f"🚫 Пользователь {uid} отключился")
            break


def send_to_telegram_admin(self, employee_data):
    """Отправляет данные на одобрение администратору в Telegram"""
    try:
        from utils.socket_manager import get_socket_client

        employee_data['chat_id'] = None
        employee_data['request_id'] = None

        socket_client = get_socket_client()

        if not socket_client.is_connected():
            QMessageBox.warning(self, "Нет подключения", "Нет подключения к серверу. Попробуйте позже.")
            return

        socket_client.request_registration(employee_data)

        bot_link = "https://t.me/TaskPlanner2035Vikusik_bot"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Заявка отправлена")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(
            f"✅ Ваша заявка на регистрацию отправлена администратору!\n\n"
            f"📋 ФИО: {employee_data.get('last_name')} {employee_data.get('first_name')}\n"
            f"📞 Телефон: {employee_data.get('phone_number')}\n\n"
            f"📱 *Для получения пароля:*\n"
            f"1. Перейдите в Telegram бота:\n"
            f"   {bot_link}\n"
            f"2. Нажмите /start\n"
            f"3. Бот свяжет ваш аккаунт с заявкой\n"
            f"4. После одобрения вы получите пароль в Telegram\n\n"
            f"⏰ Обычно это занимает несколько минут."
        )

        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl

        open_bot_btn = msg_box.addButton("Перейти в Telegram бота", QMessageBox.ButtonRole.ActionRole)
        open_bot_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(bot_link)))

        msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    except Exception as e:
        QMessageBox.critical(self, "Ошибка", f"Не удалось отправить заявку: {e}")


@sio.event
async def request_registration(sid, data):
    print(f"📝 Получен запрос на регистрацию: {data.get('last_name')} {data.get('first_name')}")

    request_id = sid
    data['request_id'] = request_id
    data['chat_id'] = None
    data['chat_id_bound'] = False
    pending_registrations[request_id] = data

    print(f"🔑 Создана заявка с ID: {request_id}, ожидает привязки Telegram")
    print(f"📋 Всего заявок в pending: {len(pending_registrations)}")


@sio.event
async def create_chat(sid, data):
    with get_tasks_session() as session:  # Исправлено
        service = ChatService(session)
        new_chat_dto = service.create_new_chat(data['creator_id'], data)
        payload = new_chat_dto.model_dump(mode='json')
        for user_id in data['participants']:
            target_sid = user_sid_map.get(user_id)
            if target_sid:
                await sio.emit("chat_created", payload, to=target_sid)


@sio.event
async def delete_chat(sid, data):
    chat_id = data['chat_id']
    with get_tasks_session() as session:  # Исправлено
        service = ChatService(session)
        if service.delete_chat(chat_id):
            await sio.emit("chat_deleted", {"chat_id": chat_id}, room=f"chat_{chat_id}")


@sio.event
async def update_participants(sid, data):
    chat_id = data['chat_id']
    added = data.get('added_users', [])
    removed = data.get('removed_users', [])

    try:
        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
            if service.update_chat_participants(chat_id, added, removed):
                await sio.emit("participants_updated", data, room=f"chat_{chat_id}")
                if added:
                    for uid in added:
                        target_sid = user_sid_map.get(uid)
                        if target_sid:
                            await sio.enter_room(target_sid, f"chat_{chat_id}")
                            await sio.emit("chat_added_manual", {"id": chat_id}, to=target_sid)
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

    with get_tasks_session() as session:  # Исправлено
        service = ChatService(session)
        if service.set_participant_admin(chat_id, target_uid, is_admin):
            await sio.emit("participant_role_changed", {
                "chat_id": chat_id,
                "user_id": target_uid,
                "is_admin": is_admin
            }, room=f"chat_{chat_id}")


@sio.event
async def send_chat_msg(sid, data):
    try:
        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
            msg_dto = service.save_new_message(
                chat_id=data['chat_id'],
                sender_id=data['sender_id'],
                content=data['content'],
                reply_to_id=data.get('reply_to_id')
            )
            formatted_data = msg_dto.model_dump(mode='json')
            print(f"Emitting to room chat_{data['chat_id']}")
            await sio.emit("new_message", formatted_data, room=f"chat_{data['chat_id']}")
    except Exception as e:
        print(f"❌ Server Error in send_chat_msg: {e}")


@sio.event
async def edit_chat_msg(sid, data):
    try:
        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
            success = service.update_message(data['message_id'], data['content'])
            if success:
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
        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
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
        print(f"❌ Server Error: {e}")


@sio.event
async def forward_message(sid, data):
    msg_id = data.get('message_id')
    target_chat_id = data.get('target_chat_id')
    user_id = data.get('user_id')

    try:
        with get_tasks_session() as session:  # Исправлено
            service = ChatService(session)
            new_msg_dto = service.forward_message(msg_id, target_chat_id, user_id)
            if new_msg_dto:
                formatted_data = new_msg_dto.model_dump(mode='json')
                print(f"🚀 Сообщение переслано в комнату chat_{target_chat_id}")
                await sio.emit("new_message", formatted_data, room=f"chat_{target_chat_id}")
    except Exception as e:
        print(f"❌ Ошибка сервера при пересылке: {e}")


@sio.event
async def messages_seen(sid, data):
    with get_tasks_session() as session:  # Исправлено
        service = ChatService(session)
        service.mark_messages_as_read(data['user_id'], data['message_ids'])
        await sio.emit("messages_read_update", {
            "chat_id": data['chat_id'],
            "message_ids": data['message_ids']
        }, room=f"chat_{data['chat_id']}")


@sio.event
async def join_chat(sid, data):
    chat_id = data.get("chat_id")
    await sio.enter_room(sid, f"chat_{chat_id}")
    print(f"User {sid} joined room chat_{chat_id}")


@sio.event
async def leave_chat(sid, data):
    chat_id = data.get("chat_id")
    await sio.leave_room(sid, f"chat_{chat_id}")


@sio.event
async def update_chat_settings(sid, data):
    chat_id = data.get('chat_id')
    new_title = data.get('new_title')
    await sio.emit("chat_info_updated", {
        "chat_id": chat_id,
        "new_title": new_title
    }, room=f"chat_{chat_id}")


async def main():
    """Главная асинхронная функция"""
    print("✅ Запуск сервера (синхронизация не требуется)")

    # Инициализируем сервис сотрудников (без синхронизации!)
    employee_service = EmployeeService()

    # Проверяем, что сотрудники доступны
    employees = employee_service.get_all_employees()
    print(f"📊 Загружено сотрудников: {len(employees)}")

    # Запускаем Telegram бота в фоновом режиме
    print("🤖 Запуск Telegram бота...")
    bot_task = asyncio.create_task(start_bot())

    # Запускаем сокет-сервер
    print("🌐 Запуск сокет-сервера...")
    config = uvicorn.Config(
        socket_app,
        host="0.0.0.0",
        port=8081,
        loop="asyncio",
        log_level="info"
    )
    server = uvicorn.Server(config)

    # Ждём завершения сервера
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())