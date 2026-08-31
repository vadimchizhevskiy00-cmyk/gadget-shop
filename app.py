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

# === НАСТРОЙКИ ПЕРЕМЕННЫХ ===
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

            # Характеристики устройства
            clean_row["Процессор"] = clean_val(clean_row.get("Процессор", "-"))
            clean_row["Мощность"] = clean_val(clean_row.get("Мощность", "-"))
            clean_row["Экран"] = clean_val(clean_row.get("Экран", "-"))
            clean_row["Камера"] = clean_val(clean_row.get("Камера", "-"))
            clean_row["Батарея"] = clean_val(clean_row.get("Батарея", "-"))

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


# === ТЕЛЕГРАМ БОТ (TELEBOT) ===


@bot.message_handler(commands=["start"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)

        # Клавиатура из 3 кнопок без лишних пунктов
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app)
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


@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин та контакти")
def contacts_cmd(message):
    text = (
        "📍 <b>Наш магазин чекає на вас!</b>\n\n"
        "🏢 <b>Адреса:</b> м. Чугуїв, бул. Центральний, 8\n"
        "⏰ <b>Графік роботи:</b> Пн-Пт: 08:00 — 18:00 | Сб-Нд: 08:00 — 17:00\n"
        "📞 <b>Телефон:</b> +380 97 391 64 00, +380 63 189 16 83\n"
        "💬 <b>Менеджер:</b> @smthwrng121"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(func=lambda msg: msg.text == "❓ Часті запитання (FAQ)")
def faq_cmd(message):
    text = (
        "❓ <b>Часті запитання:</b>\n\n"
        "1️⃣ <b>Чи є гарантія на техніку?</b>\n"
        "— Так! На нову техніку діє гарантія 12 місяців, на б/в — від 3 місяців.\n\n"
        "2️⃣ <b>Як працює бронювання?</b>\n"
        "— Ви обираєте товар у веб-каталозі, тиснете «Забронювати», і ми відкладаємо його для вас на 24 години.\n\n"
        "3️⃣ <b>Чи допомагаєте з налаштуванням та переносом даних?</b>\n"
        "— Так, наші спеціалісти допоможуть перенести всі ваші контакти, фото та додатки на новий пристрій при покупці у магазині."
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# === FLASK МАРШРУТЫ ===


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
