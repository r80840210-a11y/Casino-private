import asyncio, os, sqlite3, random
from html import escape
from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN=os.getenv("BOT_TOKEN","").strip()
API_BASE=os.getenv("API_BASE","http://67.211.221.152:8888").rstrip("/")
DB=os.getenv("DB_PATH","starfun.db")
ADMINS={int(x) for x in os.getenv("ADMIN_IDS","1780243264").split(",") if x.strip().isdigit()}
SUPPORT=os.getenv("SUPPORT_USERNAME","v1nk_molik").lstrip("@")
if not TOKEN: raise RuntimeError("Set BOT_TOKEN in Render Environment.")

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with conn() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,username TEXT,balance INTEGER DEFAULT 0,games INTEGER DEFAULT 0,wins INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY,reward INTEGER,limit_uses INTEGER,uses INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS promo_users(code TEXT,user_id INTEGER,PRIMARY KEY(code,user_id));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        INSERT OR IGNORE INTO settings VALUES('min_exchange','100');""")
def ensure(u):
    with conn() as c: c.execute("INSERT INTO users(id,name,username,balance) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET name=excluded.name,username=excluded.username",(u.id,u.full_name,u.username or ""))
def get(uid):
    with conn() as c: return c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
def menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎮 Играть"),KeyboardButton(text="👤 Профиль")],[KeyboardButton(text="⭐ Пополнить баланс")]],resize_keyboard=True)
def upgrades():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="50 ⭐",callback_data="amt:50"),InlineKeyboardButton(text="100 ⭐",callback_data="amt:100")],[InlineKeyboardButton(text="150 ⭐",callback_data="amt:150"),InlineKeyboardButton(text="200 ⭐",callback_data="amt:200")],[InlineKeyboardButton(text="✍️ Своя сумма",callback_data="amt:custom")]])
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Создать промокод",callback_data="adm:promo")],[InlineKeyboardButton(text="➕ Начислить игровой баланс",callback_data="adm:give")],[InlineKeyboardButton(text="📊 Статистика",callback_data="adm:stats")],[InlineKeyboardButton(text="⚙️ Минимум обмена",callback_data="adm:min")]])
bot=Bot(TOKEN,session=AiohttpSession(api=TelegramAPIServer.from_base(API_BASE)))
dp=Dispatcher(); pending={}

@dp.message(CommandStart())
async def start(m):
    ensure(m.from_user); u=get(m.from_user.id)
    await m.answer(f"⭐ <b>StarFun</b>\n\nДобро пожаловать в казино звёзд! ⭐\n💰 Баланс: <b>{u['balance']} ⭐</b>",reply_markup=menu(),parse_mode="HTML")

@dp.message(F.text=="🎮 Играть")
@dp.message(Command("game"))
async def game(m):
    ensure(m.from_user)
    await m.answer("⭐ <b>АПГРЕЙДЕР</b>\nВыбери сумму бесплатной игровой попытки. При успехе награда ×1,5. За неудачу баланс не списывается.",reply_markup=upgrades(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("amt:"))
async def amount(q):
    v=q.data.split(":")[1]
    if v=="custom":
        pending[q.from_user.id]={"type":"custom"}; await q.message.answer("Введи целое число от 1 до 10000."); await q.answer(); return
    await offer(q,int(v))

async def offer(q,n):
    pending[q.from_user.id]={"type":"upgrade","amount":n}
    await q.message.answer(f"⭐ <b>Апгрейдер</b>\nВыбрано: {n} ⭐\nНаграда при успехе: {int(n*1.5)} ⭐\nПопытка бесплатная.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Апгрейд",callback_data="upgrade")],[InlineKeyboardButton(text="↩️ Выбрать сумму",callback_data="back")]]),parse_mode="HTML")
    await q.answer()

@dp.callback_query(F.data=="back")
async def back(q):
    await q.message.answer("Выбери сумму:",reply_markup=upgrades()); await q.answer()

@dp.callback_query(F.data=="upgrade")
async def upgrade(q):
    s=pending.pop(q.from_user.id,None)
    if not s or s.get("type")!="upgrade": await q.answer("Сначала выбери сумму.",show_alert=True); return
    n=s["amount"]; won=random.random()<0.30
    with conn() as c:
        c.execute("UPDATE users SET games=games+1 WHERE id=?",(q.from_user.id,))
        if won: c.execute("UPDATE users SET balance=balance+?,wins=wins+1 WHERE id=?",(int(n*1.5),q.from_user.id))
    await q.message.edit_text(f"🎉 <b>АПГРЕЙД УСПЕШЕН!</b>\nНаграда: +{int(n*1.5)} ⭐" if won else "💫 <b>Апгрейд не прошёл.</b> Это бесплатная попытка — баланс не уменьшился.",parse_mode="HTML")
    await q.answer()

@dp.message(F.text=="👤 Профиль")
@dp.message(Command("profile"))
async def profile(m):
    ensure(m.from_user); u=get(m.from_user.id)
    await m.answer(f"👤 <b>Профиль StarFun</b>\nИмя: {escape(u['name'] or '')}\nUsername: @{escape(u['username'] or 'не указан')}\nID: <code>{u['id']}</code>\n💰 Баланс: <b>{u['balance']} ⭐</b>\n🎮 Попыток: {u['games']}\n🏆 Успехов: {u['wins']}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Активировать промокод",callback_data="promo")]]),parse_mode="HTML")

@dp.message(F.text=="⭐ Пополнить баланс")
async def topup(m):
    await m.answer(f"По вопросам игрового баланса напиши администратору @{escape(SUPPORT)}.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Написать администратору",url=f"https://t.me/{SUPPORT}")]]))

@dp.callback_query(F.data=="promo")
async def promo(q):
    pending[q.from_user.id]={"type":"promo"}; await q.message.answer("Отправь код промокода одним сообщением."); await q.answer()

async def redeem(m,code):
    code=code.strip().upper(); uid=m.from_user.id
    with conn() as c:
        p=c.execute("SELECT * FROM promos WHERE code=?",(code,)).fetchone()
        if not p: await m.answer("❌ Промокод не найден."); return
        if p["uses"]>=p["limit_uses"]: await m.answer("❌ Лимит активаций исчерпан."); return
        if c.execute("SELECT 1 FROM promo_users WHERE code=? AND user_id=?",(code,uid)).fetchone(): await m.answer("❌ Уже активирован."); return
        c.execute("INSERT INTO promo_users VALUES(?,?)",(code,uid)); c.execute("UPDATE promos SET uses=uses+1 WHERE code=?",(code,)); c.execute("UPDATE users SET balance=balance+? WHERE id=?",(p["reward"],uid))
    pending.pop(uid,None); await m.answer(f"✅ Начислено {p['reward']} ⭐ игрового баланса.")

@dp.message(Command("promo"))
async def promo_cmd(m):
    a=m.text.split(maxsplit=1)
    if len(a)>1: await redeem(m,a[1])
    else: pending[m.from_user.id]={"type":"promo"}; await m.answer("Отправь код промокода.")

@dp.message(Command("admin"))
async def admin(m):
    if m.from_user.id not in ADMINS: await m.answer("⛔ Нет доступа."); return
    await m.answer("🛠 <b>StarFun — админ-панель</b>\n/give ID СУММА\n/newpromo КОД НАГРАДА ЛИМИТ\n/setmin СУММА",reply_markup=admin_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm:"))
async def adm(q):
    if q.from_user.id not in ADMINS: await q.answer("Нет доступа",show_alert=True); return
    action=q.data.split(":")[1]
    if action=="promo": msg="Формат: /newpromo КОД НАГРАДА ЛИМИТ"
    elif action=="give": msg="Формат: /give ID СУММА"
    elif action=="min": msg="Формат: /setmin СУММА"
    else:
        with conn() as c: users=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]; bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM users").fetchone()[0]
        msg=f"📊 Пользователей: {users}\nСуммарный игровой баланс: {bal} ⭐"
    await q.message.answer(msg); await q.answer()

@dp.message(Command("give"))
async def give(m):
    if m.from_user.id not in ADMINS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=3 or not a[1].isdigit() or not a[2].isdigit() or int(a[2])<1: await m.answer("Формат: /give ID СУММА"); return
    if not get(int(a[1])): await m.answer("Пользователь должен сначала нажать /start."); return
    with conn() as c: c.execute("UPDATE users SET balance=balance+? WHERE id=?",(int(a[2]),int(a[1])))
    await m.answer("✅ Игровой баланс начислен.")

@dp.message(Command("newpromo"))
async def newpromo(m):
    if m.from_user.id not in ADMINS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=4 or not a[2].isdigit() or not a[3].isdigit() or int(a[2])<1 or int(a[3])<1: await m.answer("Формат: /newpromo КОД НАГРАДА ЛИМИТ"); return
    try:
        with conn() as c: c.execute("INSERT INTO promos(code,reward,limit_uses) VALUES(?,?,?)",(a[1].upper(),int(a[2]),int(a[3])))
        await m.answer(f"✅ Промокод {escape(a[1].upper())} создан.")
    except sqlite3.IntegrityError: await m.answer("Такой промокод уже есть.")

@dp.message(Command("setmin"))
async def setmin(m):
    if m.from_user.id not in ADMINS: await m.answer("⛔ Нет доступа."); return
    a=m.text.split()
    if len(a)!=2 or not a[1].isdigit(): await m.answer("Формат: /setmin СУММА"); return
    with conn() as c: c.execute("INSERT INTO settings VALUES('min_exchange',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(a[1],))
    await m.answer(f"✅ Порог установлен: {a[1]} ⭐.")

@dp.message(Command("help"))
async def help_cmd(m):
    await m.answer("/start — меню\n/game — апгрейдер\n/profile — профиль\n/promo — промокод\n/admin — админ-панель")

@dp.message()
async def fallback(m):
    s=pending.get(m.from_user.id)
    if s and s.get("type")=="promo": await redeem(m,m.text or ""); return
    if s and s.get("type")=="custom":
        t=(m.text or "").strip()
        if t.isdigit() and 1<=int(t)<=10000: await offer_from_message(m,int(t))
        else: await m.answer("Введи число от 1 до 10000.")
        return
    await m.answer("Выбери раздел в меню.",reply_markup=menu())

async def offer_from_message(m,n):
    pending[m.from_user.id]={"type":"upgrade","amount":n}
    await m.answer(f"⭐ Выбрано: {n} ⭐\nНаграда при успехе: {int(n*1.5)} ⭐\nПопытка бесплатная.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Апгрейд",callback_data="upgrade")],[InlineKeyboardButton(text="↩️ Выбрать сумму",callback_data="back")]]))

async def main():
    init(); print("StarFun started"); await dp.start_polling(bot)
if __name__=="__main__": asyncio.run(main())
