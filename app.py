import os
import re
import csv
import io
import asyncio
import threading
import time
import logging
from flask import Flask, render_template, request, jsonify
import requests
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Переменные окружения и конфигурация
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "396778432")
CSV_URL = os.environ.get("CSV_URL", "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://gadget-shop-v5kh.onrender.com")

# Хранилище подписок и статусов товаров
notification_subscriptions = {}
last_stock_status = {}

def clean_val(val):
    """Очистка строк от лишних пробелов и None значений."""
    if val is None:
        return ""
    return str(val).strip()

def get_products():
    """Загрузка и парсинг CSV из Google Таблиц."""
    try:
        response = requests.get(CSV_URL, timeout=12)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            logger.error(f"Failed to fetch CSV, status code: {response.status_code}")
            return []
        
        csv_data = response.text
        reader = csv.DictReader(io.StringIO(csv_data))
        products = []
        
        for row in reader:
            cleaned_row = {clean_val(k): clean_val(v) for k, v in row.items()}
            
            # --- РАЗБОР ПАМЯТИ И ЦЕН ---
            memory_raw = cleaned_row.get("Память", "") or cleaned_row.get("Пам'ять", "")
            price_raw = cleaned_row.get("Цена", "0") or cleaned_row.get("Ціна", "0")
            
            memory_list = [m.strip() for m in memory_raw.split(",") if m.strip()] if memory_raw else []
            price_list = [p.strip() for p in price_raw.split(",") if p.strip()] if price_raw else [price_raw]
            
            cleaned_row["memory_list"] = memory_list
            cleaned_row["price_list"] = price_list
            
            # --- РАЗБОР ЦВЕТОВ И СООТВЕТСТВУЮЩИХ ФОТО ---
            color_raw = cleaned_row.get("Цвет", "") or cleaned_row.get("Колір", "")
            photo_raw = cleaned_row.get("Фото", "")
            
            color_list = [c.strip() for c in color_raw.split(",") if c.strip()] if color_raw else []
            photo_list = [p.strip() for p in photo_raw.split(",") if p.strip()] if photo_raw else []
            
            cleaned_row["color_list"] = color_list
            cleaned_row["photo_list"] = photo_list
            
            products.append(cleaned_row)
            
        return products
    except Exception as e:
        logger.error(f"Error fetching CSV: {e}")
        return []

# --- ФОНОВЫЙ ТРЕКЕР ИЗМЕНЕНИЯ НАЛИЧИЯ (15 СЕК) ---
def check_stock_changes():
    """Каждые 15 секунд проверяет Google Таблицу на появление товаров в наличии."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    while True:
        try:
            products = get_products()
            for p in products:
                title = clean_val(p.get("Название", "") or p.get("Назва", ""))
                status = clean_val(p.get("Статус", "")).lower()
                
                # Товар в наличии, если статус не содержит слов "нет", "немає", "закончился"
                is_in_stock = not ('нет' in status or 'немає' in status or 'закончил' in status)
                
                if title in last_stock_status:
                    was_in_stock = last_stock_status[title]
                    if not was_in_stock and is_in_stock:
                        if title in notification_subscriptions and notification_subscriptions[title]:
                            subscribers = notification_subscriptions[title]
                            price = p.get("price_list", [p.get("Цена", "0")])[0]
                            
                            msg = (
                                f"🎉 **Товар знову в наявності!**\n\n"
                                f"📱 **{title}**\n"
                                f"💰 Ціна: **{price} грн**\n\n"
                                f"Завітайте до магазину або забронюйте прямо зараз через вітрину!"
                            )
                            
                            for chat_id in subscribers:
                                try:
                                    asyncio.run(bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"))
                                except Exception as err:
                                    logger.error(f"Failed to send notification to {chat_id}: {err}")
                            
                            # Очищаем список после успешной рассылки
                            notification_subscriptions[title] = []
                            
                last_stock_status[title] = is_in_stock
        except Exception as e:
            logger.error(f"Error in stock tracker loop: {e}")
        
        time.sleep(15)

# --- FLASK РОУТЫ И API ---
@app.route("/")
def index():
    """Главная страница Mini App с фильтрацией категорий и поиска."""
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
    """API подбора аксессуаров (чехлы, стёкла, плёнки) под конкретную модель."""
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
    """Обработка заказов, бронирований и подписок на уведомления."""
    data = request.json or {}
    order_type = data.get("type", "order")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # 1. Подписка на уведомление о наличии
    if order_type == "subscribe_notify":
        chat_id = data.get("chat_id")
        product_name = data.get("product_name")
        if chat_id and product_name:
            if product_name not in notification_subscriptions:
                notification_subscriptions[product_name] = []
            if chat_id not in notification_subscriptions[product_name]:
                notification_subscriptions[product_name].append(chat_id)
        return jsonify({"status": "ok"})

    # 2. Оформление заказа или брони
    if order_type in ["order", "booking"]:
        name = data.get("name", "")
        phone = data.get("phone", "")
        items = data.get("items", [])
        
        items_text = "\n".join([f"• {i['title']} — {i['price']} грн" for i in items])
        
        total = 0
        for i in items:
            p_val = str(i.get('price', '0')).replace('грн', '').strip()
            try:
                total += float(p_val)
            except ValueError:
                pass
        
        header = "📌 **НОВЕ БРОНЮВАННЯ (24 ГОД)**" if order_type == "booking" else "🛍️ **НОВЕ ЗАМОВЛЕННЯ**"
        msg = (
            f"{header}\n\n"
            f"👤 **Клієнт:** {name}\n"
            f"📞 **Телефон:** {phone}\n\n"
            f"📦 **Товари:**\n{items_text}\n\n"
            f"💰 **Разом:** {total} грн"
        )
        
        try:
            asyncio.run(bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown"))
        except Exception as e:
            logger.error(f"Error sending order notification to admin: {e}")
            
        return jsonify({"status": "ok"})

    return jsonify({"status": "error"}), 400

# --- TELEGRAM BOT HANDLERS ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    welcome_text = (
        "Вітаємо у нашому магазині гаджетів! 📱✨\n\n"
        "Натисніть кнопку нижче, щоб відкрити інтерактивну вітрину, "
        "переглянути наявність та оформити бронювання."
    )
    
    # Инициализация кнопки Mini App
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🛍️ Відкрити Магазин", web_app={"url": WEBAPP_URL})]
    ])
    
    await update.message.reply_text(welcome_text, reply_markup=kb)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    help_text = (
        "ℹ️ **Довідка магазину**\n\n"
        "• Для перегляду товарів скористайтеся Mini App через кнопку в меню.\n"
        "• Бронювання товарів є безкоштовним та триває 24 години.\n"
        "• З усіх питань звертайтеся до нашого менеджера."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def start_bot_app():
    """Инициализация и запуск приложения Telegram Бота."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация команд
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    
    # Сброс вебхуков перед поллингом для исключения конфликтов 409 Conflict
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

def run_async_loop():
    """Запуск события asyncio для Telegram Бота в отдельном потоке."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot_app())
    loop.run_forever()

if __name__ == "__main__":
    # 1. Запуск потока отслеживания остатков в Google Таблице
    threading.Thread(target=check_stock_changes, daemon=True).start()
    
    # 2. Запуск потока Telegram Бота
    threading.Thread(target=run_async_loop, daemon=True).start()
    
    # 3. Запуск основного веб-сервера Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
