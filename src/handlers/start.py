from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    nav_inline_kb,
    main_menu_reply_auth,
    main_menu_reply_unauth,
)
from utils.redis_client import get_customer_id

# импортируем старты FSM логина и регистрации
from handlers.auth import login_start, register_start
# импортируем хендлеры для карт и профиля
from handlers.mycards import mycards_cmd
from handlers.profile import profile_cmd

router = Router()

WELCOME = (
    "Добро пожаловать в ForFriends! 👋\n"
    "Используйте кнопки ниже для навигации."
)

# ===== /start =====

@router.message(CommandStart())
async def start_cmd(message: Message):
    customer_id = await get_customer_id(message.chat.id)
    if customer_id:
        await message.answer(WELCOME, reply_markup=main_menu_reply_auth())
    else:
        await message.answer(WELCOME, reply_markup=main_menu_reply_unauth())


# ===== Reply keyboard actions =====

@router.message(F.text == "🎴 Мои карты")
async def reply_cards(message: Message):
    # вместо "отправить /mycards" вызываем хендлер
    await mycards_cmd(message)

@router.message(F.text == "👤 Профиль")
async def reply_profile(message: Message):
    # вместо "отправить /me" вызываем хендлер
    await profile_cmd(message)

@router.message(F.text == "🔎 Найти заведение")
async def reply_find(message: Message):
    await message.answer(
        "Нажмите кнопку ниже, чтобы начать поиск:",
        reply_markup=nav_inline_kb()
    )

# ===== Вход и регистрация =====

@router.message(F.text == "🔐 Войти")
async def reply_login(message: Message, state: FSMContext):
    await login_start(message, state)

@router.message(F.text == "📝 Регистрация")
async def reply_register(message: Message, state: FSMContext):
    await register_start(message, state)
