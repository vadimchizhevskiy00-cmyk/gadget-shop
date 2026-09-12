import csv
import io
import json
import os
import re
import sys
import threading
import time
import traceback
from flask import Flask, jsonify, render_template, request
import requests
import telebot
from telebot import types

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "396778432")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://gadget-shop-v5kh.onrender.com")
CSV_URL = os.environ.get("CSV_URL", "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv")

SUBS_FILE = "subscriptions.json"
ORDERS_FILE = "orders.json"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)


# === ХРАНИЛИЩЕ ПОДПИСОК И ЗАКАЗОВ ===
def load_json(filepath):
    if not os.path.exists(filepath):
        return [] if filepath == SUBS_FILE else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return [] if filepath == SUBS_FILE else {}


def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {e}", file=sys.stderr)


def clean_val(val):
    if val is None:
        return ""
    return str(val).strip()


def parse_memory_and_prices(memory_raw, price_raw):
    m_str = clean_val(memory_raw)
    p_str = clean_val(price_raw)
    m_del = "/" if "/" in m_str else ","
    p_del = "/" if "/" in p_str else ","
    
    m_list = [x.strip() for x in m_str.split(m_del) if x.strip()] if m_str else []
    p_list = [x.strip() for x in p_str.split(p_del) if x.strip()] if p_str else []
    return m_list, p_list


def parse_colors_and_photos(color_raw, photo_raw):
    c_str = clean_val(color_raw)
    p_str = clean_val(photo_raw)
    c_list = [x.strip() for x in c_str.split(",") if x.strip()] if c_str else []
    p_list = [x.strip() for x in p_str.split(",") if x.strip()] if p_str else []
    return c_list, p_list


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
                clean_row.get("Память", "") or clean_row.get("Пам'ять", ""),
                clean_row.get("Цена", "") or clean_row.get("Ціна", "")
            )
            clean_row["memory_list"] = m_list
            clean_row["price_list"] = p_list

            c_list, photo_list = parse_colors_and_photos(
                clean_row.get("Цвет", "") or clean_row.get("Колір", ""),
                clean_row.get("Фото", "")
            )
            clean_row["color_list"] = c_list
            clean_row["photo_list"] = photo_list

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


# === ФОНОВЫЙ МОНИТОРИНГ НАЛИЧИЯ (15 СЕКУНД) ===
def check_stock_subscriptions():
    while True:
        try:
            time.sleep(15)
            subs = load_json(SUBS_FILE)
            if not subs:
                continue

            products = get_products()
            if not products:
                continue

            remaining_subs = []
            updated = False

            for sub in subs:
                p_name = sub.get("product_name", "").strip().lower()
                chat_id = sub.get("chat_id")

                found_and_in_stock = False
                matched_title = ""

                for p in products:
                    prod_title = clean_val(p.get("Название", "")).strip().lower()
                    status = clean_val(p.get("Статус", "")).strip().lower()

                    if prod_title in p_name or p_name in prod_title:
                        is_out = any(
                            kw in status for kw in ["нет", "немає", "закончил"]
                        )
                        if not is_out:
                            found_and_in_stock = True
                            matched_title = p.get("Название", "")
                            break

                if found_and_in_stock:
                    msg = (
                        f"🎉 <b>Чудові новини! Товар з'явився в наявності!</b>\n\n"
                        f"📦 <b>{matched_title}</b> вже чекає на вас у нашому магазині!\n\n"
                        f"Завітайте до нас або забронюйте товар у каталозі прямо зараз. 📱"
                    )
                    send_telegram_msg(chat_id, msg)
                    updated = True
                else:
                    remaining_subs.append(sub)

            if updated:
                save_json(SUBS_FILE, remaining_subs)

        except Exception as e:
            print(f"Error in stock checker: {e}", file=sys.stderr)


# === ТЕЛЕГРАМ БОТ (ОБРАБОТКА КОМАНД) ===
@bot.message_handler(commands=["start", "help"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)
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


@bot.message_handler(
    func=lambda msg: msg.text and "Магазин та контакти" in msg.text
)
def contacts_cmd(message):
    text = (
        "📍 <b>Наш магазин чекає на вас!</b>\n\n"
        "🏢 <b>Адреса:</b> м. Чугуїв, бул. Центральний, 8\n"
        "⏰ <b>Графік роботи:</b> Пн-Пт: 08:00 — 18:00 | Сб-Нд: 08:00 — 17:00\n"
        "📞 <b>Телефон:</b> +380 97 391 64 00, +380 63 189 16 83\n"
        "💬 <b>Менеджер:</b> @smthwrng121"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(
    func=lambda msg: msg.text and "Часті запитання" in msg.text
)
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


# === FLASK РУТЫ ===
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
    exact_accessories = []
    film_accessories = []

    for p in products:
        cat = clean_val(p.get("Категория", "")).lower()

        if cat in ["чехлы", "стекла", "пленки", "чохли", "скло", "плівки"]:
            compat = clean_val(p.get("Совместимость", "")).lower()
            title = clean_val(p.get("Название", "")).lower()

            item = {
                "Название": p.get("Название", ""),
                "Цена": p.get("price_list", [p.get("Цена", "0")])[0] if p.get("price_list") else p.get("Цена", "0"),
            }

            if model in compat or model in title:
                exact_accessories.append(item)

            elif cat in ["пленки", "плівки"] or (
                "пленка" in title or "плівка" in title
            ):
                film_accessories.append(item)

    result = exact_accessories if exact_accessories else film_accessories
    return jsonify(result[:4])


@app.route("/order", methods=["POST"])
def order():
    try:
        data = request.json or {}
        req_type = data.get("type", "order")

        if req_type in ["subscribe_notify", "notify"]:
            chat_id = data.get("chat_id")
            product_name = data.get("product_name")
            name = data.get("name", "Клієнт")
            phone = data.get("phone", "-")

            if chat_id:
                subs = load_json(SUBS_FILE)
                if not any(
                    s.get("chat_id") == chat_id
                    and s.get("product_name") == product_name
                    for s in subs
                ):
                    subs.append(
                        {
                            "chat_id": chat_id,
                            "product_name": product_name,
                            "name": name,
                            "phone": phone,
                        }
                    )
                    save_json(SUBS_FILE, subs)

            admin_msg = (
                f"🔔 <b>НОВА ЗАЯВКА НА ПОВІДОМЛЕННЯ!</b>\n\n"
                f"📦 <b>Товар:</b> {product_name}\n"
                f"👤 <b>Клієнт:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n"
                f"💬 <b>Chat ID:</b> {chat_id or 'Немає'}"
            )
            send_telegram_msg(ADMIN_CHAT_ID, admin_msg)
            return jsonify({"status": "ok"})

        else:
            items = data.get("items", [])
            name = data.get("name")
            phone = data.get("phone")
            client_chat_id = data.get("chat_id")  # Чат покупателя
            order_id = data.get("order_id", f"ORD-{int(time.time())}")

            total_sum = 0
            for i in items:
                p_str = str(i.get("price", "0"))
                digits = re.sub(r"[^\d]", "", p_str)
                if digits:
                    total_sum += int(digits)

            # Сохранение заказа для сканирования QR-кода
            orders = load_json(ORDERS_FILE)
            orders[order_id] = {
                "order_id": order_id,
                "name": name,
                "phone": phone,
                "items": items,
                "total": total_sum,
                "status": "active",
                "type": req_type,
                "chat_id": client_chat_id,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_json(ORDERS_FILE, orders)

            # 1. Отправляем уведомление администратору
            title_hdr = (
                "📌 <b>НОВЕ БРОНЮВАННЯ (на 24 год)!</b>"
                if req_type == "booking"
                else "🛒 <b>НОВЕ ЗАМОВЛЕННЯ!</b>"
            )
            items_str = "\n".join(
                [f"• {i.get('title')} — {i.get('price')} грн" for i in items]
            )

            admin_msg = (
                f"{title_hdr}\n"
                f"🧾 <b>Чек:</b> #{order_id}\n\n"
                f"👤 <b>Клієнт:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n"
                f"💬 <b>Chat ID:</b> {client_chat_id or 'Невідомо'}\n\n"
                f"📦 <b>Товари:</b>\n{items_str}\n\n"
                f"💰 <b>Разом:</b> {total_sum} грн"
            )
            send_telegram_msg(ADMIN_CHAT_ID, admin_msg)

            # 2. Отправляем чек с QR-кодом ПОКУПАТЕЛЮ в его личные сообщения
            if client_chat_id:
                check_url = f"{WEB_APP_URL}/admin/check?order={order_id}"
                qr_api_url = f"https://quickchart.io/qr?text={requests.utils.quote(check_url)}&size=300"

                client_msg = (
                    f"✅ <b>Ваше бронювання успішно оформлено!</b>\n\n"
                    f"🧾 <b>Чек:</b> #{order_id}\n"
                    f"👤 <b>Клієнт:</b> {name}\n"
                    f"📦 <b>Замовлення:</b>\n{items_str}\n\n"
                    f"💰 <b>Разом до сплати:</b> {total_sum} грн\n"
                    f"📍 <b>Адреса:</b> м. Чугуїв, бул. Центральний, 8\n"
                    f"⏱️ <b>Бронь діє 24 години!</b>\n\n"
                    f"👇 <i>Покажіть цей QR-код або номер чека продавцю на касі:</i>"
                )
                
                try:
                    qr_resp = requests.get(qr_api_url, timeout=10)
                    if qr_resp.status_code == 200:
                        qr_bytes = io.BytesIO(qr_resp.content)
                        qr_bytes.name = f"{order_id}.png"
                        bot.send_photo(client_chat_id, photo=qr_bytes, caption=client_msg, parse_mode="HTML")
                    else:
                        send_telegram_msg(client_chat_id, client_msg)
                except Exception as e:
                    print(f"Error sending photo to client: {e}", file=sys.stderr)
                    send_telegram_msg(client_chat_id, client_msg)

            return jsonify({"status": "ok", "order_id": order_id})

    except Exception as e:
        print(f"Error handling order: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


# === ПРОВЕРКА И ПОГАШЕНИЕ QR-КОДА (ДЛЯ ПРОДАВЦА) ===
@app.route("/admin/check")
def admin_check():
    order_id = request.args.get("order", "").strip()
    action = request.args.get("action", "").strip()
    orders = load_json(ORDERS_FILE)

    if not order_id or order_id not in orders:
        return "<h2 style='color:red; text-align:center; margin-top:40px;'>❌ Замовлення не знайдено!</h2>", 404

    order_data = orders[order_id]

    if action == "complete" and order_data["status"] == "active":
        order_data["status"] = "completed"
        save_json(ORDERS_FILE, orders)
        
        send_telegram_msg(
            ADMIN_CHAT_ID, 
            f"✅ <b>ТОВАР ВИДАНО!</b>\n🧾 Чек: #{order_id}\n👤 Клієнт: {order_data['name']}\n💰 Сума: {order_data['total']} грн"
        )

    items_html = "".join([f"<li><b>{i.get('title')}</b> — {i.get('price')} грн</li>" for i in order_data["items"]])
    status_badge = "<span style='color:green; font-weight:bold;'>🟢 АКТИВНЕ БРОНЮВАННЯ</span>" if order_data["status"] == "active" else "<span style='color:gray; font-weight:bold;'>⚪ ВИДАНО / ПОГАШЕНО</span>"

    button_html = ""
    if order_data["status"] == "active":
        button_html = f"<a href='/admin/check?order={order_id}&action=complete' style='display:block; width:100%; text-align:center; background:#34c759; color:white; padding:16px 0; border-radius:12px; font-weight:bold; text-decoration:none; margin-top:20px; font-size:18px;'>✅ ВИДАТИ ТОВАР</a>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Перевірка замовлення #{order_id}</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #f2f2f7; padding: 20px; margin:0; }}
            .card {{ background: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: 20px auto; }}
            h2 {{ margin-top:0; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Чек #{order_id}</h2>
            <p><b>Статус:</b> {status_badge}</p>
            <p><b>Клієнт:</b> {order_data['name']}</p>
            <p><b>Телефон:</b> {order_data['phone']}</p>
            <p><b>Час:</b> {order_data['time']}</p>
            <hr>
            <p><b>Товари:</b></p>
            <ul>{items_html}</ul>
            <p style='font-size: 18px; font-weight: bold; color: #007aff;'>Сума: {order_data['total']} грн</p>
            {button_html}
        </div>
    </body>
    </html>
    """
    return html


# === ЗАПУСК И ОБРАБОТКА ПОТОКОВ ===
def start_bot_polling():
    while True:
        try:
            bot.remove_webhook()
            print("Запуск polling бота...", file=sys.stderr)
            bot.infinity_polling(
                timeout=20, long_polling_timeout=10, skip_pending=True
            )
        except Exception as e:
            print(f"Ошибка polling: {e}. Перезапуск...", file=sys.stderr)
            time.sleep(3)


threading.Thread(target=start_bot_polling, daemon=True).start()
threading.Thread(target=check_stock_subscriptions, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
