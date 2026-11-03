"""Admin kirishi, begona foydalanuvchi, guruh ro‘yxati, hikoya tanlash, o‘yin yaratish, topshiriq boshqaruvi."""
import logging

import pytest
from aiogram.methods import AnswerCallbackQuery, DeleteMessage, LeaveChat, SendDocument, SendMessage

from tests.conftest import ADMIN_ID, ADMIN_PASSWORD

pytestmark = pytest.mark.asyncio


def alerts(env):
    return [c for c in env.calls_of(AnswerCallbackQuery) if c.show_alert]


def buttons(markup):
    return [(b.text, b.callback_data, b.url) for row in markup.inline_keyboard for b in row]


async def test_admin_login_with_password_and_session(env, caplog):
    caplog.set_level(logging.DEBUG)
    await env.send("/admin", ADMIN_ID)
    assert "parolini kiriting" in env.texts(ADMIN_ID)[-1]
    await env.send(ADMIN_PASSWORD, ADMIN_ID)
    assert "boshqaruv paneli" in env.texts(ADMIN_ID)[-1]
    assert env.calls_of(DeleteMessage)                                # parol xabari chatdan o‘chirildi
    assert ADMIN_PASSWORD not in caplog.text                          # parol jurnalga tushmagan
    assert await env.deps.auth.is_authenticated(ADMIN_ID)
    stored = await env.db.fetchval("SELECT authenticated_until FROM admins WHERE tg_id=$1", ADMIN_ID)
    assert stored is not None
    labels = [t for t, _, _ in buttons(env.last_markup(ADMIN_ID))]
    for needed in ("Yangi o‘yin yaratish", "Faol o‘yinlar", "Guruhlar", "Hikoyalar kutubxonasi", "Topshiriqlar",
                   "Tuzoq topshiriqlari", "O‘yin natijalari", "Statistika", "Sozlamalar"):
        assert any(needed in l for l in labels), needed


async def test_wrong_password_limit_locks_admin(env):
    await env.send("/admin", ADMIN_ID)
    for _ in range(5):
        await env.send("noto‘g‘ri-parol", ADMIN_ID)
    assert "bloklandi" in env.texts(ADMIN_ID)[-1]
    await env.send("/admin", ADMIN_ID)
    assert "limiti tugagan" in env.texts(ADMIN_ID)[-1]
    assert not await env.deps.auth.is_authenticated(ADMIN_ID)
    # blok davomida to‘g‘ri parol ham o‘tmaydi
    res = await env.deps.auth.login(ADMIN_ID, "Admin", ADMIN_PASSWORD)
    assert res.status == "locked"


async def test_stranger_cannot_become_admin(env):
    await env.send("/admin", 777)
    assert "faqat adminlar" in env.texts(777)[-1]
    # begona kishi parolni to‘g‘ri bilsa ham (FSM holatsiz) hech narsa ochilmaydi
    await env.send(ADMIN_PASSWORD, 777)
    assert not await env.deps.auth.is_authenticated(777)
    assert await env.db.fetchval("SELECT count(*) FROM admins WHERE tg_id=777") == 0
    res = await env.deps.auth.login(777, "Begona", ADMIN_PASSWORD)
    assert res.status == "forbidden"
    # admin tugmalari ishlamaydi
    env.clear()
    await env.press("a:new", 777)
    await env.press("gx:start:1", 777)
    assert len(alerts(env)) == 2
    assert not env.calls_of(SendMessage)


async def test_admin_id_without_login_is_blocked_and_group_members_cannot_use_admin(env):
    await env.press("a:games", ADMIN_ID)                              # ADMIN_IDS ichida, lekin parol kiritmagan
    assert alerts(env)
    env.clear()
    await env.send("/admin", 777, chat_id=-1001, chat_type="supergroup")   # guruhda admin buyrug‘i
    assert not env.calls_of(SendMessage)


async def test_bot_added_to_group_registers_it_and_rejects_strangers(env):
    await env.bot_added(-5001, by=ADMIN_ID, title="1-kurs")
    row = await env.db.fetchrow("SELECT * FROM groups WHERE chat_id=-5001")
    assert row and row["title"] == "1-kurs" and row["is_member"] and row["added_by"] == ADMIN_ID
    assert "guruhga ulandi" in env.texts(-5001)[-1]
    await env.bot_added(-5002, by=777)                                # begona qo‘shdi
    assert await env.db.fetchval("SELECT count(*) FROM groups WHERE chat_id=-5002") == 0
    assert env.calls_of(LeaveChat)


async def test_create_game_via_buttons_choose_story_join_and_start(env):
    await env.login_admin()
    await env.bot_added(-1001, by=ADMIN_ID, title="Filologiya-1")
    await env.press("a:new", ADMIN_ID)
    assert any("Filologiya-1" in t for t, _, _ in buttons(env.last_markup(ADMIN_ID)))
    await env.press("ng:g:-1001", ADMIN_ID)
    story_buttons = [d for _, d, _ in buttons(env.last_markup(ADMIN_ID)) if d and d.startswith("ng:s:")]
    assert len(story_buttons) == 4                                   # 4 ta tayyor hikoya tanlash uchun
    sid = await env.db.fetchval("SELECT id FROM stories WHERE slug='oxirgi-dalil'")
    await env.press(f"ng:s:-1001:{sid}", ADMIN_ID)
    await env.press(f"ng:ok:-1001:{sid}", ADMIN_ID)
    game = await env.db.fetchrow("SELECT * FROM games")
    assert game["status"] == "lobby" and game["story_id"] == sid and game["lobby_message_id"]
    lobby = env.calls_of(SendMessage, -1001)[-1]
    assert "Oxirgi dalil" in lobby.text and "Start" in lobby.text
    assert f"start=join_{game['id']}" in buttons(lobby.reply_markup)[0][2]

    # talaba ro‘yxatga yoziladi, ikkinchi marta bosganida takrorlanmaydi
    await env.send(f"/start join_{game['id']}", 501, name="Ali")
    assert "ro‘yxatiga yozildingiz" in env.texts(501)[-1]
    await env.send(f"/start join_{game['id']}", 501)
    assert "allaqachon" in env.texts(501)[-1]
    await env.send(f"/start join_{game['id']}", 502, name="Vali", username=None)   # username yo‘q talaba ham qatnashadi
    assert await env.db.fetchval("SELECT count(*) FROM game_players WHERE game_id=$1", game["id"]) == 2
    await env.deps.timer.tick()                                        # lobbi xabari yangilanadi
    assert not (await env.db.fetchval("SELECT lobby_dirty FROM games WHERE id=$1", game["id"]))

    # hikoyani boshlanishdan oldin almashtirish
    other = await env.db.fetchval("SELECT id FROM stories WHERE slug='songgi-kosmik-missiya'")
    await env.press(f"gs:{game['id']}:{other}", ADMIN_ID)
    assert (await env.db.fetchval("SELECT story_id FROM games WHERE id=$1", game["id"])) == other

    await env.press(f"gx:start:{game['id']}", ADMIN_ID)
    g = await env.db.fetchrow("SELECT * FROM games WHERE id=$1", game["id"])
    assert g["status"] == "running"
    assert "So‘nggi kosmik missiya" in "\n".join(env.texts(-1001))
    # boshlangach hikoyani almashtirib bo‘lmaydi, ro‘yxat yopiladi
    env.clear()
    await env.press(f"gs:{game['id']}:{sid}", ADMIN_ID)
    assert alerts(env)
    await env.send(f"/start join_{game['id']}", 503)
    assert "yopilgan" in env.texts(503)[-1]


async def test_start_without_players_shows_clear_error(env):
    await env.login_admin()
    await env.add_group(-1001)
    sid = await env.db.fetchval("SELECT id FROM stories LIMIT 1")
    gid = await env.deps.games.create_game(-1001, sid, ADMIN_ID)
    await env.press(f"gx:start:{gid}", ADMIN_ID)
    assert (await env.db.fetchval("SELECT status FROM games WHERE id=$1", gid)) == "lobby"
    assert "Ro‘yxatga hech kim" in env.texts(ADMIN_ID)[-1]


async def test_admin_can_pause_resume_cancel_multiple_games(env):
    await env.only_tasks("test")
    await env.login_admin()
    g1, _ = await env.start_game(chat_id=-1001, players_start=100)
    g2, _ = await env.start_game(chat_id=-1002, players_start=200)
    await env.press(f"gx:pause:{g1}", ADMIN_ID)
    assert (await env.game(g1))["status"] == "paused" and (await env.game(g2))["status"] == "running"
    assert "pauzaga" in "\n".join(env.texts(-1001))
    await env.press(f"gx:resume:{g1}", ADMIN_ID)
    assert (await env.game(g1))["status"] == "running"
    await env.press(f"gx:cancelok:{g2}", ADMIN_ID)
    assert (await env.game(g2))["status"] == "cancelled" and (await env.game(g1))["status"] == "running"
    await env.press("a:games", ADMIN_ID)
    assert len([b for b in buttons(env.last_markup(ADMIN_ID)) if b[1].startswith("gm:")]) == 1
    await env.press("a:results", ADMIN_ID)
    await env.press(f"rs:{g2}", ADMIN_ID)
    assert "Natijalar" in env.texts(ADMIN_ID)[-1]
    await env.press("a:stats", ADMIN_ID)
    assert "Statistika" in env.texts(ADMIN_ID)[-1] and "O‘yinlar: <b>2</b>" in env.texts(ADMIN_ID)[-1]


async def test_add_edit_delete_task_through_wizard(env):
    await env.login_admin()
    await env.press("tk:add:3", ADMIN_ID)
    await env.press("tk:k:test", ADMIN_ID)
    await env.send("Navoiy qaysi shaharda tug‘ilgan?", ADMIN_ID)
    await env.send("A) Samarqand\nB) Hirot\nC) Buxoro", ADMIN_ID)
    await env.press("tk:c:1", ADMIN_ID)
    await env.press("tk:t:90", ADMIN_ID)
    t = await env.deps.tasks.get_task(await env.db.fetchval("SELECT max(id) FROM tasks"))
    assert t["stage_no"] == 3 and t["kind"] == "test" and t["options"] == ["Samarqand", "Hirot", "Buxoro"]
    assert t["correct_option"] == 1 and t["time_limit_sec"] == 90 and not t["is_demo"]

    # matnli topshiriq, vaqt qo‘lda yoziladi
    await env.press("tk:add:7", ADMIN_ID)
    await env.press("tk:k:text", ADMIN_ID)
    await env.send("Bitta maqol yozing", ADMIN_ID)
    await env.send("45", ADMIN_ID)
    t2 = await env.deps.tasks.get_task(await env.db.fetchval("SELECT max(id) FROM tasks"))
    assert t2["kind"] == "text" and t2["stage_no"] == 7 and t2["time_limit_sec"] == 45 and t2["options"] == []

    # noto‘g‘ri vaqt qabul qilinmaydi
    await env.press("tk:add:7", ADMIN_ID)
    await env.press("tk:k:creative", ADMIN_ID)
    await env.send("Ijodiy topshiriq", ADMIN_ID)
    await env.send("5", ADMIN_ID)
    assert "10 dan 3600" in env.texts(ADMIN_ID)[-1]
    await env.send("120", ADMIN_ID)
    assert (await env.db.fetchval("SELECT kind FROM tasks ORDER BY id DESC LIMIT 1")) == "creative"

    # tahrirlash
    await env.press(f"tk:e:{t['id']}:time", ADMIN_ID)
    await env.send("33", ADMIN_ID)
    await env.press(f"tk:e:{t['id']}:correct", ADMIN_ID)
    await env.press("tk:ec:2", ADMIN_ID)
    await env.press(f"tk:e:{t['id']}:question", ADMIN_ID)
    await env.send("Yangi savol?", ADMIN_ID)
    t = await env.deps.tasks.get_task(t["id"])
    assert (t["time_limit_sec"], t["correct_option"], t["question"]) == (33, 2, "Yangi savol?")

    # o‘chirish
    await env.press(f"tk:dok:{t['id']}", ADMIN_ID)
    assert await env.deps.tasks.get_task(t["id"]) is None


async def test_story_editing_and_media_attachment(env):
    await env.only_tasks("test")
    await env.login_admin()
    sid = await env.db.fetchval("SELECT id FROM stories WHERE slug='yoqolgan-orol-siri'")
    stage = await env.db.fetchrow("SELECT * FROM story_stages WHERE story_id=$1 AND stage_no=1", sid)
    await env.press(f"sl:e:{stage['id']}:body", ADMIN_ID)
    await env.send("Yangi tahrirlangan hikoya matni.", ADMIN_ID)
    await env.press(f"sl:m:{stage['id']}", ADMIN_ID)
    await env.send_media(ADMIN_ID, photo=[{"file_id": "PHOTO_FID", "file_unique_id": "u", "width": 10, "height": 10}])
    row = await env.db.fetchrow("SELECT * FROM story_stages WHERE id=$1", stage["id"])
    assert row["body"] == "Yangi tahrirlangan hikoya matni." and row["media_file_id"] == "PHOTO_FID"
    assert row["media_type"] == "photo"
    await env.press(f"sl:p:{stage['id']}", ADMIN_ID)
    assert "shipwrecked" in env.texts(ADMIN_ID)[-1]                   # ingliz tilidagi prompt ko‘rinadi
    # o‘yin boshlanganda biriktirilgan rasm guruhga yuboriladi, matn tahrirlangani ko‘rinadi
    env.clear()
    await env.start_game()
    from aiogram.methods import SendPhoto
    assert any(c.photo == "PHOTO_FID" for c in env.calls_of(SendPhoto, -1001))
    assert "Yangi tahrirlangan hikoya matni." in "\n".join(env.texts(-1001))


async def test_story_without_media_still_sends_text(env):
    await env.only_tasks("test")
    env.clear()
    await env.start_game()
    assert "1-bosqich" in "\n".join(env.texts(-1001))


async def test_backup_export_sends_json_document(env):
    await env.login_admin()
    await env.press("st:backup", ADMIN_ID)
    docs = env.calls_of(SendDocument, ADMIN_ID)
    assert docs
    import json
    data = json.loads(docs[0].document.data.decode("utf-8"))
    assert len(data["stories"]) == 4 and len(data["story_stages"]) == 40


async def test_every_admin_screen_and_button_opens_without_errors(env):
    """Hech bir tugma “o‘lik” bo‘lmasligi uchun: barcha ekranlar va ichki tugmalar ketma-ket bosiladi."""
    await env.login_admin()
    await env.bot_added(-1001, by=ADMIN_ID, title="Guruh A")
    sid = await env.db.fetchval("SELECT id FROM stories ORDER BY id LIMIT 1")
    stage_id = await env.db.fetchval("SELECT id FROM story_stages WHERE story_id=$1 AND stage_no=5", sid)
    task_id = await env.db.fetchval("SELECT id FROM tasks WHERE kind='test' LIMIT 1")
    trap_id = await env.db.fetchval("SELECT id FROM traps LIMIT 1")
    for data in ("a:menu", "a:new", "ng:g:-1001", f"ng:s:-1001:{sid}", "a:games", "a:groups", "a:lib", f"sl:s:{sid}",
                 f"sl:g:{stage_id}", f"sl:p:{stage_id}", f"sl:t:{stage_id}", f"sl:t:{stage_id}", "a:tasks", "tk:l:1",
                 f"tk:v:{task_id}", f"tk:d:{task_id}", "tk:add:0", "a:traps", f"tr:v:{trap_id}", "tr:add", "a:results",
                 "a:stats", "a:settings", "st:t:reveal_correct", "st:t:reveal_correct", "st:gif:correct",
                 "st:gifx:correct"):
        env.clear()
        await env.press(data, ADMIN_ID)
        assert env.session.calls, f"{data}: javob bo‘lmadi"
        assert not alerts(env), f"{data}: ogohlantirish chiqdi"
    # o‘yin ichidagi tugmalar
    await env.only_tasks("test")
    gid, players = await env.start_game(chat_id=-1002, players_start=300)
    for data in (f"gm:{gid}", f"gx:roster:{gid}", f"gx:stats:{gid}", f"gx:kick:{gid}", f"gx:cancel:{gid}"):
        env.clear()
        await env.press(data, ADMIN_ID)
        assert env.session.calls, data
    # sozlama qiymati
    await env.press("st:v:default_time_limit", ADMIN_ID)
    await env.send("90", ADMIN_ID)
    assert await env.deps.settings.get_int("default_time_limit") == 90
    # tuzoq tahriri (only_tasks tuzoqlarni tozalagan — yangisini yaratamiz)
    trap_id = await env.deps.tasks.create_trap(stage_no=5, prompt="Sinov tuzog‘i", time_limit_sec=60)
    await env.press(f"tr:e:{trap_id}:time", ADMIN_ID)
    await env.send("77", ADMIN_ID)
    assert (await env.deps.tasks.get_trap(trap_id))["time_limit_sec"] == 77
    # guruhdagi /holat va talabaning /help
    env.clear()
    await env.send("/holat", players[0], chat_id=-1002, chat_type="supergroup")
    assert "davom etmoqda" in env.texts(-1002)[-1]
    await env.send("/help", players[0])
    assert "Yordam" in env.texts(players[0])[-1]
    await env.press("a:logout", ADMIN_ID)
    assert not await env.deps.auth.is_authenticated(ADMIN_ID)
