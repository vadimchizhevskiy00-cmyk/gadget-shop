import io
import math
import pandas as pd
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"
TELEGRAM_CHAT_ID = "396778432"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"


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

            for p in products:
                mem_raw = str(p.get("Память", "-")).strip()
                price_raw = str(p.get("Цена", "-")).strip()

                # Безопасный разбор памяти
                if "/" in mem_raw:
                    p["memory_list"] = [m.strip() for m in mem_raw.split("/") if m.strip()]
                else:
                    p["memory_list"] = [mem_raw] if mem_raw not in ["-", "nan"] else []

                # Безопасный разбор цен (гарантирует хотя бы 1 элемент в списке)
                if "/" in price_raw:
                    p["price_list"] = [pr.strip() for pr in price_raw.split("/") if pr.strip()]
                else:
                    p["price_list"] = [price_raw] if price_raw not in ["-", "nan"] else ["0"]

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
