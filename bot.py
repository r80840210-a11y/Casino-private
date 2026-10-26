import os
import asyncio
import random
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_BASE = os.getenv("TELEGRAM_API_BASE", "http://67.211.221.152:8888").rstrip("/")
OWNER_ID = 1780243264
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Render Environment variables.")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance INTEGER NOT NULL DEFAULT 0,
 wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0,
 created_at TEXT
);
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS promos(
 code TEXT PRIMARY KEY, amount INTEGER NOT NULL, max_uses INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS promo_uses(user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code));
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
""")
cur.execute("INSERT OR IGNORE INTO admins(id) VALUES(?)", (OWNER_ID,))
cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('win_chance','35')")
conn.commit()

def is_admin(uid):
    return conn.execute("SELECT 1 FROM admins WHERE id=?", (uid,)).fetchone() is not None

def ensure_user(u):
    conn.execute("""INSERT OR IGNORE INTO users(id,username,first_name,created_at)
                    VALUES(?,?,?,?)""",
                 (u.id, u.username or "", u.first_name or "", datetime.utcnow().isoformat()))
    conn.execute("UPDATE users SET username=?, first_name=? WHERE id=?",
                 (u.username or "", u.first_name or "", u.id))
    conn.commit()

def user_row(uid):
    return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def kb_main(uid):
    b = InlineKeyboardBuilder()
    b.button(text="⭐ Апгрейд", callback_data="upgrade")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="🎟 Активировать промокод", callback_data="promo")
    b.adjust(1)
    return b.as_markup()

def admin_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить админа", callback_data="adm_add")
    b.button(text="➖ Удалить админа", callback_data="adm_remove")
    b.button(text="⛔ Забанить", callback_data="adm_ban")
    b.button(text="✅ Разбанить", callback_data="adm_unban")
    b.button(text="⭐ Выдать очки", callback_data="adm_give")
    b.button(text="➖ Забрать очки", callback_data="adm_take")
    b.button(text="🎟 Создать промокод", callback_data="adm_promo")
    b.button(text="📣 Рассылка", callback_data="adm_broadcast")
    b.button(text="📊 Статистика", callback_data="adm_stats")
    b.adjust(1)
    return b.as_markup()

# One-step admin conversations are kept in memory; persistent data is in SQLite.
pending = {}

async def allowed(event):
    uid = event.from_user.id
    ensure_user(event.from_user)
    row = user_row(uid)
    if row and row["banned"]:
        if isinstance(event, CallbackQuery):
            await event.answer("Ваш аккаунт заблокирован.", show_alert=True)
        else:
            await event.answer("Ваш аккаунт заблокирован.")
        return False
    return True

async def start_handler(message: Message):
    if not await allowed(message): return
    await message.answer(
        "⭐ **StarPlay**\n\nВыберите раздел в меню ниже.",
        reply_markup=kb_main(message.from_user.id), parse_mode="Markdown"
    )

async def profile_handler(call: CallbackQuery):
    if not await allowed(call): return
    u = user_row(call.from_user.id)
    await call.message.edit_text(
        f"👤 **Профиль**\n\n"
        f"🆔 ID: `{u['id']}`\n"
        f"⭐ Баланс очков: **{u['balance']}**\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💥 Поражений: {u['losses']}\n\n"
        "Промокод можно активировать кнопкой в главном меню.",
        parse_mode="Markdown", reply_markup=kb_main(call.from_user.id)
    )
    await call.answer()

async def upgrade_handler(call: CallbackQuery):
    if not await allowed(call): return
    b = InlineKeyboardBuilder()
    for n in (5, 10, 25, 50, 100):
        b.button(text=f"{n} очков", callback_data=f"stake:{n}")
    b.button(text="⬅️ Назад", callback_data="home")
    b.adjust(2, 2, 1, 1)
    await call.message.edit_text(
        "⭐ **Апгрейд очков**\n\n"
        "Выберите ставку. При победе начисляется x1.5 от ставки; при проигрыше ставка списывается.\n"
        "Это режим на игровые очки без покупки и вывода денег.",
        parse_mode="Markdown", reply_markup=b.as_markup()
    )
    await call.answer()

async def stake_handler(call: CallbackQuery):
    if not await allowed(call): return
    stake = int(call.data.split(":")[1])
    u = user_row(call.from_user.id)
    if u["balance"] < stake:
        await call.answer("Недостаточно очков. Баланс можно получить из промокода или от администратора.", show_alert=True)
        return
    chance = int(conn.execute("SELECT value FROM settings WHERE key='win_chance'").fetchone()[0])
    won = random.randint(1, 100) <= chance
    if won:
        payout = int(stake * 1.5)
        conn.execute("UPDATE users SET balance=balance+?, wins=wins+1 WHERE id=?", (payout - stake, call.from_user.id))
        result = f"🎉 Победа! Начислено **{payout}** очков (x1.5)."
    else:
        conn.execute("UPDATE users SET balance=balance-?, losses=losses+1 WHERE id=?", (stake, call.from_user.id))
        result = f"💥 Неудача. Списано **{stake}** очков."
    conn.commit()
    u = user_row(call.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Ещё раз", callback_data="upgrade")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="🏠 Меню", callback_data="home")
    b.adjust(1)
    await call.message.edit_text(f"{result}\n\n⭐ Баланс: **{u['balance']}**", parse_mode="Markdown", reply_markup=b.as_markup())
    await call.answer()

async def home_handler(call: CallbackQuery):
    if not await allowed(call): return
    await call.message.edit_text("⭐ **StarPlay**\n\nВыберите раздел:", parse_mode="Markdown", reply_markup=kb_main(call.from_user.id))
    await call.answer()

async def promo_handler(call: CallbackQuery):
    if not await allowed(call): return
    pending[call.from_user.id] = ("promo", None)
    await call.message.answer("Отправьте название промокода одним сообщением.")
    await call.answer()

async def admin_handler(message: Message):
    if not await allowed(message): return
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await message.answer("🛠 **Админ-панель**", parse_mode="Markdown", reply_markup=admin_kb())

async def admin_button(call: CallbackQuery):
    if not await allowed(call): return
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True); return
    actions = {
        "adm_add": ("add_admin", "Введите Telegram ID пользователя, которого нужно сделать админом."),
        "adm_remove": ("remove_admin", "Введите Telegram ID админа, которого нужно удалить."),
        "adm_ban": ("ban", "Введите Telegram ID пользователя для блокировки."),
        "adm_unban": ("unban", "Введите Telegram ID пользователя для разблокировки."),
        "adm_give": ("give", "Введите ID пользователя и количество через пробел: `123456 100`."),
        "adm_take": ("take", "Введите ID пользователя и количество через пробел: `123456 100`."),
        "adm_promo": ("make_promo", "Введите данные промокода через пробел: `КОД количество_очков число_активаций`."),
        "adm_broadcast": ("broadcast", "Отправьте текст рассылки следующим сообщением."),
    }
    if call.data == "adm_stats":
        count = conn.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        total = conn.execute("SELECT COALESCE(SUM(balance),0) n FROM users").fetchone()["n"]
        await call.message.answer(f"📊 Пользователей: {count}\nВсего очков на балансах: {total}")
        await call.answer(); return
    action, prompt = actions[call.data]
    pending[call.from_user.id] = (action, None)
    await call.message.answer(prompt, parse_mode="Markdown")
    await call.answer()

async def text_handler(message: Message):
    if not await allowed(message): return
    item = pending.get(message.from_user.id)
    if not item: return
    action, _ = item
    text = (message.text or "").strip()
    if action == "promo":
        code = text.upper()
        promo = conn.execute("SELECT * FROM promos WHERE code=?", (code,)).fetchone()
        used = conn.execute("SELECT 1 FROM promo_uses WHERE user_id=? AND code=?", (message.from_user.id, code)).fetchone()
        if not promo or promo["uses"] >= promo["max_uses"]:
            await message.answer("Промокод не найден или лимит активаций исчерпан.")
        elif used:
            await message.answer("Вы уже активировали этот промокод.")
        else:
            conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (promo["amount"], message.from_user.id))
            conn.execute("UPDATE promos SET uses=uses+1 WHERE code=?", (code,))
            conn.execute("INSERT INTO promo_uses(user_id,code) VALUES(?,?)", (message.from_user.id, code))
            conn.commit()
            await message.answer(f"✅ Промокод активирован! Начислено {promo['amount']} очков.")
        pending.pop(message.from_user.id, None); return
    if not is_admin(message.from_user.id):
        pending.pop(message.from_user.id, None); return
    try:
        if action in ("add_admin", "remove_admin", "ban", "unban"):
            uid = int(text)
            if action == "add_admin":
                conn.execute("INSERT OR IGNORE INTO admins(id) VALUES(?)", (uid,)); msg = "Админ добавлен."
            elif action == "remove_admin":
                if uid == OWNER_ID: raise ValueError("Главного администратора удалить нельзя.")
                conn.execute("DELETE FROM admins WHERE id=?", (uid,)); msg = "Админ удалён."
            elif action == "ban":
                conn.execute("UPDATE users SET banned=1 WHERE id=?", (uid,)); msg = "Пользователь заблокирован (если он уже запускал бота)."
            else:
                conn.execute("UPDATE users SET banned=0 WHERE id=?", (uid,)); msg = "Пользователь разблокирован."
        elif action in ("give", "take"):
            uid_s, amount_s = text.split()
            uid, amount = int(uid_s), int(amount_s)
            if amount <= 0: raise ValueError("Количество должно быть больше нуля.")
            ensure = conn.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
            if not ensure: raise ValueError("Пользователь ещё не запускал бота.")
            delta = amount if action == "give" else -amount
            if action == "take" and user_row(uid)["balance"] < amount: raise ValueError("У пользователя недостаточно очков.")
            conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (delta, uid))
            msg = "Баланс обновлён."
        elif action == "make_promo":
            code, amount_s, uses_s = text.split()
            amount, uses = int(amount_s), int(uses_s)
            if amount <= 0 or uses <= 0: raise ValueError("Количество очков и активаций должны быть больше нуля.")
            conn.execute("INSERT INTO promos(code,amount,max_uses) VALUES(?,?,?)", (code.upper(), amount, uses))
            msg = f"Промокод {code.upper()} создан: {amount} очков, активаций: {uses}."
        elif action == "broadcast":
            pending.pop(message.from_user.id, None)
            rows = conn.execute("SELECT id FROM users WHERE banned=0").fetchall()
            ok = 0
            for row in rows:
                try:
                    await bot.send_message(row["id"], text)
                    ok += 1
                except Exception:
                    pass
            await message.answer(f"Рассылка завершена: доставлено {ok} из {len(rows)}.")
            return
        else:
            msg = "Неизвестное действие."
        conn.commit()
        await message.answer("✅ " + msg, reply_markup=admin_kb())
    except sqlite3.IntegrityError:
        await message.answer("Ошибка: такой промокод уже существует.")
    except Exception as e:
        await message.answer("Ошибка: " + str(e))
    finally:
        pending.pop(message.from_user.id, None)

async def main():
    global bot
    session = AiohttpSession(api=TelegramAPIServer.from_base(API_BASE))
    bot = Bot(TOKEN, session=session)
    dp = Dispatcher()
    dp.message.register(start_handler, CommandStart())
    dp.message.register(admin_handler, Command("admin"))
    dp.message.register(text_handler, F.text)
    dp.callback_query.register(profile_handler, F.data == "profile")
    dp.callback_query.register(upgrade_handler, F.data == "upgrade")
    dp.callback_query.register(stake_handler, F.data.startswith("stake:"))
    dp.callback_query.register(home_handler, F.data == "home")
    dp.callback_query.register(promo_handler, F.data == "promo")
    dp.callback_query.register(admin_button, F.data.startswith("adm_"))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
