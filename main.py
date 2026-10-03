import telebot
from telebot import types
import re
from datetime import date
import db

db.init_db()

TOKEN = '8856407895:AAGz8korzqo9J-l3HSgZMHy2l4bmMDXZwqU'
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
        bot.send_message(message.chat.id, "📭 В ближайшие 30 дней дней рождения нет.")
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
        "🤖 Доступные команды:\n\n"
        "👤 Профиль:\n"
        "• /start — заполнить или показать анкету\n"
        "• /profile — посмотреть свою анкету\n"
        "• /edit_wishlist — изменить вишлист\n\n"
        "🎂 Календарь дней рождения:\n"
        "• /upcoming — ближайшие ДР за 30 дней\n"
        "• /today — у кого ДР сегодня\n"
        "• /birthdays — все дни рождения\n\n"
        "👥 Общее:\n"
        "• /all_users — список всех пользователей\n"
        "• /help — эта справка\n\n"
        "🎁 Сборы (скоро):\n"
        "• /create_fund — создать сбор"
        "• /my_funds — мои сборы\n"
    )
    bot.send_message(message.chat.id, text)

# ============ МАСТЕР СБОРОВ ============

fund_data = {}


@bot.message_handler(commands=['create_fund'])
def create_fund_start(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        bot.send_message(message.chat.id, "Сначала заполни анкету командой /start")
        return

    fund_data[user_id] = {'chat_id': message.chat.id}
    bot.send_message(
        message.chat.id,
        "🎁 **Создание сбора**\n\n"
        "Шаг 1/5: Введи **название сбора**.\n"
        "Например: «День рождения Алексея» или «Корпоратив».",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, fund_step_title)


def fund_step_title(message):
    user_id = message.from_user.id
    fund_data[user_id]['title'] = message.text.strip()

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎂 День рождения", callback_data="fund_type_birthday"),
        types.InlineKeyboardButton("🎖 23 Февраля", callback_data="fund_type_men_holiday"),
        types.InlineKeyboardButton("🌷 8 Марта", callback_data="fund_type_women_holiday"),
        types.InlineKeyboardButton("🎉 Корпоратив", callback_data="fund_type_party"),
        types.InlineKeyboardButton("✏️ Другое", callback_data="fund_type_custom"),
    )
    bot.send_message(
        message.chat.id,
        "Шаг 2/5: Выбери **тип события**:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_type_'))
def fund_step_type(call):
    user_id = call.from_user.id
    fund_data[user_id]['event_type'] = call.data.replace('fund_type_', '')

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Шаг 3/5: Введи **сумму сбора**.\n"
             "Например: `5000` (общая сумма) или `500 с человека`.\n"
             "Если с человека — бот рассчитает итог автоматически.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, fund_step_amount)


def fund_step_amount(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()

    per_person = None
    total = None

    match_per = re.search(r'(\d+)\s*с\s*человека', text)
    if match_per:
        per_person = int(match_per.group(1))
    else:
        match_total = re.search(r'(\d+)', text)
        if match_total:
            total = int(match_total.group(1))
        else:
            bot.send_message(message.chat.id, "❌ Не понял сумму. Попробуй ещё раз.")
            bot.register_next_step_handler(message, fund_step_amount)
            return

    fund_data[user_id]['total_amount'] = total
    fund_data[user_id]['per_person_amount'] = per_person

    bot.send_message(
        message.chat.id,
        "Шаг 4/5: Введи **реквизиты для оплаты**.\n"
        "Например: `Сбер 1234 5678 9012 3456 Иван И.`"
    )
    bot.register_next_step_handler(message, fund_step_requisites)


def fund_step_requisites(message):
    user_id = message.from_user.id
    fund_data[user_id]['payment_details'] = message.text.strip()

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 Все активные", callback_data="fund_pay_all"),
        types.InlineKeyboardButton("👨 Только мужчины", callback_data="fund_pay_male"),
        types.InlineKeyboardButton("👩 Только женщины", callback_data="fund_pay_female"),
    )
    bot.send_message(
        message.chat.id,
        "Шаг 5/5: Кого включить в сбор?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_pay_'))
def fund_step_payers(call):
    user_id = call.from_user.id
    choice = call.data.replace('fund_pay_', '')

    if choice == 'all':
        participants = db.get_all_active_payers()
    elif choice == 'male':
        participants = db.get_payers_by_gender('male')
    elif choice == 'female':
        participants = db.get_payers_by_gender('female')
    else:
        participants = []

    if not participants:
        bot.answer_callback_query(call.id, "Нет подходящих участников")
        return

    fund = fund_data[user_id]

    if fund['per_person_amount']:
        per_person = fund['per_person_amount']
        total = per_person * len(participants)
    else:
        total = fund['total_amount']
        per_person = round(total / len(participants), 2)

    fund['total_amount'] = total
    fund['per_person_amount'] = per_person

    participants_list = [
        {'user_id': p['user_id'], 'full_name': p['full_name'], 'username': p.get('username'), 'is_paid': False}
        for p in participants
    ]

    event_id = db.create_event(
        chat_id=call.message.chat.id,
        creator_id=user_id,
        title=fund['title'],
        event_type=fund['event_type'],
        target_user_id=None,
        total_amount=total,
        per_person_amount=per_person,
        payment_details=fund['payment_details'],
        participants=participants_list
    )

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ Сбор **«{fund['title']}»** создан!\n\n"
             f"💰 Сумма: {total} ₽ (по {per_person} ₽ с человека)\n"
             f"👥 Участников: {len(participants)}\n\n"
             f"Рассылка в ЛС сейчас начнётся.",
        parse_mode='Markdown'
    )

    # Рассылка в ЛС
    for p in participants_list:
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Я перевёл(а)", callback_data=f"fund_paid_{event_id}"))
            bot.send_message(
                p['user_id'],
                f"🔔 **Сбор: {fund['title']}**\n\n"
                f"💰 Сумма: {per_person} ₽\n"
                f"💳 Реквизиты:\n`{fund['payment_details']}`\n\n"
                f"После оплаты нажми кнопку ниже 👇",
                parse_mode='Markdown',
                reply_markup=markup
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить {p['user_id']}: {e}")

    del fund_data[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_paid_'))
def fund_mark_paid(call):
    event_id = int(call.data.replace('fund_paid_', ''))
    user_id = call.from_user.id

    if db.mark_paid(event_id, user_id):
        bot.answer_callback_query(call.id, "✅ Отмечено!")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ Спасибо! Ты отметил оплату."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка")


@bot.message_handler(commands=['my_funds'])
def show_my_funds(message):
    user_id = message.from_user.id
    events = db.get_events_by_creator(user_id)

    if not events:
        bot.send_message(message.chat.id, "📭 У тебя пока нет созданных сборов.")
        return

    text = "📋 **Твои сборы:**\n\n"
    for e in events:
        paid = sum(1 for p in e['participants'] if p['is_paid'])
        total_p = len(e['participants'])
        status = "🟢 Активен" if e['status'] == 'active' else "🔴 Закрыт"
        text += (
            f"#{e['event_id']} — **{e['title']}**\n"
            f"   {status} | {paid}/{total_p} оплатили\n"
            f"   💰 {e['per_person_amount']} ₽ с человека\n\n"
        )

    bot.send_message(message.chat.id, text, parse_mode='Markdown')

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
