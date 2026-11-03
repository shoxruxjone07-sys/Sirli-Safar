"""Ma’lumotlar bazasidan zaxira nusxa olish.
1) To‘liq PostgreSQL dump (pg_dump o‘rnatilgan bo‘lsa):  python scripts/backup.py dump
2) Kontent JSON (hikoya, topshiriq, natijalar):          python scripts/backup.py json
DATABASE_URL muhit o‘zgaruvchisidan olinadi. Fayllar ./backups/ papkasiga yoziladi."""
import asyncio
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OUT = Path("backups")


async def json_backup(url: str) -> Path:
    from app.database import Db
    from app.services.backup_service import export_json
    db = await Db.connect(url, min_size=1, max_size=1)
    try:
        data = await export_json(db)
    finally:
        await db.close()
    path = OUT / f"sirli-safar-{dt.datetime.now():%Y%m%d-%H%M}.json"
    path.write_bytes(data)
    return path


def dump_backup(url: str) -> Path:
    if not shutil.which("pg_dump"):
        sys.exit("pg_dump topilmadi. PostgreSQL client o‘rnating yoki 'json' rejimidan foydalaning.")
    path = OUT / f"sirli-safar-{dt.datetime.now():%Y%m%d-%H%M}.sql"
    subprocess.run(["pg_dump", "--no-owner", "--no-privileges", "-f", str(path), url], check=True)
    return path


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL o‘rnatilmagan.")
    mode = sys.argv[1] if len(sys.argv) > 1 else "json"
    OUT.mkdir(exist_ok=True)
    path = dump_backup(url) if mode == "dump" else asyncio.run(json_backup(url))
    print("Zaxira saqlandi:", path)


if __name__ == "__main__":
    main()
