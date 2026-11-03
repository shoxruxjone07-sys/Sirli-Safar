"""Guruh va o‘yin jarayoni tugmalari."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LETTERS = "ABCD"


def lobby_kb(bot_username: str, game_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ro‘yxatga yozilish", url=f"https://t.me/{bot_username}?start=join_{game_id}")
    return b.as_markup()


def open_bot_kb(bot_username: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📩 Botni ochish", url=f"https://t.me/{bot_username}?start=task")
    return b.as_markup()


def answer_kb(gt_id: int, n_options: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(n_options):
        b.button(text=LETTERS[i], callback_data=f"ans:{gt_id}:{i}")
    b.adjust(n_options)
    return b.as_markup()


def grade_kb(gt_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ TO‘G‘RI", callback_data=f"gr:{gt_id}:1")
    b.button(text="❌ NOTO‘G‘RI", callback_data=f"gr:{gt_id}:0")
    b.adjust(2)
    return b.as_markup()


def trap_source_kb(gt_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✍️ O‘zim yozaman", callback_data=f"tp:own:{gt_id}")
    b.button(text="📚 Kutubxonadan tanlash", callback_data=f"tp:lib:{gt_id}")
    b.adjust(1)
    return b.as_markup()
