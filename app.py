from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests

app = Flask(__name__)

# Замените на ваши данные
TELEGRAM_BOT_TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"
ADMIN_CHAT_ID = "396778432"

def get_products():
    csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vReZP-fGq9BOYihV2X2DZoUuX79f0mTMaFPVJwKxyOt-P7uUGyTGf-48NKBTRFtPj2j7UpLnbR5d3VY/pub?output=csv"
    try:
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Ошибка загрузки таблицы: {e}")
        return []

@app.route('/')
def index():
    products = get_products()
    selected_category = request.args.get('category')
    selected_brand = request.args.get('brand')
    search_query = request.args.get('search', '').strip().lower()
    
    filtered_products = []
    if selected_category:
        filtered_products = [p for p in products if str(p.get('Категория')).strip().lower() == selected_category.lower()]
        
        if selected_brand and selected_brand != 'all':
            filtered_products = [p for p in filtered_products if selected_brand.lower() in str(p.get('Название')).lower()]

        if search_query:
            filtered_products = [
                p for p in filtered_products 
                if search_query in str(p.get('Название', '')).lower() or search_query in str(p.get('Описание', '')).lower()
            ]

    return render_template('index.html', products=filtered_products, category=selected_category, brand=selected_brand, search=search_query)

@app.route('/order', methods=['POST'])
def create_order():
    data = request.json
    items = data.get('items', [])
    name = data.get('name')
    phone = data.get('phone')
    
    # Считаем общую сумму
    total_price = sum(float(str(i['price']).replace(' ', '')) for i in items)
    items_text = "\n".join([f"• {i['title']} — {i['price']} грн" for i in items])

    message = (
        f"🚨 **Новый заказ из корзины!**\n\n"
        f"🛒 Товары:\n{items_text}\n\n"
        f"💰 Итого: {total_price} грн\n\n"
        f"👤 Покупатель: {name}\n"
        f"📞 Телефон: {phone}"
    )

    if TELEGRAM_BOT_TOKEN != "ВАШ_ТОКЕН_БОТА":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
