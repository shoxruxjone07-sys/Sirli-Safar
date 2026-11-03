"""Sozlamalar, hikoya ma’lumotlari, rasm/GIF, FSM saqlash, webhook xavfsizligi, backup."""
import io
import re
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

from app.config import ConfigError, load_config
from app.main import build_app
from app.seed.seeds import MODULES, PROMPTS_FILE, validate_story_data, write_prompts_markdown
from app.services.gif_service import build_gif
from app.services.staircase_service import render_staircase
from app.services.backup_service import export_json
from app.utils.fsm_storage import PgStorage
from tests.conftest import TEST_URL, make_config

GOOD_ENV = {"BOT_TOKEN": "123:abc", "ADMIN_IDS": "1, 2", "ADMIN_PASSWORD_HASH": "$2b$12$abcdefghijklmnopqrstuv",
            "DATABASE_URL": "postgresql://u:p@h/db", "WEBHOOK_URL": "https://x.onrender.com/",
            "WEBHOOK_SECRET": "a" * 20}


def test_config_loads_from_environment_only():
    c = load_config(GOOD_ENV)
    assert c.admin_ids == frozenset({1, 2}) and c.webhook_url == "https://x.onrender.com"
    assert c.webhook_full_url == "https://x.onrender.com/webhook"


@pytest.mark.parametrize("name", ["BOT_TOKEN", "ADMIN_IDS", "ADMIN_PASSWORD_HASH", "DATABASE_URL", "WEBHOOK_URL",
                                  "WEBHOOK_SECRET"])
def test_config_requires_every_variable(name):
    env = dict(GOOD_ENV)
    del env[name]
    with pytest.raises(ConfigError) as exc:
        load_config(env)
    assert name in str(exc.value)


@pytest.mark.parametrize("patch", [{"WEBHOOK_SECRET": "qisqa"}, {"WEBHOOK_SECRET": "bad secret!!!!!!!!!!!!"},
                                   {"ADMIN_PASSWORD_HASH": "plain-password"}, {"WEBHOOK_URL": "http://x.com"},
                                   {"ADMIN_IDS": "abc"}])
def test_config_rejects_bad_values(patch):
    with pytest.raises(ConfigError):
        load_config({**GOOD_ENV, **patch})


def test_no_secrets_hardcoded_in_source():
    root = Path(__file__).resolve().parent.parent
    for path in list((root / "app").rglob("*.py")) + list((root / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\d{8,10}:[A-Za-z0-9_-]{30,}", text), path          # bot token ko‘rinishi
        assert not re.search(r"postgres(?:ql)?://\w+:[^@\s\"']{4,}@", text), path             # parol bilan DSN


def test_story_data_is_complete_40_stages_with_english_prompts():
    validate_story_data()
    assert len(MODULES) == 4
    stages = [(m, s) for m in MODULES for s in m.STORY["stages"]]
    assert len(stages) == 40
    for m, s in stages:
        assert len(s["body"].split()) >= 25, (m.STORY["slug"], s["no"])           # qisqa emas
        assert re.search(r"[a-z]{3,}", s["prompt"]) and "16:9" in m.STYLE
        assert "O‘" not in s["prompt"]
    traps = {m.STORY["slug"]: [s["no"] for s in m.STORY["stages"] if s.get("trap")] for m in MODULES}
    assert all(v == [5] for v in traps.values())
    assert all("DIQQAT" in m.STORY["stages"][4]["body"] for m in MODULES)


def test_prompt_file_has_40_prompts(tmp_path):
    out = tmp_path / "p.md"
    assert write_prompts_markdown(out) == 40
    assert out.read_text(encoding="utf-8").count("```\n") == 80                  # 40 ta blok (ochilish+yopilish)
    assert PROMPTS_FILE.exists()


async def test_stories_seeded_into_database_and_idempotent(env):
    from app.seed.seeds import seed_stories
    assert await env.db.fetchval("SELECT count(*) FROM stories") == 4
    assert await env.db.fetchval("SELECT count(*) FROM story_stages") == 40
    await env.db.execute("UPDATE story_stages SET body='ADMIN TAHRIRI' WHERE stage_no=3 AND story_id=1")
    assert await seed_stories(env.db) == 0                                         # qayta yuklash tahrirni buzmaydi
    assert await env.db.fetchval("SELECT body FROM story_stages WHERE stage_no=3 AND story_id=1") == "ADMIN TAHRIRI"


async def test_demo_tasks_cover_every_stage(env):
    counts = await env.deps.tasks.count_by_stage()
    assert all(counts.get(n, 0) >= 2 for n in range(1, 10))


def test_staircase_image_shows_ten_steps_and_highlights_current():
    imgs = [Image.open(io.BytesIO(render_staircase(n, story_title="T", stage_title="S", theme=n % 4))) for n in (1, 5, 10)]
    assert all(i.size == (960, 540) for i in imgs)                                  # 16:9
    assert len({i.tobytes() for i in imgs}) == 3
    # joriy pog‘ona (5) boshqa pog‘onalardan rangi bilan ajralib turadi
    img = Image.open(io.BytesIO(render_staircase(5, theme=0))).convert("RGB")
    cur, passed, future = img.getpixel((430, 400)), img.getpixel((200, 440)), img.getpixel((600, 440))
    assert len({cur, passed, future}) == 3


@pytest.mark.parametrize("kind", ["correct", "wrong", "victory"])
def test_builtin_gifs_are_animated(kind):
    gif = Image.open(io.BytesIO(build_gif(kind)))
    assert gif.format == "GIF" and getattr(gif, "n_frames", 1) > 5


async def test_fsm_state_is_stored_in_postgres(env):
    from aiogram.fsm.storage.base import StorageKey
    storage = PgStorage(env.db)
    key = StorageKey(bot_id=1, chat_id=7, user_id=7)
    await storage.set_state(key, "AdminSt:password")
    await storage.update_data(key, {"a": 1})
    other = PgStorage(env.db)                                                       # “qayta ishga tushgan” jarayon
    assert await other.get_state(key) == "AdminSt:password" and await other.get_data(key) == {"a": 1}


async def test_webhook_checks_secret_token(env):
    app = build_app(env.deps, env.dp)
    async with TestClient(TestServer(app)) as client:
        r = await client.get("/health")
        assert r.status == 200 and (await r.json())["db"] is True
        body = {"update_id": 99999, "message": {"message_id": 1, "date": 1, "chat": {"id": 5, "type": "private"},
                                                "from": {"id": 5, "is_bot": False, "first_name": "X"}, "text": "/start",
                                                "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}}
        assert (await client.post("/webhook", json=body)).status == 401
        assert (await client.post("/webhook", json=body, headers={"X-Telegram-Bot-Api-Secret-Token": "x" * 24})).status == 401
        ok = await client.post("/webhook", json=body, headers={"X-Telegram-Bot-Api-Secret-Token": "s" * 24})
        assert ok.status == 200


async def test_backup_export_contains_content(env):
    import json
    data = json.loads((await export_json(env.db)).decode("utf-8"))
    assert len(data["stories"]) == 4 and len(data["tasks"]) >= 18 and "games" in data


async def test_migrations_are_idempotent_and_tables_exist(env):
    from app.database import run_migrations
    assert await run_migrations(env.db) == []
    names = {r["table_name"] for r in await env.db.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}
    for t in ("admins", "groups", "players", "games", "stories", "story_stages", "tasks", "task_options",
              "game_tasks", "answers", "traps", "game_events", "results"):
        assert t in names, t


def test_dotenv_file_is_loaded_without_overriding_real_environment(tmp_path):
    from app.config import load_dotenv
    f = tmp_path / ".env"
    f.write_text("# izoh\nBOT_TOKEN=123:abc\nADMIN_PASSWORD_HASH='$2b$12$xyz'\nADMIN_IDS = 5\nEMPTY=\n", encoding="utf-8")
    env = {"ADMIN_IDS": "9"}
    assert load_dotenv(f, env) == 2
    assert env["BOT_TOKEN"] == "123:abc" and env["ADMIN_PASSWORD_HASH"] == "$2b$12$xyz" and env["ADMIN_IDS"] == "9"
    assert load_dotenv(tmp_path / "yoq.env", env) == 0
