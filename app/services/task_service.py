"""Topshiriqlar va tuzoq topshiriqlari: qo‘shish, tahrirlash, o‘chirish, demo ma’lumotlar."""
from __future__ import annotations

from typing import Optional, Sequence

import asyncpg

from app.database import Db

KINDS = {
    "test": "A. Variantli test",
    "text": "B. Matnli savol",
    "individual": "C. Individual topshiriq",
    "creative": "D. Ijodiy topshiriq",
}
KIND_SHORT = {"test": "Test", "text": "Matnli", "individual": "Individual", "creative": "Ijodiy", "trap": "Tuzoq"}
LETTERS = "ABCD"


class TaskError(ValueError):
    pass


class TaskService:
    def __init__(self, db: Db):
        self.db = db

    # ---------- topshiriqlar ----------
    async def create_task(self, *, stage_no: int, kind: str, question: str, time_limit_sec: int,
                          options: Optional[Sequence[str]] = None, correct_option: Optional[int] = None,
                          created_by: Optional[int] = None, is_demo: bool = False) -> int:
        question = (question or "").strip()
        if kind not in KINDS:
            raise TaskError("Noto‘g‘ri topshiriq turi")
        if not 1 <= stage_no <= 9:
            raise TaskError("Zina 1 dan 9 gacha bo‘lishi kerak (10-zinada topshiriq berilmaydi)")
        if not question:
            raise TaskError("Savol matni bo‘sh bo‘lmasligi kerak")
        if not 10 <= time_limit_sec <= 3600:
            raise TaskError("Vaqt 10 soniyadan 3600 soniyagacha bo‘lishi kerak")
        options = [o.strip() for o in (options or []) if o and o.strip()]
        if kind == "test":
            if not 2 <= len(options) <= 4:
                raise TaskError("Test uchun 2 dan 4 gacha variant kerak")
        elif kind == "individual":
            if options and not 2 <= len(options) <= 4:
                raise TaskError("Variantlar soni 2–4 bo‘lishi kerak")
        else:
            options = []
        if options:
            if correct_option is None or not 0 <= correct_option < len(options):
                raise TaskError("To‘g‘ri javob variantlar ichidan tanlanishi kerak")
        else:
            correct_option = None
        async with self.db.tx() as conn:
            task_id = await conn.fetchval(
                "INSERT INTO tasks(stage_no,kind,question,correct_option,time_limit_sec,created_by,is_demo) "
                "VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING id",
                stage_no, kind, question, correct_option, time_limit_sec, created_by, is_demo)
            for pos, text in enumerate(options):
                await conn.execute("INSERT INTO task_options(task_id,position,text) VALUES($1,$2,$3)",
                                   task_id, pos, text)
        return task_id

    async def get_task(self, task_id: int) -> Optional[dict]:
        row = await self.db.fetchrow("SELECT * FROM tasks WHERE id=$1", task_id)
        if not row:
            return None
        task = dict(row)
        opts = await self.db.fetch("SELECT text FROM task_options WHERE task_id=$1 ORDER BY position", task_id)
        task["options"] = [o["text"] for o in opts]
        return task

    async def list_tasks(self, stage_no: Optional[int] = None) -> list[asyncpg.Record]:
        if stage_no is None:
            return await self.db.fetch("SELECT * FROM tasks WHERE is_active ORDER BY stage_no, id")
        return await self.db.fetch("SELECT * FROM tasks WHERE is_active AND stage_no=$1 ORDER BY id", stage_no)

    async def count_by_stage(self) -> dict[int, int]:
        rows = await self.db.fetch("SELECT stage_no, count(*) c FROM tasks WHERE is_active GROUP BY stage_no")
        return {r["stage_no"]: r["c"] for r in rows}

    async def delete_task(self, task_id: int) -> bool:
        # O‘yin tarixini saqlash uchun game_tasks.task_id SET NULL; topshiriq o‘zi o‘chiriladi.
        res = await self.db.execute("DELETE FROM tasks WHERE id=$1", task_id)
        return res.endswith("1")

    async def update_field(self, task_id: int, field: str, value) -> None:
        task = await self.get_task(task_id)
        if not task:
            raise TaskError("Topshiriq topilmadi")
        if field == "question":
            value = str(value).strip()
            if not value:
                raise TaskError("Savol matni bo‘sh bo‘lmasligi kerak")
            await self.db.execute("UPDATE tasks SET question=$2 WHERE id=$1", task_id, value)
        elif field == "time":
            value = int(value)
            if not 10 <= value <= 3600:
                raise TaskError("Vaqt 10–3600 soniya oralig‘ida bo‘lishi kerak")
            await self.db.execute("UPDATE tasks SET time_limit_sec=$2 WHERE id=$1", task_id, value)
        elif field == "correct":
            value = int(value)
            if not task["options"] or not 0 <= value < len(task["options"]):
                raise TaskError("Bunday variant yo‘q")
            await self.db.execute("UPDATE tasks SET correct_option=$2 WHERE id=$1", task_id, value)
        elif field == "stage":
            value = int(value)
            if not 1 <= value <= 9:
                raise TaskError("Zina 1–9 oralig‘ida bo‘lishi kerak")
            await self.db.execute("UPDATE tasks SET stage_no=$2 WHERE id=$1", task_id, value)
        elif field == "options":
            options = [o.strip() for o in value if o and o.strip()]
            if not 2 <= len(options) <= 4 or task["kind"] not in ("test", "individual"):
                raise TaskError("2–4 ta variant kerak (faqat test/individual uchun)")
            correct = task["correct_option"] if task["correct_option"] is not None else 0
            if correct >= len(options):
                correct = 0
            async with self.db.tx() as conn:
                await conn.execute("DELETE FROM task_options WHERE task_id=$1", task_id)
                for pos, text in enumerate(options):
                    await conn.execute("INSERT INTO task_options(task_id,position,text) VALUES($1,$2,$3)",
                                       task_id, pos, text)
                await conn.execute("UPDATE tasks SET correct_option=$2 WHERE id=$1", task_id, correct)
        else:
            raise TaskError("Noma’lum maydon")

    # ---------- tuzoqlar ----------
    async def create_trap(self, *, stage_no: int, prompt: str, time_limit_sec: int,
                          story_id: Optional[int] = None, created_by: Optional[int] = None) -> int:
        prompt = (prompt or "").strip()
        if not prompt:
            raise TaskError("Tuzoq matni bo‘sh bo‘lmasligi kerak")
        if not 1 <= stage_no <= 9:
            raise TaskError("Zina 1–9 oralig‘ida bo‘lishi kerak")
        if not 10 <= time_limit_sec <= 3600:
            raise TaskError("Vaqt 10–3600 soniya oralig‘ida bo‘lishi kerak")
        return await self.db.fetchval(
            "INSERT INTO traps(story_id,stage_no,prompt,time_limit_sec,created_by) VALUES($1,$2,$3,$4,$5) RETURNING id",
            story_id, stage_no, prompt, time_limit_sec, created_by)

    async def get_trap(self, trap_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow("SELECT * FROM traps WHERE id=$1", trap_id)

    async def list_traps(self, story_id: Optional[int] = None, stage_no: Optional[int] = None) -> list[asyncpg.Record]:
        return await self.db.fetch(
            "SELECT * FROM traps WHERE is_active AND ($1::int IS NULL OR story_id IS NULL OR story_id=$1) "
            "ORDER BY (CASE WHEN stage_no=$2 THEN 0 ELSE 1 END), stage_no, id", story_id, stage_no)

    async def delete_trap(self, trap_id: int) -> bool:
        return (await self.db.execute("DELETE FROM traps WHERE id=$1", trap_id)).endswith("1")

    async def update_trap(self, trap_id: int, field: str, value) -> None:
        if field == "prompt":
            if not str(value).strip():
                raise TaskError("Matn bo‘sh bo‘lmasligi kerak")
            await self.db.execute("UPDATE traps SET prompt=$2 WHERE id=$1", trap_id, str(value).strip())
        elif field == "time":
            value = int(value)
            if not 10 <= value <= 3600:
                raise TaskError("Vaqt 10–3600 soniya oralig‘ida bo‘lishi kerak")
            await self.db.execute("UPDATE traps SET time_limit_sec=$2 WHERE id=$1", trap_id, value)
        else:
            raise TaskError("Noma’lum maydon")

    # ---------- demo ma’lumotlar ----------
    async def seed_demo(self) -> int:
        """Bazada birorta ham topshiriq bo‘lmasa, o‘yinni darhol sinab ko‘rish uchun demo topshiriqlar qo‘shiladi.
        Admin ularni o‘chirishi yoki tahrirlashi mumkin (is_demo=true)."""
        from app.seed.demo_tasks import DEMO_TASKS, DEMO_TRAPS
        if await self.db.fetchval("SELECT count(*) FROM tasks") or await self.db.fetchval("SELECT count(*) FROM traps"):
            return 0
        for t in DEMO_TASKS:
            await self.create_task(is_demo=True, **t)
        for tr in DEMO_TRAPS:
            await self.create_trap(**tr)
        return len(DEMO_TASKS) + len(DEMO_TRAPS)
