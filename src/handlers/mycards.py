from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from utils.api import request, unwrap
from utils.redis_client import get_customer_id
from utils.keyboards import login_inline_kb
from utils.qr import make_qr_input_file

router = Router()


# ===== Helper для прогресса =====
def make_progress_bar(current: int, total: int) -> str:
    if not isinstance(current, int) or not isinstance(total, int) or total <= 0:
        return "—"
    current = max(0, min(current, total))
    filled = "🔘" * current
    empty = "⚪" * (total - current)
    return f"{filled}{empty} ({current}/{total})"


# ===== Универсальная функция для вывода карточек =====
async def mycards_cmd(message: Message):
    customer_id = await get_customer_id(message.chat.id)
    if not customer_id:
        await message.answer("ℹ️ Сначала войдите.", reply_markup=login_inline_kb())
        return

    status, payload = await request(
        message.chat.id, "GET", f"/customers/{customer_id}/cards/", params={"limit": 100, "offset": 0}
    )
    if status == 403:
        await message.answer("🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        return
    if status != 200:
        await message.answer(f"❌ Не удалось получить список карточек (status={status}).")
        return

    cards = unwrap(payload, as_list=True) or []

    if not cards:
        await message.answer("📭 У вас пока нет карточек.")
        return

    for c in cards:
        cid = c.get("id")
        card_name = c.get("name", "—")
        reward_name = c.get("reward_name") or "Награда"
        current = c.get("current_stamp_count")
        total = c.get("total_stamp_count")

        bar = make_progress_bar(current, total)

        filled = (
            isinstance(current, int)
            and isinstance(total, int)
            and total > 0
            and current >= total
        )

        if filled:
            # Сообщение о награде
            text = f"🏆 <b>{reward_name}</b>\nКарта: {card_name}\nПрогресс: {bar}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"🎁 {reward_name}",
                    callback_data=f"qr:redeem:{cid}"
                )
            ]])
        else:
            # Сообщение о карте
            text = f"🎴 <b>{card_name}</b>\nПрогресс: {bar}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"📲 {card_name}",
                    callback_data=f"qr:stamp:{cid}"
                )
            ]])

        await message.answer(text, reply_markup=kb)


# ===== Команда /mycards =====
@router.message(Command("mycards"))
async def mycards_command_entry(message: Message):
    await mycards_cmd(message)


# ===== Коллбэк открытия карты =====
@router.callback_query(F.data.startswith("card:open:"))
async def open_card(cb: CallbackQuery):
    try:
        _, _, card_id = cb.data.split(":", 2)
    except Exception:
        await cb.answer("Некорректные данные", show_alert=True)
        return

    customer_id = await get_customer_id(cb.message.chat.id)
    if not customer_id:
        await cb.message.answer("ℹ️ Сначала войдите.", reply_markup=login_inline_kb())
        await cb.answer()
        return

    status, payload = await request(cb.message.chat.id, "GET", f"/customers/{customer_id}/cards/{card_id}")
    if status == 403:
        await cb.message.answer("🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        await cb.answer()
        return
    if status != 200:
        await cb.message.answer("❌ Не удалось загрузить карточку.")
        await cb.answer()
        return

    card = unwrap(payload) or {}
    card_name = card.get("name", "—")
    reward_name = card.get("reward_name") or "Награда"
    current = card.get("current_stamp_count")
    total = card.get("total_stamp_count")

    bar = make_progress_bar(current, total)

    text = f"🪪 <b>{card_name}</b>\nПрогресс: {bar}"

    filled = (
        isinstance(current, int)
        and isinstance(total, int)
        and total > 0
        and current >= total
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"🎁 {reward_name}" if filled else f"📲 {card_name}",
            callback_data=f"qr:redeem:{card_id}" if filled else f"qr:stamp:{card_id}"
        )
    ]])

    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


# ===== Коллбэк для QR =====
@router.callback_query(F.data.startswith("qr:"))
async def send_qr(cb: CallbackQuery):
    try:
        _, action, card_id = cb.data.split(":", 2)
        assert action in {"stamp", "redeem"}
    except Exception:
        await cb.answer("Некорректные данные", show_alert=True)
        return

    customer_id = await get_customer_id(cb.message.chat.id)
    if not customer_id:
        await cb.message.answer("ℹ️ Сначала войдите.", reply_markup=login_inline_kb())
        await cb.answer()
        return

    # 🔗 Формируем полный URL для QR
    qr_text = f"https://api.forfriends.space/api/v1/customers/{customer_id}/cards/{card_id}/{action}"
    file = make_qr_input_file(qr_text, filename=f"{action}.png")

    caption = "✅ Штамп начислен" if action == "stamp" else "🎁 Награда доступна"
    await cb.message.answer_photo(photo=file, caption=caption)
    await cb.answer()
