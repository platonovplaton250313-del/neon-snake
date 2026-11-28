#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEON BRAWL: данные игры, бойцы, сохранения и звук."""

import json
import math
import os
import random
import struct
import sys
import time

try:                     # звук есть только на Windows
    import winsound
except Exception:        # pragma: no cover
    winsound = None

# ---------------------------------------------------------------- экран
VW, VH = 1280, 800
AX, AY, AW, AH = 40, 104, 1200, 656
TITLE = "NEON BRAWL"
VERSION = "1.0"
F_TITLE = "Bahnschrift SemiBold"
F_UI = "Segoe UI"
F_MONO = "Consolas"

# ---------------------------------------------------------------- палитра
BG = "#050912"
BG2 = "#081322"
PANEL = "#0a1424"
PANEL2 = "#0e1c32"
LINE = "#1b3050"
TEXT = "#eaf7ff"
MUTED = "#7d93b5"
DIM = "#4b5f80"
CYAN = "#7ef9ff"
BLUE = "#42a5ff"
BLUE_D = "#123a66"
RED = "#ff4d6d"
RED_D = "#5a1424"
GOLD = "#ffd45e"
GREEN = "#5ef2b2"
VIOLET = "#b07cff"
MAGENTA = "#ff5cd6"

TEAM_COLORS = (
    {"main": BLUE, "light": "#a9ecff", "dark": BLUE_D, "name": "СИНИЕ"},
    {"main": RED, "light": "#ffb3c0", "dark": RED_D, "name": "КРАСНЫЕ"},
)

MINE = (600.0, 328.0)
SPAWNS = (
    ((78.0, 236.0), (78.0, 328.0), (78.0, 420.0)),
    ((1122.0, 236.0), (1122.0, 328.0), (1122.0, 420.0)),
)
SPAWN_ZONES = ((9, 168, 174, 320), (1017, 168, 174, 320))

WALL_DEFS = (
    (490, 155, 90, 100), (620, 155, 90, 100),
    (490, 401, 90, 100), (620, 401, 90, 100),
    (250, 140, 150, 40), (800, 140, 150, 40),
    (250, 476, 150, 40), (800, 476, 150, 40),
    (370, 298, 60, 60), (770, 298, 60, 60),
    (180, 258, 40, 140), (980, 258, 40, 140),
    (540, 42, 120, 26), (540, 588, 120, 26),
)

BUSH_DEFS = (
    (250, 268, 92, 120), (858, 268, 92, 120),
    (288, 82, 142, 50), (770, 82, 142, 50),
    (288, 524, 142, 50), (770, 524, 142, 50),
    (552, 70, 96, 48), (552, 538, 96, 48),
)

BOT_NAMES = ("НЕО", "БАЙТ", "КИБЕР", "РЕКС", "ЗЕТ", "МАГМА",
             "НИКС", "ОРБИТ", "ТАЙФУН", "ГЛЮК")

MODES = {
    "skirmish": {
        "name": "СХВАТКА", "short": "СХВАТКА", "icon": "✦",
        "desc": "Командный бой 3×3. Побеждает команда, первой набравшая 15 уничтожений.",
        "rule": "ДО 15 УНИЧТОЖЕНИЙ", "time": 150.0,
    },
    "gems": {
        "name": "КРИСТАЛЛЫ", "short": "КРИСТАЛЛЫ", "icon": "◆",
        "desc": "Собирайте кристаллы в центре арены. Удержите 10 штук 15 секунд.",
        "rule": "10 КРИСТАЛЛОВ · 15 СЕК", "time": 150.0,
    },
}

DIFFICULTIES = ("Легко", "Обычно", "Сложно")
DIFF_CFG = {
    "Легко": {"aim": 0.34, "react": 0.50, "dmg": 0.78, "think": 0.20},
    "Обычно": {"aim": 0.17, "react": 0.28, "dmg": 1.00, "think": 0.14},
    "Сложно": {"aim": 0.075, "react": 0.13, "dmg": 1.08, "think": 0.09},
}

# ---------------------------------------------------------------- бойцы
HEROES = {
    "volt": {
        "id": "volt", "name": "ВОЛЬТ", "role": "ШТУРМОВИК",
        "tag": "УНИВЕРСАЛ", "art": 0,
        "desc": "Держит среднюю дистанцию и заливает арену плазмой. "
                "Идеален для тех, кто любит темп и постоянное давление.",
        "quote": "Не мигай.",
        "hp": 3400, "speed": 238,
        "damage": 310, "cooldown": 0.19, "ammo": 7, "reload": 1.12,
        "range": 540, "bullet_speed": 1500, "bullet_radius": 5,
        "shots": 1, "spread": 1.8, "attack_kind": "bullet",
        "ai_range": 330, "charge": 2500,
        "super": "overdrive", "super_name": "ПЕРЕГРУЗ",
        "super_desc": "4,5 секунды бесконечной обоймы. Выстрелы пробивают врагов.",
        "gadget": "boost", "gadget_name": "УСКОРЕНИЕ",
        "gadget_desc": "+60% скорости на 3 секунды.",
        "color": "#42a5ff", "light": "#b3efff", "dark": "#0d3355",
        "stats": (4, 3, 3),
    },
    "grom": {
        "id": "grom", "name": "ГРОМ", "role": "ТАНК",
        "tag": "ТЯЖЁЛАЯ АРТИЛЛЕРИЯ", "art": 1,
        "desc": "Живая крепость с дробовиком. Врывается в гущу боя, "
                "переживает очередь и отвечает в упор.",
        "quote": "Я. УЖЕ. ИДУ.",
        "hp": 5600, "speed": 218,
        "damage": 205, "cooldown": 0.62, "ammo": 3, "reload": 1.55,
        "range": 300, "bullet_speed": 1200, "bullet_radius": 6,
        "shots": 6, "spread": 34, "attack_kind": "bullet",
        "ai_range": 145, "charge": 2300,
        "super": "shockwave", "super_name": "УДАРНАЯ ВОЛНА",
        "super_desc": "Взрыв вокруг себя: 1400 урона и мощный отброс врагов.",
        "gadget": "shield", "gadget_name": "БРОНЯ",
        "gadget_desc": "4 секунды получаемого урона вдвое меньше.",
        "color": "#ff8a3d", "light": "#ffd2a1", "dark": "#57260c",
        "stats": (5, 5, 2),
    },
    "iskra": {
        "id": "iskra", "name": "ИСКРА", "role": "СНАЙПЕР",
        "tag": "ДАЛЬНИЙ БОЙ", "art": 2,
        "desc": "Один точный выстрел решает больше, чем десять неточных. "
                "Держит дистанцию и наказывает за открытые коридоры.",
        "quote": "Я вижу тебя насквозь.",
        "hp": 2800, "speed": 235,
        "damage": 950, "cooldown": 0.85, "ammo": 3, "reload": 1.70,
        "range": 900, "bullet_speed": 2150, "bullet_radius": 4,
        "shots": 1, "spread": 0.8, "attack_kind": "bullet",
        "ai_range": 520, "charge": 2200,
        "super": "beam", "super_name": "ИМПУЛЬС",
        "super_desc": "Мгновенный луч на 950 px: 2300 урона всем на линии.",
        "gadget": "dash", "gadget_name": "РЫВОК",
        "gadget_desc": "Мгновенный рывок на 190 px сквозь опасность.",
        "color": "#b06bff", "light": "#e3c8ff", "dark": "#34135f",
        "stats": (5, 2, 3),
    },
    "luna": {
        "id": "luna", "name": "ЛУНА", "role": "ПОДДЕРЖКА",
        "tag": "ЖИВАЯ БАРРИКАДА", "art": 3,
        "desc": "Лечит союзников и продлевает командный бой. Её гимп "
                "превращает почти проигранную стычку в шанс на камбэк.",
        "quote": "Держитесь рядом.",
        "hp": 3200, "speed": 242,
        "damage": 320, "cooldown": 0.30, "ammo": 5, "reload": 0.95,
        "range": 480, "bullet_speed": 1250, "bullet_radius": 5,
        "shots": 1, "spread": 1.5, "attack_kind": "bullet",
        "ai_range": 330, "charge": 2200,
        "super": "heal", "super_name": "ГИМН",
        "super_desc": "Лечит себя и союзников рядом на 2400 и даёт щит на 3 с.",
        "gadget": "heal", "gadget_name": "АПТЕЧКА",
        "gadget_desc": "Лечит вас на 35% и союзников рядом на 20%.",
        "color": "#46e6b0", "light": "#b8ffe9", "dark": "#0b4a3a",
        "stats": (2, 3, 4),
    },
    "fakel": {
        "id": "fakel", "name": "ФАКЕЛ", "role": "АРТИЛЛЕРИЯ",
        "tag": "ПЛОЩАДНОЙ УРОН", "art": 4,
        "desc": "Закидывает гранаты за укрытия и не даёт врагам стоять на месте. "
                "Особенно хорош на узких проходах.",
        "quote": "Грейтесь.",
        "hp": 3600, "speed": 226,
        "damage": 740, "cooldown": 0.78, "ammo": 3, "reload": 1.52,
        "range": 530, "bullet_speed": 1200, "bullet_radius": 6,
        "shots": 1, "spread": 0, "attack_kind": "lob",
        "splash": 106, "ai_range": 390, "charge": 2300,
        "super": "barrage", "super_name": "БОМБАРДИРОВКА",
        "super_desc": "Пять гранат вокруг точки прицела. 2600 урона суммарно.",
        "gadget": "dash", "gadget_name": "ПРЫЖОК",
        "gadget_desc": "Рывок на 190 px, чтобы уйти из-под удара.",
        "color": "#ff4f6d", "light": "#ffb3bf", "dark": "#5a1220",
        "stats": (4, 3, 3),
    },
    "ten": {
        "id": "ten", "name": "ТЕНЬ", "role": "АССАСИН",
        "tag": "БЛИЖНИЙ БОЙ", "art": 5,
        "desc": "Быстрая и хрупкая охотница на одиночек. Заходит с фланга, "
                "разрезает цель и исчезает раньше, чем её успевают заметить.",
        "quote": "Ты меня не видел.",
        "hp": 3500, "speed": 290,
        "damage": 290, "cooldown": 0.42, "ammo": 4, "reload": 0.92,
        "range": 310, "bullet_speed": 1850, "bullet_radius": 5,
        "shots": 3, "spread": 16, "attack_kind": "shard",
        "ai_range": 145, "charge": 2100,
        "super": "dash", "super_name": "ТЕНЕВОЙ РАЗРЕЗ",
        "super_desc": "Рывок на 400 px: 1600 урона всем на пути.",
        "gadget": "invis", "gadget_name": "МИРАЖ",
        "gadget_desc": "3 секунды невидимости для ботов.",
        "color": "#ff6ad5", "light": "#ffd1f3", "dark": "#53103f",
        "stats": (3, 3, 5),
    },
}

HERO_ORDER = ("volt", "grom", "iskra", "luna", "fakel", "ten")

# ---------------------------------------------------------------- утилиты
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def plural(n, one, few, many):
    """Русская форма слова для числа n: 1 матч, 2 матча, 5 матчей."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def lerp(a, b, t):
    return a + (b - a) * t


def dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


def norm(x, y):
    length = math.hypot(x, y)
    if length < 1e-9:
        return 0.0, 0.0
    return x / length, y / length


def angle_to(ax, ay, bx, by):
    return math.atan2(by - ay, bx - ax)


def mix(c1, c2, t):
    """Смешать два цвета #rrggbb."""
    t = clamp(t, 0.0, 1.0)
    a = c1.lstrip("#")
    b = c2.lstrip("#")
    try:
        ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
        br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    except Exception:
        return c1
    return "#%02x%02x%02x" % (
        int(ar + (br - ar) * t),
        int(ag + (bg - ag) * t),
        int(ab + (bb - ab) * t),
    )


def fmt_time(seconds):
    seconds = max(0, int(math.ceil(seconds)))
    return "%02d:%02d" % (seconds // 60, seconds % 60)


def hex_points(cx, cy, r, rot=0.0):
    return [(cx + math.cos(rot + i * math.pi / 3) * r,
             cy + math.sin(rot + i * math.pi / 3) * r) for i in range(6)]


def point_in_rect(px, py, rect):
    x, y, w, h = rect
    return x <= px <= x + w and y <= py <= y + h


def point_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    if length2 < 1e-9:
        return dist(px, py, x1, y1)
    t = clamp(((px - x1) * dx + (py - y1) * dy) / length2, 0.0, 1.0)
    return dist(px, py, x1 + dx * t, y1 + dy * t)


# ---------------------------------------------------------------- сохранение
def _merge(base, extra):
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


DEFAULT_SETTINGS = {
    "sound": True,
    "particles": True,
    "shake": True,
    "difficulty": "Обычно",
}

DEFAULT_SAVE = {
    "settings": DEFAULT_SETTINGS,
    "heroes": {},
    "matches": 0,
    "wins": 0,
    "selected": "volt",
    "mode": "skirmish",
    "name": "ИГРОК",
}

for _hid in HERO_ORDER:
    DEFAULT_SAVE["heroes"][_hid] = {"trophies": 0, "wins": 0, "kills": 0}


def user_data_path():
    base = os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__))
    candidate = os.path.join(base, "neon_brawl_save.json")
    try:
        if os.path.exists(candidate) or os.access(base, os.W_OK):
            return candidate
    except Exception:
        pass
    folder = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                          "NeonBrawl")
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return os.path.join(folder, "neon_brawl_save.json")


class SaveData:
    def __init__(self):
        self.path = user_data_path()
        self.readonly = False
        self.data = json.loads(json.dumps(DEFAULT_SAVE))
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                self.data = _merge(DEFAULT_SAVE, raw)
        except Exception:
            pass
        self.data["settings"] = _merge(DEFAULT_SETTINGS,
                                       self.data.get("settings", {}))
        if self.data.get("selected") not in HEROES:
            self.data["selected"] = "volt"
        if self.data.get("mode") not in MODES:
            self.data["mode"] = "skirmish"
        heroes = self.data.setdefault("heroes", {})
        for hid in HERO_ORDER:
            heroes[hid] = _merge({"trophies": 0, "wins": 0, "kills": 0},
                                 heroes.get(hid, {}))

    def save(self):
        if self.readonly:
            return
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def hero(self, hid):
        return self.data["heroes"].setdefault(
            hid, {"trophies": 0, "wins": 0, "kills": 0})

    def total_trophies(self):
        return sum(self.hero(h)["trophies"] for h in HERO_ORDER)

    def record_match(self, hid, won, kills):
        hero = self.hero(hid)
        delta = 8 if won else (-3 if won is False else 0)
        hero["trophies"] = max(0, int(hero["trophies"]) + delta)
        if won:
            hero["wins"] = int(hero.get("wins", 0)) + 1
            self.data["wins"] = int(self.data.get("wins", 0)) + 1
        hero["kills"] = int(hero.get("kills", 0)) + int(kills)
        self.data["matches"] = int(self.data.get("matches", 0)) + 1
        self.save()
        return delta


# ---------------------------------------------------------------- звук
def _wav_bytes(f1, f2, duration, volume=0.20, wave="square"):
    rate = 16000
    count = max(1, int(rate * duration))
    data = bytearray()
    phase = 0.0
    rnd = random.Random(7)
    for i in range(count):
        t = i / (count - 1) if count > 1 else 0.0
        freq = f1 + (f2 - f1) * t
        phase += 2.0 * math.pi * freq / rate
        if wave == "square":
            sample = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == "saw":
            sample = 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
        elif wave == "noise":
            sample = rnd.uniform(-1.0, 1.0)
        else:
            sample = math.sin(phase)
        env = (1.0 - t) ** 1.5
        value = int(max(-1.0, min(1.0, sample * volume * env)) * 32767)
        data += struct.pack("<h", value)
    header = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
              + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
              + b"data" + struct.pack("<I", len(data)))
    return header + bytes(data)


class Sound:
    def __init__(self):
        self.enabled = True
        self.last = {}
        self.bank = {}

    def prepare(self):
        if self.bank or winsound is None:
            return
        specs = {
            "shoot": (1250, 520, 0.055, 0.13, "square"),
            "heavy": (330, 120, 0.10, 0.20, "saw"),
            "hit": (220, 90, 0.06, 0.15, "noise"),
            "super": (300, 1400, 0.28, 0.20, "saw"),
            "pickup": (900, 1600, 0.09, 0.15, "sine"),
            "heal": (650, 1300, 0.20, 0.12, "sine"),
            "death": (420, 60, 0.35, 0.18, "saw"),
            "win": (500, 1200, 0.45, 0.16, "sine"),
            "lose": (500, 110, 0.50, 0.16, "saw"),
            "click": (1000, 1350, 0.035, 0.11, "square"),
        }
        for name, (f1, f2, dur, vol, wave) in specs.items():
            self.bank[name] = _wav_bytes(f1, f2, dur, vol, wave)

    def play(self, name):
        if not self.enabled or winsound is None:
            return
        now = time.perf_counter()
        if now - self.last.get(name, 0.0) < 0.045:
            return
        self.last[name] = now
        try:
            if not self.bank:
                self.prepare()
            winsound.PlaySound(self.bank[name],
                               winsound.SND_MEMORY | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
        except Exception:
            pass

