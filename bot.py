import sys
import telebot
from telebot import types

# ⚠️ ВСТАВЬТЕ СЮДА НОВЫЙ ТОКЕН И ССЫЛКУ!
TELEGRAM_BOT_TOKEN = "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY"
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_quiz_data = {}

print("Инициализация бота...", flush=True)


@bot.message_handler(commands=["start"])
def start_cmd(message):
    print(
        f"Получена команда /start от {message.from_user.username}", flush=True
    )
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)

        # Нижняя клавиатура
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(
                text="📱 Відкрити каталог", web_app=web_app
            ),
            types.KeyboardButton(text="🧭 Мастер подбора"),
        )

        welcome_text = (
            f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
            f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n\n"
            f"Шукаєте новий телефон або потрібен аксесуар? "
            f"Натисніть «🧭 Мастер подбора» и ми підберемо кращий варіант! 👇"
        )

        bot.send_message(
            message.chat.id, welcome_text, reply_markup=reply_kb
        )
    except Exception as e:
        print(f"Ошибка в /start: {e}", file=sys.stderr, flush=True)


@bot.message_handler(func=lambda msg: msg.text == "🧭 Мастер подбора")
def start_quiz(message):
    print("Нажата кнопка Мастер подбора", flush=True)
    user_quiz_data[message.chat.id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📱 Выбрать новый телефон", callback_data="goal_phone"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🛡️ Аксессуар (чехол / стекло / пленка)", callback_data="goal_acc"
        )
    )

    bot.send_message(
        message.chat.id,
        "<b>Шаг 1:</b> Что вы ищете сегодня?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    print(f"Клик по инлайн-кнопке: {call.data}", flush=True)
    bot.answer_callback_query(call.id)

    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.id

    if data == "goal_phone":
        user_quiz_data[chat_id] = {"goal": "phone"}
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "📸 Крутая камера", callback_data="pfeature_camera"
            ),
            types.InlineKeyboardButton(
                "🔋 Долгая батарея", callback_data="pfeature_battery"
            ),
        )
        kb.add(
            types.InlineKeyboardButton(
                "🎮 Игры и скорость", callback_data="pfeature_power"
            ),
            types.InlineKeyboardButton(
                "⚖️ Баланс цена/качество", callback_data="pfeature_balance"
            ),
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
            advice = (
                "Рекомендуем флагманы с продвинутой оптикой и стабилизацией."
            )
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
            types.InlineKeyboardButton(
                "🍏 Apple (iPhone)", callback_data="brand_apple"
            ),
            types.InlineKeyboardButton(
                "📱 Samsung", callback_data="brand_samsung"
            ),
        )
        kb.add(
            types.InlineKeyboardButton(
                "⚡ Xiaomi / Poco", callback_data="brand_xiaomi"
            ),
            types.InlineKeyboardButton(
                "🌐 Другой бренд", callback_data="brand_other"
            ),
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
            types.InlineKeyboardButton(
                "🛡️ Чехол", callback_data="type_Чехлы"
            ),
            types.InlineKeyboardButton(
                "✨ Защитное стекло", callback_data="type_Стекла"
            ),
        )
        kb.add(
            types.InlineKeyboardButton(
                "📜 Гидрогелевая пленка", callback_data="type_Пленки"
            )
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
    print("Удаляем старый вебхук...")
    try:
        # Безопасный сброс вебхука без конфликтующих аргументов
        bot.remove_webhook()
    except Exception as e:
        print(f"Предупреждение webhook: {e}")

    print("Запускаем бота...")
    # skip_pending=True автоматически сбросит все старые накопленные сообщения
    bot.infinity_polling(skip_pending=True)
