import telebot
from telebot import types

# 1. Токен вашего бота
TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"

# 2. Актуальная ссылка на ваш магазин
WEB_APP_URL = "https://gadget-shop-v5kh.onrender.com"

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    web_app = types.WebAppInfo(url=WEB_APP_URL)

    # 1. Создаем встроенную (Inline) кнопку прямо ПОД сообщением
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_button = types.InlineKeyboardButton(
        text="🛍️ Відкрити каталог", web_app=web_app
    )
    inline_keyboard.add(inline_button)

    # 2. Создаем постоянную нижнюю кнопку внизу экрана (Reply Keyboard)
    reply_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reply_button = types.KeyboardButton(
        text="📱 Відкрити каталог", web_app=web_app
    )
    reply_keyboard.add(reply_button)

    # Приветственный текст
    welcome_text = (
        f"Вітаємо, {message.from_user.first_name}! 👋\n\n"
        f"Ласкаво просимо до нашого магазину гаджетів та аксесуарів.\n"
        f"Натисніть кнопку нижче, щоб переглянути каталог та зробити замовлення 👇"
    )

    # Отправляем сообщение: сразу и с кнопкой в тексте, и с постоянной кнопкой снизу
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=inline_keyboard,  # Инлайн-кнопка в сообщении
    )

    # Отдельно закрепляем нижнюю постоянную кнопку
    bot.send_message(
        message.chat.id,
        "Каталог завжди доступний за кнопкою знизу ⬇️",
        reply_markup=reply_keyboard,
    )


if __name__ == "__main__":
    print("Бот успешно запущен!")
    bot.infinity_polling()
