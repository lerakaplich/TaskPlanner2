import time
import threading
import telebot
import requests
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import re
import json
import os
import tempfile

# --- НАСТРОЙКИ ---
TOKEN = "8309873506:AAEXOuOHm3HxW2NWI1XQ5tcrAWR4HCwfvws"
bot = telebot.TeleBot(TOKEN)
ua = UserAgent()

user_data = {}
monitoring_active = {}
temp_stations = {}
train_pages = {}  # Для хранения поездов по страницам


def get_browser():
    """Создает экземпляр браузера с чистым профилем"""
    options = Options()

    # ВАЖНО: отключаем выбор аккаунта
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-component-update')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-sync')

    # Создаем временную директорию для профиля
    temp_profile_dir = tempfile.mkdtemp()

    # Настройки профиля
    options.add_argument(f'--user-data-dir={temp_profile_dir}')
    options.add_argument('--profile-directory=Default')

    # Отключаем всплывающие окна
    options.add_argument('--disable-popup-blocking')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Добавляем User-Agent
    options.add_argument(f'--user-agent={ua.random}')

    # Разрешаем все куки по умолчанию
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')

    # Устанавливаем язык
    options.add_argument('--lang=ru')

    # Для Windows - дополнительные опции
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')

    # Включаем headless режим для мониторинга (невидимое окно)
    options.add_argument('--headless')  # <-- ВКЛЮЧАЕМ ДЛЯ МОНИТОРИНГА

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Отключаем обнаружение автоматизации
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": ua.random,
            "platform": "Win32"
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        driver.set_page_load_timeout(45)
        driver.set_script_timeout(30)

        return driver
    except Exception as e:
        print(f"Ошибка при создании браузера: {e}")
        # Пробуем очистить временную директорию
        try:
            import shutil
            shutil.rmtree(temp_profile_dir, ignore_errors=True)
        except:
            pass
        raise


def accept_cookies(browser):
    """Принимает куки на сайте"""
    try:
        # Пробуем несколько вариантов кнопок принятия куки
        cookie_selectors = [
            "//button[contains(., 'ПРИНЯТЬ')]",
            "//button[contains(., 'Принять')]",
            "//button[contains(., 'Accept')]",
            "//button[contains(., 'ОК')]",
            "//button[contains(., 'Ok')]",
            "//button[contains(., 'OK')]",
            "//button[@id='cookie-accept']",
            "//button[contains(@class, 'cookie')]",
        ]

        for selector in cookie_selectors:
            try:
                cookie_btn = WebDriverWait(browser, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_btn.click()
                print("✅ Куки приняты")
                time.sleep(1)
                return True
            except:
                continue

        return False

    except Exception as e:
        print(f"Не удалось принять куки: {e}")
        return False


def search_stations(city_query):
    """Поиск станций через API"""
    stations = []
    try:
        url = f"https://pass.rw.by/ru/ajax/autocomplete/search/?term={city_query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://pass.rw.by/ru/',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data[:6]:
                value_parts = item['value'].split('|')
                station_name = value_parts[0] if value_parts else item['label'].split(',')[0]
                station_code = value_parts[1] if len(value_parts) > 1 else ''

                stations.append({
                    'label': item['label'],
                    'value': item['value'],
                    'name': station_name,
                    'code': station_code,
                    'display': f"{station_name} ({station_code})" if station_code else station_name
                })
    except Exception as e:
        print(f"Ошибка поиска станций: {e}")
    return stations


def parse_station_info(station_item):
    """Парсит информацию о станции"""
    # Значение приходит в формате: "Название станции|код|ЕСР"
    parts = station_item['value'].split('|')

    raw_name = parts[0].strip() if parts else station_item.get('name', '')
    clean_name = raw_name.replace('ст. ', '')

    # Получаем все доступные коды
    code = parts[1].strip() if len(parts) > 1 else ''
    esr = parts[2].strip() if len(parts) > 2 else ''

    # Если esr пустой, но есть code, используем его
    if not esr and code:
        esr = code

    return {
        'raw_name': raw_name,
        'clean_name': clean_name,
        'code': code,
        'esr': esr
    }


def build_direct_url(from_info, to_info, date_str):
    """Строит прямой URL для запроса"""
    d, m, y = date_str.split('.')

    # Кодируем названия станций
    from_encoded = requests.utils.quote(from_info['raw_name'])
    to_encoded = requests.utils.quote(to_info['raw_name'])

    # Используем коды станций из данных
    from_esr = from_info['esr'] or from_info['code'] or '0'
    to_esr = to_info['esr'] or to_info['code'] or '0'

    # Строим URL БЕЗ фиксированного to_exp
    url = (f"https://pass.rw.by/ru/route/"
           f"?from={from_encoded}"
           f"&from_exp=0"
           f"&from_esr={from_esr}"
           f"&to={to_encoded}"
           f"&to_exp=0"  # <--- ИЗМЕНИТЕ ЭТО на 0
           f"&to_esr={to_esr}"
           f"&date={y}-{m}-{d}"
           f"&type=1")

    print(f"🔗 URL мониторинга: {url}")
    return url


def fetch_available_trains(from_info, to_info, date_str):
    """Поиск поездов для отображения пользователю"""
    print(f"🔍 Поиск поездов для пользователя...")

    # Временно отключаем headless для видимого браузера при поиске
    browser = None
    trains = []

    try:
        # Создаем браузер БЕЗ headless для отладки
        temp_options = Options()
        temp_options.add_argument('--no-first-run')
        temp_options.add_argument('--no-default-browser-check')
        temp_options.add_argument(f'--user-agent={ua.random}')

        # НЕ добавляем --headless, чтобы видеть процесс

        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=temp_options)

        # Строим URL
        url = build_direct_url(from_info, to_info, date_str)

        print(f"🌐 Открываю: {url}")
        browser.get(url)

        # Принимаем куки
        time.sleep(2)
        accept_cookies(browser)

        # Ждем загрузки
        time.sleep(5)

        # Ищем поезда
        try:
            rows = browser.find_elements(By.CLASS_NAME, "sch-table__row-wrap")
            print(f"Найдено строк в расписании: {len(rows)}")

            for i, row in enumerate(rows[:20]):  # Увеличим лимит до 20 поездов
                try:
                    # Пытаемся найти номер и время
                    train_num_elem = row.find_elements(By.CLASS_NAME, "train-number")
                    train_time_elem = row.find_elements(By.CLASS_NAME, "train-from-time")

                    if train_num_elem and train_time_elem:
                        train_num = train_num_elem[0].text.strip()
                        train_time = train_time_elem[0].text.strip()

                        if train_num and train_time:
                            trains.append({
                                "number": train_num,
                                "time": train_time,
                                "full_info": row.text[:100]  # Сохраняем часть текста для отладки
                            })
                            print(f"  ✅ Поезд {i + 1}: {train_time} | {train_num}")
                except Exception as e:
                    print(f"  Ошибка в строке {i}: {e}")
                    continue

        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            # Альтернативный метод
            page_text = browser.page_source
            if "17:25" in browser.page_source:
                print("ℹ️ На странице есть время 17:25 (значит поезд есть)")

        print(f"📊 Найдено поездов: {len(trains)}")

    except Exception as e:
        print(f"❌ Ошибка поиска: {str(e)[:200]}")

    finally:
        if browser:
            try:
                browser.quit()
            except:
                pass

    return trains


def monitor_train_tickets(chat_id, from_info, to_info, date_str, target_time):
    """Мониторинг наличия билетов на конкретный поезд"""
    print(f"📡 Начинаю мониторинг поезда {target_time}...")

    url = build_direct_url(from_info, to_info, date_str)
    last_status = None
    check_count = 0

    while monitoring_active.get(chat_id, False):
        check_count += 1
        browser = None

        try:
            print(f"🔍 Проверка #{check_count} поезд {target_time}...")

            # Создаем браузер для мониторинга (в headless режиме)
            browser = get_browser()

            # Открываем страницу
            browser.get(url)

            # Принимаем куки если нужно
            time.sleep(2)
            accept_cookies(browser)

            # Ждем загрузки
            time.sleep(3)

            # Ищем нужный поезд
            found_train = False
            tickets_available = False
            ticket_info = ""

            try:
                # Ищем все поезда
                rows = browser.find_elements(By.CLASS_NAME, "sch-table__row-wrap")
                print(f"  Найдено поездов на странице: {len(rows)}")

                for row in rows:
                    try:
                        # Проверяем время поезда
                        time_elem = row.find_element(By.CLASS_NAME, "train-from-time")
                        current_time = time_elem.text.strip()

                        if current_time == target_time:
                            found_train = True
                            print(f"  ✅ Найден поезд {target_time}")

                            # Ищем информацию о билетах
                            try:
                                # Ищем элементы с билетами
                                ticket_elements = row.find_elements(By.CLASS_NAME, "sch-table__t-item")

                                if ticket_elements:
                                    tickets_available = True
                                    ticket_details = []

                                    for ticket in ticket_elements:
                                        ticket_text = ticket.text.strip()
                                        if ticket_text and any(char.isdigit() for char in ticket_text):
                                            ticket_details.append(ticket_text)

                                    if ticket_details:
                                        ticket_info = "\n".join(
                                            [f"• {detail}" for detail in ticket_details[:3]])  # Ограничиваем 3 пунктами
                                        print(f"  🎫 Найдены билеты: {len(ticket_details)} вариантов")
                                    else:
                                        print(f"  ℹ️ Есть элементы билетов, но текст пустой")
                                else:
                                    print(f"  📭 Нет элементов билетов")

                            except Exception as e:
                                print(f"  Ошибка при проверке билетов: {e}")

                            break

                    except Exception as e:
                        continue

            except Exception as e:
                print(f"  Ошибка при поиске поезда: {e}")

            # Определяем текущий статус
            current_status = None
            if found_train:
                if tickets_available and ticket_info:
                    current_status = f"AVAILABLE:{ticket_info}"
                else:
                    current_status = "NO_TICKETS"
            else:
                current_status = "TRAIN_NOT_FOUND"

            # Отправляем уведомление при изменении статуса
            if current_status != last_status:
                if current_status.startswith("AVAILABLE:"):
                    # Извлекаем информацию о билетах
                    ticket_details = current_status.split(":", 1)[1]
                    message = (f"🔔 *ПОЯВИЛИСЬ БИЛЕТЫ!*\n\n"
                               f"*Поезд:* {target_time}\n"
                               f"*Маршрут:* {from_info['clean_name']} → {to_info['clean_name']}\n"
                               f"*Дата:* {date_str}\n\n"
                               f"*Доступные места:*\n{ticket_details}\n\n"
                               f"_Проверено в {time.strftime('%H:%M:%S')}_")

                    bot.send_message(chat_id, message, parse_mode='Markdown')
                    print(f"  📨 Отправлено уведомление о билетах")

                elif current_status == "NO_TICKETS" and last_status and last_status.startswith("AVAILABLE"):
                    message = (f"❌ *Билеты закончились*\n\n"
                               f"Поезд {target_time}\n"
                               f"Больше нет доступных мест.")

                    bot.send_message(chat_id, message, parse_mode='Markdown')
                    print(f"  📨 Отправлено уведомление об отсутствии билетов")

                elif current_status == "TRAIN_NOT_FOUND":
                    message = (f"⚠️ *Поезд не найден*\n\n"
                               f"Поезд {target_time} отсутствует в расписании.\n"
                               f"Возможно, расписание изменилось.")

                    bot.send_message(chat_id, message, parse_mode='Markdown')
                    print(f"  📨 Отправлено уведомление - поезд не найден")

                last_status = current_status

            # Логируем статус
            status_map = {
                "AVAILABLE:": "🎫 Есть билеты",
                "NO_TICKETS": "📭 Нет билетов",
                "TRAIN_NOT_FOUND": "🚫 Поезд не найден"
            }

            for key, value in status_map.items():
                if current_status.startswith(key):
                    print(f"  Статус: {value}")
                    break

        except Exception as e:
            print(f"  ❌ Ошибка при проверке: {str(e)[:100]}")

        finally:
            if browser:
                try:
                    browser.quit()
                except:
                    pass

        # Ждем перед следующей проверкой
        if monitoring_active.get(chat_id, False):
            print(f"  ⏳ Следующая проверка через 60 секунд...")
            for i in range(60):
                if not monitoring_active.get(chat_id, False):
                    break
                time.sleep(1)

    print(f"🛑 Мониторинг поезда {target_time} остановлен")


def create_train_selection_keyboard(trains, page=0, trains_per_page=5):
    """Создает клавиатуру для выбора поезда с пагинацией"""
    markup = types.InlineKeyboardMarkup()

    # Рассчитываем индексы для текущей страницы
    start_idx = page * trains_per_page
    end_idx = start_idx + trains_per_page

    # Кнопки поездов для текущей страницы
    for train in trains[start_idx:end_idx]:
        btn_text = f"{train['time']} | №{train['number']}"
        if len(btn_text) > 40:
            btn_text = f"{train['time']} | поезд"
        markup.add(types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"sel_{train['time']}"
        ))

    # Кнопки пагинации
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}")
        )

    # Показываем информацию о странице
    total_pages = (len(trains) + trains_per_page - 1) // trains_per_page
    page_info = f"Страница {page + 1}/{total_pages}"
    pagination_buttons.append(
        types.InlineKeyboardButton(text=page_info, callback_data="page_info")
    )

    if (page + 1) * trains_per_page < len(trains):
        pagination_buttons.append(
            types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page + 1}")
        )

    if pagination_buttons:
        markup.row(*pagination_buttons)

    # Кнопка нового поиска
    markup.add(types.InlineKeyboardButton(text="🔄 Новый поиск", callback_data="restart"))

    return markup, start_idx, end_idx


# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---

@bot.message_handler(commands=['start'])
def start(message):
    """Начало работы"""
    chat_id = message.chat.id
    monitoring_active[chat_id] = False

    bot.send_message(chat_id,
                     "🚂 *Бот для поиска и мониторинга билетов на поезда*\n\n"
                     "Напишите *город отправления* (например: Минск):",
                     parse_mode='Markdown')
    bot.register_next_step_handler(message, handle_from_input)


def handle_from_input(message):
    """Обработка города отправления"""
    chat_id = message.chat.id

    if message.text.startswith('/'):
        bot.send_message(chat_id, "Пожалуйста, введите название города.")
        return

    bot.send_message(chat_id, f"🔍 Ищу станции для: *{message.text}*...", parse_mode='Markdown')

    stations = search_stations(message.text)

    if not stations:
        bot.send_message(chat_id, "❌ Станции не найдены. Попробуйте другое название:")
        bot.register_next_step_handler(message, handle_from_input)
        return

    temp_stations[chat_id] = stations

    markup = types.InlineKeyboardMarkup()
    for i, station in enumerate(stations[:5]):
        btn_text = station['display']
        if len(btn_text) > 30:
            btn_text = btn_text[:27] + "..."
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"sf_{i}"))

    bot.send_message(chat_id, "📍 Выберите станцию:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('sf_'))
def set_from(call):
    """Установка станции отправления"""
    idx = int(call.data.split('_')[1])
    chat_id = call.message.chat.id

    if chat_id not in temp_stations or idx >= len(temp_stations[chat_id]):
        bot.answer_callback_query(call.id, "Ошибка выбора станции")
        return

    station = temp_stations[chat_id][idx]
    station_info = parse_station_info(station)

    user_data[chat_id] = {
        'from': station_info,
        'from_display': station_info['clean_name']
    }

    bot.edit_message_text(
        f"✅ *Отправление:* {station_info['clean_name']}\n\n"
        f"📍 Напишите *город назначения*:",
        chat_id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, handle_to_input)


def handle_to_input(message):
    """Обработка города назначения"""
    chat_id = message.chat.id

    bot.send_message(chat_id, f"🔍 Ищу станции для: *{message.text}*...", parse_mode='Markdown')

    stations = search_stations(message.text)

    if not stations:
        bot.send_message(chat_id, "❌ Станции не найдены. Попробуйте другое название:")
        bot.register_next_step_handler(message, handle_to_input)
        return

    temp_stations[chat_id] = stations

    markup = types.InlineKeyboardMarkup()
    for i, station in enumerate(stations[:5]):
        btn_text = station['display']
        if len(btn_text) > 30:
            btn_text = btn_text[:27] + "..."
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"st_{i}"))

    bot.send_message(chat_id, "📍 Выберите станцию:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('st_'))
def set_to(call):
    """Установка станции назначения"""
    idx = int(call.data.split('_')[1])
    chat_id = call.message.chat.id

    if chat_id not in temp_stations or idx >= len(temp_stations[chat_id]):
        bot.answer_callback_query(call.id, "Ошибка выбора станции")
        return

    station = temp_stations[chat_id][idx]
    station_info = parse_station_info(station)

    user_data[chat_id]['to'] = station_info
    user_data[chat_id]['to_display'] = station_info['clean_name']

    bot.edit_message_text(
        f"✅ *Маршрут:*\n"
        f"🚂 От: {user_data[chat_id]['from_display']}\n"
        f"🏁 До: {station_info['clean_name']}\n\n"
        f"📅 Напишите *дату* (ДД.ММ.ГГГГ):",
        chat_id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_date)


def process_date(message):
    """Обработка даты"""
    chat_id = message.chat.id

    date_text = message.text.strip()

    try:
        # Проверка даты
        time.strptime(date_text, '%d.%m.%Y')

        user_data[chat_id]['date'] = date_text

        from_name = user_data[chat_id]['from_display']
        to_name = user_data[chat_id]['to_display']

        bot.send_message(chat_id,
                         f"🔎 *Ищу поезда...*\n"
                         f"*Маршрут:* {from_name} → {to_name}\n"
                         f"*Дата:* {date_text}",
                         parse_mode='Markdown')

        # Ищем поезда
        trains = fetch_available_trains(
            user_data[chat_id]['from'],
            user_data[chat_id]['to'],
            date_text
        )

        if not trains:
            bot.send_message(chat_id,
                             "❌ *Поездов не найдено.*\n\n"
                             "Возможные причины:\n"
                             "• На эту дату нет расписания\n"
                             "• Маршрут временно не обслуживается\n"
                             "• Технические проблемы сайта\n\n"
                             "Попробуйте другую дату или маршрут.",
                             parse_mode='Markdown')

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart"))
            bot.send_message(chat_id, "Хотите попробовать другой маршрут?", reply_markup=markup)

            return

        # Сохраняем поезда для этого чата
        train_pages[chat_id] = trains

        # Показываем найденные поезда (первые 10 для списка)
        trains_text = "\n".join([f"🕒 {t['time']} | 🚂 {t['number']}" for t in trains[:10]])

        # Создаем клавиатуру с пагинацией
        markup, start_idx, end_idx = create_train_selection_keyboard(trains, page=0)

        bot.send_message(chat_id,
                         f"✅ *Найдено поездов: {len(trains)}*\n\n"
                         f"*Первые 10 поездов:*\n"
                         f"{trains_text}\n\n"
                         f"Выберите поезд для отслеживания (используйте кнопки навигации):",
                         reply_markup=markup,
                         parse_mode='Markdown')

    except ValueError:
        bot.send_message(chat_id,
                         "❌ *Неверный формат даты!*\n\n"
                         "Используйте: *ДД.ММ.ГГГГ*\n"
                         "Пример: 30.01.2026",
                         parse_mode='Markdown')
        bot.register_next_step_handler(message, process_date)


@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page_navigation(call):
    """Обработка переключения страниц"""
    chat_id = call.message.chat.id

    if chat_id not in train_pages:
        bot.answer_callback_query(call.id, "Данные о поездах устарели. Начните поиск заново.")
        return

    trains = train_pages[chat_id]
    page = int(call.data.split('_')[1])

    # Создаем клавиатуру для новой страницы
    markup, start_idx, end_idx = create_train_selection_keyboard(trains, page=page)

    # Обновляем сообщение с новой клавиатурой
    bot.edit_message_reply_markup(
        chat_id,
        call.message.message_id,
        reply_markup=markup
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "page_info")
def handle_page_info(call):
    """Обработка клика по информации о странице"""
    bot.answer_callback_query(call.id, "Используйте кнопки для навигации")


@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def handle_selection(call):
    """Обработка выбора поезда"""
    target_time = call.data.split('_')[1]
    chat_id = call.message.chat.id

    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Ошибка: данные не найдены")
        return

    # Останавливаем предыдущий мониторинг если был
    monitoring_active[chat_id] = False
    time.sleep(2)  # Даем время завершиться

    # Запускаем новый мониторинг
    monitoring_active[chat_id] = True

    from_info = user_data[chat_id]['from']
    to_info = user_data[chat_id]['to']
    date_str = user_data[chat_id]['date']

    bot.edit_message_text(
        f"📡 *Мониторинг запущен!*\n\n"
        f"🔔 Отслеживаю билеты на поезд:\n"
        f"• Время: {target_time}\n"
        f"• Маршрут: {from_info['clean_name']} → {to_info['clean_name']}\n"
        f"• Дата: {date_str}\n\n"
        f"_Проверка каждую минуту. Остановить: /stop_",
        chat_id,
        call.message.message_id,
        parse_mode='Markdown'
    )

    # Запускаем мониторинг в отдельном потоке
    monitor_thread = threading.Thread(
        target=monitor_train_tickets,
        args=(chat_id, from_info, to_info, date_str, target_time),
        daemon=True
    )
    monitor_thread.start()

    print(f"🧵 Запущен поток мониторинга для чата {chat_id}, поезд {target_time}")


@bot.callback_query_handler(func=lambda call: call.data == "restart")
def restart(call):
    """Перезапуск"""
    chat_id = call.message.chat.id
    monitoring_active[chat_id] = False

    # Очищаем данные о поездах
    if chat_id in train_pages:
        del train_pages[chat_id]

    bot.edit_message_text("🔄 Начинаем заново...", chat_id, call.message.message_id)

    # Даем время остановиться мониторингу
    time.sleep(1)
    start(call.message)


@bot.message_handler(commands=['stop', 'stop_'])
def stop_monitoring(message):
    """Остановка мониторинга"""
    chat_id = message.chat.id

    if monitoring_active.get(chat_id):
        monitoring_active[chat_id] = False
        bot.send_message(chat_id,
                         "🛑 *Мониторинг остановлен.*\n\n"
                         "Для нового поиска: /start",
                         parse_mode='Markdown')
        print(f"🛑 Остановлен мониторинг для чата {chat_id}")
    else:
        bot.send_message(chat_id,
                         "📊 Мониторинг не активен.\n"
                         "Начать поиск: /start",
                         parse_mode='Markdown')


@bot.message_handler(commands=['status'])
def status(message):
    """Статус мониторинга"""
    chat_id = message.chat.id

    if monitoring_active.get(chat_id):
        if chat_id in user_data:
            from_name = user_data[chat_id].get('from_display', 'неизвестно')
            to_name = user_data[chat_id].get('to_display', 'неизвестно')
            date_str = user_data[chat_id].get('date', 'неизвестно')

            bot.send_message(chat_id,
                             f"📊 *Мониторинг активен*\n\n"
                             f"• Маршрут: {from_name} → {to_name}\n"
                             f"• Дата: {date_str}\n"
                             f"• Проверка каждую минуту\n\n"
                             f"Остановить: /stop",
                             parse_mode='Markdown')
        else:
            bot.send_message(chat_id,
                             "📊 *Мониторинг активен*\n\n"
                             "Детали маршрута недоступны.\n\n"
                             "Остановить: /stop",
                             parse_mode='Markdown')
    else:
        bot.send_message(chat_id,
                         "📊 *Мониторинг не активен*\n\n"
                         "Начать поиск поездов: /start",
                         parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def help_command(message):
    """Справка"""
    help_text = """
🚂 *Бот для поиска и мониторинга билетов*

📋 *Доступные команды:*
/start - Начать поиск поездов
/stop - Остановить мониторинг
/status - Проверить статус мониторинга
/help - Эта справка

📌 *Как использовать:*
1. Нажмите /start
2. Введите город отправления
3. Выберите станцию из списка
4. Введите город назначения
5. Выберите станцию назначения
6. Введите дату (ДД.ММ.ГГГГ)
7. Выберите поезд для мониторинга (листайте кнопками)
8. Бот будет уведомлять о появлении билетов

⚠️ *Важно:*
• Мониторинг работает в фоновом режиме
• Проверка выполняется каждую минуту
• Бот уведомит при появлении или исчезновении билетов
• Для остановки используйте /stop

🔔 *Уведомления:*
• 🎫 - Появились билеты
• ❌ - Билеты закончились
• ⚠️ - Поезд не найден (расписание изменилось)

📄 *Навигация по поездам:*
• Используйте кнопки ⬅️ и ➡️ для листания списка
• Каждая страница показывает по 5 поездов
• Кликните по времени поезда для начала мониторинга
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Обработка других сообщений"""
    if message.text.lower() in ['привет', 'hello', 'hi', 'start']:
        start(message)
    else:
        bot.send_message(message.chat.id,
                         "🤖 Я бот для поиска билетов на поезда.\n\n"
                         "Используйте /start для начала поиска\n"
                         "Или /help для справки.")


if __name__ == "__main__":
    print("🤖 Бот запущен...")
    print("📡 Ожидание запросов...")

    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"❌ Ошибка: {e}")