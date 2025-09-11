from .start import router as start_router
from .auth import router as auth_router
from .profile import router as profile_router
from .find_cards import router as find_cards_router
from .mycards import router as mycards_router

__all__ = [
    "start_router",
    "auth_router",
    "profile_router",
    "find_cards_router",
    "mycards_router",
]
