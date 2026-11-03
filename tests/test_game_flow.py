"""Zina mexanizmi, javoblar, vaqt, bir nechta guruh, qayta ishga tushish."""
import asyncio

import pytest
from aiogram.methods import SendAnimation, SendMessage, SendPhoto

from tests.conftest import ADMIN_ID

pytestmark = pytest.mark.asyncio


async def test_start_game_sends_story_stair_and_first_task(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    g = await env.game(gid)
    assert g["status"] == "running" and g["current_stage"] == 1
    gt = await env.active_task(gid)
    assert gt["status"] == "open" and gt["kind"] == "test" and gt["deadline_at"] is not None
    texts = "\n".join(env.texts(-1001))
    assert "SIRLI SAFAR boshlandi" in texts
    assert "1-bosqich" in texts            # hikoya matni yuborilgan
    assert env.calls_of(SendPhoto, -1001)  # zinapoya rasmi
    assert "Savol 1.0" in texts


async def test_correct_answer_moves_up(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    env.clear()
    await env.answer(gid, players[0], correct=True)
    g = await env.game(gid)
    assert g["current_stage"] == 2
    texts = "\n".join(env.texts(-1001))
    assert "To‘g‘ri" in texts and "1-zinadan 2-zinaga" in texts
    assert "2-bosqich" in texts                      # yangi hikoya bo‘lagi
    assert env.calls_of(SendAnimation, -1001)        # olqishlovchi GIF
    assert env.calls_of(SendPhoto, -1001)            # yangilangan zinapoya rasmi
    nxt = await env.active_task(gid)
    assert nxt["stage_no"] == 2 and nxt["status"] == "open"


async def test_wrong_answer_moves_down_and_floor_at_stage_1(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    # 1-zinada noto‘g‘ri javob: pastga tushmaydi
    await env.answer(gid, players[0], correct=False)
    assert (await env.game(gid))["current_stage"] == 1
    assert "1-zinada qoldi" in "\n".join(env.texts(-1001))
    # 2-zinaga chiqib, keyin xato: 1-zinaga qaytadi
    await env.answer(gid, players[0], correct=True)
    assert (await env.game(gid))["current_stage"] == 2
    env.clear()
    await env.answer(gid, players[1], correct=False)
    assert (await env.game(gid))["current_stage"] == 1
    assert "2-zinadan 1-zinaga" in "\n".join(env.texts(-1001))
    assert "To‘g‘ri javob: <b>A)" in "\n".join(env.texts(-1001))


async def test_reaching_stage_10_finishes_game_with_results(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    await env.answer(gid, players[0], correct=False)    # 1-zinada qoladi
    for i in range(9):
        await env.answer(gid, players[i % 3], correct=True)
    g = await env.game(gid)
    assert g["status"] == "finished" and g["current_stage"] == 10 and g["finished_at"]
    assert await env.active_task(gid) is None
    texts = "\n".join(env.texts(-1001))
    assert "G‘ALABA" in texts and "Yakuniy natijalar" in texts and "Eng faol talabalar" in texts
    assert "To‘g‘ri javoblar: <b>10</b>" in texts and "Noto‘g‘ri javoblar: <b>1</b>" in texts   # 9 javob + tuzoq
    assert "Bajarilgan individual topshiriqlar" in texts
    assert "Jamoa 10-zinaga" in texts or "10-bosqich" in texts   # yakuniy sahna
    assert "Yakuniy natijalar" in "\n".join(env.texts(1))        # adminning shaxsiy chatiga ham
    res = await env.db.fetchrow("SELECT * FROM results WHERE game_id=$1", gid)
    assert res["correct_count"] == 10 and res["wrong_count"] == 1 and res["final_stage"] == 10
    # o‘yin tugagach xuddi shu guruhda yangi o‘yin boshlash mumkin
    sid = await env.db.fetchval("SELECT id FROM stories WHERE slug='oxirgi-dalil'")
    assert await env.deps.games.create_game(-1001, sid, ADMIN_ID)


async def test_duplicate_answer_blocked(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    first = await env.deps.games.submit_choice(gt["id"], players[0], 1)   # noto‘g‘ri
    again = await env.deps.games.submit_choice(gt["id"], players[1], 0)   # to‘g‘ri bo‘lsa ham qabul qilinmaydi
    assert first.status == "ok" and again.status in ("closed", "already")
    assert await env.db.fetchval("SELECT count(*) FROM answers WHERE game_task_id=$1", gt["id"]) == 1
    assert (await env.game(gid))["current_stage"] == 1


async def test_concurrent_answers_only_one_counts(env):
    await env.only_tasks("test")
    gid, players = await env.start_game(n_players=6)
    gt = await env.active_task(gid)
    results = await asyncio.gather(*[env.deps.games.submit_choice(gt["id"], p, 0) for p in players])
    assert sorted(r.status for r in results).count("ok") == 1
    assert await env.db.fetchval("SELECT count(*) FROM answers WHERE game_task_id=$1", gt["id"]) == 1
    assert (await env.game(gid))["current_stage"] == 2          # aynan bitta zina


async def test_answer_and_timeout_race_gives_single_result(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    await env.expire_now(gid)
    results = await asyncio.gather(env.deps.games.submit_choice(gt["id"], players[0], 0),
                                   env.deps.games.expire(gt["id"]))
    resolved = [r for r in results if (getattr(r, "resolution", r) is not None)]
    assert len(resolved) == 1                                   # yagona natija
    row = await env.db.fetchrow("SELECT status,outcome FROM game_tasks WHERE id=$1", gt["id"])
    assert row["status"] == "resolved" and row["outcome"] == "timeout"   # deadline bo‘yicha — vaqt tugagan
    assert (await env.game(gid))["current_stage"] == 1


async def test_timeout_moves_down_via_timer(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    await env.answer(gid, players[0], correct=True)             # 2-zina
    await env.expire_now(gid)
    env.clear()
    await env.deps.timer.tick()
    g = await env.game(gid)
    assert g["current_stage"] == 1
    assert "Vaqt tugadi" in "\n".join(env.texts(-1001))
    row = await env.db.fetchrow("SELECT outcome FROM game_tasks WHERE game_id=$1 AND seq=2", gid)
    assert row["outcome"] == "timeout"
    nxt = await env.active_task(gid)
    assert nxt and nxt["stage_no"] == 1 and nxt["status"] == "open"


async def test_non_roster_user_cannot_answer(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    outsider = (await env.add_players(1, start=900))[0]
    gt = await env.active_task(gid)
    r = await env.deps.games.submit_choice(gt["id"], outsider, 0)
    assert r.status == "not_player"
    assert (await env.game(gid))["current_stage"] == 1


async def test_roster_frozen_after_start(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    late = (await env.add_players(1, start=950))[0]
    assert await env.deps.games.join(gid, late) == "closed"
    assert not await env.deps.games.is_in_roster(gid, late)


async def test_pause_blocks_answers_and_resume_shifts_deadline(env):
    await env.only_tasks("test", time_limit=60)
    gid, players = await env.start_game()
    gt = await env.active_task(gid)
    await env.deps.games.pause(gid)
    assert (await env.deps.games.submit_choice(gt["id"], players[0], 0)).status == "paused"
    # pauza davomida deadline o‘tib ketsa ham taymer o‘yinni “o‘ldirmaydi”
    await env.db.execute("UPDATE games SET paused_at = now() - interval '30 seconds' WHERE id=$1", gid)
    before = (await env.active_task(gid))["deadline_at"]
    await env.deps.timer.tick()
    assert (await env.game(gid))["current_stage"] == 1
    await env.deps.games.resume(gid)
    after = (await env.active_task(gid))["deadline_at"]
    assert 28 <= (after - before).total_seconds() <= 40          # ≈30 soniyaga surildi
    assert (await env.deps.games.submit_choice(gt["id"], players[0], 0)).status == "ok"


async def test_cancel_game(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    await env.deps.games.cancel(gid)
    await env.deps.flow.announce_cancel(gid)
    assert (await env.game(gid))["status"] == "cancelled"
    assert "bekor qilindi" in "\n".join(env.texts(-1001))
    assert await env.active_task(gid) is None


async def test_one_active_game_per_group_but_independent_groups(env):
    await env.only_tasks("test")
    g1, p1 = await env.start_game(chat_id=-1001, players_start=100)
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    from app.services.game_service import GameError
    with pytest.raises(GameError):
        await env.deps.games.create_game(-1001, sid, ADMIN_ID)      # bir guruhda ikkinchi faol o‘yin yo‘q
    g2, p2 = await env.start_game(chat_id=-1002, players_start=200, story_slug="songgi-kosmik-missiya")
    await env.answer(g1, p1[0], True)
    await env.answer(g1, p1[0], True)
    await env.answer(g2, p2[0], False)
    s1, s2 = (await env.game(g1))["current_stage"], (await env.game(g2))["current_stage"]
    assert (s1, s2) == (3, 1)                                        # natijalar bir-biriga ta’sir qilmaydi
    assert await env.db.fetchval("SELECT count(*) FROM game_tasks WHERE game_id=$1", g2) == 2


async def test_restart_recovers_running_game(env):
    """Server qayta ishga tushganda (yangi xotira) o‘yin bazadan tiklanadi."""
    from aiogram import Bot
    from app.deps import build_deps
    from app.main import build_dispatcher
    from app.services.timer_service import TimerService
    from tests.conftest import FakeSession, make_config

    await env.only_tasks("test")
    gid, players = await env.start_game()
    await env.answer(gid, players[0], True)                          # 2-zina, ochiq topshiriq bor
    open_task = await env.active_task(gid)

    # “qayta ishga tushish”: butunlay yangi obyektlar, baza o‘sha-o‘sha
    session2 = FakeSession()
    deps2 = build_deps(make_config(), env.db, Bot("123456:TESTTOKEN", session=session2))
    await deps2.flow.init()
    deps2.timer = TimerService(deps2.games, deps2.flow, interval=0.1)
    assert (await deps2.games.get_game(gid))["current_stage"] == 2
    # ochiq topshiriqqa javob yangi jarayonda ishlaydi
    r = await deps2.games.submit_choice(open_task["id"], players[1], 0)
    assert r.status == "ok"
    await deps2.flow.after_resolve(r.resolution)
    assert (await deps2.games.get_game(gid))["current_stage"] == 3

    # uxlab turganda muddat o‘tgan topshiriq uyg‘onganda hal qilinadi
    await env.expire_now(gid)
    await deps2.timer.tick()
    assert (await deps2.games.get_game(gid))["current_stage"] == 2

    # faol topshiriq “yo‘qolib” qolgan holatni ham tiklaydi (crash: natija yozildi, keyingisi yaratilmadi)
    await env.db.execute("UPDATE game_tasks SET status='resolved', outcome='correct', "
                         "resolved_at = now() WHERE game_id=$1 AND status='open'", gid)
    await env.db.execute("UPDATE game_tasks SET resolved_at = now() - interval '1 minute' "
                         "WHERE game_id=$1 AND resolved_at IS NOT NULL", gid)
    assert await env.active_task(gid) is None
    await deps2.timer.tick()
    revived = await env.active_task(gid)
    assert revived and revived["status"] == "open"
    assert any(getattr(c, "chat_id", None) == -1001 for c in session2.calls)


async def test_no_tasks_at_stage_pauses_instead_of_crashing(env):
    await env.only_tasks("test")
    gid, players = await env.start_game()
    await env.db.execute("DELETE FROM tasks WHERE stage_no=2")        # admin 2-zina topshiriqlarini o‘chirdi
    env.clear()
    await env.answer(gid, players[0], True)
    assert (await env.game(gid))["status"] == "paused"
    assert "topshiriq yo‘q" in "\n".join(env.texts(ADMIN_ID))


async def test_game_refuses_to_start_without_tasks_or_players(env):
    await env.only_tasks("test", stages=range(1, 6))                   # 6–9 zinalarda topshiriq yo‘q
    await env.add_group(-1001)
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    gid = await env.deps.games.create_game(-1001, sid, ADMIN_ID)
    problems = await env.deps.games.preflight(gid)
    assert any("6-zina" in p for p in problems) and any("Ro‘yxatga hech kim" in p for p in problems)
    from app.services.game_service import GameError
    with pytest.raises(GameError):
        await env.deps.games.start(gid)
