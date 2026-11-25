#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEON BRAWL — оригинальная неоновая арена 3×3 на tkinter.

Запуск:
    python neon_brawl.py
    play_brawl.bat

Управление:
    WASD / стрелки  — движение
    мышь            — прицел
    ЛКМ             — огонь
    ПКМ / ПРОБЕЛ    — суперспособность
    E               — гаджет
    ESC             — пауза
"""

import math
import random
import sys
import time
import traceback
import tkinter as tk

from neon_brawl_data import (
    BG, BLUE, CYAN, DIM, DIFFICULTIES, F_MONO, F_TITLE, F_UI, GOLD, GREEN,
    HEROES, HERO_ORDER, LINE, MAGENTA, MODES, MUTED, PANEL, PANEL2, RED,
    TEAM_COLORS, TEXT, VERSION, VH, VIOLET, VW,
    clamp, dist, fmt_time, mix, plural, point_in_rect,
)
from neon_brawl_draw import (
    bar, crystal, draw_hero_bust, draw_hero_full, hero_icon, rrect,
    text_glow, trophy,
)
from neon_brawl_engine import Match


class App:
    def __init__(self, root, smoke=False):
        self.root = root
        self.smoke = smoke
        root.title("NEON BRAWL — арена 3×3")
        root.geometry("%dx%d" % (VW, VH))
        root.resizable(False, False)
        root.configure(bg=BG)
        self.canvas = tk.Canvas(root, width=VW, height=VH, bg=BG,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        from neon_brawl_data import SaveData, Sound
        self.save = SaveData()
        self.save.readonly = smoke
        self.sound = Sound()
        self.sound.enabled = bool(self.save.data["settings"].get("sound", True))
        if self.sound.enabled and not smoke:
            self.sound.prepare()

        self.state = "menu"
        self.match = None
        self.results = None
        self.paused = False
        self.menu_sel = 0
        self.hero_sel = HERO_ORDER.index(self.save.data.get("selected", "volt"))
        self.selected = HERO_ORDER[self.hero_sel]
        self.mode = self.save.data.get("mode", "skirmish")
        if self.mode not in MODES:
            self.mode = "skirmish"
        self.keys = set()
        self.mouse = (VW // 2, VH // 2)
        self.fire_held = False
        self.hotspots = []
        self._cursor = ""
        self.time = 0.0
        self.last = time.perf_counter()
        self.confirm_reset = 0.0
        self.toast = ""
        self.toast_t = 0.0
        self.bg_particles = [self._new_particle() for _ in range(52)]

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.canvas.bind("<FocusOut>", self.on_focus_out)
        self.canvas.bind("<FocusIn>", lambda e: self.canvas.focus_set())

        self.loop()

    # ------------------------------------------------------------ фон
    def _new_particle(self):
        return {
            "x": random.uniform(0, VW),
            "y": random.uniform(0, VH),
            "vy": random.uniform(-26, -8),
            "vx": random.uniform(-5, 5),
            "s": random.uniform(1, 3),
            "c": random.choice((CYAN, BLUE, VIOLET, MAGENTA, GOLD)),
            "a": random.uniform(0.2, 0.8),
        }

    def update_bg(self, dt):
        for p in self.bg_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] < -10:
                p.update(self._new_particle())
                p["y"] = VH + 10

    def draw_bg(self, t=None):
        c = self.canvas
        t = self.time if t is None else t
        c.create_rectangle(0, 0, VW, VH, fill=BG, outline="")
        bands = 16
        for i in range(bands):
            col = mix("#060c17", "#0b1a30", i / (bands - 1))
            c.create_rectangle(0, i * VH / bands, VW, (i + 1) * VH / bands + 1,
                               fill=col, outline="")
        for x in range(0, VW + 1, 64):
            c.create_line(x, 0, x, VH, fill="#0a1729")
        for y in range(0, VH + 1, 64):
            c.create_line(0, y, VW, y, fill="#0a1729")
        for ox, oy, r, col in ((150, 640, 260, "#123a5e"),
                               (1130, 160, 310, "#3b1140"),
                               (760, 720, 220, "#0b3a36")):
            for i in range(4):
                rr = r - i * 38
                c.create_oval(ox - rr, oy - rr, ox + rr, oy + rr,
                              outline=mix(BG, col, 0.12 + i * 0.08), width=2)
        # диагональные акценты
        c.create_polygon([VW - 390, 0, VW - 280, 0, VW - 60, VH, VW - 170, VH],
                         fill="#071426", stipple="gray25", outline="")
        c.create_polygon([VW - 250, 0, VW - 232, 0, VW - 20, VH, VW - 38, VH],
                         fill=CYAN, stipple="gray12", outline="")
        for p in self.bg_particles:
            s = p["s"]
            col = mix(p["c"], BG, 1.0 - p["a"] * 0.75)
            c.create_oval(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s,
                          fill=col, outline="")
        c.create_rectangle(0, VH - 2, VW, VH, fill="#0c2037", outline="")

    # ------------------------------------------------------------ кнопки
    def hot(self, x1, y1, x2, y2):
        return point_in_rect(self.mouse[0], self.mouse[1],
                             (x1, y1, x2 - x1, y2 - y1))

    def add_hotspot(self, x1, y1, x2, y2, action):
        self.hotspots.append((x1, y1, x2, y2, action))

    def button(self, x1, y1, x2, y2, label, action, style="ghost",
               accent=CYAN, selected=False, sub=None, hotkey=None,
               enabled=True):
        c = self.canvas
        hover = enabled and self.hot(x1, y1, x2, y2)
        if style == "primary":
            base = accent if not hover else mix(accent, "#ffffff", 0.15)
            fill, outline, fg = base, mix(accent, "#ffffff", 0.3), "#031019"
            if not enabled:
                fill, outline, fg = "#162233", LINE, DIM
            rrect(c, x1 - 3, y1 - 3, x2 + 3, y2 + 3, 12,
                  fill=mix(accent, BG, 0.55), outline="")
            rrect(c, x1, y1, x2, y2, 10, fill=fill, outline=outline, width=2)
            c.create_polygon([x1 + 12, y2 - 1, x2 - 12, y2 - 1,
                              x2 - 20, y2 + 5, x1 + 20, y2 + 5],
                             fill=mix(accent, BG, 0.35), outline="")
        elif style == "tab":
            active = selected
            fill = mix(BG, accent, 0.18) if active else PANEL
            outline = accent if active else LINE
            fg = TEXT if active else MUTED
            rrect(c, x1, y1, x2, y2, 9, fill=fill, outline=outline,
                  width=2 if active else 1)
        else:
            fill = mix(BG, accent, 0.10) if hover else PANEL
            outline = accent if (hover or selected) else LINE
            fg = TEXT if (hover or selected) else MUTED
            rrect(c, x1, y1, x2, y2, 9, fill=fill, outline=outline,
                  width=2 if (hover or selected) else 1)
        if selected and style != "tab":
            rrect(c, x1 - 5, y1 + 8, x1 - 2, y2 - 8, 1, fill=accent, outline="")
        cy = (y1 + y2) / 2
        if sub:
            c.create_text((x1 + x2) / 2, cy - 9, text=label,
                          font=(F_TITLE, 15), fill=fg)
            c.create_text((x1 + x2) / 2, cy + 10, text=sub,
                          font=(F_UI, 8), fill=mix(fg, BG, 0.3))
        else:
            c.create_text((x1 + x2) / 2, cy, text=label,
                          font=(F_TITLE, 15 if style == "primary" else 12),
                          fill=fg)
        if hotkey:
            c.create_text(x2 - 12, cy, text=hotkey, anchor="e",
                          font=(F_UI, 8), fill=mix(fg, BG, 0.35))
        if enabled and action:
            self.add_hotspot(x1, y1, x2, y2, action)
        return hover

    def toast_message(self, text, seconds=1.8):
        self.toast = text
        self.toast_t = seconds

    # ------------------------------------------------------------ меню
    def draw_menu(self):
        c = self.canvas
        self.draw_bg()
        c.create_text(72, 106, text="НЕОНОВАЯ АРЕНА · 3 × 3",
                      anchor="w", font=(F_UI, 10, "bold"), fill=CYAN)
        text_glow(c, 70, 177, "NEON", (F_TITLE, 82), CYAN,
                  anchor="w", glow="#0a414d", off=3)
        text_glow(c, 70, 260, "BRAWL", (F_TITLE, 82), MAGENTA,
                  anchor="w", glow="#421035", off=3)
        c.create_line(74, 314, 470, 314, fill=mix(CYAN, BG, 0.45), width=2)
        c.create_text(76, 340, text="Шесть бойцов. Две команды. Одна арена.",
                      anchor="w", font=(F_UI, 11), fill=MUTED)
        chips = [
            ("КУБКИ", str(self.save.total_trophies()), GOLD),
            ("МАТЧИ", str(self.save.data.get("matches", 0)), CYAN),
            ("ПОБЕДЫ", str(self.save.data.get("wins", 0)), GREEN),
        ]
        x = 76
        for label, value, col in chips:
            rrect(c, x, 360, x + 105, 386, 7, fill=PANEL, outline=LINE)
            c.create_text(x + 9, 373, text=label, anchor="w",
                          font=(F_UI, 7, "bold"), fill=MUTED)
            c.create_text(x + 96, 373, text=value, anchor="e",
                          font=(F_TITLE, 12), fill=col)
            x += 114

        actions = [
            ("ИГРАТЬ", self.open_select, "primary", "ВЫБРАТЬ БОЙЦА И РЕЖИМ"),
            ("КАК ИГРАТЬ", self.open_help, "ghost", "УПРАВЛЕНИЕ И ПРАВИЛА"),
            ("НАСТРОЙКИ", self.open_settings, "ghost", "ЗВУК · ЭФФЕКТЫ · СЛОЖНОСТЬ"),
            ("ВЫХОД", self.quit, "ghost", "ЗАКРЫТЬ АРЕНУ"),
        ]
        for i, (label, action, style, sub) in enumerate(actions):
            y = 410 + i * 66
            self.button(70, y, 390, y + 54, label, action, style,
                        selected=(self.menu_sel == i), sub=sub)

        # герой на подиуме
        hero = HEROES[self.selected]
        cx, cy = 965, 455
        for r, a in ((250, 0.13), (210, 0.16), (170, 0.20)):
            c.create_oval(cx - r, cy - r * 0.94, cx + r, cy + r * 0.94,
                          outline=mix(BG, hero["color"], a), width=2)
        c.create_polygon([cx - 120, 692, cx - 82, 662, cx + 82, 662,
                          cx + 120, 692, cx + 82, 722, cx - 82, 722],
                         fill="#0b1727", outline=mix(hero["color"], BG, 0.35),
                         width=2)
        draw_hero_full(c, cx, 470, 1.48, hero, self.time)
        text_glow(c, cx, 748, hero["name"], (F_TITLE, 30), hero["light"],
                  off=2)
        c.create_text(cx, 773, text=hero["role"] + " · " + hero["tag"],
                      font=(F_UI, 9, "bold"), fill=MUTED)
        stats = self.save.hero(self.selected)
        trophy(c, cx - 54, 792, 7)
        c.create_text(cx - 42, 793, text=str(stats["trophies"]), anchor="w",
                      font=(F_TITLE, 11), fill=GOLD)
        c.create_text(cx + 18, 793, text="· %d ПОБЕД" % stats["wins"],
                      font=(F_UI, 8), fill=MUTED)
        if self.hot(760, 260, 1180, 800):
            self.add_hotspot(760, 260, 1180, 800, self.open_select)
        c.create_text(72, VH - 24, text="ESC — выход   ·   M — звук   ·   v%s" % VERSION,
                      anchor="w", font=(F_UI, 8), fill=DIM)
        c.create_text(VW - 30, VH - 24, text="ВДОХНОВЛЕНО ЖАНРОМ АРЕНА-ШУТЕРОВ",
                      anchor="e", font=(F_UI, 7), fill=DIM)
        if self.toast_t > 0:
            c.create_text(VW / 2, 60, text=self.toast,
                          font=(F_UI, 10, "bold"), fill=CYAN)

    # ------------------------------------------------------------ выбор бойца
    def draw_select(self):
        c = self.canvas
        self.draw_bg()
        self.button(28, 24, 72, 64, "←", self.go_menu, "ghost")
        c.create_text(92, 32, text="БОЙЦЫ", anchor="w",
                      font=(F_TITLE, 24), fill=TEXT)
        c.create_text(92, 56, text="ВЫБЕРИТЕ ГЕРОЯ И РЕЖИМ",
                      anchor="w", font=(F_UI, 8, "bold"), fill=MUTED)
        trophy(c, VW - 160, 36, 9)
        c.create_text(VW - 146, 37, text=str(self.save.total_trophies()),
                      anchor="w", font=(F_TITLE, 14), fill=GOLD)
        c.create_text(VW - 30, 37, text="КУБКИ", anchor="e",
                      font=(F_UI, 8, "bold"), fill=MUTED)

        # карточки
        for i, hid in enumerate(HERO_ORDER):
            col = i % 3
            row = i // 3
            x = 40 + col * 260
            y = 100 + row * 222
            self.draw_hero_card(x, y, 240, 200, HEROES[hid], i == self.hero_sel)
        c.create_text(40, 558, text="← ↑ → ↓ — выбор   ·   ENTER — в бой   ·   TAB — режим   ·   1–6 — быстрый выбор",
                      anchor="w", font=(F_UI, 9), fill=MUTED)

        # панель справа
        px, py, pw = 828, 92, 412
        rrect(c, px, py, px + pw, 790, 14, fill=PANEL, outline=LINE, width=1)
        c.create_text(px + 18, py + 20, text="РЕЖИМ", anchor="w",
                      font=(F_UI, 8, "bold"), fill=MUTED)
        for j, key in enumerate(("skirmish", "gems")):
            self.button(px + 18 + j * 190, py + 34,
                        px + 18 + j * 190 + 180, py + 76,
                        MODES[key]["name"], lambda k=key: self.set_mode(k),
                        "tab", accent=CYAN if key == "skirmish" else VIOLET,
                        selected=(self.mode == key))
        c.create_text(px + 18, py + 94, text=MODES[self.mode]["desc"],
                      anchor="nw", width=pw - 36, font=(F_UI, 9), fill=MUTED)
        hero = HEROES[self.selected]
        draw_hero_bust(c, px + pw / 2, py + 212, 0.94, hero, self.time)
        text_glow(c, px + pw / 2, py + 338, hero["name"],
                  (F_TITLE, 26), hero["light"], off=2)
        c.create_text(px + pw / 2, py + 360, text=hero["role"] + " · " + hero["tag"],
                      font=(F_UI, 8, "bold"), fill=MUTED)
        trophy(c, px + pw / 2 - 22, py + 378, 7)
        c.create_text(px + pw / 2 - 10, py + 379,
                      text=str(self.save.hero(self.selected)["trophies"]),
                      anchor="w", font=(F_UI, 9, "bold"), fill=GOLD)
        self.draw_stats(px + 18, py + 400, pw - 36, hero)
        c.create_text(px + 18, py + 464, anchor="nw", width=pw - 36,
                      text='«%s»' % hero["quote"],
                      font=(F_UI, 9, "italic"), fill=mix(hero["color"], TEXT, 0.35))
        c.create_text(px + 18, py + 486, anchor="nw", width=pw - 36,
                      text=hero["desc"], font=(F_UI, 8), fill=MUTED)
        c.create_text(px + 18, py + 526, text="СУПЕР · " + hero["super_name"],
                      anchor="w", font=(F_UI, 9, "bold"), fill=hero["color"])
        c.create_text(px + 18, py + 544, anchor="nw", width=pw - 36,
                      text=hero["super_desc"], font=(F_UI, 8), fill=MUTED)
        c.create_text(px + 18, py + 582, text="ГАДЖЕТ · " + hero["gadget_name"],
                      anchor="w", font=(F_UI, 9, "bold"), fill=GOLD)
        c.create_text(px + 18, py + 600, anchor="nw", width=pw - 36,
                      text=hero["gadget_desc"], font=(F_UI, 8), fill=MUTED)
        self.button(px + 18, py + 634, px + pw - 18, py + 676,
                    "В БОЙ  →", self.start_match, "primary")

    def draw_hero_card(self, x, y, w, h, hero, selected):
        c = self.canvas
        hover = self.hot(x, y, x + w, y + h)
        accent = hero["color"]
        fill = mix(BG, accent, 0.10 if hover else 0.04)
        outline = accent if (selected or hover) else LINE
        rrect(c, x, y, x + w, y + h, 12, fill=fill, outline=outline,
              width=2 if selected else 1)
        if selected:
            rrect(c, x - 5, y + 18, x - 1, y + h - 18, 2,
                  fill=accent, outline="")
        rrect(c, x + 8, y + 8, x + 112, y + h - 8, 9,
              fill=mix(BG, accent, 0.12), outline=mix(accent, BG, 0.45))
        draw_hero_bust(c, x + 60, y + h / 2 + 8, 0.60, hero, self.time,
                       glow=False)
        c.create_text(x + 124, y + 26, text=hero["name"], anchor="w",
                      font=(F_TITLE, 16), fill=hero["light"])
        c.create_text(x + 124, y + 45, text=hero["role"], anchor="w",
                      font=(F_UI, 7, "bold"), fill=MUTED)
        trophy(c, x + 130, y + 62, 5)
        c.create_text(x + 139, y + 63,
                      text=str(self.save.hero(hero["id"])["trophies"]),
                      anchor="w", font=(F_UI, 8), fill=GOLD)
        for j, (label, value) in enumerate(zip(
                ("УРОН", "БРОНЯ", "СКОР."), hero["stats"])):
            yy = y + 92 + j * 23
            c.create_text(x + 124, yy, text=label, anchor="w",
                          font=(F_UI, 6, "bold"), fill=DIM)
            for k in range(5):
                bx = x + 160 + k * 14
                col = accent if k < value else "#16233a"
                rrect(c, bx, yy - 4, bx + 10, yy + 2, 2, fill=col, outline="")
        c.create_text(x + 124, y + h - 22, text=hero["tag"], anchor="w",
                      font=(F_UI, 7, "bold"), fill=mix(accent, TEXT, 0.2))
        self.add_hotspot(x, y, x + w, y + h,
                         lambda i=HERO_ORDER.index(hero["id"]): self.pick_hero(i))

    def draw_stats(self, x, y, w, hero):
        c = self.canvas
        labels = ("УРОН", "БРОНЯ", "СКОРОСТЬ")
        for i, (label, value) in enumerate(zip(labels, hero["stats"])):
            yy = y + i * 22
            c.create_text(x, yy, text=label, anchor="w",
                          font=(F_UI, 7, "bold"), fill=MUTED)
            bar(c, x + 78, yy - 5, w - 110, 9, value / 5.0, hero["color"],
                back="#111c2e", radius=4)
            c.create_text(x + w, yy, text="%d/5" % value, anchor="e",
                          font=(F_UI, 7, "bold"), fill=DIM)

    # ------------------------------------------------------------ справка
    def draw_help(self):
        c = self.canvas
        self.draw_bg()
        self.button(28, 24, 72, 64, "←", self.go_menu, "ghost")
        c.create_text(92, 32, text="КАК ИГРАТЬ", anchor="w",
                      font=(F_TITLE, 24), fill=TEXT)
        c.create_text(92, 56, text="ПЯТЬ МИНУТ — И ТЫ В ДЕЛЕ",
                      anchor="w", font=(F_UI, 8, "bold"), fill=MUTED)

        rrect(c, 60, 100, 610, 740, 14, fill=PANEL, outline=LINE)
        c.create_text(84, 124, text="УПРАВЛЕНИЕ", anchor="w",
                      font=(F_TITLE, 16), fill=CYAN)
        controls = [
            ("W A S D / ← ↑ → ↓", "движение по арене"),
            ("МЫШЬ", "прицел и направление выстрела"),
            ("ЛКМ", "огонь (можно удерживать)"),
            ("ПКМ / ПРОБЕЛ", "суперспособность, когда шкала полна"),
            ("E", "гаджет — два заряда на матч"),
            ("ESC", "пауза и выход в меню"),
            ("M", "включить или выключить звук"),
        ]
        for i, (key, text) in enumerate(controls):
            y = 164 + i * 48
            rrect(c, 84, y, 286, y + 32, 7, fill=PANEL2, outline=LINE)
            c.create_text(185, y + 16, text=key, font=(F_UI, 9, "bold"),
                          fill=TEXT)
            c.create_text(306, y + 16, text=text, anchor="w",
                          font=(F_UI, 9), fill=MUTED)
        c.create_text(84, 520, text="ПРАВИЛА", anchor="w",
                      font=(F_TITLE, 16), fill=CYAN)
        tips = [
            "• Боты не видят вас в кустах, пока вы не выстрелите.",
            "• Лечение начинается само, если 4 секунды не получать урон.",
            "• Заряжайте супер уроном: чем больше попаданий, тем быстрее.",
            "• Патроны не бесконечны. Используйте укрытия для перезарядки.",
            "• После смерти вы возвращаетесь через 4 секунды.",
        ]
        for i, line in enumerate(tips):
            c.create_text(84, 554 + i * 26, text=line, anchor="w",
                          font=(F_UI, 9), fill=MUTED)
        c.create_text(84, 706, text="ЦЕЛЬ МАТЧА", anchor="w",
                      font=(F_UI, 8, "bold"), fill=GOLD)
        c.create_text(84, 724, text="Побеждает команда, которая выполнит задачу режима.",
                      anchor="w", font=(F_UI, 8), fill=MUTED)

        rrect(c, 630, 100, 1220, 740, 14, fill=PANEL, outline=LINE)
        c.create_text(654, 124, text="РЕЖИМЫ", anchor="w",
                      font=(F_TITLE, 16), fill=MAGENTA)
        y = 170
        for key in ("skirmish", "gems"):
            mode = MODES[key]
            rrect(c, 654, y, 1196, y + 92, 10, fill=PANEL2, outline=LINE)
            c.create_text(674, y + 24, text=mode["name"], anchor="w",
                          font=(F_TITLE, 14), fill=CYAN if key == "skirmish" else VIOLET)
            c.create_text(674, y + 46, text=mode["rule"], anchor="w",
                          font=(F_UI, 8, "bold"), fill=MUTED)
            c.create_text(674, y + 66, text=mode["desc"], anchor="w",
                          width=490, font=(F_UI, 8), fill=MUTED)
            y += 106
        c.create_text(654, 390, text="БОЙЦЫ", anchor="w",
                      font=(F_TITLE, 16), fill=GOLD)
        x = 664
        for hid in HERO_ORDER:
            hero = HEROES[hid]
            hero_icon(c, x, 446, 28, hero)
            c.create_text(x, 486, text=hero["name"], font=(F_UI, 7, "bold"),
                          fill=hero["light"])
            x += 88
        c.create_text(654, 526, text="СОВЕТЫ", anchor="w",
                      font=(F_TITLE, 16), fill=GREEN)
        tips2 = [
            "Стреляйте с упреждением — снаряды летят не мгновенно.",
            "Не стойте на линии огня союзника: стены спасают не всегда.",
            "Супер лучше приберечь для решающей стычки.",
            "В «Кристаллах» носите не больше 10: лишние кристаллы — риск.",
            "Сложность ботов меняется в настройках.",
        ]
        for i, line in enumerate(tips2):
            c.create_text(654, 560 + i * 25, text="• " + line, anchor="w",
                          font=(F_UI, 8), fill=MUTED)
        c.create_text(654, 706, text="ПОДСКАЗКА: наведите мышь на бойца, чтобы увидеть его роль.",
                      anchor="w", font=(F_UI, 8), fill=DIM)
        self.button(VW - 230, 744, VW - 40, 786, "ПОНЯТНО", self.go_menu,
                    "primary")

    # ------------------------------------------------------------ настройки
    def draw_settings(self):
        c = self.canvas
        self.draw_bg()
        self.button(28, 24, 72, 64, "←", self.go_menu, "ghost")
        c.create_text(92, 32, text="НАСТРОЙКИ", anchor="w",
                      font=(F_TITLE, 24), fill=TEXT)
        c.create_text(92, 56, text="ВСЁ СОХРАНЯЕТСЯ АВТОМАТИЧЕСКИ",
                      anchor="w", font=(F_UI, 8, "bold"), fill=MUTED)
        s = self.save.data["settings"]
        rrect(c, 220, 100, 1060, 700, 16, fill=PANEL, outline=LINE)
        rows = [
            ("ЗВУК", "Короткие синтезированные сигналы боя", "sound"),
            ("ЧАСТИЦЫ", "Искры, взрывы и следы снарядов", "particles"),
            ("ТРЯСКА ЭКРАНА", "Отдача от выстрелов и взрывов", "shake"),
        ]
        for i, (title, desc, key) in enumerate(rows):
            y = 126 + i * 86
            c.create_text(252, y, text=title, anchor="w",
                          font=(F_TITLE, 14), fill=TEXT)
            c.create_text(252, y + 24, text=desc, anchor="w",
                          font=(F_UI, 8), fill=MUTED)
            on = bool(s.get(key, True))
            self.draw_toggle(936, y - 12, on,
                             lambda k=key: self.toggle_setting(k))
            c.create_line(252, y + 54, 1028, y + 54, fill=LINE)
        y = 126 + 3 * 86
        c.create_text(252, y, text="СЛОЖНОСТЬ БОТОВ", anchor="w",
                      font=(F_TITLE, 14), fill=TEXT)
        c.create_text(252, y + 24, text="Влияет на меткость, реакцию и урон ИИ",
                      anchor="w", font=(F_UI, 8), fill=MUTED)
        for i, d in enumerate(DIFFICULTIES):
            self.button(724 + i * 104, y - 12, 820 + i * 104, y + 22, d,
                        lambda dd=d: self.set_difficulty(dd), "tab",
                        accent=GREEN, selected=(s.get("difficulty") == d))
        c.create_line(252, y + 54, 1028, y + 54, fill=LINE)

        y = 126 + 4 * 86
        c.create_text(252, y, text="ПРОГРЕСС", anchor="w",
                      font=(F_TITLE, 14), fill=TEXT)
        c.create_text(252, y + 24,
                      text="Кубков: %d   ·   Матчей: %d   ·   Побед: %d" %
                      (self.save.total_trophies(),
                       self.save.data.get("matches", 0),
                       self.save.data.get("wins", 0)),
                      anchor="w", font=(F_UI, 8), fill=MUTED)
        armed = self.confirm_reset > 0
        self.button(824, y - 12, 1028, y + 24,
                    "ТОЧНО СБРОСИТЬ?" if armed else "СБРОСИТЬ ПРОГРЕСС",
                    self.ask_reset, "ghost",
                    accent=RED if armed else CYAN)
        c.create_line(252, y + 54, 1028, y + 54, fill=LINE)

        y = 126 + 5 * 86
        c.create_text(252, y, text="СЛУЖЕБНОЕ", anchor="w",
                      font=(F_TITLE, 14), fill=TEXT)
        c.create_text(252, y + 24, text="Файл сохранения: " +
                      self.save.path, anchor="w",
                      font=(F_UI, 8), fill=DIM)
        c.create_text(252, y + 44, text="Версия %s · сделано на tkinter, без внешних библиотек" %
                      VERSION, anchor="w", font=(F_UI, 8), fill=DIM)
        self.button(VW - 230, 722, VW - 40, 764, "ГОТОВО", self.go_menu,
                    "primary")
        c.create_text(64, 748, text="ESC — назад",
                      font=(F_UI, 9), fill=MUTED)

    def draw_toggle(self, x, y, on, action):
        c = self.canvas
        hover = self.hot(x, y, x + 92, y + 34)
        track = mix(CYAN, BG, 0.25) if on else "#182536"
        outline = CYAN if on else LINE
        if hover:
            outline = mix(outline, "#ffffff", 0.25)
        rrect(c, x, y, x + 92, y + 34, 17, fill=track, outline=outline,
              width=2)
        knob_x = x + 73 if on else x + 19
        c.create_oval(knob_x - 12, y + 5, knob_x + 12, y + 29,
                      fill="#ffffff" if on else "#4f6483", outline="")
        c.create_text(x + (20 if on else 58), y + 17,
                      text="ВКЛ" if on else "ВЫКЛ",
                      font=(F_UI, 7, "bold"),
                      fill="#03202a" if on else MUTED)
        self.add_hotspot(x, y, x + 92, y + 34, action)

    # ------------------------------------------------------------ результаты
    def draw_results(self):
        c = self.canvas
        res = self.results or {}
        self.draw_bg()
        result = res.get("result", "win")
        titles = {"win": ("ПОБЕДА", CYAN), "lose": ("ПОРАЖЕНИЕ", RED),
                  "draw": ("НИЧЬЯ", GOLD)}
        title, col = titles.get(result, titles["win"])
        hero = HEROES.get(res.get("hero", self.selected), HEROES[self.selected])
        text_glow(c, VW / 2, 82, title, (F_TITLE, 52), col, off=3)
        c.create_text(VW / 2, 124, text=res.get("mode_name", "") + " · " + res.get("reason", ""),
                      font=(F_UI, 9, "bold"), fill=MUTED)
        rrect(c, 160, 152, 1120, 684, 18, fill=PANEL, outline=LINE)
        draw_hero_bust(c, 330, 360, 1.18, hero, self.time)
        text_glow(c, 330, 530, hero["name"], (F_TITLE, 24), hero["light"], off=2)
        c.create_text(330, 556, text=hero["role"], font=(F_UI, 8, "bold"),
                      fill=MUTED)
        trophy(c, 294, 582, 8)
        c.create_text(308, 583, text=str(res.get("trophies", 0)),
                      anchor="w", font=(F_TITLE, 14), fill=GOLD)
        delta = res.get("delta", 0)
        dcol = GREEN if delta > 0 else RED if delta < 0 else MUTED
        c.create_text(386, 583, text="%+d" % delta if delta else "±0",
                      anchor="w", font=(F_TITLE, 14), fill=dcol)
        matches = self.save.data.get("matches", 0)
        wins = self.save.data.get("wins", 0)
        c.create_text(330, 622,
                      text="%d %s · %d %s" % (
                          matches, plural(matches, "матч", "матча", "матчей"),
                          wins, plural(wins, "победа", "победы", "побед")),
                      font=(F_UI, 8), fill=DIM)
        c.create_line(520, 188, 520, 650, fill=LINE)

        c.create_text(760, 206, text="СЧЁТ", font=(F_UI, 8, "bold"), fill=MUTED)
        c.create_text(680, 258, text=str(res.get("score0", 0)),
                      font=(F_TITLE, 46), fill=TEAM_COLORS[0]["light"])
        c.create_text(840, 258, text=str(res.get("score1", 0)),
                      font=(F_TITLE, 46), fill=TEAM_COLORS[1]["light"])
        c.create_oval(755, 243, 765, 253, fill=MUTED, outline="")
        c.create_oval(755, 265, 765, 275, fill=MUTED, outline="")
        c.create_text(680, 296, text="ВЫ", font=(F_UI, 8, "bold"),
                      fill=TEAM_COLORS[0]["main"])
        c.create_text(840, 296, text="ВРАГИ", font=(F_UI, 8, "bold"),
                      fill=TEAM_COLORS[1]["main"])
        stats = [
            ("УБИЙСТВА", str(res.get("kills", 0)), CYAN),
            ("СМЕРТИ", str(res.get("deaths", 0)), RED),
            ("УРОН", str(res.get("damage", 0)), GOLD),
            ("КРИСТАЛЛЫ", str(res.get("gems", 0)), VIOLET),
            ("СУПЕРЫ", str(res.get("supers", 0)), GREEN),
            ("КУБКИ", str(res.get("trophies", 0)), GOLD),
        ]
        for i, (label, value, color) in enumerate(stats):
            sx = 560 + (i % 2) * 270
            sy = 340 + (i // 2) * 82
            rrect(c, sx, sy, sx + 250, sy + 66, 9, fill=PANEL2, outline=LINE)
            c.create_text(sx + 16, sy + 20, text=label, anchor="w",
                          font=(F_UI, 7, "bold"), fill=MUTED)
            c.create_text(sx + 16, sy + 45, text=value, anchor="w",
                          font=(F_TITLE, 20), fill=color)
        c.create_text(760, 620, text="ЛУЧШИЙ МОМЕНТ: %s" % res.get("best", "отличная игра"),
                      font=(F_UI, 8), fill=DIM)
        self.button(560, 714, 760, 760, "ЕЩЁ РАЗ", self.rematch, "primary")
        self.button(780, 714, 980, 760, "В МЕНЮ", self.go_menu, "ghost")
        c.create_text(760, 778, text="ENTER — ещё раз   ·   ESC — в меню",
                      font=(F_UI, 8), fill=DIM)

    # ------------------------------------------------------------ пауза
    def draw_pause(self):
        c = self.canvas
        if not self.match:
            return
        c.create_rectangle(0, 0, VW, VH, fill="#02050c", stipple="gray50",
                           outline="")
        rrect(c, 410, 220, 870, 610, 18, fill=PANEL, outline=LINE, width=2)
        text_glow(c, 640, 276, "ПАУЗА", (F_TITLE, 40), CYAN, off=3)
        c.create_text(640, 318, text="МАТЧ ПРИОСТАНОВЛЕН",
                      font=(F_UI, 8, "bold"), fill=MUTED)
        c.create_text(640, 356, text="%s · %s" %
                      (MODES[self.match.mode]["name"], fmt_time(self.match.time_left)),
                      font=(F_UI, 10, "bold"), fill=TEXT)
        self.button(470, 396, 810, 444, "ПРОДОЛЖИТЬ", self.resume_match,
                    "primary")
        self.button(470, 458, 810, 502, "В МЕНЮ (МАТЧ НЕ ЗАСЧИТАЕТСЯ)",
                    self.abandon_match, "ghost")
        c.create_text(640, 540, text="ESC — продолжить",
                      font=(F_UI, 9), fill=MUTED)
        c.create_text(640, 570, text="WASD — движение   ·   ЛКМ — огонь   ·   ПКМ/SPACE — супер   ·   E — гаджет",
                      font=(F_UI, 8), fill=DIM)

    # ------------------------------------------------------------ отрисовка
    def draw(self):
        c = self.canvas
        c.delete("all")
        self.hotspots = []
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "select":
            self.draw_select()
        elif self.state == "help":
            self.draw_help()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "match":
            if self.match:
                self.match.draw(c)
                if self.paused:
                    self.draw_pause()
        elif self.state == "results":
            self.draw_results()
        if self.toast_t > 0:
            rrect(c, VW / 2 - 150, 12, VW / 2 + 150, 42, 8,
                  fill="#071726", outline=CYAN)
            c.create_text(VW / 2, 27, text=self.toast,
                          font=(F_UI, 9, "bold"), fill=CYAN)
        self.update_cursor()

    def update_cursor(self):
        if self.state == "match" and not self.paused:
            cur = "crosshair"
        elif any(point_in_rect(self.mouse[0], self.mouse[1],
                               (x1, y1, x2 - x1, y2 - y1))
                 for x1, y1, x2, y2, _ in self.hotspots):
            cur = "hand2"
        else:
            cur = "arrow"
        if cur != self._cursor:
            self._cursor = cur
            try:
                self.canvas.config(cursor=cur)
            except Exception:
                pass

    # ------------------------------------------------------------ переходы
    def open_select(self):
        self.state = "select"
        self.hero_sel = HERO_ORDER.index(self.selected)
        self.fire_held = False

    def open_help(self):
        self.state = "help"
        self.fire_held = False

    def open_settings(self):
        self.state = "settings"
        self.fire_held = False

    def go_menu(self):
        self.state = "menu"
        self.match = None
        self.paused = False
        self.fire_held = False
        self.keys.clear()
        self.save.data["selected"] = self.selected
        self.save.data["mode"] = self.mode
        self.save.save()

    def pick_hero(self, index):
        self.hero_sel = index % len(HERO_ORDER)
        self.selected = HERO_ORDER[self.hero_sel]
        self.save.data["selected"] = self.selected
        self.save.save()
        self.sound.play("click")

    def set_mode(self, mode):
        if mode in MODES:
            self.mode = mode
            self.save.data["mode"] = mode
            self.save.save()
            self.sound.play("click")

    def toggle_setting(self, key):
        s = self.save.data["settings"]
        s[key] = not bool(s.get(key, True))
        if key == "sound":
            self.sound.enabled = bool(s[key])
            if self.sound.enabled:
                self.sound.prepare()
        self.save.save()
        self.toast_message(("ВКЛЮЧЕНО" if s[key] else "ВЫКЛЮЧЕНО") +
                           " · " + key.upper())

    def set_difficulty(self, diff):
        if diff in DIFFICULTIES:
            self.save.data["settings"]["difficulty"] = diff
            self.save.save()
            self.sound.play("click")

    def ask_reset(self):
        if self.confirm_reset > 0:
            for hid in HERO_ORDER:
                self.save.data["heroes"][hid] = {
                    "trophies": 0, "wins": 0, "kills": 0}
            self.save.data["matches"] = 0
            self.save.data["wins"] = 0
            self.save.save()
            self.confirm_reset = 0.0
            self.toast_message("ПРОГРЕСС СБРОШЕН")
        else:
            self.confirm_reset = 4.0
            self.toast_message("НАЖМИТЕ ЕЩЁ РАЗ ДЛЯ СБРОСА")

    def start_match(self):
        self.save.data["selected"] = self.selected
        self.save.data["mode"] = self.mode
        self.save.save()
        self.match = Match(self, self.selected, self.mode)
        self.state = "match"
        self.paused = False
        self.fire_held = False
        self.keys.clear()
        self.results = None

    def finish_match(self):
        m = self.match
        if not m or m.recorded:
            return
        if m.result == "win":
            won = True
        elif m.result == "lose":
            won = False
        else:
            won = None
        delta = self.save.record_match(self.selected, won, m.player.kills)
        score0 = (m.team_kills[0] if m.mode == "skirmish"
                  else m.team_gems(0))
        score1 = (m.team_kills[1] if m.mode == "skirmish"
                  else m.team_gems(1))
        self.results = {
            "result": m.result,
            "mode_name": MODES[m.mode]["name"],
            "reason": m.reason,
            "hero": self.selected,
            "kills": m.player.kills,
            "deaths": m.player.deaths,
            "damage": int(m.player.damage_done),
            "gems": m.player.gems_collected,
            "supers": m.player.supers_used,
            "score0": score0,
            "score1": score1,
            "delta": delta,
            "trophies": self.save.hero(self.selected)["trophies"],
            "best": ("без потерь" if m.player.deaths == 0 else
                     "точный супер" if m.player.supers_used else
                     "хорошая командная игра"),
        }
        m.recorded = True
        self.state = "results"
        self.paused = False
        self.fire_held = False

    def rematch(self):
        self.start_match()

    def resume_match(self):
        self.paused = False
        self.fire_held = False
        self.keys.clear()
        self.canvas.focus_set()

    def abandon_match(self):
        self.match = None
        self.paused = False
        self.fire_held = False
        self.keys.clear()
        self.state = "menu"

    def quit(self):
        try:
            self.save.data["selected"] = self.selected
            self.save.data["mode"] = self.mode
            self.save.save()
        except Exception:
            pass
        self.root.destroy()

    # ------------------------------------------------------------ ввод
    def normalize_key(self, keysym):
        s = keysym.lower()
        table = {
            "left": "left", "right": "right", "up": "up", "down": "down",
            "cyrillic_ef": "a", "cyrillic_ve": "d",
            "cyrillic_yeru": "s", "cyrillic_tse": "w",
            "cyrillic_u": "e", "cyrillic_soft_sign": "m",
            "ф": "a", "в": "d", "ы": "s", "ц": "w",
            "у": "e", "ь": "m",
            "return": "return", "kp_enter": "return",
            "space": "space", "escape": "escape", "tab": "tab",
        }
        return table.get(s, s)

    def on_key_press(self, event):
        sym = self.normalize_key(event.keysym)
        new = sym not in self.keys
        self.keys.add(sym)
        if sym == "m" and new:
            self.toggle_setting("sound")
            return "break"
        if self.state == "match":
            if self.paused:
                if sym == "escape":
                    self.resume_match()
                return "break"
            if sym == "escape":
                self.paused = True
                self.fire_held = False
                self.keys.clear()
                return "break"
            if sym == "space" and new:
                self.player_super()
                return "break"
            if sym == "e" and new:
                self.player_gadget()
                return "break"
            if sym in ("left", "a", "right", "d", "up", "w", "down", "s"):
                return "break"
            return
        if self.state == "menu":
            if sym in ("up", "w"):
                self.menu_sel = (self.menu_sel - 1) % 4
                self.sound.play("click")
            elif sym in ("down", "s"):
                self.menu_sel = (self.menu_sel + 1) % 4
                self.sound.play("click")
            elif sym in ("return", "space"):
                self.activate_menu()
            elif sym == "escape":
                self.quit()
            return "break"
        if self.state == "select":
            if sym in ("left", "a"):
                self.pick_hero(self.hero_sel - 1)
            elif sym in ("right", "d"):
                self.pick_hero(self.hero_sel + 1)
            elif sym in ("up", "w"):
                self.pick_hero((self.hero_sel - 3) % 6)
            elif sym in ("down", "s"):
                self.pick_hero((self.hero_sel + 3) % 6)
            elif sym in ("1", "2", "3", "4", "5", "6"):
                self.pick_hero(int(sym) - 1)
            elif sym == "tab":
                self.set_mode("gems" if self.mode == "skirmish" else "skirmish")
            elif sym in ("return", "space"):
                self.start_match()
            elif sym == "escape":
                self.go_menu()
            return "break"
        if self.state == "help":
            if sym in ("escape", "return", "space"):
                self.go_menu()
            return "break"
        if self.state == "settings":
            if sym in ("escape", "return"):
                self.go_menu()
            return "break"
        if self.state == "results":
            if sym in ("return", "space"):
                self.rematch()
            elif sym == "escape":
                self.go_menu()
            return "break"

    def on_key_release(self, event):
        self.keys.discard(self.normalize_key(event.keysym))

    def on_motion(self, event):
        self.mouse = (event.x, event.y)

    def on_click(self, event):
        self.mouse = (event.x, event.y)
        self.canvas.focus_set()
        if self.state == "match" and not self.paused and self.match:
            self.fire_held = True
            return
        for x1, y1, x2, y2, action in reversed(self.hotspots):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.sound.play("click")
                action()
                return

    def on_release(self, event):
        self.fire_held = False

    def on_right_click(self, event):
        self.mouse = (event.x, event.y)
        if self.state == "match" and not self.paused and self.match:
            self.player_super()
            return "break"

    def on_focus_out(self, event):
        self.keys.clear()
        self.fire_held = False
        if self.state == "match" and not self.paused and not self.smoke:
            self.paused = True

    def player_super(self):
        m = self.match
        if not m or m.finished or not m.player.alive:
            return
        wx = self.mouse[0] - 40
        wy = self.mouse[1] - 104
        m.use_super(m.player, m.player.aim, aim_point=(wx, wy))

    def player_gadget(self):
        m = self.match
        if not m or m.finished or not m.player.alive:
            return
        m.use_gadget(m.player, m.player.aim)

    def activate_menu(self):
        actions = (self.open_select, self.open_help, self.open_settings,
                   self.quit)
        actions[self.menu_sel % len(actions)]()

    # ------------------------------------------------------------ цикл
    def loop(self):
        try:
            now = time.perf_counter()
            dt = min(0.05, now - self.last)
            self.last = now
            self.time += dt
            self.update_bg(dt)
            if self.toast_t > 0:
                self.toast_t -= dt
            if self.confirm_reset > 0:
                self.confirm_reset -= dt
            if self.state == "match" and not self.paused and self.match:
                self.match.update(dt)
                if (self.match.finished and self.match.finished_t > 1.55
                        and not self.match.recorded):
                    self.finish_match()
            self.draw()
        except Exception:
            traceback.print_exc()
            try:
                self.root.after(500, self.loop)
            except Exception:
                pass
            return
        try:
            self.root.after(15, self.loop)
        except tk.TclError:
            pass


def run_smoke(app, root):
    try:
        app.start_match()
        app.match.intro = 0.0
        for _ in range(1500):
            app.match.update(1 / 60.0)
            if app.match.finished:
                break
        app.draw()
        m = app.match
        print("SMOKE skirmish:", "finished=%s" % m.finished,
              "t=%.1f" % m.t, "kills=%s" % m.team_kills,
              "hp=%d" % m.player.hp, "bots=%d" % (len(m.brawlers) - 1))
        app.match = Match(app, "iskra", "gems")
        app.state = "match"
        app.paused = False
        app.match.intro = 0.0
        for _ in range(1500):
            app.match.update(1 / 60.0)
            if app.match.finished:
                break
        app.draw()
        m = app.match
        print("SMOKE gems:", "finished=%s" % m.finished,
              "t=%.1f" % m.t, "gems=%d:%d" % (m.team_gems(0), m.team_gems(1)),
              "hold=%.1f/%.1f" % (m.hold[0], m.hold[1]))
        print("SMOKE OK")
    except Exception:
        traceback.print_exc()
        print("SMOKE FAIL")
    root.destroy()


def main():
    smoke = "--smoke" in sys.argv
    try:
        root = tk.Tk()
    except Exception:
        traceback.print_exc()
        return 1
    app = App(root, smoke=smoke)
    if smoke:
        root.after(150, lambda: run_smoke(app, root))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())



