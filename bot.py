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

        # Главное меню с добавленной кнопкой FAQ
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app),
            types.KeyboardButton(text="🧭 Майстер з підбору"),
        )
        reply_kb.add(
            types.KeyboardButton(text="📍 Магазин та контакти"),
            types.KeyboardButton(text="❓ Часті питання (FAQ)"),
        )

        welcome_text = (
            f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
            f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n\n"
            f"Обирайте потрібный раздел в меню ниже! 👇"
        )

        bot.send_message(message.chat.id, welcome_text, reply_markup=reply_kb)
    except Exception as e:
        print(f"Ошибка в /start: {e}", file=sys.stderr)


# ==========================================
# ❓ РАЗДЕЛ FAQ (ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ)
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "❓ Частые вопросы (FAQ)")
def send_faq_menu(message):
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Яка гарантія на техніку?", callback_data="faq_warranty"))
        kb.add(types.InlineKeyboardButton("📌 Що таке бронювання товару?", callback_data="faq_booking"))
        kb.add(types.InlineKeyboardButton("📲 Перенесення даних", callback_data="faq_transfer"))
        kb.add(types.InlineKeyboardButton("✨ Встановлення захисту на дисплей", callback_data="faq_service"))
        kb.add(types.InlineKeyboardButton("💬 Задати питання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

        faq_text = (
            "❓ <b>Відповіді на питання</b>\n\n"
            "Выберите интересующий вас вопрос ниже:"
        )

        bot.send_message(message.chat.id, faq_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(f"Ошибка FAQ: {e}", file=sys.stderr)


# ==========================================
# 📍 ИНТЕРАКТИВНАЯ КАРТА И КОНТАКТЫ
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин и контакты")
def send_contacts(message):
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗺️ Де нас знайти (Google Maps)", url=GOOGLE_MAPS_LINK))
        kb.add(types.InlineKeyboardButton("💬 Зв'язок з менеджером", url=f"https://t.me/{MANAGER_USERNAME}"))

        contact_text = (
            f"🏢 <b>Вітаємо у Lifecell!</b>\n\n"
            f"📍 <b>Адреса:</b> {SHOP_ADDRESS}\n"
            f"⏰ <b>Час роботи:</b> {SHOP_HOURS}\n"
            f"📞 <b>Телефон:</b> {SHOP_PHONE}\n\n"
            f"💡 <i>Ви зможете прийти, подивитися техніку, придбати аксесуари та поклеїти захист саме в нас!</i>"
        )

        bot.send_message(message.chat.id, contact_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(f"Ошибка контактов: {e}", file=sys.stderr)


# ==========================================
# 🧭 МАСТЕР ПОДБОРА И ОБРАБОТКА CALLBACK
# ==========================================
@bot.message_handler(func=lambda msg: msg.text == "🧭 Майстер з підбору")
def start_quiz(message):
    user_quiz_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📱Обрати новий телефон", callback_data="goal_phone"))
    kb.add(types.InlineKeyboardButton("🛡️ Аксесуар (чохол / скло / плівка)", callback_data="goal_acc"))

    bot.send_message(message.chat.id, "<b>Шаг 1:</b> Що ви шукаєте сьогодні?", parse_mode="HTML", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    bot.answer_callback_query(call.id)
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.id

    # ---------------- ОБРАБОТКА FAQ ----------------
    if data.startswith("faq_"):
        faq_answers = {
            "warranty": (
                "🛡️ <b>Гарантія на техніку</b>\n\n"
                "Вся нова техніка має гарантію 12 місяців з моменту придбання.\n"
                "Гарантія магазину на б/у техніку складає 2 тижні."
            ),
            "booking": (
                "📌 <b>Як працює бронювання товару на 24 години?</b>\n\n"
                "При оформленні товару ви можете натиснути кнопку "Забронювати на 24 години".\n"
                "Ми резервуємо пристрій в магазині та чекаємо вашого візиту."
            ),
            "transfer": (
                "📲 <b>Перенос данных</b>\n\n"
                "Так! При покупці пристрою продавці аналізуют обсяг інформації, яку треба перенести, визначают приблизний час та вартість робіт."
            ),
            "service": (
                "✨ <b>Встановлення захисного скла та плівок</b>\n\n"
                "Магазин пропонує великий спектр захисту для вашого пристрою. Якщо в нас нема скла на ваш телефон - не переймайтесь, гідрогелева плівка завжди в наявності!"
            ),
        }

        topic = data.split("_")[1]
        ans_text = faq_answers.get(topic, "Зачекайте хвилинку...")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад до питань", callback_data="faq_back"))
        kb.add(types.InlineKeyboardButton("💬 Задати своє питання", url=f"https://t.me/{MANAGER_USERNAME}"))

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=ans_text, parse_mode="HTML", reply_markup=kb)

    elif data == "faq_back":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛡️ Яка гарантія на техніку?", callback_data="faq_warranty"))
        kb.add(types.InlineKeyboardButton("📌 Що таке бронювання товару?", callback_data="faq_booking"))
        kb.add(types.InlineKeyboardButton("📲 Перенесення даних?", callback_data="faq_transfer"))
        kb.add(types.InlineKeyboardButton("✨ Встановлення захисту на дисплей", callback_data="faq_service"))
        kb.add(types.InlineKeyboardButton("💬 Задати питання менеджеру", url=f"https://t.me/{MANAGER_USERNAME}"))

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❓ <b>Відповіді на питання</b>\n\nОберіть питання нижче:", parse_mode="HTML", reply_markup=kb)

    # ---------------- ВЕТКА МАСТЕРА ПОДБОРА ----------------
    elif data == "goal_phone":
        user_quiz_data[chat_id] = {"goal": "phone"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("📸 Краща камера", callback_data="pfeature_camera"),
            types.InlineKeyboardButton("🔋 Автономна батарея", callback_data="pfeature_battery"),
        )
        kb.add(
            types.InlineKeyboardButton("🎮 Швидкість та плавність", callback_data="pfeature_power"),
            types.InlineKeyboardButton("⚖️ Баланс ціна/якість", callback_data="pfeature_balance"),
        )
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Шаг 2:</b> Що для вас головне в смартфоні?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("pfeature_"):
        feature = data.split("_")[1]
        advice = "Рекомендуємо смартфони з потужним процесором та яскравим екраном."
        if feature == "camera":
            advice = "Рекомендуем флагманы с продвинутой оптикой и стабилизацией."
        elif feature == "battery":
            advice = "Рекомендуємо моделі с батареєю від 5000 мАг та швидкою зарядкою."
        elif feature == "balance":
            advice = "Рекомендуємо популярні середньобюджетні телефони."

        final_url = f"{WEB_APP_URL}/?category=телефоны"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="📱 Подивитися варіанти", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ <b>Підбір телефонів завершений!</b>\n\n💡 <i>{advice}</i>\n\nПерейдіть до каталогу:", parse_mode="HTML", reply_markup=kb)

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
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Шаг 2:</b> Вкажіть бренд вашого пристрою:", parse_mode="HTML", reply_markup=kb)

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
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="<b>Шаг 3:</b> Що саме ви шукаєте?", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("type_"):
        p_type = data.split("_")[1]
        user_data = user_quiz_data.get(chat_id, {})
        brand = user_data.get("brand", "all")
        search_term = "iphone" if brand == "apple" else ("samsung" if brand == "samsung" else "xiaomi")

        final_url = f"{WEB_APP_URL}/?category={p_type}&search={search_term}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="🎯 Подивитися варіанти", web_app=types.WebAppInfo(url=final_url)))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ <b>Підбір завершений!</b> Натисніть на кнопку нижче, щоб подивитися каталог:", parse_mode="HTML", reply_markup=kb)


if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception:
        pass

    print("Бот с модулем FAQ запущен...")
    bot.infinity_polling(skip_pending=True)
