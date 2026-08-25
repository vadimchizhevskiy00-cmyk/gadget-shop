import sys
import telebot
from telebot import types

# ==========================================
# ⚙️ НАЛАШТУВАННЯ МАГАЗИНУ
# ==========================================
TELEGRAM_BOT_TOKEN = "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY"
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"

# Контакты и адрес вашего физического магазина
SHOP_ADDRESS = "м. Чугуїв, бул. Центральний, 8"  # Укажите ваш адрес
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

        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
            types.KeyboardButton(text="🧭 Майстер підбору"),
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
        print(f"Помилка в /start: {e}", file=sys.stderr)


# ==========================================
# ❓ РОЗДІЛ FAQ (ЧАСТІ ЗАПИТАННЯ)
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "❓ Часті запитання (FAQ)")
def send_faq_menu(message):
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Чи є гарантія на техніку?", callback_data="faq_warranty"))
        kb.add(types.InlineKeyboardButton("📌 Як працює бронювання?", callback_data="faq_booking"))
        kb.add(types.InlineKeyboardButton("📲 Чи допомагаєте перенести дані?", callback_data="faq_transfer"))
        kb.add(types.InlineKeyboardButton("✨ Поклейка скла / плівок", callback_data="faq_service"))
        kb.add(types.InlineKeyboardButton("💬 Поставити запитання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

        faq_text = (
            "❓ <b>Відповіді на часті запитання</b>\n\n"
            "Оберіть запитання, яке вас цікавить:"
        )

        bot.send_message(message.chat.id, faq_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(f"Помилка FAQ: {e}", file=sys.stderr)


# ==========================================
# 📍 ІНТЕРАКТИВНА КАРТА ТА КОНТАКТИ
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин та контакти")
def send_contacts(message):
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗺️ Прокласти маршрут (Google Maps)", url=GOOGLE_MAPS_LINK))
        kb.add(types.InlineKeyboardButton("💬 Написати менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

        contact_text = (
            f"🏢 <b>Наш магазин гаджетів та аксесуарів</b>\n\n"
            f"📍 <b>Адреса:</b> {SHOP_ADDRESS}\n"
            f"⏰ <b>Час роботи:</b> {SHOP_HOURS}\n"
            f"📞 <b>Телефон:</b> {SHOP_PHONE}\n\n"
            f"💡 <i>Ви можете приїхати, подивитися, приміряти чохол або поклеїти скло прямо у нас!</i>"
        )

        bot.send_message(message.chat.id, contact_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(f"Помилка контактів: {e}", file=sys.stderr)


# ==========================================
# 🧭 МАЙСТЕР ПІДБОРУ ТА ОБРОБКА CALLBACK
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "🧭 Майстер підбору")
def start_quiz(message):
    user_quiz_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📱 Обрати новий телефон", callback_data="goal_phone"))
    kb.add(types.InlineKeyboardButton("🛡️ Аксесуар (чохол / скло / плівка)", callback_data="goal_acc"))

    bot.send_message(message.chat.id, "<b>Крок 1:</b> Що ви шукаєте сьогодні?", parse_mode="HTML", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    bot.answer_callback_query(call.id)
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.id

    if data.startswith("faq_"):
        faq_answers = {
            "warranty": (
                "🛡️ <b>Гарантія на техніку</b>\n\n"
                "На всю нову техніку надається офіційна гарантія від 12 місяців.\n"
                "На б/в техніку перед продажем проводиться повна діагностика за 25 пунктами та надається наша гарантія від магазину."
            ),
            "booking": (
                "📌 <b>Як працює бронь на 24 години?</b>\n\n"
                "Ви оформлюєте товар у Mini App та обираєте пункт «Забронювати в магазині».\n"
                "Ми резервуємо позицію на складі на 24 години. Ви спокійно приїжджаєте, оглядаєте товар та сплачуєте на місці!"
            ),
            "transfer": (
                "📲 <b>Перенесення даних</b>\n\n"
                "Так! При покупці смартфона у нас в магазині наші фахівці безкоштовно або за мінімальною вартістю допоможуть перенести всі контакти, фото та додатки зі старого пристрою на новий."
            ),
            "service": (
                "✨ <b>Поклейка захисного скла та плівок</b>\n\n"
                "Вам не потрібно клеїти скло самостійно! Наші майстри зроблять ідеальну поклейку без пилу та бульбашок прямо при вас у магазині."
            ),
        }

        topic = data.split("_")[1]
        ans_text = faq_answers.get(topic, "Інформація уточнюється...")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад до запитань", callback_data="faq_back"))
        kb.add(types.InlineKeyboardButton("💬 Поставити своє запитання", url=f"https://t.me/{MANAGER_USERNAME}"))

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=ans_text, parse_mode="HTML", reply_markup=kb)

    elif data == "faq_back":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Чи є гарантія на техніку?", callback_data="faq_warranty"))
        kb.add(types.InlineKeyboardButton("📌 Як працює бронювання?", callback_data="faq_booking"))
        kb.add(types.InlineKeyboardButton("📲 Чи допомагаєте перенести дані?", callback_data="faq_transfer"))
        kb.add(types.InlineKeyboardButton("✨ Поклейка скла / плівок", callback_data="faq_service"))
        kb.add(types.InlineKeyboardButton("💬 Поставити запитання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❓ <b>Відповіді на часті запитання</b>\n\nОберіть запитання, яке вас цікавить:", parse_mode="HTML", reply_markup=kb)

    elif data == "goal_phone":
        user_quiz_data[chat_id] = {"goal": "phone"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("📸 Крута камера", callback_data="pfeature_camera"),
            types.InlineKeyboardButton("🔋 Довга батарея", callback_data="pfeature_battery"),
        )
        kb.add(
            types.InlineKeyboardButton("🎮 Ігри та швидкість", callback_data="pfeature_power"),
            types.InlineKeyboardButton("⚖️ Баланс ціна/якість", callback_data="pfeature_balance"),
        )
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 2:</b> Що для вас найважливіше у смартфоні?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("pfeature_"):
        feature = data.split("_")[1]
        advice = "Рекомендуємо смартфони з потужним процесором та яскравим екраном."
        if feature == "camera":
            advice = "Рекомендуємо флагмани з просунутою оптикою та стабілізацією."
        elif feature == "battery":
            advice = "Рекомендуємо моделі з акумулятором від 5000 мАг та швидкою зарядкою."
        elif feature == "balance":
            advice = "Рекомендуємо популярні середньобюджетні хіти продажів."

        final_url = f"{WEB_APP_URL}/?category=телефоны"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="📱 Переглянути відповідні телефони", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ <b>Підбір телефона завершено!</b>\n\n💡 <i>{advice}</i>\n\nПерейдіть до каталогу:", parse_mode="HTML", reply_markup=kb)

    elif data == "goal_acc":
        user_quiz_data[chat_id] = {"goal": "acc"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🍏 Apple (iPhone)", callback_data="brand_apple"),
            types.InlineKeyboardButton("📱 Samsung", callback_data="brand_samsung"),
        )
        kb.add(
            types.InlineKeyboardButton("⚡ Xiaomi / Poco", callback_data="brand_xiaomi"),
            types.InlineKeyboardButton("🌐 Інший бренд", callback_data="brand_other"),
        )
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 2:</b> Вкажіть бренд вашого пристрою:", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("brand_"):
        brand = data.split("_")[1]
        user_quiz_data[chat_id] = user_quiz_data.get(chat_id, {})
        user_quiz_data[chat_id]["brand"] = brand
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🛡️ Чохол", callback_data="type_Чехлы"),
            types.InlineKeyboardButton("✨ Захисне скло", callback_data="type_Стекла"),
        )
        kb.add(types.InlineKeyboardButton("📜 Гідрогелева плівка", callback_data="type_Пленки"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Крок 3:</b> Що саме ви шукаєте?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("type_"):
        p_type = data.split("_")[1]
        user_data = user_quiz_data.get(chat_id, {})
        brand = user_data.get("brand", "all")
        search_term = "iphone" if brand == "apple" else ("samsung" if brand == "samsung" else "xiaomi")

        final_url = f"{WEB_APP_URL}/?category={p_type}&search={search_term}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="🎯 Переглянути варіанти", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ <b>Підбір завершено!</b> Натисніть кнопку нижче, щоб відкрити каталог:", parse_mode="HTML", reply_markup=kb)


if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception:
        pass

    print("Бот українською мовою успішно запущений...")
    bot.infinity_polling(skip_pending=True)
