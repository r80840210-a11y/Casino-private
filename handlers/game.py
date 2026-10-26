from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random

from database import db
from keyboards import back_keyboard, cancel_keyboard
from config import HOUSE_EDGE, MIN_BET

router = Router()

class GameStates(StatesGroup):
    waiting_bet = State()

@router.callback_query(F.data == "upgrade")
async def start_upgrade(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    balance = db.get_balance(user_id)

    await callback.message.edit_text(
        f"🎰 <b>АПГРЕЙД ЗВЕЗД</b>

"
        f"💰 Твой баланс: <b>{balance} ⭐</b>

"
        f"📝 Введи сумму ставки (мин. {MIN_BET} ⭐):

"
        f"🎯 Шанс победы: ~35%
"
        f"💎 При выигрыше: <b>x1.5</b> от ставки
"
        f"💀 При проигрыше: теряешь ставку",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(GameStates.waiting_bet)

@router.message(GameStates.waiting_bet)
async def process_bet(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if db.is_banned(user_id):
        await message.answer("🚫 Вы заблокированы!")
        await state.clear()
        return

    try:
        bet = int(message.text.strip())
        if bet < MIN_BET:
            await message.answer(f"❌ Минимальная ставка: {MIN_BET} ⭐
Попробуй еще раз:", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!
Попробуй еще раз:", reply_markup=cancel_keyboard())
        return

    balance = db.get_balance(user_id)

    if bet > balance:
        await message.answer(
            f"❌ Недостаточно звезд!
"
            f"💰 Баланс: {balance} ⭐
"
            f"💳 Нужно: {bet} ⭐

"
            f"Пополни баланс или уменьши ставку.",
            reply_markup=back_keyboard()
        )
        await state.clear()
        return

    # Списываем ставку
    db.update_balance(user_id, -bet)

    # Крутим (65% проигрыш)
    win = random.random() > HOUSE_EDGE

    if win:
        win_amount = int(bet * 1.5)
        db.update_balance(user_id, win_amount)
        db.add_win(user_id, win_amount - bet)
        db.add_game_history(user_id, bet, 'win', win_amount)

        new_balance = db.get_balance(user_id)

        await message.answer(
            f"🎉 <b>ПОБЕДА!</b>

"
            f"💰 Ставка: {bet} ⭐
"
            f"💎 Выигрыш: +{win_amount - bet} ⭐
"
            f"💵 Новый баланс: {new_balance} ⭐

"
            f"Хочешь еще раз?",
            reply_markup=back_keyboard()
        )
    else:
        db.add_loss(user_id, bet)
        db.add_game_history(user_id, bet, 'loss', 0)

        new_balance = db.get_balance(user_id)

        await message.answer(
            f"💀 <b>ПРОИГРЫШ!</b>

"
            f"💰 Ставка: {bet} ⭐
"
            f"📉 Потерял: -{bet} ⭐
"
            f"💵 Баланс: {new_balance} ⭐

"
            f"Попробуешь еще?",
            reply_markup=back_keyboard()
        )

    await state.clear()

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f"🎰 <b>Stars Casino</b>

"
        f"💰 Твой баланс: <b>{db.get_balance(user_id)} ⭐</b>

"
        f"Выбери действие:",
        reply_markup=main_menu_keyboard()
    )
