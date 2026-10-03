# Временное хранилище в памяти (данные исчезнут при перезапуске)
users_db = {
    # Тестовые пользователи (3 человека)
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
    """Ничего не делает — база в памяти уже готова"""
    print("Инициализация БД (в памяти): загружено", len(users_db), "пользователей")

def get_user(user_id):
    """Возвращает словарь с данными пользователя или None"""
    return users_db.get(user_id)

def save_user(user_id, username, full_name, gender, birth_day, birth_month, birth_year=None):
    """Сохраняет или обновляет анкету пользователя"""
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
    """Обновляет вишлист пользователя"""
    if user_id in users_db:
        users_db[user_id]['wishlist'] = wishlist
        print(f"🎁 Вишлист обновлён для {users_db[user_id]['full_name']}")

def get_all_users():
    """Возвращает список всех пользователей (для тестов)"""
    return list(users_db.values())
