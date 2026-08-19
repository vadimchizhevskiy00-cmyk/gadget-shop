import os
from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

app = Flask(__name__)

# Настройка подключения к Google Таблицам
# (Убедитесь, что ваш файл с ключом json подключен корректно, либо используются переменные окружения)
scope = ["https://spreadsheets.google.com/feeds", "https://www.auth.com/auth/drive"]

def get_sheet():
    # Пример инициализации (подставьте свой путь к json или настройки Render)
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ])
    client = gspread.authorize(creds)
    # Название вашей таблицы в Google
    sheet = client.open("GadgetStoreDB").sheet1 
    return sheet

@app.route('/')
def index():
    category = request.args.get('category')
    search_query = request.args.get('search', '').lower()
    
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
    except Exception as e:
        print(f"Ошибка подключения к таблице: {e}")
        records = []

    products = []
    if category:
        for r in records:
            # Проверка соответствия категории
            if str(r.get('Категория', '')).strip().lower() == category.strip().lower():
                # Фильтрация по поиску, если он введен
                title = str(r.get('Название', '')).lower()
                desc = str(r.get('Описание', '')).lower()
                if not search_query or search_query in title or search_query in desc:
                    products.append(r)

    return render_template('index.html', products=products, category=category, search=search_query)

@app.route('/order', methods=['POST'])
def order():
    data = request.json
    items = data.get('items', [])
    name = data.get('name')
    phone = data.get('phone')
    
    # Формируем текст заказа для отправки в Telegram (опционально владельцу магазина)
    order_text = f"🚨 **Новый заказ!**\n👤 Имя: {name}\n📞 Телефон: {phone}\n\n🛒 **Товары:**\n"
    total_sum = 0
    
    for item in items:
        order_text += f"- {item['title']} — {item['price']} грн\n"
        try:
            total_sum += float(item['price'])
        except:
            pass
            
    order_text += f"\n💰 **Итого:** {total_sum} грн"

    # Отправка уведомления в Telegram (требуется токен бота и ваш chat_id)
    bot_token = os.environ.get("BOT_TOKEN")
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID")
    
    if bot_token and admin_chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={
            "chat_id": admin_chat_id,
            "text": order_text,
            "parse_mode": "Markdown"
        })

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
