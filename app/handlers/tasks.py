"""Admin: topshiriqlar va tuzoq topshiriqlarini boshqarish; o‘yin paytida tuzoq berish."""
from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.deps import Deps
from app.handlers.states import TaskAdd, TaskEdit, TrapAdd, TrapEdit, TrapOwn
from app.middlewares.admin_gate import AdminGate
from app.services.game_service import GameError
from app.services.task_service import KIND_SHORT, KINDS, LETTERS, TaskError
from app.utils.tg import esc, fmt_limit
from app.utils.ui import back_kb, render, short

log = logging.getLogger(__name__)
router = Router(name="admin-tasks")
router.message.filter(F.chat.type == "private")
router.message.middleware(AdminGate())
router.callback_query.middleware(AdminGate())

TIME_CHOICES = [30, 60, 90, 120, 180, 300]
KIND_BUTTONS = [
    ("test", "A. Variantli test"), ("text", "B. Matnli savol"),
    ("individual_opts", "C. Individual (variantli)"), ("individual_text", "C. Individual (matnli)"),
    ("creative", "D. Ijodiy topshiriq"),
]


def _time_kb(prefix: str, back: str):
    b = InlineKeyboardBuilder()
    for sec in TIME_CHOICES:
        b.button(text=fmt_limit(sec), callback_data=f"{prefix}:{sec}")
    b.button(text="❌ Bekor qilish", callback_data=back)
    b.adjust(3, 3, 1)
    return b.as_markup()


def _parse_options(text: str) -> list[str]:
    out = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[A-Da-d][\)\.\:]|\d[\)\.])\s*", "", line).strip()
        if line:
            out.append(line)
    return out


def _task_card(t: dict) -> str:
    kind = KIND_SHORT[t["kind"]] + (" (variantli)" if t["kind"] == "individual" and t["options"]
                                    else " (matnli)" if t["kind"] == "individual" else "")
    lines = [f"🧩 <b>Topshiriq #{t['id']}</b> — {t['stage_no']}-zina", f"Turi: <b>{kind}</b>",
             f"⏱ Vaqt: <b>{fmt_limit(t['time_limit_sec'])}</b>" + (" · demo" if t["is_demo"] else ""), "",
             esc(t["question"])]
    for i, o in enumerate(t["options"]):
        lines.append(f"{'✅' if i == t['correct_option'] else '▫️'} <b>{LETTERS[i]})</b> {esc(o)}")
    return "\n".join(lines)


# ====================================================================== topshiriqlar ro‘yxati
@router.callback_query(F.data == "a:tasks")
async def cb_tasks(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    counts = await deps.tasks.count_by_stage()
    b = InlineKeyboardBuilder()
    for n in range(1, 10):
        c = counts.get(n, 0)
        b.button(text=f"{n}-zina · {c} ta{' ⚠️' if not c else ''}", callback_data=f"tk:l:{n}")
    b.button(text="➕ Yangi topshiriq", callback_data="tk:add:0")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(3, 3, 3, 1, 1)
    await render(call, "🧩 <b>Topshiriqlar</b>\nHar bir zina uchun istalgancha topshiriq qo‘shing — o‘yinda ular "
                       "tasodifiy tanlanadi. ⚠️ — topshirig‘i yo‘q zina (o‘yin boshlanmaydi).", b.as_markup())


@router.callback_query(F.data.startswith("tk:l:"))
async def cb_task_list(call: CallbackQuery, deps: Deps):
    stage = int(call.data.split(":")[2])
    tasks = await deps.tasks.list_tasks(stage)
    b = InlineKeyboardBuilder()
    for t in tasks:
        b.button(text=f"#{t['id']} · {KIND_SHORT[t['kind']]} · {short(t['question'], 34)}", callback_data=f"tk:v:{t['id']}")
    b.button(text="➕ Shu zinaga qo‘shish", callback_data=f"tk:add:{stage}")
    b.button(text="⬅️ Orqaga", callback_data="a:tasks")
    b.adjust(1)
    await render(call, f"🧩 <b>{stage}-zina topshiriqlari</b> ({len(tasks)} ta)", b.as_markup())


async def _show_task(event, deps: Deps, task_id: int) -> None:
    t = await deps.tasks.get_task(task_id)
    if not t:
        await render(event, "Topshiriq topilmadi.", back_kb("a:tasks"))
        return
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Savol", callback_data=f"tk:e:{t['id']}:question")
    b.button(text="⏱ Vaqt", callback_data=f"tk:e:{t['id']}:time")
    b.button(text="🔢 Zina", callback_data=f"tk:e:{t['id']}:stage")
    if t["kind"] in ("test", "individual") and t["options"]:
        b.button(text="🔤 Variantlar", callback_data=f"tk:e:{t['id']}:options")
        b.button(text="✅ To‘g‘ri javob", callback_data=f"tk:e:{t['id']}:correct")
    b.button(text="🗑 O‘chirish", callback_data=f"tk:d:{t['id']}")
    b.button(text="⬅️ Orqaga", callback_data=f"tk:l:{t['stage_no']}")
    b.adjust(3, 2, 1, 1)
    await render(event, _task_card(t), b.as_markup())


@router.callback_query(F.data.startswith("tk:v:"))
async def cb_task_view(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    await _show_task(call, deps, int(call.data.split(":")[2]))


@router.callback_query(F.data.startswith("tk:d:"))
async def cb_task_delete(call: CallbackQuery, deps: Deps):
    tid = int(call.data.split(":")[2])
    b = InlineKeyboardBuilder()
    b.button(text="🗑 Ha, o‘chirish", callback_data=f"tk:dok:{tid}")
    b.button(text="⬅️ Yo‘q", callback_data=f"tk:v:{tid}")
    b.adjust(1)
    await render(call, "Topshiriqni o‘chirasizmi? (Avvalgi o‘yinlar tarixi saqlanadi.)", b.as_markup())


@router.callback_query(F.data.startswith("tk:dok:"))
async def cb_task_delete_ok(call: CallbackQuery, deps: Deps):
    tid = int(call.data.split(":")[2])
    t = await deps.tasks.get_task(tid)
    await deps.tasks.delete_task(tid)
    await call.answer("O‘chirildi")
    await render(call, "🗑 Topshiriq o‘chirildi.", back_kb(f"tk:l:{t['stage_no']}" if t else "a:tasks"))


# ====================================================================== qo‘shish (FSM)
@router.callback_query(F.data.startswith("tk:add:"))
async def cb_task_add(call: CallbackQuery, state: FSMContext):
    stage = int(call.data.split(":")[2])
    await state.clear()
    if stage:
        await state.update_data(stage=stage)
        await _ask_kind(call, state)
        return
    await state.set_state(TaskAdd.stage)
    b = InlineKeyboardBuilder()
    for n in range(1, 10):
        b.button(text=f"{n}-zina", callback_data=f"tk:st:{n}")
    b.button(text="❌ Bekor qilish", callback_data="a:tasks")
    b.adjust(3, 3, 3, 1)
    await render(call, "Qaysi zina uchun topshiriq qo‘shamiz?", b.as_markup())


@router.callback_query(TaskAdd.stage, F.data.startswith("tk:st:"))
async def cb_task_stage(call: CallbackQuery, state: FSMContext):
    await state.update_data(stage=int(call.data.split(":")[2]))
    await _ask_kind(call, state)


async def _ask_kind(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TaskAdd.kind)
    b = InlineKeyboardBuilder()
    for key, label in KIND_BUTTONS:
        b.button(text=label, callback_data=f"tk:k:{key}")
    b.button(text="❌ Bekor qilish", callback_data="a:tasks")
    b.adjust(1)
    await render(call, "Topshiriq turini tanlang:\n\n"
                       "• <b>Test</b> — A/B/C/D, bot avtomatik tekshiradi\n"
                       "• <b>Matnli</b> / <b>Ijodiy</b> — guruh matn yozadi, siz baholaysiz\n"
                       "• <b>Individual</b> — tasodifiy talabaga shaxsiy chatda beriladi", b.as_markup())


@router.callback_query(TaskAdd.kind, F.data.startswith("tk:k:"))
async def cb_task_kind(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[2]
    kind = "individual" if key.startswith("individual") else key
    await state.update_data(kind=kind, with_options=key in ("test", "individual_opts"))
    await state.set_state(TaskAdd.question)
    await render(call, "✍️ Savol (topshiriq) matnini yuboring:", back_kb("a:tasks", "❌ Bekor qilish"))


@router.message(TaskAdd.question, F.text)
async def task_question(message: Message, state: FSMContext):
    q = (message.text or "").strip()
    if not q:
        await message.answer("Matn bo‘sh bo‘lmasin.")
        return
    await state.update_data(question=q)
    data = await state.get_data()
    if data["with_options"]:
        await state.set_state(TaskAdd.options)
        await message.answer("🔤 Javob variantlarini yuboring — <b>har bir variant yangi qatorda</b> (2 tadan 4 tagacha):\n"
                             "<code>Toshkent\nSamarqand\nBuxoro\nXiva</code>")
    else:
        await state.set_state(TaskAdd.time)
        await message.answer("⏱ Javob uchun vaqtni tanlang yoki soniyada yozing (10–3600):", reply_markup=_time_kb("tk:t", "a:tasks"))


@router.message(TaskAdd.options, F.text)
async def task_options(message: Message, state: FSMContext):
    opts = _parse_options(message.text or "")
    if not 2 <= len(opts) <= 4:
        await message.answer("2 dan 4 gacha variant yuboring (har biri yangi qatorda).")
        return
    await state.update_data(options=opts)
    await state.set_state(TaskAdd.correct)
    b = InlineKeyboardBuilder()
    text = ["✅ To‘g‘ri javobni tanlang:"]
    for i, o in enumerate(opts):
        text.append(f"<b>{LETTERS[i]})</b> {esc(o)}")
        b.button(text=LETTERS[i], callback_data=f"tk:c:{i}")
    b.adjust(len(opts))
    await message.answer("\n".join(text), reply_markup=b.as_markup())


@router.callback_query(TaskAdd.correct, F.data.startswith("tk:c:"))
async def cb_task_correct(call: CallbackQuery, state: FSMContext):
    await state.update_data(correct=int(call.data.split(":")[2]))
    await state.set_state(TaskAdd.time)
    await render(call, "⏱ Javob uchun vaqtni tanlang yoki soniyada yozing (10–3600):", _time_kb("tk:t", "a:tasks"))


async def _save_task(event, state: FSMContext, deps: Deps, seconds: int, user_id: int) -> None:
    data = await state.get_data()
    try:
        tid = await deps.tasks.create_task(
            stage_no=data["stage"], kind=data["kind"], question=data["question"], time_limit_sec=seconds,
            options=data.get("options"), correct_option=data.get("correct"), created_by=user_id)
    except TaskError as exc:
        await render(event, f"❌ {esc(exc)}", back_kb("a:tasks"))
        await state.clear()
        return
    await state.clear()
    b = InlineKeyboardBuilder()
    b.button(text="➕ Yana qo‘shish", callback_data=f"tk:add:{data['stage']}")
    b.button(text="📋 Ko‘rish", callback_data=f"tk:v:{tid}")
    b.button(text="⬅️ Topshiriqlar", callback_data="a:tasks")
    b.adjust(2, 1)
    await render(event, f"✅ Topshiriq #{tid} saqlandi ({data['stage']}-zina, {fmt_limit(seconds)}).", b.as_markup())


@router.callback_query(TaskAdd.time, F.data.startswith("tk:t:"))
async def cb_task_time(call: CallbackQuery, state: FSMContext, deps: Deps):
    await _save_task(call, state, deps, int(call.data.split(":")[2]), call.from_user.id)


@router.message(TaskAdd.time, F.text)
async def task_time_text(message: Message, state: FSMContext, deps: Deps):
    try:
        sec = int((message.text or "").strip())
    except ValueError:
        await message.answer("Soniyani raqam bilan yozing (masalan, 90).")
        return
    if not 10 <= sec <= 3600:
        await message.answer("Vaqt 10 dan 3600 soniyagacha bo‘lishi kerak.")
        return
    await _save_task(message, state, deps, sec, message.from_user.id)


# ====================================================================== tahrirlash
@router.callback_query(F.data.startswith("tk:e:"))
async def cb_task_edit(call: CallbackQuery, state: FSMContext, deps: Deps):
    _, _, tid, field = call.data.split(":")
    tid = int(tid)
    task = await deps.tasks.get_task(tid)
    if not task:
        await call.answer("Topshiriq topilmadi", show_alert=True)
        return
    await state.set_state(TaskEdit.value)
    await state.update_data(task_id=tid, field=field)
    back = back_kb(f"tk:v:{tid}", "❌ Bekor qilish")
    if field == "correct":
        b = InlineKeyboardBuilder()
        for i, o in enumerate(task["options"]):
            b.button(text=f"{LETTERS[i]}) {short(o, 30)}", callback_data=f"tk:ec:{i}")
        b.button(text="❌ Bekor qilish", callback_data=f"tk:v:{tid}")
        b.adjust(1)
        await render(call, "To‘g‘ri variantni tanlang:", b.as_markup())
    elif field == "stage":
        b = InlineKeyboardBuilder()
        for n in range(1, 10):
            b.button(text=f"{n}", callback_data=f"tk:ec:{n}")
        b.button(text="❌ Bekor qilish", callback_data=f"tk:v:{tid}")
        b.adjust(5, 4, 1)
        await render(call, "Qaysi zinaga ko‘chiramiz?", b.as_markup())
    else:
        prompts = {"question": "✍️ Yangi savol matnini yuboring:",
                   "time": "⏱ Yangi vaqtni soniyada yuboring (10–3600):",
                   "options": "🔤 Yangi variantlarni yuboring (har biri yangi qatorda, 2–4 ta). To‘g‘ri javob A variantga o‘rnatiladi — "
                              "keyin «To‘g‘ri javob» orqali o‘zgartiring:"}
        await render(call, prompts[field], back)


@router.callback_query(TaskEdit.value, F.data.startswith("tk:ec:"))
async def cb_task_edit_choice(call: CallbackQuery, state: FSMContext, deps: Deps):
    data = await state.get_data()
    val = int(call.data.split(":")[2])
    try:
        await deps.tasks.update_field(data["task_id"], data["field"], val)
    except TaskError as exc:
        await call.answer(str(exc), show_alert=True)
        return
    await state.clear()
    await call.answer("Saqlandi")
    await _show_task(call, deps, data["task_id"])


@router.message(TaskEdit.value, F.text)
async def task_edit_value(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    field = data["field"]
    try:
        if field == "options":
            await deps.tasks.update_field(data["task_id"], "options", _parse_options(message.text or ""))
            await deps.tasks.update_field(data["task_id"], "correct", 0)
        elif field == "time":
            await deps.tasks.update_field(data["task_id"], "time", int((message.text or "").strip()))
        elif field == "question":
            await deps.tasks.update_field(data["task_id"], "question", message.text or "")
        else:
            return
    except (TaskError, ValueError) as exc:
        await message.answer(f"❌ {esc(exc) if isinstance(exc, TaskError) else 'Raqam yuboring.'}")
        return
    await state.clear()
    t = await deps.tasks.get_task(data["task_id"])
    await message.answer("✅ Saqlandi.\n\n" + _task_card(t), reply_markup=back_kb(f"tk:v:{t['id']}", "📋 Topshiriqqa qaytish"))


# ====================================================================== tuzoq kutubxonasi
@router.callback_query(F.data == "a:traps")
async def cb_traps(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    traps = await deps.tasks.list_traps()
    b = InlineKeyboardBuilder()
    for t in traps:
        b.button(text=f"#{t['id']} · {t['stage_no']}-zina · {short(t['prompt'], 34)}", callback_data=f"tr:v:{t['id']}")
    b.button(text="➕ Yangi tuzoq", callback_data="tr:add")
    b.button(text="⬅️ Orqaga", callback_data="a:menu")
    b.adjust(1)
    await render(call, "🪤 <b>Tuzoq topshiriqlari</b>\nTuzoq paytida siz shu kutubxonadan tanlashingiz yoki o‘zingiz "
                       "yangi topshiriq yozishingiz mumkin. Hikoya bosqichida tuzoq belgisini «Hikoyalar kutubxonasi» "
                       "orqali yoqasiz/o‘chirasiz.", b.as_markup())


@router.callback_query(F.data.startswith("tr:v:"))
async def cb_trap_view(call: CallbackQuery, deps: Deps, state: FSMContext):
    await state.clear()
    t = await deps.tasks.get_trap(int(call.data.split(":")[2]))
    if not t:
        await render(call, "Topilmadi.", back_kb("a:traps"))
        return
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Matn", callback_data=f"tr:e:{t['id']}:prompt")
    b.button(text="⏱ Vaqt", callback_data=f"tr:e:{t['id']}:time")
    b.button(text="🗑 O‘chirish", callback_data=f"tr:d:{t['id']}")
    b.button(text="⬅️ Orqaga", callback_data="a:traps")
    b.adjust(2, 1, 1)
    await render(call, f"🪤 <b>Tuzoq #{t['id']}</b> · {t['stage_no']}-zina · ⏱ {fmt_limit(t['time_limit_sec'])}\n\n{esc(t['prompt'])}",
                 b.as_markup())


@router.callback_query(F.data.startswith("tr:d:"))
async def cb_trap_delete(call: CallbackQuery, deps: Deps):
    tid = int(call.data.split(":")[2])
    await deps.tasks.delete_trap(tid)
    await call.answer("O‘chirildi")
    await render(call, "🗑 Tuzoq o‘chirildi.", back_kb("a:traps"))


@router.callback_query(F.data == "tr:add")
async def cb_trap_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(TrapAdd.stage)
    b = InlineKeyboardBuilder()
    for n in range(1, 10):
        b.button(text=f"{n}-zina", callback_data=f"tr:st:{n}")
    b.button(text="❌ Bekor qilish", callback_data="a:traps")
    b.adjust(3, 3, 3, 1)
    await render(call, "Tuzoq qaysi zina uchun mo‘ljallangan?", b.as_markup())


@router.callback_query(TrapAdd.stage, F.data.startswith("tr:st:"))
async def cb_trap_stage(call: CallbackQuery, state: FSMContext):
    await state.update_data(stage=int(call.data.split(":")[2]))
    await state.set_state(TrapAdd.prompt)
    await render(call, "✍️ Tuzoq topshirig‘i matnini yuboring:", back_kb("a:traps", "❌ Bekor qilish"))


@router.message(TrapAdd.prompt, F.text)
async def trap_prompt(message: Message, state: FSMContext):
    await state.update_data(prompt=(message.text or "").strip())
    await state.set_state(TrapAdd.time)
    await message.answer("⏱ Vaqtni tanlang yoki soniyada yozing:", reply_markup=_time_kb("tr:t", "a:traps"))


async def _save_trap(event, state: FSMContext, deps: Deps, sec: int, uid: int) -> None:
    data = await state.get_data()
    try:
        tid = await deps.tasks.create_trap(stage_no=data["stage"], prompt=data["prompt"], time_limit_sec=sec, created_by=uid)
    except TaskError as exc:
        await render(event, f"❌ {esc(exc)}", back_kb("a:traps"))
        await state.clear()
        return
    await state.clear()
    await render(event, f"✅ Tuzoq #{tid} saqlandi.", back_kb("a:traps", "🪤 Tuzoqlar"))


@router.callback_query(TrapAdd.time, F.data.startswith("tr:t:"))
async def cb_trap_time(call: CallbackQuery, state: FSMContext, deps: Deps):
    await _save_trap(call, state, deps, int(call.data.split(":")[2]), call.from_user.id)


@router.message(TrapAdd.time, F.text)
async def trap_time_text(message: Message, state: FSMContext, deps: Deps):
    try:
        sec = int((message.text or "").strip())
    except ValueError:
        await message.answer("Soniyani raqam bilan yozing.")
        return
    await _save_trap(message, state, deps, sec, message.from_user.id)


@router.callback_query(F.data.startswith("tr:e:"))
async def cb_trap_edit(call: CallbackQuery, state: FSMContext):
    _, _, tid, field = call.data.split(":")
    await state.set_state(TrapEdit.value)
    await state.update_data(trap_id=int(tid), field=field)
    await render(call, "✍️ Yangi matnni yuboring:" if field == "prompt" else "⏱ Yangi vaqtni soniyada yuboring (10–3600):",
                 back_kb(f"tr:v:{tid}", "❌ Bekor qilish"))


@router.message(TrapEdit.value, F.text)
async def trap_edit_value(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    try:
        value = (message.text or "").strip()
        await deps.tasks.update_trap(data["trap_id"], data["field"], int(value) if data["field"] == "time" else value)
    except (TaskError, ValueError) as exc:
        await message.answer(f"❌ {esc(exc) if isinstance(exc, TaskError) else 'Raqam yuboring.'}")
        return
    await state.clear()
    await message.answer("✅ Saqlandi.", reply_markup=back_kb(f"tr:v:{data['trap_id']}", "🪤 Tuzoqqa qaytish"))


# ====================================================================== o‘yin paytida tuzoq berish
@router.callback_query(F.data.startswith("tp:own:"))
async def cb_trap_own(call: CallbackQuery, state: FSMContext, deps: Deps):
    gt_id = int(call.data.split(":")[2])
    gt = await deps.games.get_task(gt_id)
    if not gt or gt["status"] != "needs_input":
        await call.answer("Bu tuzoq allaqachon e’lon qilingan yoki yopilgan.", show_alert=True)
        return
    await state.set_state(TrapOwn.text)
    await state.update_data(gt_id=gt_id)
    await render(call, "✍️ Tuzoq topshirig‘ini yozing — u guruhga yuboriladi:")


@router.message(TrapOwn.text, F.text)
async def trap_own_text(message: Message, state: FSMContext, deps: Deps):
    await state.update_data(prompt=(message.text or "").strip())
    await state.set_state(TrapOwn.time)
    await message.answer("⏱ Vaqtni tanlang:", reply_markup=_time_kb("tp:time", "a:menu"))


@router.callback_query(TrapOwn.time, F.data.startswith("tp:time:"))
async def cb_trap_own_time(call: CallbackQuery, state: FSMContext, deps: Deps):
    data = await state.get_data()
    await state.clear()
    await _publish_trap(call, deps, data["gt_id"], data["prompt"], int(call.data.split(":")[2]))


@router.message(TrapOwn.time, F.text)
async def trap_own_time_text(message: Message, state: FSMContext, deps: Deps):
    data = await state.get_data()
    try:
        sec = int((message.text or "").strip())
    except ValueError:
        await message.answer("Soniyani raqam bilan yozing.")
        return
    await state.clear()
    await _publish_trap(message, deps, data["gt_id"], data["prompt"], sec)


@router.callback_query(F.data.startswith("tp:lib:"))
async def cb_trap_lib(call: CallbackQuery, deps: Deps):
    gt_id = int(call.data.split(":")[2])
    gt = await deps.games.get_task(gt_id)
    if not gt or gt["status"] != "needs_input":
        await call.answer("Bu tuzoq allaqachon e’lon qilingan yoki yopilgan.", show_alert=True)
        return
    traps = await deps.tasks.list_traps(gt["story_id"], gt["stage_no"])
    if not traps:
        await call.answer("Kutubxonada tuzoq yo‘q. «O‘zim yozaman»ni tanlang.", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for t in traps[:12]:
        b.button(text=short(t["prompt"], 48), callback_data=f"tp:use:{gt_id}:{t['id']}")
    b.button(text="✍️ O‘zim yozaman", callback_data=f"tp:own:{gt_id}")
    b.adjust(1)
    await render(call, "📚 Tuzoqni tanlang:", b.as_markup())


@router.callback_query(F.data.startswith("tp:use:"))
async def cb_trap_use(call: CallbackQuery, deps: Deps):
    _, _, gt_id, trap_id = call.data.split(":")
    trap = await deps.tasks.get_trap(int(trap_id))
    if not trap:
        await call.answer("Tuzoq topilmadi", show_alert=True)
        return
    await _publish_trap(call, deps, int(gt_id), trap["prompt"], trap["time_limit_sec"])


async def _publish_trap(event, deps: Deps, gt_id: int, prompt: str, seconds: int) -> None:
    try:
        ok = await deps.games.set_trap(gt_id, prompt, seconds)
    except GameError as exc:
        await render(event, f"❌ {esc(exc)}")
        return
    if not ok:
        await render(event, "Bu tuzoq allaqachon e’lon qilingan yoki yopilgan.")
        return
    await render(event, "🪤 Tuzoq guruhga yuborilmoqda… Natijani baholash tugmalari alohida xabarda keladi.")
    await deps.flow.announce(gt_id)
