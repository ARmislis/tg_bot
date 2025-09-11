from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# ===== Inline keyboards (top / pinned) =====

def nav_inline_kb() -> InlineKeyboardMarkup:
    """
    Pinned inline navigation used across the bot.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Мои карты", callback_data="nav:cards"),
            InlineKeyboardButton(text="👤 Профиль",  callback_data="nav:profile"),
        ],
        [
            # opens inline mode of the bot in the current chat
            InlineKeyboardButton(text="🔎 Найти заведение", switch_inline_query_current_chat=""),
        ],
    ])

def back_inline_kb(to: str = "menu") -> InlineKeyboardMarkup:
    """
    Single 'Back' inline button. `to` controls callback suffix.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"nav:{to}")]
    ])

def login_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти", callback_data="nav:login")]
    ])

def confirm_inline_kb() -> InlineKeyboardMarkup:
    """
    Backward-compat for auth.py flows which expect 'sendcode_inline' callback.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Отправить код подтверждения", callback_data="sendcode_inline")]
    ])

# ===== Reply keyboards (bottom) =====

def main_menu_reply_unauth() -> ReplyKeyboardMarkup:
    """
    Bottom reply keyboard for NOT authenticated users.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Войти"), KeyboardButton(text="📝 Регистрация")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Войдите или зарегистрируйтесь"
    )

def main_menu_reply_auth() -> ReplyKeyboardMarkup:
    """
    Bottom reply keyboard for authenticated users.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎴 Мои карты"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🔎 Найти заведение")],
            [KeyboardButton(text="🚪 Выйти")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
