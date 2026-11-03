"""Individual topshiriqlar, matnli javobni admin baholashi, tuzoq tizimi, tasodifiy tanlash."""
import pytest
from aiogram.methods import AnswerCallbackQuery

from tests.conftest import ADMIN_ID

pytestmark = pytest.mark.asyncio

OPTS = dict(options=["to‘g‘ri", "xato"], correct_option=0)


def alerts(env):
    return [c for c in env.calls_of(AnswerCallbackQuery) if c.show_alert]


async def no_traps(env):
    await env.db.execute("UPDATE story_stages SET has_trap=FALSE")


# ------------------------------------------------------------------ tasodifiy tanlash
async def test_random_task_selection_only_from_current_stage(env):
    await env.only_tasks("test", per_stage=5)
    gid, players = await env.start_game()
    for _ in range(30):                       # 1-zinada xato javob: zina o‘zgarmaydi, yangi tasodifiy topshiriq
        await env.answer(gid, players[0], correct=False)
    rows = await env.db.fetch(
        "SELECT gt.stage_no, gt.task_id, t.stage_no AS task_stage FROM game_tasks gt "
        "JOIN tasks t ON t.id=gt.task_id WHERE gt.game_id=$1", gid)
    assert len(rows) == 31
    assert all(r["stage_no"] == 1 and r["task_stage"] == 1 for r in rows)
    assert len({r["task_id"] for r in rows}) >= 3         # tasodifiy tanlanyapti
    assert len(rows) > len({r["task_id"] for r in rows})  # bir o‘yinda takrorlanishi mumkin


# ------------------------------------------------------------------ individual topshiriqlar
async def test_individual_task_is_sent_privately_and_checked_automatically(env):
    await env.only_tasks("individual", **OPTS)
    await no_traps(env)
    gid, players = await env.start_game(n_players=3)
    gt = await env.active_task(gid)
    assert gt["kind"] == "individual" and gt["status"] == "open"
    user = gt["assigned_user_id"]
    assert user in players
    assert f"@talaba{user}, sizga maxsus topshiriq yuborildi!" in "\n".join(env.texts(-1001))
    assert any("Sizga maxsus topshiriq" in t for t in env.texts(user))      # shaxsiy chatga yuborildi
    assert not any("Savol 1.0" in t for t in env.texts(-1001) if "maxsus" not in t and "<b>1-zina" in t)
    other = next(p for p in players if p != user)
    assert (await env.deps.games.submit_choice(gt["id"], other, 0)).status == "not_yours"
    env.clear()
    await env.press(f"ans:{gt['id']}:0", user, message_id=gt["dm_message_id"])
    assert (await env.game(gid))["current_stage"] == 2
    assert "Bajarilgan" not in "\n".join(env.texts(-1001))
    stats = await env.deps.games.stats(gid)
    assert stats["individual_done"] == 1 and stats["correct"] == 1
    # qayta javob berib bo‘lmaydi
    assert (await env.deps.games.submit_choice(gt["id"], user, 0)).status in ("closed", "already")


async def test_individual_selection_is_fair_and_skips_unregistered(env):
    await env.only_tasks("individual", **OPTS)
    await no_traps(env)
    await env.add_group(-1001)
    ids = await env.add_players(3)
    ghost = (await env.add_players(1, start=500, dm_ok=False))[0]       # botga /start bosmagan
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    gid = await env.deps.games.create_game(-1001, sid, ADMIN_ID)
    await env.deps.flow.post_lobby(gid)
    for p in ids + [ghost]:
        await env.deps.games.join(gid, p)
    await env.deps.games.start(gid)
    await env.deps.flow.begin(gid)
    picks = []
    for _ in range(6):
        gt = await env.active_task(gid)
        picks.append(gt["assigned_user_id"])
        await env.press(f"ans:{gt['id']}:0", gt["assigned_user_id"], message_id=gt["dm_message_id"])
    assert ghost not in picks
    assert all(a != b for a, b in zip(picks, picks[1:]))                  # ketma-ket bir xil talaba emas
    counts = [picks.count(p) for p in ids]
    assert max(counts) - min(counts) <= 1 and sum(counts) == 6            # adolatli taqsimot


async def test_individual_dm_failure_reassigns_and_explains_in_group(env):
    await env.only_tasks("individual", **OPTS)
    await no_traps(env)
    await env.add_group(-1001)
    p1, p2 = await env.add_players(2)
    env.session.forbidden_chats.add(p1)                                   # p1 botni bloklagan
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    gid = await env.deps.games.create_game(-1001, sid, ADMIN_ID)
    await env.deps.flow.post_lobby(gid)
    for p in (p1, p2):
        await env.deps.games.join(gid, p)
    await env.deps.games.start(gid)
    await env.deps.flow.begin(gid)
    gt = await env.active_task(gid)
    assert gt["assigned_user_id"] == p2 and gt["status"] == "open"
    if not await env.db.fetchval("SELECT dm_ok FROM players WHERE tg_id=$1", p1):
        assert "botga shaxsiy /start bosmagan" in "\n".join(env.texts(-1001))


async def test_individual_all_dms_fail_pauses_instead_of_hanging(env):
    await env.only_tasks("individual", **OPTS)
    await no_traps(env)
    await env.add_group(-1001)
    ids = await env.add_players(2)
    env.session.forbidden_chats.update(ids)
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    gid = await env.deps.games.create_game(-1001, sid, ADMIN_ID)
    await env.deps.flow.post_lobby(gid)
    for p in ids:
        await env.deps.games.join(gid, p)
    await env.deps.games.start(gid)
    await env.deps.flow.begin(gid)
    assert (await env.game(gid))["status"] == "paused"
    assert "botga shaxsiy /start bosmagan" in "\n".join(env.texts(-1001))
    assert "faol topshiriq yo‘q" in "\n".join(env.texts(ADMIN_ID))


async def test_individual_text_answer_is_graded_by_admin_and_timeout_is_wrong(env):
    await env.only_tasks("individual")                                    # matnli individual
    await no_traps(env)
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    user = gt["assigned_user_id"]
    await env.send("Mening javobim: kitob bilim manbai", user)           # shaxsiy chatda javob
    assert "o‘qituvchiga yuborildi" in env.texts(user)[-1]
    review = [t for t in env.texts(ADMIN_ID) if "Javobni tekshiring" in t][-1]
    assert "kitob bilim manbai" in review
    await env.send("ikkinchi urinish", user)
    assert "allaqachon" in env.texts(user)[-1]
    await env.press(f"gr:{gt['id']}:1", ADMIN_ID)
    assert (await env.game(gid))["current_stage"] == 2
    # keyingisi: vaqt tugaydi → noto‘g‘ri
    await env.expire_now(gid)
    await env.deps.timer.tick()
    assert (await env.game(gid))["current_stage"] == 1
    last = await env.db.fetchrow("SELECT outcome,kind FROM game_tasks WHERE game_id=$1 AND seq=2", gid)
    assert (last["kind"], last["outcome"]) == ("individual", "timeout")


# ------------------------------------------------------------------ matnli / ijodiy javoblar
@pytest.mark.parametrize("kind", ["text", "creative"])
async def test_group_text_answer_goes_to_admin_who_grades(env, kind):
    await env.only_tasks(kind)
    await no_traps(env)
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    mid = gt["group_message_id"]
    outsider = (await env.add_players(1, start=900))[0]
    await env.send("begona javobi", outsider, chat_id=-1001, chat_type="supergroup", reply_to=mid)
    assert "ro‘yxatida yo‘q" in env.texts(-1001)[-1]
    await env.send("oddiy gap (reply emas)", players[0], chat_id=-1001, chat_type="supergroup")
    assert await env.db.fetchval("SELECT count(*) FROM answers") == 0
    await env.send("Jamoa javobi shu", players[0], chat_id=-1001, chat_type="supergroup", reply_to=mid)
    assert (await env.active_task(gid))["status"] == "awaiting_review"
    review = [t for t in env.texts(ADMIN_ID) if "Javobni tekshiring" in t][-1]
    assert "Jamoa javobi shu" in review
    await env.send("kech qolgan javob", players[1], chat_id=-1001, chat_type="supergroup", reply_to=mid)
    assert "allaqachon qabul qilingan" in env.texts(-1001)[-1]
    assert await env.db.fetchval("SELECT count(*) FROM answers") == 1
    assert (await env.game(gid))["current_stage"] == 1                  # baholanguncha zina o‘zgarmaydi
    env.clear()
    await env.press(f"gr:{gt['id']}:1", ADMIN_ID)
    assert (await env.game(gid))["current_stage"] == 2
    assert "1-zinadan 2-zinaga" in "\n".join(env.texts(-1001))          # natija guruhga e’lon qilindi
    await env.press(f"gr:{gt['id']}:0", ADMIN_ID)                       # ikkinchi marta bosish ta’sir qilmaydi
    assert (await env.game(gid))["current_stage"] == 2 and alerts(env)
    # NOTO‘G‘RI baho
    nxt = await env.active_task(gid)
    await env.send("yana javob", players[2], chat_id=-1001, chat_type="supergroup", reply_to=nxt["group_message_id"])
    await env.press(f"gr:{nxt['id']}:0", ADMIN_ID)
    assert (await env.game(gid))["current_stage"] == 1
    ans = await env.db.fetchrow("SELECT is_correct, graded_by FROM answers WHERE game_task_id=$1", nxt["id"])
    assert ans["is_correct"] is False and ans["graded_by"] == ADMIN_ID


async def test_only_admin_can_grade(env):
    await env.only_tasks("text")
    await no_traps(env)
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    await env.send("javob", players[0], chat_id=-1001, chat_type="supergroup", reply_to=gt["group_message_id"])
    env.clear()
    await env.press(f"gr:{gt['id']}:1", players[0])                      # talaba o‘zini baholamoqchi
    await env.press(f"gr:{gt['id']}:1", 777)
    assert len(alerts(env)) == 2
    assert (await env.game(gid))["current_stage"] == 1
    assert (await env.active_task(gid))["status"] == "awaiting_review"


async def test_grading_blocked_while_paused(env):
    await env.only_tasks("text")
    await no_traps(env)
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    await env.send("javob", players[0], chat_id=-1001, chat_type="supergroup", reply_to=gt["group_message_id"])
    await env.deps.games.pause(gid)
    env.clear()
    await env.press(f"gr:{gt['id']}:1", ADMIN_ID)
    assert alerts(env) and (await env.game(gid))["current_stage"] == 1
    await env.deps.games.resume(gid)
    await env.press(f"gr:{gt['id']}:1", ADMIN_ID)
    assert (await env.game(gid))["current_stage"] == 2


# ------------------------------------------------------------------ tuzoq
async def reach_trap(env, gid, players):
    for _ in range(4):                       # 1→5-zina
        await env.answer(gid, players[0], True)
    gt = await env.active_task(gid)
    assert gt["status"] == "needs_input" and gt["kind"] == "trap" and gt["stage_no"] == 5
    return gt


async def test_trap_admin_writes_prompt_and_grades_wrong_then_library_and_correct(env):
    await env.only_tasks("test")
    await env.login_admin()
    trap_id = await env.deps.tasks.create_trap(stage_no=5, prompt="Kutubxona tuzog‘i: 3 ta sinonim ayting", time_limit_sec=45)
    gid, players = await env.start_game()
    gt = await reach_trap(env, gid, players)
    texts = "\n".join(env.texts(-1001))
    assert "DIQQAT! Siz xavfli hududga kirib qoldingiz!" in texts      # hikoyadagi tuzoq hodisasi
    admin_msg = [t for t in env.texts(ADMIN_ID) if "Tuzoq vaqti" in t]
    assert admin_msg
    # 1) admin o‘zi yozadi
    await env.press(f"tp:own:{gt['id']}", ADMIN_ID)
    await env.send("Tuzoq: jamoa 3 ta maqol aytsin", ADMIN_ID)
    await env.press("tp:time:60", ADMIN_ID)
    trap = await env.active_task(gid)
    assert trap["status"] == "open" and trap["kind"] == "trap" and trap["time_limit_sec"] == 60
    assert "Tuzoq: jamoa 3 ta maqol aytsin" in "\n".join(env.texts(-1001))
    outsider = (await env.add_players(1, start=900))[0]
    await env.send("noto‘g‘ri odam", outsider, chat_id=-1001, chat_type="supergroup", reply_to=trap["group_message_id"])
    await env.send("Maqol: Ilm — nur", players[1], chat_id=-1001, chat_type="supergroup", reply_to=trap["group_message_id"])
    assert any("Tuzoq javobi" in t and "Ilm — nur" in t for t in env.texts(ADMIN_ID))
    assert await env.db.fetchval("SELECT count(*) FROM answers WHERE game_task_id=$1", trap["id"]) == 0
    await env.press(f"gr:{trap['id']}:0", ADMIN_ID)                    # NOTO‘G‘RI → bir zina pastga
    g = await env.game(gid)
    assert g["current_stage"] == 4 and g["cleared_traps"] == []
    assert "Tuzoq ishladi" in "\n".join(env.texts(-1001))
    # 2) qayta 5-zinaga chiqqanda tuzoq yana ishlaydi; kutubxonadan tanlanadi
    await env.answer(gid, players[0], True)
    gt2 = await env.active_task(gid)
    assert gt2["status"] == "needs_input" and gt2["stage_no"] == 5
    await env.press(f"tp:lib:{gt2['id']}", ADMIN_ID)
    await env.press(f"tp:use:{gt2['id']}:{trap_id}", ADMIN_ID)
    t2 = await env.active_task(gid)
    assert t2["status"] == "open" and t2["time_limit_sec"] == 45 and "Kutubxona tuzog‘i" in t2["question"]
    await env.press(f"gr:{t2['id']}:1", ADMIN_ID)                      # TO‘G‘RI → omon o‘tadi, BONUS YO‘Q
    g = await env.game(gid)
    assert g["current_stage"] == 5 and g["cleared_traps"] == [5]
    assert "Tuzoqdan omon o‘tdingiz" in "\n".join(env.texts(-1001))
    nxt = await env.active_task(gid)
    assert nxt["kind"] == "test" and nxt["stage_no"] == 5 and nxt["status"] == "open"
    await env.answer(gid, players[0], True)
    assert (await env.game(gid))["current_stage"] == 6                 # tuzoq qaytib ishlamaydi


async def test_trap_timeout_counts_as_wrong_and_cannot_be_graded_late(env):
    await env.only_tasks("test")
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await reach_trap(env, gid, players)
    await env.deps.games.set_trap(gt["id"], "Tuzoq", 30)
    await env.deps.flow.announce(gt["id"])
    trap = await env.active_task(gid)
    await env.expire_now(gid)
    late = await env.deps.games.grade(trap["id"], ADMIN_ID, True)       # admin kech qoldi
    assert late.status == "timeout"
    assert (await env.game(gid))["current_stage"] == 4
    row = await env.db.fetchrow("SELECT outcome FROM game_tasks WHERE id=$1", trap["id"])
    assert row["outcome"] == "timeout"
    await env.deps.flow.after_resolve(late.resolution)
    assert "Tuzoq vaqti tugadi" in "\n".join(env.texts(-1001))


async def test_trap_needs_input_survives_restart_and_can_be_reprompted(env):
    await env.only_tasks("test")
    await env.login_admin()
    gid, players = await env.start_game()
    gt = await reach_trap(env, gid, players)
    env.clear()
    await env.press(f"gx:kick:{gid}", ADMIN_ID)                         # “To‘xtab qolgan bosqichni davom ettirish”
    assert any("Tuzoq vaqti" in t for t in env.texts(ADMIN_ID))
    assert (await env.active_task(gid))["id"] == gt["id"]               # ikkinchi tuzoq yaratilmadi
