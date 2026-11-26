# -*- coding: utf-8 -*-
"""生成 PWA 图标（需 Pillow）：品牌蓝底 + 白色“武”字。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "看板"
OUT.mkdir(parents=True, exist_ok=True)
FONT = r"C:\Windows\Fonts\msyh.ttc"

TOP = (11, 61, 92)
BOTTOM = (29, 111, 156)


def make(size, radius_ratio=0.22, padding_ratio=0.0):
    img = Image.new("RGB", (size, size), TOP)
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(1, size - 1)
        c = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        d.line([(0, y), (size, y)], fill=c)

    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    r = int(size * radius_ratio)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    img.putalpha(mask)

    inner = int(size * (1 - padding_ratio * 2))
    font_size = int(inner * 0.62)
    font = ImageFont.truetype(FONT, font_size)
    bbox = d.textbbox((0, 0), "武", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), "武", font=font, fill=(255, 255, 255, 255))
    return img


make(180).save(OUT / "icon-180.png")
make(192).save(OUT / "icon-192.png")
make(512).save(OUT / "icon-512.png")
make(512, padding_ratio=0.1).save(OUT / "icon-maskable-512.png")
print("icons written to", OUT)
