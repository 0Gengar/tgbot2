import sqlite3

DB_NAME = 'bot.db'


def init_db():
    """Создаёт таблицы, если их ещё нет"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей (из ТЗ, раздел 5)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            gender TEXT CHECK(gender IN ('male', 'female', 'unknown')) DEFAULT 'unknown',
            birth_day INTEGER,
            birth_month INTEGER,
            birth_year INTEGER,
            wishlist TEXT,
            saved_payment_details TEXT,
            is_active_payer BOOLEAN DEFAULT 1
        )
    ''')

    # Таблица чатов (из ТЗ, раздел 5)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def get_user(user_id):
    """Возвращает данные пользователя или None"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def save_user(user_id, username, full_name, gender, birth_day, birth_month, birth_year=None):
    """Сохраняет или обновляет анкету пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, full_name, gender, birth_day, birth_month, birth_year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            gender = excluded.gender,
            birth_day = excluded.birth_day,
            birth_month = excluded.birth_month,
            birth_year = excluded.birth_year
    ''', (user_id, username, full_name, gender, birth_day, birth_month, birth_year))
    conn.commit()
    conn.close()


def update_wishlist(user_id, wishlist):
    """Обновляет вишлист пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET wishlist = ? WHERE user_id = ?', (wishlist, user_id))
    conn.commit()
    conn.close()
