import csv
import io
import os
import sys
import threading
import traceback
from flask import Flask, jsonify, render_template, request
import requests
import telebot
from telebot import types

# === НАСТРОЙКИ И ПЕРЕМЕННЫЕ ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "396778432")
WEB_APP_URL = os.environ.get(
    "WEB_APP_URL", "https://gadget-shop-v5kh.onrender.com"
)
CSV_URL = os.environ.get(
    "CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv",
)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Хранилище временного выбора пользователя при примерке чехла
fitting_room_data = {}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def clean_val(val):
    if val is None:
        return ""
    return str(val).strip()


def parse_memory_and_prices(memory_raw, price_raw):
    m_str = clean_val(memory_raw)
    p_str = clean_val(price_raw)
    m_list = [x.strip() for x in m_str.split("/") if x.strip()] if m_str else []
    p_list = [x.strip() for x in p_str.split("/") if x.strip()] if p_str else []
    return m_list, p_list


def get_products():
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        reader = csv.DictReader(io.StringIO(response.text))

        products = []
        for row in reader:
            clean_row = {clean_val(k): clean_val(v) for k, v in row.items()}
            m_list, p_list = parse_memory_and_prices(
                clean_row.get("Память", ""), clean_row.get("Цена", "")
            )
            clean_row["memory_list"] = m_list
            clean_row["price_list"] = p_list
            products.append(clean_row)

        return products
    except Exception as e:
        print(f"Error fetching CSV: {e}", file=sys.stderr)
        return []


def send_telegram_msg(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending TG msg: {e}", file=sys.stderr)


# === ЛОГИКА ТЕЛЕГРАМ БОТА (TELEBOT) ===


@bot.message_handler(commands=["start"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
            types.KeyboardButton(text="📸 Приміряти чохол"),
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


@bot.message_handler(func=lambda msg: msg.text == "📸 Приміряти чохол")
def start_fitting(message):
    fitting_room_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📱 iPhone 13 / 14", callback_data="fit_model_iphone13_14"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📱 iPhone 15 / 15 Pro", callback_data="fit_model_iphone15"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📱 iPhone 16 / 16 Pro", callback_data="fit_model_iphone16"
        )
    )

    bot.send_message(
        message.chat.id,
        "📸 <b>Віртуальна примірочна чохлів!</b>\n\nОберіть модель вашого смартфона:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("fit_"))
def handle_fitting_callbacks(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data

    if data.startswith("fit_model_"):
        model_code = data.replace("fit_model_", "")
        fitting_room_data[chat_id] = {"model": model_code}

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "⚫ Black / Midnight", callback_data="fit_color_black"
            ),
            types.InlineKeyboardButton(
                "⚪ White / Silver", callback_data="fit_color_white"
            ),
        )
        kb.add(
            types.InlineKeyboardButton(
                "🩶 Natural Titanium", callback_data="fit_color_gray"
            ),
            types.InlineKeyboardButton(
                "🔵 Blue / Pacific", callback_data="fit_color_blue"
            ),
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>Крок 2:</b> Вкажіть колір корпусу вашого пристрою:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("fit_color_"):
        color_code = data.replace("fit_color_", "")
        if chat_id in fitting_room_data:
            fitting_room_data[chat_id]["color"] = color_code

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "💎 Прозорий Silicone Case z MagSafe",
                callback_data="fit_case_clear",
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "🖤 Чорний Soft-Touch Silicone",
                callback_data="fit_case_black",
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "🤎 Шкіряний Leather Case", callback_data="fit_case_leather"
            )
        )

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>Крок 3:</b> Який чохол приміряємо?",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("fit_case_"):
        case_type = data.replace("fit_case_", "")
        user_fit = fitting_room_data.get(chat_id, {})
        model = user_fit.get("model", "iphone")
        color = user_fit.get("color", "black")

        sample_photos = {
            "clear": "https://images.unsplash.com/photo-1603313011101-320f26a4f6f6?w=600",
            "black": "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600",
            "leather": "https://images.unsplash.com/photo-1541877944-ac82a091518a?w=600",
        }
        photo_url = sample_photos.get(case_type, sample_photos["clear"])

        kb = types.InlineKeyboardMarkup()
        catalog_url = f"{WEB_APP_URL}/?category=Чехлы"
        kb.add(
            types.InlineKeyboardButton(
                "🛍️ Забронювати цей чохол",
                web_app=types.WebAppInfo(url=catalog_url),
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "🔄 Приміряти інший варіант",
                callback_data="fit_model_iphone15",
            )
        )

        bot.delete_message(chat_id=chat_id, message_id=message_id)
        bot.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=(
                f"✨ <b>Ось як це буде виглядати!</b>\n\n"
                f"📱 <b>Пристрій:</b> {model.upper()} ({color.capitalize()})\n"
                f"🛡️ <b>Чохол:</b> {case_type.capitalize()} Edition\n\n"
                f"💡 <i>Усі чохли мають ідеальну посадку та захист бортів камери.</i>"
            ),
            parse_mode="HTML",
            reply_markup=kb,
        )


@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин та контакти")
def contacts_cmd(message):
    text = (
        "📍 <b>Наш магазин чекає на вас!</b>\n\n"
        "🏢 <b>Адреса:</b> м. Київ, вул. Хрещатик, 1\n"
        "⏰ <b>Графік роботи:</b> Щодня з 10:00 до 20:00\n"
        "📞 <b>Телефон:</b> +380 99 123 45 67\n"
        "💬 <b>Менеджер:</b> @manager_username"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(func=lambda msg: msg.text == "❓ Часті запитання (FAQ)")
def faq_cmd(message):
    text = (
        "❓ <b>Часті запитання:</b>\n\n"
        "1️⃣ <b>Чи є гарантія на техніку?</b>\n"
        "— Так! На нову техніку діє гарантія 12 місяців, на б/в — від 3 місяців.\n\n"
        "2️⃣ <b>Як працює бронювання?</b>\n"
        "— Ви обираєте товар у веб-каталозі, тиснете «Забронювати», і ми відкладаємо його для вас на 24 години."
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# === МАРШРУТЫ FLASK (ВЕБ-ПРИЛОЖЕНИЕ) ===


@app.route("/")
def index():
    try:
        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip().lower()

        products = get_products() or []
        filtered_products = []

        for p in products:
            p_cat = clean_val(p.get("Категория", "")).lower()
            if category and category.lower() != "all":
                if p_cat != category.lower():
                    continue

            p_title = clean_val(p.get("Название", "")).lower()
            p_compat = clean_val(p.get("Совместимость", "")).lower()

            if search and (search not in p_title and search not in p_compat):
                continue

            filtered_products.append(p)

        return render_template(
            "index.html",
            products=filtered_products,
            category=category,
            search=search,
        )
    except Exception as e:
        print(
            f"CRITICAL ERROR IN INDEX ROUTE:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return f"<h3>Помилка завантаження:</h3><pre>{e}</pre>", 500


@app.route("/api/accessories")
def api_accessories():
    model = request.args.get("model", "").strip().lower()
    if not model:
        return jsonify([])

    products = get_products() or []
    accessories = []

    for p in products:
        cat = clean_val(p.get("Категория", "")).lower()
        if cat in ["чехлы", "стекла", "пленки", "чохли", "скло", "плівки"]:
            compat = clean_val(p.get("Совместимость", "")).lower()
            title = clean_val(p.get("Название", "")).lower()

            if model in compat or model in title:
                accessories.append(
                    {
                        "Название": p.get("Название", ""),
                        "Цена": p.get("Цена", "0"),
                    }
                )

    return jsonify(accessories[:4])


@app.route("/order", methods=["POST"])
def order():
    try:
        data = request.json or {}
        req_type = data.get("type", "order")

        if req_type == "subscribe_notify":
            chat_id = data.get("chat_id")
            product_name = data.get("product_name")

            admin_msg = (
                f"🔔 <b>НОВА ЗАЯВКА НА ПОВІДОМЛЕННЯ!</b>\n\n"
                f"📦 <b>Товар:</b> {product_name}\n"
                f"👤 <b>Chat ID:</b> {chat_id}"
            )
            send_telegram_msg(ADMIN_CHAT_ID, admin_msg)
            return jsonify({"status": "ok"})

        elif req_type == "notify":
            product_name = data.get("product_name")
            name = data.get("name")
            phone = data.get("phone")

            admin_msg = (
                f"🔔 <b>НОВА ЗАЯВКА НА ПОВІДОМЛЕННЯ!</b>\n\n"
                f"📦 <b>Товар:</b> {product_name}\n"
                f"👤 <b>Клієнт:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}"
            )
            send_telegram_msg(ADMIN_CHAT_ID, admin_msg)
            return jsonify({"status": "ok"})

        else:
            items = data.get("items", [])
            name = data.get("name")
            phone = data.get("phone")

            title_hdr = (
                "📌 <b>НОВЕ БРОНЮВАННЯ (на 24 год)!</b>"
                if req_type == "booking"
                else "🛒 <b>НОВЕ ЗАМОВЛЕННЯ!</b>"
            )

            total_sum = sum(int(i.get("price", 0)) for i in items)
            items_str = "\n".join(
                [f"• {i.get('title')} — {i.get('price')} грн" for i in items]
            )

            admin_msg = (
                f"{title_hdr}\n\n"
                f"👤 <b>Клієнт:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n\n"
                f"📦 <b>Товари:</b>\n{items_str}\n\n"
                f"💰 <b>Разом:</b> {total_sum} грн"
            )
            send_telegram_msg(ADMIN_CHAT_ID, admin_msg)
            return jsonify({"status": "ok"})

    except Exception as e:
        print(f"Error handling order: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


# Запуск бота в отдельном потоке, чтобы он не блокировал Flask веб-сервер
def run_bot():
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot error: {e}", file=sys.stderr)


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
