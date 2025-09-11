import redis.asyncio as aioredis
from config import REDIS_HOST, REDIS_PORT

redis = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

async def set_customer_id(chat_id: int, customer_id: str):
    await redis.set(f"customer_id:{chat_id}", customer_id)

async def get_customer_id(chat_id: int) -> str | None:
    return await redis.get(f"customer_id:{chat_id}")

async def clear_customer(chat_id: int):
    await redis.delete(f"customer_id:{chat_id}")
    await redis.delete(f"cookies:{chat_id}")

async def get_cookies_raw(chat_id: int) -> str | None:
    return await redis.get(f"cookies:{chat_id}")

async def set_cookies_raw(chat_id: int, cookie_str: str):
    await redis.set(f"cookies:{chat_id}", cookie_str)
