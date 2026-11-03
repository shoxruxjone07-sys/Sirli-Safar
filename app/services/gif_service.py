"""Olqishlovchi / xafa / g‘alaba animatsiyalari (Pillow bilan yaratiladigan GIF).
Admin o‘z GIF’ini yuklagan bo‘lsa, o‘sha ishlatiladi; aks holda shu o‘rnatilgan animatsiya yuboriladi."""
from __future__ import annotations

import io
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

from app.services.staircase_service import _font, _text_center

W, H, FRAMES = 480, 270, 16

KINDS = {
    "correct": {"text": "TO'G'RI!", "bg": ((8, 70, 48), (4, 28, 22)), "fg": (200, 255, 215),
                "colors": [(255, 215, 0), (80, 220, 140), (255, 255, 255), (90, 200, 255)]},
    "wrong": {"text": "NOTO'G'RI", "bg": ((90, 20, 28), (30, 8, 12)), "fg": (255, 215, 215),
              "colors": [(160, 160, 170), (200, 90, 90), (110, 110, 120)]},
    "victory": {"text": "G'ALABA!", "bg": ((70, 46, 4), (22, 12, 2)), "fg": (255, 236, 150),
                "colors": [(255, 215, 0), (255, 140, 0), (255, 255, 255), (255, 90, 120), (120, 220, 255)]},
}


def _bg(top, bottom) -> Image.Image:
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


@lru_cache(maxsize=8)
def build_gif(kind: str) -> bytes:
    spec = KINDS[kind]
    rng = random.Random(kind)
    parts = [
        (rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 20), rng.choice(spec["colors"]), rng.randint(4, 9),
         rng.uniform(-3, 3))
        for _ in range(48)
    ]
    frames = []
    for f in range(FRAMES):
        img = _bg(*spec["bg"])
        d = ImageDraw.Draw(img)
        if kind == "victory":  # otashbozlik: kengayuvchi nurlar
            for b in range(3):
                bx, by = 120 + b * 120, 70 + (b % 2) * 60
                prog = ((f + b * 5) % FRAMES) / FRAMES
                for k in range(14):
                    ang = k * math.pi * 2 / 14
                    r0, r1 = 12 + prog * 38, 20 + prog * 70
                    d.line([(bx + r0 * math.cos(ang), by + r0 * math.sin(ang)),
                            (bx + r1 * math.cos(ang), by + r1 * math.sin(ang))],
                           fill=spec["colors"][(k + b) % len(spec["colors"])], width=3)
        for (x, y0, speed, color, size, drift) in parts:  # konfetti / zarralar
            y = (y0 + speed * f) % H
            x2 = (x + drift * f) % W
            d.rectangle([x2, y, x2 + size, y + size * 0.6], fill=color)
        if kind == "wrong":
            offset = 9 if f % 2 == 0 else -9
            cx = W / 2 + offset
            size = 56
        else:
            cx = W / 2
            size = int(54 + 8 * math.sin(f / FRAMES * math.pi * 2))
        _text_center(d, (cx + 2, H / 2 + 3), spec["text"], _font(size), (0, 0, 0))
        _text_center(d, (cx, H / 2), spec["text"], _font(size), spec["fg"])
        frames.append(img)
    out = io.BytesIO()
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=70, loop=0, disposal=2)
    return out.getvalue()
