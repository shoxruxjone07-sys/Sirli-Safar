"""Admin interfeysi uchun umumiy yordamchilar."""
from __future__ import annotations

from typing import Optional, Union

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

STATUS_LABEL = {
    "lobby": "🟡 Ro‘yxat yig‘ilmoqda", "running": "🟢 Davom etmoqda", "paused": "⏸ Pauzada",
    "finished": "🏁 Yakunlangan", "cancelled": "🛑 Bekor qilingan",
}


async def render(event: Union[Message, CallbackQuery], text: str, markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """Callback bo‘lsa xabarni tahrirlaydi, aks holda yangi xabar yuboradi."""
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                await event.message.answer(text, reply_markup=markup)
        except TelegramAPIError:
            await event.message.answer(text, reply_markup=markup)
        try:
            await event.answer()
        except TelegramAPIError:
            pass
    else:
        await event.answer(text, reply_markup=markup)


def back_kb(target: str = "a:menu", text: str = "⬅️ Orqaga") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=text, callback_data=target)
    return b.as_markup()


def menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🆕 Yangi o‘yin yaratish", callback_data="a:new")
    b.button(text="🎮 Faol o‘yinlar", callback_data="a:games")
    b.button(text="👥 Guruhlar", callback_data="a:groups")
    b.button(text="📚 Hikoyalar kutubxonasi", callback_data="a:lib")
    b.button(text="🧩 Topshiriqlar", callback_data="a:tasks")
    b.button(text="🪤 Tuzoq topshiriqlari", callback_data="a:traps")
    b.button(text="🏆 O‘yin natijalari", callback_data="a:results")
    b.button(text="📊 Statistika", callback_data="a:stats")
    b.button(text="⚙️ Sozlamalar", callback_data="a:settings")
    b.adjust(1, 2, 2, 2, 2)
    return b.as_markup()


def short(text: str, n: int = 60) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"
