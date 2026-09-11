import os
import re
import csv
import io
import asyncio
import threading
import time
from flask import Flask, render_template, request, jsonify
import requests
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

app = Flask(__name__)

# Токены и URL (берутся из переменных окружения Render / OS)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "396778432")
CSV_URL = os.environ.get("CSV_URL", "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv")

# Глобальные структуры для отслеживания наличия и подписок
notification_subscriptions = {}
last_stock_status = {}

def clean_val(val):
    if val is None:
        return ""
    return str(val).strip()

def get_products():
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return []
        
        csv_data = response.text
        reader = csv.DictReader(io.StringIO(csv_data))
        products = []
        
        for row in reader:
            cleaned_row = {clean_val(k): clean_val(v) for k, v in row.items()}
            
            # Разбор памяти и цен через запятую
            memory_raw = cleaned_row.get("Память", "") or cleaned_row.get("Пам'ять", "")
            price_raw = cleaned_row.get("Цена", "0") or cleaned_row.get("Ціна", "0")
            
            memory_list = [m.strip() for m in memory_raw.split(",") if m.strip()] if memory_raw else []
            price_list = [p.strip() for p in price_raw.split(",") if p.strip()] if price_raw else [price_raw]
            
            cleaned_row["memory_list"] = memory_list
            cleaned_row["price_list"] = price_list
            
            # Разбор цветов и соответствующих фото через запятую
            color_raw = cleaned_row.get("Цвет", "") or cleaned_row.get("Колір", "")
            photo_raw = cleaned_row.get("Фото", "")
            
            color_list = [c.strip() for c in color_raw.split(",") if c.strip()] if color_raw else []
            photo_list = [p.strip() for p in photo_raw.split(",") if p.strip()] if photo_raw else []
            
            cleaned_row["color_list"] = color_list
            cleaned_row["photo_list"] = photo_list
            
            products.append(cleaned_row)
            
        return products
    except Exception as e:
        print(f"Error fetching CSV: {e}")
        return []

# --- ФОНОВЫЙ ТРЕКЕР ИЗМЕНЕНИЯ НАЛИЧИЯ (15 СЕК) ---
def check_stock_changes():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    while True:
        try:
            products = get_products()
            for p in products:
                title = clean_val(p.get("Название", "") or p.get("Назва", ""))
                status = clean_val(p.get("Статус", "")).lower()
                
                is_in_stock = not ('нет' in status or 'немає' in status or 'закончил' in status)
                
                if title in last_stock_status:
                    was_in_stock = last_stock_status[title]
                    if not was_in_stock and is_in_stock:
                        if title in notification_subscriptions and notification_subscriptions[title]:
                            subscribers = notification_subscriptions[title]
                            price = p.get("price_list", [p.get("Цена", "0")])[0]
                            msg = f"🎉 **Товар знову в наявності!**\n\n📱 **{title}**\n💰 Ціна: {price} грн\n\nЗавітайте до магазину або забронюйте прямо зараз!"
                            
                            for chat_id in subscribers:
                                try:
                                    asyncio.run(bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"))
                                except Exception as err:
                                    print(f"Failed to send notification to {chat_id}: {err}")
                            
                            notification_subscriptions[title] = []
                            
                last_stock_status[title] = is_in_stock
        except Exception as e:
            print(f"Error in stock tracker loop: {e}")
        
        time.sleep(15)

# --- МАРШРУТЫ FLASK ---
@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip().lower()
    
    all_products = get_products()
    filtered = []
    
    for p in all_products:
        p_cat = clean_val(p.get("Категория", "") or p.get("Категорія", "")).lower()
        p_title = clean_val(p.get("Название", "") or p.get("Назва", "")).lower()
        
        if category and p_cat != category.lower():
            continue
            
        if search and search not in p_title:
            continue
            
        filtered.append(p)
        
    return render_template("index.html", products=filtered, category=category, search=search)

@app.route("/api/accessories")
def api_accessories():
    model = request.args.get("model", "").strip().lower()
    if not model:
        return jsonify([])

    products = get_products() or []
    exact_accessories = []
    film_accessories = []

    for p in products:
        cat = clean_val(p.get("Категория", "") or p.get("Категорія", "")).lower()

        if cat in ["чехлы", "стекла", "пленки", "чохли", "скло", "плівки"]:
            compat = clean_val(p.get("Совместимость", "") or p.get("Сумісність", "")).lower()
            title = clean_val(p.get("Название", "") or p.get("Назва", "")).lower()

            item = {
                "Название": p.get("Название", "") or p.get("Назва", ""),
                "Цена": p.get("price_list", [p.get("Цена", "0")])[0],
            }

            if model in compat or model in title:
                exact_accessories.append(item)
            elif cat in ["пленки", "плівки"] or ("пленка" in title or "плівка" in title):
                film_accessories.append(item)

    result = exact_accessories if exact_accessories else film_accessories
    return jsonify(result[:4])

@app.route("/order", methods=["POST"])
def place_order():
    data = request.json or {}
    order_type = data.get("type", "order")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    if order_type == "subscribe_notify":
        chat_id = data.get("chat_id")
        product_name = data.get("product_name")
        if chat_id and product_name:
            if product_name not in notification_subscriptions:
                notification_subscriptions[product_name] = []
            if chat_id not in notification_subscriptions[product_name]:
                notification_subscriptions[product_name].append(chat_id)
        return jsonify({"status": "ok"})

    if order_type in ["order", "booking"]:
        name = data.get("name", "")
        phone = data.get("phone", "")
        items = data.get("items", [])
        
        items_text = "\n".join([f"• {i['title']} — {i['price']} грн" for i in items])
        
        total = 0
        for i in items:
            p_val = str(i.get('price', '0')).replace('грн', '').strip()
            if p_val.isdigit():
                total += float(p_val)
        
        header = "📌 **НОВЕ БРОНЮВАННЯ (24 ГОД)**" if order_type == "booking" else "🛍️ **НОВЕ ЗАМОВЛЕННЯ**"
        msg = f"{header}\n\n👤 **Клієнт:** {name}\n📞 **Телефон:** {phone}\n\n📦 **Товари:**\n{items_text}\n\n💰 **Разом:** {total} грн"
        
        try:
            asyncio.run(bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown"))
        except Exception as e:
            print(f"Error sending order notification: {e}")
            
        return jsonify({"status": "ok"})

    return jsonify({"status": "error"}), 400

# --- ИНИЦИАЛИЗАЦИЯ И ЗАПУСК TELEGRAM-БОТА ---
async def start_bot_app():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Ласкаво просимо! Натисніть кнопку нижче, щоб відкрити магазин.")

    application.add_handler(CommandHandler("start", start_cmd))
    
    # Удаление вебхука перед поллингом для защиты от конфликтов
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

def run_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot_app())
    loop.run_forever()

if __name__ == "__main__":
    # 1. Запуск потока отслеживания остатков
    threading.Thread(target=check_stock_changes, daemon=True).start()
    
    # 2. Запуск потока Telegram Bot (CommandHandler /start)
    threading.Thread(target=run_async_loop, daemon=True).start()
    
    # 3. Запуск веб-сервера Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
