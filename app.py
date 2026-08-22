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
# ⚙️ НАСТРОЙКИ (Укажите ваши данные)
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"
TELEGRAM_CHAT_ID = "396778432"

# Ссылка на вашу опубликованную CSV-таблицу Google Sheets
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"

# Ваша прямая ссылка на сервис Render (например, https://my-shop.onrender.com)
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"


# ==========================================
# 🛠️ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def clean_val(val):
    """Очищает значения от NaN для предотвращения ошибок jsonify"""
    if val is None:
        return "-"
    if isinstance(val, float) and math.isnan(val):
        return "-"
    val_str = str(val).strip()
    return val_str if val_str and val_str != "nan" else "-"


def get_products():
    """Чтение продуктов напрямую по ссылке CSV_URL из Google Sheets"""
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
            return products
        else:
            print(f"Ошибка загрузки CSV: статус {response.status_code}")
            return []
    except Exception as e:
        print(f"Ошибка при чтении CSV по ссылке: {e}")
        return []


# ==========================================
# 🌐 МАРШРУТЫ FLASK (САЙТ/МИНИ-АПП)
# ==========================================
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
        if search and search not in p_title:
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

    # 1. Поиск совпадений в Названии и в колонке Совместимость
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

    # 2. Если стекла для модели (или аналогов) нет — подтягиваем пленки
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
# 🤖 ТЕЛЕГРАМ БОТ (ВСТРОЕННЫЙ ФОНОВЫЙ ПРОЦЕСС)
# ==========================================
tb_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@tb_bot.message_handler(commands=["start"])
def start_cmd(message):
    web_app = types.WebAppInfo(url=WEB_APP_URL)

    # 1. Инлайн-кнопка прямо под приветственным текстом
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(
        types.InlineKeyboardButton(
            text="🛍️ Відкрити каталог", web_app=web_app
        )
    )

    # 2. Нижняя зафиксированная кнопка
    reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reply_kb.add(
        types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app)
    )

    welcome_text = (
        f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
        f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n"
        f"Натисніть кнопку нижче, щоб переглянути каталог та зробити замовлення 👇"
    )

    # Отправляем сообщение
    tb_bot.send_message(
        message.chat.id, welcome_text, reply_markup=inline_kb
    )
    tb_bot.send_message(
        message.chat.id,
        "Каталог завжди доступний за кнопкою знизу ⬇️",
        reply_markup=reply_kb,
    )


def run_bot():
    try:
        print("Telegram-бот успешно запущен в фоновом режиме...")
        tb_bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в фоновой работе бота: {e}")


# Запускаем бота в отдельном фоновом потоке при старте Flask
threading.Thread(target=run_bot, daemon=True).start()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
