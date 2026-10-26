import asyncio, os, sqlite3, random
from datetime import datetime
from html import escape
from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_BASE = os.getenv("API_BASE", "http://67.211.221.152:8888").rstrip("/")
DB_PATH = os.getenv("DB_PATH", "starfun.db")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "1780243264").split(",") if x.strip().isdigit()}
SUPPORT = os.getenv("SUPPORT_USERNAME", "v1nk_molik").lstrip("@")
if not TOKEN: raise RuntimeError("Set BOT_TOKEN in Render Environment.")

def connect():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; return c

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, username TEXT, balance INTEGER DEFAULT 0, games INTEGER DEFAULT 0, wins INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, reward INTEGER, limit_uses INTEGER, uses INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS promo_users(code TEXT, user_id INTEGER, PRIMARY KEY(code,user_id));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        INSERT OR IGNORE INTO settings VALUES('min_exchange','100');
        """)

def ensure(u):
    with connect() as c:
        c.execute("INSERT INTO users(id,name,username,balance) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET name=excluded.name,username=excluded.username",(u.id,u.full_name,u.username or ""))

def get_user(uid):
    with connect() as c: return c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()

def menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎮 Играть"),KeyboardButton(text="👤 Профиль")],[KeyboardButton(text="⭐ Пополнить баланс")]],resize_keyboard=True)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Начислить баланс",callback_data="givehelp")],
        [InlineKeyboardButton(text="🎟 Создать промокод",callback_data="promohelp")],
        [InlineKeyboardButton(text="📊 Статистика",callback_data="stats")],
        [InlineKeyboardButton(text="⚙️ Минимум обмена",callback_data="minhelp")]])

bot = Bot(TOKEN, session=AiohttpSession(api=TelegramAPIServer.from_base(API_BASE)))
dp = Dispatcher()
pending = {}

@dp.message(CommandStart())
async def start(m):
    ensure(m.from_user); u=get_user(m.from_user.id)
    await m.answer(f"⭐ <b>StarFun</b>\n\nДобро пожаловать в казино звёзд! ⭐\n💰 Баланс: <b>{u['balance']} ⭐</b>",reply_markup=menu(),parse_mode="HTML")

@dp.message(Command("profile"))
@dp.message(F.text=="👤 Профиль")
async def profile(m):
    ensure(m.from_user); u=get_user(m.from_user.id)
    await m.answer(f"👤 <b>Профиль StarFun</b>\n\nИмя: {escape(u['name'] or '')}\nUsername: @{escape(u['username'] or 'не указан')}\nID: <code>{u['id']}</code>\n💰 Баланс: <b>{u['balance']} ⭐</b>\n🎮 Игр: {u['games']}\n✅ Верных ответов: {u['wins']}",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Активировать промокод",callback_data="promo")]]),parse_mode="HTML")

@dp.message(F.text=="⭐ Пополнить баланс")
async def topup(m):
    await m.answer("⭐ <b>Пополнение игрового баланса</b>\n\nПо вопросам игрового баланса напиши администратору @"+escape(SUPPORT)+".",parse_mode="HTML",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Написать администратору",url=f"https://t.me/{SUPPORT}")]]))

@dp.message(Command("game"))
@dp.message(F.text=="🎮 Играть")
async def game(m):
    ensure(m.from_user); a,b=random.randint(2,12),random.randint(2,12); ans=a*b
    pending[m.from_user.id]={"answer":ans}
    options=list({ans, max(1,ans+random.choice([-5,-3,2,4])),max(1,ans+random.choice([-4,-2,3,5]))})
    random.shuffle(options)
    await m.answer(f"🎮 <b>Мини-игра</b>\nСколько будет {a} × {b}?\nЗа правильный ответ начисляется 10 ⭐. Попытка бесплатная.",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(x),callback_data=f"ans:{x}") for x in options]]),parse_mode="HTML")

@dp.callback_query(F.data.startswith("ans:"))
async def answer(q):
    state=pending.pop(q.from_user.id,None)
    if not state: await q.answer("Начни новую игру.",show_alert=True); return
    val=int(q.data.split(":")[1]); ok=val==state["answer"]
    with connect() as c:
        c.execute("UPDATE users SET games=games+1 WHERE id=?",(q.from_user.id,))
        if ok: c.execute("UPDATE users SET balance=balance+10,wins=wins+1 WHERE id=?",(q.from_user.id,))
    await q.message.edit_text("✅ Верно! Начислено 10 ⭐." if ok else f"❌ Неверно. Ответ: {state['answer']}.")
    await q.answer()

@dp.callback_query(F.data=="promo")
async def promo_begin(q):
    pending[q.from_user.id]={"promo":True}; await q.message.answer("Отправь название промокода одним сообщением."); await q.answer()

async def redeem(m,code):
    code=code.strip().upper(); uid=m.from_user.id
    with connect() as c:
        p=c.execute("SELECT * FROM promos WHERE code=?",(code,)).fetchone()
        if not p: await m.answer("❌ Промокод не найден."); return
        if p["uses"]>=p["limit_uses"]: await m.answer("❌ Лимит активаций исчерпан."); return
        if c.execute("SELECT 1 FROM promo_users WHERE code=? AND user_id=?",(code,uid)).fetchone():
            await m.answer("❌ Ты уже активировал этот промокод."); return
        c.execute("INSERT INTO promo_users VALUES(?,?)",(code,uid)); c.execute("UPDATE promos SET uses=uses+1 WHERE code=?",(code,))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?",(p["reward"],uid))
    pending.pop(uid,None); await m.answer(f"✅ Промокод активирован! +{p['reward']} ⭐")

@dp.message(Command("promo"))
async def promo_cmd(m):
    args=m.text.split(maxsplit=1)
    if len(args)>1: await redeem(m,args[1])
    else: pending[m.from_user.id]={"promo":True}; await m.answer("Отправь название промокода.")

@dp.message(Command("admin"))
async def admin(m):
    if m.from_user.id not in ADMIN_IDS: await m.answer("⛔ Нет доступа."); return
    await m.answer("🛠 <b>StarFun — админ-панель</b>\n\n/give ID СУММА\n/newpromo КОД НАГРАДА ЛИМИТ\n/setmin СУММА",reply_markup=admin_kb(),parse_mode="HTML")

@dp.callback_query(F.data.in_({"givehelp","promohelp","minhelp","stats"}))
async def admin_buttons(q):
    if q.from_user.id not in ADMIN_IDS: await q.answer("Нет доступа",show_alert=True); return
    if q.data=="givehelp": msg="Формат: /give ID СУММА"
    elif q.data=="promohelp": msg="Формат: /newpromo КОД НАГРАДА ЛИМИТ"
    elif q.data=="minhelp": msg="Формат: /setmin СУММА"
    else:
        with connect() as c:
            n=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]; bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM users").fetchone()[0]
        msg=f"📊 Пользователей: {n}\nСуммарный игровой баланс: {bal} ⭐"
    await q.message.answer(msg); await q.answer()

@dp.message(Command("give"))
async def give(m):
    if m.from_user.id not in ADMIN_IDS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=3 or not a[1].isdigit() or not a[2].isdigit() or int(a[2])<1: await m.answer("Формат: /give ID СУММА"); return
    if not get_user(int(a[1])): await m.answer("Пользователь должен сначала нажать /start."); return
    with connect() as c: c.execute("UPDATE users SET balance=balance+? WHERE id=?",(int(a[2]),int(a[1])))
    await m.answer(f"✅ Начислено {a[2]} ⭐ игрового баланса.")

@dp.message(Command("newpromo"))
async def newpromo(m):
    if m.from_user.id not in ADMIN_IDS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=4 or not a[2].isdigit() or not a[3].isdigit() or int(a[2])<1 or int(a[3])<1:
        await m.answer("Формат: /newpromo КОД НАГРАДА ЛИМИТ"); return
    try:
        with connect() as c: c.execute("INSERT INTO promos(code,reward,limit_uses) VALUES(?,?,?)",(a[1].upper(),int(a[2]),int(a[3])))
        await m.answer(f"✅ Промокод {a[1].upper()} создан. Награда: {a[2]} ⭐, активаций: {a[3]}.")
    except sqlite3.IntegrityError: await m.answer("Такой промокод уже существует.")

@dp.message(Command("setmin"))
async def setmin(m):
    if m.from_user.id not in ADMIN_IDS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=2 or not a[1].isdigit(): await m.answer("Формат: /setmin СУММА"); return
    with connect() as c: c.execute("INSERT INTO settings VALUES('min_exchange',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(a[1],))
    await m.answer(f"✅ Минимальный порог обмена установлен: {a[1]} ⭐.")

@dp.message(Command("help"))
async def help_cmd(m):
    await m.answer("/start — меню\n/profile — профиль\n/game — мини-игра\n/promo — промокод\n/admin — админ-панель")

@dp.message()
async def fallback(m):
    state=pending.get(m.from_user.id)
    if state and state.get("promo"): await redeem(m,m.text or ""); return
    await m.answer("Выбери раздел в меню.",reply_markup=menu())

async def main():
    init_db()
    print("StarFun started")
    await dp.start_polling(bot)

if __name__=="__main__": asyncio.run(main())
