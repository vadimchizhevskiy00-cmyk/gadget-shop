import os
import sys
import telebot
from telebot import types

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8762340517:AAEcvIHkqCdLduHJj-4cyVEgN2ohQN3VeuY")
WEB_APP_URL = os.environ.get(
    "WEB_APP_URL", "https://gadget-shop-v5kh.onrender.com"
)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")


# === КОМАНДА /START ===
@bot.message_handler(commands=["start"])
def start_cmd(message):
    try:
        web_app = types.WebAppInfo(url=WEB_APP_URL)

        # Клавиатура строго из 3 кнопок
        reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        reply_kb.add(
            types.KeyboardButton(text="📱 Відкрити каталог", web_app=web_app)
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
        print(f"Помилка /start: {e}", file=sys.stderr)


# === КНОПКА КОНТАКТЫ ===
@bot.message_handler(func=lambda msg: msg.text == "📍 Магазин та контакти")
def contacts_cmd(message):
    text = (
        "📍 <b>Наш магазин чекає на вас!</b>\n\n"
        "🏢 <b>Адреса:</b> м. Чугуїв, бул. Центральний, 8\n"
        "⏰ <b>Графік роботи:</b> Пн-Пт: 08:00 — 18:00 | Сб-Нд: 08:00 — 17:00\n"
        "📞 <b>Телефон:</b> +380 97 391 64 00, +380 63 189 16 83\n"
        "💬 <b>Менеджер:</b> @smthwrng121"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# === КНОПКА FAQ (без слова "безкоштовно") ===
@bot.message_handler(func=lambda msg: msg.text == "❓ Часті запитання (FAQ)")
def faq_cmd(message):
    text = (
        "❓ <b>Часті запитання:</b>\n\n"
        "1️⃣ <b>Чи є гарантія на техніку?</b>\n"
        "— Так! На нову техніку діє гарантія 12 місяців, на б/в — від 3 місяців.\n\n"
        "2️⃣ <b>Як працює бронювання?</b>\n"
        "— Ви обираєте товар у веб-каталозі, тиснете «Забронювати», і ми відкладаємо його для вас на 24 години.\n\n"
        "3️⃣ <b>Чи допомагаєте з налаштуванням та переносом даних?</b>\n"
        "— Так, наші спеціалісти допоможуть перенести всі ваші контакти, фото та додатки на новий пристрій при покупці у магазині."
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


if __name__ == "__main__":
    print("Бот успішно запущений...")
    bot.infinity_polling(skip_pending=True)
