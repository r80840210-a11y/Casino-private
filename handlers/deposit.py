from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import db
from keyboards import deposit_keyboard

router = Router()

@router.callback_query(F.data == "deposit")
async def show_deposit(callback: CallbackQuery):
    user_id = callback.from_user.id

    if db.is_banned(user_id):
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return

    await callback.message.edit_text(
        f"💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n\n"
        f"Чтобы пополнить баланс звездами:\n\n"
        f"1️⃣ Напиши нашему оператору: <b>@v1nk_molik</b>\n"
        f"2️⃣ Укажи сколько звезд хочешь внести\n"
        f"3️⃣ Переведи звезды оператору\n"
        f"4️⃣ Получишь звезды на баланс в боте\n\n"
        f"💰 Текущий баланс: <b>{db.get_balance(user_id)} ⭐</b>",
        reply_markup=deposit_keyboard()
    )
