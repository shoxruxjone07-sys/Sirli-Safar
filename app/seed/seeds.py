"""Hikoyalarni bazaga yuklash (faqat yo‘q bo‘lsa; admin tahrirlarini ustiga yozmaydi)
va 40 ta vizual promptni fayl sifatida chiqarish."""
from __future__ import annotations

import logging
from pathlib import Path

from app.database import Db
from app.seed import story_dalil, story_kosmos, story_orol, story_sivilizatsiya

log = logging.getLogger(__name__)
MODULES = [story_orol, story_sivilizatsiya, story_dalil, story_kosmos]
PROMPTS_FILE = Path(__file__).resolve().parent.parent.parent / "assets" / "stories" / "image_prompts.md"


def full_prompt(module, stage: dict) -> str:
    return f"{stage['prompt']}, {module.STYLE}"


def validate_story_data() -> None:
    for position, mod in enumerate(MODULES):
        st = mod.STORY
        assert len(st["stages"]) == 10, f"{st['slug']}: 10 ta bosqich kerak"
        for i, stage in enumerate(st["stages"], start=1):
            assert stage["no"] == i, f"{st['slug']}: bosqich tartibi buzilgan ({i})"
            for key in ("title", "body", "visual", "prompt"):
                assert stage.get(key), f"{st['slug']} {i}: '{key}' bo‘sh"
            if i < 10:
                assert stage.get("bridge"), f"{st['slug']} {i}: bog‘lovchi jumla yo‘q"
        assert st["stages"][9].get("final"), f"{st['slug']}: yakuniy sahna yo‘q"
        assert any(s.get("trap") for s in st["stages"]), f"{st['slug']}: tuzoq yo‘q"


async def seed_stories(db: Db) -> int:
    """Yangi qo‘shilgan hikoyalar sonini qaytaradi."""
    added = 0
    for position, mod in enumerate(MODULES):
        st = mod.STORY
        async with db.tx() as conn:
            exists = await conn.fetchval("SELECT id FROM stories WHERE slug=$1", st["slug"])
            if exists:
                continue
            story_id = await conn.fetchval(
                "INSERT INTO stories(slug,title,genre,synopsis,theme,position) VALUES($1,$2,$3,$4,$5,$6) RETURNING id",
                st["slug"], st["title"], st["genre"], st["synopsis"], st["theme"], position)
            for stage in st["stages"]:
                await conn.execute(
                    "INSERT INTO story_stages(story_id,stage_no,title,body,bridge,visual_desc,image_prompt,has_trap,final_scene) "
                    "VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)",
                    story_id, stage["no"], stage["title"], stage["body"], stage.get("bridge", ""),
                    stage["visual"], full_prompt(mod, stage), bool(stage.get("trap")), stage.get("final"))
            added += 1
            log.info("Hikoya yuklandi: %s", st["title"])
    return added


def write_prompts_markdown(path: Path = PROMPTS_FILE) -> int:
    lines = [
        "# SIRLI SAFAR — 40 ta rasm uchun ingliz tilidagi promptlar",
        "",
        "Barcha promptlar bir xil vizual uslubda (cinematic, realistik fantasy, sifatli yorug‘lik, 16:9).",
        "Pullik generator majburiy emas: istalgan bepul rasm generatorida ishlating, so‘ng rasmni botga yuborib,",
        "admin panelda **Hikoyalar kutubxonasi → hikoya → bosqich → 🖼 Rasm/GIF biriktirish** orqali biriktiring.",
        "",
    ]
    n = 0
    for mod in MODULES:
        st = mod.STORY
        lines += [f"## {st['title']}", ""]
        for stage in st["stages"]:
            n += 1
            lines += [
                f"### {stage['no']}-bosqich — {stage['title']}" + ("  🪤 (tuzoq)" if stage.get("trap") else ""),
                f"*Tasvir tavsifi:* {stage['visual']}",
                "",
                f"```\n{full_prompt(mod, stage)}\n```",
                "",
            ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return n


if __name__ == "__main__":
    validate_story_data()
    print(f"{write_prompts_markdown()} ta prompt yozildi → {PROMPTS_FILE}")
