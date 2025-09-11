from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    ChosenInlineResult,
)

from utils.api import request, unwrap
from utils.redis_client import get_customer_id
from utils.keyboards import login_inline_kb

router = Router()


# ===== Универсальная функция =====
async def find_cards_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔎 Найти заведение", switch_inline_query_current_chat="")
    ]])
    await message.answer("Нажмите кнопку, чтобы найти заведение:", reply_markup=kb)


# ===== Команда /find =====
@router.message(Command("find"))
async def find_command_entry(message: Message):
    await find_cards_cmd(message)


# ===== Inline-поиск =====
@router.inline_query()
async def inline_find(inline_query: InlineQuery):
    q = inline_query.query.strip()
    if not q:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    status, payload = await request(
        inline_query.from_user.id, "GET", "/businesses/",
        params={"q": q, "limit": 10, "offset": 0}
    )
    if status != 200:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    businesses = unwrap(payload, as_list=True)
    print("=== /businesses payload ===")
    print(payload)

    results = []
    for b in businesses:
        bid = b.get("id")
        name = b.get("name", "—")
        if not bid:
            continue
        results.append(
            InlineQueryResultArticle(
                id=bid,
                title=name,
                description="Заведение",
                input_message_content=InputTextMessageContent(message_text=f"/biz_{bid}"),
            )
        )
    await inline_query.answer(results, cache_time=1, is_personal=True)


# ===== Выбор inline-результата =====
@router.chosen_inline_result()
async def inline_chosen(chosen: ChosenInlineResult):
    business_id = chosen.result_id
    chat_id = chosen.from_user.id

    status, payload = await request(
        chat_id, "GET", f"/businesses/{business_id}/punch-cards/",
        params={"limit": 50, "offset": 0}
    )
    print("=== /businesses/{id}/punch-cards payload ===")
    print(payload)

    if status == 403:
        await router.bot.send_message(chat_id, "🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        return
    if status != 200:
        await router.bot.send_message(chat_id, f"❌ Ошибка загрузки карточек (status={status}).")
        return

    cards = unwrap(payload, as_list=True)
    if not cards:
        await router.bot.send_message(chat_id, "📭 У этого заведения пока нет карточек.")
        return

    rows = []
    for c in cards:
        cid = c.get("id") or c.get("punch_card_id")
        if not cid:
            continue
        title = c.get("name", "—")
        # передаём только id в callback
        cb = f"addcard:{cid}"
        rows.append([InlineKeyboardButton(text=f"➕ {title}", callback_data=cb)])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await router.bot.send_message(chat_id, "🎴 Карточки заведения:\nВыберите, что добавить:", reply_markup=kb)


# ===== Подстраховка на /biz_<id> =====
@router.message(F.text.startswith("/biz_"))
async def show_business_cards(message: Message):
    business_id = message.text.replace("/biz_", "", 1)
    status, payload = await request(
        message.chat.id, "GET", f"/businesses/{business_id}/punch-cards/",
        params={"limit": 50, "offset": 0}
    )
    print("=== /businesses/{id}/punch-cards payload ===")
    print(payload)

    if status == 403:
        await message.answer("🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        return
    if status != 200:
        await message.answer(f"❌ Ошибка загрузки карточек (status={status}).")
        return

    cards = unwrap(payload, as_list=True)
    if not cards:
        await message.answer("📭 У этого заведения пока нет карточек.")
        return

    rows = []
    for c in cards:
        cid = c.get("id") or c.get("punch_card_id")
        if not cid:
            continue
        title = c.get("name", "—")
        cb = f"addcard:{cid}"
        rows.append([InlineKeyboardButton(text=f"➕ {title}", callback_data=cb)])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer("🎴 Карточки заведения:\nВыберите, что добавить:", reply_markup=kb)


# ===== Добавление карточки =====
# ===== Добавление карточки =====
@router.callback_query(F.data.startswith("addcard:"))
async def add_card(cb: CallbackQuery):
    try:
        parts = cb.data.split(":")
        pcard_id = parts[1]
    except Exception:
        await cb.answer("Некорректные данные", show_alert=True)
        return

    customer_id = await get_customer_id(cb.message.chat.id)
    if not customer_id:
        await cb.message.answer("ℹ️ Сначала войдите.", reply_markup=login_inline_kb())
        await cb.answer()
        return

    payload_json = {"punch_card_id": pcard_id}
    print("=== [REQUEST] POST /customers/{}/cards/ ===".format(customer_id))
    print("Payload:", payload_json)

    status, payload = await request(
        cb.message.chat.id,
        "POST",
        f"/customers/{customer_id}/cards/",
        json=payload_json
    )

    print("=== [RESPONSE] POST /customers/{}/cards/ ===".format(customer_id))
    print("Status:", status)
    print("Payload:", payload)

    if status == 403:
        await cb.message.answer("🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        await cb.answer()
        return
    if status not in (200, 201, 204):
        await cb.message.answer(f"❌ Не удалось добавить карточку (status={status}).")
        await cb.answer("Ошибка", show_alert=True)
        return

    obj = unwrap(payload) or {}
    card_id = obj.get("id")
    name = obj.get("name")

    msg = "✅ Карточка добавлена!"
    if name:
        msg = f"✅ Карточка «<b>{name}</b>» добавлена!"

    kb = None
    if card_id and customer_id:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📲 Получить штамп", callback_data=f"qr:stamp:{card_id}"
            )
        ]])

    await cb.message.answer(msg, reply_markup=kb)
    await cb.answer("Добавлено")

