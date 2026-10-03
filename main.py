import telebot
from telebot import types
import re
from datetime import date
import db

db.init_db()

TOKEN = '8856407895:AAGz8korzqo9J-l3HSgZMHy2l4bmMDXZwqU'
bot = telebot.TeleBot(TOKEN)

user_data = {}
menu_messages = {}
fund_data = {}

def fake_message_from_call(call):
    """Создаёт объект message с правильным from_user из call."""
    msg = call.message
    msg.from_user = call.from_user
    return msg


# ============ ГЛАВНОЕ МЕНЮ ============

def delete_previous_menu(chat_id):
    if chat_id in menu_messages:
        try:
            bot.delete_message(chat_id, menu_messages[chat_id])
        except:
            pass


def send_main_menu(chat_id, edit=False, message_id=None):
    text = "🏠 **Главное меню**\n\nВыбери раздел:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
        types.InlineKeyboardButton("🎂 Календарь", callback_data="menu_calendar"),
        types.InlineKeyboardButton("👥 Общее", callback_data="menu_general"),
        types.InlineKeyboardButton("🎁 Сборы", callback_data="menu_funds"),
    )

    if edit and message_id:
        try:
            bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text,
                parse_mode='Markdown', reply_markup=markup
            )
        except:
            pass
    else:
        delete_previous_menu(chat_id)
        msg = bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
        menu_messages[chat_id] = msg.message_id


@bot.message_handler(commands=['menu'])
def show_main_menu(message):
    send_main_menu(message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == 'menu_main')
def menu_back_to_main(call):
    bot.answer_callback_query(call.id)
    send_main_menu(call.message.chat.id, edit=True, message_id=call.message.message_id)


# ============ ПОДМЕНЮ: ПРОФИЛЬ ============

@bot.callback_query_handler(func=lambda call: call.data == 'menu_profile')
def menu_profile(call):
    bot.answer_callback_query(call.id)
    text = "👤 **Профиль**\n\nВыбери действие:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 Заполнить анкету", callback_data="profile_fill"),
        types.InlineKeyboardButton("👁 Посмотреть профиль", callback_data="profile_view"),
        types.InlineKeyboardButton("🎁 Изменить вишлист", callback_data="profile_wishlist"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'profile_fill')
def profile_fill(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if user:
        bot.send_message(call.message.chat.id, "У тебя уже есть анкета. Используй «Посмотреть профиль».")
        send_main_menu(call.message.chat.id)
        return
    bot.send_message(
        call.message.chat.id,
        f"Привет, {call.from_user.first_name}! 👋\n\nДавай заполним твою анкету.\n\nУкажи свой **пол**:",
        parse_mode='Markdown', reply_markup=get_gender_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == 'profile_view')
def profile_view(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_profile(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'profile_wishlist')
def profile_wishlist(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    edit_wishlist(call.message)


# ============ ПОДМЕНЮ: КАЛЕНДАРЬ ============

@bot.callback_query_handler(func=lambda call: call.data == 'menu_calendar')
def menu_calendar(call):
    bot.answer_callback_query(call.id)
    text = "🎂 **Календарь**\n\nВыбери действие:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⏳ Ближайшие 30 дней", callback_data="cal_upcoming"),
        types.InlineKeyboardButton("🎉 Сегодня", callback_data="cal_today"),
        types.InlineKeyboardButton("📅 Все дни рождения", callback_data="cal_all"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'cal_upcoming')
def cal_upcoming(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_upcoming(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'cal_today')
def cal_today(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_today(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'cal_all')
def cal_all(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_all_birthdays(call.message)


# ============ ПОДМЕНЮ: ОБЩЕЕ ============

@bot.callback_query_handler(func=lambda call: call.data == 'menu_general')
def menu_general(call):
    bot.answer_callback_query(call.id)
    text = "👥 **Общее**\n\nВыбери действие:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 Все пользователи", callback_data="gen_users"),
        types.InlineKeyboardButton("ℹ️ Помощь", callback_data="gen_help"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'gen_users')
def gen_users(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_all_users(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'gen_help')
def gen_help(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_help(call.message)


# ============ ПОДМЕНЮ: СБОРЫ ============

@bot.callback_query_handler(func=lambda call: call.data == 'menu_funds')
def menu_funds(call):
    bot.answer_callback_query(call.id)
    text = "🎁 **Сборы**\n\nВыбери действие:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Создать сбор", callback_data="fund_create"),
        types.InlineKeyboardButton("📋 Мои сборы", callback_data="fund_list"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'fund_create')
def fund_create(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    create_fund_start(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'fund_list')
def fund_list(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_my_funds(call.message)


# ============ АНКЕТА ============

def get_gender_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male"),
        types.InlineKeyboardButton("👩 Женский", callback_data="gender_female"),
    )
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        send_main_menu(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот для организации корпоративных сборов и поздравлений.\n"
            "Давай заполним твою анкету. Это займёт минуту.\n\n"
            "Укажи свой **пол**:",
            parse_mode='Markdown', reply_markup=get_gender_keyboard()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def callback_gender(call):
    user_id = call.from_user.id
    gender = call.data.split('_')[1]

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['gender'] = gender

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
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
        bot.send_message(message.chat.id,
            "❌ Неверный формат. Напиши так: `15.03` или `15.03.1995`", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_birthday)
        return

    day, month, year = match.groups()
    day, month = int(day), int(month)

    if not (1 <= day <= 31 and 1 <= month <= 12):
        bot.send_message(message.chat.id, "❌ Такой даты не существует.")
        bot.register_next_step_handler(message, process_birthday)
        return

    user_data[user_id]['birth_day'] = day
    user_data[user_id]['birth_month'] = month
    user_data[user_id]['birth_year'] = int(year) if year else None

    bot.send_message(message.chat.id,
        "Принято! 📅\n\nТеперь напиши свой **вишлист** (или «Пропустить»).")
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
    bot.send_message(message.chat.id, "✅ Анкета заполнена!")
    send_main_menu(message.chat.id)


# ============ КОМАНДЫ ПРОФИЛЯ ============

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
        f"🎁 Твой текущий вишлист:\n_{current}_\n\nНапиши новый вишлист или «Пропустить»:",
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


# ============ КАЛЕНДАРЬ ============

@bot.message_handler(commands=['upcoming'])
def show_upcoming(message):
    upcoming = db.get_upcoming_birthdays(days_ahead=30)
    if not upcoming:
        bot.send_message(message.chat.id, "📭 В ближайшие 30 дней ДР нет.")
        return

    text = "🎂 **Ближайшие дни рождения (30 дней):**\n\n"
    for item in upcoming:
        user = item['user']
        days_left = item['days_left']
        bday = item['date']
        when = "🎉 **СЕГОДНЯ!**" if days_left == 0 else ("⏰ Завтра" if days_left == 1 else f"⏳ Через {days_left} дн.")
        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += f"\n   📅 {bday.strftime('%d.%m.%Y')} — {when}\n"
        if item['turning_age']:
            text += f"   🎈 Исполнится: {item['turning_age']} лет\n"
        text += "\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['today'])
def show_today(message):
    upcoming = db.get_upcoming_birthdays(days_ahead=0)
    if not upcoming:
        bot.send_message(message.chat.id, "📭 Сегодня ДР нет.")
        return

    text = "🎉 **Сегодня день рождения у:**\n\n"
    for item in upcoming:
        user = item['user']
        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += "\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['birthdays'])
def show_all_birthdays(message):
    birthdays = db.get_all_birthdays()
    if not birthdays:
        bot.send_message(message.chat.id, "📭 В базе нет ДР.")
        return

    text = "📅 **Все дни рождения:**\n"
    month_names = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",
                   7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}
    current_month = None
    for item in birthdays:
        user = item['user']; month = item['month']; day = item['day']
        if month != current_month:
            text += f"\n🗓 **{month_names[month]}**\n"
            current_month = month
        text += f"   • {day:02d}.{month:02d} — {user['full_name']}"
        if user.get('birth_year'):
            text += f" ({date.today().year - user['birth_year']} лет)"
        text += "\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ============ ОБЩЕЕ ============

@bot.message_handler(commands=['all_users'])
def show_all_users(message):
    users = db.get_all_users()
    text = "👥 **Пользователи:**\n\n"
    for u in users:
        text += f"• {u['full_name']} (@{u['username']}) — {u['gender']}, ДР: {u['birth_day']:02d}.{u['birth_month']:02d}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def show_help(message):
    text = (
        "🤖 Доступные команды:\n\n"
        "• /menu — главное меню\n"
        "• /start — регистрация\n"
        "• /profile — профиль\n"
        "• /create_fund — создать сбор\n"
        "• /my_funds — мои сборы\n"
        "• /upcoming — ближайшие ДР\n"
        "• /today — ДР сегодня\n"
        "• /birthdays — все ДР\n"
        "• /all_users — все пользователи\n"
    )
    bot.send_message(message.chat.id, text)
    send_main_menu(message.chat.id)


# ============ МАСТЕР СБОРОВ ============

@bot.message_handler(commands=['create_fund'])
def create_fund_start(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "Сначала заполни анкету /start")
        return
    fund_data[user_id] = {'chat_id': message.chat.id}
    bot.send_message(
        message.chat.id,
        "🎁 **Создание сбора**\n\nШаг 1/5: Введи **название сбора**.",
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
    bot.send_message(message.chat.id, "Шаг 2/5: Выбери **тип события**:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_type_'))
def fund_step_type(call):
    user_id = call.from_user.id
    fund_data[user_id]['event_type'] = call.data.replace('fund_type_', '')
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text="Шаг 3/5: Введи **сумму сбора**.\nНапример: `5000` (общая) или `500 с человека`.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, fund_step_amount)


def fund_step_amount(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()
    per_person = None; total = None
    match_per = re.search(r'(\d+)\s*с\s*человека', text)
    if match_per:
        per_person = int(match_per.group(1))
    else:
        match_total = re.search(r'(\d+)', text)
        if match_total:
            total = int(match_total.group(1))
        else:
            bot.send_message(message.chat.id, "❌ Не понял сумму.")
            bot.register_next_step_handler(message, fund_step_amount)
            return
    fund_data[user_id]['total_amount'] = total
    fund_data[user_id]['per_person_amount'] = per_person
    bot.send_message(message.chat.id, "Шаг 4/5: Введи **реквизиты для оплаты**.")
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
    bot.send_message(message.chat.id, "Шаг 5/5: Кого включить?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_pay_'))
def fund_step_payers(call):
    user_id = call.from_user.id
    choice = call.data.replace('fund_pay_', '')
    if choice == 'all':
        participants = db.get_all_active_payers()
    elif choice == 'male':
        participants = db.get_payers_by_gender('male')
    else:
        participants = db.get_payers_by_gender('female')

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

    participants_list = [
        {'user_id': p['user_id'], 'full_name': p['full_name'], 'is_paid': False}
        for p in participants
    ]

    event_id = db.create_event(
        chat_id=call.message.chat.id, creator_id=user_id,
        title=fund['title'], event_type=fund['event_type'], target_user_id=None,
        total_amount=total, per_person_amount=per_person,
        payment_details=fund['payment_details'], participants=participants_list
    )

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id,
        text=f"✅ Сбор **«{fund['title']}»** создан!\n\n"
             f"💰 {total} ₽ (по {per_person} ₽)\n👥 {len(participants)} участников",
        parse_mode='Markdown'
    )

    for p in participants_list:
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Я перевёл(а)", callback_data=f"fund_paid_{event_id}"))
            bot.send_message(
                p['user_id'],
                f"🔔 **Сбор: {fund['title']}**\n\n💰 {per_person} ₽\n💳 Реквизиты:\n`{fund['payment_details']}`",
                parse_mode='Markdown', reply_markup=markup
            )
        except Exception as e:
            print(f"⚠️ Не отправлено {p['user_id']}: {e}")

    del fund_data[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_paid_'))
def fund_mark_paid(call):
    event_id = int(call.data.replace('fund_paid_', ''))
    if db.mark_paid(event_id, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Отмечено!")
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text="✅ Спасибо! Ты отметил оплату."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка")


@bot.message_handler(commands=['my_funds'])
def show_my_funds(message):
    events = db.get_events_by_creator(message.from_user.id)
    if not events:
        bot.send_message(message.chat.id, "📭 У тебя нет сборов.")
        return
    text = "📋 **Твои сборы:**\n\n"
    for e in events:
        paid = sum(1 for p in e['participants'] if p['is_paid'])
        text += (
            f"#{e['event_id']} — **{e['title']}**\n"
            f"   {paid}/{len(e['participants'])} оплатили | {e['per_person_amount']} ₽\n\n"
        )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
