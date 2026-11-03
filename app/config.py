"""Sozlamalar: barcha maxfiy qiymatlar faqat muhit o‘zgaruvchilaridan olinadi."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

WEBHOOK_PATH = "/webhook"
_SECRET_RE = re.compile(r"^[A-Za-z0-9_-]{16,256}$")


class ConfigError(RuntimeError):
    pass


def load_dotenv(path: str | os.PathLike | None = None, env: dict | None = None) -> int:
    """Loyiha papkasidagi `.env` faylini o‘qiydi (lokal ishlatish uchun). Muhitda allaqachon bor qiymatlarni
    (masalan, Render’dagi) o‘zgartirmaydi. Qaytaradi: yangi o‘rnatilgan o‘zgaruvchilar soni."""
    from pathlib import Path
    target = env if env is not None else os.environ
    file = Path(path) if path else Path(__file__).resolve().parent.parent / ".env"
    if not file.is_file():
        return 0
    count = 0
    for raw in file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and value and not target.get(key):
            target[key] = value
            count += 1
    return count


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset
    admin_password_hash: str
    database_url: str
    webhook_url: str  # asosiy manzil, oxirida "/" va "/webhook" siz
    webhook_secret: str
    port: int = 8080
    admin_session_hours: int = 12
    log_level: str = "INFO"

    @property
    def webhook_full_url(self) -> str:
        return f"{self.webhook_url}{WEBHOOK_PATH}"


def _parse_admin_ids(raw: str) -> frozenset:
    ids = set()
    for part in re.split(r"[,\s;]+", raw.strip()):
        if not part:
            continue
        if not re.fullmatch(r"-?\d+", part):
            raise ConfigError("ADMIN_IDS faqat vergul bilan ajratilgan raqamlardan iborat bo‘lishi kerak")
        ids.add(int(part))
    return frozenset(ids)


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    missing = []

    def need(name: str) -> str:
        value = (env.get(name) or "").strip()
        if not value:
            missing.append(name)
        return value

    bot_token = need("BOT_TOKEN")
    admin_ids_raw = need("ADMIN_IDS")
    pw_hash = need("ADMIN_PASSWORD_HASH")
    database_url = need("DATABASE_URL")
    secret = need("WEBHOOK_SECRET")
    webhook_url = (env.get("WEBHOOK_URL") or env.get("RENDER_EXTERNAL_URL") or "").strip()
    if not webhook_url:
        missing.append("WEBHOOK_URL")
    if missing:
        raise ConfigError("Quyidagi muhit o‘zgaruvchilari kiritilmagan: " + ", ".join(missing))

    admin_ids = _parse_admin_ids(admin_ids_raw)
    if not admin_ids:
        raise ConfigError("ADMIN_IDS bo‘sh bo‘lmasligi kerak")
    if not _SECRET_RE.match(secret):
        raise ConfigError("WEBHOOK_SECRET faqat A-Z a-z 0-9 _ - belgilaridan iborat, 16–256 belgi bo‘lishi kerak")
    if not pw_hash.startswith("$2"):
        raise ConfigError("ADMIN_PASSWORD_HASH bcrypt hash bo‘lishi kerak (scripts/make_password_hash.py)")

    webhook_url = webhook_url.rstrip("/")
    if webhook_url.endswith(WEBHOOK_PATH):
        webhook_url = webhook_url[: -len(WEBHOOK_PATH)]
    if not webhook_url.startswith("https://"):
        raise ConfigError("WEBHOOK_URL https:// bilan boshlanishi kerak")

    try:
        port = int(env.get("PORT") or 8080)
        hours = int(env.get("ADMIN_SESSION_HOURS") or 12)
    except ValueError as exc:
        raise ConfigError("PORT va ADMIN_SESSION_HOURS butun son bo‘lishi kerak") from exc

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        admin_password_hash=pw_hash,
        database_url=database_url,
        webhook_url=webhook_url,
        webhook_secret=secret,
        port=port,
        admin_session_hours=max(1, hours),
        log_level=(env.get("LOG_LEVEL") or "INFO").upper(),
    )
