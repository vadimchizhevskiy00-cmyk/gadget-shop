import sys
import telebot
from telebot import types

# ==========================================
# ⚙️ НАСТРОЙКИ МАГАЗИНА
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY"
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"

# Контакты и адрес вашего физического магазина
SHOP_ADDRESS = "м.Чугуїв, бул.Центральний, 8"  # Укажите ваш адрес
SHOP_HOURS = "Пн-Пт: 08:00 — 18:00 | Сб-Нд: 08:00 — 17:00"
SHOP_PHONE = "+380 97 391 64 00, +380 63 189 16 83"  # Укажите ваш телефон
MANAGER_USERNAME = "smthwrng121"  # Telegram юзернейм менеджера без @
GOOGLE_MAPS_LINK = "https://maps.app.goo.gl/RukWZ1QBZbQQsqnA9"  # Ссылка на вашу точку на Google Maps


bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_quiz_data = {}


@bot.message_handler(commands=["start"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)

        # Главная нижняя клавиатура
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
            types.KeyboardButton(text="🧭 Мастер подбора"),
        )
        reply_kb.add(
            types.KeyboardButton(text="📍 Магазин и контакты"),
        )

        welcome_text = (
            f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
            f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n\n"
            f"Шукаєте новий телефон, потрібен аксесуар або хочете завітати до нас в гості? "
            f"Скористайтесь меню нижче! 👇"
        )

        bot.send_message(message.chat.id, welcome_text, reply_markup=reply_kb)
    except Exception as e:
        print(f"Ошибка в /start: {e}", file=sys.stderr)


# ==========================================
# 📍 ИНТЕРАКТИВНАЯ КАРТА И КОНТАКТЫ
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин и контакты")
def send_contacts(message):
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "🗺️ Проложить маршрут (Google Maps)", url=GOOGLE_MAPS_LINK
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "💬 Написать менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"
            )
        )

        contact_text = (
            f"🏢 <b>Наш магазин гаджетов и аксессуаров</b>\n\n"
            f"📍 <b>Адрес:</b> {SHOP_ADDRESS}\n"
            f"⏰ <b>Время работы:</b> {SHOP_HOURS}\n"
            f"📞 <b>Телефон:</b> {SHOP_PHONE}\n\n"
            f"💡 <i>Вы можете приехать, посмотреть, примерить чехол или поклеить стекло прямо у нас в магазине!</i>\n\n"
            f"Нажмите кнопку ниже, чтобы открыть навигатор:"
        )

        bot.send_message(
            message.chat.id,
            contact_text,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        print(f"Ошибка при отправке контактов: {e}", file=sys.stderr)


# ==========================================
# 🧭 МАСТЕР ПОДБОРА (КВИЗ)
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "🧭 Мастер подбора")
def start_quiz(message):
    user_quiz_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📱 Выбрать новый телефон", callback_data="goal_phone"),
    )
    kb.add(
        types.InlineKeyboardButton("🛡️ Аксессуар (чехол / стекло / пленка)", callback_data="goal_acc"),
    )

    bot.send_message(
        message.chat.id,
        "<b>Шаг 1:</b> Что вы ищете сегодня?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    bot.answer_callback_query(call.id)

    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.id

    if data == "goal_phone":
        user_quiz_data[chat_id] = {"goal": "phone"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("📸 Крутая камера", callback_data="pfeature_camera"),
            types.InlineKeyboardButton("🔋 Долгая батарея", callback_data="pfeature_battery"),
        )
        kb.add(
            types.InlineKeyboardButton("🎮 Игры и скорость", callback_data="pfeature_power"),
            types.InlineKeyboardButton("⚖️ Баланс цена/качество", callback_data="pfeature_balance"),
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>Шаг 2:</b> Что для вас самое главное в смартфоне?",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("pfeature_"):
        feature = data.split("_")[1]
        advice = "Рекомендуем смартфоны с мощным процессором и ярким экраном."
        if feature == "camera":
            advice = "Рекомендуем флагманы с продвинутой оптикой и стабилизацией."
        elif feature == "battery":
            advice = "Рекомендуем модели с аккумулятором от 5000 мАч и быстрой зарядкой."
        elif feature == "balance":
            advice = "Рекомендуем популярные среднебюджетные хиты продаж."

        final_url = f"{WEB_APP_URL}/?category=телефоны"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                text="📱 Посмотреть подходящие телефоны",
                web_app=types.WebAppInfo(url=final_url),
            )
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"✅ <b>Подбор телефона завершен!</b>\n\n💡 <i>{advice}</i>\n\nПерейдите в каталог:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data == "goal_acc":
        user_quiz_data[chat_id] = {"goal": "acc"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🍏 Apple (iPhone)", callback_data="brand_apple"),
            types.InlineKeyboardButton("📱 Samsung", callback_data="brand_samsung"),
        )
        kb.add(
            types.InlineKeyboardButton("⚡ Xiaomi / Poco", callback_data="brand_xiaomi"),
            types.InlineKeyboardButton("🌐 Другой бренд", callback_data="brand_other"),
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>Шаг 2:</b> Укажите бренд вашего устройства:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("brand_"):
        brand = data.split("_")[1]
        user_quiz_data[chat_id] = user_quiz_data.get(chat_id, {})
        user_quiz_data[chat_id]["brand"] = brand
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🛡️ Чехол", callback_data="type_Чехлы"),
            types.InlineKeyboardButton("✨ Защитное стекло", callback_data="type_Стекла"),
        )
        kb.add(
            types.InlineKeyboardButton("📜 Гидрогелевая пленка", callback_data="type_Пленки")
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>Шаг 3:</b> Что именно вы ищете?",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("type_"):
        p_type = data.split("_")[1]
        user_data = user_quiz_data.get(chat_id, {})
        brand = user_data.get("brand", "all")
        search_term = (
            "iphone"
            if brand == "apple"
            else ("samsung" if brand == "samsung" else "xiaomi")
        )

        final_url = f"{WEB_APP_URL}/?category={p_type}&search={search_term}"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                text="🎯 Посмотреть варианты",
                web_app=types.WebAppInfo(url=final_url),
            )
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="✅ <b>Подбор завершен!</b> Нажмите кнопку ниже, чтобы открыть каталог:",
            parse_mode="HTML",
            reply_markup=kb,
        )


if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception:
        pass

    print("Бот с интерактивными контактами запущен...")
    bot.infinity_polling(skip_pending=True)
