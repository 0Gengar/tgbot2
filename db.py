from datetime import date

users_db = {
    111111111: {
        'user_id': 111111111,
        'username': 'alex',
        'full_name': 'Алексей Смирнов',
        'gender': 'male',
        'birth_day': 15,
        'birth_month': 3,
        'birth_year': 1995,
        'wishlist': 'Наушники Sony WH-1000XM5',
        'saved_payment_details': None,
        'is_active_payer': 1
    },
    222222222: {
        'user_id': 222222222,
        'username': 'maria',
        'full_name': 'Мария Иванова',
        'gender': 'female',
        'birth_day': 8,
        'birth_month': 7,
        'birth_year': None,
        'wishlist': 'Сертификат в SPA, книга "Мастер и Маргарита"',
        'saved_payment_details': None,
        'is_active_payer': 1
    },
    333333333: {
        'user_id': 333333333,
        'username': 'dmitry',
        'full_name': 'Дмитрий Козлов',
        'gender': 'male',
        'birth_day': 23,
        'birth_month': 2,
        'birth_year': 1990,
        'wishlist': None,
        'saved_payment_details': None,
        'is_active_payer': 1
    }
}


def init_db():
    print("Инициализация БД (в памяти): загружено", len(users_db), "пользователей")


def get_user(user_id):
    return users_db.get(user_id)


def save_user(user_id, username, full_name, gender, birth_day, birth_month, birth_year=None):
    users_db[user_id] = {
        'user_id': user_id,
        'username': username,
        'full_name': full_name,
        'gender': gender,
        'birth_day': birth_day,
        'birth_month': birth_month,
        'birth_year': birth_year,
        'wishlist': users_db.get(user_id, {}).get('wishlist'),
        'saved_payment_details': users_db.get(user_id, {}).get('saved_payment_details'),
        'is_active_payer': 1
    }
    print(f"✅ Пользователь {full_name} сохранён")


def update_wishlist(user_id, wishlist):
    if user_id in users_db:
        users_db[user_id]['wishlist'] = wishlist
        print(f"🎁 Вишлист обновлён для {users_db[user_id]['full_name']}")


def get_all_users():
    return list(users_db.values())


def get_upcoming_birthdays(days_ahead=30):
    today = date.today()
    upcoming = []

    for user in users_db.values():
        if not user.get('birth_day') or not user.get('birth_month'):
            continue

        try:
            bday_this_year = date(today.year, user['birth_month'], user['birth_day'])
        except ValueError:
            continue

        if bday_this_year < today:
            try:
                bday_this_year = date(today.year + 1, user['birth_month'], user['birth_day'])
            except ValueError:
                continue

        days_left = (bday_this_year - today).days

        if 0 <= days_left <= days_ahead:
            upcoming.append({
                'user': user,
                'date': bday_this_year,
                'days_left': days_left,
                'turning_age': (bday_this_year.year - user['birth_year']) if user.get('birth_year') else None
            })

    upcoming.sort(key=lambda x: x['days_left'])
    return upcoming


def get_all_birthdays():
    result = []

    for user in users_db.values():
        if not user.get('birth_day') or not user.get('birth_month'):
            continue

        result.append({
            'user': user,
            'month': user['birth_month'],
            'day': user['birth_day']
        })

    result.sort(key=lambda x: (x['month'], x['day']))
    return result
