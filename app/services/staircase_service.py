"""Zinapoya rasmini dinamik yaratish (Pillow): 10 ta ko‘rinadigan pog‘ona, joriy pog‘ona ajralib turadi."""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
W, H = 960, 540  # 16:9
STEPS = 10

# (yuqori fon, pastki fon, o‘tilgan pog‘ona, kelgusi pog‘ona, joriy pog‘ona)
THEMES = [
    ((12, 52, 70), (6, 20, 34), (38, 150, 150), (30, 62, 80), (255, 196, 64)),     # orol
    ((92, 56, 20), (38, 22, 10), (200, 140, 60), (80, 56, 34), (255, 220, 110)),   # cho‘l
    ((24, 28, 48), (8, 8, 18), (92, 110, 170), (36, 40, 64), (255, 170, 60)),      # detektiv
    ((8, 18, 60), (2, 4, 20), (40, 170, 220), (24, 36, 84), (255, 130, 50)),       # kosmos
]


@lru_cache(maxsize=8)
def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


def _gradient(top, bottom) -> Image.Image:
    img = Image.new("RGB", (W, H), top)
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def _text_center(draw: ImageDraw.ImageDraw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((xy[0] - w / 2 - bbox[0], xy[1] - h / 2 - bbox[1]), text, font=font, fill=fill)


def _star(draw, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def render_staircase(current: int, *, story_title: str = "", stage_title: str = "", theme: int = 0) -> bytes:
    """PNG baytlarini qaytaradi. current: 1..10."""
    current = max(1, min(STEPS, int(current)))
    top, bottom, passed, future, cur = THEMES[theme % len(THEMES)]
    img = _gradient(top, bottom).convert("RGBA")

    # yulduzchalar / zarralar (bezak)
    deco = ImageDraw.Draw(img)
    for i in range(45):
        x = (i * 211 + 37) % W
        y = (i * 97 + 13) % (H // 2)
        r = 1 + (i % 3)
        deco.ellipse([x, y, x + r, y + r], fill=(255, 255, 255, 60 + (i % 4) * 25))

    base_y, x0, step_w = 462, 56, 84
    heights = [60 + i * 31 for i in range(STEPS)]

    # joriy pog‘ona atrofida yorug‘lik (glow)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gx = x0 + (current - 1) * step_w + step_w // 2
    gy = base_y - heights[current - 1]
    ImageDraw.Draw(glow).ellipse([gx - 95, gy - 95, gx + 95, gy + 95], fill=cur + (150,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(28)))

    draw = ImageDraw.Draw(img)
    for i in range(STEPS):
        n = i + 1
        left = x0 + i * step_w
        right = left + step_w - 8
        topy = base_y - heights[i]
        if n == current:
            fill, outline, width = cur, (255, 255, 255), 5
        elif n < current:
            fill, outline, width = passed, (230, 240, 245), 2
        else:
            fill, outline, width = future, (110, 130, 150), 2
        draw.rounded_rectangle([left, topy, right, base_y], radius=10, fill=fill, outline=outline, width=width)
        num_color = (30, 20, 5) if n == current else ((255, 255, 255) if n < current else (170, 185, 200))
        _text_center(draw, ((left + right) / 2, topy + 30), str(n), _font(34 if n == current else 28), num_color)
    # yer chizig‘i
    draw.rectangle([0, base_y, W, H], fill=(0, 0, 0, 110))

    # jamoa belgisi (bayroqcha ko‘targan odamcha) joriy pog‘ona ustida
    cx = x0 + (current - 1) * step_w + (step_w - 8) // 2
    ty = base_y - heights[current - 1]
    draw.ellipse([cx - 11, ty - 62, cx + 11, ty - 40], fill=(255, 255, 255), outline=(20, 20, 20), width=2)
    draw.polygon([(cx - 15, ty - 4), (cx + 15, ty - 4), (cx + 8, ty - 40), (cx - 8, ty - 40)], fill=(255, 80, 80),
                 outline=(20, 20, 20))
    draw.line([(cx + 12, ty - 72), (cx + 12, ty - 28)], fill=(240, 240, 240), width=3)
    draw.polygon([(cx + 12, ty - 72), (cx + 38, ty - 62), (cx + 12, ty - 52)], fill=cur)
    if current == STEPS:
        _star(draw, cx, ty - 105, 22, (255, 230, 90))

    # sarlavhalar
    draw.text((36, 24), "SIRLI SAFAR", font=_font(42), fill=(255, 255, 255))
    if story_title:
        draw.text((38, 76), story_title[:46], font=_font(24, bold=False), fill=(215, 225, 235))
    label = f"{current}-ZINA  /  {STEPS}"
    _text_center(draw, (W / 2, H - 52), label, _font(34), cur)
    if stage_title:
        _text_center(draw, (W / 2, H - 20), stage_title[:60], _font(20, bold=False), (225, 232, 240))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def text_ladder(current: int) -> str:
    current = max(1, min(STEPS, int(current)))
    return "▰" * current + "▱" * (STEPS - current) + f"  {current}/{STEPS}"
