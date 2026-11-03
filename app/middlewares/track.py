"""Foydalanuvchini kuzatish: Telegram ID, username, ism (har bir o‘zgarishda yangilanadi)."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class TrackUsers(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict) -> Any:
        user = data.get("event_from_user")
        deps = data.get("deps")
        if user and deps and not user.is_bot:
            private = isinstance(event, Message) and event.chat.type == "private"
            await deps.db.execute(
                "INSERT INTO players(tg_id, username, full_name, dm_ok) VALUES($1,$2,$3,$4) "
                "ON CONFLICT (tg_id) DO UPDATE SET username=EXCLUDED.username, full_name=EXCLUDED.full_name, "
                "dm_ok = players.dm_ok OR EXCLUDED.dm_ok, updated_at=now() "
                "WHERE players.username IS DISTINCT FROM EXCLUDED.username "
                "OR players.full_name IS DISTINCT FROM EXCLUDED.full_name "
                "OR (EXCLUDED.dm_ok AND NOT players.dm_ok)",
                user.id, user.username, user.full_name or str(user.id), private)
        return await handler(event, data)
