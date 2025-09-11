import re
import asyncio
import aiohttp
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.api import request
from utils.redis_client import set_customer_id, get_customer_id, clear_customer
from utils.keyboards import (
    main_menu_reply_auth,
    main_menu_reply_unauth,
)

router = Router()

# ===== FSM состояния =====

class RegisterFlow(StatesGroup):
    name = State()
    birth_date = State()
    phone = State()
    password = State()

class LoginFlow(StatesGroup):
    phone = State()
    password = State()

PHONE_PATTERN = re.compile(r"^\+7\d{10}$")
CODE_PATTERN = re.compile(r"^\d{4}$")  # только 4 цифры


# ===== Универсальная отмена =====

@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu_reply_unauth())

def back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

# ===== Логика кнопки "Назад" =====

async def go_back(message: Message, state: FSMContext, flow: str):
    current = await state.get_state()

    if flow == "register":
        if current == RegisterFlow.birth_date.state:
            await state.set_state(RegisterFlow.name)
            await message.answer("Введите ваше имя:", reply_markup=back_kb())
        elif current == RegisterFlow.phone.state:
            await state.set_state(RegisterFlow.birth_date)
            await message.answer("Введите дату рождения (формат ДД.ММ.ГГГГ):", reply_markup=back_kb())
        elif current == RegisterFlow.password.state:
            await state.set_state(RegisterFlow.phone)
            await message.answer("Введите номер телефона (формат +7XXXXXXXXXX):", reply_markup=back_kb(), input_field_placeholder="+7")

    elif flow == "login":
        if current == LoginFlow.password.state:
            await state.set_state(LoginFlow.phone)
            await message.answer("Введите номер телефона (формат +7XXXXXXXXXX):", reply_markup=back_kb(), input_field_placeholder="+7")

# ===== Регистрация =====

@router.message(Command("register"))
async def register_start(message: Message, state: FSMContext):
    await message.answer("Введите ваше имя:", reply_markup=back_kb())
    await state.set_state(RegisterFlow.name)

@router.message(RegisterFlow.name, F.text != "⬅️ Назад")
async def register_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите дату рождения (формат ДД.ММ.ГГГГ):", reply_markup=back_kb())
    await state.set_state(RegisterFlow.birth_date)

@router.message(RegisterFlow.name, F.text == "⬅️ Назад")
async def register_back_name(message: Message, state: FSMContext):
    await cancel_cmd(message, state)

@router.message(RegisterFlow.birth_date, F.text == "⬅️ Назад")
async def register_back_birth(message: Message, state: FSMContext):
    await go_back(message, state, "register")

@router.message(RegisterFlow.birth_date, F.text != "⬅️ Назад")
async def register_birth(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите дату в виде ДД.ММ.ГГГГ")
        return
    await state.update_data(birth_date=message.text.strip())
    await message.answer("Введите номер телефона (формат +7XXXXXXXXXX):", reply_markup=back_kb(), input_field_placeholder="+7")
    await state.set_state(RegisterFlow.phone)

@router.message(RegisterFlow.phone, F.text == "⬅️ Назад")
async def register_back_phone(message: Message, state: FSMContext):
    await go_back(message, state, "register")

@router.message(RegisterFlow.phone, F.text != "⬅️ Назад")
async def register_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_PATTERN.match(phone):
        await message.answer("❌ Неверный формат. Введите номер в виде +7XXXXXXXXXX")
        return
    await state.update_data(phone=phone)
    await message.answer("Введите пароль 8 символов и более:", reply_markup=back_kb())
    await state.set_state(RegisterFlow.password)

@router.message(RegisterFlow.password, F.text == "⬅️ Назад")
async def register_back_password(message: Message, state: FSMContext):
    await go_back(message, state, "register")

@router.message(RegisterFlow.password, F.text != "⬅️ Назад")
async def register_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    password = message.text.strip()
    phone = data["phone"]

    payload = {
        "name": data["name"],
        "birth_date": datetime.strptime(data["birth_date"], "%d.%m.%Y").strftime("%Y-%m-%dT00:00:00Z"),
        "phone": phone,
        "password": password,
        "language": "ru",
        "timezone": "Europe/Moscow",
    }

    status, resp = await request(message.chat.id, "POST", "/auth/customers/register", json=payload)

    if status in (200, 201) and isinstance(resp, dict):
        obj = resp.get("data") or resp
        customer_id = obj.get("id")
        await set_customer_id(message.chat.id, customer_id)



        sc_status, _ = await request(message.chat.id, "POST", f"/auth/customers/{customer_id}/send-code")

        if sc_status in (200, 204):
            # Сообщение с таймером сразу после регистрации
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Отправить код повторно (через 1:00)", callback_data="wait")]]
            )
            msg = await message.answer(
                "✅ Регистрация успешна!\n\n📞 Ответьте на звонок! Робот продиктует код.\n"
                "Отправьте только 4 цифры из звонка.",
                reply_markup=kb
            )

            # Обратный отсчёт
            for remaining in range(50, 0, -10):
                await asyncio.sleep(10)
                try:
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text=f"🔄 Отправить код повторно (через 0:{remaining:02d})", callback_data="wait")]]
                    )
                    await msg.edit_reply_markup(reply_markup=kb)
                except Exception:
                    break

            # Активируем кнопку через 60 секунд
            await asyncio.sleep(10)
            kb_enabled = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Отправить код повторно", callback_data="resend_code")]]
            )
            try:
                await msg.edit_reply_markup(reply_markup=kb_enabled)
            except Exception:
                pass
                # 🔑 сразу после регистрации делаем скрытый login, чтобы получить куки
        login_status, login_resp = await request(
            message.chat.id,
            "POST",
            "/auth/customers/login",
            json={"phone": phone, "password": password}
        )
    else:
        await message.answer(f"❌ Ошибка регистрации ({status}): <code>{resp}</code>")

    await state.clear()

# ===== Логин =====

@router.message(Command("login"))
async def login_start(message: Message, state: FSMContext):
    await message.answer("Введите номер телефона (формат +7XXXXXXXXXX):", reply_markup=back_kb(), input_field_placeholder="+7")
    await state.set_state(LoginFlow.phone)

@router.message(LoginFlow.phone, F.text != "⬅️ Назад")
async def login_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_PATTERN.match(phone):
        await message.answer("❌ Неверный формат. Введите номер в виде +7XXXXXXXXXX")
        return
    await state.update_data(phone=phone)
    await message.answer("Введите пароль:", reply_markup=back_kb())
    await state.set_state(LoginFlow.password)

@router.message(LoginFlow.phone, F.text == "⬅️ Назад")
async def login_back_phone(message: Message, state: FSMContext):
    await cancel_cmd(message, state)

@router.message(LoginFlow.password, F.text == "⬅️ Назад")
async def login_back_password(message: Message, state: FSMContext):
    await go_back(message, state, "login")

@router.message(LoginFlow.password, F.text != "⬅️ Назад")
async def login_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    phone, password = data["phone"], message.text.strip()

    status, resp = await request(
        message.chat.id, "POST", "/auth/customers/login", json={"phone": phone, "password": password}
    )

    if status == 200 and isinstance(resp, dict):
        obj = resp.get("data") or resp
        customer_id = obj.get("id")
        name_v = obj.get("name", "—")

        if customer_id:
            await set_customer_id(message.chat.id, customer_id)
            await message.answer(
                f"✅ Вход успешен. Добро пожаловать, <b>{name_v}</b>!",
                reply_markup=main_menu_reply_auth()
            )
        else:
            await message.answer("⚠️ Вход выполнен, но ID не найден.")
    else:
        await message.answer(f"❌ Ошибка входа ({status}): <code>{resp}</code>")

    await state.clear()

# ===== Подтверждение кода (только 4 цифры) =====

@router.message(F.text.regexp(r"^\d{4}$"))
async def confirm_code(message: Message):
    customer_id = await get_customer_id(message.chat.id)
    if not customer_id:
        await message.answer("❌ Сначала войдите или зарегистрируйтесь.")
        return

    code = message.text.strip()
    # подтверждение через query string
    status, resp = await request(
        message.chat.id,
        "GET",
        f"/auth/customers/{customer_id}/confirm?code={code}"
    )

    if status == 200:
        await message.answer("✅ Телефон подтверждён!", reply_markup=main_menu_reply_auth())
    else:
        await message.answer(f"❌ Ошибка подтверждения ({status}): <code>{resp}</code>")

# ===== Обработка повторной отправки кода =====

@router.callback_query(F.data == "resend_code")
async def resend_code(cb):
    customer_id = await get_customer_id(cb.message.chat.id)
    if not customer_id:
        await cb.answer("Сначала /register или /login", show_alert=True)
        return

    status, _ = await request(cb.message.chat.id, "POST", f"/auth/customers/{customer_id}/send-code")
    if status in (200, 204):
        await cb.message.answer("📨 Новый звонок отправлен. Ответьте на звонок и введите 4 цифры.")
        await cb.answer("Код отправлен")
    else:
        await cb.message.answer("❌ Ошибка при повторной отправке кода.")
        await cb.answer("Ошибка", show_alert=True)

# ===== Логаут =====

@router.message(Command("logout"))
async def logout_cmd(message: Message):
    # напрямую дергаем forfriends.space/api/_flush_cookies, минуя request()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://forfriends.space/api/_flush_cookies") as resp:
                status = resp.status
                text = await resp.text()
    except Exception as e:
        status = 500
        text = str(e)

    # чистим Redis
    await clear_customer(message.chat.id)

    if status in (200, 204):
        await message.answer("🔒 Вы вышли из аккаунта.", reply_markup=main_menu_reply_unauth())
    else:
        await message.answer(
            f"🔒 Сессия локально очищена. Сервер ответил (status={status}): <code>{text}</code>",
            reply_markup=main_menu_reply_unauth()
        )
