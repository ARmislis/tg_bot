import aiohttp
from http.cookies import SimpleCookie
from typing import Any, Dict, Tuple
from config import API_BASE
from .redis_client import get_cookies_raw, set_cookies_raw

def _raw_to_cookiejar(raw: str | None) -> aiohttp.CookieJar:
    jar = aiohttp.CookieJar()
    if raw:
        sc = SimpleCookie(); sc.load(raw)
        jar.update_cookies({k: m.value for k, m in sc.items()})
    return jar

def _cookiejar_to_raw(jar: aiohttp.CookieJar) -> str:
    pairs = [f"{c.key}={c.value}" for c in jar]
    return "; ".join(pairs)

async def request(
    chat_id: int, method: str, path: str,
    *, params: Dict[str, Any] | None = None,
    json: Dict[str, Any] | None = None,
) -> Tuple[int, Any]:
    cookie_raw = await get_cookies_raw(chat_id)
    jar = _raw_to_cookiejar(cookie_raw)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
        async with session.request(method.upper(), url, params=params, json=json) as resp:
            await set_cookies_raw(chat_id, _cookiejar_to_raw(session.cookie_jar))
            try:
                payload = await resp.json(content_type=None)
            except Exception:
                payload = await resp.text()
            return resp.status, payload

def unwrap(payload: Any, *, as_list: bool = False):
    """
    API часто отвечает {"data": ...}. Достаём это значение.
    Если as_list=True, гарантируем список.
    """
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if as_list:
        return payload if isinstance(payload, list) else []
    return payload
