"""Admin routeri uchun darvoza: faqat ADMIN_IDS ichidagi va parol bilan kirgan foydalanuvchilar."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AdminGate(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict) -> Any:
        user = data.get("event_from_user")
        deps = data["deps"]
        if user and await deps.auth.is_authenticated(user.id):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer("🔐 Sessiya tugagan yoki ruxsat yo‘q. /admin buyrug‘ini yuboring.", show_alert=True)
        elif isinstance(event, Message):
            await event.answer("🔐 Avval /admin orqali tizimga kiring.")
        return None
