"""Hikoyalar kutubxonasi: o‘qish va tahrirlash (hamma narsa bazadan o‘qiladi)."""
from __future__ import annotations

from typing import Optional

import asyncpg

from app.database import Db


class StoryService:
    def __init__(self, db: Db):
        self.db = db

    async def list_stories(self, only_active: bool = True) -> list[asyncpg.Record]:
        q = "SELECT * FROM stories " + ("WHERE is_active " if only_active else "") + "ORDER BY position, id"
        return await self.db.fetch(q)

    async def get_story(self, story_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)

    async def stages(self, story_id: int) -> list[asyncpg.Record]:
        return await self.db.fetch("SELECT * FROM story_stages WHERE story_id=$1 ORDER BY stage_no", story_id)

    async def get_stage(self, story_id: int, stage_no: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow(
            "SELECT * FROM story_stages WHERE story_id=$1 AND stage_no=$2", story_id, stage_no)

    async def get_stage_by_id(self, stage_id: int) -> Optional[asyncpg.Record]:
        return await self.db.fetchrow(
            "SELECT ss.*, s.title AS story_title, s.theme FROM story_stages ss "
            "JOIN stories s ON s.id=ss.story_id WHERE ss.id=$1", stage_id)

    FIELDS = {"title": "title", "body": "body", "bridge": "bridge", "final": "final_scene"}

    async def update_stage_text(self, stage_id: int, field: str, value: str) -> bool:
        col = self.FIELDS.get(field)
        if not col:
            return False
        res = await self.db.execute(f"UPDATE story_stages SET {col}=$2 WHERE id=$1", stage_id, value)
        return res.endswith("1")

    async def set_trap_flag(self, stage_id: int, flag: bool) -> None:
        await self.db.execute("UPDATE story_stages SET has_trap=$2 WHERE id=$1", stage_id, flag)

    async def attach_media(self, stage_id: int, file_id: str, media_type: str) -> None:
        if media_type not in ("photo", "animation"):
            raise ValueError("media_type")
        await self.db.execute(
            "UPDATE story_stages SET media_file_id=$2, media_type=$3 WHERE id=$1", stage_id, file_id, media_type)

    async def clear_media(self, stage_id: int) -> None:
        await self.db.execute("UPDATE story_stages SET media_file_id=NULL, media_type=NULL WHERE id=$1", stage_id)

    async def update_story_title(self, story_id: int, title: str) -> None:
        await self.db.execute("UPDATE stories SET title=$2 WHERE id=$1", story_id, title)
