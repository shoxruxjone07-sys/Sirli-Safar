"""Test muhiti: haqiqiy PostgreSQL + soxta Telegram sessiyasi (tarmoqsiz).

TEST_DATABASE_URL (standart: postgresql://postgres@127.0.0.1:54329/sirli_test) ko‘rsatgan bazani
test boshida tozalaydi — hech qachon ishchi bazani ko‘rsatmang!"""
from __future__ import annotations

import datetime as dt
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import (EditMessageText, GetChatMember, GetMe, SendAnimation, SendDocument, SendMessage,
                             SendPhoto)
from aiogram.types import Animation, Chat, ChatMemberMember, Message, User

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config  # noqa: E402
from app.database import Db, run_migrations  # noqa: E402
from app.deps import Deps, build_deps  # noqa: E402
from app.main import build_dispatcher  # noqa: E402
from app.seed.seeds import seed_stories  # noqa: E402
from app.services.timer_service import TimerService  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@127.0.0.1:54329/sirli_test")
ADMIN_ID = 1
ADMIN_PASSWORD = "parol-12345"
TABLES = ("admins, groups, players, stories, story_stages, tasks, task_options, traps, games, game_players, "
          "game_tasks, answers, game_events, results, settings, user_states")


class FakeSession(BaseSession):
    """Telegram’ga so‘rov yubormaydi; barcha chaqiruvlarni yozib boradi."""

    def __init__(self):
        super().__init__()
        self.calls: list = []
        self.mid = 1000
        self.forbidden_chats: set[int] = set()

    async def close(self) -> None:
        return None

    async def stream_content(self, *a, **k):
        raise NotImplementedError

    async def make_request(self, bot, method, timeout=None):
        if isinstance(method, (SendMessage, SendPhoto, SendAnimation, SendDocument)):
            if int(method.chat_id) in self.forbidden_chats:
                raise TelegramForbiddenError(method=method, message="Forbidden: bot was blocked by the user")
            self.calls.append(method)
            self.mid += 1
            chat_id = int(method.chat_id)
            data: dict[str, Any] = dict(message_id=self.mid, date=dt.datetime.now(dt.timezone.utc),
                                        chat=Chat(id=chat_id, type="private" if chat_id > 0 else "supergroup"))
            if isinstance(method, SendAnimation):
                data["animation"] = Animation(file_id=f"anim{self.mid}", file_unique_id=f"u{self.mid}",
                                              width=1, height=1, duration=1)
            return Message(**data)
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=999000, is_bot=True, first_name="Sirli", username="sirli_bot")
        if isinstance(method, GetChatMember):
            return ChatMemberMember(user=User(id=method.user_id, is_bot=False, first_name="x"), status="member")
        return True


def make_config() -> Config:
    return Config(bot_token="123456:TESTTOKEN", admin_ids=frozenset({ADMIN_ID}),
                  admin_password_hash=_HASH, database_url=TEST_URL, webhook_url="https://example.onrender.com",
                  webhook_secret="s" * 24)


_HASH = hash_password(ADMIN_PASSWORD)


@pytest_asyncio.fixture(scope="session")
async def db():
    d = await Db.connect(TEST_URL, min_size=2, max_size=10)
    await d.execute("DROP SCHEMA public CASCADE")
    await d.execute("CREATE SCHEMA public")
    await run_migrations(d)
    yield d
    await d.close()


class Env:
    def __init__(self, deps: Deps, session: FakeSession, dp):
        self.deps, self.session, self.dp, self.bot, self.db = deps, session, dp, deps.bot, deps.db
        self.uid = 10_000

    # ---------- Telegram update’larini yuborish ----------
    def _user(self, uid: int, name: Optional[str] = None, username: Optional[str] = "default"):
        u = {"id": uid, "is_bot": False, "first_name": name or f"User{uid}"}
        if username == "default":
            username = f"user{uid}"
        if username:
            u["username"] = username
        return u

    def _msg(self, uid, chat_id, chat_type, **extra):
        self.uid += 1
        chat = {"id": chat_id, "type": chat_type}
        if chat_type != "private":
            chat["title"] = "Guruh"
        msg = {"message_id": self.session.mid + 1, "date": int(time.time()), "chat": chat,
               "from": self._user(uid, extra.pop("name", None), extra.pop("username", "default"))}
        self.session.mid += 1
        msg.update(extra)
        return msg

    async def send(self, text: str, uid: int, *, chat_id: Optional[int] = None, chat_type: str = "private",
                   reply_to: Optional[int] = None, name=None, username="default"):
        chat_id = chat_id if chat_id is not None else uid
        extra: dict[str, Any] = {"text": text, "name": name, "username": username}
        if text.startswith("/"):
            cmd = text.split()[0]
            extra["entities"] = [{"type": "bot_command", "offset": 0, "length": len(cmd)}]
        if reply_to:
            extra["reply_to_message"] = {"message_id": reply_to, "date": int(time.time()),
                                         "chat": {"id": chat_id, "type": chat_type, "title": "Guruh"},
                                         "from": {"id": 999000, "is_bot": True, "first_name": "Sirli"}, "text": "x"}
        update = {"update_id": self._upd(), "message": self._msg(uid, chat_id, chat_type, **extra)}
        await self.dp.feed_raw_update(self.bot, update)

    async def send_media(self, uid: int, **media):
        update = {"update_id": self._upd(), "message": self._msg(uid, uid, "private", **media)}
        await self.dp.feed_raw_update(self.bot, update)

    async def press(self, data: str, uid: int, *, message_id: int = 5000, chat_id: Optional[int] = None,
                    chat_type: str = "private") -> None:
        chat_id = chat_id if chat_id is not None else uid
        chat = {"id": chat_id, "type": chat_type}
        if chat_type != "private":
            chat["title"] = "Guruh"
        update = {"update_id": self._upd(), "callback_query": {
            "id": str(self._upd()), "chat_instance": "ci", "data": data, "from": self._user(uid),
            "message": {"message_id": message_id, "date": int(time.time()), "chat": chat, "text": "menu",
                        "from": {"id": 999000, "is_bot": True, "first_name": "Sirli"}}}}
        await self.dp.feed_raw_update(self.bot, update)

    async def bot_added(self, chat_id: int, by: int, title: str = "Guruh") -> None:
        update = {"update_id": self._upd(), "my_chat_member": {
            "chat": {"id": chat_id, "type": "supergroup", "title": title}, "from": self._user(by),
            "date": int(time.time()),
            "old_chat_member": {"status": "left", "user": {"id": 999000, "is_bot": True, "first_name": "Sirli"}},
            "new_chat_member": {"status": "member", "user": {"id": 999000, "is_bot": True, "first_name": "Sirli"}}}}
        await self.dp.feed_raw_update(self.bot, update)

    _n = 0

    def _upd(self) -> int:
        Env._n += 1
        return Env._n

    # ---------- yozib olingan chaqiruvlar ----------
    def texts(self, chat_id: int) -> list[str]:
        out = []
        for c in self.session.calls:
            if isinstance(c, (SendMessage, EditMessageText)) and c.chat_id is not None and int(c.chat_id) == chat_id:
                out.append(c.text)
            elif isinstance(c, (SendAnimation, SendPhoto)) and int(c.chat_id) == chat_id and c.caption:
                out.append(c.caption)
        return out

    def calls_of(self, kind, chat_id: Optional[int] = None) -> list:
        return [c for c in self.session.calls if isinstance(c, kind)
                and (chat_id is None or int(getattr(c, "chat_id", 0)) == chat_id)]

    def last_markup(self, chat_id: int):
        for c in reversed(self.session.calls):
            if (isinstance(c, (SendMessage, EditMessageText)) and c.chat_id is not None
                    and int(c.chat_id) == chat_id and c.reply_markup):
                return c.reply_markup
        return None

    def clear(self) -> None:
        self.session.calls.clear()

    # ---------- tayyorlash yordamchilari ----------
    async def login_admin(self, uid: int = ADMIN_ID) -> None:
        await self.db.execute(
            "INSERT INTO admins(tg_id,name,authenticated_until) VALUES($1,'Admin', now() + interval '1 hour') "
            "ON CONFLICT (tg_id) DO UPDATE SET authenticated_until = now() + interval '1 hour', "
            "failed_attempts=0, locked_until=NULL", uid)

    async def add_group(self, chat_id: int = -1001, title: str = "Guruh 1") -> int:
        await self.db.execute(
            "INSERT INTO groups(chat_id,title,added_by) VALUES($1,$2,$3) "
            "ON CONFLICT (chat_id) DO UPDATE SET is_member=TRUE", chat_id, title, ADMIN_ID)
        return chat_id

    async def add_players(self, n: int, start: int = 100, dm_ok: bool = True) -> list[int]:
        ids = list(range(start, start + n))
        for i in ids:
            await self.db.execute(
                "INSERT INTO players(tg_id,username,full_name,dm_ok) VALUES($1,$2,$3,$4) "
                "ON CONFLICT (tg_id) DO UPDATE SET dm_ok=EXCLUDED.dm_ok", i, f"talaba{i}", f"Talaba {i}", dm_ok)
        return ids

    async def only_tasks(self, kind: str = "test", per_stage: int = 1, time_limit: int = 60, stages=range(1, 10),
                         **extra) -> None:
        """Barcha topshiriqlarni o‘chirib, har bir zinaga bir xil turdagi topshiriq(lar) qo‘shadi."""
        await self.db.execute("DELETE FROM tasks")
        await self.db.execute("DELETE FROM traps")
        for stage in stages:
            for k in range(per_stage):
                spec: dict[str, Any] = dict(stage_no=stage, kind=kind, question=f"Savol {stage}.{k}?",
                                            time_limit_sec=time_limit)
                if kind in ("test",) or extra.get("options"):
                    spec.update(options=["to‘g‘ri", "xato 1", "xato 2", "xato 3"], correct_option=0)
                spec.update(extra)
                await self.deps.tasks.create_task(**spec)

    async def start_game(self, *, chat_id: int = -1001, n_players: int = 3, story_slug: str = "yoqolgan-orol-siri",
                         players_start: int = 100, begin: bool = True) -> tuple[int, list[int]]:
        await self.add_group(chat_id, f"Guruh {chat_id}")
        players = await self.add_players(n_players, start=players_start)
        sid = await self.db.fetchval("SELECT id FROM stories WHERE slug=$1", story_slug)
        gid = await self.deps.games.create_game(chat_id, sid, ADMIN_ID)
        await self.deps.flow.post_lobby(gid)
        for p in players:
            assert await self.deps.games.join(gid, p) == "ok"
        await self.deps.games.start(gid)
        if begin:
            await self.deps.flow.begin(gid)
        return gid, players

    async def active_task(self, game_id: int) -> Optional[dict]:
        row = await self.db.fetchrow(
            "SELECT * FROM game_tasks WHERE game_id=$1 AND status IN ('needs_input','pending','open','awaiting_review')",
            game_id)
        return dict(row) if row else None

    async def game(self, game_id: int) -> dict:
        return dict(await self.db.fetchrow("SELECT * FROM games WHERE id=$1", game_id))

    async def answer(self, game_id: int, uid: int, correct: bool = True) -> None:
        """Guruhdagi test tugmasini bosadi (Telegram update orqali)."""
        gt = await self.active_task(game_id)
        if gt and gt["status"] == "needs_input":        # tuzoq bosqichi: admin tuzoqni berib, “to‘g‘ri” deb baholaydi
            await self.clear_trap(game_id)
            gt = await self.active_task(game_id)
        assert gt and gt["status"] == "open", gt
        idx = gt["correct_option"] if correct else (gt["correct_option"] + 1) % len(gt["options"])
        g = await self.game(game_id)
        await self.press(f"ans:{gt['id']}:{idx}", uid, message_id=gt["group_message_id"] or 7, chat_id=g["group_id"],
                         chat_type="supergroup")

    async def clear_trap(self, game_id: int, correct: bool = True) -> None:
        gt = await self.active_task(game_id)
        assert gt and gt["status"] == "needs_input", gt
        assert await self.deps.games.set_trap(gt["id"], "Tuzoq topshirig‘i: jamoa 3 ta maqol aytsin", 60)
        await self.deps.flow.announce(gt["id"])
        gt = await self.active_task(game_id)
        assert gt["status"] == "open" and gt["kind"] == "trap"
        r = await self.deps.games.grade(gt["id"], ADMIN_ID, correct)
        assert r.status == "ok"
        await self.deps.flow.after_resolve(r.resolution)

    async def expire_now(self, game_id: int) -> None:
        await self.db.execute(
            "UPDATE game_tasks SET deadline_at = now() - interval '1 second' WHERE game_id=$1 AND status='open'", game_id)


@pytest_asyncio.fixture
async def env(db):
    await db.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    session = FakeSession()
    bot = Bot("123456:TESTTOKEN", session=session)
    deps = build_deps(make_config(), db, bot)
    await seed_stories(db)
    await deps.tasks.seed_demo()
    await deps.flow.init()
    dp = build_dispatcher(deps)
    deps.timer = TimerService(deps.games, deps.flow, interval=0.1)
    e = Env(deps, session, dp)
    session.calls.clear()
    yield e
    await deps.drain()
