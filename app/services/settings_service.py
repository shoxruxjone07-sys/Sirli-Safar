"""Global sozlamalar (settings jadvali)."""
from __future__ import annotations

from app.database import Db

DEFAULTS = {
    "reveal_correct": "1",       # noto‘g‘ri javobda to‘g‘ri variantni ko‘rsatish
    "default_time_limit": "60",  # yangi topshiriq uchun standart vaqt (soniya)
    "trap_time_limit": "120",    # admin jonli bergan tuzoq uchun vaqt (soniya)
}


class SettingsService:
    def __init__(self, db: Db):
        self.db = db

    async def get(self, key: str) -> str:
        val = await self.db.fetchval("SELECT value FROM settings WHERE key=$1", key)
        return val if val is not None else DEFAULTS.get(key, "")

    async def get_opt(self, key: str):
        return await self.db.fetchval("SELECT value FROM settings WHERE key=$1", key)

    async def get_bool(self, key: str) -> bool:
        return (await self.get(key)) == "1"

    async def get_int(self, key: str) -> int:
        try:
            return int(await self.get(key))
        except ValueError:
            return int(DEFAULTS.get(key, "0") or 0)

    async def set(self, key: str, value: str) -> None:
        await self.db.execute(
            "INSERT INTO settings(key,value) VALUES($1,$2) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
            key, value)

    async def delete(self, key: str) -> None:
        await self.db.execute("DELETE FROM settings WHERE key=$1", key)

    async def toggle(self, key: str) -> bool:
        new = "0" if await self.get_bool(key) else "1"
        await self.set(key, new)
        return new == "1"
