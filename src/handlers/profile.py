from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from utils.api import request, unwrap
from utils.redis_client import get_customer_id
from utils.keyboards import login_inline_kb

router = Router()

# универсальная функция, которую можно вызвать и из кнопки, и из /me
async def profile_cmd(message: Message):
    customer_id = await get_customer_id(message.chat.id)
    if not customer_id:
        await message.answer("ℹ️ Сначала войдите.", reply_markup=login_inline_kb())
        return

    status, payload = await request(message.chat.id, "GET", f"/customers/{customer_id}/")
    if status == 403:
        await message.answer("🔐 Сессия истекла. Войдите снова.", reply_markup=login_inline_kb())
        return

    if status == 200:
        obj = unwrap(payload)
        name = obj.get("name", "—")
        phone = obj.get("phone", "—")
        lang = obj.get("language", "—")
        await message.answer(f"👤 <b>{name}</b>\n📞 {phone}\n🌐 {lang}")
    else:
        await message.answer(f"❌ Ошибка профиля (status={status}):\n<code>{payload}</code>")


# команда /me просто вызывает ту же функцию
@router.message(Command("me"))
async def profile_command_entry(message: Message):
    await profile_cmd(message)
