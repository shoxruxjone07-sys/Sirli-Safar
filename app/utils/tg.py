"""Telegram yordamchilari: HTML qochirish, tilga olish, qayta urinish bilan yuborish."""
from __future__ import annotations

import asyncio
import html
import logging
from typing import Any, Awaitable, Callable, Optional

from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter

log = logging.getLogger(__name__)
MAX_LEN = 4000


def esc(text: Any) -> str:
    return html.escape(str(text if text is not None else ""), quote=False)


def user_label(username: Optional[str], full_name: str) -> str:
    return f"@{username}" if username else full_name


def mention(user_id: int, full_name: str, username: Optional[str] = None) -> str:
    """@username bo‘lsa — o‘sha; bo‘lmasa ism bo‘yicha havola (username bo‘lmagan foydalanuvchilar uchun)."""
    if username:
        return f"@{esc(username)}"
    return f'<a href="tg://user?id={int(user_id)}">{esc(full_name)}</a>'


def fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} soat {m} daqiqa {s} soniya"
    if m:
        return f"{m} daqiqa {s} soniya"
    return f"{s} soniya"


def fmt_limit(seconds: int) -> str:
    if seconds % 60 == 0:
        return f"{seconds // 60} daqiqa"
    if seconds > 60:
        return f"{seconds // 60} daqiqa {seconds % 60} soniya"
    return f"{seconds} soniya"


def split_text(text: str, limit: int = MAX_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for para in text.split("\n"):
        while len(para) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(para[:limit])
            para = para[limit:]
        if len(cur) + len(para) + 1 > limit:
            parts.append(cur)
            cur = para
        else:
            cur = f"{cur}\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


async def tg_call(fn: Callable[..., Awaitable[Any]], *args: Any, retries: int = 3, **kwargs: Any) -> Any:
    """Telegram so‘rovi: flood limit va tarmoq xatolarida qayta urinadi. Boshqa xatolarni qaytaradi (raise)."""
    for attempt in range(retries + 1):
        try:
            return await fn(*args, **kwargs)
        except TelegramRetryAfter as exc:
            if attempt == retries:
                raise
            await asyncio.sleep(min(float(exc.retry_after), 30.0) + 0.5)
        except TelegramNetworkError:
            if attempt == retries:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))


async def try_call(fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """Xato bo‘lsa None qaytaradi (jurnalga yozadi) — muhim bo‘lmagan yuborishlar uchun."""
    try:
        return await tg_call(fn, *args, **kwargs)
    except TelegramAPIError as exc:
        log.warning("Telegram xatosi (%s): %s", getattr(fn, "__name__", "call"), exc)
        return None
