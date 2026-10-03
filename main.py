import telebot


TOKEN = '8856407895:AAGkQulOmWlMkAD4KDivUFGB6Kv1jzpWPlM'
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        show_profile(message)
    else:
        bot.send_message(
            message.chat.id,
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот для организации корпоративных сборов и поздравлений.\n"
            "Давай заполним твою анкету. Это займёт минуту.\n\n"
            "Укажи свой **пол**:",
            parse_mode='Markdown',
            reply_markup=get_gender_keyboard()
        )

