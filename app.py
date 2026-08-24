import io
import math
import os
import threading
import pandas as pd
import requests
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types

app = Flask(__name__)

# ==========================================
# ⚙️ НАСТРОЙКИ
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"
TELEGRAM_CHAT_ID = "396778432"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"


def clean_val(val):
    if val is None:
        return "-"
    if isinstance(val, float) and math.isnan(val):
        return "-"
    val_str = str(val).strip()
    return val_str if val_str and val_str != "nan" else "-"


def get_products():
    if not CSV_URL or "http" not in CSV_URL:
        return []

    try:
        response = requests.get(CSV_URL)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            df = df.fillna("-")
            products = df.to_dict(orient="records")

            # Безопасная предобработка памяти и цен
            for p in products:
                mem_raw = str(p.get("Память", "-")).strip()
                price_raw = str(p.get("Цена", "-")).strip()

                if "/" in mem_raw and "/" in price_raw:
                    p["memory_list"] = [m.strip() for m in mem_raw.split("/")]
                    p["price_list"] = [pr.strip() for pr in price_raw.split("/")]
                else:
                    p["memory_list"] = [mem_raw] if mem_raw != "-" else []
                    p["price_list"] = [price_raw]

            return products
        else:
            return []
    except Exception as e:
        print(f"Ошибка при чтении CSV: {e}")
        return []


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip().lower()

    products = get_products()
    filtered_products = []

    for p in products:
        p_cat = str(p.get("Категория", "")).strip().lower()
        if category and category.lower() != "all":
            if p_cat != category.lower():
                continue

        p_title = str(p.get("Название", "")).strip().lower()
        p_compat = str(p.get("Совместимость", "")).strip().lower()
        
        if search and (search not in p_title and search not in p_compat):
            continue

        filtered_products.append(p)

    return render_template(
        "index.html",
        products=filtered_products,
        category=category,
        search=search,
    )


@app.route("/api/accessories")
def get_accessories():
    model_query = request.args.get("model", "").strip().lower()
    if not model_query:
        return jsonify([])

    products = get_products()
    matched = []

    glass_categories = ["стекла", "захисні стекла"]
    case_categories = ["чехлы", "чохлы"]
    film_categories = ["пленки", "плівки"]

    has_glass = False

    for p in products:
        cat = str(p.get("Категория", "")).strip().lower()
        title = str(p.get("Название", "")).strip().lower()
        compat = str(p.get("Совместимость", "")).strip().lower()

        if (model_query in title) or (model_query in compat):
            if cat in glass_categories:
                has_glass = True

            if cat in (glass_categories + case_categories + film_categories):
                clean_p = {k: clean_val(v) for k, v in p.items()}
                if clean_p not in matched:
                    matched.append(clean_p)

    if not has_glass:
        for p in products:
            cat = str(p.get("Категория", "")).strip().lower()
            if cat in film_categories:
                clean_p = {k: clean_val(v) for k, v in p.items()}
                if clean_p not in matched:
                    matched.append(clean_p)

    return jsonify(matched)


@app.route("/order", methods=["POST"])
def send_order():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    name = data.get("name", "Не указано")
    phone = data.get("phone", "Не указан")
    items = data.get("items", [])

    if not items:
        return jsonify({"status": "error", "message": "Cart is empty"}), 400

    total_price = sum(float(i.get("price", 0)) for i in items)

    items_text = ""
    for idx, item in enumerate(items, 1):
        items_text += f"{idx}. {item.get('title')} — {item.get('price')} грн\n"

    message = (
        f"🛍️ <b>Новый заказ!</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        f"📋 <b>Товары:</b>\n{items_text}\n"
        f"💰 <b>Итого:</b> {total_price} грн"
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке заказа в Telegram: {e}")

    return jsonify({"status": "success"})


# ==========================================
# 🤖 ТЕЛЕГРАМ БОТ
# ==========================================
tb_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_quiz_data = {}


@tb_bot.message_handler(commands=["start"])
def start_cmd(message):
    web_app = types.WebAppInfo(url=WEB_APP_URL)

    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(
        types.InlineKeyboardButton(
            text="🛍️ Відкрити каталог", web_app=web_app
        )
    )

    reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reply_kb.add(
        types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
        types.KeyboardButton(text="🧭 Мастер подбора"),
    )

    welcome_text = (
        f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
        f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n\n"
        f"Не знаєте, що обрати? Натисніть «🧭 Мастер подбора» і ми допоможемо! 👇"
    )

    tb_bot.send_message(
        message.chat.id, welcome_text, reply_markup=inline_kb
    )
    tb_bot.send_message(
        message.chat.id,
        "Каталог та помічник завжди поруч ⬇️",
        reply_markup=reply_kb,
    )


@tb_bot.message_handler(func=lambda msg: msg.text == "🧭 Мастер подбора")
def start_quiz(message):
    user_quiz_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📱 Выбрать новый телефон", callback_data="goal_phone"),
    )
    kb.add(
        types.InlineKeyboardButton("🛡️ Аксессуар (чехол / стекло / пленка)", callback_data="goal_acc"),
    )

    tb_bot.send_message(
        message.chat.id,
        "<b>Шаг 1:</b> Что вы ищете сегодня?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@tb_bot.callback_query_handler(func=lambda call: call.data == "goal_phone")
def quiz_phone_step1(call):
    user_quiz_data[call.message.chat.id] = {"goal": "phone"}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📸 Крутая камера", callback_data="pfeature_camera"),
        types.InlineKeyboardButton("🔋 Долгая батарея", callback_data="pfeature_battery"),
    )
    kb.add(
        types.InlineKeyboardButton("🎮 Игры и скорость", callback_data="pfeature_power"),
        types.InlineKeyboardButton("⚖️ Баланс цена/качество", callback_data="pfeature_balance"),
    )

    tb_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text="<b>Шаг 2:</b> Что для вас самое главное в смартфоне?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@tb_bot.callback_query_handler(func=lambda call: call.data.startswith("pfeature_"))
def quiz_phone_finish(call):
    feature = call.data.split("_")[1]
    advice = "Рекомендуем смартфоны с мощным процессором и ярким экраном."
    if feature == "camera":
        advice = "Рекомендуем флагманы с продвинутой оптикой и оптической стабилизацией."
    elif feature == "battery":
        advice = "Рекомендуем модели с аккумулятором от 5000 мАч и быстрой зарядкой."
    elif feature == "balance":
        advice = "Рекомендуем популярные среднебюджетные хиты продаж."

    final_url = f"{WEB_APP_URL}/?category=телефоны"

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="📱 Посмотреть подходящие телефоны",
            web_app=types.WebAppInfo(url=final_url),
        )
    )

    tb_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text=f"✅ <b>Подбор завершен!</b>\n\n💡 <i>{advice}</i>\n\nПерейдите в каталог:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@tb_bot.callback_query_handler(func=lambda call: call.data == "goal_acc")
def quiz_acc_step1(call):
    user_quiz_data[call.message.chat.id] = {"goal": "acc"}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🍏 Apple (iPhone)", callback_data="brand_apple"),
        types.InlineKeyboardButton("📱 Samsung", callback_data="brand_samsung"),
    )
    kb.add(
        types.InlineKeyboardButton("⚡ Xiaomi / Poco", callback_data="brand_xiaomi"),
        types.InlineKeyboardButton("🌐 Другой бренд", callback_data="brand_other"),
    )

    tb_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text="<b>Шаг 2:</b> Укажите бренд вашего устройства:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@tb_bot.callback_query_handler(func=lambda call: call.data.startswith("brand_"))
def quiz_acc_step2(call):
    brand = call.data.split("_")[1]
    user_data = user_quiz_data.get(call.message.chat.id, {})
    user_data["brand"] = brand

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🛡️ Чехол", callback_data="type_Чехлы"),
        types.InlineKeyboardButton("✨ Защитное стекло", callback_data="type_Стекла"),
    )
    kb.add(
        types.InlineKeyboardButton("📜 Гидрогелевая пленка", callback_data="type_Пленки"),
    )

    tb_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text="<b>Шаг 3:</b> Что именно вы ищете?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@tb_bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def quiz_acc_finish(call):
    p_type = call.data.split("_")[1]
    user_data = user_quiz_data.get(call.message.chat.id, {})
    brand = user_data.get("brand", "all")

    search_term = ""
    if brand == "apple":
        search_term = "iphone"
    elif brand == "samsung":
        search_term = "samsung"
    elif brand == "xiaomi":
        search_term = "xiaomi"

    final_url = f"{WEB_APP_URL}/?category={p_type}&search={search_term}"

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="🎯 Посмотреть варианты",
            web_app=types.WebAppInfo(url=final_url),
        )
    )

    tb_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text="✅ <b>Подбор завершен!</b> Нажмите кнопку ниже, чтобы открыть каталог:",
        parse_mode="HTML",
        reply_markup=kb,
    )


def run_bot():
    try:
        tb_bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")


threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
