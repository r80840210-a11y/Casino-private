from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards import profile_keyboard, back_keyboard, cancel_keyboard

router = Router()

class PromoStates(StatesGroup):
    waiting_code = State()

class WithdrawStates(StatesGroup):
    waiting_amount = State()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    user = db.get_user(user_id)
    stats = db.get_user_stats(user_id)

    games = stats['games'] or 0
    wins = stats['wins'] or 0
    losses = stats['losses'] or 0
    won_stars = stats['won_stars'] or 0
    lost_stars = stats['lost_stars'] or 0

    winrate = (wins / games * 100) if games > 0 else 0

    username = f"@{user['username']}" if user['username'] else "нет"

    await callback.message.edit_text(
        f"👤 <b>ПРОФИЛЬ</b>

"
        f"🆔 ID: <code>{user_id}</code>
"
        f"👤 Ник: {username}
"
        f"📛 Имя: {user['first_name'] or 'нет'}

"
        f"💰 Баланс: <b>{user['balance']} ⭐</b>

"
        f"📊 <b>СТАТИСТИКА:</b>
"
        f"🎮 Всего игр: {games}
"
        f"✅ Побед: {wins}
"
        f"❌ Поражений: {losses}
"
        f"📈 Винрейт: {winrate:.1f}%

"
        f"💎 Всего выиграно: {won_stars} ⭐
"
        f"📉 Всего проиграно: {lost_stars} ⭐",
        reply_markup=profile_keyboard()
    )

@router.callback_query(F.data == "withdraw")
async def start_withdraw(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    balance = db.get_balance(user_id)
    min_withdraw = db.get_min_withdraw()

    if balance < min_withdraw:
        await callback.answer(
            f"❌ Минимальная сумма вывода: {min_withdraw} ⭐
"
            f"💰 Твой баланс: {balance} ⭐",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"💸 <b>ВЫВОД ЗВЕЗД</b>

"
        f"💰 Баланс: {balance} ⭐
"
        f"📉 Мин. вывод: {min_withdraw} ⭐

"
        f"Введи сумму для вывода:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(WithdrawStates.waiting_amount)

@router.message(WithdrawStates.waiting_amount)
async def process_withdraw(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if db.is_banned(user_id):
        await message.answer("🚫 Вы заблокированы!")
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount < 1:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    balance = db.get_balance(user_id)
    min_withdraw = db.get_min_withdraw()

    if amount < min_withdraw:
        await message.answer(
            f"❌ Минимальная сумма вывода: {min_withdraw} ⭐
"
            f"Попробуй еще раз:",
            reply_markup=cancel_keyboard()
        )
        return

    if amount > balance:
        await message.answer(
            f"❌ Недостаточно звезд!
"
            f"💰 Баланс: {balance} ⭐
"
            f"📉 Запросил: {amount} ⭐

"
            f"Попробуй еще раз:",
            reply_markup=cancel_keyboard()
        )
        return

    # Списываем
    db.update_balance(user_id, -amount)
    new_balance = db.get_balance(user_id)

    await message.answer(
        f"✅ <b>ЗАЯВКА НА ВЫВОД СОЗДАНА!</b>

"
        f"💸 Сумма: {amount} ⭐
"
        f"💰 Остаток: {new_balance} ⭐

"
        f"📱 Для получения звезд напиши: @v1nk_molik
"
        f"🆔 Укажи свой ID: <code>{user_id}</code>",
        reply_markup=back_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "activate_promo")
async def start_activate_promo(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🎁 <b>АКТИВАЦИЯ ПРОМОКОДА</b>

"
        f"Введи промокод:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PromoStates.waiting_code)

@router.message(PromoStates.waiting_code)
async def process_promo(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if db.is_banned(user_id):
        await message.answer("🚫 Вы заблокированы!")
        await state.clear()
        return

    code = message.text.strip().upper()
    promo = db.get_promo(code)

    if not promo:
        await message.answer(
            f"❌ Промокод не найден или неактивен!
"
            f"Попробуй еще раз:",
            reply_markup=cancel_keyboard()
        )
        return

    success, result = db.activate_promo(user_id, promo['id'])

    if success:
        new_balance = db.get_balance(user_id)
        await message.answer(
            f"🎉 <b>ПРОМОКОД АКТИВИРОВАН!</b>

"
            f"🎁 Код: <code>{code}</code>
"
            f"💎 Получено: +{result} ⭐
"
            f"💰 Баланс: {new_balance} ⭐",
            reply_markup=back_keyboard()
        )
        await state.clear()
    else:
        if result == "already_activated":
            text = "❌ Ты уже активировал этот промокод!"
        elif result == "limit_reached":
            text = "❌ Лимит активаций исчерпан!"
        else:
            text = "❌ Ошибка активации!"

        await message.answer(text, reply_markup=back_keyboard())
        await state.clear()
