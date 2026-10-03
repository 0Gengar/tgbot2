import telebot

bot = telebot.TeleBot('8856407895:AAHnKzDYAaHUUrpCxJxtggI-BwUprTRML0Y')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'hello')

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, 'Это команда help')

bot.infinity_polling()