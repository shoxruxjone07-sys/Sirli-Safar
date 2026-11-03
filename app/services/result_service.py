"""Natijalarni matn ko‘rinishiga keltirish."""
from __future__ import annotations

from app.utils.tg import esc, fmt_duration, mention


def format_stats(stats: dict, *, title: str = "📊 Natijalar") -> str:
    lines = [
        f"<b>{title}</b>",
        f"⏱ O‘yin davomiyligi: <b>{fmt_duration(stats['duration_sec'])}</b>",
        f"✅ To‘g‘ri javoblar: <b>{stats['correct']}</b>",
        f"❌ Noto‘g‘ri javoblar: <b>{stats['wrong']}</b>",
        f"⏰ Vaqt tugagan topshiriqlar: <b>{stats['timeout']}</b>",
        f"🎯 Bajarilgan individual topshiriqlar: <b>{stats['individual_done']}</b>",
    ]
    top = stats.get("top") or []
    if top:
        lines.append("")
        lines.append("🏅 <b>Eng faol talabalar</b>")
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, t in enumerate(top):
            lines.append(f"{medals[i]} {mention(t['tg_id'], t['full_name'], t.get('username'))} — "
                         f"{t['answered']} ta javob, {t['correct']} ta to‘g‘ri")
    else:
        lines.append("")
        lines.append("🏅 Eng faol talabalar: ma’lumot yo‘q")
    return "\n".join(lines)
