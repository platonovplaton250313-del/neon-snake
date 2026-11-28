#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEON BRAWL: рисование интерфейса и портретов бойцов."""

import math

from neon_brawl_data import (
    BG, CYAN, GOLD, MUTED, TEXT, clamp, hex_points, mix,
)


def rrect(c, x1, y1, x2, y2, r=8, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return c.create_polygon(pts, smooth=True, splinesteps=8, **kw)


def text_glow(c, x, y, text, font, fill, anchor="center", glow=None,
              off=2, **kw):
    glow = glow or mix(fill, BG, 0.72)
    for dx, dy in ((-off, 0), (off, 0), (0, -off), (0, off),
                   (-off, -off), (off, off)):
        c.create_text(x + dx, y + dy, text=text, font=font, fill=glow,
                      anchor=anchor, **kw)
    return c.create_text(x, y, text=text, font=font, fill=fill,
                         anchor=anchor, **kw)


def bar(c, x, y, w, h, value, color, back="#101d31", radius=None):
    radius = h / 2 if radius is None else radius
    rrect(c, x, y, x + w, y + h, radius, fill=back, outline="")
    value = clamp(value, 0.0, 1.0)
    if value > 0.001:
        rrect(c, x, y, x + max(h, w * value), y + h, radius,
              fill=color, outline="")


def crystal(c, cx, cy, s=10, color="#b07cff", light="#e8d8ff", rot=0.0):
    pts = []
    for i, (rx, ry) in enumerate(((0.0, -1.25), (1.0, -0.35), (0.62, 1.15),
                                   (-0.62, 1.15), (-1.0, -0.35))):
        a = rot + i * 0.0
        pts.extend((cx + rx * s, cy + ry * s))
    c.create_polygon(pts, fill=color, outline=light, width=max(1, int(s * 0.12)),
                     smooth=False)
    c.create_polygon([cx, cy - s * 1.1, cx + s * 0.5, cy,
                      cx, cy + s * 0.8, cx - s * 0.5, cy],
                     fill=light, outline="")


def trophy(c, cx, cy, s=9, color=GOLD):
    c.create_polygon([cx - s * 0.7, cy - s, cx + s * 0.7, cy - s,
                      cx + s * 0.45, cy + s * 0.2, cx - s * 0.45, cy + s * 0.2],
                     fill=color, outline="")
    c.create_rectangle(cx - s * 0.18, cy + s * 0.15, cx + s * 0.18,
                       cy + s * 0.65, fill=color, outline="")
    c.create_rectangle(cx - s * 0.55, cy + s * 0.6, cx + s * 0.55,
                       cy + s * 0.85, fill=color, outline="")


def hero_icon(c, cx, cy, r, hero):
    col = hero["color"]
    c.create_polygon(hex_points(cx, cy, r), fill=hero["dark"],
                     outline=col, width=2)
    c.create_oval(cx - r * 0.42, cy - r * 0.46, cx + r * 0.42, cy + r * 0.26,
                  fill="#0a1322", outline=col, width=max(1, int(r * 0.07)))
    c.create_rectangle(cx - r * 0.3, cy - r * 0.27, cx + r * 0.3,
                       cy - r * 0.1, fill=hero["light"], outline="")
    c.create_text(cx, cy + r * 0.55, text=hero["name"][0],
                  font=("Bahnschrift SemiBold", max(8, int(r * 0.5))),
                  fill=col)


def _head(c, cx, cy, s, hero):
    art = hero["art"]
    col, light, dark = hero["color"], hero["light"], hero["dark"]
    if art == 2:
        hood = [(cx - 46 * s, cy + 8 * s), (cx - 30 * s, cy - 54 * s),
                (cx, cy - 72 * s), (cx + 30 * s, cy - 54 * s),
                (cx + 46 * s, cy + 8 * s), (cx + 30 * s, cy + 2 * s),
                (cx - 30 * s, cy + 2 * s)]
        c.create_polygon(hood, fill=dark, outline=col, width=max(1, int(3 * s)),
                         smooth=True)
    c.create_oval(cx - 34 * s, cy - 54 * s, cx + 34 * s, cy + 12 * s,
                  fill="#0a1322", outline=col, width=max(2, int(3 * s)))
    if art == 3:
        c.create_oval(cx - 46 * s, cy - 84 * s, cx + 46 * s, cy - 58 * s,
                      outline=GOLD, width=max(1, int(3 * s)))
        c.create_oval(cx + 24 * s, cy - 20 * s, cx + 54 * s, cy + 30 * s,
                      fill=dark, outline=col, width=max(1, int(2 * s)))
    if art == 0:
        c.create_polygon([cx - 28 * s, cy - 50 * s, cx - 12 * s, cy - 79 * s,
                          cx, cy - 54 * s, cx + 13 * s, cy - 84 * s,
                          cx + 26 * s, cy - 50 * s], fill=col, outline="")
    elif art == 1:
        c.create_polygon([cx - 16 * s, cy - 56 * s, cx, cy - 88 * s,
                          cx + 16 * s, cy - 56 * s], fill=col, outline="")
        c.create_polygon([cx - 54 * s, cy - 20 * s, cx - 70 * s, cy + 8 * s,
                          cx - 35 * s, cy + 2 * s], fill=dark, outline=col,
                         width=max(1, int(2 * s)))
        c.create_polygon([cx + 54 * s, cy - 20 * s, cx + 70 * s, cy + 8 * s,
                          cx + 35 * s, cy + 2 * s], fill=dark, outline=col,
                         width=max(1, int(2 * s)))
    elif art == 5:
        c.create_polygon([cx - 42 * s, cy - 50 * s, cx - 16 * s, cy - 78 * s,
                          cx + 18 * s, cy - 72 * s, cx + 42 * s, cy - 44 * s,
                          cx + 30 * s, cy - 18 * s, cx - 30 * s, cy - 18 * s],
                         fill=dark, outline=col, width=max(1, int(2 * s)),
                         smooth=True)
    c.create_rectangle(cx - 26 * s, cy - 38 * s, cx + 26 * s, cy - 19 * s,
                       fill=light, outline="")
    c.create_rectangle(cx - 22 * s, cy - 35 * s, cx + 22 * s, cy - 23 * s,
                       fill="#0a2a3a", outline="")
    if art == 4:
        c.create_oval(cx - 23 * s, cy - 11 * s, cx - 7 * s, cy + 7 * s,
                      fill=dark, outline=col, width=max(1, int(2 * s)))
        c.create_oval(cx + 7 * s, cy - 11 * s, cx + 23 * s, cy + 7 * s,
                      fill=dark, outline=col, width=max(1, int(2 * s)))
        c.create_line(cx - 8 * s, cy + 1 * s, cx + 8 * s, cy + 1 * s,
                      fill=col, width=max(1, int(2 * s)))
    elif art == 5:
        c.create_polygon([cx - 28 * s, cy - 4 * s, cx + 28 * s, cy - 12 * s,
                          cx + 24 * s, cy + 6 * s, cx - 24 * s, cy + 9 * s],
                         fill=col, outline="")
    else:
        c.create_line(cx - 26 * s, cy - 24 * s, cx + 26 * s, cy - 24 * s,
                      fill=mix(light, "#ffffff", 0.3),
                      width=max(1, int(1.5 * s)))


def _torso(c, cx, cy, s, hero):
    col, light, dark = hero["color"], hero["light"], hero["dark"]
    pts = [
        cx - 72 * s, cy + 96 * s, cx - 58 * s, cy + 46 * s,
        cx - 30 * s, cy + 26 * s, cx + 30 * s, cy + 26 * s,
        cx + 58 * s, cy + 46 * s, cx + 72 * s, cy + 96 * s,
        cx + 40 * s, cy + 108 * s, cx - 40 * s, cy + 108 * s,
    ]
    c.create_polygon(pts, fill=dark, outline=col, width=max(2, int(3 * s)),
                     smooth=True)
    rrect(c, cx - 34 * s, cy + 34 * s, cx + 34 * s, cy + 92 * s, 8 * s,
          fill=mix(dark, "#000000", 0.2), outline=light,
          width=max(1, int(1.5 * s)))
    c.create_polygon(hex_points(cx, cy + 58 * s, 15 * s), fill=light,
                     outline=col, width=max(1, int(1.5 * s)))
    c.create_text(cx, cy + 58 * s, text=hero["name"][0],
                  font=("Bahnschrift SemiBold", max(8, int(16 * s))),
                  fill=dark)
    for side in (-1, 1):
        c.create_oval(cx + side * 62 * s - 17 * s, cy + 26 * s,
                      cx + side * 62 * s + 17 * s, cy + 60 * s,
                      fill=dark, outline=col, width=max(1, int(2 * s)))
        c.create_line(cx + side * 64 * s, cy + 38 * s,
                      cx + side * 66 * s, cy + 50 * s,
                      fill=light, width=max(1, int(1.5 * s)))


def _weapon(c, cx, cy, s, hero):
    art = hero["art"]
    col, light, dark = hero["color"], hero["light"], hero["dark"]
    if art == 0:
        c.create_line(cx + 36 * s, cy + 58 * s, cx + 122 * s, cy + 8 * s,
                      fill=dark, width=max(3, int(13 * s)),
                      capstyle="round")
        c.create_line(cx + 36 * s, cy + 58 * s, cx + 122 * s, cy + 8 * s,
                      fill=light, width=max(1, int(3 * s)),
                      capstyle="round")
        c.create_line(cx + 112 * s, cy + 15 * s, cx + 136 * s, cy - 2 * s,
                      fill=col, width=max(2, int(5 * s)))
    elif art == 1:
        c.create_line(cx + 36 * s, cy + 52 * s, cx + 112 * s, cy + 24 * s,
                      fill=dark, width=max(4, int(20 * s)),
                      capstyle="round")
        c.create_line(cx + 36 * s, cy + 52 * s, cx + 112 * s, cy + 24 * s,
                      fill=light, width=max(1, int(3 * s)))
        c.create_line(cx + 104 * s, cy + 18 * s, cx + 130 * s, cy + 8 * s,
                      fill=col, width=max(3, int(9 * s)),
                      capstyle="round")
    elif art == 2:
        c.create_line(cx + 30 * s, cy + 58 * s, cx + 148 * s, cy - 12 * s,
                      fill=dark, width=max(2, int(7 * s)),
                      capstyle="round")
        c.create_line(cx + 30 * s, cy + 58 * s, cx + 148 * s, cy - 12 * s,
                      fill=light, width=max(1, int(2 * s)))
        c.create_oval(cx + 66 * s, cy + 16 * s, cx + 84 * s, cy + 34 * s,
                      fill="#0a1322", outline=col, width=2)
        c.create_line(cx + 140 * s, cy - 17 * s, cx + 162 * s, cy - 27 * s,
                      fill=col, width=max(2, int(4 * s)))
    elif art == 3:
        c.create_line(cx + 64 * s, cy - 82 * s, cx + 64 * s, cy + 88 * s,
                      fill=dark, width=max(3, int(8 * s)),
                      capstyle="round")
        c.create_oval(cx + 46 * s, cy - 102 * s, cx + 82 * s, cy - 64 * s,
                      fill=dark, outline=GOLD, width=max(2, int(3 * s)))
        c.create_oval(cx + 54 * s, cy - 94 * s, cx + 74 * s, cy - 72 * s,
                      fill=GOLD, outline="")
    elif art == 4:
        c.create_line(cx + 32 * s, cy + 60 * s, cx + 120 * s, cy + 40 * s,
                      fill=dark, width=max(4, int(22 * s)),
                      capstyle="round")
        c.create_line(cx + 32 * s, cy + 60 * s, cx + 120 * s, cy + 40 * s,
                      fill=light, width=max(1, int(3 * s)))
        c.create_oval(cx + 104 * s, cy + 26 * s, cx + 136 * s, cy + 56 * s,
                      fill=col, outline=light, width=max(1, int(2 * s)))
    elif art == 5:
        for side, dy in ((-1, 10), (1, -14)):
            c.create_line(cx + side * 30 * s, cy + 66 * s,
                          cx + side * 98 * s, cy + dy * s,
                          fill=light, width=max(1, int(4 * s)),
                          capstyle="round")
            c.create_line(cx + side * 30 * s, cy + 66 * s,
                          cx + side * 98 * s, cy + dy * s,
                          fill=dark, width=max(1, int(1.5 * s)))


def draw_hero_bust(c, cx, cy, s, hero, t=0.0, glow=True):
    col = hero["color"]
    if glow:
        for r in (92, 74, 58):
            c.create_oval(cx - r * s, cy - r * s * 0.85,
                          cx + r * s, cy + r * s * 0.9,
                          outline=mix(col, BG, 0.84), width=2)
    _torso(c, cx, cy, s, hero)
    c.create_rectangle(cx - 9 * s, cy - 8 * s, cx + 9 * s, cy + 34 * s,
                       fill=hero["dark"], outline="")
    _head(c, cx, cy, s, hero)
    _weapon(c, cx, cy, s, hero)


def draw_hero_full(c, cx, cy, s, hero, t=0.0):
    col, light, dark = hero["color"], hero["light"], hero["dark"]
    for r in (150, 126, 102):
        c.create_oval(cx - r * s, cy - r * s, cx + r * s, cy + r * s,
                      outline=mix(col, BG, 0.87), width=2)
    for side in (-1, 1):
        lx = cx + side * 25 * s
        c.create_polygon([lx - 14 * s, cy + 92 * s, lx + 14 * s, cy + 92 * s,
                          lx + 18 * s, cy + 154 * s, lx - 12 * s, cy + 154 * s],
                         fill=dark, outline=col, width=max(1, int(2 * s)),
                         smooth=True)
        c.create_oval(lx - 18 * s, cy + 146 * s, lx + 20 * s, cy + 168 * s,
                      fill=mix(dark, "#000000", 0.35), outline=light,
                      width=max(1, int(1.5 * s)))
    draw_hero_bust(c, cx, cy - 26 * s, s, hero, t)
    c.create_oval(cx - 52 * s, cy - 138 * s, cx + 52 * s, cy - 40 * s,
                  outline=mix(col, BG, 0.8), width=1)


def draw_simple_brawler(c, x, y, radius, angle, hero, team_color, player=False,
                        flash=0.0, invis=False, overdrive=False, shield=False,
                        spawn_shield=False, bob=0.0):
    """Вид сверху для арены."""
    import math
    col, light, dark = hero["color"], hero["light"], hero["dark"]
    bob_y = math.sin(bob) * 2.0
    stipple = "gray50" if invis else ""
    # тень
    c.create_oval(x - radius * 0.9, y + radius * 0.5,
                  x + radius * 0.9, y + radius * 1.05,
                  fill="#02050b", outline="")
    if overdrive:
        c.create_oval(x - radius - 8, y - radius - 8,
                      x + radius + 8, y + radius + 8,
                      outline=mix(GOLD, BG, 0.15), width=3)
    c.create_oval(x - radius - 4, y - radius - 4 + bob_y,
                  x + radius + 4, y + radius + 4 + bob_y,
                  outline=team_color, width=3 if player else 2)
    if player:
        c.create_oval(x - radius - 8, y - radius - 8 + bob_y,
                      x + radius + 8, y + radius + 8 + bob_y,
                      outline="#ffffff", width=1, dash=(3, 4))
    body = "#ffffff" if flash > 0 else col
    c.create_oval(x - radius, y - radius + bob_y, x + radius,
                  y + radius + bob_y, fill=body, outline=dark,
                  width=max(2, int(radius * 0.16)), stipple=stipple)
    c.create_oval(x - radius * 0.68, y - radius * 0.75 + bob_y,
                  x + radius * 0.68, y + radius * 0.2 + bob_y,
                  fill=mix(dark, "#000000", 0.3), outline="", stipple=stipple)
    # визор
    ca, sa = math.cos(angle), math.sin(angle)
    px, py = -sa, ca
    c.create_line(x + px * radius * 0.65, y + py * radius * 0.65 + bob_y,
                  x - px * radius * 0.65, y - py * radius * 0.65 + bob_y,
                  fill=light, width=max(3, int(radius * 0.18)))
    # оружие
    gx1 = x + ca * radius * 0.4
    gy1 = y + sa * radius * 0.4 + bob_y
    gx2 = x + ca * (radius + 13)
    gy2 = y + sa * (radius + 13) + bob_y
    c.create_line(gx1, gy1, gx2, gy2, fill=dark,
                  width=max(5, int(radius * 0.32)), capstyle="round")
    c.create_line(gx1, gy1, gx2, gy2, fill=light,
                  width=max(1, int(radius * 0.1)), capstyle="round")
    c.create_oval(gx2 - 3, gy2 - 3, gx2 + 3, gy2 + 3,
                  fill=light, outline="")
    if shield:
        c.create_oval(x - radius - 9, y - radius - 9 + bob_y,
                      x + radius + 9, y + radius + 9 + bob_y,
                      outline=CYAN, width=2)
    if spawn_shield:
        c.create_oval(x - radius - 12, y - radius - 12 + bob_y,
                      x + radius + 12, y + radius + 12 + bob_y,
                      outline=mix(CYAN, BG, 0.25), width=2, dash=(5, 4))
