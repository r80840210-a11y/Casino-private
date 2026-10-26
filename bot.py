
import os
import asyncio
import random
import sqlite3
from datetime import datetime, date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE = os.getenv("API_BASE", "http://67.211.221.152:8888")
DB_PATH = os.getenv("DB_PATH", "starfun.db")

MAIN_ADMIN_ID = 1780243264
START_BALANCE = 1000
WIN_CHANCE = 0.30
DAILY_REWARD = 100

if not TOKEN:
    raise RuntimeError("Укажи BOT_TOKEN в переменных окружения.")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            balance INTEGER NOT NULL DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bet INTEGER,
            result TEXT,
            delta INTEGER,
            created_at TEXT
        );
        """)
        con.execute(
            "INSERT OR IGNORE INTO admins(user_id) VALUES(?)",
            (MAIN_ADMIN_ID,)
        )

def is_admin(uid):
    with db() as con:
        return con.execute(
            "SELECT 1 FROM admins WHERE user_id=?", (uid,)
        ).fetchone() is not None

def get_user(uid, username=""):
    with db() as con:
        con.execute(
            """INSERT OR IGNORE INTO users
            (user_id, username, balance, created_at)
            VALUES (?, ?, ?, ?)""",
            (uid, username or "", START_BALANCE,
             datetime.utcnow().isoformat())
        )
        con.execute(
            "UPDATE users SET username=? WHERE user_id=?",
            (username or "", uid)
        )
        return con.execute(
            "SELECT * FROM users WHERE user_id=?", (uid,)
        ).fetchone()

def main_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🎰 Играть", callback_data="play")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="🎁 Ежедневный бонус", callback_data="daily")
    b.button(text="ℹ️ Правила", callback_data="rules")
    b.adjust(2, 2)
    return b.as_markup()

def play_kb():
    b = InlineKeyboardBuilder()
    for n in (10, 25, 50, 100, 250):
        b.button(text=f"🎲 Ставка {n}", callback_data=f"bet:{n}")
    b.button(text="⬅️ Меню", callback_data="menu")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()

def admin_kb():
    b = InlineKeyboardBuilder()
    items = [
        ("➕ Выдать очки", "adm:give"),
        ("➖ Забрать очки", "adm:take"),
        ("🚫 Забанить", "adm:ban"),
        ("✅ Разбанить", "adm:unban"),
        ("➕ Добавить админа", "adm:add"),
        ("➖ Удалить админа", "adm:del"),
        ("📣 Рассылка", "adm:broadcast"),
        ("📊 Статистика", "adm:stats"),
    ]
    for label, data in items:
        b.button(text=label, callback_data=data)
    b.adjust(2, 2, 2, 2)
    return b.as_markup()

bot = Bot(
    TOKEN,
    session=AiohttpSession(
        api=TelegramAPIServer.from_base(API_BASE)
    )
)
dp = Dispatcher()
pending = {}

@dp.message(CommandStart())
async def start(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["banned"]:
        return await m.answer("⛔ Доступ ограничен.")

    await m.answer(
        "⭐ <b>StarFun</b>\n\n"
        "🎰 Игра на виртуальные очки.\n"
        f"💰 Баланс: <b>{u['balance']}</b>\n\n"
        "Очки не являются Telegram Stars, "
        "не покупаются и не выводятся за деньги.",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def admin(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("⛔ Нет доступа.")
    await m.answer(
        "🛠 <b>Панель администратора</b>",
        reply_markup=admin_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery):
    await c.message.edit_text(
        "⭐ Главное меню", reply_markup=main_kb()
    )
    await c.answer()

@dp.callback_query(F.data == "play")
async def play(c: CallbackQuery):
    u = get_user(c.from_user.id, c.from_user.username)
    if u["banned"]:
        return await c.answer("Доступ ограничен.", show_alert=True)

    await c.message.edit_text(
        f"🎰 Выбери ставку.\n"
        f"Баланс: {u['balance']} очков\n"
        f"Шанс победы: {int(WIN_CHANCE * 100)}%",
        reply_markup=play_kb()
    )
    await c.answer()

@dp.callback_query(F.data.startswith("bet:"))
async def bet(c: CallbackQuery):
    try:
        amount = int(c.data.split(":")[1])
    except (ValueError, IndexError):
        return await c.answer("Некорректная ставка.", show_alert=True)

    u = get_user(c.from_user.id, c.from_user.username)

    if u["banned"]:
        return await c.answer("Доступ ограничен.", show_alert=True)

    if amount not in (10, 25, 50, 100, 250):
        return await c.answer("Некорректная ставка.", show_alert=True)

    win = random.random() < WIN_CHANCE
    delta = amount if win else -amount

    with db() as con:
        row = con.execute(
            "SELECT balance, banned FROM users WHERE user_id=?",
            (c.from_user.id,)
        ).fetchone()

        if not row or row["banned"] or row["balance"] < amount:
            return await c.answer(
                "Недостаточно очков.", show_alert=True
            )

        con.execute(
            """UPDATE users
            SET balance=balance+?, wins=wins+?, losses=losses+?
            WHERE user_id=?""",
            (delta, int(win), int(not win), c.from_user.id)
        )

        con.execute(
            """INSERT INTO history
            (user_id, bet, result, delta, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (
                c.from_user.id, amount,
                "win" if win else "loss", delta,
                datetime.utcnow().isoformat()
            )
        )

        balance = con.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (c.from_user.id,)
        ).fetchone()["balance"]

    result = (
        f"🎉 <b>Победа!</b>\n+{amount} очков"
        if win else
        f"😢 <b>Проигрыш!</b>\n−{amount} очков"
    )

    await c.message.edit_text(
        f"{result}\n\n⭐ Баланс: <b>{balance}</b>",
        reply_markup=play_kb(),
        parse_mode="HTML"
    )
    await c.answer()

@dp.callback_query(F.data == "profile")
async def profile(c: CallbackQuery):
    u = get_user(c.from_user.id, c.from_user.username)
    await c.message.edit_text(
        "👤 <b>Профиль</b>\n"
        f"🆔 ID: <code>{c.from_user.id}</code>\n"
        f"Имя: @{c.from_user.username or 'не задан'}\n"
        f"⭐ Баланс: <b>{u['balance']}</b>\n"
        f"🏆 Побед: {u['wins']}\n"
        f"📉 Поражений: {u['losses']}",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )
    await c.answer()

@dp.callback_query(F.data == "daily")
async def daily(c: CallbackQuery):
    u = get_user(c.from_user.id, c.from_user.username)

    if u["banned"]:
        return await c.answer("Доступ ограничен.", show_alert=True)

    today = date.today().isoformat()

    if u["last_daily"] == today:
        return await c.answer(
            "Бонус уже получен сегодня.", show_alert=True
        )

    with db() as con:
        con.execute(
            """UPDATE users SET balance=balance+?, last_daily=?
            WHERE user_id=?""",
            (DAILY_REWARD, today, c.from_user.id)
        )
        balance = con.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (c.from_user.id,)
        ).fetchone()["balance"]

    await c.message.edit_text(
        f"🎁 Получено {DAILY_REWARD} очков!\n"
        f"Баланс: {balance}",
        reply_markup=main_kb()
    )
    await c.answer()

@dp.callback_query(F.data == "rules")
async def rules(c: CallbackQuery):
    await c.message.edit_text(
        "ℹ️ <b>Правила</b>\n"
        "• Только виртуальные очки.\n"
        "• Победа — 30%, проигрыш — 70%.\n"
        "• Раунды независимы друг от друга.\n"
        "• Очки нельзя вывести или обменять на деньги "
        "и Telegram Stars.",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )
    await c.answer()

@dp.callback_query(F.data.startswith("adm:"))
async def admin_actions(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа.", show_alert=True)

    action = c.data.split(":")[1]

    if action == "stats":
        with db() as con:
            users = con.execute(
                "SELECT COUNT(*) n FROM users"
            ).fetchone()["n"]
            total = con.execute(
                "SELECT COALESCE(SUM(balance),0) n FROM users"
            ).fetchone()["n"]
            banned = con.execute(
                "SELECT COUNT(*) n FROM users WHERE banned=1"
            ).fetchone()["n"]

        await c.message.answer(
            f"📊 Игроков: {users}\n"
            f"Забанено: {banned}\n"
            f"Всего очков: {total}"
        )
    else:
        prompts = {
            "give": "Введи ID и количество: <code>ID количество</code>",
            "take": "Введи ID и количество: <code>ID количество</code>",
            "ban": "Введи Telegram ID для бана.",
            "unban": "Введи Telegram ID для разбана.",
            "add": "Введи Telegram ID нового администратора.",
            "del": "Введи ID администратора для удаления.",
            "broadcast": "Введи текст рассылки."
        }
        pending[c.from_user.id] = action
        await c.message.answer(
            prompts[action], parse_mode="HTML"
        )

    await c.answer()

@dp.message()
async def admin_input(m: Message):
    action = pending.get(m.from_user.id)

    if not action or not is_admin(m.from_user.id):
        return

    pending.pop(m.from_user.id, None)

    try:
        if action in ("give", "take"):
            parts = m.text.split()
            if len(parts) != 2:
                raise ValueError()

            uid, amount = map(int, parts)
            if amount <= 0:
                raise ValueError()

            with db() as con:
                con.execute(
                    """INSERT OR IGNORE INTO users
                    (user_id, username, balance, created_at)
                    VALUES (?, '', ?, ?)""",
                    (uid, START_BALANCE, datetime.utcnow().isoformat())
                )

                if action == "give":
                    con.execute(
                        "UPDATE users SET balance=balance+? WHERE user_id=?",
                        (amount, uid)
                    )
                else:
                    con.execute(
                        "UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?",
                        (amount, uid)
                    )

            await m.answer("✅ Готово.")

        elif action in ("ban", "unban"):
            uid = int(m.text.strip())

            with db() as con:
                con.execute(
                    """INSERT OR IGNORE INTO users
                    (user_id, username, balance, created_at)
                    VALUES (?, '', ?, ?)""",
                    (uid, START_BALANCE, datetime.utcnow().isoformat())
                )
                con.execute(
                    "UPDATE users SET banned=? WHERE user_id=?",
                    (int(action == "ban"), uid)
                )

            await m.answer("✅ Готово.")

        elif action in ("add", "del"):
            uid = int(m.text.strip())

            if uid == MAIN_ADMIN_ID and action == "del":
                return await m.answer(
                    "Нельзя удалить главного администратора."
                )

            with db() as con:
                if action == "add":
                    con.execute(
                        "INSERT OR IGNORE INTO admins(user_id) VALUES(?)",
                        (uid,)
                    )
                else:
                    con.execute(
                        "DELETE FROM admins WHERE user_id=?", (uid,)
                    )

            await m.answer("✅ Готово.")

        elif action == "broadcast":
            with db() as con:
                ids = [
                    r["user_id"] for r in con.execute(
                        "SELECT user_id FROM users WHERE banned=0"
                    )
                ]

            sent = 0
            for uid in ids:
                try:
                    await bot.send_message(uid, m.text)
                    sent += 1
                except Exception:
                    pass

            await m.answer(f"📣 Рассылка завершена. Отправлено: {sent}")

    except (ValueError, AttributeError):
        await m.answer(
            "❌ Неверный формат. Открой /admin и попробуй снова."
        )
    except Exception:
        await m.answer("❌ Ошибка выполнения команды.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
