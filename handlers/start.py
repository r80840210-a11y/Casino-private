from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from database import db
from keyboards import main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Добавляем пользователя
    db.add_user(user_id, username, first_name)

    # Проверяем бан
    if db.is_banned(user_id):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return

    await message.answer(
        f"👋 Привет, {first_name}!\n\n"
        f"🎰 Добро пожаловать в Stars Casino!\n\n"
        f"💰 Твой баланс: <b>{db.get_balance(user_id)} ⭐</b>\n\n"
        f"Выбери действие:",
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🎰 <b>Stars Casino</b>\n\n"
        f"💰 Твой баланс: <b>{db.get_balance(user_id)} ⭐</b>\n\n"
        f"Выбери действие:",
        reply_markup=main_menu_keyboard()
    )
