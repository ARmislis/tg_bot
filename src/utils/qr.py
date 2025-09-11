# utils/qr.py
from io import BytesIO
from typing import Literal

import qrcode
from aiogram.types import BufferedInputFile

# Базовый путь/хост. По умолчанию шьём только путь, как ты просил.
API_HOST = "https://api.forfriends.space"  # при необходимости переопредели
API_PREFIX = "/api/v1"
INCLUDE_HOST = False  # если нужен ПОЛНЫЙ URL в QR — поменяй на True

def build_qr_text(customer_id: str, card_id: str, action: Literal["stamp", "redeem"]) -> str:
    path = f"{API_PREFIX}/customers/{customer_id}/cards/{card_id}/{action}"
    return f"{API_HOST}{path}" if INCLUDE_HOST else f"/{path.lstrip('/')}"

def make_qr_bytes(text: str) -> bytes:
    """Генерирует PNG-QR в памяти (bytes). Бросает исключение при сбое."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio.read()

def make_qr_input_file(text: str, filename: str) -> BufferedInputFile:
    return BufferedInputFile(make_qr_bytes(text), filename=filename)
