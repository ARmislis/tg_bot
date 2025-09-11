import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, DEFAULT_BOT_PROPS
from handlers import (
    start as start_handlers,
    auth as auth_handlers,
    profile as profile_handlers,
    find_cards as find_cards_handlers,
    mycards as mycards_handlers,
)

async def main():
    bot = Bot(token=BOT_TOKEN, default=DEFAULT_BOT_PROPS)
    dp = Dispatcher()

    dp.include_router(start_handlers.router)
    dp.include_router(auth_handlers.router)
    dp.include_router(profile_handlers.router)
    dp.include_router(find_cards_handlers.router)
    dp.include_router(mycards_handlers.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
