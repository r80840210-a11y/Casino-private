import sqlite3
import os
from datetime import datetime
from config import DB_PATH, DEFAULT_MIN_WITHDRAW

class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Пользователи
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_won_stars INTEGER DEFAULT 0,
                total_lost_stars INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Промокоды
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                stars INTEGER,
                max_activations INTEGER,
                current_activations INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Активации промокодов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, promo_id)
            )
        """)

        # Настройки
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # История игр
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet INTEGER,
                result TEXT,
                won INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Рассылки
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                sent_by INTEGER,
                total_users INTEGER,
                success INTEGER,
                failed INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Устанавливаем минимальный вывод если не задан
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', ?)", 
                          (str(DEFAULT_MIN_WITHDRAW),))

        self.conn.commit()

    # ==================== USERS ====================
    def add_user(self, user_id, username=None, first_name=None):
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name) 
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def update_username(self, user_id, username, first_name):
        self.cursor.execute("""
            UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
        """, (username, first_name, user_id))
        self.conn.commit()

    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0

    def update_balance(self, user_id, amount):
        self.cursor.execute("""
            UPDATE users SET balance = balance + ? WHERE user_id = ?
        """, (amount, user_id))
        self.conn.commit()

    def set_balance(self, user_id, amount):
        self.cursor.execute("""
            UPDATE users SET balance = ? WHERE user_id = ?
        """, (amount, user_id))
        self.conn.commit()

    def add_win(self, user_id, stars):
        self.cursor.execute("""
            UPDATE users SET total_wins = total_wins + 1, total_won_stars = total_won_stars + ? 
            WHERE user_id = ?
        """, (stars, user_id))
        self.conn.commit()

    def add_loss(self, user_id, stars):
        self.cursor.execute("""
            UPDATE users SET total_losses = total_losses + 1, total_lost_stars = total_lost_stars + ? 
            WHERE user_id = ?
        """, (stars, user_id))
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        return self.cursor.fetchall()

    def get_users_count(self):
        self.cursor.execute("SELECT COUNT(*) as c FROM users")
        return self.cursor.fetchone()['c']

    # ==================== ADMIN ====================
    def is_admin(self, user_id):
        user = self.get_user(user_id)
        return user and user['is_admin'] == 1

    def add_admin(self, user_id):
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, is_admin) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_admin = 1
        """, (user_id,))
        self.conn.commit()

    def remove_admin(self, user_id):
        self.cursor.execute("""
            UPDATE users SET is_admin = 0 WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()

    def get_all_admins(self):
        self.cursor.execute("SELECT user_id, username, first_name FROM users WHERE is_admin = 1")
        return self.cursor.fetchall()

    def ban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def unban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_banned(self, user_id):
        user = self.get_user(user_id)
        return user and user['is_banned'] == 1

    # ==================== PROMOCODES ====================
    def create_promo(self, code, stars, max_activations, created_by):
        try:
            self.cursor.execute("""
                INSERT INTO promocodes (code, stars, max_activations, created_by) 
                VALUES (?, ?, ?, ?)
            """, (code.upper(), stars, max_activations, created_by))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_promo(self, code):
        self.cursor.execute("SELECT * FROM promocodes WHERE code = ? AND is_active = 1", (code.upper(),))
        return self.cursor.fetchone()

    def activate_promo(self, user_id, promo_id):
        # Проверяем не активировал ли уже
        self.cursor.execute("""
            SELECT id FROM promo_activations WHERE user_id = ? AND promo_id = ?
        """, (user_id, promo_id))
        if self.cursor.fetchone():
            return False, "already_activated"

        # Получаем промокод
        self.cursor.execute("SELECT * FROM promocodes WHERE id = ?", (promo_id,))
        promo = self.cursor.fetchone()

        if not promo:
            return False, "not_found"

        if promo['current_activations'] >= promo['max_activations']:
            return False, "limit_reached"

        # Активируем
        self.cursor.execute("""
            INSERT INTO promo_activations (user_id, promo_id) VALUES (?, ?)
        """, (user_id, promo_id))

        self.cursor.execute("""
            UPDATE promocodes SET current_activations = current_activations + 1 WHERE id = ?
        """, (promo_id,))

        # Начисляем звезды
        self.update_balance(user_id, promo['stars'])

        self.conn.commit()
        return True, promo['stars']

    def get_all_promos(self):
        self.cursor.execute("SELECT * FROM promocodes ORDER BY created_at DESC")
        return self.cursor.fetchall()

    def delete_promo(self, promo_id):
        self.cursor.execute("UPDATE promocodes SET is_active = 0 WHERE id = ?", (promo_id,))
        self.conn.commit()

    # ==================== SETTINGS ====================
    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row['value'] if row else None

    def set_setting(self, key, value):
        self.cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, str(value)))
        self.conn.commit()

    def get_min_withdraw(self):
        val = self.get_setting('min_withdraw')
        return int(val) if val else DEFAULT_MIN_WITHDRAW

    # ==================== GAMES ====================
    def add_game_history(self, user_id, bet, result, won):
        self.cursor.execute("""
            INSERT INTO game_history (user_id, bet, result, won) VALUES (?, ?, ?, ?)
        """, (user_id, bet, result, won))
        self.conn.commit()

    def get_user_stats(self, user_id):
        self.cursor.execute("""
            SELECT COUNT(*) as games, 
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                   SUM(CASE WHEN result = 'win' THEN bet ELSE 0 END) as won_stars,
                   SUM(CASE WHEN result = 'loss' THEN bet ELSE 0 END) as lost_stars
            FROM game_history WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()

    # ==================== BROADCAST ====================
    def add_broadcast(self, message, sent_by, total, success, failed):
        self.cursor.execute("""
            INSERT INTO broadcast_history (message, sent_by, total_users, success, failed) 
            VALUES (?, ?, ?, ?, ?)
        """, (message, sent_by, total, success, failed))
        self.conn.commit()

    def get_stats(self):
        stats = {}
        self.cursor.execute("SELECT COUNT(*) as c FROM users")
        stats['total_users'] = self.cursor.fetchone()['c']

        self.cursor.execute("SELECT COUNT(*) as c FROM users WHERE is_banned = 1")
        stats['banned'] = self.cursor.fetchone()['c']

        self.cursor.execute("SELECT COUNT(*) as c FROM users WHERE is_admin = 1")
        stats['admins'] = self.cursor.fetchone()['c']

        self.cursor.execute("SELECT COUNT(*) as c FROM promocodes WHERE is_active = 1")
        stats['active_promos'] = self.cursor.fetchone()['c']

        self.cursor.execute("SELECT SUM(balance) as s FROM users")
        result = self.cursor.fetchone()
        stats['total_stars'] = result['s'] if result['s'] else 0

        self.cursor.execute("SELECT COUNT(*) as c FROM game_history")
        stats['total_games'] = self.cursor.fetchone()['c']

        return stats

db = Database()
