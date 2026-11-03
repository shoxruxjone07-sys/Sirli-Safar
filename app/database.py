"""PostgreSQL (asyncpg) ulanishi, migratsiyalar va o‘yin bo‘yicha qulflash."""
from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import asyncpg

log = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def _ssl_for(dsn: str):
    """Supabase uchun SSL majburiy; lokal bazada kerak emas."""
    if re.search(r"[?&]sslmode=", dsn):
        return None  # asyncpg o‘zi o‘qiydi
    host = re.sub(r"^.*@", "", dsn.split("?")[0].split("//", 1)[-1]).split("/")[0]
    host = host.split(":")[0].strip("[]")
    if host in _LOCAL_HOSTS or dsn.startswith("postgresql:///") or "host=/" in dsn:
        return None
    return "require"


async def _init_conn(conn: asyncpg.Connection) -> None:
    for typ in ("jsonb", "json"):
        await conn.set_type_codec(typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


class Db:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def connect(cls, dsn: str, *, min_size: int = 1, max_size: int = 6) -> "Db":
        kwargs: dict[str, Any] = {}
        ssl = _ssl_for(dsn)
        if ssl:
            kwargs["ssl"] = ssl
        pool = await asyncpg.create_pool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            init=_init_conn,
            statement_cache_size=0,  # Supabase pooler (pgbouncer) bilan mos
            command_timeout=30,
            **kwargs,
        )
        return cls(pool)

    async def close(self) -> None:
        await self.pool.close()

    # --- oddiy so‘rovlar ---
    async def fetch(self, q: str, *a):
        return await self.pool.fetch(q, *a)

    async def fetchrow(self, q: str, *a):
        return await self.pool.fetchrow(q, *a)

    async def fetchval(self, q: str, *a):
        return await self.pool.fetchval(q, *a)

    async def execute(self, q: str, *a):
        return await self.pool.execute(q, *a)

    @asynccontextmanager
    async def tx(self) -> AsyncIterator[asyncpg.Connection]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    @asynccontextmanager
    async def game_tx(self, game_id: int) -> AsyncIterator[tuple[asyncpg.Connection, asyncpg.Record | None]]:
        """O‘yin qatorini qulflaydi. Barcha o‘zgartirishlar shu tartibda (avval o‘yin) bajariladi —
        shu sababli bir vaqtda kelgan javoblar, taymer va admin amallari ketma-ket ishlaydi."""
        async with self.tx() as conn:
            game = await conn.fetchrow("SELECT * FROM games WHERE id=$1 FOR UPDATE", game_id)
            yield conn, game

    async def now(self):
        return await self.fetchval("SELECT now()")


async def run_migrations(db: Db) -> list[str]:
    applied: list[str] = []
    async with db.pool.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock(727401)")
        try:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            done = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                sql = path.read_text(encoding="utf-8")
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute("INSERT INTO schema_migrations(version) VALUES($1)", path.name)
                applied.append(path.name)
                log.info("Migratsiya qo‘llandi: %s", path.name)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(727401)")
    return applied
