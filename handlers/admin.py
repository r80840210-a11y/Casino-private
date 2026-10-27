from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

from database import db
from keyboards import admin_keyboard, admin_back_keyboard, cancel_keyboard, main_menu_keyboard
from config import MAIN_ADMIN_ID

router = Router()

# ==================== STATES ====================
class AdminStates(StatesGroup):
    waiting_admin_id_add = State()
    waiting_admin_id_remove = State()
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_give_id = State()
    waiting_give_amount = State()
    waiting_take_id = State()
    waiting_take_amount = State()
    waiting_promo_code = State()
    waiting_promo_stars = State()
    waiting_promo_activations = State()
    waiting_broadcast = State()
    waiting_min_withdraw = State()

# ==================== ПРОВЕРКА АДМИНА ====================
def is_admin(user_id):
    return db.is_admin(user_id)

# ==================== АДМИН ПАНЕЛЬ ====================
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У тебя нет доступа!")
        return

    stats = db.get_stats()

    await message.answer(
        f"👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🔨 Забанено: {stats['banned']}\n"
        f"👑 Админов: {stats['admins']}\n"
        f"🎮 Всего игр: {stats['total_games']}\n"
        f"💰 Всего звезд в боте: {stats['total_stars']} ⭐\n"
        f"🎁 Активных промокодов: {stats['active_promos']}\n\n"
        f"Выбери действие:",
        reply_markup=admin_keyboard()
    )

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    stats = db.get_stats()

    await callback.message.edit_text(
        f"👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🔨 Забанено: {stats['banned']}\n"
        f"👑 Админов: {stats['admins']}\n"
        f"🎮 Всего игр: {stats['total_games']}\n"
        f"💰 Всего звезд в боте: {stats['total_stars']} ⭐\n"
        f"🎁 Активных промокодов: {stats['active_promos']}\n\n"
        f"Выбери действие:",
        reply_markup=admin_keyboard()
    )

# ==================== ДОБАВИТЬ АДМИНА ====================
@router.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "➕ <b>ДОБАВИТЬ АДМИНА</b>\n\n"
        "Введи ID пользователя:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_admin_id_add)

@router.message(AdminStates.waiting_admin_id_add)
async def admin_add_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    db.add_admin(user_id)

    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> теперь админ!",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== УДАЛИТЬ АДМИНА ====================
@router.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    admins = db.get_all_admins()
    admins_text = "\n".join([f"• <code>{a['user_id']}</code> (@{a['username'] or 'нет'})" for a in admins])

    await callback.message.edit_text(
        f"➖ <b>УДАЛИТЬ АДМИНА</b>\n\n"
        f"Текущие админы:\n{admins_text}\n\n"
        f"Введи ID админа для удаления:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_admin_id_remove)

@router.message(AdminStates.waiting_admin_id_remove)
async def admin_remove_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    if user_id == MAIN_ADMIN_ID:
        await message.answer("❌ Нельзя удалить главного админа!", reply_markup=admin_back_keyboard())
        await state.clear()
        return

    db.remove_admin(user_id)

    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> больше не админ!",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== ЗАБАНИТЬ ====================
@router.callback_query(F.data == "admin_ban")
async def admin_ban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "🔨 <b>ЗАБАНИТЬ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        "Введи ID пользователя:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_ban_id)

@router.message(AdminStates.waiting_ban_id)
async def admin_ban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    if user_id == MAIN_ADMIN_ID:
        await message.answer("❌ Нельзя забанить главного админа!", reply_markup=admin_back_keyboard())
        await state.clear()
        return

    db.ban_user(user_id)

    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> забанен!",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== РАЗБАНИТЬ ====================
@router.callback_query(F.data == "admin_unban")
async def admin_unban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "🔓 <b>РАЗБАНИТЬ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        "Введи ID пользователя:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_unban_id)

@router.message(AdminStates.waiting_unban_id)
async def admin_unban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    db.unban_user(user_id)

    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> разбанен!",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== ВЫДАТЬ ЗВЕЗДЫ ====================
@router.callback_query(F.data == "admin_give")
async def admin_give_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "💰 <b>ВЫДАТЬ ЗВЕЗДЫ</b>\n\n"
        "Введи ID пользователя:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_give_id)

@router.message(AdminStates.waiting_give_id)
async def admin_give_id_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден в базе!", reply_markup=admin_back_keyboard())
        await state.clear()
        return

    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"💰 Выдача звезд пользователю <code>{user_id}</code>\n"
        f"💵 Текущий баланс: {user['balance']} ⭐\n\n"
        f"Введи количество звезд:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_give_amount)

@router.message(AdminStates.waiting_give_amount)
async def admin_give_amount_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    user_id = data['target_user_id']

    db.update_balance(user_id, amount)
    new_balance = db.get_balance(user_id)

    await message.answer(
        f"✅ Выдано <b>{amount} ⭐</b> пользователю <code>{user_id}</code>\n"
        f"💵 Новый баланс: {new_balance} ⭐",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== ЗАБРАТЬ ЗВЕЗДЫ ====================
@router.callback_query(F.data == "admin_take")
async def admin_take_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "💸 <b>ЗАБРАТЬ ЗВЕЗДЫ</b>\n\n"
        "Введи ID пользователя:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_take_id)

@router.message(AdminStates.waiting_take_id)
async def admin_take_id_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID!", reply_markup=cancel_keyboard())
        return

    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден в базе!", reply_markup=admin_back_keyboard())
        await state.clear()
        return

    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"💸 Забор звезд у пользователя <code>{user_id}</code>\n"
        f"💵 Текущий баланс: {user['balance']} ⭐\n\n"
        f"Введи количество звезд для забора:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_take_amount)

@router.message(AdminStates.waiting_take_amount)
async def admin_take_amount_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    user_id = data['target_user_id']

    balance = db.get_balance(user_id)
    actual_take = min(amount, balance)

    db.update_balance(user_id, -actual_take)
    new_balance = db.get_balance(user_id)

    await message.answer(
        f"✅ Забрано <b>{actual_take} ⭐</b> у пользователя <code>{user_id}</code>\n"
        f"💵 Новый баланс: {new_balance} ⭐",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== СОЗДАТЬ ПРОМОКОД ====================
@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "🎁 <b>СОЗДАТЬ ПРОМОКОД</b>\n\n"
        "Введи название промокода (только латиница и цифры):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_promo_code)

@router.message(AdminStates.waiting_promo_code)
async def admin_promo_code_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    code = message.text.strip().upper()

    if not code.isalnum():
        await message.answer("❌ Только латиница и цифры!", reply_markup=cancel_keyboard())
        return

    await state.update_data(promo_code=code)
    await message.answer(
        f"🎁 Промокод: <code>{code}</code>\n\n"
        f"Введи количество звезд:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_promo_stars)

@router.message(AdminStates.waiting_promo_stars)
async def admin_promo_stars_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        stars = int(message.text.strip())
        if stars <= 0:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    await state.update_data(promo_stars=stars)
    await message.answer(
        f"💎 Звезд: {stars}\n\n"
        f"Введи количество активаций:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_promo_activations)

@router.message(AdminStates.waiting_promo_activations)
async def admin_promo_activations_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        activations = int(message.text.strip())
        if activations <= 0:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    code = data['promo_code']
    stars = data['promo_stars']

    success = db.create_promo(code, stars, activations, message.from_user.id)

    if success:
        await message.answer(
            f"✅ <b>ПРОМОКОД СОЗДАН!</b>\n\n"
            f"🎁 Код: <code>{code}</code>\n"
            f"💎 Звезд: {stars} ⭐\n"
            f"🔢 Активаций: {activations}",
            reply_markup=admin_back_keyboard()
        )
    else:
        await message.answer(
            f"❌ Промокод <code>{code}</code> уже существует!",
            reply_markup=admin_back_keyboard()
        )

    await state.clear()

# ==================== СПИСОК ПРОМОКОДОВ ====================
@router.callback_query(F.data == "admin_list_promos")
async def admin_list_promos(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    promos = db.get_all_promos()

    if not promos:
        text = "📋 Промокодов нет."
    else:
        text = "📋 <b>СПИСОК ПРОМОКОДОВ:</b>\n\n"
        for p in promos[:20]:
            status = "✅" if p['is_active'] else "❌"
            text += (
                f"{status} <code>{p['code']}</code>\n"
                f"   💎 {p['stars']} ⭐ | 🔢 {p['current_activations']}/{p['max_activations']}\n\n"
            )

    await callback.message.edit_text(text, reply_markup=admin_back_keyboard())

# ==================== РАССЫЛКА ====================
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>РАССЫЛКА</b>\n\n"
        "Отправь сообщение для рассылки всем пользователям:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_broadcast)

@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_process(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    users = db.get_all_users()
    total = len(users)
    success = 0
    failed = 0

    status_msg = await message.answer(f"📢 Начинаю рассылку на {total} пользователей...")

    for user in users:
        try:
            await bot.copy_message(
                chat_id=user['user_id'],
                from_chat_id=message.from_user.id,
                message_id=message.message_id
            )
            success += 1
        except:
            failed += 1

        await asyncio.sleep(0.05)  # Задержка чтобы не спамить

    db.add_broadcast(message.text or "media", message.from_user.id, total, success, failed)

    await status_msg.edit_text(
        f"✅ <b>РАССЫЛКА ЗАВЕРШЕНА!</b>\n\n"
        f"📊 Всего пользователей: {total}\n"
        f"✅ Доставлено: {success}\n"
        f"❌ Не доставлено: {failed}",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== МИН. ВЫВОД ====================
@router.callback_query(F.data == "admin_min_withdraw")
async def admin_min_withdraw_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    current = db.get_min_withdraw()

    await callback.message.edit_text(
        f"⚙️ <b>МИНИМАЛЬНЫЙ ВЫВОД</b>\n\n"
        f"Текущее значение: {current} ⭐\n\n"
        f"Введи новое значение:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_min_withdraw)

@router.message(AdminStates.waiting_min_withdraw)
async def admin_min_withdraw_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount < 0:
            await message.answer("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_keyboard())
        return

    db.set_setting('min_withdraw', amount)

    await message.answer(
        f"✅ Минимальный вывод установлен: {amount} ⭐",
        reply_markup=admin_back_keyboard()
    )
    await state.clear()

# ==================== СТАТИСТИКА ====================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return

    stats = db.get_stats()

    await callback.message.edit_text(
        f"📊 <b>ПОЛНАЯ СТАТИСТИКА</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🔨 Забанено: {stats['banned']}\n"
        f"👑 Админов: {stats['admins']}\n"
        f"🎮 Всего игр: {stats['total_games']}\n"
        f"💰 Всего звезд в боте: {stats['total_stars']} ⭐\n"
        f"🎁 Активных промокодов: {stats['active_promos']}",
        reply_markup=admin_back_keyboard()
    )

# ==================== ОТМЕНА ====================
@router.callback_query(F.data == "cancel_action")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    if is_admin(callback.from_user.id):
        await callback.message.edit_text(
            "👑 <b>АДМИН ПАНЕЛЬ</b>",
            reply_markup=admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "🎰 <b>Stars Casino</b>",
            reply_markup=main_menu_keyboard()
        )
