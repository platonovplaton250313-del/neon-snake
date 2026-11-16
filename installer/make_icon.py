# -*- coding: utf-8 -*-
"""Рисует неоновую иконку assets/neon_snake.ico без сторонних библиотек.

Иконка содержит размеры 16..256 px. Запуск: python installer/make_icon.py
"""

import math
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "neon_snake.ico")
SIZES = (16, 24, 32, 48, 64, 128, 256)

BG_TOP = (10, 8, 24)
BG_BOTTOM = (4, 4, 12)
GRID = (22, 44, 52)
BODY = (57, 255, 136)
BODY_DARK = (12, 120, 74)
APPLE = (255, 64, 120)
APPLE_DARK = (150, 12, 60)
LEAF = (80, 220, 120)
EYE = (6, 10, 18)

SNAKE = ((9.0, 46.0), (21.0, 46.0), (21.0, 33.0),
         (33.0, 33.0), (33.0, 46.0), (46.0, 46.0))
HEAD = (51.5, 46.0)
HEAD_R = 7.0
BODY_R = 5.4
GLOW_R = 10.0
APPLE_C = (51.5, 16.0)
APPLE_R = 6.2


def _mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return (a[0] + (b[0] - a[0]) * k,
            a[1] + (b[1] - a[1]) * k,
            a[2] + (b[2] - a[2]) * k)


def _dist_to_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length <= 1e-9:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


def _snake_distance(px, py):
    best = 1e9
    for ax, ay in zip(SNAKE, SNAKE[1:]):
        best = min(best, _dist_to_segment(px, py, ax[0], ay[0], ax[1], ay[1]))
    return best


def _blend(color, target, k):
    return _mix(color, target, k)


def _render_design(px, py):
    """px, py — координаты в сетке 64x64."""
    k = py / 64.0
    color = _mix(BG_TOP, BG_BOTTOM, k)

    # неоновая сетка
    step = 8.0
    if px % step < 0.55 or py % step < 0.55:
        color = _blend(color, GRID, 0.55)

    # яблоко
    d_apple = math.hypot(px - APPLE_C[0], py - APPLE_C[1])
    if d_apple < APPLE_R:
        shade = 0.35 + 0.65 * (1.0 - d_apple / APPLE_R)
        color = _mix(APPLE_DARK, APPLE, shade)
    elif d_apple < APPLE_R + 2.2:
        color = _blend(color, APPLE, 0.22 * (1.0 - (d_apple - APPLE_R) / 2.2))

    # листик
    lx, ly = px - (APPLE_C[0] + 1.2), py - (APPLE_C[1] - APPLE_R - 1.2)
    if (lx / 3.6) ** 2 + (ly / 1.7) ** 2 < 1.0:
        color = LEAF

    # змея + свечение
    d = _snake_distance(px, py)
    d_head = math.hypot(px - HEAD[0], py - HEAD[1])
    d_body = min(d, max(0.0, d_head - (HEAD_R - BODY_R)))

    if d_body < BODY_R:
        edge = d_body / BODY_R
        color = _mix(BODY, BODY_DARK, 0.55 * edge)
        # блик сверху
        if py < 44.0:
            color = _blend(color, (220, 255, 235), 0.25)
    elif d_body < GLOW_R:
        fade = 1.0 - (d_body - BODY_R) / (GLOW_R - BODY_R)
        color = _blend(color, BODY, 0.30 * fade * fade)

    # глаза
    for ex, ey in ((54.2, 44.2), (54.2, 48.0)):
        if math.hypot(px - ex, py - ey) < 1.35:
            color = EYE

    return color


def render(size):
    scale = size / 64.0
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            dx = (x + 0.5) / scale
            dy = (y + 0.5) / scale
            r, g, b = _render_design(dx, dy)
            row += bytes((int(b), int(g), int(r), 255))
        rows.append(bytes(row))
    return b"".join(reversed(rows))


def ico_bytes():
    images = []
    for size in SIZES:
        pixels = render(size)
        mask_row = ((size + 31) // 32) * 4
        mask = b"\x00" * (mask_row * size)
        header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32,
                             0, len(pixels) + len(mask), 0, 0, 0, 0)
        images.append((size, header + pixels + mask))

    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    for size, data in images:
        width = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32,
                           len(data), offset)
        offset += len(data)
    for _, data in images:
        out += data
    return bytes(out)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = ico_bytes()
    with open(OUT, "wb") as fh:
        fh.write(data)
    print("icon:", OUT, len(data), "bytes")


if __name__ == "__main__":
    main()
