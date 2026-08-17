from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

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
    
    filtered_products = []
    if selected_category:
        # Сравниваем точь-в-точь с вашей категорией из таблицы
        filtered_products = [p for p in products if str(p.get('Категория')).strip().lower() == selected_category.lower()]
        
        if selected_brand and selected_brand != 'all':
            filtered_products = [p for p in filtered_products if selected_brand.lower() in str(p.get('Название')).lower()]

    return render_template('index.html', products=filtered_products, category=selected_category, brand=selected_brand)

if __name__ == '__main__':
    app.run(debug=True, port=5000)