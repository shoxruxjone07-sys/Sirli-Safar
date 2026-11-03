"""Talabalar: /start, ro‘yxatga yozilish, yordam."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatMemberUpdated, Message

from app.deps import Deps
from app.utils.tg import esc

log = logging.getLogger(__name__)
router = Router(name="players")

WELCOME = (
    "🧭 <b>SIRLI SAFAR</b> — jamoaviy sarguzasht o‘yini!\n\n"
    "Siz botda ro‘yxatdan o‘tdingiz ✅ — endi bot sizga shaxsiy topshiriq yubora oladi.\n\n"
    "<b>Keyingi qadam:</b> guruhdagi o‘yin xabarida <b>«✅ Ro‘yxatga yozilish»</b> tugmasini bosing. "
    "O‘yin boshlangach ro‘yxat yopiladi, shuning uchun oldindan yoziling."
)


@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message, command: CommandObject, deps: Deps):
    arg = (command.args or "").strip()
    if arg.startswith("join_") and arg[5:].isdigit():
        await _join(message, deps, int(arg[5:]))
        return
    text = WELCOME
    if deps.auth.is_admin_id(message.from_user.id):
        text += "\n\n🔐 Siz adminsiz: boshqaruv paneli uchun /admin buyrug‘ini yuboring."
    if arg == "task":
        text = ("🎯 Agar sizga individual topshiriq yuborilgan bo‘lsa, u shu chatda ko‘rinadi. "
                "Variantli topshiriqda tugmani bosing, matnli topshiriqda javobingizni yozing.")
    await message.answer(text)


async def _join(message: Message, deps: Deps, game_id: int) -> None:
    user = message.from_user
    game = await deps.games.get_game(game_id)
    if not game:
        await message.answer("Bunday o‘yin topilmadi.")
        return
    try:  # begona odam havola orqali kirib qolmasligi uchun guruh a’zoligini tekshiramiz
        member = await deps.bot.get_chat_member(game["group_id"], user.id)
        if member.status in ("left", "kicked"):
            await message.answer("Siz bu o‘yin guruhining a’zosi emassiz.")
            return
    except TelegramAPIError as exc:
        log.info("Guruh a’zoligini tekshirib bo‘lmadi: %s", exc)
    result = await deps.games.join(game_id, user.id)
    title = esc(game["group_title"])
    if result == "ok":
        await message.answer(f"✅ Siz <b>{title}</b> guruhidagi «{esc(game['story_title'])}» o‘yini ro‘yxatiga yozildingiz!\n"
                             "O‘qituvchi o‘yinni boshlashini kuting. Topshiriqlar guruhda va shu chatda keladi.")
    elif result == "already":
        await message.answer(f"Siz allaqachon <b>{title}</b> o‘yini ro‘yxatidasiz ✅")
    elif result == "closed":
        await message.answer("⏳ Bu o‘yin allaqachon boshlangan — ro‘yxat yopilgan. Siz keyingi o‘yinda qatnashasiz.")
    else:
        await message.answer("Bunday o‘yin topilmadi.")


@router.message(Command("help", "yordam"), F.chat.type == "private")
async def cmd_help(message: Message, deps: Deps):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n"
        "• Guruhdagi o‘yin xabarida «Ro‘yxatga yozilish» tugmasini bosing.\n"
        "• To‘g‘ri javob — jamoa bir zina yuqoriga, noto‘g‘ri javob — bir zina pastga.\n"
        "• Maqsad: 10-zinaga yetish.\n"
        "• Individual topshiriq sizga shaxsiy chatda keladi.\n"
        "• Guruhda /holat — o‘yin holatini ko‘rsatadi.")


@router.my_chat_member(F.chat.type == "private")
async def pm_status(update: ChatMemberUpdated, deps: Deps):
    ok = update.new_chat_member.status == "member"
    await deps.db.execute("UPDATE players SET dm_ok=$2 WHERE tg_id=$1", update.from_user.id, ok)
