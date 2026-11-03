"""aiogram FSM holatini PostgreSQL’da saqlash (Render qayta ishga tushsa ham yo‘qolmaydi)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from app.database import Db


class PgStorage(BaseStorage):
    def __init__(self, db: Db):
        self.db = db

    @staticmethod
    def _k(key: StorageKey) -> str:
        return f"{key.chat_id}:{key.user_id}:{key.thread_id or 0}:{key.destiny}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        await self.db.execute(
            "INSERT INTO user_states(key, state) VALUES($1,$2) "
            "ON CONFLICT (key) DO UPDATE SET state=EXCLUDED.state, updated_at=now()",
            self._k(key), value,
        )

    async def get_state(self, key: StorageKey) -> Optional[str]:
        return await self.db.fetchval("SELECT state FROM user_states WHERE key=$1", self._k(key))

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        await self.db.execute(
            "INSERT INTO user_states(key, data) VALUES($1,$2) "
            "ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=now()",
            self._k(key), dict(data),
        )

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        row = await self.db.fetchval("SELECT data FROM user_states WHERE key=$1", self._k(key))
        return dict(row) if row else {}

    async def close(self) -> None:  # pool Db tomonidan yopiladi
        return None
