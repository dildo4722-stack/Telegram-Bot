import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            orders_count INTEGER DEFAULT 0,
            reg_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id):
    if not get_user(user_id):
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        reg_date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute('INSERT INTO users (user_id, reg_date) VALUES (?, ?)', (user_id, reg_date))
        conn.commit()
        conn.close()