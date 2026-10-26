import os, asyncio, random, sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE = os.getenv("API_BASE", "http://67.211.221.152:8888")
ADMIN_IDS = {1780243264}
DB_PATH = os.getenv("DB_PATH", "starfun.db")
START_BALANCE = 1000
BET_MIN, BET_MAX = 1, 1000

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Render environment variables.")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER NOT NULL DEFAULT 1000,
          wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
          banned INTEGER NOT NULL DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS history(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bet INTEGER,
          result TEXT, delta INTEGER, created_at TEXT
        );
        """)
        for admin in ADMIN_IDS:
            con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (admin,))

def is_admin(uid):
    with db() as con:
        return uid in ADMIN_IDS or con.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,)).fetchone() is not None

def get_user(uid, username):
    with db() as con:
        con.execute("INSERT OR IGNORE INTO users(user_id,username,balance,created_at) VALUES(?,?,?,?)",
                    (uid, username or "", START_BALANCE, datetime.utcnow().isoformat()))
        con.execute("UPDATE users SET username=? WHERE user_id=?", (username or "", uid))
        return con.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def kb_main():
    b = InlineKeyboardBuilder()
    b.button(text="🎰 Играть", callback_data="play")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="🎁 Получить очки", callback_data="daily")
    b.button(text="ℹ️ Правила", callback_data="rules")
    b.adjust(2,2)
    return b.as_markup()

def kb_play():
    b = InlineKeyboardBuilder()
    for n in (10, 25, 50, 100, 250):
        b.button(text=f"🎲 {n} очков", callback_data=f"bet:{n}")
    b.button(text="⬅️ Меню", callback_data="menu")
    b.adjust(2,2,1,1)
    return b.as_markup()

def admin_kb():
    b = InlineKeyboardBuilder()
    for label, data in [
        ("➕ Выдать очки", "adm:give"), ("➖ Забрать очки", "adm:take"),
        ("🚫 Забанить", "adm:ban"), ("✅ Разбанить", "adm:unban"),
        ("➕ Добавить админа", "adm:add"), ("➖ Удалить админа", "adm:del"),
        ("📣 Рассылка", "adm:broadcast"), ("📊 Статистика", "adm:stats")
    ]:
        b.button(text=label, callback_data=data)
    b.adjust(2,2,2,2)
    return b.as_markup()

bot = Bot(TOKEN, session=AiohttpSession(api=TelegramAPIServer.from_base(API_BASE)))
dp = Dispatcher()
pending = {}

@dp.message(CommandStart())
async def start(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["banned"]:
        return await m.answer("⛔ Доступ к боту ограничен.")
    await m.answer(
        "⭐ <b>StarFun — игровое казино на виртуальных очках</b>\n\n"
        "Играй в демо-режиме: очки не имеют денежной стоимости, "
        "их нельзя купить, вывести или обменять на реальные звёзды.\n"
        f"Твой баланс: <b>{u['balance']}</b> очков",
        reply_markup=kb_main(), parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def admin(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("⛔ Нет доступа.")
    await m.answer("🛠 <b>Панель администратора</b>", reply_markup=admin_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery):
    await c.message.edit_text("⭐ Главное меню", reply_markup=kb_main())
    await c.answer()

@dp.callback_query(F.data == "play")
async def play(c: CallbackQuery):
    await c.message.edit_text("Выбери ставку виртуальных очков:", reply_markup=kb_play())
    await c.answer()

@dp.callback_query(F.data.startswith("bet:"))
async def bet(c: CallbackQuery):
    amount = int(c.data.split(":")[1])
    u = get_user(c.from_user.id, c.from_user.username)
    if u["banned"]:
        return await c.answer("Доступ ограничен.", show_alert=True)
    if amount < BET_MIN or amount > BET_MAX or u["balance"] < amount:
        return await c.answer("Недостаточно очков.", show_alert=True)
    win = random.random() < 0.48
    delta = amount if win else -amount
    result = "win" if win else "loss"
    with db() as con:
        con.execute("UPDATE users SET balance=balance+?, wins=wins+?, losses=losses+? WHERE user_id=?",
                    (delta, int(win), int(not win), c.from_user.id))
        con.execute("INSERT INTO history(user_id,bet,result,delta,created_at) VALUES(?,?,?,?,?)",
                    (c.from_user.id, amount, result, delta, datetime.utcnow().isoformat()))
        newbal = con.execute("SELECT balance FROM users WHERE user_id=?", (c.from_user.id,)).fetchone()["balance"]
    msg = f"🎉 Победа! +{amount} очков." if win else f"🙃 Не повезло: −{amount} очков."
    await c.message.edit_text(f"{msg}\nБаланс: <b>{newbal}</b> очков", reply_markup=kb_play(), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "profile")
async def profile(c: CallbackQuery):
    u = get_user(c.from_user.id, c.from_user.username)
    await c.message.edit_text(
        f"👤 <b>Профиль</b>\nID: <code>{c.from_user.id}</code>\n"
        f"Имя: @{c.from_user.username or 'не задан'}\n"
        f"Баланс: <b>{u['balance']}</b> очков\n"
        f"Побед: {u['wins']} | Поражений: {u['losses']}",
        reply_markup=kb_main(), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "daily")
async def daily(c: CallbackQuery):
    u = get_user(c.from_user.id, c.from_user.username)
    if u["banned"]:
        return await c.answer("Доступ ограничен.", show_alert=True)
    with db() as con:
        con.execute("UPDATE users SET balance=balance+100 WHERE user_id=?", (c.from_user.id,))
        bal = con.execute("SELECT balance FROM users WHERE user_id=?", (c.from_user.id,)).fetchone()["balance"]
    await c.message.edit_text(f"🎁 Начислено 100 бесплатных очков!\nБаланс: {bal}", reply_markup=kb_main())
    await c.answer()

@dp.callback_query(F.data == "rules")
async def rules(c: CallbackQuery):
    await c.message.edit_text(
        "ℹ️ <b>Правила демо-режима</b>\n"
        "• Используются только виртуальные очки.\n"
        "• Очки нельзя купить, продать, вывести или обменять на деньги/Telegram Stars.\n"
        "• Результат каждого раунда случайный.\n"
        "• Команды администратора доступны только назначенным администраторам.",
        reply_markup=kb_main(), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("adm:"))
async def admin_actions(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа.", show_alert=True)
    action = c.data.split(":")[1]
    if action == "stats":
        with db() as con:
            users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            total = con.execute("SELECT COALESCE(SUM(balance),0) n FROM users").fetchone()["n"]
        await c.message.answer(f"📊 Пользователей: {users}\nВсего очков на балансах: {total}")
    else:
        prompts = {
            "give": "Введите: ID количество — выдать виртуальные очки.",
            "take": "Введите: ID количество — забрать виртуальные очки.",
            "ban": "Введите Telegram ID для блокировки.",
            "unban": "Введите Telegram ID для разблокировки.",
            "add": "Введите Telegram ID для назначения администратором.",
            "del": "Введите Telegram ID для удаления администратора.",
            "broadcast": "Введите текст рассылки."
        }
        pending[c.from_user.id] = action
        await c.message.answer(prompts[action])
    await c.answer()

@dp.message()
async def admin_input(m: Message):
    action = pending.get(m.from_user.id)
    if not action or not is_admin(m.from_user.id):
        return
    pending.pop(m.from_user.id, None)
    try:
        if action in ("give", "take"):
            uid, amount = map(int, m.text.split())
            if amount <= 0: raise ValueError()
            with db() as con:
                con.execute("INSERT OR IGNORE INTO users(user_id,username,balance,created_at) VALUES(?,?,?,?)",
                            (uid, "", START_BALANCE, datetime.utcnow().isoformat()))
                delta = amount if action == "give" else -amount
                if action == "take":
                    con.execute("UPDATE users SET balance=MAX(0,balance+?) WHERE user_id=?", (delta, uid))
                else:
                    con.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (delta, uid))
            await m.answer("Готово.")
        elif action in ("ban", "unban"):
            uid = int(m.text)
            with db() as con: con.execute("UPDATE users SET banned=? WHERE user_id=?", (int(action=="ban"), uid))
            await m.answer("Готово.")
        elif action in ("add", "del"):
            uid = int(m.text)
            with db() as con:
                if action == "add": con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
                else: con.execute("DELETE FROM admins WHERE user_id=?", (uid,))
            await m.answer("Готово.")
        elif action == "broadcast":
            with db() as con: ids = [r["user_id"] for r in con.execute("SELECT user_id FROM users")]
            sent = 0
            for uid in ids:
                try: await bot.send_message(uid, m.text); sent += 1
                except Exception: pass
            await m.answer(f"Рассылка завершена. Доставлено: {sent}")
    except Exception:
        await m.answer("Не получилось обработать ввод. Проверь формат и попробуй ещё раз.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
