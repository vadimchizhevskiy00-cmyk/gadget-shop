import io
import math
import pandas as pd
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Замените на ваши данные Telegram
TELEGRAM_BOT_TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"
TELEGRAM_CHAT_ID = "396778432"

# Ссылка на вашу опубликованную CSV-таблицу Google Sheets
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"


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


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip().lower()

    products = get_products()
    filtered_products = []

    for p in products:
        # Фильтрация по категории
        p_cat = str(p.get("Категория", "")).strip().lower()
        if category and category.lower() != "all":
            if p_cat != category.lower():
                continue

        # Фильтрация по поисковому запросу
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

    # Разделяем категории по типам
    glass_categories = ["стекла", "захисні стекла"]
    case_categories = ["чехлы", "чохлы"]
    film_categories = ["пленки", "плівки"]

    has_glass = False

    # 1. Ищем чехлы и стекла для конкретной модели
    for p in products:
        cat = str(p.get("Категория", "")).strip().lower()
        title = str(p.get("Название", "")).strip().lower()

        if model_query in title:
            if cat in glass_categories:
                has_glass = True

            if cat in (glass_categories + case_categories + film_categories):
                matched.append({k: clean_val(v) for k, v in p.items()})

    # 2. Если стекла для данной модели НЕТ — подтягиваем варианты пленок
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
        print(f"Ошибка при отправке в Telegram: {e}")

    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
