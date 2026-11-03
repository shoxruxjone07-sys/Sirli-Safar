"""O‘yin mantig‘i (faqat ma’lumotlar bazasi, Telegram’siz).

Asosiy qoidalar:
* Har bir o‘zgartirish `games` qatorini FOR UPDATE bilan qulflab bajariladi — bir vaqtda kelgan javoblar,
  vaqt tugashi va admin amallari ketma-ket ishlaydi.
* Vaqt chegarasi UTC `deadline_at` sifatida bazada saqlanadi; javob va taymer bir vaqtda kelsa,
  deadline bo‘yicha yagona natija belgilanadi.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any, Optional

import asyncpg

from app.database import Db

FINAL_STAGE = 10
ACTIVE_TASK_STATUSES = ["needs_input", "pending", "open", "awaiting_review"]
ACTIVE_GAME_STATUSES = ["lobby", "running", "paused"]


class GameError(Exception):
    """Foydalanuvchiga ko‘rsatish mumkin bo‘lgan xato."""


@dataclass
class Resolution:
    game_id: int
    group_id: int
    task: dict
    outcome: str  # correct | wrong | timeout
    old_stage: int
    new_stage: int
    finished: bool
    trap_cleared: bool = False

    @property
    def moved(self) -> str:
        if self.new_stage > self.old_stage:
            return "up"
        if self.new_stage < self.old_stage:
            return "down"
        return "none"


@dataclass
class AnswerResult:
    status: str  # ok | already | closed | paused | not_player | not_yours | timeout | wrong_kind | missing
    resolution: Optional[Resolution] = None
    task: Optional[dict] = None
    user: Optional[dict] = None
    text: Optional[str] = None
    choice: Optional[int] = None


@dataclass
class Prepared:
    gt_id: Optional[int]
    reason: str = "ok"  # ok | busy | not_running | no_tasks
    stage: int = 0
    kind: str = ""


class GameService:
    def __init__(self, db: Db, settings=None):
        self.db = db
        self.settings = settings

    # ------------------------------------------------------------------ lobbi
    async def create_game(self, group_id: int, story_id: int, admin_id: int) -> int:
        async with self.db.tx() as conn:
            group = await conn.fetchrow("SELECT * FROM groups WHERE chat_id=$1", group_id)
            if not group or not group["is_member"]:
                raise GameError("Bot bu guruhda emas. Avval botni guruhga qo‘shing.")
            story = await conn.fetchrow("SELECT id FROM stories WHERE id=$1 AND is_active", story_id)
            if not story:
                raise GameError("Hikoya topilmadi")
            try:
                async with conn.transaction():
                    game_id = await conn.fetchval(
                        "INSERT INTO games(group_id, story_id, admin_id) VALUES($1,$2,$3) RETURNING id",
                        group_id, story_id, admin_id)
            except asyncpg.UniqueViolationError as exc:
                raise GameError("Bu guruhda allaqachon faol o‘yin bor. Avval uni yakunlang yoki bekor qiling.") from exc
            await self._event(conn, game_id, "game_created", {"admin": admin_id, "story": story_id})
        return game_id

    async def get_game(self, game_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow(
            "SELECT g.*, gr.title AS group_title, s.title AS story_title, s.theme AS story_theme "
            "FROM games g JOIN groups gr ON gr.chat_id=g.group_id JOIN stories s ON s.id=g.story_id WHERE g.id=$1",
            game_id)

    async def active_game_for_group(self, group_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow(
            "SELECT g.*, gr.title AS group_title, s.title AS story_title, s.theme AS story_theme "
            "FROM games g JOIN groups gr ON gr.chat_id=g.group_id JOIN stories s ON s.id=g.story_id "
            "WHERE g.group_id=$1 AND g.status = ANY($2::text[])", group_id, ACTIVE_GAME_STATUSES)

    async def list_active_games(self) -> list[asyncpg.Record]:
        return await self.db.fetch(
            "SELECT g.*, gr.title AS group_title, s.title AS story_title FROM games g "
            "JOIN groups gr ON gr.chat_id=g.group_id JOIN stories s ON s.id=g.story_id "
            "WHERE g.status = ANY($1::text[]) ORDER BY g.id DESC", ACTIVE_GAME_STATUSES)

    async def list_finished_games(self, limit: int = 10) -> list[asyncpg.Record]:
        return await self.db.fetch(
            "SELECT g.*, gr.title AS group_title, s.title AS story_title FROM games g "
            "JOIN groups gr ON gr.chat_id=g.group_id JOIN stories s ON s.id=g.story_id "
            "WHERE g.status IN ('finished','cancelled') ORDER BY g.id DESC LIMIT $1", limit)

    async def join(self, game_id: int, user_id: int) -> str:
        """'ok' | 'already' | 'closed' | 'missing'"""
        async with self.db.game_tx(game_id) as (conn, game):
            if not game:
                return "missing"
            if game["status"] != "lobby":
                return "closed"
            inserted = await conn.fetchval(
                "INSERT INTO game_players(game_id,user_id) VALUES($1,$2) ON CONFLICT DO NOTHING RETURNING 1",
                game_id, user_id)
            if not inserted:
                return "already"
            await conn.execute("UPDATE games SET lobby_dirty=TRUE WHERE id=$1", game_id)
            await self._event(conn, game_id, "player_joined", {"user": user_id})
            return "ok"

    async def roster(self, game_id: int) -> list[asyncpg.Record]:
        return await self.db.fetch(
            "SELECT p.*, gp.times_selected FROM game_players gp JOIN players p ON p.tg_id=gp.user_id "
            "WHERE gp.game_id=$1 ORDER BY gp.joined_at, p.tg_id", game_id)

    async def is_in_roster(self, game_id: int, user_id: int) -> bool:
        return bool(await self.db.fetchval(
            "SELECT 1 FROM game_players WHERE game_id=$1 AND user_id=$2", game_id, user_id))

    async def set_story(self, game_id: int, story_id: int) -> None:
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] != "lobby":
                raise GameError("Hikoyani faqat o‘yin boshlanishidan oldin almashtirish mumkin")
            if not await conn.fetchval("SELECT 1 FROM stories WHERE id=$1 AND is_active", story_id):
                raise GameError("Hikoya topilmadi")
            await conn.execute("UPDATE games SET story_id=$2, lobby_dirty=TRUE WHERE id=$1", game_id, story_id)
            await self._event(conn, game_id, "story_changed", {"story": story_id})

    async def preflight(self, game_id: int) -> list[str]:
        """O‘yinni boshlashga to‘sqinlik qiladigan muammolar ro‘yxati (bo‘sh = tayyor)."""
        problems: list[str] = []
        game = await self.db.fetchrow("SELECT * FROM games WHERE id=$1", game_id)
        if not game:
            return ["O‘yin topilmadi"]
        if await self.db.fetchval("SELECT count(*) FROM game_players WHERE game_id=$1", game_id) == 0:
            problems.append("Ro‘yxatga hech kim yozilmagan. Talabalar botga /start bosib, ro‘yxatga yozilishi kerak.")
        have = {r["stage_no"] for r in await self.db.fetch(
            "SELECT DISTINCT stage_no FROM tasks WHERE is_active")}
        missing = [n for n in range(1, FINAL_STAGE) if n not in have]
        if missing:
            problems.append("Quyidagi zinalar uchun topshiriq yo‘q: " + ", ".join(f"{n}-zina" for n in missing))
        stages = await self.db.fetchval("SELECT count(*) FROM story_stages WHERE story_id=$1", game["story_id"])
        if stages != FINAL_STAGE:
            problems.append("Hikoya 10 ta bosqichdan iborat emas")
        return problems

    async def start(self, game_id: int) -> asyncpg.Record:
        problems = await self.preflight(game_id)
        if problems:
            raise GameError("\n".join(problems))
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] != "lobby":
                raise GameError("O‘yin allaqachon boshlangan yoki yakunlangan")
            await conn.execute(
                "UPDATE games SET status='running', started_at=now(), current_stage=1, max_stage_reached=1 WHERE id=$1",
                game_id)
            await self._event(conn, game_id, "game_started", {})
        return await self.db.fetchrow("SELECT * FROM games WHERE id=$1", game_id)

    async def pause(self, game_id: int) -> None:
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] != "running":
                raise GameError("Faqat ishlayotgan o‘yinni pauza qilish mumkin")
            await conn.execute("UPDATE games SET status='paused', paused_at=now() WHERE id=$1", game_id)
            await self._event(conn, game_id, "paused", {})

    async def resume(self, game_id: int) -> None:
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] != "paused":
                raise GameError("O‘yin pauzada emas")
            shift = await conn.fetchval("SELECT GREATEST(0, EXTRACT(EPOCH FROM (now() - $1::timestamptz)))",
                                        game["paused_at"])
            # ochiq topshiriqlar deadline’i pauza davomiyligicha suriladi
            await conn.execute(
                "UPDATE game_tasks SET deadline_at = deadline_at + make_interval(secs => $2) "
                "WHERE game_id=$1 AND status='open' AND deadline_at IS NOT NULL", game_id, float(shift))
            await conn.execute(
                "UPDATE games SET status='running', paused_at=NULL, paused_total_sec = paused_total_sec + $2 WHERE id=$1",
                game_id, int(shift))
            await self._event(conn, game_id, "resumed", {"paused_sec": int(shift)})

    async def cancel(self, game_id: int) -> None:
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] not in ACTIVE_GAME_STATUSES:
                raise GameError("O‘yin allaqachon yakunlangan")
            await conn.execute(
                "UPDATE game_tasks SET status='cancelled' WHERE game_id=$1 AND status = ANY($2::text[])",
                game_id, ACTIVE_TASK_STATUSES)
            await conn.execute("UPDATE games SET status='cancelled', finished_at=now() WHERE id=$1", game_id)
            await self._event(conn, game_id, "cancelled", {})

    # ---------------------------------------------------------- topshiriq berish
    async def prepare_next(self, game_id: int, exclude_kinds: tuple = ()) -> Prepared:
        """Keyingi topshiriq qatorini yaratadi (status: pending yoki tuzoq uchun needs_input)."""
        async with self.db.game_tx(game_id) as (conn, game):
            if not game or game["status"] != "running":
                return Prepared(None, "not_running")
            busy = await conn.fetchval(
                "SELECT id FROM game_tasks WHERE game_id=$1 AND status = ANY($2::text[]) LIMIT 1",
                game_id, ACTIVE_TASK_STATUSES)
            if busy:
                return Prepared(None, "busy")
            stage = game["current_stage"]
            seq = int(await conn.fetchval("SELECT COALESCE(max(seq),0) FROM game_tasks WHERE game_id=$1", game_id)) + 1
            has_trap = await conn.fetchval(
                "SELECT has_trap FROM story_stages WHERE story_id=$1 AND stage_no=$2", game["story_id"], stage)
            if has_trap and stage not in (game["cleared_traps"] or []):
                limit = await self._int_setting("trap_time_limit", 120)
                gt_id = await conn.fetchval(
                    "INSERT INTO game_tasks(game_id,seq,stage_no,kind,question,time_limit_sec,status) "
                    "VALUES($1,$2,$3,'trap','',$4,'needs_input') RETURNING id", game_id, seq, stage, limit)
                await self._event(conn, game_id, "trap_triggered", {"stage": stage, "game_task": gt_id})
                return Prepared(gt_id, "ok", stage, "trap")

            tasks = await conn.fetch("SELECT * FROM tasks WHERE is_active AND stage_no=$1", stage)
            tasks = [t for t in tasks if t["kind"] not in exclude_kinds]
            candidates: list[asyncpg.Record] = []
            if any(t["kind"] == "individual" for t in tasks):
                candidates = await self._individual_candidates(conn, game)
                if not candidates:
                    tasks = [t for t in tasks if t["kind"] != "individual"]
            if not tasks:
                await conn.execute("UPDATE games SET status='paused', paused_at=now() WHERE id=$1", game_id)
                await self._event(conn, game_id, "no_tasks", {"stage": stage})
                return Prepared(None, "no_tasks", stage)

            task = random.choice(tasks)
            opts = [r["text"] for r in await conn.fetch(
                "SELECT text FROM task_options WHERE task_id=$1 ORDER BY position", task["id"])]
            assigned = None
            if task["kind"] == "individual":
                chosen = self._pick_fair(candidates, game["last_individual_user"])
                assigned = chosen["tg_id"]
                await conn.execute("UPDATE game_players SET times_selected = times_selected + 1 "
                                   "WHERE game_id=$1 AND user_id=$2", game_id, assigned)
                await conn.execute("UPDATE games SET last_individual_user=$2 WHERE id=$1", game_id, assigned)
            gt_id = await conn.fetchval(
                "INSERT INTO game_tasks(game_id,seq,stage_no,kind,task_id,question,options,correct_option,"
                "time_limit_sec,assigned_user_id,status) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'pending') RETURNING id",
                game_id, seq, stage, task["kind"], task["id"], task["question"], opts or None,
                task["correct_option"], task["time_limit_sec"], assigned)
            await self._event(conn, game_id, "task_created",
                              {"game_task": gt_id, "kind": task["kind"], "stage": stage, "assigned": assigned})
            return Prepared(gt_id, "ok", stage, task["kind"])

    async def _individual_candidates(self, conn, game) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT p.*, gp.times_selected FROM game_players gp JOIN players p ON p.tg_id=gp.user_id "
            "WHERE gp.game_id=$1 AND p.dm_ok", game["id"])

    @staticmethod
    def _pick_fair(candidates, last_user: Optional[int]):
        """Adolatli tanlash: eng kam tanlanganlar orasidan, ketma-ket bir xil talaba emas."""
        pool = list(candidates)
        if len(pool) > 1 and last_user is not None:
            pool = [c for c in pool if c["tg_id"] != last_user] or pool
        least = min(c["times_selected"] for c in pool)
        pool = [c for c in pool if c["times_selected"] == least]
        return random.choice(pool)

    async def reassign_individual(self, gt_id: int, failed_user: int) -> Optional[asyncpg.Record]:
        """Talabaga shaxsiy xabar yuborib bo‘lmasa — boshqa talabani tanlaydi."""
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return None
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt or gt["status"] != "pending" or not game:
                return None
            await conn.execute("UPDATE players SET dm_ok=FALSE WHERE tg_id=$1", failed_user)
            cands = [c for c in await self._individual_candidates(conn, game) if c["tg_id"] != failed_user]
            if not cands:
                await conn.execute("UPDATE game_tasks SET status='skipped' WHERE id=$1", gt_id)
                await self._event(conn, game["id"], "individual_skipped", {"game_task": gt_id})
                return None
            chosen = self._pick_fair(cands, failed_user)
            await conn.execute("UPDATE game_tasks SET assigned_user_id=$2 WHERE id=$1", gt_id, chosen["tg_id"])
            await conn.execute("UPDATE game_players SET times_selected = times_selected + 1 "
                               "WHERE game_id=$1 AND user_id=$2", game["id"], chosen["tg_id"])
            await conn.execute("UPDATE games SET last_individual_user=$2 WHERE id=$1", game["id"], chosen["tg_id"])
            return chosen

    async def set_trap(self, gt_id: int, prompt: str, time_limit_sec: int) -> bool:
        prompt = (prompt or "").strip()
        if not prompt:
            raise GameError("Tuzoq matni bo‘sh bo‘lmasin")
        if not 10 <= time_limit_sec <= 3600:
            raise GameError("Vaqt 10–3600 soniya bo‘lishi kerak")
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return False
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            res = await conn.execute(
                "UPDATE game_tasks SET question=$2, time_limit_sec=$3, status='pending' "
                "WHERE id=$1 AND status='needs_input'", gt_id, prompt, time_limit_sec)
            return res.endswith("1")

    async def open_task(self, gt_id: int, group_message_id: Optional[int], dm_message_id: Optional[int] = None):
        """Topshiriq e’lon qilingach hisoblagich shu yerdan boshlanadi."""
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return None
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            return await conn.fetchrow(
                "UPDATE game_tasks SET status='open', opened_at=now(), group_message_id=$2, dm_message_id=$3, "
                "deadline_at = now() + make_interval(secs => time_limit_sec) "
                "WHERE id=$1 AND status='pending' RETURNING *", gt_id, group_message_id, dm_message_id)

    async def get_task(self, gt_id: int) -> Optional[dict]:
        row = await self.db.fetchrow(
            "SELECT gt.*, g.group_id, g.status AS game_status, g.admin_id, g.current_stage, g.story_id "
            "FROM game_tasks gt JOIN games g ON g.id=gt.game_id WHERE gt.id=$1", gt_id)
        return dict(row) if row else None

    async def find_open_by_group_message(self, group_id: int, message_id: int) -> Optional[dict]:
        row = await self.db.fetchrow(
            "SELECT gt.*, g.group_id, g.status AS game_status, g.admin_id FROM game_tasks gt "
            "JOIN games g ON g.id=gt.game_id WHERE g.group_id=$1 AND gt.group_message_id=$2 "
            "AND gt.status IN ('open','awaiting_review')", group_id, message_id)
        return dict(row) if row else None

    async def find_open_individual(self, user_id: int) -> Optional[dict]:
        row = await self.db.fetchrow(
            "SELECT gt.*, g.group_id, g.status AS game_status, g.admin_id FROM game_tasks gt "
            "JOIN games g ON g.id=gt.game_id WHERE gt.assigned_user_id=$1 AND gt.status IN ('open','awaiting_review') "
            "AND gt.kind='individual' AND g.status IN ('running','paused') ORDER BY gt.id DESC LIMIT 1", user_id)
        return dict(row) if row else None

    # ----------------------------------------------------------------- javoblar
    async def submit_choice(self, gt_id: int, user_id: int, idx: int) -> AnswerResult:
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return AnswerResult("missing")
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt:
                return AnswerResult("missing")
            if game["status"] == "paused" and gt["status"] == "open":
                return AnswerResult("paused")
            if game["status"] != "running" or gt["status"] != "open":
                return AnswerResult("closed")
            if gt["kind"] not in ("test", "individual") or not gt["options"]:
                return AnswerResult("wrong_kind")
            denied = await self._who_can_answer(conn, game, gt, user_id)
            if denied:
                return AnswerResult(denied)
            if await conn.fetchval("SELECT now() >= $1::timestamptz", gt["deadline_at"]):
                res = await self._resolve(conn, game, gt, "timeout", None)
                return AnswerResult("timeout", res, dict(gt))
            if not 0 <= idx < len(gt["options"]):
                return AnswerResult("wrong_kind")
            inserted = await conn.fetchval(
                "INSERT INTO answers(game_task_id,user_id,choice_index,is_correct) VALUES($1,$2,$3,$4) "
                "ON CONFLICT (game_task_id) DO NOTHING RETURNING id",
                gt_id, user_id, idx, idx == gt["correct_option"])
            if not inserted:
                return AnswerResult("already")
            outcome = "correct" if idx == gt["correct_option"] else "wrong"
            res = await self._resolve(conn, game, gt, outcome, None)
            return AnswerResult("ok", res, dict(gt), choice=idx, user={"tg_id": user_id})

    async def submit_text(self, gt_id: int, user_id: int, text: str) -> AnswerResult:
        text = (text or "").strip()
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return AnswerResult("missing")
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt:
                return AnswerResult("missing")
            if game["status"] == "paused" and gt["status"] == "open":
                return AnswerResult("paused")
            if game["status"] != "running" or gt["status"] != "open":
                return AnswerResult("closed")
            if gt["kind"] == "trap" or (gt["kind"] == "individual" and gt["options"]) or gt["kind"] == "test":
                return AnswerResult("wrong_kind")
            denied = await self._who_can_answer(conn, game, gt, user_id)
            if denied:
                return AnswerResult(denied)
            if await conn.fetchval("SELECT now() >= $1::timestamptz", gt["deadline_at"]):
                res = await self._resolve(conn, game, gt, "timeout", None)
                return AnswerResult("timeout", res, dict(gt))
            if not text:
                return AnswerResult("wrong_kind")
            inserted = await conn.fetchval(
                "INSERT INTO answers(game_task_id,user_id,text) VALUES($1,$2,$3) "
                "ON CONFLICT (game_task_id) DO NOTHING RETURNING id", gt_id, user_id, text[:3500])
            if not inserted:
                return AnswerResult("already")
            await conn.execute("UPDATE game_tasks SET status='awaiting_review' WHERE id=$1", gt_id)
            await self._event(conn, game["id"], "answer_submitted", {"game_task": gt_id, "user": user_id})
            return AnswerResult("ok", None, dict(gt), text=text)

    async def check_trap_reply(self, gt_id: int, user_id: int) -> AnswerResult:
        """Tuzoqqa jamoa javob yozganda: faqat ro‘yxatdagi talaba va ochiq tuzoq bo‘lsa 'ok' qaytaradi."""
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return AnswerResult("missing")
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt or gt["kind"] != "trap":
                return AnswerResult("wrong_kind")
            if game["status"] == "paused" and gt["status"] == "open":
                return AnswerResult("paused")
            if game["status"] != "running" or gt["status"] != "open":
                return AnswerResult("closed")
            denied = await self._who_can_answer(conn, game, gt, user_id)
            if denied:
                return AnswerResult(denied)
            return AnswerResult("ok", None, dict(gt))

    async def grade(self, gt_id: int, admin_id: int, ok: bool) -> AnswerResult:
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return AnswerResult("missing")
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt:
                return AnswerResult("missing")
            if gt["status"] not in ("awaiting_review", "open") or (gt["status"] == "open" and gt["kind"] != "trap"):
                return AnswerResult("closed")
            if game["status"] == "paused":
                return AnswerResult("paused")
            if game["status"] != "running":
                return AnswerResult("closed")
            if gt["status"] == "open" and await conn.fetchval("SELECT now() >= $1::timestamptz", gt["deadline_at"]):
                res = await self._resolve(conn, game, gt, "timeout", None)  # tuzoq: deadline bo‘yicha yagona natija
                return AnswerResult("timeout", res, dict(gt))
            outcome = "correct" if ok else "wrong"
            await conn.execute(
                "UPDATE answers SET is_correct=$2, graded_by=$3, graded_at=now() WHERE game_task_id=$1",
                gt_id, ok, admin_id)
            res = await self._resolve(conn, game, gt, outcome, admin_id)
            return AnswerResult("ok", res, dict(gt))

    async def expire(self, gt_id: int) -> Optional[Resolution]:
        row = await self.db.fetchrow("SELECT game_id FROM game_tasks WHERE id=$1", gt_id)
        if not row:
            return None
        async with self.db.game_tx(row["game_id"]) as (conn, game):
            gt = await conn.fetchrow("SELECT * FROM game_tasks WHERE id=$1 FOR UPDATE", gt_id)
            if not gt or gt["status"] != "open" or game["status"] != "running":
                return None
            if not await conn.fetchval("SELECT now() >= $1::timestamptz", gt["deadline_at"]):
                return None
            return await self._resolve(conn, game, gt, "timeout", None)

    async def _who_can_answer(self, conn, game, gt, user_id: int) -> Optional[str]:
        if gt["kind"] == "individual":
            return None if gt["assigned_user_id"] == user_id else "not_yours"
        in_roster = await conn.fetchval(
            "SELECT 1 FROM game_players WHERE game_id=$1 AND user_id=$2", game["id"], user_id)
        return None if in_roster else "not_player"

    # --------------------------------------------------------------- natijani qo‘llash
    async def _resolve(self, conn, game, gt, outcome: str, graded_by: Optional[int]) -> Resolution:
        old = game["current_stage"]
        trap_cleared = False
        if gt["kind"] == "trap" and outcome == "correct":
            new = old  # tuzoqdan o‘tish — bonus yo‘q, zina o‘zgarmaydi
            trap_cleared = True
        elif outcome == "correct":
            new = min(FINAL_STAGE, old + 1)
        else:
            new = max(1, old - 1)  # 1-zinadan pastga tushmaydi
        finished = new >= FINAL_STAGE
        await conn.execute(
            "UPDATE game_tasks SET status='resolved', outcome=$2, resolved_at=now() WHERE id=$1", gt["id"], outcome)
        if finished:
            await conn.execute(
                "UPDATE games SET status='finished', current_stage=$2, max_stage_reached=$2, finished_at=now() "
                "WHERE id=$1", game["id"], FINAL_STAGE)
        else:
            await conn.execute(
                "UPDATE games SET current_stage=$2, max_stage_reached=GREATEST(max_stage_reached,$2), "
                "cleared_traps = CASE WHEN $3 THEN array_append(cleared_traps,$4) ELSE cleared_traps END WHERE id=$1",
                game["id"], new, trap_cleared, old)
        await self._event(conn, game["id"], "task_resolved",
                          {"game_task": gt["id"], "outcome": outcome, "from": old, "to": new, "by": graded_by})
        if finished:
            await self._store_results(conn, game["id"])
        return Resolution(game["id"], game["group_id"], dict(gt), outcome, old, new, finished, trap_cleared)

    async def stats(self, game_id: int, conn=None) -> dict:
        c = conn or self.db.pool
        base = await c.fetchrow(
            "SELECT count(*) FILTER (WHERE status='resolved') AS total, "
            "count(*) FILTER (WHERE outcome='correct') AS correct, "
            "count(*) FILTER (WHERE outcome='wrong') AS wrong, "
            "count(*) FILTER (WHERE outcome='timeout') AS timeout, "
            "count(*) FILTER (WHERE kind='individual' AND outcome IN ('correct','wrong')) AS individual_done "
            "FROM game_tasks WHERE game_id=$1", game_id)
        game = await c.fetchrow("SELECT * FROM games WHERE id=$1", game_id)
        top = await c.fetch(
            "SELECT p.tg_id, p.username, p.full_name, count(*) AS answered, "
            "count(*) FILTER (WHERE a.is_correct) AS correct FROM answers a "
            "JOIN game_tasks gt ON gt.id=a.game_task_id JOIN players p ON p.tg_id=a.user_id "
            "WHERE gt.game_id=$1 GROUP BY p.tg_id ORDER BY correct DESC, answered DESC, p.full_name LIMIT 5", game_id)
        duration = 0
        if game and game["started_at"]:
            secs = await c.fetchval(
                "SELECT EXTRACT(EPOCH FROM (COALESCE($1::timestamptz, now()) - $2::timestamptz))",
                game["finished_at"], game["started_at"])
            paused = game["paused_total_sec"] or 0
            if game["status"] == "paused" and game["paused_at"]:
                paused += int(await c.fetchval("SELECT EXTRACT(EPOCH FROM (now() - $1::timestamptz))", game["paused_at"]))
            duration = max(0, int(float(secs)) - paused)
        return {
            "total": base["total"], "correct": base["correct"], "wrong": base["wrong"], "timeout": base["timeout"],
            "individual_done": base["individual_done"], "duration_sec": duration,
            "stage": game["current_stage"] if game else 1,
            "top": [dict(t) for t in top],
        }

    async def _store_results(self, conn, game_id: int) -> None:
        s = await self.stats(game_id, conn)
        await conn.execute(
            "INSERT INTO results(game_id,duration_sec,total_tasks,correct_count,wrong_count,timeout_count,"
            "individual_done,final_stage,top_players) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) "
            "ON CONFLICT (game_id) DO NOTHING",
            game_id, s["duration_sec"], s["total"], s["correct"], s["wrong"], s["timeout"],
            s["individual_done"], s["stage"], s["top"])

    async def get_result(self, game_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow("SELECT * FROM results WHERE game_id=$1", game_id)

    # ------------------------------------------------------------ taymer so‘rovlari
    async def due_task_ids(self, limit: int = 20) -> list[int]:
        rows = await self.db.fetch(
            "SELECT gt.id FROM game_tasks gt JOIN games g ON g.id=gt.game_id "
            "WHERE g.status='running' AND gt.status='open' AND gt.deadline_at <= now() "
            "ORDER BY gt.deadline_at LIMIT $1", limit)
        return [r["id"] for r in rows]

    async def warn_candidates(self) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT gt.id FROM game_tasks gt JOIN games g ON g.id=gt.game_id "
            "WHERE g.status='running' AND gt.status='open' AND NOT gt.warned AND gt.time_limit_sec >= 30 "
            "AND gt.deadline_at - now() <= interval '10 seconds' AND gt.deadline_at > now()")
        out = []
        for r in rows:
            claimed = await self.db.fetchval(
                "UPDATE game_tasks SET warned=TRUE WHERE id=$1 AND NOT warned RETURNING id", r["id"])
            if claimed:
                out.append(r["id"])
        return out

    async def stale_pending_ids(self) -> list[int]:
        rows = await self.db.fetch(
            "SELECT gt.id FROM game_tasks gt JOIN games g ON g.id=gt.game_id "
            "WHERE g.status='running' AND gt.status='pending' AND gt.created_at < now() - interval '15 seconds'")
        return [r["id"] for r in rows]

    async def idle_game_ids(self) -> list[int]:
        """Ishlayotgan, lekin faol topshirig‘i yo‘q o‘yinlar (masalan, server qayta ishga tushgan)."""
        rows = await self.db.fetch(
            "SELECT g.id FROM games g WHERE g.status='running' AND NOT EXISTS ("
            "SELECT 1 FROM game_tasks gt WHERE gt.game_id=g.id AND gt.status = ANY($1::text[])) "
            "AND COALESCE((SELECT max(resolved_at) FROM game_tasks WHERE game_id=g.id), g.started_at) "
            "< now() - interval '20 seconds'", ACTIVE_TASK_STATUSES)
        return [r["id"] for r in rows]

    async def needs_input_tasks(self, game_id: Optional[int] = None) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT gt.*, g.admin_id, g.group_id FROM game_tasks gt JOIN games g ON g.id=gt.game_id "
            "WHERE gt.status='needs_input' AND g.status='running' AND ($1::int IS NULL OR g.id=$1)", game_id)
        return [dict(r) for r in rows]

    async def pending_reviews(self, game_id: Optional[int] = None) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT gt.*, g.group_id, gr.title AS group_title, a.text AS answer_text, a.user_id AS answer_user, "
            "p.full_name, p.username FROM game_tasks gt JOIN games g ON g.id=gt.game_id "
            "JOIN groups gr ON gr.chat_id=g.group_id LEFT JOIN answers a ON a.game_task_id=gt.id "
            "LEFT JOIN players p ON p.tg_id=a.user_id "
            "WHERE gt.status='awaiting_review' AND ($1::int IS NULL OR g.id=$1) ORDER BY gt.id", game_id)
        return [dict(r) for r in rows]

    async def dirty_lobby_ids(self) -> list[int]:
        rows = await self.db.fetch(
            "SELECT id FROM games WHERE status='lobby' AND lobby_dirty AND lobby_message_id IS NOT NULL")
        return [r["id"] for r in rows]

    async def has_active_games(self) -> bool:
        return bool(await self.db.fetchval(
            "SELECT 1 FROM games WHERE status = ANY($1::text[]) LIMIT 1", ACTIVE_GAME_STATUSES))

    # ------------------------------------------------------------------ yordamchi
    async def _int_setting(self, key: str, default: int) -> int:
        if self.settings is None:
            return default
        try:
            return await self.settings.get_int(key)
        except Exception:
            return default

    async def _event(self, conn, game_id: int, type_: str, payload: dict) -> None:
        await conn.execute("INSERT INTO game_events(game_id,type,payload) VALUES($1,$2,$3)",
                           game_id, type_, payload)

    async def recent_events(self, game_id: int, limit: int = 15) -> list[asyncpg.Record]:
        return await self.db.fetch(
            "SELECT * FROM game_events WHERE game_id=$1 ORDER BY id DESC LIMIT $2", game_id, limit)
