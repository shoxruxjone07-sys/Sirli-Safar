"""Kontentni JSON ko‘rinishida zaxiralash (hikoyalar, topshiriqlar, tuzoqlar, natijalar)."""
from __future__ import annotations

import datetime as dt
import decimal
import json
from typing import Any

from app.database import Db

TABLES = {
    "stories": "SELECT * FROM stories ORDER BY id",
    "story_stages": "SELECT * FROM story_stages ORDER BY story_id, stage_no",
    "tasks": "SELECT * FROM tasks ORDER BY id",
    "task_options": "SELECT * FROM task_options ORDER BY task_id, position",
    "traps": "SELECT * FROM traps ORDER BY id",
    "groups": "SELECT * FROM groups ORDER BY chat_id",
    "games": "SELECT * FROM games ORDER BY id",
    "results": "SELECT * FROM results ORDER BY game_id",
    "settings": "SELECT * FROM settings WHERE key NOT LIKE 'gif_builtin:%' ORDER BY key",
}


def _default(o: Any):
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


async def export_json(db: Db) -> bytes:
    data: dict[str, Any] = {"app": "SIRLI SAFAR", "exported_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    for name, query in TABLES.items():
        data[name] = [dict(r) for r in await db.fetch(query)]
    return json.dumps(data, ensure_ascii=False, indent=1, default=_default).encode("utf-8")
