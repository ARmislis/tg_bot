import os
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE = os.getenv("API_BASE", "https://api.forfriends.space/api/v1")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

DEFAULT_BOT_PROPS = DefaultBotProperties(parse_mode="HTML")