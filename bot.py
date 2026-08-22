import telebot
from telebot import types

# 1. Вставьте токен вашего бота
TOKEN = "8762340517:AAHqxuOU0qfTs9qADk0IDCUyu2X2YI8LJAM"

# 2. Вставьте вашу ссылку на Flask-сайт (ngrok / pythonanywhere / ваш домен)
WEB_APP_URL = "https://https://gadget-shop-v5kh.onrender.com"

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    web_app = types.WebAppInfo(url=WEB_APP_URL)

    # Создаем нижнюю кнопку для любого нового пользователя
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton(
        text="📱 Відкрити каталог", web_app=web_app
    )
    keyboard.add(button)

    bot.send_message(
        message.chat.id,
        "Вітаємо! Натисніть кнопку нижче, щоб відкрити каталог товарів:",
        reply_markup=keyboard,
    )


if __name__ == "__main__":
    print("Бот успешно запущен и ждет новых пользователей!")
    bot.infinity_polling()
