"""Admin autentifikatsiyasi: bcrypt hash, urinishlar limiti, sessiya muddati."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import bcrypt

from app.config import Config
from app.database import Db

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def _verify_sync(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("ascii"))
    except ValueError:
        return False


async def verify_password(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(_verify_sync, password, hashed)


@dataclass
class LoginResult:
    status: str  # ok | bad | locked | forbidden
    attempts_left: int = 0
    locked_minutes: int = 0


class AdminAuth:
    def __init__(self, db: Db, config: Config):
        self.db = db
        self.config = config

    def is_admin_id(self, tg_id: int) -> bool:
        return tg_id in self.config.admin_ids

    async def is_authenticated(self, tg_id: int) -> bool:
        if not self.is_admin_id(tg_id):
            return False
        return bool(await self.db.fetchval(
            "SELECT authenticated_until > now() FROM admins WHERE tg_id=$1", tg_id))

    async def lock_minutes_left(self, tg_id: int) -> int:
        secs = await self.db.fetchval(
            "SELECT EXTRACT(EPOCH FROM (locked_until - now())) FROM admins "
            "WHERE tg_id=$1 AND locked_until > now()", tg_id)
        return int((float(secs) + 59) // 60) if secs else 0

    async def login(self, tg_id: int, name: str, password: str) -> LoginResult:
        if not self.is_admin_id(tg_id):
            return LoginResult("forbidden")
        async with self.db.tx() as conn:
            await conn.execute(
                "INSERT INTO admins(tg_id, name) VALUES($1,$2) ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
                tg_id, name)
            row = await conn.fetchrow("SELECT * FROM admins WHERE tg_id=$1 FOR UPDATE", tg_id)
            locked_left = await conn.fetchval(
                "SELECT CEIL(EXTRACT(EPOCH FROM (locked_until - now()))) FROM admins "
                "WHERE tg_id=$1 AND locked_until > now()", tg_id)
            if locked_left:
                return LoginResult("locked", locked_minutes=max(1, int((locked_left + 59) // 60)))
            if row["locked_until"] is not None:  # blok muddati o‘tgan — urinishlar nolga
                await conn.execute("UPDATE admins SET failed_attempts=0, locked_until=NULL WHERE tg_id=$1", tg_id)
                row = await conn.fetchrow("SELECT * FROM admins WHERE tg_id=$1", tg_id)
            ok = await verify_password(password, self.config.admin_password_hash)
            if ok:
                await conn.execute(
                    "UPDATE admins SET failed_attempts=0, locked_until=NULL, last_login_at=now(), "
                    "authenticated_until = now() + make_interval(hours => $2) WHERE tg_id=$1",
                    tg_id, self.config.admin_session_hours)
                return LoginResult("ok")
            failed = row["failed_attempts"] + 1
            if failed >= MAX_ATTEMPTS:
                await conn.execute(
                    "UPDATE admins SET failed_attempts=0, authenticated_until=NULL, "
                    "locked_until = now() + make_interval(mins => $2) WHERE tg_id=$1", tg_id, LOCK_MINUTES)
                log.warning("Admin %s: urinishlar limiti tugadi, %s daqiqaga bloklandi", tg_id, LOCK_MINUTES)
                return LoginResult("locked", locked_minutes=LOCK_MINUTES)
            await conn.execute("UPDATE admins SET failed_attempts=$2 WHERE tg_id=$1", tg_id, failed)
            return LoginResult("bad", attempts_left=MAX_ATTEMPTS - failed)

    async def logout(self, tg_id: int) -> None:
        await self.db.execute("UPDATE admins SET authenticated_until=NULL WHERE tg_id=$1", tg_id)
