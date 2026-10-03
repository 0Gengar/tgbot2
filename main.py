import telebot
from telebot import types
import re
import db

# Инициализация базы данных при запуске
db.init_db()

# Токен (лучше вынести в .env, но пока оставим так для теста)
TOKEN = '8856407895:AAHnKzDYAaHUUrpCxJxtggI-BwUprTRML0Y'
bot = telebot.TeleBot(TOKEN)

# Временное хранилище для данных анкеты (в памяти)
user_data = {}


# ---------- КОМАНДА /start ----------
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
        bot.register_next_step_handler(message, process_gender)


def get_gender_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_male = types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male")
    btn_female = types.InlineKeyboardButton("👩 Женский", callback_data="gender_female")
    markup.add(btn_male, btn_female)
    return markup


# ---------- ОБРАБОТКА ВЫБОРА ПОЛА (кнопкой) ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def callback_gender(call):
    user_id = call.from_user.id
    gender = call.data.split('_')[1]
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['gender'] = gender
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Отлично! Теперь напиши свою **дату рождения** в формате `ДД.ММ` (например, `15.03`).\n"
             "Год можно не указывать, если не хочешь.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_birthday)


# ---------- ОБРАБОТКА ПОЛА (текстом, если не нажал кнопку) ----------
def process_gender(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()
    
    if text in ['мужской', 'муж', 'м', 'male']:
        gender = 'male'
    elif text in ['женский', 'жен', 'ж', 'female']:
        gender = 'female'
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выбери пол кнопками выше 👆")
        bot.register_next_step_handler(message, process_gender)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['gender'] = gender
    
    bot.send_message(
        message.chat.id,
        "Отлично! Теперь напиши свою **дату рождения** в формате `ДД.ММ` (например, `15.03`).",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, process_birthday)


# ---------- ОБРАБОТКА ДАТЫ РОЖДЕНИЯ ----------
def process_birthday(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    match = re.match(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$', text)
    
    if not match:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Пожалуйста, напиши дату так: `15.03` или `15.03.1995`",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, process_birthday)
        return
    
    day, month, year = match.groups()
    day, month = int(day), int(month)
    
    if not (1 <= day <= 31 and 1 <= month <= 12):
        bot.send_message(message.chat.id, "❌ Такой даты не существует. Попробуй ещё раз.")
        bot.register_next_step_handler(message, process_birthday)
        return
    
    user_data[user_id]['birth_day'] = day
    user_data[user_id]['birth_month'] = month
    user_data[user_id]['birth_year'] = int(year) if year else None
    
    bot.send_message(
        message.chat.id,
        "Принято! 📅\n\n"
        "Теперь напиши свой **вишлист** (список желаемых подарков).\n"
        "Это может быть просто текст или ссылки. Если не хочешь — напиши «Пропустить».",
    )
    bot.register_next_step_handler(message, process_wishlist)


# ---------- ОБРАБОТКА ВИШЛИСТА ----------
def process_wishlist(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    wishlist = None if text.lower() in ['пропустить', 'нет', '-'] else text
    
    db.save_user(
        user_id=user_id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        gender=user_data[user_id]['gender'],
        birth_day=user_data[user_id]['birth_day'],
        birth_month=user_data[user_id]['birth_month'],
        birth_year=user_data[user_id]['birth_year']
    )
    
    if wishlist:
        db.update_wishlist(user_id, wishlist)
    
    del user_data[user_id]
    
    bot.send_message(
        message.chat.id,
        "✅ Анкета заполнена! Спасибо.\n\n"
        "Теперь ты можешь посмотреть свой профиль командой /profile.\n"
        "А организаторы могут создавать сборы командой /create_fund (скоро)."
    )


# ---------- КОМАНДА /profile ----------
@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "Ты ещё не заполнил анкету. Напиши /start")
        return
    
    gender_map = {'male': '👨 Мужской', 'female': '👩 Женский', 'unknown': '❓ Не указан'}
    
    birth = f"{user['birth_day']:02d}.{user['birth_month']:02d}"
    if user.get('birth_year'):
        birth += f".{user['birth_year']}"
    
    text = (
        f"📋 **Твоя анкета:**\n\n"
        f"👤 Имя: {user['full_name']}\n"
        f"⚧ Пол: {gender_map.get(user['gender'], '❓')}\n"
        f"🎂 Дата рождения: {birth}\n"
        f"🎁 Вишлист: {user.get('wishlist') or 'не указан'}\n"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ---------- КОМАНДА /all_users (только для тестов) ----------
@bot.message_handler(commands=['all_users'])
def show_all_users(message):
    users = db.get_all_users()
    text = "👥 **Пользователи в базе:**\n\n"
    for u in users:
        text += f"• {u['full_name']} (@{u['username']}) — {u['gender']}, ДР: {u['birth_day']:02d}.{u['birth_month']:02d}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
