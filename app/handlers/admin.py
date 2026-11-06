"""Admin: parol bilan kirish, boshqaruv paneli, o‘yin yaratish va boshqarish, kutubxona, natijalar, sozlamalar."""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.deps import Deps
from app.handlers.states import AdminSt, SettingEdit, StoryEdit
from app.middlewares.admin_gate import AdminGate
from app.services.backup_service import export_json
from app.services.game_service import GameError
from app.services.result_service import format_stats
from app.services.staircase_service import text_ladder
from app.utils.tg import esc, fmt_duration, mention
from app.utils.ui import STATUS_LABEL, back_kb, menu_kb, render, short

log = logging.getLogger(__name__)

# ---- kirish (darvozasiz) ---------------------------------------------------------------
login_router = Router(name="admin-login")
login_router.message.filter(F.chat.type == "private")


@login_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, deps: Deps):
    uid = message.from_user.id
    if not deps.auth.is_admin_id(uid):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    if await deps.auth.is_authenticated(uid):
        await state.clear()
        await message.answer("🧭 <b>SIRLI SAFAR — boshqaruv paneli</b>", reply_markup=menu_kb())
        return
    mins = await deps.auth.lock_minutes_left(uid)
    if mins:
        await message.answer(f"🔒 Urinishlar limiti tugagan. {mins} daqiqadan keyin qayta urinib ko‘ring.")
        return
    await state.set_state(AdminSt.password)
    await message.answer("🔐 Admin parolini kiriting:\n<i>(xabaringiz kiritilgach darhol o‘chiriladi)</i>")


@login_router.message(AdminSt.password, F.text)
async def check_password(message: Message, state: FSMContext, deps: Deps):
    password = message.text or ""
    try:  # parolni chatda qoldirmaymiz
        await message.delete()
    except TelegramAPIError:
        pass
    res = await deps.auth.login(message.from_user.id, message.from_user.full_name, password)
    if res.status == "ok":
        await state.clear()
        await message.answer("✅ Xush kelibsiz!\n\n🧭 <b>SIRLI SAFAR — boshqaruv paneli</b>", reply_markup=menu_kb())
    elif res.status == "locked":
        await state.clear()
        await message.answer(f"🔒 Juda ko‘p noto‘g‘ri urinish. {res.locked_minutes} daqiqaga bloklandi.")
    elif res.status == "forbidden":
        await state.clear()
        await message.answer("⛔ Ruxsat yo‘q.")
    else:
        await message.answer(f"❌ Parol noto‘g‘ri. Qolgan urinishlar: <b>{res.attempts_left}</b>. Qayta kiriting:")


# ---- boshqaruv paneli (darvoza bilan) ---------------------------------------------------
router = Router(name="admin")
router.message.filter(F.chat.type == "private")
router.message.middleware(AdminGate())
router.callback_query.middleware(AdminGate())


@router.callback_query(F.data == "a:menu")
async def cb_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await render(call, "🧭 <b>SIRLI SAFAR — boshqaruv paneli</b>", menu_kb())


@router.callback_query(F.data == "a:logout")
async def cb_logout(call: CallbackQuery, state: FSMContext, deps: Deps):
    await state.clear()
    await deps.auth.logout(call.from_user.id)
    await render(call, "🚪 Tizimdan chiqdingiz. Qayta kirish uchun /admin.")


# ---------- yangi o‘yin ----------
@router.callback_query(F.data == "a:new")
async def cb_new(call: CallbackQuery, deps: Deps):
    groups = await deps.db.fetch("SELECT * FROM groups WHERE is_member ORDER BY title")
    if not groups:
        await render(call, "Hali birorta guruh ulanmagan.\n\nBotni Telegram guruhiga qo‘shing (siz admin bo‘lishingiz "
                           "shart) — shundan so‘ng guruh shu yerda paydo bo‘ladi.", back_kb())
        return
    b = InlineKeyboardBuilder()
    for g in groups:
        b.button(text=short(g["title"], 40), callback_data=f"ng:g:{g['chat_id']}")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "👥 O‘yin qaysi guruhda o‘tkaziladi?", b.as_markup())


@router.callback_query(F.data.startswith("ng:g:"))
async def cb_new_group(call: CallbackQuery, deps: Deps):
    chat_id = int(call.data.split(":")[2])
    active = await deps.games.active_game_for_group(chat_id)
    if active:
        await call.answer("Bu guruhda faol o‘yin bor. Avval uni yakunlang yoki bekor qiling.", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="📖 Hikoya bilan", callback_data=f"ng:m:{chat_id}:1")
    b.button(text="⚡ Hikoyasiz (faqat savollar)", callback_data=f"ng:m:{chat_id}:0")
    b.button(text="⬅️ Orqaga", callback_data="a:new")
    b.adjust(1)
    await render(call, "🎬 <b>Hikoya rejimi</b>\n\n"
                       "• <b>Hikoya bilan</b> — har zinada hikoya matni, rasm/GIF chiqadi, o‘yin hikoya bilan davom etadi.\n"
                       "• <b>Hikoyasiz</b> — hikoya ko‘rsatilmaydi, faqat zinapoya, savollar va natijalar.",
                 b.as_markup())


@router.callback_query(F.data.startswith("ng:m:"))
async def cb_new_mode(call: CallbackQuery, deps: Deps):
    _, _, chat_id, mode = call.data.split(":")
    chat_id = int(chat_id)
    if mode == "1":
        stories = await deps.stories.list_stories()
        b = InlineKeyboardBuilder()
        for s in stories:
            b.button(text=f"📖 {s['title']}", callback_data=f"ng:s:{chat_id}:{s['id']}")
        b.button(text="⬅️ Orqaga", callback_data=f"ng:g:{chat_id}")
        b.adjust(1)
        await render(call, "📚 Hikoyani tanlang:", b.as_markup())
        return
    group = await deps.db.fetchrow("SELECT * FROM groups WHERE chat_id=$1", chat_id)
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ro‘yxat yig‘ishni boshlash", callback_data=f"ng:ok:{chat_id}:0")
    b.button(text="⬅️ Orqaga", callback_data=f"ng:g:{chat_id}")
    b.adjust(1)
    await render(call, f"👥 Guruh: <b>{esc(group['title'])}</b>\n⚡ Rejim: <b>hikoyasiz</b>\n\n"
                       "Tasdiqlasangiz, guruhga ro‘yxatga yozilish xabari yuboriladi.", b.as_markup())


@router.callback_query(F.data.startswith("ng:s:"))
async def cb_new_story(call: CallbackQuery, deps: Deps):
    _, _, chat_id, story_id = call.data.split(":")
    story = await deps.stories.get_story(int(story_id))
    group = await deps.db.fetchrow("SELECT * FROM groups WHERE chat_id=$1", int(chat_id))
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ro‘yxat yig‘ishni boshlash", callback_data=f"ng:ok:{chat_id}:{story_id}")
    b.button(text="⬅️ Orqaga", callback_data=f"ng:m:{chat_id}:1")
    b.adjust(1)
    await render(call, f"👥 Guruh: <b>{esc(group['title'])}</b>\n📖 Hikoya: <b>{esc(story['title'])}</b>\n"
                       f"<i>{esc(story['genre'])}</i>\n\n{esc(story['synopsis'])}\n\n"
                       "Tasdiqlasangiz, guruhga ro‘yxatga yozilish xabari yuboriladi.", b.as_markup())


@router.callback_query(F.data.startswith("ng:ok:"))
async def cb_new_ok(call: CallbackQuery, deps: Deps):
    _, _, chat_id, story_id = call.data.split(":")
    try:
        story_mode = int(story_id) != 0  # 0 = hikoyasiz rejim
        game_id = await deps.games.create_game(int(chat_id), int(story_id) if story_mode else None,
                                               call.from_user.id, story_mode=story_mode)
    except GameError as exc:
        await call.answer(str(exc), show_alert=True)
        return
    try:
        await deps.flow.post_lobby(game_id)
    except TelegramAPIError as exc:
        await deps.games.cancel(game_id)
        await render(call, f"❌ Guruhga xabar yuborib bo‘lmadi: {esc(exc)}\nBot guruhda va yozish huquqiga ega ekanini tekshiring.",
                     back_kb("a:new"))
        return
    await call.answer("Lobbi ochildi")
    await show_game(call, deps, game_id)


# ---------- faol o‘yinlar ----------
@router.callback_query(F.data == "a:games")
async def cb_games(call: CallbackQuery, deps: Deps):
    games = await deps.games.list_active_games()
    b = InlineKeyboardBuilder()
    for g in games:
        b.button(text=f"#{g['id']} · {short(g['group_title'], 24)} · {STATUS_LABEL[g['status']]}",
                 callback_data=f"gm:{g['id']}")
    b.button(text="🆕 Yangi o‘yin", callback_data="a:new")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "🎮 <b>Faol o‘yinlar</b>" + ("" if games else "\n\nHozir faol o‘yin yo‘q."), b.as_markup())


async def show_game(event, deps: Deps, game_id: int) -> None:
    g = await deps.games.get_game(game_id)
    if not g:
        await render(event, "O‘yin topilmadi.", back_kb("a:games"))
        return
    roster = await deps.games.roster(game_id)
    stats = await deps.games.stats(game_id)
    reviews = len(await deps.games.pending_reviews(game_id))
    text = [
        f"🎮 <b>O‘yin #{g['id']}</b>",
        f"👥 Guruh: <b>{esc(g['group_title'])}</b>",
        (f"📖 Hikoya: <b>{esc(g['story_title'])}</b>" if g["story_mode"] else "⚡ Rejim: <b>hikoyasiz</b>"),
        f"Holat: <b>{STATUS_LABEL[g['status']]}</b>",
        f"🪜 {text_ladder(g['current_stage'])}",
        f"👤 Ro‘yxatda: <b>{len(roster)}</b> kishi",
    ]
    if g["status"] != "lobby":
        text.append(f"✅ {stats['correct']} · ❌ {stats['wrong']} · ⏰ {stats['timeout']} · ⏱ {fmt_duration(stats['duration_sec'])}")
    if reviews:
        text.append(f"📝 Tekshirilishi kutilayotgan javoblar: <b>{reviews}</b>")
    b = InlineKeyboardBuilder()
    st = g["status"]
    if st == "lobby":
        b.button(text="▶️ O‘yinni boshlash", callback_data=f"gx:start:{game_id}")
        if g["story_mode"]:
            b.button(text="🔁 Hikoyani almashtirish", callback_data=f"gx:story:{game_id}")
        b.button(text="👥 Ro‘yxat", callback_data=f"gx:roster:{game_id}")
    elif st == "running":
        b.button(text="⏸ Pauza", callback_data=f"gx:pause:{game_id}")
    elif st == "paused":
        b.button(text="▶️ Davom ettirish", callback_data=f"gx:resume:{game_id}")
    if st in ("running", "paused"):
        b.button(text=f"📝 Javoblarni tekshirish ({reviews})", callback_data=f"gx:reviews:{game_id}")
        b.button(text="📊 Natijalar", callback_data=f"gx:stats:{game_id}")
        b.button(text="👥 Ro‘yxat", callback_data=f"gx:roster:{game_id}")
        b.button(text="🔄 To‘xtab qolgan bosqichni davom ettirish", callback_data=f"gx:kick:{game_id}")
    if st in ("lobby", "running", "paused"):
        b.button(text="🛑 Bekor qilish", callback_data=f"gx:cancel:{game_id}")
    b.button(text="🔃 Yangilash", callback_data=f"gm:{game_id}")
    b.button(text="⬅️ Faol o‘yinlar", callback_data="a:games")
    b.adjust(1)
    await render(event, "\n".join(text), b.as_markup())


@router.callback_query(F.data.startswith("gm:"))
async def cb_game(call: CallbackQuery, deps: Deps):
    await show_game(call, deps, int(call.data.split(":")[1]))


@router.callback_query(F.data.startswith("gx:"))
async def cb_game_action(call: CallbackQuery, deps: Deps):
    _, action, gid = call.data.split(":")
    gid = int(gid)
    try:
        if action == "start":
            await deps.games.start(gid)
            await call.answer("▶️ O‘yin boshlandi!")
            await show_game(call, deps, gid)
            await deps.flow.begin(gid)
            return
        if action == "pause":
            await deps.games.pause(gid)
            await call.answer("⏸ Pauza")
            await show_game(call, deps, gid)
            await deps.flow.announce_pause(gid)
            return
        if action == "resume":
            await deps.games.resume(gid)
            await call.answer("▶️ Davom etmoqda")
            await show_game(call, deps, gid)
            await deps.flow.announce_resume(gid)
            return
        if action == "cancel":
            b = InlineKeyboardBuilder()
            b.button(text="🛑 Ha, bekor qilish", callback_data=f"gx:cancelok:{gid}")
            b.button(text="⬅️ Yo‘q", callback_data=f"gm:{gid}")
            b.adjust(1)
            await render(call, "Rostdan ham o‘yinni bekor qilmoqchimisiz? Bu amalni qaytarib bo‘lmaydi.", b.as_markup())
            return
        if action == "cancelok":
            await deps.games.cancel(gid)
            await call.answer("Bekor qilindi")
            await show_game(call, deps, gid)
            await deps.flow.announce_cancel(gid)
            return
        if action == "kick":
            await call.answer("Tekshirilmoqda…")
            await deps.flow.recover_game(gid)
            await show_game(call, deps, gid)
            return
    except GameError as exc:
        await call.answer(str(exc)[:190], show_alert=True)
        if action == "start":
            await call.message.answer("❌ <b>O‘yinni boshlab bo‘lmadi:</b>\n" + esc(exc))
        return

    if action == "story":
        stories = await deps.stories.list_stories()
        b = InlineKeyboardBuilder()
        for s in stories:
            b.button(text=f"📖 {s['title']}", callback_data=f"gs:{gid}:{s['id']}")
        b.button(text="⬅️ Orqaga", callback_data=f"gm:{gid}")
        b.adjust(1)
        await render(call, "Yangi hikoyani tanlang (faqat o‘yin boshlanishidan oldin):", b.as_markup())
    elif action == "roster":
        roster = await deps.games.roster(gid)
        lines = [f"👥 <b>Ro‘yxat ({len(roster)})</b>"]
        for i, p in enumerate(roster, start=1):
            lines.append(f"{i}. {mention(p['tg_id'], p['full_name'], p['username'])}"
                         + (f" · 🎯 {p['times_selected']}" if p["times_selected"] else ""))
        await render(call, "\n".join(lines) if roster else "Ro‘yxat bo‘sh.", back_kb(f"gm:{gid}"))
    elif action == "stats":
        await render(call, format_stats(await deps.games.stats(gid), title="📊 Joriy natijalar"), back_kb(f"gm:{gid}"))
    elif action == "reviews":
        pend = await deps.games.pending_reviews(gid)
        if not pend:
            await call.answer("Tekshirilishi kutilayotgan javob yo‘q.", show_alert=True)
            return
        await call.answer(f"{len(pend)} ta javob yuborilmoqda")
        for p in pend[:10]:
            user = {"tg_id": p["answer_user"], "full_name": p["full_name"] or "?", "username": p["username"]}
            await deps.flow.send_review(p, user, p["answer_text"] or "")
        if await deps.games.needs_input_tasks(gid):
            await deps.flow.recover_game(gid)


@router.callback_query(F.data.startswith("gs:"))
async def cb_set_story(call: CallbackQuery, deps: Deps):
    _, gid, sid = call.data.split(":")
    try:
        await deps.games.set_story(int(gid), int(sid))
    except GameError as exc:
        await call.answer(str(exc), show_alert=True)
        return
    await deps.flow.refresh_lobby(int(gid))
    await call.answer("Hikoya almashtirildi")
    await show_game(call, deps, int(gid))


# ---------- guruhlar ----------
@router.callback_query(F.data == "a:groups")
async def cb_groups(call: CallbackQuery, deps: Deps):
    groups = await deps.db.fetch("SELECT * FROM groups ORDER BY is_member DESC, title")
    lines = ["👥 <b>Guruhlar</b>", ""]
    b = InlineKeyboardBuilder()
    for g in groups:
        active = await deps.games.active_game_for_group(g["chat_id"]) if g["is_member"] else None
        mark = "🟢" if g["is_member"] else "⚪️ (bot chiqarilgan)"
        extra = f" — o‘yin #{active['id']} ({STATUS_LABEL[active['status']]})" if active else ""
        lines.append(f"{mark} {esc(g['title'])}{extra}")
        if active:
            b.button(text=f"🎮 {short(g['title'], 28)}", callback_data=f"gm:{active['id']}")
        elif g["is_member"]:
            b.button(text=f"🆕 {short(g['title'], 28)}", callback_data=f"ng:g:{g['chat_id']}")
    if not groups:
        lines.append("Hali birorta guruh ulanmagan. Botni guruhga qo‘shing.")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "\n".join(lines), b.as_markup())


# ---------- hikoyalar kutubxonasi ----------
@router.callback_query(F.data == "a:lib")
async def cb_lib(call: CallbackQuery, deps: Deps):
    b = InlineKeyboardBuilder()
    for s in await deps.stories.list_stories(only_active=False):
        b.button(text=f"📖 {s['title']}", callback_data=f"sl:s:{s['id']}")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "📚 <b>Hikoyalar kutubxonasi</b>\nHikoyani tanlab, bosqich matnlarini tahrirlang va "
                       "rasm/GIF biriktiring.", b.as_markup())


@router.callback_query(F.data.startswith("sl:s:"))
async def cb_lib_story(call: CallbackQuery, deps: Deps):
    sid = int(call.data.split(":")[2])
    story = await deps.stories.get_story(sid)
    b = InlineKeyboardBuilder()
    for st in await deps.stories.stages(sid):
        marks = ("🪤" if st["has_trap"] else "") + ("🖼" if st["media_file_id"] else "")
        b.button(text=f"{st['stage_no']}. {short(st['title'], 28)} {marks}".strip(), callback_data=f"sl:g:{st['id']}")
    b.button(text="⬅️ Orqaga", callback_data="a:lib")
    b.adjust(1)
    await render(call, f"📖 <b>{esc(story['title'])}</b>\n<i>{esc(story['genre'])}</i>\n\n"
                       "🪤 — tuzoq bosqichi, 🖼 — rasm/GIF biriktirilgan.", b.as_markup())


async def show_stage(event, deps: Deps, stage_id: int) -> None:
    st = await deps.stories.get_stage_by_id(stage_id)
    if not st:
        await render(event, "Bosqich topilmadi.", back_kb("a:lib"))
        return
    body = st["body"] if len(st["body"]) < 1500 else st["body"][:1500] + "…"
    text = (f"📖 <b>{esc(st['story_title'])}</b> · {st['stage_no']}-bosqich\n<b>{esc(st['title'])}</b>\n\n{esc(body)}\n\n"
            f"<i>Bog‘lovchi:</i> {esc(st['bridge']) or '—'}\n"
            f"🪤 Tuzoq: {'ha' if st['has_trap'] else 'yo‘q'} · 🖼 Rasm/GIF: "
            f"{'biriktirilgan (' + st['media_type'] + ')' if st['media_file_id'] else 'yo‘q'}")
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Sarlavha", callback_data=f"sl:e:{stage_id}:title")
    b.button(text="✏️ Matn", callback_data=f"sl:e:{stage_id}:body")
    b.button(text="✏️ Bog‘lovchi jumla", callback_data=f"sl:e:{stage_id}:bridge")
    if st["stage_no"] == 10:
        b.button(text="✏️ Yakuniy sahna", callback_data=f"sl:e:{stage_id}:final")
    else:
        b.button(text="🪤 Tuzoqni yoqish/o‘chirish", callback_data=f"sl:t:{stage_id}")
    b.button(text="🖼 Rasm/GIF biriktirish", callback_data=f"sl:m:{stage_id}")
    if st["media_file_id"]:
        b.button(text="🗑 Rasm/GIFni olib tashlash", callback_data=f"sl:x:{stage_id}")
    b.button(text="🎨 Rasm prompti (ingliz tilida)", callback_data=f"sl:p:{stage_id}")
    b.button(text="⬅️ Orqaga", callback_data=f"sl:s:{st['story_id']}")
    b.adjust(2, 1, 1, 1, 1, 1, 1)
    await render(event, text, b.as_markup())


@router.callback_query(F.data.startswith("sl:g:"))
async def cb_stage(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    await show_stage(call, deps, int(call.data.split(":")[2]))


@router.callback_query(F.data.startswith("sl:t:"))
async def cb_stage_trap(call: CallbackQuery, deps: Deps):
    sid = int(call.data.split(":")[2])
    st = await deps.stories.get_stage_by_id(sid)
    if st and st["stage_no"] < 10:
        await deps.stories.set_trap_flag(sid, not st["has_trap"])
    await show_stage(call, deps, sid)


@router.callback_query(F.data.startswith("sl:p:"))
async def cb_stage_prompt(call: CallbackQuery, deps: Deps):
    sid = int(call.data.split(":")[2])
    st = await deps.stories.get_stage_by_id(sid)
    await render(call, f"🎨 <b>{st['stage_no']}-bosqich rasm prompti</b>\n\n<code>{esc(st['image_prompt'])}</code>\n\n"
                       "Bu promptni istalgan bepul rasm generatoriga qo‘ying, so‘ng rasmni botga yuborib biriktiring.",
                 back_kb(f"sl:g:{sid}"))


@router.callback_query(F.data.startswith("sl:e:"))
async def cb_stage_edit(call: CallbackQuery, state: FSMContext):
    _, _, sid, field = call.data.split(":")
    await state.set_state(StoryEdit.value)
    await state.update_data(stage_id=int(sid), field=field)
    names = {"title": "sarlavha", "body": "hikoya matni", "bridge": "bog‘lovchi jumla", "final": "yakuniy sahna"}
    await render(call, f"✏️ Yangi <b>{names[field]}</b>ni yuboring (bitta xabar bilan):", back_kb(f"sl:g:{sid}", "❌ Bekor qilish"))


@router.message(StoryEdit.value, F.text)
async def stage_edit_value(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    text = (message.text or "").strip()
    if not text:
        await message.answer("Matn bo‘sh bo‘lmasin.")
        return
    await deps.stories.update_stage_text(data["stage_id"], data["field"], text)
    await state.clear()
    await message.answer("✅ Saqlandi.")
    await show_stage(message, deps, data["stage_id"])


@router.callback_query(F.data.startswith("sl:m:"))
async def cb_stage_media(call: CallbackQuery, state: FSMContext):
    sid = int(call.data.split(":")[2])
    await state.set_state(StoryEdit.media)
    await state.update_data(stage_id=sid)
    await render(call, "🖼 Shu bosqich uchun <b>rasm</b> yoki <b>GIF</b> yuboring.\n"
                       "<i>Rasm «Fayl» sifatida emas, oddiy rasm sifatida yuborilsin.</i>",
                 back_kb(f"sl:g:{sid}", "❌ Bekor qilish"))


@router.message(StoryEdit.media, F.photo | F.animation)
async def stage_media_received(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    if message.animation:
        await deps.stories.attach_media(data["stage_id"], message.animation.file_id, "animation")
    else:
        await deps.stories.attach_media(data["stage_id"], message.photo[-1].file_id, "photo")
    await state.clear()
    await message.answer("✅ Biriktirildi. Endi bu bosqichda guruhga shu rasm/GIF yuboriladi.")
    await show_stage(message, deps, data["stage_id"])


@router.message(StoryEdit.media)
async def stage_media_wrong(message: Message):
    await message.answer("Iltimos, rasm yoki GIF yuboring (matn emas).")


@router.callback_query(F.data.startswith("sl:x:"))
async def cb_stage_media_clear(call: CallbackQuery, deps: Deps):
    sid = int(call.data.split(":")[2])
    await deps.stories.clear_media(sid)
    await show_stage(call, deps, sid)


# ---------- natijalar va statistika ----------
@router.callback_query(F.data == "a:results")
async def cb_results(call: CallbackQuery, deps: Deps):
    games = await deps.games.list_finished_games(10)
    b = InlineKeyboardBuilder()
    for g in games:
        icon = "🏁" if g["status"] == "finished" else "🛑"
        b.button(text=f"{icon} #{g['id']} · {short(g['group_title'], 22)} · {short(g['story_title'], 18)}",
                 callback_data=f"rs:{g['id']}")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "🏆 <b>O‘yin natijalari</b>" + ("" if games else "\n\nHali yakunlangan o‘yin yo‘q."), b.as_markup())


@router.callback_query(F.data.startswith("rs:"))
async def cb_result(call: CallbackQuery, deps: Deps):
    gid = int(call.data.split(":")[1])
    g = await deps.games.get_game(gid)
    stats = await deps.games.stats(gid)
    head = (f"🎮 <b>O‘yin #{gid}</b> — {esc(g['group_title'])}\n📖 {esc(g['story_title'])}\n"
            f"{STATUS_LABEL[g['status']]} · yetilgan zina: <b>{g['max_stage_reached']}</b>\n\n")
    await render(call, head + format_stats(stats), back_kb("a:results"))


@router.callback_query(F.data == "a:stats")
async def cb_stats(call: CallbackQuery, deps: Deps):
    q = deps.db
    games = await q.fetchrow(
        "SELECT count(*) AS total, count(*) FILTER (WHERE status='finished') AS finished, "
        "count(*) FILTER (WHERE status='cancelled') AS cancelled, "
        "count(*) FILTER (WHERE status IN ('lobby','running','paused')) AS active FROM games")
    ans = await q.fetchrow(
        "SELECT count(*) AS total, count(*) FILTER (WHERE ok) AS correct FROM ("
        "SELECT COALESCE(is_correct, FALSE) AS ok FROM answers UNION ALL "
        "SELECT (v.choice_index = gt.correct_option) AS ok FROM votes v "
        "JOIN game_tasks gt ON gt.id=v.game_task_id) x")
    outcomes = await q.fetchrow(
        "SELECT count(*) FILTER (WHERE outcome='timeout') AS timeout, count(*) FILTER (WHERE outcome IS NOT NULL) AS total "
        "FROM game_tasks")
    players = await q.fetchval("SELECT count(*) FROM players")
    groups = await q.fetchval("SELECT count(*) FROM groups WHERE is_member")
    tasks = await q.fetchval("SELECT count(*) FROM tasks WHERE is_active")
    traps = await q.fetchval("SELECT count(*) FROM traps WHERE is_active")
    acc = f"{round(100 * ans['correct'] / ans['total'])}%" if ans["total"] else "—"
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"🎮 O‘yinlar: <b>{games['total']}</b> (yakunlangan {games['finished']}, bekor {games['cancelled']}, faol {games['active']})\n"
        f"👥 Faol guruhlar: <b>{groups}</b>\n🙋 Foydalanuvchilar: <b>{players}</b>\n"
        f"🧩 Topshiriqlar: <b>{tasks}</b> · 🪤 Tuzoqlar: <b>{traps}</b>\n"
        f"✍️ Berilgan javoblar: <b>{ans['total']}</b>, to‘g‘ri: <b>{ans['correct']}</b> (aniqlik {acc})\n"
        f"⏰ Vaqt tugagan topshiriqlar: <b>{outcomes['timeout']}</b> / {outcomes['total']}")
    await render(call, text, back_kb())


# ---------- sozlamalar ----------
async def show_settings(event, deps: Deps) -> None:
    s = deps.settings
    reveal = await s.get_bool("reveal_correct")
    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"• Noto‘g‘ri javobda to‘g‘ri variantni ko‘rsatish: <b>{'yoqilgan' if reveal else 'o‘chirilgan'}</b>\n"
        f"• Yangi topshiriq uchun standart vaqt: <b>{await s.get_int('default_time_limit')} soniya</b>\n"
        f"• Tuzoq topshirig‘i vaqti: <b>{await s.get_int('trap_time_limit')} soniya</b>\n"
        f"• Admin sessiyasi: <b>{deps.config.admin_session_hours} soat</b>\n\n"
        "🎞 O‘z GIF’ingizni «to‘g‘ri / noto‘g‘ri / g‘alaba» lahzalariga o‘rnatishingiz mumkin.")
    b = InlineKeyboardBuilder()
    b.button(text=f"{'🔕' if reveal else '🔔'} To‘g‘ri variantni ko‘rsatish", callback_data="st:t:reveal_correct")
    b.button(text="⏱ Standart vaqt", callback_data="st:v:default_time_limit")
    b.button(text="⏱ Tuzoq vaqti", callback_data="st:v:trap_time_limit")
    for kind, label in (("correct", "to‘g‘ri"), ("wrong", "noto‘g‘ri"), ("victory", "g‘alaba")):
        custom = await s.get_opt(f"gif_custom:{kind}")
        b.button(text=f"🎞 GIF: {label}{' ✔' if custom else ''}", callback_data=f"st:gif:{kind}")
    b.button(text="💾 Zaxira nusxasi (JSON)", callback_data="st:backup")
    b.button(text="🚪 Chiqish", callback_data="a:logout")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1, 2, 3, 1, 1, 1)
    await render(event, text, b.as_markup())


@router.callback_query(F.data == "a:settings")
async def cb_settings(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    await show_settings(call, deps)


@router.callback_query(F.data.startswith("st:t:"))
async def cb_setting_toggle(call: CallbackQuery, deps: Deps):
    key = call.data.split(":")[2]
    if key == "reveal_correct":
        await deps.settings.toggle(key)
    await show_settings(call, deps)


@router.callback_query(F.data.startswith("st:v:"))
async def cb_setting_value(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[2]
    if key not in ("default_time_limit", "trap_time_limit"):
        await call.answer()
        return
    await state.set_state(SettingEdit.value)
    await state.update_data(key=key)
    await render(call, "Yangi qiymatni soniyalarda yuboring (10 dan 3600 gacha):", back_kb("a:settings", "❌ Bekor qilish"))


@router.message(SettingEdit.value, F.text)
async def setting_value(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    try:
        val = int((message.text or "").strip())
        if not 10 <= val <= 3600:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, 10 dan 3600 gacha butun son yuboring.")
        return
    await deps.settings.set(data["key"], str(val))
    await state.clear()
    await message.answer("✅ Saqlandi.")
    await show_settings(message, deps)


@router.callback_query(F.data.startswith("st:gif:"))
async def cb_setting_gif(call: CallbackQuery, deps: Deps, state: FSMContext):
    kind = call.data.split(":")[2]
    custom = await deps.settings.get_opt(f"gif_custom:{kind}")
    b = InlineKeyboardBuilder()
    if custom:
        b.button(text="♻️ Standart GIFga qaytarish", callback_data=f"st:gifx:{kind}")
    b.button(text="⬅️ Orqaga", callback_data="a:settings")
    b.adjust(1)
    await state.set_state(SettingEdit.gif)
    await state.update_data(kind=kind)
    await render(call, "🎞 Shu lahza uchun <b>GIF</b> (animatsiya) yuboring:", b.as_markup())


@router.message(SettingEdit.gif, F.animation)
async def setting_gif_received(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    await deps.settings.set(f"gif_custom:{data['kind']}", message.animation.file_id)
    await state.clear()
    await message.answer("✅ GIF o‘rnatildi.")
    await show_settings(message, deps)


@router.message(SettingEdit.gif)
async def setting_gif_wrong(message: Message):
    await message.answer("GIF (animatsiya) yuboring.")


@router.callback_query(F.data.startswith("st:gifx:"))
async def cb_setting_gif_reset(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    await deps.settings.delete(f"gif_custom:{call.data.split(':')[2]}")
    await show_settings(call, deps)


@router.callback_query(F.data == "st:backup")
async def cb_backup(call: CallbackQuery, deps: Deps):
    data = await export_json(deps.db)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M")
    await call.answer()
    await call.message.answer_document(BufferedInputFile(data, filename=f"sirli-safar-zaxira-{stamp}.json"),
                                       caption="💾 Zaxira nusxasi. Xavfsiz joyda saqlang.")
