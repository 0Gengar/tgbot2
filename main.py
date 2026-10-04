import telebot
from telebot import types
import re
from datetime import date
import db

db.init_db()

TOKEN = '8856407895:AAGz8korzqo9J-l3HSgZMHy2l4bmMDXZwqU'
bot = telebot.TeleBot(TOKEN)

user_data = {}
fund_data = {}
last_bot_messages = {}


# ============ УТИЛИТЫ ============

def remember_message(chat_id, message_id):
    if chat_id not in last_bot_messages:
        last_bot_messages[chat_id] = []
    last_bot_messages[chat_id].append(message_id)


def clear_chat(chat_id, keep_last=0):
    if chat_id not in last_bot_messages:
        return
    msgs = last_bot_messages[chat_id]
    to_delete = msgs[:-keep_last] if keep_last > 0 else msgs
    for mid in to_delete:
        try:
            bot.delete_message(chat_id, mid)
        except:
            pass
    last_bot_messages[chat_id] = msgs[-keep_last:] if keep_last > 0 else []


def safe_send(chat_id, text, **kwargs):
    msg = bot.send_message(chat_id, text, **kwargs)
    remember_message(chat_id, msg.message_id)
    return msg


def safe_edit(chat_id, message_id, text, **kwargs):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
    except:
        pass


def delete_user_message(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass


# ============ ГЛАВНОЕ МЕНЮ ============

def send_main_menu(chat_id, edit=False, message_id=None, clean=True):
    text = "🏠 **Главное меню**\n\nВыбери раздел:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
        types.InlineKeyboardButton("🎂 Календарь", callback_data="menu_calendar"),
        types.InlineKeyboardButton("👥 Общее", callback_data="menu_general"),
        types.InlineKeyboardButton("🎁 Сборы", callback_data="menu_funds"),
    )

    if edit and message_id:
        safe_edit(chat_id, message_id, text, parse_mode='Markdown', reply_markup=markup)
    else:
        if clean:
            clear_chat(chat_id)
        safe_send(chat_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['menu'])
def show_main_menu(message):
    send_main_menu(message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == 'menu_main')
def menu_back_to_main(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)
    send_main_menu(call.message.chat.id, clean=False)


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
    safe_edit(call.message.chat.id, call.message.message_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'profile_fill')
def profile_fill(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)
    user_id = call.from_user.id
    user = db.get_user(user_id)
    if user:
        safe_send(call.message.chat.id, "У тебя уже есть анкета. Используй «Посмотреть профиль».")
        send_main_menu(call.message.chat.id, clean=False)
        return
    safe_send(
        call.message.chat.id,
        f"Привет, {call.from_user.first_name}! 👋\n\nДавай заполним твою анкету.\n\nУкажи свой **пол**:",
        parse_mode='Markdown', reply_markup=get_gender_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == 'profile_view')
def profile_view(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    user_id = call.from_user.id
    user = db.get_user(user_id)

    if not user:
        safe_send(call.message.chat.id, "❌ Ты ещё не заполнил анкету.\nНажми «📝 Заполнить анкету».")
        send_main_menu(call.message.chat.id, clean=False)
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
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data == 'profile_wishlist')
def profile_wishlist(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    user_id = call.from_user.id
    user = db.get_user(user_id)

    if not user:
        safe_send(call.message.chat.id, "❌ Ты ещё не заполнил анкету.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    current = user.get('wishlist') or 'не указан'
    safe_send(
        call.message.chat.id,
        f"🎁 Твой текущий вишлист:\n_{current}_\n\nНапиши новый вишлист или «Пропустить»:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_new_wishlist)


def process_new_wishlist(message):
    delete_user_message(message)
    user_id = message.from_user.id
    text = message.text.strip()

    if text.lower() in ['пропустить', 'нет', '-']:
        db.update_wishlist(user_id, None)
        safe_send(message.chat.id, "✅ Вишлист удалён.")
    else:
        db.update_wishlist(user_id, text)
        safe_send(message.chat.id, "✅ Вишлист обновлён!")

    user = db.get_user(user_id)
    gender_map = {'male': '👨 Мужской', 'female': '👩 Женский', 'unknown': '❓ Не указан'}
    birth = f"{user['birth_day']:02d}.{user['birth_month']:02d}"
    if user.get('birth_year'):
        birth += f".{user['birth_year']}"

    text_out = (
        f"📋 **Твоя анкета:**\n\n"
        f"👤 Имя: {user['full_name']}\n"
        f"⚧ Пол: {gender_map.get(user['gender'], '❓')}\n"
        f"🎂 Дата рождения: {birth}\n"
        f"🎁 Вишлист: {user.get('wishlist') or 'не указан'}\n"
    )
    safe_send(message.chat.id, text_out, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


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
    safe_edit(call.message.chat.id, call.message.message_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'cal_upcoming')
def cal_upcoming(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    upcoming = db.get_upcoming_birthdays(days_ahead=30)
    if not upcoming:
        safe_send(call.message.chat.id, "📭 В ближайшие 30 дней ДР нет.")
        send_main_menu(call.message.chat.id, clean=False)
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
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data == 'cal_today')
def cal_today(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    upcoming = db.get_upcoming_birthdays(days_ahead=0)
    if not upcoming:
        safe_send(call.message.chat.id, "📭 Сегодня ДР нет.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    text = "🎉 **Сегодня день рождения у:**\n\n"
    for item in upcoming:
        user = item['user']
        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += "\n"
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data == 'cal_all')
def cal_all(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    birthdays = db.get_all_birthdays()
    if not birthdays:
        safe_send(call.message.chat.id, "📭 В базе нет ДР.")
        send_main_menu(call.message.chat.id, clean=False)
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
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


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
    safe_edit(call.message.chat.id, call.message.message_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'gen_users')
def gen_users(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    users = db.get_all_users()
    if not users:
        safe_send(call.message.chat.id, "📭 В базе нет пользователей.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    text = "👥 **Пользователи:**\n\n"
    for u in users:
        gender_map = {'male': '👨', 'female': '👩', 'unknown': '❓'}
        g = gender_map.get(u['gender'], '❓')
        text += f"{g} {u['full_name']} (@{u['username']}) — ДР: {u['birth_day']:02d}.{u['birth_month']:02d}\n"
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data == 'gen_help')
def gen_help(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

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
    safe_send(call.message.chat.id, text)
    send_main_menu(call.message.chat.id, clean=False)


# ============ ПОДМЕНЮ: СБОРЫ ============

@bot.callback_query_handler(func=lambda call: call.data == 'menu_funds')
def menu_funds(call):
    bot.answer_callback_query(call.id)
    text = "🎁 **Сборы**\n\nВыбери действие:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Создать сбор", callback_data="fund_create"),
        types.InlineKeyboardButton("📋 Мои сборы", callback_data="fund_list"),
        types.InlineKeyboardButton("📊 Все сборы", callback_data="fund_all"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_main"),
    )
    safe_edit(call.message.chat.id, call.message.message_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'fund_create')
def fund_create(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    user_id = call.from_user.id
    user = db.get_user(user_id)

    if not user:
        safe_send(call.message.chat.id, "❌ Сначала заполни анкету.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    fund_data[user_id] = {'chat_id': call.message.chat.id}
    safe_send(
        call.message.chat.id,
        "🎁 **Создание сбора**\n\nШаг 1/5: Введи **название сбора**.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, fund_step_title)


@bot.callback_query_handler(func=lambda call: call.data == 'fund_list')
def fund_list(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    user_id = call.from_user.id
    events = db.get_events_by_creator(user_id)

    if not events:
        safe_send(call.message.chat.id, "📭 У тебя нет сборов.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    text = "📋 **Твои сборы:**\n\n"
    for e in events:
        paid = sum(1 for p in e['participants'] if p['is_paid'])
        text += (
            f"#{e['event_id']} — **{e['title']}**\n"
            f"   {paid}/{len(e['participants'])} оплатили | {e['per_person_amount']} ₽\n\n"
        )
    safe_send(call.message.chat.id, text, parse_mode='Markdown')
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data == 'fund_all')
def fund_all(call):
    bot.answer_callback_query(call.id)
    clear_chat(call.message.chat.id)

    events = db.get_all_active_events()
    if not events:
        safe_send(call.message.chat.id, "📭 Активных сборов нет.")
        send_main_menu(call.message.chat.id, clean=False)
        return

    safe_send(call.message.chat.id, f"📊 **Все активные сборы:** {len(events)}")
    for e in events:
        paid = sum(1 for p in e['participants'] if p['is_paid'])
        total_p = len(e['participants'])
        text = (
            f"🎁 **{e['title']}**\n"
            f"💰 {e['per_person_amount']} ₽ с человека\n"
            f"👥 {paid}/{total_p} оплатили\n"
            f"💳 Реквизиты: `{e['payment_details']}`"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("💸 Перевести", callback_data=f"fund_show_{e['event_id']}"),
            types.InlineKeyboardButton("✅ Я перевёл(а)", callback_data=f"fund_paid_{e['event_id']}")
        )
        safe_send(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_show_'))
def fund_show_details(call):
    event_id = int(call.data.replace('fund_show_', ''))
    event = db.get_event(event_id)
    if not event:
        bot.answer_callback_query(call.id, "Сбор не найден")
        return

    clear_chat(call.message.chat.id)
    text = (
        f"🎁 **{event['title']}**\n\n"
        f"💰 Сумма: {event['per_person_amount']} ₽\n"
        f"💳 Реквизиты:\n`{event['payment_details']}`\n\n"
        f"Скопируй реквизиты и переведи. После оплаты нажми «✅ Я перевёл(а)»."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Я перевёл(а)", callback_data=f"fund_paid_{event_id}"))
    safe_send(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    send_main_menu(call.message.chat.id, clean=False)
    bot.answer_callback_query(call.id)


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
        clear_chat(message.chat.id)
        safe_send(
            message.chat.id,
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Давай заполним твою анкету.\n\nУкажи свой **пол**:",
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
    safe_edit(
        call.message.chat.id, call.message.message_id,
        "Отлично! Теперь напиши свою **дату рождения** в формате `ДД.ММ` (например, `15.03`).",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_birthday)


def process_birthday(message):
    delete_user_message(message)
    user_id = message.from_user.id
    text = message.text.strip()
    match = re.match(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$', text)

    if not match:
        safe_send(message.chat.id, "❌ Неверный формат. Напиши так: `15.03`", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_birthday)
        return

    day, month, year = match.groups()
    day, month = int(day), int(month)

    if not (1 <= day <= 31 and 1 <= month <= 12):
        safe_send(message.chat.id, "❌ Такой даты не существует.")
        bot.register_next_step_handler(message, process_birthday)
        return

    user_data[user_id]['birth_day'] = day
    user_data[user_id]['birth_month'] = month
    user_data[user_id]['birth_year'] = int(year) if year else None

    safe_send(message.chat.id, "Принято! 📅\n\nТеперь напиши свой **вишлист** (или «Пропустить»).")
    bot.register_next_step_handler(message, process_wishlist)


def process_wishlist(message):
    delete_user_message(message)
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
    safe_send(message.chat.id, "✅ Анкета заполнена!")
    send_main_menu(message.chat.id, clean=False)


# ============ КОМАНДЫ ПРОФИЛЯ ============

@bot.message_handler(commands=['profile'])
def show_profile(message):
    clear_chat(message.chat.id)
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        safe_send(message.chat.id, "Ты ещё не заполнил анкету. Напиши /start")
        send_main_menu(message.chat.id, clean=False)
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
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


@bot.message_handler(commands=['edit_wishlist'])
def edit_wishlist(message):
    clear_chat(message.chat.id)
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        safe_send(message.chat.id, "Сначала заполни анкету командой /start")
        send_main_menu(message.chat.id, clean=False)
        return

    current = user.get('wishlist') or 'не указан'
    safe_send(
        message.chat.id,
        f"🎁 Твой текущий вишлист:\n_{current}_\n\nНапиши новый вишлист или «Пропустить»:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, process_new_wishlist)


# ============ КАЛЕНДАРЬ ============

@bot.message_handler(commands=['upcoming'])
def show_upcoming(message):
    clear_chat(message.chat.id)
    upcoming = db.get_upcoming_birthdays(days_ahead=30)
    if not upcoming:
        safe_send(message.chat.id, "📭 В ближайшие 30 дней ДР нет.")
        send_main_menu(message.chat.id, clean=False)
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
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


@bot.message_handler(commands=['today'])
def show_today(message):
    clear_chat(message.chat.id)
    upcoming = db.get_upcoming_birthdays(days_ahead=0)
    if not upcoming:
        safe_send(message.chat.id, "📭 Сегодня ДР нет.")
        send_main_menu(message.chat.id, clean=False)
        return

    text = "🎉 **Сегодня день рождения у:**\n\n"
    for item in upcoming:
        user = item['user']
        text += f"👤 **{user['full_name']}**"
        if user.get('username'):
            text += f" (@{user['username']})"
        text += "\n"
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


@bot.message_handler(commands=['birthdays'])
def show_all_birthdays(message):
    clear_chat(message.chat.id)
    birthdays = db.get_all_birthdays()
    if not birthdays:
        safe_send(message.chat.id, "📭 В базе нет ДР.")
        send_main_menu(message.chat.id, clean=False)
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
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


# ============ ОБЩЕЕ ============

@bot.message_handler(commands=['all_users'])
def show_all_users(message):
    clear_chat(message.chat.id)
    users = db.get_all_users()
    if not users:
        safe_send(message.chat.id, "📭 В базе нет пользователей.")
        send_main_menu(message.chat.id, clean=False)
        return

    text = "👥 **Пользователи:**\n\n"
    for u in users:
        gender_map = {'male': '👨', 'female': '👩', 'unknown': '❓'}
        g = gender_map.get(u['gender'], '❓')
        text += f"{g} {u['full_name']} (@{u['username']}) — ДР: {u['birth_day']:02d}.{u['birth_month']:02d}\n"
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


@bot.message_handler(commands=['help'])
def show_help(message):
    clear_chat(message.chat.id)
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
    safe_send(message.chat.id, text)
    send_main_menu(message.chat.id, clean=False)


# ============ МАСТЕР СБОРОВ ============

@bot.message_handler(commands=['create_fund'])
def create_fund_start(message):
    clear_chat(message.chat.id)
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        safe_send(message.chat.id, "Сначала заполни анкету /start")
        send_main_menu(message.chat.id, clean=False)
        return
    fund_data[user_id] = {'chat_id': message.chat.id}
    safe_send(message.chat.id, "🎁 **Создание сбора**\n\nШаг 1/5: Введи **название сбора**.", parse_mode='Markdown')
    bot.register_next_step_handler(message, fund_step_title)


def fund_step_title(message):
    delete_user_message(message)
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
    safe_send(message.chat.id, "Шаг 2/5: Выбери **тип события**:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_type_'))
def fund_step_type(call):
    user_id = call.from_user.id
    fund_data[user_id]['event_type'] = call.data.replace('fund_type_', '')
    bot.answer_callback_query(call.id)
    safe_edit(
        call.message.chat.id, call.message.message_id,
        "Шаг 3/5: Введи **сумму сбора**.\nНапример: `5000` (общая) или `500 с человека`.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, fund_step_amount)


def fund_step_amount(message):
    delete_user_message(message)
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
            safe_send(message.chat.id, "❌ Не понял сумму.")
            bot.register_next_step_handler(message, fund_step_amount)
            return
    fund_data[user_id]['total_amount'] = total
    fund_data[user_id]['per_person_amount'] = per_person
    safe_send(message.chat.id, "Шаг 4/5: Введи **реквизиты для оплаты**.")
    bot.register_next_step_handler(message, fund_step_requisites)


def fund_step_requisites(message):
    delete_user_message(message)
    user_id = message.from_user.id
    fund_data[user_id]['payment_details'] = message.text.strip()
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 Все активные", callback_data="fund_pay_all"),
        types.InlineKeyboardButton("👨 Только мужчины", callback_data="fund_pay_male"),
        types.InlineKeyboardButton("👩 Только женщины", callback_data="fund_pay_female"),
    )
    safe_send(message.chat.id, "Шаг 5/5: Кого включить?", reply_markup=markup)


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
    clear_chat(call.message.chat.id)
    safe_send(
        call.message.chat.id,
        f"✅ Сбор **«{fund['title']}»** создан!\n\n"
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
    send_main_menu(call.message.chat.id, clean=False)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fund_paid_'))
def fund_mark_paid(call):
    event_id = int(call.data.replace('fund_paid_', ''))
    if db.mark_paid(event_id, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Отмечено!")
        safe_edit(
            call.message.chat.id, call.message.message_id,
            "✅ Спасибо! Ты отметил оплату."
        )
        remember_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка")


@bot.message_handler(commands=['my_funds'])
def show_my_funds(message):
    clear_chat(message.chat.id)
    events = db.get_events_by_creator(message.from_user.id)
    if not events:
        safe_send(message.chat.id, "📭 У тебя нет сборов.")
        send_main_menu(message.chat.id, clean=False)
        return
    text = "📋 **Твои сборы:**\n\n"
    for e in events:
        paid = sum(1 for p in e['participants'] if p['is_paid'])
        text += (
            f"#{e['event_id']} — **{e['title']}**\n"
            f"   {paid}/{len(e['participants'])} оплатили | {e['per_person_amount']} ₽\n\n"
        )
    safe_send(message.chat.id, text, parse_mode='Markdown')
    send_main_menu(message.chat.id, clean=False)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
