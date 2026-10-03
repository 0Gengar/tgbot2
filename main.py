import telebot
from telebot import types
import re
from datetime import date
import db

db.init_db()

TOKEN = 'ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ'
bot = telebot.TeleBot(TOKEN)

user_data = {}


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


def get_gender_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_male = types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male")
    btn_female = types.InlineKeyboardButton("👩 Женский", callback_data="gender_female")
    markup.add(btn_male, btn_female)
    return markup


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
        "Все доступные команды — /help.\n"
        "А организаторы могут создавать сборы командой /create_fund (скоро)."
    )


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


@bot.message_handler(commands=['edit_wishlist'])
def edit_wishlist(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        bot.send_message(message.chat.id, "Сначала заполни анкету командой /start")
        return

    current = user.get('wishlist') or 'не указан'
    bot.send_message(
        message.chat.id,
        f"🎁 Твой текущий вишлист:\n_{current}_\n\n"
        "Напиши новый вишлист или «Пропустить», чтобы удалить:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, process_new_wishlist)


def process_new_wishlist(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text.lower() in ['пропустить', 'нет', '-']:
        db.update_wishlist(user_id, None)
        bot.send_message(message.chat.id, "✅ Вишлист удалён.")
    else:
        db.update_wishlist(user_id, text)
        bot.send_message(message.chat.id, "✅ Вишлист обновлён!")

    show_profile(message)


@bot.message_handler(commands=['all_users'])
def show_all_users(message):
    users = db.get_all_users()
    text = "👥 **Пользователи в базе:**\n\n"
    for u in users:
        text += f"• {u['full_name']} (@{u['username']}) — {u['gender']}, ДР: {u['birth_day']:02d}.{u['birth_month']:02d}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['upcoming'])
def show_upcoming(message):
    upcoming = db.get_upcoming_birthdays(days_ahead=30)

    if not upcoming:
        bot.send_message(
            message.chat.id,
            "📭 В ближайшие 30 дней дней рождения нет."
        )
        return

    text = "🎂 **Ближайшие дни рождения (30 дней):**\n\n"

    for item in upcoming:
        user = item['user']
        days_left = item['days_left']
        bday = item['date']

        if days_left == 0:
            when = "🎉 **СЕГОДНЯ!**"
        elif days_left == 1:
            when = "⏰ Завтра"
        else:
            when = f"⏳ Через {days_left} дн."

        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += f"\n"
        text += f"   📅 {bday.strftime('%d.%m.%Y')} — {when}\n"

        if item['turning_age']:
            text += f"   🎈 Исполнится: {item['turning_age']} лет\n"

        if user.get('wishlist'):
            text += f"   🎁 Вишлист: {user['wishlist'][:60]}\n"

        text += "\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['today'])
def show_today(message):
    upcoming = db.get_upcoming_birthdays(days_ahead=0)

    if not upcoming:
        bot.send_message(message.chat.id, "📭 Сегодня дней рождения нет.")
        return

    text = "🎉 **Сегодня день рождения у:**\n\n"
    for item in upcoming:
        user = item['user']
        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += "\n"
        if user.get('wishlist'):
            text += f"🎁 Вишлист: {user['wishlist']}\n"
        text += "\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['birthdays'])
def show_all_birthdays(message):
    birthdays = db.get_all_birthdays()

    if not birthdays:
        bot.send_message(message.chat.id, "📭 В базе пока нет дней рождения.")
        return

    text = "📅 **Все дни рождения:**\n"

    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    current_month = None

    for item in birthdays:
        user = item['user']
        month = item['month']
        day = item['day']

        if month != current_month:
            text += f"\n🗓 **{month_names[month]}**\n"
            current_month = month

        text += f"   • {day:02d}.{month:02d} — {user['full_name']}"
        if user.get('username'):
            text += f" (@{user['username']})"
        if user.get('birth_year'):
            age = date.today().year - user['birth_year']
            text += f" ({age} лет)"
        text += "\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def show_help(message):
    text = (
        "🤖 **Доступные команды:**\n\n"
        "👤 **Профиль:**\n"
        "• /start — заполнить или показать анкету\n"
        "• /profile — посмотреть свою анкету\n"
        "• /edit_wishlist — изменить вишлист\n\n"
        "🎂 **Календарь дней рождения:**\n"
        "• /upcoming — ближайшие ДР за 30 дней\n"
        "• /today — у кого ДР сегодня\n"
        "• /birthdays — все дни рождения\n\n"
        "👥 **Общее:**\n"
        "• /all_users — список всех пользователей\n"
        "• /help — эта справка\n\n"
        "🎁 **Сборы (скоро):**\n"
        "• /create_fund — создать сбор\n"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
