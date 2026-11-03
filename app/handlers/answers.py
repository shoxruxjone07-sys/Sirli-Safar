"""Javoblar: tugmalar (test), guruhdagi reply (matnli/tuzoq), shaxsiy individual javoblar, admin baholashi."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.deps import Deps
from app.utils.tg import esc, mention, try_call

log = logging.getLogger(__name__)
router = Router(name="answers")
GROUP = F.chat.type.in_({"group", "supergroup"})

DENY = {
    "paused": "⏸ O‘yin pauzada. Javob qabul qilinmaydi.",
    "closed": "Bu topshiriq yopilgan.",
    "already": "Bu topshiriqqa javob allaqachon qabul qilingan.",
    "not_player": ("Siz bu o‘yin ro‘yxatida yo‘qsiz. Ro‘yxat o‘yin boshlanganda yopilgan — "
                   "keyingi o‘yinda qatnashasiz. (Botga /start bosib, ro‘yxatga yozilishni unutmang.)"),
    "not_yours": "Bu topshiriq sizga berilmagan.",
    "wrong_kind": "Bu amal bu topshiriq uchun mos emas.",
    "missing": "Topshiriq topilmadi.",
}


@router.callback_query(F.data.startswith("ans:"))
async def on_choice(call: CallbackQuery, deps: Deps):
    try:
        _, gt_id, idx = call.data.split(":")
        gt_id, idx = int(gt_id), int(idx)
    except ValueError:
        await call.answer()
        return
    res = await deps.games.submit_choice(gt_id, call.from_user.id, idx)
    if res.status in ("ok", "timeout"):
        await call.answer("✅ Javob qabul qilindi!" if res.status == "ok" else "⏰ Vaqt tugagan edi.")
        # individual topshiriq bo‘lsa, shaxsiy chatdagi tugmalarni olib tashlaymiz
        if call.message and call.message.chat.type == "private":
            await try_call(call.message.edit_reply_markup, reply_markup=None)
            await try_call(call.message.answer,
                           "✅ Javobingiz qabul qilindi. Natija guruhda e’lon qilinadi." if res.status == "ok"
                           else "⏰ Vaqt tugagan edi — topshiriq noto‘g‘ri hisoblandi.")
        await deps.flow.after_resolve(res.resolution)
        return
    if res.status in ("already", "closed") and call.message and call.message.chat.type == "private":
        await try_call(call.message.edit_reply_markup, reply_markup=None)
    await call.answer(DENY.get(res.status, "Xatolik"), show_alert=True)


@router.callback_query(F.data.startswith("gr:"))
async def on_grade(call: CallbackQuery, deps: Deps):
    if not await deps.auth.is_authenticated(call.from_user.id):
        await call.answer("🔐 Avval /admin orqali tizimga kiring.", show_alert=True)
        return
    try:
        _, gt_id, ok = call.data.split(":")
        gt_id = int(gt_id)
    except ValueError:
        await call.answer()
        return
    good = ok == "1"
    res = await deps.games.grade(gt_id, call.from_user.id, good)
    if res.status in ("ok", "timeout"):
        label = ("✅ TO‘G‘RI" if good else "❌ NOTO‘G‘RI") if res.status == "ok" else "⏰ Vaqt tugagan edi — noto‘g‘ri"
        await call.answer("Baholandi")
        if call.message:
            await try_call(call.message.edit_text, f"{call.message.html_text}\n\n<b>Baholandi: {label}</b>",
                           reply_markup=None)
        await deps.flow.after_resolve(res.resolution)
        return
    msgs = {"paused": "⏸ O‘yin pauzada — avval davom ettiring.", "closed": "Bu topshiriq allaqachon baholangan.",
            "missing": "Topshiriq topilmadi."}
    if res.status == "closed" and call.message:
        await try_call(call.message.edit_reply_markup, reply_markup=None)
    await call.answer(msgs.get(res.status, "Xatolik"), show_alert=True)


@router.message(GROUP, F.reply_to_message, F.text)
async def on_group_reply(message: Message, deps: Deps):
    gt = await deps.games.find_open_by_group_message(message.chat.id, message.reply_to_message.message_id)
    if not gt:
        return
    user = message.from_user
    info = {"tg_id": user.id, "full_name": user.full_name, "username": user.username}
    if gt["kind"] == "trap":
        r = await deps.games.check_trap_reply(gt["id"], user.id)
        if r.status == "ok":
            await try_call(deps.bot.send_message, gt["admin_id"],
                           f"📨 <b>Tuzoq javobi</b> — {mention(user.id, user.full_name, user.username)}:\n{esc(message.text)}")
        elif r.status == "not_player":
            await message.reply(DENY["not_player"])
        return
    if gt["kind"] not in ("text", "creative"):
        return
    if gt["status"] == "awaiting_review":
        await message.reply("Bu topshiriq uchun jamoa javobi allaqachon qabul qilingan — o‘qituvchi tekshirmoqda.")
        return
    r = await deps.games.submit_text(gt["id"], user.id, message.text)
    if r.status == "ok":
        await message.reply("✅ Javob qabul qilindi va o‘qituvchiga yuborildi. Natija tez orada e’lon qilinadi.")
        await deps.flow.send_review(r.task, info, message.text)
    elif r.status == "timeout":
        await deps.flow.after_resolve(r.resolution)
    elif r.status in ("not_player", "paused", "already"):
        await message.reply(DENY[r.status])


@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def on_private_text(message: Message, state: FSMContext, deps: Deps):
    if await state.get_state():
        return
    user = message.from_user
    gt = await deps.games.find_open_individual(user.id)
    if not gt:
        await message.answer("Hozir sizga berilgan topshiriq yo‘q. Guruhdagi o‘yinni kuzating 🙂")
        return
    if gt["status"] == "awaiting_review":
        await message.answer("Javobingiz allaqachon qabul qilingan — o‘qituvchi tekshirmoqda.")
        return
    if gt["options"]:
        await message.answer("Bu topshiriqda javobni yuqoridagi tugmalar orqali tanlang 👆")
        return
    r = await deps.games.submit_text(gt["id"], user.id, message.text)
    info = {"tg_id": user.id, "full_name": user.full_name, "username": user.username}
    if r.status == "ok":
        await message.answer("✅ Javobingiz o‘qituvchiga yuborildi. Natija guruhda e’lon qilinadi.")
        await deps.flow.send_review(r.task, info, message.text)
    elif r.status == "timeout":
        await message.answer("⏰ Vaqt tugagan edi — topshiriq noto‘g‘ri hisoblandi.")
        await deps.flow.after_resolve(r.resolution)
    elif r.status in ("already", "paused", "closed"):
        await message.answer(DENY[r.status])
