"""Guruh hodisalari: bot qo‘shilishi/chiqarilishi, /holat."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

from app.deps import Deps
from app.services.game_service import GameError
from app.services.staircase_service import text_ladder
from app.utils.tg import esc, try_call

log = logging.getLogger(__name__)
router = Router(name="group")
GROUP = F.chat.type.in_({"group", "supergroup"})


@router.my_chat_member(GROUP)
async def bot_status_changed(update: ChatMemberUpdated, deps: Deps):
    chat = update.chat
    new = update.new_chat_member.status
    if new in ("member", "administrator"):
        adder = update.from_user
        if not deps.auth.is_admin_id(adder.id):
            await try_call(deps.bot.send_message, chat.id,
                           "⛔ Bu botni faqat admin (o‘qituvchi) guruhga qo‘sha oladi. Bot guruhni tark etadi.")
            await try_call(deps.bot.leave_chat, chat.id)
            return
        await deps.db.execute(
            "INSERT INTO groups(chat_id,title,added_by,is_member) VALUES($1,$2,$3,TRUE) "
            "ON CONFLICT (chat_id) DO UPDATE SET title=EXCLUDED.title, added_by=EXCLUDED.added_by, "
            "is_member=TRUE, updated_at=now()", chat.id, chat.title or str(chat.id), adder.id)
        await try_call(deps.bot.send_message, chat.id,
                       "🧭 <b>SIRLI SAFAR</b> guruhga ulandi!\nO‘qituvchi botning shaxsiy chatida /admin orqali "
                       "yangi o‘yin yaratadi. Talabalar o‘yin xabaridagi tugma orqali ro‘yxatdan o‘tadi.")
        await try_call(deps.bot.send_message, adder.id,
                       f"✅ Guruh ulandi: <b>{esc(chat.title)}</b>. Endi /admin → «Yangi o‘yin yaratish».")
    elif new in ("left", "kicked"):
        await deps.db.execute("UPDATE groups SET is_member=FALSE, updated_at=now() WHERE chat_id=$1", chat.id)
        game = await deps.games.active_game_for_group(chat.id)
        if game:
            try:
                await deps.games.cancel(game["id"])
            except GameError:
                pass
            await try_call(deps.bot.send_message, game["admin_id"],
                           f"⚠️ Bot <b>{esc(chat.title)}</b> guruhidan chiqarildi — o‘yin bekor qilindi.")


@router.message(GROUP, F.migrate_to_chat_id)
async def group_migrated(message: Message, deps: Deps):
    await deps.db.execute("UPDATE groups SET chat_id=$2 WHERE chat_id=$1", message.chat.id, message.migrate_to_chat_id)


@router.message(GROUP, Command("holat", "status"))
async def cmd_status(message: Message, deps: Deps):
    game = await deps.games.active_game_for_group(message.chat.id)
    if not game:
        await message.reply("Hozir bu guruhda faol o‘yin yo‘q.")
        return
    roster = await deps.games.roster(game["id"])
    names = {"lobby": "ro‘yxat yig‘ilmoqda", "running": "davom etmoqda", "paused": "pauzada"}
    await message.reply(
        f"📖 <b>{esc(game['story_title'])}</b>\nHolat: <b>{names[game['status']]}</b>\n"
        f"🪜 {text_ladder(game['current_stage'])}\n👥 Ro‘yxatda: {len(roster)} kishi")


@router.message(GROUP, Command("start"))
async def group_start(message: Message, deps: Deps):
    await message.reply("Botni shaxsiy chatda oching va «Start» tugmasini bosing, so‘ng o‘yin xabaridagi "
                        "«Ro‘yxatga yozilish» tugmasidan foydalaning.")
