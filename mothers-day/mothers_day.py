#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
«С Днём Матери!» — тёплая анимированная открытка на pygame.

Управление:
    ПРОБЕЛ / клик  — салют из сердечек
    S              — сохранить открытку в PNG
    F11            — полный экран
    Esc            — выход

Запуск:  python mothers_day.py
"""

from __future__ import annotations

import argparse
import math
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

# ----------------------------------------------------------------------------
# Общие настройки
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "assets" / "fonts"
WIDTH, HEIGHT = 1600, 1120      # внутреннее разрешение — как у печатной открытки
FPS = 120
HEART_ASPECT = 1.106376          # ширина / высота сердца из формулы
HEART_CY = 652                   # центр большого сердца
HEART_BASE_HEIGHT = 430
MAT_COLOR = (68, 28, 41)         # «паспарту» вокруг открытки в полный экран
POSTCARD_NAME = "mothers_day_otkrytka.png"

# Палитра: слоновая кость, пудровая роза и тёплое золото
BG_TOP = (255, 250, 244)
BG_BOTTOM = (247, 203, 209)
TITLE_TOP = (192, 92, 112)
TITLE_BOTTOM = (108, 30, 51)
TITLE_SHADOW = (121, 47, 67)
TITLE_SHADOW_LIGHT = (255, 244, 236)
TEXT_DARK = (112, 46, 63)
TEXT_SOFT = (146, 86, 101)
GOLD = (191, 150, 92)
GOLD_LIGHT = (232, 200, 138)
GOLD_DEEP = (146, 104, 52)
ROSE = (176, 68, 92)
ROSE_DEEP = (116, 32, 53)
BIG_TOP = (250, 116, 140)
BIG_BOTTOM = (164, 26, 56)
HEART_COLORS = [
    (240, 111, 142),
    (247, 157, 178),
    (255, 190, 202),
    (236, 139, 160),
    (246, 170, 148),
]
SPARK_COLORS = [
    (255, 251, 238),
    (255, 228, 187),
    (255, 215, 226),
    (247, 201, 132),
]
PETAL_COLORS = [
    (255, 222, 214),
    (250, 188, 202),
    (243, 168, 189),
    (255, 233, 220),
]
WASH_COLORS = [
    (255, 226, 214),
    (252, 210, 218),
    (255, 238, 222),
    (244, 198, 209),
    (247, 219, 206),
]
LEAF_COLORS = [(126, 144, 105), (108, 128, 90), (154, 164, 128)]


# ----------------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------------
def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp_color(c1, c2, k: float):
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c1, c2))


def sample_stops(stops, k: float):
    """Цвет по набору опорных точек (позиция, цвет)."""
    k = clamp(k, 0.0, 1.0)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= k <= p1:
            t = (k - p0) / max(1e-6, p1 - p0)
            return lerp_color(c0, c1, t)
    return stops[-1][1]


def gradient_surface(size, top, bottom, alpha: int = 255) -> pygame.Surface:
    """Вертикальный градиент."""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if h == 1:
        surf.fill((*top, alpha))
        return surf
    for y in range(h):
        color = lerp_color(top, bottom, y / (h - 1))
        pygame.draw.line(surf, (*color, alpha), (0, y), (w, y))
    return surf


def diagonal_gradient_surface(size, light, deep, alpha: int = 255) -> pygame.Surface:
    """Мягкий градиент по диагонали: свет сверху-слева, тень снизу-справа."""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    tw = max(8, min(128, w))
    th = max(8, min(128, h))
    small = pygame.Surface((tw, th), pygame.SRCALPHA)
    for y in range(th):
        fy = y / (th - 1)
        for x in range(tw):
            fx = x / (tw - 1)
            k = clamp(0.28 * fx + 0.72 * fy, 0.0, 1.0)
            small.set_at((x, y), (*lerp_color(light, deep, k), alpha))
    return pygame.transform.smoothscale(small, (w, h))


def multiply_alpha(surf: pygame.Surface, factor: float) -> pygame.Surface:
    """Аккуратно умножает альфу поверхности (не трогая RGB)."""
    factor = clamp(factor, 0.0, 1.0)
    if factor >= 0.999:
        return surf
    result = surf.copy()
    layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    layer.fill((255, 255, 255, int(255 * factor)))
    result.blit(layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return result


def blur_colored(layer: pygame.Surface, color, radius: float) -> pygame.Surface:
    """Размывает слой, сохраняя цвет в прозрачных пикселях (без серой каймы)."""
    canvas = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    canvas.fill((*color, 0))
    canvas.blit(layer, (0, 0))
    return soft_blur(canvas, radius)


def render_tracked(
    text: str,
    font: pygame.font.Font,
    color,
    tracking: int = 6,
    alpha: int = 255,
) -> pygame.Surface:
    """Текст с разрядкой между буквами — для золотой надписи-кикера."""
    space_w = font.size(" ")[0]
    glyphs = [font.render(ch, True, color) for ch in text]
    width = sum(g.get_width() if ch != " " else space_w
                for g, ch in zip(glyphs, text)) + tracking * max(0, len(text) - 1)
    height = font.get_height()
    surf = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
    x = 0
    for g, ch in zip(glyphs, text):
        if ch == " ":
            x += space_w
        else:
            surf.blit(g, (x, 0))
            x += g.get_width()
        x += tracking
    if alpha < 255:
        surf = multiply_alpha(surf, alpha / 255)
    return surf


def soft_blur(surf: pygame.Surface, radius: float) -> pygame.Surface:
    radius = max(0, int(round(radius)))
    if radius <= 0:
        return surf
    w, h = surf.get_size()
    # Большие поверхности размываем быстрым box blur (два прохода мягче).
    box_blur = getattr(pygame.transform, "box_blur", None)
    if box_blur is not None and w * h >= 150_000:
        r1 = max(1, int(radius * 0.62))
        r2 = max(1, radius - r1)
        out = box_blur(surf, r1)
        return box_blur(out, r2)
    blur = getattr(pygame.transform, "gaussian_blur", None)
    if blur is not None:
        return blur(surf, radius)
    if box_blur is not None:
        return box_blur(surf, radius)
    # Запасной вариант для классического pygame.
    factor = max(2, radius)
    small = pygame.transform.smoothscale(
        surf, (max(1, w // factor), max(1, h // factor))
    )
    return pygame.transform.smoothscale(small, (w, h))


def radial_sprite(radius: int, color, max_alpha: int) -> pygame.Surface:
    """Мягкий круглый свет с плавной альфой."""
    radius = max(2, int(radius))
    small = max(4, radius // 3)
    s = pygame.Surface((small * 2, small * 2), pygame.SRCALPHA)
    for r in range(small, 0, -1):
        k = r / small
        a = int(max_alpha * (1.0 - k) ** 1.8)
        if a:
            pygame.draw.circle(s, (*color, a), (small, small), r, 1)
    pygame.draw.circle(s, (*color, max_alpha), (small, small), 1)
    return pygame.transform.smoothscale(s, (radius * 2, radius * 2))


FONT_FILES = {
    "display": "PlayfairDisplay-Regular.ttf",
    "display_semibold": "PlayfairDisplay-SemiBold.ttf",
    "display_bold": "PlayfairDisplay-Bold.ttf",
    "body": "PT_Serif-Web-Regular.ttf",
    "body_bold": "PT_Serif-Web-Bold.ttf",
    "body_italic": "PT_Serif-Web-Italic.ttf",
    "script": "MarckScript-Regular.ttf",
}


@lru_cache(maxsize=96)
def load_font(kind: str, size: int) -> pygame.font.Font:
    """Загружает шрифт из assets/fonts, иначе — системный запасной."""
    path = FONT_DIR / FONT_FILES.get(kind, "")
    if path.is_file():
        try:
            return pygame.font.Font(str(path), size)
        except (OSError, pygame.error):
            pass

    fallback = {
        "display": ("georgia", "constantia", "palatinolinotype", "timesnewroman"),
        "display_semibold": ("georgia", "constantia", "palatinolinotype"),
        "display_bold": ("georgia", "constantia", "palatinolinotype"),
        "body": ("georgia", "constantia", "cambria", "timesnewroman"),
        "body_bold": ("georgia", "constantia", "cambria"),
        "body_italic": ("georgia", "constantia", "cambria"),
        "script": ("gabriola", "segoescript", "segoeui"),
    }.get(kind, ("georgia", "segoeui", "dejavuserif"))

    bold = kind in ("display_bold", "body_bold")
    italic = kind == "body_italic"
    for name in fallback:
        match = pygame.font.match_font(name, bold=bold, italic=italic)
        if match:
            try:
                return pygame.font.Font(match, size)
            except (OSError, pygame.error):
                pass
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    font.set_italic(italic)
    return font


def text_with_soft_shadow(
    text: str,
    font: pygame.font.Font,
    color,
    shadow_color=TITLE_SHADOW,
    shadow_alpha: int = 80,
    shadow_offset=(0, 4),
    shadow_blur: float = 2.5,
    alpha: int = 255,
) -> pygame.Surface:
    """Текст с мягкой тенью, возвращается поверхность с полями."""
    main = font.render(text, True, color)
    if alpha < 255:
        main = multiply_alpha(main, alpha / 255)
    w, h = main.get_size()
    pad = max(6, int(shadow_blur * 3))
    canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)

    shadow = font.render(text, True, shadow_color)
    shadow = multiply_alpha(shadow, shadow_alpha / 255)
    sh_canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    sh_canvas.blit(shadow, (pad, pad))
    if shadow_blur:
        sh_canvas = soft_blur(sh_canvas, shadow_blur)
    canvas.blit(sh_canvas, shadow_offset)
    canvas.blit(main, (pad, pad))
    return canvas


def gradient_text(
    text: str,
    font: pygame.font.Font,
    top,
    bottom,
    shadow_color=TITLE_SHADOW,
    shadow_alpha: int = 70,
    shadow_offset=(0, 5),
    shadow_blur: float = 4.0,
    light_halo: bool = True,
) -> pygame.Surface:
    """Текст с вертикальным градиентом и мягким свечением/тенью."""
    base = font.render(text, True, (255, 255, 255))
    w, h = base.get_size()
    mask = pygame.mask.from_surface(base)
    mask_surf = mask.to_surface(
        setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)
    )
    grad = gradient_surface((w, h), top, bottom)
    grad.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    pad = max(10, int(shadow_blur * 3))
    canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)

    if light_halo:
        halo = font.render(text, True, TITLE_SHADOW_LIGHT)
        halo = multiply_alpha(halo, 0.90)
        halo_canvas = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        halo_canvas.blit(halo, (pad, pad + 2))
        halo_canvas = soft_blur(halo_canvas, max(1.0, shadow_blur))
        canvas.blit(halo_canvas, (0, 0))

    shadow = font.render(text, True, shadow_color)
    shadow = multiply_alpha(shadow, shadow_alpha / 255)
    sh_canvas = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
    sh_canvas.blit(shadow, (pad, pad))
    if shadow_blur:
        sh_canvas = soft_blur(sh_canvas, shadow_blur)
    canvas.blit(sh_canvas, shadow_offset)
    canvas.blit(grad, (pad, pad))
    return canvas


def blit_center(target: pygame.Surface, surf: pygame.Surface, cx: float, cy: float) -> None:
    target.blit(
        surf,
        (round(cx - surf.get_width() / 2), round(cy - surf.get_height() / 2)),
    )


def heartbeat(t: float) -> float:
    """Двойной удар сердца, значение 0..1."""
    phase = (t * 0.92) % 1.0
    first = math.exp(-(((phase - 0.10) / 0.050) ** 2))
    second = 0.62 * math.exp(-(((phase - 0.27) / 0.062) ** 2))
    return clamp(first + second, 0.0, 1.0)


# ----------------------------------------------------------------------------
# Сердца и лепестки
# ----------------------------------------------------------------------------
def heart_points(width: int, height: int, n: int = 180, inset: float = 0.0):
    raw = []
    for i in range(n):
        t = math.tau * i / n
        x = 16.0 * math.sin(t) ** 3
        y = (
            13.0 * math.cos(t)
            - 5.0 * math.cos(2.0 * t)
            - 2.0 * math.cos(3.0 * t)
            - math.cos(4.0 * t)
        )
        raw.append((x, y))

    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x, span_y = max_x - min_x, max_y - min_y
    scale = min(
        (width - inset * 2.0) / span_x,
        (height - inset * 2.0) / span_y,
    )
    content_w, content_h = span_x * scale, span_y * scale
    ox = (width - content_w) / 2.0
    oy = (height - content_h) / 2.0
    return [
        (
            ox + (x - min_x) * scale,
            oy + (max_y - y) * scale,  # экранная ось Y направлена вниз
        )
        for x, y in raw
    ]


# Нормализованный контур большого сердца: полные доли, собранный низ и
# естественная точка вместо длинной иглы классической формулы.
_BIG_HEART_NOTCH = (0.500, 0.235)
_BIG_HEART_SEGMENTS = (
    ((0.555, 0.100), (0.670, 0.020), (0.800, 0.030)),
    ((0.940, 0.040), (1.000, 0.190), (0.995, 0.365)),
    ((0.990, 0.610), (0.860, 0.790), (0.670, 0.880)),
    ((0.590, 0.925), (0.535, 0.950), (0.515, 0.958)),
)
_BIG_HEART_TIP = ((0.505, 0.974), (0.500, 0.978))


def big_heart_points(width: int, height: int, inset: float = 0.0):
    """Гладкий симметричный силуэт большого сердца в пикселях."""
    def cubic(p0, p1, p2, p3, steps=56):
        out = []
        for i in range(1, steps + 1):
            t = i / steps
            mt = 1.0 - t
            out.append((
                mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
                + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
                + 3 * mt * t * t * p2[1] + t ** 3 * p3[1],
            ))
        return out

    def quad(p0, p1, p2, steps=20):
        out = []
        for i in range(1, steps + 1):
            t = i / steps
            mt = 1.0 - t
            out.append((
                mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
            ))
        return out

    right = [_BIG_HEART_NOTCH]
    for a, b, c in _BIG_HEART_SEGMENTS:
        right += cubic(right[-1], a, b, c)
    right += quad(right[-1], *_BIG_HEART_TIP)
    norm = right + [(1.0 - x, y) for x, y in reversed(right[:-1])]

    xs = [p[0] for p in norm]
    ys = [p[1] for p in norm]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x, span_y = max_x - min_x, max_y - min_y
    scale = min(
        (width - inset * 2.0) / span_x,
        (height - inset * 2.0) / span_y,
    )
    content_w, content_h = span_x * scale, span_y * scale
    ox = (width - content_w) / 2.0
    oy = (height - content_h) / 2.0
    return [
        (ox + (x - min_x) * scale, oy + (y - min_y) * scale) for x, y in norm
    ]


def heart_fill_surface(width: int, height: int, top, bottom) -> pygame.Surface:
    """Бархатистый объём: свет сверху-слева, глубокий тон снизу-справа."""
    tw = th = 200
    small = pygame.Surface((tw, th), pygame.SRCALPHA)
    light = lerp_color(top, (255, 244, 236), 0.28)
    deep = bottom
    darkest = lerp_color(bottom, (110, 14, 40), 0.45)
    for y in range(th):
        fy = y / (th - 1)
        for x in range(tw):
            fx = x / (tw - 1)
            k = clamp(0.34 * fx + 0.66 * fy, 0.0, 1.0)
            if k < 0.46:
                col = lerp_color(light, top, (k / 0.46) ** 0.82)
            elif k < 0.82:
                col = lerp_color(top, deep, ((k - 0.46) / 0.36) ** 1.05)
            else:
                col = lerp_color(deep, darkest, (k - 0.82) / 0.18)
            # широкий тёплый блик на верхней левой доле
            glow = math.exp(
                -(((fx - 0.28) ** 2) / 0.050 + ((fy - 0.22) ** 2) / 0.038)
            )
            col = lerp_color(col, (255, 212, 206), 0.22 * glow)
            # отсвет снизу-справа, чтобы тень не была «грязной»
            bounce = math.exp(
                -(((fx - 0.74) ** 2) / 0.045 + ((fy - 0.84) ** 2) / 0.035)
            )
            col = lerp_color(col, (240, 110, 116), 0.13 * bounce)
            small.set_at((x, y), (*col, 255))
    return pygame.transform.smoothscale(small, (width, height))


def shifted_band(mask_surf: pygame.Surface, dx: int, dy: int) -> pygame.Surface:
    """Полоса у края маски: остаток после сдвига копии."""
    w, h = mask_surf.get_size()
    shifted = pygame.Surface((w, h), pygame.SRCALPHA)
    shifted.blit(mask_surf, (dx, dy))
    band = pygame.Surface((w, h), pygame.SRCALPHA)
    band.blit(mask_surf, (0, 0))
    band.blit(shifted, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    return band


def colorize_mask(mask_surf: pygame.Surface, color) -> pygame.Surface:
    out = pygame.Surface(mask_surf.get_size(), pygame.SRCALPHA)
    out.fill((*color, 255))
    band = mask_surf.copy()
    white = pygame.Surface(band.get_size(), pygame.SRCALPHA)
    white.fill((255, 255, 255, 255))
    # BLEND_SUB обнуляет RGB полосы — возвращаем белый, сохраняя альфу.
    band.blit(white, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
    out.blit(band, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def add_gloss(fill: pygame.Surface, hi_w: int, hi_h: int, strength: float = 1.0) -> None:
    """Лаковый блик: широкая полоса по верхней левой доле и горячая точка."""
    gw, gh = max(36, hi_w // 5), max(36, hi_h // 5)
    layer = pygame.Surface((gw, gh), pygame.SRCALPHA)

    def sheen(cx, cy, ew, eh, alpha, radius, angle):
        pad = radius * 3 + 6
        sw = max(8, int(ew + pad * 2))
        sh = max(8, int(eh + pad * 2))
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        rect = pygame.Rect(pad, pad, max(3, int(ew)), max(3, int(eh)))
        pygame.draw.ellipse(
            surf, (255, 253, 248, clamp(int(alpha * strength), 0, 255)), rect
        )
        surf = soft_blur(surf, radius)
        surf = pygame.transform.rotate(surf, angle)
        layer.blit(surf, surf.get_rect(center=(int(cx), int(cy))))

    # большой мягкий отсвет, повторяющий наклон верхней доли
    sheen(gw * 0.32, gh * 0.255, gw * 0.36, gh * 0.120, 28, 7, -22)
    # узкая яркая полоса внутри
    sheen(gw * 0.290, gh * 0.222, gw * 0.25, gh * 0.048, 58, 4, -22)
    # слабый отсвет на правой доле
    sheen(gw * 0.685, gh * 0.300, gw * 0.13, gh * 0.035, 20, 4, -22)
    fill.blit(
        pygame.transform.smoothscale(layer, (hi_w, hi_h)),
        (0, 0),
    )


def draw_sparkle(
    surf: pygame.Surface, x: int, y: int, radius: int, alpha: int = 150
) -> None:
    """Тонкая четырёхлучевая звёздочка-блик."""
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for rr, aa in (
        (radius, int(alpha * 0.40)),
        (max(2, int(radius * 0.60)), int(alpha * 0.72)),
        (1, alpha),
    ):
        pygame.draw.line(overlay, (255, 255, 255, aa), (x - rr, y), (x + rr, y), 1)
        pygame.draw.line(overlay, (255, 255, 255, aa), (x, y - rr), (x, y + rr), 1)
    pygame.draw.circle(overlay, (255, 255, 255, min(255, alpha + 60)), (x, y), 1)
    surf.blit(overlay, (0, 0))


def heart_3d_surface(width: int, height: int, top, bottom) -> pygame.Surface:
    """Объёмное сердце: поле высот из силуэта, мягкий свет и бархатистый блик."""
    lw = 300
    lh = max(60, round(lw / HEART_ASPECT))
    shape = pygame.Surface((lw, lh), pygame.SRCALPHA)
    pts = heart_points(lw, lh, n=240, inset=1.0)
    pygame.draw.polygon(shape, (255, 255, 255, 255), pts)

    blurred = soft_blur(shape.copy(), 26)
    field = [[0.0] * lw for _ in range(lh)]
    for y in range(lh):
        row = field[y]
        for x in range(lw):
            a = blurred.get_at((x, y))[3] / 255.0
            row[x] = clamp((a - 0.5) * 2.0, 0.0, 1.0) ** 0.55

    for _ in range(2):
        nxt = [[0.0] * lw for _ in range(lh)]
        for y in range(lh):
            row = field[y]
            up = field[y - 1] if y else row
            dn = field[y + 1] if y + 1 < lh else row
            dest = nxt[y]
            for x in range(lw):
                xm = x - 1 if x else x
                xp = x + 1 if x + 1 < lw else x
                dest[x] = (
                    up[xm] + up[x] + up[xp]
                    + row[xm] + row[x] + row[xp]
                    + dn[xm] + dn[x] + dn[xp]
                ) / 9.0
        field = nxt

    light = (-0.66, -0.42, 0.60)
    ln = math.sqrt(sum(c * c for c in light))
    lx, ly, lz = (c / ln for c in light)
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx / hn, hy / hn, hz / hn

    warm = (255, 236, 226)
    out = pygame.Surface((lw, lh), pygame.SRCALPHA)
    strength = 5.0

    for y in range(lh):
        fy = y / (lh - 1)
        base_y = lerp_color(top, bottom, clamp(fy ** 1.10, 0.0, 1.0))
        row = field[y]
        up = field[y - 1] if y else row
        dn = field[y + 1] if y + 1 < lh else row
        for x in range(lw):
            fx = x / (lw - 1)
            base = lerp_color(base_y, warm, 0.14 * (1.0 - fx) * (1.0 - fy))
            xm = x - 1 if x else x
            xp = x + 1 if x + 1 < lw else x
            dx = (row[xp] - row[xm]) * 0.5 * strength
            dy = (dn[x] - up[x]) * 0.5 * strength
            nx, ny, nz = -dx, -dy, 1.0
            nn = math.sqrt(nx * nx + ny * ny + nz * nz)
            nx, ny, nz = nx / nn, ny / nn, nz / nn
            diff = max(0.0, nx * lx + ny * ly + nz * lz)
            shade = 0.47 + 0.55 * diff
            col = tuple(min(255, int(c * shade)) for c in base)
            spec = max(0.0, nx * hx + ny * hy + nz * hz) ** 16
            spec *= clamp((row[x] - 0.08) / 0.30, 0.0, 1.0)
            if spec > 0.002:
                amount = int(82 * spec)
                col = (
                    min(255, col[0] + amount),
                    min(255, col[1] + int(amount * 0.96)),
                    min(255, col[2] + int(amount * 0.90)),
                )
            # тёплый отсвет от бумаги снизу
            bounce = (1.0 - nz) ** 2 * max(0.0, ny) * 62
            if bounce > 1.0:
                col = (
                    min(255, col[0] + int(bounce)),
                    min(255, col[1] + int(bounce * 0.42)),
                    min(255, col[2] + int(bounce * 0.36)),
                )
            out.set_at((x, y), (*col, 255))

    return pygame.transform.smoothscale(out, (width, height))


def heart_satin_surface(width: int, height: int, top, bottom) -> pygame.Surface:
    """Большое сердце: гладкий силуэт с естественной точкой, сатиновый свет."""
    ss = 3
    hi_w, hi_h = width * ss, height * ss
    pts = big_heart_points(hi_w, hi_h, inset=1.4 * ss)
    shape = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
    pygame.draw.polygon(shape, (255, 255, 255, 255), pts)
    # сглаживаем стык долей и слегка округляем точку
    softened = soft_blur(shape.copy(), max(2, round(width * ss * 0.004)))
    shape = pygame.mask.from_surface(softened, 127).to_surface(
        setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)
    )

    res = min(620, max(360, round(width * 1.22)))
    res_h = max(40, round(res * height / width))
    small = pygame.transform.smoothscale(shape, (res, res_h))
    blurred = soft_blur(small.copy(), max(4, round(res * 0.15)))
    field = [[0.0] * res for _ in range(res_h)]
    for y in range(res_h):
        row = field[y]
        for x in range(res):
            a = blurred.get_at((x, y))[3] / 255.0
            row[x] = clamp((a - 0.14) / 0.76, 0.0, 1.0) ** 0.72

    # один проход 3x3 — убираем ступеньки smoothscale
    nxt = [[0.0] * res for _ in range(res_h)]
    for y in range(res_h):
        row = field[y]
        up = field[y - 1] if y else row
        dn = field[y + 1] if y + 1 < res_h else row
        dest = nxt[y]
        for x in range(res):
            xm = x - 1 if x else x
            xp = x + 1 if x + 1 < res else x
            dest[x] = (
                up[xm] + 2 * up[x] + up[xp]
                + 2 * row[xm] + 4 * row[x] + 2 * row[xp]
                + dn[xm] + 2 * dn[x] + dn[xp]
            ) / 16.0
    field = nxt

    lx, ly, lz = -0.60, -0.46, 0.66
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx / hn, hy / hn, hz / hn

    warm = (255, 236, 224)
    out = pygame.Surface((res, res_h), pygame.SRCALPHA)

    def noise(x: int, y: int) -> float:
        value = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
        value = (value ^ (value >> 16)) & 1023
        return value / 511.5 - 1.0

    for y in range(res_h):
        fy = y / (res_h - 1)
        base_y = lerp_color(top, bottom, clamp(fy ** 1.04, 0.0, 1.0))
        row = field[y]
        up = field[y - 1] if y else row
        dn = field[y + 1] if y + 1 < res_h else row
        for x in range(res):
            fx = x / (res - 1)
            base = lerp_color(
                base_y, warm, 0.11 * (1.0 - fx) * (1.0 - fy)
            )
            xm = x - 1 if x else x
            xp = x + 1 if x + 1 < res else x
            dx = (row[xp] - row[xm]) * 0.5 * 4.5
            dy = (dn[x] - up[x]) * 0.5 * 4.5
            nx, ny, nz = -dx, -dy, 1.0
            nn = math.sqrt(nx * nx + ny * ny + nz * nz)
            nx, ny, nz = nx / nn, ny / nn, nz / nn
            diff = max(0.0, nx * lx + ny * ly + nz * lz)
            shade = 0.40 + 0.65 * diff
            col = tuple(min(255, int(c * shade)) for c in base)

            ndoth = max(0.0, nx * hx + ny * hy + nz * hz)
            spec = ndoth ** 11 * clamp((row[x] - 0.02) / 0.30, 0.0, 1.0)
            spec2 = ndoth ** 30 * clamp((row[x] - 0.16) / 0.34, 0.0, 1.0)
            amount = int(40 * spec + 18 * spec2)
            if amount:
                col = (
                    min(255, col[0] + amount),
                    min(255, col[1] + int(amount * 0.94)),
                    min(255, col[2] + int(amount * 0.86)),
                )

            rim = (1.0 - nz) ** 3 * max(0.0, -(nx * 0.70 + ny * 0.70)) * 82
            if rim > 1.0:
                col = (
                    min(255, col[0] + int(rim)),
                    min(255, col[1] + int(rim * 0.58)),
                    min(255, col[2] + int(rim * 0.44)),
                )
            bounce = (1.0 - nz) ** 2 * max(0.0, ny) * 36
            if bounce > 1.0:
                col = (
                    min(255, col[0] + int(bounce)),
                    min(255, col[1] + int(bounce * 0.28)),
                    min(255, col[2] + int(bounce * 0.22)),
                )

            n = noise(x, y)
            col = (
                clamp(int(col[0] + n * 1.4), 0, 255),
                clamp(int(col[1] + n * 1.4), 0, 255),
                clamp(int(col[2] + n * 1.4), 0, 255),
            )
            out.set_at((x, y), (*col, 255))

    cropped = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
    cropped.blit(pygame.transform.smoothscale(out, (hi_w, hi_h)), (0, 0))
    cropped.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    clean_rgb = cropped.copy()
    cropped.blit(clean_rgb, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
    return pygame.transform.smoothscale(cropped, (width, height))


def painterly_heart_surface(width: int, height: int, top, bottom) -> pygame.Surface:
    """Сатиновый объём + деликатная акварельная фактура + золотой контур."""
    base = heart_satin_surface(width, height, top, bottom)
    rng = random.Random(11)

    tw, th = 220, max(40, round(220 * height / width))
    tex = pygame.Surface((tw, th), pygame.SRCALPHA)
    tex.fill((249, 249, 249, 255))
    for _ in range(20):
        cx = rng.uniform(0.05, 0.95) * tw
        cy = rng.uniform(0.05, 0.95) * th
        rx = rng.uniform(0.10, 0.30) * tw
        ry = rx * rng.uniform(0.65, 1.35)
        v = rng.randint(226, 255)
        pygame.draw.ellipse(
            tex, (v, v - 2, v - 4, rng.randint(16, 38)),
            pygame.Rect(
                round(cx - rx), round(cy - ry),
                max(2, round(rx * 2)), max(2, round(ry * 2)),
            ),
        )
    tex = soft_blur(tex, 7)
    nw, nh = 72, max(24, round(72 * height / width))
    noise = pygame.Surface((nw, nh), pygame.SRCALPHA)
    for y in range(nh):
        for x in range(nw):
            v = rng.randint(240, 255)
            noise.set_at((x, y), (v, v, v, 255))
    tex.blit(
        pygame.transform.smoothscale(noise, (tw, th)), (0, 0),
        special_flags=pygame.BLEND_RGB_MULT,
    )
    tex = pygame.transform.smoothscale(tex, (width, height))
    out = base.copy()
    out.blit(tex, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    # цветные лессировки, обрезанные по силуэту
    tint = pygame.Surface((tw, th), pygame.SRCALPHA)
    for _ in range(14):
        cx = rng.uniform(0.05, 0.95) * tw
        cy = rng.uniform(0.05, 0.95) * th
        rx = rng.uniform(0.10, 0.32) * tw
        ry = rx * rng.uniform(0.6, 1.3)
        col = rng.choice(((232, 148, 160), (255, 218, 198), (196, 70, 98)))
        pygame.draw.ellipse(
            tint, (*col, rng.randint(8, 20)),
            pygame.Rect(
                round(cx - rx), round(cy - ry),
                max(2, round(rx * 2)), max(2, round(ry * 2)),
            ),
        )
    tint = soft_blur(tint, 8)
    tint = pygame.transform.smoothscale(tint, (width, height))
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(
        mask, (255, 255, 255, 255),
        big_heart_points(width, height, inset=1.2),
    )
    mask = soft_blur(mask, 1)
    tint.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(tint, (0, 0))

    gold = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.lines(
        gold, (206, 164, 100, 170), True,
        big_heart_points(width, height, inset=1.0), 2,
    )
    out.blit(gold, (0, 0))

    # мягкий внутренний контур глубины: читается как объём, а не плоский мокрый пятно
    inner = pygame.Surface((width, height), pygame.SRCALPHA)
    inner.fill((118, 26, 44, 52))
    mask2 = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(
        mask2, (255, 255, 255, 255),
        big_heart_points(width, height, inset=1.0),
    )
    mask2 = soft_blur(mask2, 2)
    inner.blit(mask2, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(inner, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def make_heart(
    height: int,
    color,
    bottom_color=None,
    alpha: int = 255,
    sheen: bool = False,
    depth: bool = False,
) -> pygame.Surface:
    """Глянцевое объёмное сердце с кантом, внутренней тенью и бликами."""
    height = max(6, int(round(height)))
    width = max(6, int(round(height * HEART_ASPECT)))

    top = tuple(color)
    bottom = tuple(bottom_color) if bottom_color else top

    if depth and height >= 160:
        out = painterly_heart_surface(width, height, top, bottom)
        if alpha < 255:
            out = multiply_alpha(out, alpha / 255)
        return out

    ss = 2 if height >= 120 else (3 if height >= 34 else 4)
    hi_w, hi_h = width * ss, height * ss
    base = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
    n = 260 if hi_w > 420 else (120 if hi_w > 100 else 64)
    pts = heart_points(hi_w, hi_h, n=n, inset=1.4 * ss)
    pygame.draw.polygon(base, (255, 255, 255, 255), pts)
    mask_surf = pygame.mask.from_surface(base).to_surface(
        setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)
    )

    if height >= 50:
        fill = diagonal_gradient_surface((hi_w, hi_h), top, bottom)
    else:
        fill = gradient_surface((hi_w, hi_h), top, bottom)
    if sheen:
        add_gloss(fill, hi_w, hi_h, strength=0.9)

    # Запоминаем цвет до обрезки: иначе прозрачные пиксели станут чёрными
    # и smoothscale нарисует тёмную кайму вокруг сердца.
    fill_rgb = fill.copy()
    fill.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    fill.blit(fill_rgb, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
    out = pygame.transform.smoothscale(fill, (width, height))

    if alpha < 255:
        out = multiply_alpha(out, alpha / 255)
    return out


def make_heart_glow(
    height: int,
    color,
    alpha: int = 150,
    blur_radius: float = 30.0,
) -> pygame.Surface:
    """Мягкое свечение/тень по силуэту сердца (считается в низком разрешении)."""
    final_w = round(height * HEART_ASPECT) + int(blur_radius * 4)
    final_h = height + int(blur_radius * 4)
    proxy_h = 220
    k = proxy_h / max(1, height)
    proxy_blur = max(2, int(blur_radius * k))
    base_w = max(6, round(proxy_h * HEART_ASPECT))
    base = pygame.Surface((base_w, proxy_h), pygame.SRCALPHA)
    pygame.draw.polygon(
        base,
        (*color, 255),
        big_heart_points(base_w, proxy_h, inset=1.4),
    )
    pad = proxy_blur * 2
    canvas = pygame.Surface(
        (base.get_width() + pad * 2, base.get_height() + pad * 2), pygame.SRCALPHA
    )
    canvas.fill((*color, 0))
    canvas.blit(base, (pad, pad))
    blurred = soft_blur(canvas, proxy_blur)

    white = pygame.Surface(blurred.get_size(), pygame.SRCALPHA)
    white.fill((255, 255, 255, 255))
    blurred.blit(white, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
    out = pygame.Surface(blurred.get_size(), pygame.SRCALPHA)
    out.fill((*color, 255))
    out.blit(blurred, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out = multiply_alpha(out, alpha / 255)
    return pygame.transform.smoothscale(out, (final_w, final_h))


class HeartArt:
    def __init__(self):
        self.cache: dict = {}
        self.glow_cache: dict = {}

    def get(
        self,
        height: int,
        color,
        bottom_color=None,
        alpha: int = 255,
        sheen: bool = False,
        depth: bool = False,
    ) -> pygame.Surface:
        height = max(6, int(round(height)))
        color = tuple(color)
        bottom_color = tuple(bottom_color) if bottom_color else color
        alpha = clamp(int(alpha), 0, 255)
        key = (height, color, bottom_color, alpha, sheen, depth)
        surf = self.cache.get(key)
        if surf is None:
            surf = make_heart(height, color, bottom_color, alpha, sheen, depth)
            self.cache[key] = surf
        return surf

    def get_glow(
        self,
        height: int,
        color,
        alpha: int = 150,
        blur_radius: float = 20.0,
    ) -> pygame.Surface:
        height = max(6, int(round(height)))
        key = (height, tuple(color), int(alpha), round(float(blur_radius), 1))
        surf = self.glow_cache.get(key)
        if surf is None:
            surf = make_heart_glow(height, color, alpha, blur_radius)
            self.glow_cache[key] = surf
        return surf


def make_petal(size: int, color, alpha: int) -> pygame.Surface:
    size = max(5, int(size))
    ss = 4
    w, h = size * ss, int(size * 0.66 * ss)
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(base, (*color, alpha), (0, 0, w - 1, h - 1))
    sheen = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(
        sheen,
        (255, 255, 255, min(110, alpha // 2)),
        (w * 0.16, h * 0.12, w * 0.46, h * 0.40),
    )
    base.blit(sheen, (0, 0))
    return pygame.transform.smoothscale(base, (size, max(3, int(size * 0.66))))


class PetalArt:
    def __init__(self):
        self.bases: dict = {}
        self.rotated: dict = {}

    def get(self, size: int, color, alpha: int, angle: float) -> pygame.Surface:
        size = max(5, int(round(size)))
        color = tuple(color)
        alpha = clamp(int(alpha // 12) * 12, 0, 255)
        angle_key = int(round(angle / 8.0)) * 8 % 360
        base_key = (size, color, alpha)
        base = self.bases.get(base_key)
        if base is None:
            base = make_petal(size, color, alpha)
            self.bases[base_key] = base
        key = (base_key, angle_key)
        surf = self.rotated.get(key)
        if surf is None:
            surf = pygame.transform.rotate(base, angle_key)
            self.rotated[key] = surf
        return surf


# ----------------------------------------------------------------------------
# Акварельная ботаника и золотые орнаменты
# ----------------------------------------------------------------------------
BLOOM_TONES = {
    "rose": ((252, 202, 204), (231, 138, 158), (164, 60, 88), (255, 245, 235)),
    "peach": ((255, 218, 196), (240, 156, 128), (184, 92, 78), (255, 246, 234)),
}


def quad_bezier(p0, p1, p2, steps: int = 32):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        pts.append((
            mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
            mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
        ))
    return pts


def make_leaf(
    length: float,
    width: float,
    angle: float,
    fill,
    alpha: int = 100,
    vein=None,
) -> pygame.Surface:
    """Заострённый акварельный листик."""
    ss = 2
    L = max(8, int(round(length * ss)))
    Wd = max(4, int(round(width * ss)))
    pad = 3
    surf = pygame.Surface((L + pad * 2, Wd + pad * 2), pygame.SRCALPHA)
    pts = []
    n = 18
    for i in range(n + 1):
        u = -1.0 + 2.0 * i / n
        ww = (Wd / 2.0) * max(0.0, 1.0 - u * u) ** 0.62
        pts.append((pad + (u + 1.0) * 0.5 * L, pad + Wd / 2.0 - ww))
    for i in range(n, -1, -1):
        u = -1.0 + 2.0 * i / n
        ww = (Wd / 2.0) * max(0.0, 1.0 - u * u) ** 0.62
        pts.append((pad + (u + 1.0) * 0.5 * L, pad + Wd / 2.0 + ww))
    pygame.draw.polygon(surf, (*fill, alpha), pts)
    if vein:
        pygame.draw.line(
            surf,
            (*vein, min(255, alpha + 35)),
            (pad + 2, pad + Wd // 2),
            (pad + L - 2, pad + Wd // 2),
            max(1, ss // 2),
        )
    out = pygame.transform.smoothscale(
        surf, ((L + pad * 2) // ss, (Wd + pad * 2) // ss)
    )
    return pygame.transform.rotate(out, angle)


def make_blossom(radius: float, tone: str = "rose", rng=None) -> pygame.Surface:
    """Полупрозрачный акварельный цветок из нескольких слоёв лепестков."""
    rng = rng or random.Random(11)
    light, mid, deep, cream = BLOOM_TONES.get(tone, BLOOM_TONES["rose"])
    ss = 2
    R = int(radius * ss)
    pad = int(R * 0.35)
    total = R * 2 + pad * 2
    surf = pygame.Surface((total, total), pygame.SRCALPHA)
    cx = cy = total // 2
    layers = (
        (8, 0.48, 0.98, 0.54, 78, light),
        (6, 0.30, 0.74, 0.42, 96, mid),
        (5, 0.15, 0.50, 0.30, 114, mid),
        (3, 0.06, 0.26, 0.19, 130, deep),
    )
    for layer_idx, (count, dist, pw, ph, alpha, col) in enumerate(layers):
        for i in range(count):
            ang = (
                math.tau * i / count
                + layer_idx * 0.62
                + rng.uniform(-0.09, 0.09)
            )
            jitter = rng.uniform(0.88, 1.12)
            petal = pygame.Surface(
                (
                    max(4, int(R * pw * 2 * jitter)),
                    max(4, int(R * ph * 2 * jitter)),
                ),
                pygame.SRCALPHA,
            )
            rect = petal.get_rect().inflate(-4, -4)
            pygame.draw.ellipse(petal, (*col, alpha), rect)
            # тень у основания лепестка
            shade_rect = rect.inflate(-int(rect.w * 0.18), -int(rect.h * 0.40))
            shade_rect.move_ip(0, int(rect.h * 0.20))
            pygame.draw.ellipse(
                petal, (*deep, max(12, alpha // 2)), shade_rect
            )
            # светлая кромка
            hl = pygame.Rect(
                rect.x + int(rect.w * 0.14),
                rect.y + int(rect.h * 0.08),
                int(rect.w * 0.50),
                int(rect.h * 0.28),
            )
            pygame.draw.ellipse(petal, (*cream, max(12, alpha // 3)), hl)
            petal = pygame.transform.rotate(petal, -math.degrees(ang))
            px = cx + math.cos(ang) * R * dist
            py = cy + math.sin(ang) * R * dist
            surf.blit(petal, petal.get_rect(center=(px, py)))

    rr = max(4, int(R * 0.18))
    pygame.draw.circle(surf, (*deep, 190), (cx, cy), rr)
    pygame.draw.circle(surf, (*deep, 220), (cx, cy), max(1, int(rr * 0.55)))
    for i in range(9):
        a = math.tau * i / 9 + 0.3
        pygame.draw.circle(
            surf,
            (*deep, 215),
            (int(cx + math.cos(a) * rr * 0.85), int(cy + math.sin(a) * rr * 0.85)),
            max(1, ss),
        )
        pygame.draw.circle(
            surf,
            (*GOLD_DEEP, 150),
            (int(cx + math.cos(a + 0.35) * rr * 0.35),
             int(cy + math.sin(a + 0.35) * rr * 0.35)),
            max(1, ss // 2),
        )
    surf = soft_blur(surf, 1)
    return pygame.transform.smoothscale(surf, (total // ss, total // ss))


def draw_gold_sprig(surf, start, ctrl, end, rng: random.Random, alpha=120) -> None:
    pts = quad_bezier(start, ctrl, end, 36)
    pygame.draw.lines(surf, (*GOLD, alpha), False, pts, 2)
    for j, t in enumerate((0.22, 0.38, 0.55, 0.72, 0.87)):
        x, y = pts[min(len(pts) - 1, int(t * (len(pts) - 1)))]
        x2, y2 = pts[min(len(pts) - 1, int(t * (len(pts) - 1)) + 4)]
        ang = math.degrees(math.atan2(y2 - y, x2 - x))
        side = -1 if j % 2 else 1
        leaf = make_leaf(24, 8, ang + side * 52, GOLD_LIGHT, alpha - 15)
        surf.blit(leaf, leaf.get_rect(center=(x, y)))
    pygame.draw.circle(surf, (*GOLD_LIGHT, alpha), (int(end[0]), int(end[1])), 3)


def make_bouquet(tone: str = "rose", seed: int = 101) -> pygame.Surface:
    """Небольшой акварельный букет для угла открытки."""
    rng = random.Random(seed)
    w, h = 660, 520
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((255, 255, 255, 0))
    root = (335, 545)
    flowers = ((182, 286, 96), (366, 206, 72), (486, 336, 54), (272, 404, 27))

    for fx, fy, fr in flowers:
        ctrl = (
            (fx + root[0]) // 2 + rng.randint(-55, 55),
            (fy + root[1]) // 2 + rng.randint(-15, 35),
        )
        pts = quad_bezier(root, ctrl, (fx, fy), 38)
        pygame.draw.lines(surf, (128, 146, 110, 92), False, pts, 4)
        pygame.draw.lines(surf, (180, 190, 152, 65), False, pts, 1)
        for j, t in enumerate((0.28, 0.48, 0.70)):
            idx = min(len(pts) - 1, int(t * (len(pts) - 1)))
            x, y = pts[idx]
            x2, y2 = pts[min(len(pts) - 1, idx + 4)]
            ang = math.degrees(math.atan2(y2 - y, x2 - x))
            side = -1 if j % 2 else 1
            leaf = make_leaf(
                rng.uniform(44, 62),
                rng.uniform(16, 23),
                ang + side * rng.uniform(48, 68),
                rng.choice(LEAF_COLORS),
                rng.randint(92, 136),
                vein=(96, 112, 84),
            )
            surf.blit(leaf, leaf.get_rect(center=(x, y)))

    draw_gold_sprig(surf, (330, 520), (500, 430), (610, 292), rng, 110)
    draw_gold_sprig(surf, (320, 520), (160, 400), (92, 286), rng, 100)
    draw_gold_sprig(surf, (340, 510), (420, 300), (372, 128), rng, 120)

    for fx, fy, fr in flowers:
        bloom = make_blossom(fr, tone, rng)
        surf.blit(bloom, bloom.get_rect(center=(fx, fy)))

    # пара свободных лепестков и золотые точки
    for _ in range(9):
        px = rng.randint(60, 590)
        py = rng.randint(270, 490)
        petal = pygame.Surface((18, 11), pygame.SRCALPHA)
        pygame.draw.ellipse(petal, (252, 205, 208, 90), petal.get_rect())
        surf.blit(pygame.transform.rotate(petal, rng.randint(0, 180)), (px, py))
    for _ in range(12):
        pygame.draw.circle(
            surf,
            (*GOLD_LIGHT, rng.randint(50, 100)),
            (rng.randint(40, 620), rng.randint(120, 500)),
            rng.choice((1, 1, 2)),
        )
    return surf


def make_gold_flourish(size: int = 250) -> pygame.Surface:
    """Угловой золотой завиток с листьями (рисуется в 2x и уменьшается)."""
    ss = 2
    s = size * ss
    surf = pygame.Surface((s, s), pygame.SRCALPHA)

    main = quad_bezier((0.06 * s, 0.94 * s), (0.20 * s, 0.44 * s), (0.94 * s, 0.06 * s), 90)
    pygame.draw.lines(surf, (*GOLD, 150), False, main, 2 * ss)
    inner = quad_bezier((0.10 * s, 0.84 * s), (0.26 * s, 0.42 * s), (0.84 * s, 0.10 * s), 90)
    pygame.draw.lines(surf, (*GOLD_LIGHT, 80), False, inner, max(1, ss))

    for j, t in enumerate((0.16, 0.30, 0.44, 0.58, 0.72, 0.85)):
        idx = min(len(main) - 2, int(t * (len(main) - 1)))
        x, y = main[idx]
        x2, y2 = main[idx + 2]
        ang = math.degrees(math.atan2(y2 - y, x2 - x))
        side = -1 if j % 2 else 1
        leaf = make_leaf(24 * ss, 8 * ss, ang + side * 58, GOLD, 150)
        surf.blit(leaf, leaf.get_rect(center=(x + side * 5 * ss, y - 2 * ss)))

    for cx, cy, r in ((0.06 * s, 0.94 * s, 12 * ss), (0.94 * s, 0.06 * s, 10 * ss)):
        pygame.draw.circle(surf, (*GOLD, 130), (int(cx), int(cy)), int(r), max(1, ss))
    for _ in range(7):
        pygame.draw.circle(
            surf,
            (*GOLD_LIGHT, 130),
            (int(0.18 * s + random.random() * 0.5 * s),
             int(0.18 * s + random.random() * 0.5 * s)),
            2 * ss,
        )
    return pygame.transform.smoothscale(surf, (size, size))


# ----------------------------------------------------------------------------
# Частицы
# ----------------------------------------------------------------------------
@dataclass
class HeartParticle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: tuple
    life: float
    max_life: float
    phase: float = 0.0

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.vy += 380.0 * dt
        self.vx *= 1.0 - 0.45 * dt
        self.vy *= 1.0 - 0.08 * dt
        age = self.max_life - self.life
        self.x += (self.vx + math.sin(self.phase + age * 5.0) * 15.0) * dt
        self.y += self.vy * dt
        return self.life > 0.0 and self.y < HEIGHT + 80

    def draw(self, target: pygame.Surface, art: HeartArt) -> None:
        fade = clamp(self.life / max(0.001, self.max_life), 0.0, 1.0)
        alpha = int(255 * min(1.0, fade * 1.65))
        if alpha < 6:
            return
        size = max(8, int(round(self.size * (0.55 + 0.45 * fade) / 2.0)) * 2)
        alpha = max(6, min(255, (alpha // 16) * 16))
        surf = art.get(size, self.color, alpha=alpha)
        target.blit(surf, surf.get_rect(center=(round(self.x), round(self.y))))


@dataclass
class SparkParticle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: tuple
    life: float
    max_life: float
    kind: str = "star"

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.vy += 320.0 * dt
        self.vx *= 1.0 - 0.55 * dt
        self.vy *= 1.0 - 0.16 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0.0 and self.y < HEIGHT + 40

    def draw(self, layer: pygame.Surface) -> None:
        fade = clamp(self.life / max(0.001, self.max_life), 0.0, 1.0)
        alpha = int(230 * fade)
        if alpha < 4:
            return
        x, y = int(self.x), int(self.y)
        if self.kind == "dot":
            pygame.draw.circle(layer, (*self.color, alpha), (x, y),
                               max(1, int(self.size * fade)))
            return
        r = self.size * (0.35 + 0.65 * fade)
        arm_x = max(1, int(r))
        arm_y = max(1, int(r * 0.62))
        pygame.draw.line(layer, (*self.color, alpha), (x - arm_x, y), (x + arm_x, y), 1)
        pygame.draw.line(layer, (*self.color, alpha), (x, y - arm_y), (x, y + arm_y), 1)
        if self.size > 3.0:
            pygame.draw.circle(layer, (*self.color, min(255, alpha + 20)), (x, y), 1)


@dataclass
class Ripple:
    x: float
    y: float
    life: float
    max_life: float
    radius: float
    color: tuple

    def draw(self, layer: pygame.Surface) -> None:
        p = 1.0 - clamp(self.life / max(0.001, self.max_life), 0.0, 1.0)
        alpha = int(105 * (1.0 - p) ** 2)
        if alpha < 3:
            return
        r = max(2, int(self.radius * (0.18 + 0.82 * p)))
        pygame.draw.circle(
            layer,
            (*self.color, alpha),
            (int(self.x), int(self.y)),
            r,
            max(1, int(2.5 * (1.0 - p))),
        )


@dataclass
class Flash:
    x: float
    y: float
    life: float
    max_life: float
    radius: float
    color: tuple

    def draw(self, layer: pygame.Surface) -> None:
        fade = clamp(self.life / max(0.001, self.max_life), 0.0, 1.0)
        if fade <= 0.0:
            return
        for i in range(7, 0, -1):
            k = i / 7.0
            r = max(2, int(self.radius * k * (0.55 + 0.45 * fade)))
            a = int(8 * fade * (1.0 - k * 0.45))
            if a:
                pygame.draw.circle(layer, (*self.color, a), (int(self.x), int(self.y)), r)


@dataclass
class FloatingHeart:
    x: float
    y: float
    height: int
    color: tuple
    alpha: int
    speed: float
    phase: float

    def reset(self, rng: random.Random, initial: bool = False) -> None:
        if rng.random() < 0.5:
            self.x = rng.uniform(46, 330)
        else:
            self.x = rng.uniform(WIDTH - 330, WIDTH - 46)
        self.y = rng.uniform(-20, HEIGHT) if initial else HEIGHT + rng.uniform(30, 120)
        self.height = rng.randint(20, 36)
        self.color = rng.choice(HEART_COLORS)
        self.alpha = rng.randint(48, 82)
        self.speed = rng.uniform(16, 32)
        self.phase = rng.uniform(0, math.tau)


@dataclass
class Petal:
    x: float
    y: float
    size: int
    color: tuple
    alpha: int
    speed: float
    sway: float
    sway_speed: float
    phase: float
    angle: float
    spin: float
    front: bool

    def reset(self, rng: random.Random, initial: bool = False) -> None:
        self.x = rng.uniform(-20, WIDTH + 20)
        self.y = rng.uniform(-30, HEIGHT) if initial else -rng.uniform(20, 100)
        self.size = rng.randint(13, 24)
        self.color = rng.choice(PETAL_COLORS)
        self.alpha = rng.randint(80, 150)
        self.speed = rng.uniform(24, 52)
        self.sway = rng.uniform(15, 38)
        self.sway_speed = rng.uniform(0.35, 0.9)
        self.phase = rng.uniform(0, math.tau)
        self.angle = rng.uniform(0, 360)
        self.spin = rng.uniform(-26, 26)


@dataclass
class Twinkle:
    x: float
    y: float
    size: float
    phase: float
    speed: float
    color: tuple
    drift: float


# ----------------------------------------------------------------------------
# Сцена
# ----------------------------------------------------------------------------
class Scene:
    def __init__(self):
        self.rng = random.Random(20260511)
        self.t = 0.0
        self.hearts = HeartArt()
        self.petals_art = PetalArt()

        self.font_subtitle = load_font("body_italic", 38)
        self.font_line1 = load_font("display_semibold", 45)
        self.font_line2 = load_font("body_italic", 30)
        self.font_hint = load_font("body", 21)
        self.font_toast = load_font("body", 23)
        self.font_signature = load_font("script", 38)
        self.font_kicker = load_font("body", 23)
        self.font_title = load_font("display_bold", 92)

        # --- фоновые слои ---
        self.vignette = self._build_vignette()
        self.background = self._build_background()

        # --- сердце ---
        self.big_heights = list(range(HEART_BASE_HEIGHT, HEART_BASE_HEIGHT + 24, 2))
        biggest = self.hearts.get(
            self.big_heights[-1], BIG_TOP, BIG_BOTTOM, sheen=True, depth=True
        )
        self.big_frames = []
        for h in self.big_heights:
            if h == self.big_heights[-1]:
                self.big_frames.append(biggest)
            else:
                self.big_frames.append(
                    pygame.transform.smoothscale(
                        biggest, (round(h * HEART_ASPECT), h)
                    )
                )
        self.glow_outer = self.hearts.get_glow(
            HEART_BASE_HEIGHT + 90, (255, 246, 232), alpha=78, blur_radius=44
        )
        self.glow_inner = self.hearts.get_glow(
            HEART_BASE_HEIGHT + 10, (255, 216, 222), alpha=58, blur_radius=18
        )
        # Мягкая эллиптическая тень: силуэт сердца в качестве тени давал
        # тёмную «каплю» под кончиком.
        shadow = pygame.Surface((640, 260), pygame.SRCALPHA)
        for sw, sh, a in ((530, 100, 15), (450, 80, 19), (360, 60, 23)):
            rect = pygame.Rect(0, 0, sw, sh)
            rect.center = (320, 130)
            pygame.draw.ellipse(shadow, (116, 34, 52, a), rect)
        self.heart_shadow = soft_blur(shadow, 26)

        # --- надписи ---
        self.kicker = self._make_kicker("ДЛЯ ТЕБЯ, МАМА")
        self.title = gradient_text(
            "С Днём Матери!",
            self.font_title,
            TITLE_TOP,
            TITLE_BOTTOM,
            shadow_color=(92, 28, 45),
            shadow_alpha=38,
            shadow_offset=(0, 4),
            shadow_blur=3.0,
            light_halo=False,
        )
        self.subtitle = text_with_soft_shadow(
            "самой любимой маме на свете",
            self.font_subtitle,
            (150, 78, 94),
            shadow_color=(140, 70, 88),
            shadow_alpha=32,
            shadow_offset=(0, 1),
            shadow_blur=1.0,
        )
        self.line1 = text_with_soft_shadow(
            "Мама, я тебя очень люблю.",
            self.font_line1,
            TEXT_DARK,
            shadow_color=(120, 40, 60),
            shadow_alpha=34,
            shadow_offset=(0, 2),
            shadow_blur=1.8,
        )
        self.line2 = text_with_soft_shadow(
            "Пусть каждый день будет таким же тёплым, как твои объятия.",
            self.font_line2,
            (132, 72, 88),
            shadow_color=(150, 88, 104),
            shadow_alpha=30,
            shadow_offset=(0, 1),
            shadow_blur=1.0,
        )
        self.hint = text_with_soft_shadow(
            "ПРОБЕЛ / клик — салют   •   S — сохранить   "
            "•   F11 — полный экран   •   Esc — выход",
            self.font_hint,
            (146, 96, 108),
            shadow_color=(255, 248, 242),
            shadow_alpha=0,
            shadow_blur=0,
            alpha=215,
        )
        self.divider = self._build_divider()
        self.signature = text_with_soft_shadow(
            "с любовью",
            self.font_signature,
            (126, 52, 72),
            shadow_color=(140, 72, 88),
            shadow_alpha=38,
            shadow_offset=(0, 1),
            shadow_blur=1.0,
        )
        self.footer = self._make_footer()
        self.toast_success = self._make_toast(
            f"Открытка сохранена: {POSTCARD_NAME}"
        )
        self.toast_error = self._make_toast("Не удалось сохранить открытку")

        # --- украшения ---
        self.twinkles = self._make_twinkles()
        self.floaters = []
        for _ in range(5):
            f = FloatingHeart(0, 0, 30, HEART_COLORS[0], 100, 24, 0)
            f.reset(self.rng, initial=True)
            self.floaters.append(f)

        self.petals = []
        for _ in range(22):
            p = Petal(
                0, 0, 18, PETAL_COLORS[0], 120, 32, 20, 0.5, 0, 0, 0,
                self.rng.random() < 0.42,
            )
            p.reset(self.rng, initial=True)
            self.petals.append(p)

        self.back_petals = list(self.petals)
        self.front_petals = []

        # --- эффекты ---
        self.particles: list[HeartParticle] = []
        self.sparks: list[SparkParticle] = []
        self.ripples: list[Ripple] = []
        self.flashes: list[Flash] = []
        self.fx_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.toast_until = -1.0
        self.toast_surface = None
        self.next_auto = 1.2

    # ------------------------------------------------------------------ фон
    def _build_background(self) -> pygame.Surface:
        rng = random.Random(5309)
        bg = pygame.Surface((WIDTH, HEIGHT)).convert()
        stops = (
            (0.0, (255, 250, 244)),
            (0.34, (254, 244, 237)),
            (0.68, (252, 227, 222)),
            (1.0, (247, 203, 209)),
        )
        for y in range(HEIGHT):
            pygame.draw.line(
                bg, sample_stops(stops, y / (HEIGHT - 1)), (0, y), (WIDTH, y)
            )

        # акварельные разводы — считаем в низком разрешении
        wash = pygame.Surface((WIDTH // 5, HEIGHT // 5), pygame.SRCALPHA)
        ww, wh = wash.get_size()
        for _ in range(30):
            cx = rng.uniform(-0.1, 1.1) * ww
            cy = rng.uniform(-0.1, 1.1) * wh
            base = rng.uniform(0.07, 0.22) * ww
            col = rng.choice(WASH_COLORS)
            alpha = rng.randint(9, 22)
            phase = rng.uniform(0, math.tau)
            pts = []
            for i in range(30):
                a = math.tau * i / 30
                r = base * (
                    0.62 + 0.38 * rng.random() + 0.10 * math.sin(3 * a + phase)
                )
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            pygame.draw.polygon(wash, (*col, alpha), pts)
        wash = soft_blur(wash, 5)
        bg.blit(pygame.transform.smoothscale(wash, (WIDTH, HEIGHT)), (0, 0))

        # тёплый свет за сердцем и по углам
        blit_center(bg, radial_sprite(570, (255, 252, 246), 42), WIDTH / 2, 640)
        blit_center(bg, radial_sprite(390, (255, 231, 221), 26), WIDTH / 2, 800)
        blit_center(bg, radial_sprite(320, (255, 244, 230), 24), 420, 320)
        blit_center(bg, radial_sprite(300, (255, 236, 230), 22), WIDTH - 380, 870)

        # волокна бумаги
        fibers = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(650):
            x = rng.uniform(0, WIDTH)
            y = rng.uniform(0, HEIGHT)
            ln = rng.uniform(2, 16)
            ang = rng.uniform(0, math.tau)
            if rng.random() < 0.62:
                col = (255, 255, 255, rng.randint(6, 16))
            else:
                col = (161, 124, 109, rng.randint(4, 10))
            pygame.draw.line(
                fibers,
                col,
                (x, y),
                (x + math.cos(ang) * ln, y + math.sin(ang) * ln),
                1,
            )
        bg.blit(fibers, (0, 0))

        # зерно бумаги
        gw, gh = 400, 280
        grain = pygame.Surface((gw, gh), pygame.SRCALPHA)
        for y in range(gh):
            for x in range(gw):
                v = rng.randint(0, 9)
                grain.set_at((x, y), (v, v, v, 255))
        bg.blit(
            pygame.transform.smoothscale(grain, (WIDTH, HEIGHT)),
            (0, 0),
            special_flags=pygame.BLEND_RGB_ADD,
        )

        bg.blit(self.vignette, (0, 0))

        # Акварельные букеты в противоположных углах временно убраны:
        # крупные полупрозрачные цветы читались как грязные пятна.
        # Вместо них — мягкие размытые акварельные облака и золотая графика.
        bouquet = pygame.transform.smoothscale(
            make_bouquet("rose", 101), (607, 478)
        )
        bouquet = soft_blur(bouquet, 9)
        bg.blit(multiply_alpha(bouquet, 0.20), (-150, HEIGHT - 470))
        bouquet2 = pygame.transform.flip(make_bouquet("peach", 202), True, False)
        bouquet2 = pygame.transform.smoothscale(bouquet2, (515, 406))
        bouquet2 = soft_blur(bouquet2, 9)
        bg.blit(multiply_alpha(bouquet2, 0.18), (WIDTH - 480, -70))

        # двойная золотая рамка
        frame = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(
            frame,
            (*GOLD, 135),
            (28, 28, WIDTH - 56, HEIGHT - 56),
            width=2,
            border_radius=18,
        )
        pygame.draw.rect(
            frame,
            (*GOLD, 85),
            (44, 44, WIDTH - 88, HEIGHT - 88),
            width=1,
            border_radius=12,
        )
        bg.blit(frame, (0, 0))

        # тонкие золотые завитки в углах рамки — только точная деталь,
        # без крупных «нарисованных кустов».
        corners = (
            (64, 64, 5.0, 85.0),
            (WIDTH - 64, 64, 95.0, 175.0),
            (64, HEIGHT - 64, 185.0, 265.0),
            (WIDTH - 64, HEIGHT - 64, 275.0, 355.0),
        )
        for cx, cy, a0, a1 in corners:
            leaf = make_leaf(17, 5, float((a0 + a1) / 2), GOLD_LIGHT, 140)
            bg.blit(leaf, leaf.get_rect(center=(int(cx), int(cy))))

        # золотая пыль
        specks = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(52):
            x = clamp(rng.gauss(WIDTH / 2, 430), 90, WIDTH - 90)
            y = clamp(rng.gauss(HEIGHT / 2, 330), 110, HEIGHT - 110)
            a = rng.randint(30, 95)
            pygame.draw.circle(
                specks, (*GOLD_LIGHT, a), (int(x), int(y)), rng.choice((1, 1, 2))
            )
        bg.blit(specks, (0, 0))
        return bg

    def _build_vignette(self) -> pygame.Surface:
        sw, sh = 160, 112
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = (sw - 1) / 2, (sh - 1) / 2
        for y in range(sh):
            for x in range(sw):
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                d = math.sqrt(dx * dx * 0.92 + dy * dy)
                k = clamp((d - 0.60) / 0.55, 0.0, 1.0)
                a = int(42 * k * k)
                if a:
                    surf.set_at((x, y), (104, 44, 62, a))
        return pygame.transform.smoothscale(surf, (WIDTH, HEIGHT))

    def _build_divider(self) -> pygame.Surface:
        w, h = 620, 62
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        for side in (-1, 1):
            # линия плавно истончается к краю
            for i in range(186):
                k = i / 185.0
                a = int(150 * ((1.0 - k) ** 0.72))
                x = cx + side * (62 + i)
                pygame.draw.line(surf, (*GOLD, a), (x, cy), (x, cy))
            ex = cx + side * 250
            pygame.draw.polygon(
                surf,
                (*GOLD, 185),
                [(ex, cy - 4), (ex + 4, cy), (ex, cy + 4), (ex - 4, cy)],
            )
            for dx, ang in ((104, 40), (164, -40)):
                leaf = make_leaf(23, 7, side * ang, GOLD_LIGHT, 155)
                surf.blit(leaf, leaf.get_rect(center=(cx + side * dx, cy)))
            pygame.draw.circle(surf, (*GOLD_LIGHT, 150), (cx + side * 58, cy), 2)
            pygame.draw.circle(surf, (*GOLD, 90), (cx + side * 72, cy), 1)
        heart = self.hearts.get(44, (216, 124, 144), (150, 40, 68), sheen=True)
        surf.blit(heart, heart.get_rect(center=(cx, cy)))
        pygame.draw.circle(surf, (*GOLD, 80), (cx, cy), 31, 1)
        return surf

    def _make_kicker(self, text: str) -> pygame.Surface:
        label = render_tracked(
            text, self.font_kicker, (172, 130, 74), tracking=9, alpha=235
        )
        d = 5
        gap = 16
        w = label.get_width() + 2 * (gap + 3 * d)
        h = max(label.get_height(), 16)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(label, (gap + 3 * d, (h - label.get_height()) // 2))
        cy = h // 2
        for cx in (gap + d, w - gap - d):
            pygame.draw.polygon(
                surf,
                (*GOLD, 200),
                [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)],
            )
        return surf

    def _make_footer(self) -> pygame.Surface:
        sig = self.signature
        w = sig.get_width() + 300
        h = max(sig.get_height(), 48)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sig, ((w - sig.get_width()) // 2, (h - sig.get_height()) // 2))
        cy = h // 2
        for side in (-1, 1):
            inner = w // 2 + side * (sig.get_width() // 2 + 20)
            tiny = self.hearts.get(15, (198, 116, 134), alpha=215)
            surf.blit(tiny, tiny.get_rect(center=(inner, cy)))
            x0 = w // 2 + side * (sig.get_width() // 2 + 38)
            x1 = w // 2 + side * (sig.get_width() // 2 + 112)
            for i in range(70):
                k = i / 69.0
                a = int(130 * ((1.0 - k) ** 0.65))
                x = int(x0 + (x1 - x0) * k)
                pygame.draw.line(surf, (*GOLD, a), (x, cy), (x, cy))
            dx = x1 + side * 7
            pygame.draw.polygon(
                surf,
                (*GOLD, 180),
                [(dx, cy - 4), (dx + 4, cy), (dx, cy + 4), (dx - 4, cy)],
            )
        return surf

    def _make_toast(self, text: str) -> pygame.Surface:
        label = self.font_toast.render(text, True, (124, 55, 76))
        w, h = label.get_width() + 40, label.get_height() + 18
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 251, 247, 228), (0, 0, w, h),
                         border_radius=h // 2)
        pygame.draw.rect(surf, (218, 154, 169, 150), (0, 0, w, h), width=1,
                         border_radius=h // 2)
        surf.blit(label, (20, 9))
        return surf

    @staticmethod
    def _inside_heart_zone(x: float, y: float) -> bool:
        """Запретная зона вокруг сердца: блики не должны лежать на нём."""
        dx = (x - WIDTH / 2) / (HEART_BASE_HEIGHT * HEART_ASPECT * 0.66)
        dy = (y - HEART_CY) / (HEART_BASE_HEIGHT * 0.62)
        return dx * dx + dy * dy < 1.0

    def _make_twinkles(self) -> list[Twinkle]:
        rng = self.rng
        result: list[Twinkle] = []
        palette = [(255, 252, 242), (255, 232, 194), (255, 222, 232)]
        attempts = 0
        while len(result) < 40 and attempts < 600:
            attempts += 1
            x = clamp(rng.gauss(WIDTH / 2, WIDTH * 0.30), 60, WIDTH - 60)
            y = clamp(rng.gauss(640, 270), 120, HEIGHT - 90)
            if self._inside_heart_zone(x, y):
                continue
            result.append(
                Twinkle(
                    x=x,
                    y=y,
                    size=rng.uniform(1.6, 5.2),
                    phase=rng.uniform(0, math.tau),
                    speed=rng.uniform(1.0, 3.2),
                    color=rng.choice(palette),
                    drift=rng.uniform(3, 10),
                )
            )
        # «главные» звёздочки — только по сторонам от сердца
        result.append(Twinkle(408, 468, 7.0, 0.4, 2.0, (255, 250, 234), 4.0))
        result.append(Twinkle(1210, 648, 6.2, 2.0, 1.6, (255, 243, 226), 5.0))
        result.append(Twinkle(1140, 372, 5.2, 4.3, 2.4, (255, 236, 244), 4.0))
        return result

    # --------------------------------------------------------------- события
    def celebrate_tip(self, strength: float = 1.0) -> None:
        h = self.big_heights[-1]
        tip_y = HEART_CY + h / 2.0 - 3
        self._burst(WIDTH / 2 + self.rng.uniform(-8, 8), tip_y,
                    beauty=strength, fountain=True)

    def celebrate_at(self, x: float, y: float, strength: float = 0.9) -> None:
        self._burst(x, y, beauty=strength, fountain=False)

    def _burst(self, x: float, y: float, beauty: float = 1.0,
               fountain: bool = False) -> None:
        if len(self.particles) > 320:
            return

        heart_count = max(7, int(round(16 * beauty)))
        heart_count += 2
        for i in range(heart_count):
            if fountain:
                angle = self.rng.uniform(-math.pi * 0.91, -math.pi * 0.09)
            else:
                angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(150, 480) * (0.78 + beauty * 0.30)
            x0 = x + (self.rng.uniform(-34, 34) if fountain else 0)
            y0 = y + (self.rng.uniform(-6, 14) if fountain else 0)
            self.particles.append(
                HeartParticle(
                    x=x0,
                    y=y0,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - (60 if fountain else 0),
                    size=self.rng.uniform(18, 40) * (0.8 + beauty * 0.25),
                    color=self.rng.choice(HEART_COLORS),
                    life=self.rng.uniform(1.5, 2.7),
                    max_life=2.7,
                    phase=self.rng.uniform(0, math.tau),
                )
            )

        spark_count = int(round(20 * beauty))
        for _ in range(spark_count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(150, 520)
            col = self.rng.choice(SPARK_COLORS)
            kind = "star" if self.rng.random() < 0.68 else "dot"
            self.sparks.append(
                SparkParticle(
                    x=x + self.rng.uniform(-12, 12),
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 35,
                    size=self.rng.uniform(2.2, 6.2),
                    color=col,
                    life=self.rng.uniform(0.5, 1.3),
                    max_life=1.3,
                    kind=kind,
                )
            )

        self.ripples.append(Ripple(x, y, 0.62, 0.62, 230 * beauty, (255, 219, 225)))
        self.flashes.append(Flash(x, y, 0.26, 0.26, 230 * beauty, (255, 242, 220)))

    def save_postcard(self, canvas: pygame.Surface) -> Path:
        path = ROOT / POSTCARD_NAME
        try:
            self.draw(canvas, show_hud=False, beat=0.72, clean=True)
            pygame.image.save(canvas, str(path))
            self.toast_surface = self.toast_success
            print(f"Postcard saved: {path}")
        except (OSError, pygame.error) as exc:
            self.toast_surface = self.toast_error
            print(f"Could not save postcard: {exc}")
        self.toast_until = self.t + 3.4
        return path

    # --------------------------------------------------------------- анимация
    def update(self, dt: float) -> None:
        dt = min(dt, 0.05)
        self.t += dt

        if self.t >= self.next_auto:
            self.celebrate_tip(strength=0.42)
            self.next_auto = self.t + self.rng.uniform(8.0, 11.0)

        for p in self.particles[:]:
            if not p.update(dt):
                self.particles.remove(p)
        for s in self.sparks[:]:
            if not s.update(dt):
                self.sparks.remove(s)
        for r in self.ripples[:]:
            r.life -= dt
            if r.life <= 0:
                self.ripples.remove(r)
        for f in self.flashes[:]:
            f.life -= dt
            if f.life <= 0:
                self.flashes.remove(f)

        for f in self.floaters:
            f.y -= f.speed * dt
            if f.y < -55:
                f.reset(self.rng)

        for p in self.petals:
            p.y += p.speed * dt
            p.x += math.sin(self.t * p.sway_speed + p.phase) * p.sway * dt
            p.angle += p.spin * dt
            if p.y > HEIGHT + 40 or p.x < -60 or p.x > WIDTH + 60:
                p.reset(self.rng)

    # ---------------------------------------------------------------- отрисовка
    def draw(
        self,
        target: pygame.Surface,
        show_hud: bool = True,
        beat: float | None = None,
        clean: bool = False,
    ) -> None:
        target.blit(self.background, (0, 0))

        # дальние сердечки
        for f in self.floaters:
            wobble = 20 * math.sin(self.t * 1.25 + f.phase)
            surf = self.hearts.get(f.height, f.color, alpha=f.alpha)
            target.blit(
                surf,
                surf.get_rect(center=(round(f.x + wobble), round(f.y))),
            )

        # лепестки за сердцем
        for p in self.back_petals:
            sprite = self.petals_art.get(p.size, p.color, p.alpha, p.angle)
            target.blit(
                sprite,
                sprite.get_rect(center=(round(p.x), round(p.y))),
            )

        if beat is None:
            beat = heartbeat(self.t)
        frame_idx = min(
            len(self.big_frames) - 1,
            int(round(beat * (len(self.big_frames) - 1))),
        )
        big = self.big_frames[frame_idx]
        bob = math.sin(self.t * 1.08) * 4.0
        sway = math.sin(self.t * 0.53) * 3.0
        cx = WIDTH / 2 + sway
        cy = HEART_CY + bob

        # свечение, тень и объёмное сердце
        blit_center(target, self.glow_outer, cx, cy)
        blit_center(target, self.heart_shadow, cx + 6, cy + 198)
        blit_center(target, self.glow_inner, cx, cy)
        blit_center(target, big, cx, cy)

        # частицы
        if not clean:
            for p in self.particles:
                p.draw(target, self.hearts)
            for p in self.front_petals:
                sprite = self.petals_art.get(p.size, p.color, p.alpha, p.angle)
                target.blit(
                    sprite,
                    sprite.get_rect(center=(round(p.x), round(p.y))),
                )

        # мерцающие звёздочки, вспышки и кольца
        self.fx_layer.fill((0, 0, 0, 0))
        for sp in self.twinkles:
            shimmer = 0.5 + 0.5 * math.sin(self.t * sp.speed + sp.phase)
            a = int(180 * shimmer ** 3)
            if a < 5:
                continue
            x = int(sp.x + math.sin(self.t * 0.35 + sp.phase) * sp.drift)
            y = int(sp.y + math.cos(self.t * 0.29 + sp.phase) * sp.drift * 0.6)
            r = sp.size * (0.5 + 0.5 * shimmer)
            arm_x = max(1, int(round(r)))
            arm_y = max(1, int(round(r * 0.55)))
            pygame.draw.line(self.fx_layer, (*sp.color, a),
                             (x - arm_x, y), (x + arm_x, y), 1)
            pygame.draw.line(self.fx_layer, (*sp.color, a),
                             (x, y - arm_y), (x, y + arm_y), 1)
            if sp.size > 3.4:
                d = max(1, int(r * 0.5))
                pygame.draw.line(self.fx_layer, (*sp.color, a // 2),
                                 (x - d, y - d), (x + d, y + d), 1)
                pygame.draw.line(self.fx_layer, (*sp.color, a // 2),
                                 (x + d, y - d), (x - d, y + d), 1)

        if not clean:
            for f in self.flashes:
                f.draw(self.fx_layer)
            for r in self.ripples:
                r.draw(self.fx_layer)
            for s in self.sparks:
                s.draw(self.fx_layer)
        target.blit(self.fx_layer, (0, 0))

        # надписи
        blit_center(target, self.kicker, WIDTH / 2, 82)
        blit_center(target, self.title, WIDTH / 2, 182)
        blit_center(target, self.divider, WIDTH / 2, 292)
        blit_center(target, self.subtitle, WIDTH / 2, 356)
        blit_center(target, self.line1, WIDTH / 2, 928)
        blit_center(target, self.line2, WIDTH / 2, 984)

        if show_hud:
            if self.t < self.toast_until and self.toast_surface is not None:
                blit_center(target, self.toast_surface, WIDTH / 2, 1042)
            else:
                blit_center(target, self.hint, WIDTH / 2, 1042)
        else:
            blit_center(target, self.footer, WIDTH / 2, 1042)


# ----------------------------------------------------------------------------
# Приложение
# ----------------------------------------------------------------------------
def choose_window_size():
    """Подбирает комфортный размер окна под экран, сохраняя пропорции 10:7."""
    try:
        sizes = pygame.display.get_desktop_sizes()
        desk_w, desk_h = sizes[0]
    except (pygame.error, IndexError, AttributeError):
        desk_w, desk_h = 1600, 900
    scale = min((desk_w * 0.90) / WIDTH, (desk_h * 0.86) / HEIGHT)
    scale = clamp(scale, 0.34, 1.0)
    return (
        max(640, int(round(WIDTH * scale))),
        max(448, int(round(HEIGHT * scale))),
    )


def make_window_icon() -> pygame.Surface:
    icon = pygame.Surface((128, 128), pygame.SRCALPHA)
    pygame.draw.circle(icon, (255, 250, 244, 255), (64, 64), 62)
    pygame.draw.circle(icon, (*GOLD, 255), (64, 64), 62, 2)
    pygame.draw.circle(icon, (244, 214, 214, 255), (64, 64), 54, 1)
    heart = make_heart(84, BIG_TOP, BIG_BOTTOM, sheen=True)
    icon.blit(heart, heart.get_rect(center=(64, 66)))
    return icon


class CardApp:
    def __init__(self, headless: bool = False):
        self.headless = headless
        pygame.display.set_caption("С Днём Матери!  •  ПРОБЕЛ — салют  •  F11 — полный экран")
        try:
            pygame.display.set_icon(make_window_icon())
        except pygame.error:
            pass
        self.window_size = choose_window_size()
        flags = 0 if headless else pygame.RESIZABLE
        self.window = pygame.display.set_mode(self.window_size, flags)
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.scene = Scene()
        self.running = True
        self.fullscreen = False
        self.fit_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self._mat_shadow = None
        self._mat_shadow_key = None
        self.scene.draw(self.canvas, beat=0.55)
        self.present()

    def toggle_fullscreen(self) -> None:
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)

    def window_to_canvas(self, pos):
        r = self.fit_rect
        if r.w <= 0 or r.h <= 0 or not r.collidepoint(pos):
            return None
        x = (pos[0] - r.x) * WIDTH / r.w
        y = (pos[1] - r.y) * HEIGHT / r.h
        return x, y

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.scene.celebrate_tip(1.0)
                    self.scene.next_auto = self.scene.t + 8.5
                elif event.key == pygame.K_s:
                    self.scene.save_postcard(self.canvas)
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.window_to_canvas(event.pos)
                if pos is not None:
                    self.scene.celebrate_at(pos[0], pos[1], 0.85)
                    self.scene.next_auto = self.scene.t + 8.5

    def _get_mat_shadow(self, out_w: int, out_h: int) -> pygame.Surface:
        key = (out_w, out_h)
        if self._mat_shadow_key != key:
            pad = 70
            surf = pygame.Surface((out_w + pad * 2, out_h + pad * 2), pygame.SRCALPHA)
            pygame.draw.rect(
                surf, (0, 0, 0, 95), (pad, pad + 12, out_w, out_h), border_radius=6
            )
            self._mat_shadow = soft_blur(surf, 22)
            self._mat_shadow_key = key
        return self._mat_shadow

    def present(self) -> None:
        window = pygame.display.get_surface()
        if window is None:
            return
        win_w, win_h = window.get_size()
        if win_w <= 0 or win_h <= 0:
            return

        if win_w == WIDTH and win_h == HEIGHT:
            window.blit(self.canvas, (0, 0))
            self.fit_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        else:
            window.fill(MAT_COLOR)
            scale = min(win_w / WIDTH, win_h / HEIGHT)
            out_w = max(1, int(round(WIDTH * scale)))
            out_h = max(1, int(round(HEIGHT * scale)))
            x = (win_w - out_w) // 2
            y = (win_h - out_h) // 2
            self.fit_rect = pygame.Rect(x, y, out_w, out_h)
            if out_w == WIDTH and out_h == HEIGHT:
                scaled = self.canvas
            else:
                scaled = pygame.transform.smoothscale(self.canvas, (out_w, out_h))
            shadow = self._get_mat_shadow(out_w, out_h)
            window.blit(shadow, shadow.get_rect(center=(win_w // 2, win_h // 2 + 8)))
            window.blit(scaled, (x, y))
            pygame.draw.rect(window, (214, 180, 126), self.fit_rect, 1)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if not self.running:
                break
            self.scene.update(dt)
            self.scene.draw(self.canvas)
            self.present()

    def render_selftest(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        for i in range(200):
            self.scene.update(1.0 / 60.0)
            if i == 120:
                self.scene.celebrate_tip(1.0)
        self.scene.draw(self.canvas, show_hud=True, beat=0.55)
        pygame.image.save(self.canvas, str(path))

        # даём салюту догореть — открытка для печати должна быть чистой
        for _ in range(220):
            self.scene.update(1.0 / 60.0)
        poster_path = path.with_name(f"{path.stem}_poster{path.suffix}")
        self.scene.draw(self.canvas, show_hud=False, beat=0.78, clean=True)
        pygame.image.save(self.canvas, str(poster_path))
        print(f"Preview saved: {path}")
        print(f"Poster saved:  {poster_path}")


# ----------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Анимированная открытка «С Днём Матери!»"
    )
    parser.add_argument(
        "--selftest",
        nargs="?",
        const=str(ROOT / "build" / "mothers_day_preview.png"),
        default=None,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    headless = bool(args.selftest)
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    try:
        app = CardApp(headless=headless)
        if args.selftest:
            app.render_selftest(Path(args.selftest))
        else:
            app.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
