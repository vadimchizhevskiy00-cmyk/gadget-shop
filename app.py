import io
import math
import sys
import traceback
import pandas as pd
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ==========================================
# ⚙️ НАСТРОЙКИ
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY"
TELEGRAM_CHAT_ID = "396778432"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"


def clean_val(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "-"
    val_str = str(val).strip()
    return val_str if val_str and val_str != "nan" else "-"


def get_products():
    if not CSV_URL or "http" not in CSV_URL:
        return []

    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            df = df.fillna("-")
            products = df.to_dict(orient="records")

            for p in products:
                mem_raw = clean_val(p.get("Память", "-"))
                price_raw = clean_val(p.get("Цена", "-"))

                if "/" in mem_raw:
                    p["memory_list"] = [m.strip() for m in mem_raw.split("/") if m.strip()]
                else:
                    p["memory_list"] = [mem_raw] if mem_raw not in ["-", "nan"] else []

                if "/" in price_raw:
                    p["price_list"] = [pr.strip() for pr in price_raw.split("/") if pr.strip()]
                else:
                    p["price_list"] = [price_raw] if price_raw not in ["-", "nan"] else ["0"]

            return products
        else:
            return []
    except Exception as e:
        print(f"Ошибка при обработке CSV:\n{traceback.format_exc()}", file=sys.stderr)
        return []


@app.route("/")
def index():
    try:
        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip().lower()

        products = get_products()
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
        print(f"CRITICAL ERROR IN INDEX ROUTE:\n{traceback.format_exc()}", file=sys.stderr)
        return f"<h3>Произошла ошибка при загрузке каталога:</h3><pre>{e}</pre>", 500


@app.route("/api/accessories")
def get_accessories():
    try:
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
            cat = clean_val(p.get("Категория", "")).lower()
            title = clean_val(p.get("Название", "")).lower()
            compat = clean_val(p.get("Совместимость", "")).lower()

            if (model_query in title) or (model_query in compat):
                if cat in glass_categories:
                    has_glass = True

                if cat in (glass_categories + case_categories + film_categories):
                    clean_p = {k: clean_val(v) for k, v in p.items()}
                    if clean_p not in matched:
                        matched.append(clean_p)

        if not has_glass:
            for p in products:
                cat = clean_val(p.get("Категория", "")).lower()
                if cat in film_categories:
                    clean_p = {k: clean_val(v) for k, v in p.items()}
                    if clean_p not in matched:
                        matched.append(clean_p)

        return jsonify(matched)
    except Exception as e:
        print(f"ERROR IN ACCESSORIES API:\n{traceback.format_exc()}", file=sys.stderr)
        return jsonify([])


@app.route("/order", methods=["POST"])
def send_order():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400

        name = data.get("name", "Не указано")
        phone = data.get("phone", "Не указан")
        items = data.get("items", [])
        is_booking = data.get("is_booking", False)

        if not items:
            return jsonify({"status": "error", "message": "Cart is empty"}), 400

        total_price = sum(float(i.get("price", 0)) for i in items)

        items_text = ""
        for idx, item in enumerate(items, 1):
            items_text += f"{idx}. {item.get('title')} — {item.get('price')} грн\n"

        header_title = "📌 <b>НОВАЯ БРОНЬ В МАГАЗИНЕ (24Ч)</b>" if is_booking else "🛍️ <b>Новый заказ!</b>"

        message = (
            f"{header_title}\n\n"
            f"👤 <b>Имя:</b> {name}\n"
            f"📞 <b>Телефон:</b> {phone}\n\n"
            f"📋 <b>Товары:</b>\n{items_text}\n"
            f"💰 <b>К оплате в магазине:</b> {total_price} грн"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        requests.post(url, json=payload, timeout=10)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"ERROR IN ORDER ROUTE:\n{traceback.format_exc()}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
