import io
import json
import os
import sys
import threading
import time
import pandas as pd
import requests
import telebot
from telebot import types

# ==========================================
# ⚙️ НАЛАШТУВАННЯ
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY"
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"
SUBS_FILE = "subscriptions.json"

# Контакты и адрес вашего физического магазина
SHOP_ADDRESS = "м. Чугуїв, бул. Центральний, 8"  # Укажите ваш адрес
SHOP_HOURS = "Пн-Пт: 08:00 — 18:00 | Сб-Нд: 08:00 — 17:00"
SHOP_PHONE = "+380 97 391 64 00, +380 63 189 16 83"  # Укажите ваш телефон
MANAGER_USERNAME = "smthwrng121"  # Telegram юзернейм менеджера без @
GOOGLE_MAPS_LINK = "https://maps.app.goo.gl/RukWZ1QBZbQQsqnA9"  # Ссылка на вашу точку на Google Maps

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_quiz_data = {}


# ---------------- ФОНОВА ПЕРЕВІРКА НАЯВНОСТІ ----------------
def check_stock_and_notify():
    while True:
        try:
            if os.path.exists(SUBS_FILE):
                with open(SUBS_FILE, "r", encoding="utf-8") as f:
                    subs = json.load(f)

                if subs and CSV_URL and "http" in CSV_URL:
                    # Скидаємо кєш Google Таблиць за допомогою _nocache
                    fresh_csv_url = f"{CSV_URL}&_nocache={int(time.time())}"
                    res = requests.get(fresh_csv_url, timeout=10)
                    
                    if res.status_code == 200:
                        csv_data = io.StringIO(res.text)
                        df = pd.read_csv(csv_data).fillna("-")
                        products = df.to_dict(orient="records")

                        remaining_subs = []

                        for sub in subs:
                            c_id = sub.get("chat_id")
                            p_name = sub.get("product_name", "")
                            
                            # Очищаємо назву підписки від дужок (наприклад, "iPhone 15 (128GB)" -> "iphone 15")
                            clean_sub_name = p_name.split("(")[0].strip().lower()
                            notified = False

                            for p in products:
                                title = str(p.get("Название", "")).strip().lower()
                                status = str(p.get("Статус", "")).strip().lower()

                                # Перевіряємо збіг назв
                                if (clean_sub_name in title) or (title in clean_sub_name):
                                    # Перевіряємо, що товар у наявності
                                    if "нет" not in status and "немає" not in status and "закончил" not in status:
                                        try:
                                            kb = types.InlineKeyboardMarkup()
                                            kb.add(types.InlineKeyboardButton("🛍️ Відкрити каталог", web_app=types.WebAppInfo(url=WEB_APP_URL)))
                                            
                                            bot.send_message(
                                                c_id,
                                                f"🎉 <b>Чудова новина!</b>\n\n"
                                                f"Товар <b>«{p_name}»</b> знову з'явився в наявності у нашому магазині!\n\n"
                                                f"Ви можете забронювати його прямо зараз у каталозі 👇",
                                                parse_mode="HTML",
                                                reply_markup=kb
                                            )
                                            notified = True
                                            print(f"[SUCCESS] Сповіщення про товар «{p_name}» успішно надіслано користувачу {c_id}")
                                        except Exception as err:
                                            print(f"Помилка надсилання сповіщення: {err}")
                                        break

                            if not notified:
                                remaining_subs.append(sub)

                        # Перезаписуємо список підписок
                        with open(SUBS_FILE, "w", encoding="utf-8") as f:
                            json.dump(remaining_subs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Помилка у фоновому сканері: {e}")

        # Перевірка щохвилини
        time.sleep(60)


threading.Thread(target=check_stock_and_notify, daemon=True).start()


@bot.message_handler(commands=["start"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
            types.KeyboardButton(text="🧭 Майстер підбору"),
        )
        reply_kb.add(
            types.KeyboardButton(text="📍 Магазин та контакти"),
            types.KeyboardButton(text="❓ Часті запитання (FAQ)"),
        )

        welcome_text = (
            f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
            f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n\n"
            f"Обирайте потрібний розділ у меню нижче! 👇"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=reply_kb)
    except Exception as e:
        print(f"Помилка /start: {e}", file=sys.stderr)


@bot.message_handler(func=lambda msg: msg.text == "❓ Часті запитання (FAQ)")
def send_faq_menu(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛡️ Чи є гарантія на техніку?", callback_data="faq_warranty"))
    kb.add(types.InlineKeyboardButton("📌 Як працює бронювання?", callback_data="faq_booking"))
    kb.add(types.InlineKeyboardButton("📲 Чи допомагаєте перенести дані?", callback_data="faq_transfer"))
    kb.add(types.InlineKeyboardButton("✨ Поклейка скла / плівок", callback_data="faq_service"))
    kb.add(types.InlineKeyboardButton("🔄 Чи є обмін / Trade-In?", callback_data="faq_tradein"))
    kb.add(types.InlineKeyboardButton("💬 Поставити запитання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))
    bot.send_message(message.chat.id, "❓ <b>Відповіді на часті запитання</b>\n\nОберіть запитання:", parse_mode="HTML", reply_markup=kb)


@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин та контакти")
def send_contacts(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🗺️ Прокласти маршрут (Google Maps)", url=GOOGLE_MAPS_LINK))
    kb.add(types.InlineKeyboardButton("💬 Написати менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

    contact_text = (
        f"🏢 <b>Наш магазин гаджетів та аксесуарів</b>\n\n"
        f"📍 <b>Адреса:</b> {SHOP_ADDRESS}\n"
        f"⏰ <b>Час роботи:</b> {SHOP_HOURS}\n"
        f"📞 <b>Телефон:</b> {SHOP_PHONE}\n\n"
        f"💡 <i>Ви можете приїхати, подивитися, приміряти чохол або поклеїти скло прямо у нас!</i>"
    )
    bot.send_message(message.chat.id, contact_text, parse_mode="HTML", reply_markup=kb)


@bot.message_handler(func=lambda msg: msg.text == "🧭 Майстер підбору")
def start_quiz(message):
    user_quiz_data[message.chat.id] = {}
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📱 Обрати новий телефон", callback_data="goal_phone"))
    kb.add(types.InlineKeyboardButton("🛡️ Аксесуар (чохол / скло / плівка)", callback_data="goal_acc"))
    bot.send_message(message.chat.id, "<b>Крок 1:</b> Що ви шукаєте сьогодні?", parse_mode="HTML", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    bot.answer_callback_query(call.id)
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.id

    if data.startswith("faq_"):
        faq_answers = {
            "warranty": "🛡️ <b>Гарантія на техніку</b>\n\nНа всю нову техніку надається офіційна гарантія від 12 місяців.\nНа б/в техніку надається наша гарантія від магазину.",
            "booking": "📌 <b>Як працює бронь на 24 години?</b>\n\nВи оформлюєте товар у Mini App та обираєте «Забронювати у магазині».\nМи резервуємо товар на складі на 24 години.",
            "transfer": "📲 <b>Перенесення даних</b>\n\nТак! Наші фахівці допомагають безкоштовно перенести всі контакти, фото та додатки.",
            "service": "✨ <b>Поклейка скла</b>\n\nНаші майстри зроблять ідеальну поклейку без пилу прямо при вас у магазині.",
            "tradein": "🔄 <b>Trade-In</b>\n\nВи можете здати свій старий пристрій у залік вартості нового гаджета!"
        }
        topic = data.split("_")[1]
        ans_text = faq_answers.get(topic, "Інформація уточнюється...")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад до запитань", callback_data="faq_back"))
        kb.add(types.InlineKeyboardButton("💬 Поставити запитання", url=f"https://t.me/{MANAGER_USERNAME}"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=ans_text, parse_mode="HTML", reply_markup=kb)

    elif data == "faq_back":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Чи є гарантія на техніку?", callback_data="faq_warranty"))
        kb.add(types.InlineKeyboardButton("📌 Як працює бронювання?", callback_data="faq_booking"))
        kb.add(types.InlineKeyboardButton("📲 Чи допомагаєте перенести дані?", callback_data="faq_transfer"))
        kb.add(types.InlineKeyboardButton("✨ Поклейка скла / плівок", callback_data="faq_service"))
        kb.add(types.InlineKeyboardButton("🔄 Чи є обмін / Trade-In?", callback_data="faq_tradein"))
        kb.add(types.InlineKeyboardButton("💬 Поставити запитання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❓ <b>Відповіді на часті запитання</b>\n\nОберіть запитання:", parse_mode="HTML", reply_markup=kb)

    elif data == "goal_phone":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📸 Крута камера", callback_data="pfeature_camera"), types.InlineKeyboardButton("🔋 Довга батарея", callback_data="pfeature_battery"))
        kb.add(types.InlineKeyboardButton("🎮 Ігри та швидкість", callback_data="pfeature_power"), types.InlineKeyboardButton("⚖️ Баланс ціна/якість", callback_data="pfeature_balance"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 2:</b> Що для вас найважливіше у смартфоні?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("pfeature_"):
        final_url = f"{WEB_APP_URL}/?category=телефоны"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="📱 Переглянути відповідні телефони", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ <b>Підбір телефона завершено!</b>\n\nПерейдіть до каталогу:", parse_mode="HTML", reply_markup=kb)

    elif data == "goal_acc":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🍏 Apple (iPhone)", callback_data="brand_apple"), types.InlineKeyboardButton("📱 Samsung", callback_data="brand_samsung"))
        kb.add(types.InlineKeyboardButton("⚡ Xiaomi / Poco", callback_data="brand_xiaomi"), types.InlineKeyboardButton("🌐 Інший бренд", callback_data="brand_other"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 2:</b> Вкажіть бренд вашого пристрою:", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("brand_"):
        brand = data.split("_")[1]
        user_quiz_data[chat_id] = {"brand": brand}
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Чохол", callback_data="type_Чехлы"), types.InlineKeyboardButton("✨ Захисне скло", callback_data="type_Стекла"))
        kb.add(types.InlineKeyboardButton("📜 Гідрогелева плівка", callback_data="type_Пленки"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 3:</b> Що саме ви шукаєте?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("type_"):
        p_type = data.split("_")[1]
        user_data = user_quiz_data.get(chat_id, {})
        brand = user_data.get("brand", "all")
        search_term = "iphone" if brand == "apple" else ("samsung" if brand == "samsung" else "xiaomi")
        final_url = f"{WEB_APP_URL}/?category={p_type}&search={search_term}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="🎯 Переглянути варіанти", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ <b>Підбір завершено!</b> Натисніть кнопку нижче, щоб відкрити каталог:", parse_mode="HTML", reply_markup=kb)


if __name__ == "__main__":
    print("Очищаємо вебхуки та чергу повідомлень...")
    try:
        bot.remove_webhook()
    except Exception:
        pass

    print("Бот запущений і чекає на команди...")
    bot.infinity_polling(skip_pending=True)
