import uvicorn
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI
from sqlalchemy import select
import socketio
import asyncio
from database import TasksSessionLocal
from services.chat_service import ChatService

# Импортируем сервис синхронизации
from sync_service import sync_service
from telegram_bot import pending_registrations, telegram_bot

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

        with TasksSessionLocal() as session:
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


@sio.event
async def create_chat(sid, data):
    with TasksSessionLocal() as session:
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
    with TasksSessionLocal() as session:
        service = ChatService(session)
        if service.delete_chat(chat_id):
            await sio.emit("chat_deleted", {"chat_id": chat_id}, room=f"chat_{chat_id}")


@sio.event
async def update_participants(sid, data):
    chat_id = data['chat_id']
    added = data.get('added_users', [])
    removed = data.get('removed_users', [])

    try:
        with TasksSessionLocal() as session:
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

    with TasksSessionLocal() as session:
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
        with TasksSessionLocal() as session:
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
async def request_registration(sid, data):
    """
    Обработчик запроса на регистрацию от клиента
    Отправляет уведомление всем администраторам
    """
    print(f"📝 Получен запрос на регистрацию: {data.get('last_name')} {data.get('first_name')}")

    request_id = data.get('user_chat_id') or sid
    pending_registrations[request_id] = data

    with TasksSessionLocal() as session:
        from models.employees import ExternalEmployee
        stmt = select(ExternalEmployee).where(
            ExternalEmployee.rights.in_(['admin', 'superadmin'])
        )
        admins = list(session.scalars(stmt))

        if not admins:
            print("⚠️ Нет администраторов для уведомления")
            return

        # Получаем названия отдела и подразделения
        division_name = "Не указано"
        department_name = "Не указано"

        if data.get('division_id'):
            from models.employees import DivisionFDW
            div = session.get(DivisionFDW, data['division_id'])
            division_name = div.name if div else "Не указано"

        if data.get('department_id'):
            from models.employees import DepartmentFDW
            dept = session.get(DepartmentFDW, data['department_id'])
            department_name = dept.name if dept else "Не указано"

        # Получаем дату рождения
        birth_date = data.get('birth_date', 'Не указана')
        if birth_date and birth_date != 'Не указана':
            # Форматируем дату из ISO в DD.MM.YYYY
            try:
                from datetime import datetime
                birth_date_obj = datetime.fromisoformat(birth_date)
                birth_date = birth_date_obj.strftime("%d.%m.%Y")
            except:
                pass

        # Рабочий номер
        work_number = data.get('work_number', 'Не указан')
        if not work_number or work_number == '':
            work_number = 'Не указан'

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{request_id}")
            ]
        ])

        message_text = (
            f"🆕 *Новая заявка на регистрацию!*\n\n"
            f"📝 *ФИО:* {data.get('last_name')} {data.get('first_name')} {data.get('middle_name') or ''}\n"
            f"📞 *Моб. телефон:* {data.get('phone_number')}\n"
            f"📞 *Раб. телефон:* {work_number}\n"
            f"📧 *Email:* {data.get('email') or 'Не указан'}\n"
            f"🎂 *Дата рождения:* {birth_date}\n"
            f"💼 *Должность:* {data.get('position')}\n"
            f"🏢 *Подразделение:* {division_name}\n"
            f"📁 *Отдел:* {department_name}\n\n"
            f"Используйте кнопки ниже для подтверждения или отклонения заявки."
        )

        # Отправляем уведомление каждому администратору
        tasks = []
        for admin in admins:
            if admin.chat_id:
                task = send_telegram_message(admin.chat_id, message_text, keyboard)
                tasks.append(task)
                print(f"📨 Отправка уведомления администратору {admin.id}")

        if tasks:
            await asyncio.gather(*tasks)
            print(f"✅ Уведомления отправлены {len(admins)} администраторам")


@sio.event
async def edit_chat_msg(sid, data):
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
        with TasksSessionLocal() as session:
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
    with TasksSessionLocal() as session:
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


if __name__ == "__main__":
    # Запускаем синхронизацию
    print("🔄 Запуск синхронизации сотрудников...")
    sync_service.sync_employees()
    print("✅ Начальная синхронизация завершена")

    sync_service.start_background_sync()

    # Запускаем Telegram бота в том же event loop
    print("🤖 Запуск Telegram бота...")

    # Запускаем сервер
    print("🌐 Запуск сокет-сервера...")
    uvicorn.run(socket_app, host="0.0.0.0", port=8081)