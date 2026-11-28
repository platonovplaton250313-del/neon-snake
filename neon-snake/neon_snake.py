#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEON SNAKE — неоновая змейка на tkinter, без сторонних библиотек.

Запуск:
    snake            — если папка игры добавлена в PATH (install_snake.cmd)
    python neon_snake.py

Режимы:
    Классика, лабиринт, блиц, хаос, игра против ботов и сетевая игра
    по локальной сети (хост + гость, TCP, без сторонних библиотек).

Управление:
    ← ↑ → ↓ / WASD  — движение
    ПРОБЕЛ / P      — пауза
    R               — заново
    ESC             — меню / выход
"""

import json
import math
import os
import queue
import random
import socket
import sys
import threading
import time
import traceback
import tkinter as tk
from collections import deque
from datetime import date, timedelta

try:                     # звук есть только на Windows
    import winsound
except Exception:        # pragma: no cover
    winsound = None

# ---------------------------------------------------------------- геометрия
CELL = 26
COLS = 26
ROWS = 20
FIELD_W = COLS * CELL            # 676
FIELD_H = ROWS * CELL            # 520
FX, FY = 62, 104
WIN_W = FX * 2 + FIELD_W         # 800
WIN_H = FY + FIELD_H + 76        # 700

# ---------------------------------------------------------------- палитра
BG_TOP = "#04070f"
BG_BOT = "#0a1122"
FIELD_BG = "#070e1b"
PANEL_BG = "#060b16"
MUTED = "#5d6f8f"
TEXT = "#e8f6ff"
CYAN = "#7ef9ff"
MID_C = "#3fd0ff"
HEAD_C = "#a8fbff"
TAIL_C = "#9a6cff"
BLUE = "#4a7dff"
VIOLET = "#b06bff"
MAGENTA = "#ff4d9d"
GOLD = "#ffd24a"
ORANGE = "#ff9a4d"

F_TITLE = "Bahnschrift SemiBold"
F_UI = "Segoe UI"

DIR_KEYS = {
    "left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
    "a": (-1, 0), "d": (1, 0), "w": (0, -1), "s": (0, 1),
    "ф": (-1, 0), "в": (1, 0), "ц": (0, -1), "ы": (0, 1),
}

# ---------------------------------------------------------------- режимы и настройки
MODES = (
    ("classic", "КЛАССИКА", "Чистая змейка: яблоки, комбо и тонны адреналина."),
    ("maze", "ЛАБИРИНТ", "На поле вырастают неоновые стены — ищи обход."),
    ("blitz", "БЛИЦ 60", "Одна минута на всё: собирай и не тормози."),
    ("chaos", "ХАОС", "Метеориты, турбо и бонусы без передышки."),
    ("bots", "ПРОТИВ БОТОВ", "Две змеи-ИИ на одном поле: кто кого переиграет."),
    ("net", "СЕТЕВАЯ ИГРА", "Два игрока по локальной сети: хост и гость."),
)
MODE_NAMES = {m[0]: m[1] for m in MODES}
MODE_DESC = {m[0]: m[2] for m in MODES}

# ---------------------------------------------------------------- магазин
SKINS = (
    {"id": "classic", "name": "НЕОН", "desc": "Фирменный бирюзовый градиент",
     "price": 0, "colors": (HEAD_C, MID_C, TAIL_C)},
    {"id": "magma", "name": "МАГМА", "desc": "Раскалённый закат",
     "price": 600, "colors": ("#ffe0a8", "#ff8a3d", "#b51b4b")},
    {"id": "toxic", "name": "ТОКСИН", "desc": "Кислотный лайм",
     "price": 800, "colors": ("#eaffb0", "#8dff4d", "#1fbf6b")},
    {"id": "ice", "name": "ЛЁД", "desc": "Ледяная сталь",
     "price": 900, "colors": ("#ffffff", "#9fe8ff", "#4a7dff")},
    {"id": "royal", "name": "ЗОЛОТО", "desc": "Королевский металл",
     "price": 1200, "colors": ("#fff4c2", "#ffd24a", "#b0720e")},
    {"id": "void", "name": "ПУСТОТА", "desc": "Фиолетовая бездна",
     "price": 1500, "colors": ("#e3c8ff", "#b06bff", "#3d1a7a")},
    {"id": "pixel", "name": "ПИКСЕЛЬ", "desc": "Ретро-аркадный неон",
     "price": 1800, "colors": ("#c8ff8a", "#39ff88", "#0e7a5a")},
    {"id": "rainbow", "name": "РАДУГА", "desc": "Переливается прямо в игре",
     "price": 2500, "colors": ("#ff9ad0", "#ffd24a", "#39ff88"),
     "special": "rainbow"},
)
SKIN_BY_ID = {s["id"]: s for s in SKINS}
RAINBOW_PALETTES = (
    ("#ff9ad0", "#ff4d9d", "#8f2a66"),
    ("#ffe9a0", "#ffb347", "#7a4a16"),
    ("#eaffb0", "#8dff4d", "#1fbf6b"),
    ("#c8f7ff", "#3fd0ff", "#4a7dff"),
    ("#e3c8ff", "#b06bff", "#5a2a9a"),
    ("#ffd0dd", "#ff4d9d", "#b06bff"),
)

CHEATS = (
    {"id": "ghost", "name": "ФАНТОМ", "chip": "ФАНТОМ", "icon": "◈", "price": 2200,
     "desc": "Проходить сквозь стены, метеориты и соперников."},
    {"id": "x2", "name": "ДВОЙНЫЕ ОЧКИ", "chip": "×2", "icon": "×2", "price": 2600,
     "desc": "Все очки удваиваются, включая сетевую игру."},
    {"id": "revive", "name": "ВТОРОЙ ШАНС", "chip": "ШАНС", "icon": "↺", "price": 2400,
     "desc": "Одно автоматическое возрождение за игру."},
    {"id": "lucky", "name": "ЗВЕЗДОПАД", "chip": "ЗВЁЗДЫ", "icon": "★", "price": 1800,
     "desc": "Золотые звёзды появляются заметно чаще."},
    {"id": "rich", "name": "ЗОЛОТАЯ ЖИЛА", "chip": "+50%", "icon": "◆", "price": 2000,
     "desc": "+50% неонов после каждой игры."},
)
CHEAT_BY_ID = {c["id"]: c for c in CHEATS}

PROMO_CODES = {
    "NEON2026": {"coins": 500},
    "SNAKE777": {"coins": 777},
    "NEONRICH": {"coins": 1000},
    "GOLDSTAR": {"skin": "royal"},
    "HAPPYSNAKE": {"coins": 300, "skin": "toxic"},
    "PIXELPOWER": {"skin": "pixel"},
    "RAINBOWCODE": {"skin": "rainbow"},
    "GHOSTMODE": {"cheat": "ghost"},
    "DOUBLEUP": {"cheat": "x2"},
    "SECONDSHOT": {"cheat": "revive"},
    "LUCKYSTAR": {"cheat": "lucky"},
    "GOLDDIGGER": {"cheat": "rich"},
}

NET_PORT = 45871
NET_MATCH_TIME = 90.0
BOT_STYLES = (
    ("НИО", ("#ff9ad0", "#ff4d9d", "#7a1f52")),
    ("ВОЛЬТ", ("#ffe9a0", "#ffb347", "#7a4a16")),
)
NET_HOST_COLORS = (HEAD_C, MID_C, TAIL_C)
NET_GUEST_COLORS = ("#ffb3d9", "#ff4d9d", "#8f2a66")

SPEEDS = {
    "Медленно": (0.185, 0.095, 0.0028),
    "Обычно": (0.155, 0.075, 0.0032),
    "Быстро": (0.125, 0.060, 0.0038),
}
SPECIAL_EVERY = {"Редко": 6, "Обычно": 4, "Часто": 2}
SPEED_NAMES = ("Медленно", "Обычно", "Быстро")
SPECIAL_NAMES = ("Редко", "Обычно", "Часто")

POWER_EVERY = {"classic": 4, "maze": 5, "blitz": 3, "chaos": 3,
               "bots": 4, "net": 4}
POWER_KINDS = ("shield", "double", "slow")
POWER_DURATION = {"shield": 7.0, "double": 10.0, "slow": 8.0}
POWER_TEXT = {"shield": "ЩИТ!", "double": "×2 ОЧКИ!", "slow": "ЗАМЕДЛЕНИЕ!"}
EFFECT_INFO = {
    "shield": ("ЩИТ", CYAN),
    "double": ("×2", MAGENTA),
    "slow": ("МЕДЛ", VIOLET),
    "surge": ("ТУРБО", GOLD),
}
CHAOS_EVENTS = ("meteor", "surge", "star")

DEFAULT_SETTINGS = {
    "speed": "Обычно",
    "wrap": False,
    "grid": True,
    "particles": True,
    "shake": True,
    "sound": False,
    "specials": "Обычно",
}

SETTING_ROWS = (
    ("speed", "СКОРОСТЬ", SPEED_NAMES),
    ("wrap", "СТЕНЫ", None),
    ("grid", "СЕТКА", None),
    ("particles", "ЧАСТИЦЫ", None),
    ("shake", "ТРЯСКА ЭКРАНА", None),
    ("sound", "ЗВУК", None),
    ("specials", "ЗОЛОТАЯ ЗВЕЗДА", SPECIAL_NAMES),
)

SOUND_ALIASES = {
    "eat": "SystemAsterisk",
    "special": "SystemExclamation",
    "die": "SystemHand",
    "menu": "SystemDefault",
}


# ---------------------------------------------------------------- утилиты
def mix(c1, c2, t):
    """Смешивает два цвета #rrggbb (t=0 -> c1, t=1 -> c2)."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    a = (int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16))
    b = (int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16))
    return "#%02x%02x%02x" % (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def rr_pts(x0, y0, x1, y1, r, steps=4):
    """Точки скруглённого прямоугольника для сглаженного полигона."""
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = []
    for cx, cy, start in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0),
                          (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(steps + 1):
            a = math.radians(start + 90.0 * k / steps)
            pts.extend((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def valid_skin_id(value):
    try:
        return value if value in SKIN_BY_ID else "classic"
    except TypeError:
        return "classic"


def default_cheat_flags():
    return {c["id"]: False for c in CHEATS}


def valid_cheat_ids(values):
    out = []
    if isinstance(values, list):
        for value in values:
            try:
                valid = value in CHEAT_BY_ID
            except TypeError:
                valid = False
            if valid and value not in out:
                out.append(value)
    return out


def valid_dir(value, default=(1, 0)):
    try:
        if isinstance(value, (list, tuple)) and len(value) == 2:
            dx, dy = int(value[0]), int(value[1])
            if (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                return (dx, dy)
    except (TypeError, ValueError):
        pass
    return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_cells(values):
    out = []
    if isinstance(values, (list, tuple)):
        for cell in values:
            try:
                if len(cell) != 2:
                    continue
                x, y = int(cell[0]), int(cell[1])
            except (TypeError, ValueError):
                continue
            if 0 <= x < COLS and 0 <= y < ROWS:
                out.append((x, y))
    return out


def date_key(offset_days=0):
    return (date.today() + timedelta(days=offset_days)).isoformat()


# ---------------------------------------------------------------- журнал ошибок
def _data_dir():
    """Папка для сохранений и журнала.

    Собранная версия (.exe) хранит данные в %APPDATA%\\NeonSnake:
    папка игры может быть только для чтения, а обновления её не трогают.
    """
    base = os.environ.get("NEON_SNAKE_DATA")
    if not base and getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = os.path.join(appdata, "NeonSnake")
    if base:
        try:
            os.makedirs(base, exist_ok=True)
            return base
        except OSError:
            pass
    return os.path.dirname(os.path.abspath(__file__))


def _error_log_path():
    return os.path.join(_data_dir(), "neon_snake_error.log")


def _write_error(text):
    """Пишет traceback рядом с игрой: полезно при запуске без консоли."""
    path = _error_log_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        return None
    return path


# ---------------------------------------------------------------- эффекты
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "ttl", "color", "size")

    def __init__(self, x, y, color):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(35, 185)
        self.x, self.y = x, y
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.ttl = random.uniform(0.35, 0.85)
        self.life = self.ttl
        self.color = color
        self.size = random.uniform(1.6, 3.7)

    def update(self, dt):
        self.life -= dt
        f = 0.92 ** (dt * 60)
        self.vx *= f
        self.vy = self.vy * f + 60 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0

    def draw(self, c):
        k = max(0.0, self.life / self.ttl)
        r = self.size * (0.25 + 0.75 * k)
        c.create_oval(self.x - r, self.y - r, self.x + r, self.y + r,
                      fill=mix(self.color, FIELD_BG, 1 - k), outline="", tags="dyn")


class Ring:
    __slots__ = ("x", "y", "r0", "rmax", "r", "ttl", "life", "color")

    def __init__(self, x, y, color, rmax=44, ttl=0.45):
        self.x, self.y = x, y
        self.r0, self.rmax, self.r = 8.0, rmax, 8.0
        self.ttl = self.life = ttl
        self.color = color

    def update(self, dt):
        self.life -= dt
        k = max(0.0, self.life / self.ttl)
        self.r = self.r0 + (self.rmax - self.r0) * (1 - k)
        return self.life > 0

    def draw(self, c):
        k = max(0.0, self.life / self.ttl)
        c.create_oval(self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r,
                      outline=mix(self.color, FIELD_BG, 1 - k * 0.85),
                      width=1 + 2.2 * k, tags="dyn")


class FloatText:
    __slots__ = ("x", "y", "text", "color", "life", "ttl")

    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text, self.color = text, color
        self.ttl = self.life = 0.9

    def update(self, dt):
        self.life -= dt
        self.y -= 38 * dt
        return self.life > 0

    def draw(self, c):
        k = max(0.0, self.life / self.ttl)
        c.create_text(self.x, self.y, text=self.text,
                      font=(F_TITLE, 13, "bold"),
                      fill=mix(self.color, FIELD_BG, 1 - min(1.0, k * 1.7)),
                      tags="dyn")


class Ambient:
    __slots__ = ("x", "y", "r", "vx", "vy", "color")

    def __init__(self, initial=True):
        self.reset(initial)

    def reset(self, initial=False):
        self.x = random.uniform(0, WIN_W)
        self.y = random.uniform(0, WIN_H) if initial else WIN_H + 5
        self.r = random.uniform(0.6, 1.8)
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-16, -4)
        self.color = random.choice(("#1b3154", "#231f4c", "#163a47", "#2a2440"))

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -6 or self.x < -10 or self.x > WIN_W + 10:
            self.reset()

    def draw(self, c):
        c.create_oval(self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r,
                      fill=self.color, outline="", tags="dyn")


# ---------------------------------------------------------------- сеть
class NetLink:
    """TCP-соединение с построчным JSON-протоколом.

    Читает сокет в отдельном потоке и складывает сообщения в очередь:
    tkinter-цикл забирает их без блокировки.
    """

    def __init__(self, sock, role):
        self.sock = sock
        self.role = role
        self.events = queue.Queue()
        self.alive = True
        self._buf = b""
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while self.alive:
            try:
                data = self.sock.recv(65536)
            except OSError:
                break
            if not data:
                break
            self._buf += data
            while b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(msg, dict):
                    self.events.put(msg)
        self.alive = False
        self.events.put({"t": "closed"})

    def send(self, msg):
        if not self.alive:
            return
        try:
            self.sock.sendall((json.dumps(msg, separators=(",", ":"),
                                         ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            self.alive = False

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass


class NetServer:
    """Слушает порт и отдаёт принятое соединение через очередь."""

    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.events = queue.Queue()
        self.alive = True
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        try:
            conn, addr = self.sock.accept()
        except OSError:
            return
        self.events.put({"t": "accepted", "sock": conn, "addr": addr})

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass


def _net_connect(ip, port, events):
    try:
        sock = socket.create_connection((ip, port), timeout=6.0)
        sock.settimeout(None)
        events.put({"t": "connected", "sock": sock})
    except OSError as exc:
        events.put({"t": "connect_failed", "error": str(exc)})


def _local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


# ---------------------------------------------------------------- игра
class Game:
    def __init__(self, root=None):
        self.root = root or tk.Tk()
        self.root.report_callback_exception = self._tk_error
        self.root.title("NEON SNAKE")
        self.root.configure(bg=BG_TOP)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                bg=BG_TOP, highlightthickness=0, bd=0)
        self.canvas.pack()
        self._center_window()

        self.running = True
        self.time = 0.0
        self.last = time.perf_counter()

        self.settings, self.bests, self.mode, self.eco = self._load_save()
        self.menu_sel = 0
        self.modes_sel = [m[0] for m in MODES].index(self.mode)
        self.settings_sel = 0
        self.reset_confirm = False
        self.death_reason = "crash"
        self.state = "menu"
        self.shop_tab = 0
        self.shop_sel = 0
        self.shop_status = ""
        self.shop_status_color = MUTED

        # --- сеть ---
        self.net = None
        self.net_server = None
        self.net_role = None
        self.net_events = queue.Queue()
        self.net_status = ""
        self.net_ip = "127.0.0.1"
        self.net_port = NET_PORT
        self.net_lan_ip = "127.0.0.1"
        self.net_send_timer = 0.0
        self.net_have_state = False
        self.net_over = False
        self.net_won = False
        self.net_winner = 0
        self.net_lost = False
        self.net_menu_sel = 0
        self.net_last_role = None
        self.player_colors = None
        self.rivals = []

        self.particles = []
        self.rings = []
        self.floats = []
        self.ambient = [Ambient() for _ in range(44)]

        self.reset()
        self._draw_static()

        self.root.bind("<KeyPress>", self.on_key)
        self.root.bind("<FocusOut>", self.on_blur)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.focus_force()
        self.canvas.focus_set()
        self.root.after(15, self.loop)

    # ------------------------------------------------ окно и сохранения
    def _tk_error(self, exc, val, tb):
        _write_error("".join(traceback.format_exception(exc, val, tb)))

    def _center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - WIN_W) // 2
        y = max(0, (self.root.winfo_screenheight() - WIN_H) // 2 - 26)
        self.root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, x, y))

    def _save_path(self):
        return os.path.join(_data_dir(), "neon_snake_save.json")

    def _load_save(self):
        settings = dict(DEFAULT_SETTINGS)
        bests = {m[0]: 0 for m in MODES}
        mode = "classic"
        eco = {
            "coins": 0,
            "skin": "classic",
            "skins": ["classic"],
            "ownedCheats": [],
            "cheats": default_cheat_flags(),
            "usedCodes": [],
            "daily": {"last": "", "streak": 0},
        }
        try:
            with open(self._save_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in (data.get("settings") or {}).items():
                if k in settings:
                    settings[k] = v
            for k, v in (data.get("best") or {}).items():
                if k in bests:
                    try:
                        bests[k] = int(v)
                    except (TypeError, ValueError):
                        pass
            mode = data.get("mode", mode)

            coins = data.get("coins", 0)
            try:
                eco["coins"] = max(0, int(coins))
            except (TypeError, ValueError):
                eco["coins"] = 0
            skin = valid_skin_id(data.get("skin"))
            skins = ["classic"]
            saved_skins = data.get("skins")
            if isinstance(saved_skins, list):
                for item in saved_skins:
                    if item in SKIN_BY_ID and item not in skins:
                        skins.append(item)
            if skin not in skins:
                skin = "classic"
            eco["skin"] = skin
            eco["skins"] = skins
            eco["ownedCheats"] = valid_cheat_ids(data.get("ownedCheats"))
            saved_cheats = data.get("cheats")
            if isinstance(saved_cheats, dict):
                for cid in eco["ownedCheats"]:
                    eco["cheats"][cid] = bool(saved_cheats.get(cid))
            saved_codes = data.get("usedCodes")
            if isinstance(saved_codes, list):
                for code in saved_codes:
                    if isinstance(code, str) and 0 < len(code) <= 24:
                        code = code.upper()
                        if code not in eco["usedCodes"]:
                            eco["usedCodes"].append(code)
            daily = data.get("daily")
            if isinstance(daily, dict):
                last = daily.get("last")
                if isinstance(last, str):
                    eco["daily"]["last"] = last[:10]
                try:
                    streak = int(daily.get("streak", 0))
                    eco["daily"]["streak"] = max(0, min(7, streak))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

        # перенос рекорда из ранней версии игры
        if not any(bests.values()):
            legacy = os.path.join(os.path.dirname(self._save_path()), "neon_snake_best.json")
            try:
                with open(legacy, "r", encoding="utf-8") as f:
                    bests["classic"] = int(json.load(f).get("best", 0))
            except Exception:
                pass

        if not isinstance(mode, str) or mode not in bests:
            mode = "classic"
        if not isinstance(settings.get("speed"), str) or settings.get("speed") not in SPEEDS:
            settings["speed"] = "Обычно"
        if not isinstance(settings.get("specials"), str) or \
                settings.get("specials") not in SPECIAL_EVERY:
            settings["specials"] = "Обычно"
        settings["wrap"] = bool(settings.get("wrap"))
        for k in ("grid", "particles", "shake", "sound"):
            settings[k] = bool(settings.get(k, DEFAULT_SETTINGS[k]))
        return settings, bests, mode, eco

    @property
    def best(self):
        return self.bests.get(self.mode, 0)

    def save_game(self):
        try:
            with open(self._save_path(), "w", encoding="utf-8") as f:
                json.dump({"settings": self.settings, "best": self.bests,
                           "mode": self.mode,
                           "coins": self.eco["coins"],
                           "skin": self.eco["skin"],
                           "skins": self.eco["skins"],
                           "ownedCheats": self.eco["ownedCheats"],
                           "cheats": self.eco["cheats"],
                           "usedCodes": self.eco["usedCodes"],
                           "daily": self.eco["daily"]},
                          f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ------------------------------------------------ экономика и магазин
    def active_cheat_ids(self):
        return [c["id"] for c in CHEATS
                if c["id"] in self.eco["ownedCheats"]
                and self.eco["cheats"].get(c["id"])]

    def cheat_flags(self):
        flags = default_cheat_flags()
        for cid in self.active_cheat_ids():
            flags[cid] = True
        return flags

    def _cheat_payload(self, flags=None):
        source = self.cheats if flags is None else flags
        return {c["id"]: bool(source.get(c["id"])) for c in CHEATS}

    def _skin_palette(self, skin_id, t=0.0):
        skin = SKIN_BY_ID.get(valid_skin_id(skin_id))
        if not skin:
            skin = SKINS[0]
        if skin.get("special") == "rainbow":
            return RAINBOW_PALETTES[int(t * 1.7) % len(RAINBOW_PALETTES)]
        return skin["colors"]

    def add_coins(self, amount):
        try:
            value = int(round(float(amount)))
        except (TypeError, ValueError):
            value = 0
        if value <= 0:
            return 0
        self.eco["coins"] += value
        self.save_game()
        return value

    def daily_status(self):
        today = date_key()
        yesterday = date_key(-1)
        daily = self.eco["daily"]
        claimed = daily.get("last") == today
        if claimed:
            next_streak = max(1, int(daily.get("streak", 1)))
        elif daily.get("last") == yesterday:
            next_streak = min(7, int(daily.get("streak", 0)) + 1)
        else:
            next_streak = 1
        return {
            "claimed": claimed,
            "streak": int(daily.get("streak", 0)),
            "next": next_streak,
            "reward": 40 + (next_streak - 1) * 10,
        }

    def claim_daily(self):
        daily = self.daily_status()
        if daily["claimed"]:
            self._shop_note("БОНУС УЖЕ ПОЛУЧЕН СЕГОДНЯ", MUTED)
            return
        self.eco["daily"] = {"last": date_key(), "streak": daily["next"]}
        self.add_coins(daily["reward"])
        self.save_game()
        self.play_sound("special")
        self._shop_note("ЕЖЕДНЕВНЫЙ БОНУС +%d ◆" % daily["reward"], GOLD)

    def open_shop(self):
        self.stop_net()
        self.shop_tab = 0
        self.shop_sel = 0
        self.shop_status = ""
        self.state = "shop"
        self.play_sound("menu")

    def _shop_note(self, text, color=None):
        self.shop_status = text
        self.shop_status_color = color or CYAN

    def _shop_item_count(self):
        if self.shop_tab == 0:
            return len(SKINS)
        if self.shop_tab == 1:
            return len(CHEATS)
        return 1

    def _shop_action(self):
        if self.shop_tab == 0:
            self._buy_skin(SKINS[self.shop_sel])
        elif self.shop_tab == 1:
            self._buy_cheat(CHEATS[self.shop_sel])
        else:
            self._prompt_code()

    def _buy_skin(self, skin):
        sid = skin["id"]
        if sid in self.eco["skins"]:
            self.eco["skin"] = sid
            self.save_game()
            self._shop_note("СКИН ВЫБРАН: " + skin["name"], CYAN)
            self.play_sound("menu")
            return
        if self.eco["coins"] < skin["price"]:
            self._shop_note("НЕ ХВАТАЕТ %d ◆" %
                            (skin["price"] - self.eco["coins"]), MAGENTA)
            self.play_sound("die")
            return
        self.eco["coins"] -= skin["price"]
        self.eco["skins"].append(sid)
        self.eco["skin"] = sid
        self.save_game()
        self._shop_note("КУПЛЕНО: " + skin["name"], GOLD)
        self.play_sound("special")

    def _buy_cheat(self, cheat):
        cid = cheat["id"]
        if cid in self.eco["ownedCheats"]:
            self.eco["cheats"][cid] = not bool(self.eco["cheats"].get(cid))
            self.save_game()
            self._shop_note(("ЧИТ ВКЛЮЧЁН: " if self.eco["cheats"][cid]
                             else "ЧИТ ВЫКЛЮЧЕН: ") + cheat["name"],
                            GOLD if self.eco["cheats"][cid] else MUTED)
            self.play_sound("menu")
            return
        if self.eco["coins"] < cheat["price"]:
            self._shop_note("НЕ ХВАТАЕТ %d ◆" %
                            (cheat["price"] - self.eco["coins"]), MAGENTA)
            self.play_sound("die")
            return
        self.eco["coins"] -= cheat["price"]
        self.eco["ownedCheats"].append(cid)
        self.eco["cheats"][cid] = True
        self.save_game()
        self._shop_note("ЧИТ ОТКРЫТ: " + cheat["name"], GOLD)
        self.play_sound("special")

    def _prompt_code(self):
        from tkinter import simpledialog
        value = simpledialog.askstring(
            "ПРОМОКОД", "Введите промокод или секретный код:",
            parent=self.root)
        if value is None:
            return
        code = "".join(ch for ch in str(value).upper() if ch.isalnum())[:24]
        if len(code) < 3:
            self._shop_note("ВВЕДИТЕ КОД", MAGENTA)
            return
        if code in self.eco["usedCodes"]:
            self._shop_note("ЭТОТ КОД УЖЕ ИСПОЛЬЗОВАН", MAGENTA)
            return
        promo = PROMO_CODES.get(code)
        if not promo:
            self._shop_note("НЕВЕРНЫЙ КОД: " + code, MAGENTA)
            self.play_sound("die")
            return
        rewards = []
        coins_gain = int(promo.get("coins", 0))
        skin_id = promo.get("skin")
        if skin_id and skin_id in SKIN_BY_ID:
            skin = SKIN_BY_ID[skin_id]
            if skin_id in self.eco["skins"]:
                extra = max(50, skin["price"] // 2)
                coins_gain += extra
                rewards.append("КОМПЕНСАЦИЯ %d ◆" % extra)
            else:
                self.eco["skins"].append(skin_id)
                rewards.append("СКИН " + skin["name"])
        cheat_id = promo.get("cheat")
        if cheat_id and cheat_id in CHEAT_BY_ID:
            cheat = CHEAT_BY_ID[cheat_id]
            if cheat_id in self.eco["ownedCheats"]:
                extra = max(50, cheat["price"] // 2)
                coins_gain += extra
                rewards.append("КОМПЕНСАЦИЯ %d ◆" % extra)
            else:
                self.eco["ownedCheats"].append(cheat_id)
                self.eco["cheats"][cheat_id] = True
                rewards.append("ЧИТ " + cheat["name"])
        if coins_gain:
            self.eco["coins"] += coins_gain
            rewards.insert(0, "+%d ◆" % coins_gain)
        self.eco["usedCodes"].append(code)
        self.save_game()
        self._shop_note("КОД АКТИВИРОВАН: " + " · ".join(rewards), GOLD)
        self.play_sound("special")

    def grant_coins(self):
        if getattr(self, "rewarded", False):
            return
        self.rewarded = True
        base = (int(self.score) // 5 + self.apples * 3 +
                self.stars * 6 + self.powers * 4)
        record_bonus = 150 if self.new_record else 0
        net_bonus = 0
        if self.mode == "net":
            net_bonus = 15
            my_winner = 2 if self.net_role == "client" else 1
            if self.net_winner == my_winner:
                net_bonus += 30
        raw_total = (base + record_bonus + net_bonus) * self.coin_mult
        total = max(1, int(math.floor(raw_total + 0.5)))
        self.reward_coins = total
        self.reward_record_bonus = record_bonus
        self.eco["coins"] += total
        self.save_game()

    def play_sound(self, kind):
        if not self.settings.get("sound") or winsound is None:
            return
        alias = SOUND_ALIASES.get(kind)
        if not alias:
            return
        try:
            winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            pass

    def close(self):
        self.running = False
        self.stop_net()
        self.save_game()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------ состояние
    def reset(self):
        self.wrap = bool(self.settings.get("wrap"))
        self.base_int, self.min_int, self.ramp = SPEEDS.get(
            self.settings.get("speed"), SPEEDS["Обычно"])
        if self.mode == "blitz":
            self.base_int *= 0.88
            self.min_int *= 0.90
        elif self.mode == "chaos":
            self.base_int *= 0.94
            self.min_int *= 0.94
        self.interval = self.base_int
        self.power_every = POWER_EVERY.get(self.mode, 4)
        self.cheats = self.cheat_flags()
        self.score_mult = 2 if self.cheats.get("x2") else 1
        self.revives = 1 if self.cheats.get("revive") else 0
        self.coin_mult = 1.5 if self.cheats.get("rich") else 1.0
        special_every = SPECIAL_EVERY.get(self.settings.get("specials"), 4)
        if self.cheats.get("lucky"):
            special_every = max(2, special_every - 2)
        self.special_every = special_every

        cy = ROWS // 2
        cx = COLS // 2
        if self.mode == "net" and self.net_role == "client":
            self.snake = [(COLS - 6 - i, cy) for i in range(4)]
            self.dir = (-1, 0)
        elif self.mode == "net":
            self.snake = [(5 - i, cy) for i in range(4)]
            self.dir = (1, 0)
        else:
            self.snake = [(cx + 1 - i, cy) for i in range(4)]
            self.dir = (1, 0)
        self.prev_snake = list(self.snake)
        self.queue = []
        self.score = 0
        self.combo = 1
        self.combo_timer = 0.0
        self.apples = 0
        self.special = None
        self.powerup = None
        self.effects = {k: 0.0 for k in EFFECT_INFO}
        self.meteors = {}
        self.event_timer = 7.5 if self.mode == "chaos" else None
        self.stars = 0
        self.powers = 0
        self.max_combo = 1
        self.run_time = 0.0
        self.acc = 0.0
        self.t_render = 0.0
        self.score_pulse = 0.0
        self.flash = 0.0
        self.shake = 0.0
        self.dead_at = 0.0
        self.new_record = False
        self.rewarded = False
        self.reward_coins = 0
        self.reward_record_bonus = 0
        self.player_skin = self.eco["skin"]
        if self.mode == "blitz":
            self.time_left = 60.0
        elif self.mode == "net":
            self.time_left = NET_MATCH_TIME
        else:
            self.time_left = None
        self.walls = set()
        if self.mode == "maze":
            self._build_walls()
        self.rivals = []
        self.player_colors = None
        if self.mode == "bots":
            self._spawn_bots()
        elif self.mode == "net":
            self.player_colors = self._skin_palette(self.player_skin, self.time)
            if self.net_role == "host":
                self._spawn_net_guest()
        self.food = None
        self.pending_eats = []
        self._new_food()

    def start_game(self):
        if self.mode == "net" and self.net is None:
            self.open_netmenu()
            return
        self.particles.clear()
        self.rings.clear()
        self.floats.clear()
        self.reset()
        self.state = "playing"
        self.play_sound("menu")

    def to_menu(self):
        self.stop_net()
        self.reset()
        self.state = "menu"
        self.menu_sel = 0

    def open_modes(self):
        self.modes_sel = [m[0] for m in MODES].index(self.mode)
        self.state = "modes"
        self.play_sound("menu")

    # ------------------------------------------------ сетевое лобби
    def open_netmenu(self):
        self.stop_net()
        self.net_menu_sel = 0
        self.net_status = ""
        self.state = "netmenu"
        self.play_sound("menu")

    def host_net(self):
        self.stop_net()
        port = self.net_port
        try:
            self.net_server = NetServer(port)
        except (OSError, OverflowError, ValueError):
            try:
                self.net_server = NetServer(0)
            except (OSError, OverflowError, ValueError) as exc:
                self.net_status = "ПОРТ ЗАНЯТ: %s" % exc
                return
        self.net_port = self.net_server.port
        self.net_role = "host"
        self.net_lan_ip = _local_ip()
        self.net_status = ""
        self.state = "netwait"
        self.play_sound("menu")

    def join_net(self):
        from tkinter import simpledialog
        value = simpledialog.askstring(
            "СЕТЕВАЯ ИГРА",
            "IP-адрес хоста (можно добавить :порт):",
            initialvalue=self.net_ip, parent=self.root)
        if not value:
            return
        value = value.strip()
        host, port = value, NET_PORT
        if ":" in value:
            host, tail = value.rsplit(":", 1)
            try:
                port = int(tail)
                if not 1 <= port <= 65535:
                    port = NET_PORT
            except ValueError:
                port = NET_PORT
        self.net_ip = host or "127.0.0.1"
        self.net_port = port
        self.stop_net()
        self.net_role = "client"
        self.net_events = queue.Queue()
        threading.Thread(target=_net_connect,
                         args=(self.net_ip, port, self.net_events),
                         daemon=True).start()
        self.state = "netconnect"
        self.play_sound("menu")

    def _poll_lobby(self):
        if self.net_server is not None:
            try:
                msg = self.net_server.events.get_nowait()
            except queue.Empty:
                msg = None
            if msg and msg.get("t") == "accepted":
                sock = msg.get("sock")
                self.net_server.close()
                self.net_server = None
                self.net = NetLink(sock, "host")
                self._begin_net_play()

        if self.state == "netconnect":
            try:
                msg = self.net_events.get_nowait()
            except queue.Empty:
                msg = None
            if msg and msg.get("t") == "connected":
                self.net = NetLink(msg.get("sock"), "client")
                self._begin_net_play()
            elif msg and msg.get("t") == "connect_failed":
                self.net_status = "НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ: %s" % msg.get("error", "")
                self.net_role = None
                self.state = "netmenu"

    def _begin_net_play(self):
        self.net_over = False
        self.net_won = False
        self.net_winner = 0
        self.net_lost = False
        self.net_have_state = False
        self.net_send_timer = 0.0
        self.particles.clear()
        self.rings.clear()
        self.floats.clear()
        self.reset()
        self.state = "playing"
        self.acc = 0.0
        if self.net_role == "host":
            self._net_host_send(0.0, force=True)
        else:
            self._net_send_loadout()
        self.play_sound("menu")

    def stop_net(self):
        if self.net is not None:
            self.net.close()
            self.net = None
        if self.net_server is not None:
            self.net_server.close()
            self.net_server = None
        self.net_role = None
        self.net_have_state = False
        self.net_send_timer = 0.0
        self.player_colors = None

    def leave_net(self):
        self.stop_net()
        self.to_menu()

    def _net_menu_action(self):
        if self.net_menu_sel == 0:
            self.host_net()
        elif self.net_menu_sel == 1:
            self.join_net()
        else:
            self.back_to_menu()

    def open_settings(self):
        self.settings_sel = 0
        self.reset_confirm = False
        self.state = "settings"
        self.play_sound("menu")

    def back_to_menu(self):
        self.stop_net()
        self.menu_sel = 0
        self.state = "menu"
        self.save_game()

    # ------------------------------------------------ клетки и стены
    def _reachable(self, start):
        seen = {start}
        stack = [start]
        while stack:
            x, y = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.wrap:
                    nx %= COLS
                    ny %= ROWS
                elif not (0 <= nx < COLS and 0 <= ny < ROWS):
                    continue
                cell = (nx, ny)
                if cell in seen or cell in self.walls:
                    continue
                seen.add(cell)
                stack.append(cell)
        return seen

    def _build_walls(self):
        self.walls = set()
        cx, cy = COLS // 2, ROWS // 2
        safe = {(x, y) for x in range(cx - 5, cx + 6)
                for y in range(cy - 2, cy + 3)}
        target = random.randint(48, 66)
        for _ in range(240):
            if len(self.walls) >= target:
                break
            horizontal = random.random() < 0.5
            length = random.randint(3, 7)
            x = random.randint(1, COLS - 2)
            y = random.randint(1, ROWS - 2)
            seg = []
            for i in range(length):
                c = (x + i, y) if horizontal else (x, y + i)
                if not (0 <= c[0] < COLS and 0 <= c[1] < ROWS):
                    break
                if c in safe:
                    seg = []
                    break
                seg.append(c)
            if len(seg) >= 3:
                self.walls.update(seg)
        for _ in range(4):
            c = (random.randint(1, COLS - 2), random.randint(1, ROWS - 2))
            if c not in safe:
                self.walls.add(c)

    def _free_cells(self):
        blocked = set(self.snake) | self.walls | set(self.meteors)
        for r in self.rivals:
            if r["alive"]:
                blocked.update(r["body"])
        if self.food:
            blocked.add(self.food)
        if self.special:
            blocked.add(self.special["pos"])
        if self.powerup:
            blocked.add(self.powerup["pos"])
        cells = [(x, y) for y in range(ROWS) for x in range(COLS)
                 if (x, y) not in blocked]
        reach = self._reachable(self.snake[0]) if self.snake else set()
        good = [c for c in cells if c in reach]
        return good or cells

    def _new_food(self):
        cells = self._free_cells()
        self.food = random.choice(cells) if cells else None

    def _new_special(self):
        cells = self._free_cells()
        if cells:
            self.special = {"pos": random.choice(cells), "left": 7.5, "ttl": 7.5}

    def _new_power(self):
        cells = self._free_cells()
        if not cells:
            return
        free = [k for k in POWER_KINDS if self.effects.get(k, 0.0) <= 0.0]
        kind = random.choice(free or list(POWER_KINDS))
        self.powerup = {"pos": random.choice(cells), "kind": kind,
                        "left": 9.0, "ttl": 9.0}

    # ------------------------------------------------ соперники и боты
    def _make_rival(self, name, colors, body, direction):
        return {"name": name, "colors": colors, "body": list(body),
                "prev": list(body), "dir": direction, "queue": [],
                "score": 0, "alive": True, "respawn": 0.0, "ai": True,
                "apples": 0, "stars": 0, "powers": 0,
                "skin": None, "cheats": default_cheat_flags(), "revives": 0}

    def _spawn_bots(self):
        cy = ROWS // 2
        y1 = min(ROWS - 3, max(2, cy - 5))
        y2 = min(ROWS - 3, max(2, cy + 5))
        self.rivals = [
            self._make_rival(BOT_STYLES[0][0], BOT_STYLES[0][1],
                             [(3 - i, y1) for i in range(4)], (1, 0)),
            self._make_rival(BOT_STYLES[1][0], BOT_STYLES[1][1],
                             [(COLS - 4 + i, y2) for i in range(4)], (-1, 0)),
        ]

    def _spawn_net_guest(self):
        cy = ROWS // 2
        rival = self._make_rival("ГОСТЬ", NET_GUEST_COLORS,
                                 [(COLS - 6 + i, cy) for i in range(4)],
                                 (-1, 0))
        rival["ai"] = False
        self.rivals = [rival]

    def _rival_cells(self, exclude=None):
        cells = set()
        for r in self.rivals:
            if r is not exclude and r["alive"]:
                cells.update(r["body"])
        return cells

    def _other_rival_cells(self, rival):
        cells = set()
        for r in self.rivals:
            if r is not rival and r["alive"]:
                cells.update(r["body"])
        return cells

    def _respawn_rival(self, rival):
        cells = self._free_cells()
        random.shuffle(cells)
        for cell in cells:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                body = []
                ok = True
                for i in range(4):
                    c = (cell[0] - d[0] * i, cell[1] - d[1] * i)
                    if self.wrap:
                        c = (c[0] % COLS, c[1] % ROWS)
                    elif not (0 <= c[0] < COLS and 0 <= c[1] < ROWS):
                        ok = False
                        break
                    if c in self.walls or c in self.snake or \
                            c in self._other_rival_cells(rival):
                        ok = False
                        break
                    body.append(c)
                if ok:
                    rival["body"] = body
                    rival["prev"] = list(body)
                    rival["dir"] = d
                    rival["queue"] = []
                    rival["alive"] = True
                    rival["respawn"] = 0.0
                    return True
        return False

    def _kill_rival(self, rival, reason="crash"):
        if not rival["alive"]:
            return
        if self.mode == "net" and rival.get("revives", 0) > 0:
            old_body = rival["body"]
            rival["alive"] = False
            rival["body"] = []
            if self._respawn_rival(rival):
                rival["revives"] -= 1
                x, y = self._center_of(rival["body"][0])
                self.rings.append(Ring(x, y, GOLD, rmax=52, ttl=0.5))
                self.floats.append(FloatText(x, y - 14, "ВТОРОЙ ШАНС!", GOLD))
                self.play_sound("special")
                return
            rival["body"] = old_body
        rival["alive"] = False
        rival["respawn"] = 2.6 if self.mode == "bots" else 0.0
        x, y = self._center_of(rival["body"][0])
        if self.settings.get("particles"):
            for seg in rival["body"]:
                sx, sy = self._center_of(seg)
                self.particles.append(Particle(sx, sy, rival["colors"][1]))
            self.rings.append(Ring(x, y, rival["colors"][1], rmax=66, ttl=0.5))
        if self.mode == "net" and self.net_role == "host":
            self._net_end(1, "crash")

    def _step_rival(self, rival):
        if not rival["alive"]:
            return
        if rival["ai"]:
            d = self._bot_dir(rival)
            if d:
                rival["dir"] = d
        elif rival["queue"]:
            rival["dir"] = rival["queue"].pop(0)
        dx, dy = rival["dir"]
        head = (rival["body"][0][0] + dx, rival["body"][0][1] + dy)
        cheats = rival.get("cheats") or {}
        ghost = bool(cheats.get("ghost"))
        score_mult = 2 if cheats.get("x2") else 1

        outside = not (0 <= head[0] < COLS and 0 <= head[1] < ROWS)
        if outside and (self.wrap or ghost):
            head = (head[0] % COLS, head[1] % ROWS)
            outside = False

        eat = self.food is not None and head == self.food
        eat_special = self.special is not None and head == self.special["pos"]
        eat_power = self.powerup is not None and head == self.powerup["pos"]
        body = rival["body"] if eat else rival["body"][:-1]
        body_blocked = head in body
        world_blocked = (head in self.walls or head in self.meteors
                         or head in self.snake
                         or head in self._other_rival_cells(rival))
        if outside or body_blocked or (world_blocked and not ghost):
            self._kill_rival(rival)
            return

        rival["prev"] = list(rival["body"])
        rival["body"].insert(0, head)
        if not eat:
            rival["body"].pop()

        x, y = self._center_of(head)
        if eat:
            rival["score"] += 10 * score_mult
            rival["apples"] += 1
            self._new_food()
            if self.settings.get("particles"):
                for _ in range(7):
                    self.particles.append(Particle(x, y, rival["colors"][1]))
        if eat_special:
            rival["score"] += 30 * score_mult
            rival["stars"] += 1
            self.special = None
            if self.settings.get("particles"):
                self.rings.append(Ring(x, y, GOLD, rmax=40))
        if eat_power:
            rival["score"] += 15 * score_mult
            rival["powers"] += 1
            self.powerup = None
            if self.settings.get("particles"):
                self.rings.append(Ring(x, y, VIOLET, rmax=40))

    def _step_rivals(self):
        for rival in self.rivals:
            if self.state != "playing":
                return
            if rival["alive"]:
                self._step_rival(rival)

    def _update_respawns(self, dt):
        for rival in self.rivals:
            if not rival["alive"] and rival["respawn"] > 0.0:
                rival["respawn"] -= dt
                if rival["respawn"] <= 0.0:
                    self._respawn_rival(rival)

    def _ai_blocked(self, rival):
        blocked = set(self.walls) | set(self.meteors) | set(self.snake)
        for r in self.rivals:
            if r is not rival and r["alive"]:
                blocked.update(r["body"])
        if rival["body"]:
            blocked.discard(rival["body"][-1])
        if self.snake:
            blocked.discard(self.snake[-1])
        return blocked

    def _bfs_map(self, start, blocked):
        dist = {start: 0}
        dq = deque([start])
        while dq:
            x, y = dq.popleft()
            nd = dist[(x, y)] + 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.wrap:
                    nx %= COLS
                    ny %= ROWS
                elif not (0 <= nx < COLS and 0 <= ny < ROWS):
                    continue
                cell = (nx, ny)
                if cell in dist or cell in blocked:
                    continue
                dist[cell] = nd
                dq.append(cell)
        return dist

    def _open_area(self, start, blocked, limit=48):
        seen = {start}
        dq = deque([start])
        count = 0
        while dq and count < limit:
            x, y = dq.popleft()
            count += 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.wrap:
                    nx %= COLS
                    ny %= ROWS
                elif not (0 <= nx < COLS and 0 <= ny < ROWS):
                    continue
                cell = (nx, ny)
                if cell in seen or cell in blocked:
                    continue
                seen.add(cell)
                dq.append(cell)
        return count

    def _bot_dir(self, rival):
        if not rival["body"]:
            return rival["dir"]
        head = rival["body"][0]
        blocked = self._ai_blocked(rival)
        dist = self._bfs_map(self.food, blocked) if self.food is not None else {}
        best, best_score = None, -1e9
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if d == (-rival["dir"][0], -rival["dir"][1]):
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if self.wrap:
                nx %= COLS
                ny %= ROWS
            elif not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            cell = (nx, ny)
            if cell in blocked:
                continue
            score = 0.0
            if self.food is not None:
                fd = dist.get(cell)
                if fd is not None:
                    score += 260.0 - fd * 5.0
                else:
                    score -= 90.0
            score += self._open_area(cell, blocked, 48) * 1.2
            if d == rival["dir"]:
                score += 3.0
            score += random.random() * 4.0
            if score > best_score:
                best_score, best = score, d
        return best or rival["dir"]

    # ------------------------------------------------ сетевой протокол
    def _net_send_dir(self, d):
        if self.net is None or self.net_role != "client":
            return
        self.net.send({"t": "input", "d": [int(d[0]), int(d[1])]})

    def _net_apply_input(self, msg):
        d = msg.get("d")
        if not (isinstance(d, list) and len(d) == 2):
            return
        try:
            d = (int(d[0]), int(d[1]))
        except (TypeError, ValueError):
            return
        if d not in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            return
        for rival in self.rivals:
            if not rival["ai"]:
                last = rival["queue"][-1] if rival["queue"] else rival["dir"]
                if d == last or (d[0] == -last[0] and d[1] == -last[1]):
                    return
                if len(rival["queue"]) < 2:
                    rival["queue"].append(d)
                return

    def _net_send_loadout(self):
        if self.net is not None and self.net_role == "client":
            self.net.send({"t": "loadout", "sk": self.player_skin,
                           "ch": self._cheat_payload()})

    def _net_apply_loadout(self, msg):
        if self.net_role != "host" or not self.rivals:
            return
        rival = self.rivals[0]
        skin = valid_skin_id(msg.get("sk"))
        flags = default_cheat_flags()
        raw = msg.get("ch")
        if isinstance(raw, dict):
            for cid in flags:
                flags[cid] = bool(raw.get(cid))
        rival["skin"] = skin
        rival["colors"] = self._skin_palette(skin, self.time)
        rival["cheats"] = flags
        rival["revives"] = 1 if flags.get("revive") else 0
        base = SPECIAL_EVERY.get(self.settings.get("specials"), 4)
        if flags.get("lucky"):
            self.special_every = min(self.special_every, max(2, base - 2))

    def _net_snake_state(self):
        if self.rivals:
            guest = self.rivals[0]
            p2 = {"b": [list(c) for c in guest["body"]],
                  "pv": [list(c) for c in guest["prev"]],
                  "d": list(guest["dir"]), "s": guest["score"],
                  "a": guest["apples"], "st": guest["stars"],
                  "pw": guest["powers"],
                  "sk": guest.get("skin") or "classic",
                  "ch": self._cheat_payload(guest.get("cheats") or {})}
        else:
            p2 = {"b": [], "pv": [], "d": [1, 0], "s": 0,
                  "a": 0, "st": 0, "pw": 0,
                  "sk": "classic", "ch": default_cheat_flags()}
        return p2

    def _net_host_send(self, dt, force=False):
        if self.net is None or self.net_role != "host":
            return
        self.net_send_timer -= dt
        if self.net_send_timer > 0.0 and not force:
            return
        self.net_send_timer = 0.05
        msg = {
            "t": "state",
            "p1": {"b": [list(c) for c in self.snake],
                   "pv": [list(c) for c in self.prev_snake],
                   "d": list(self.dir), "s": self.score,
                   "sk": self.player_skin,
                   "ch": self._cheat_payload()},
            "p2": self._net_snake_state(),
            "food": list(self.food) if self.food else None,
            "sp": ({"pos": list(self.special["pos"]),
                    "left": round(self.special["left"], 2),
                    "ttl": self.special["ttl"]} if self.special else None),
            "pu": ({"pos": list(self.powerup["pos"]),
                    "kind": self.powerup["kind"],
                    "left": round(self.powerup["left"], 2),
                    "ttl": self.powerup["ttl"]} if self.powerup else None),
            "eff": {k: round(v, 2) for k, v in self.effects.items() if v > 0.0},
            "tl": round(self.time_left, 2) if self.time_left is not None else None,
            "rt": round(self.run_time, 2),
            "iv": round(self.interval, 4),
        }
        self.net.send(msg)

    def _apply_net_state(self, msg):
        if self.mode != "net" or self.net_role != "client" or self.state == "dead":
            return
        p2 = msg.get("p2") or {}
        body = parse_cells(p2.get("b"))
        prev = parse_cells(p2.get("pv"))
        if body:
            self.snake = body
            self.prev_snake = prev or list(body)
        self.dir = valid_dir(p2.get("d"), self.dir)
        self.score = safe_int(p2.get("s", self.score), self.score)
        self.apples = safe_int(p2.get("a", self.apples), self.apples)
        self.stars = safe_int(p2.get("st", self.stars), self.stars)
        self.powers = safe_int(p2.get("pw", self.powers), self.powers)

        p1 = msg.get("p1") or {}
        host_body = parse_cells(p1.get("b"))
        host_prev = parse_cells(p1.get("pv"))
        host_skin = valid_skin_id(p1.get("sk") or "classic")
        host_flags = default_cheat_flags()
        raw_flags = p1.get("ch")
        if isinstance(raw_flags, dict):
            for cid in host_flags:
                host_flags[cid] = bool(raw_flags.get(cid))
        host_colors = self._skin_palette(host_skin, self.time)
        if not self.rivals:
            rival = self._make_rival("ХОСТ", host_colors, host_body or [],
                                     tuple(p1.get("d") or (1, 0)))
            rival["ai"] = False
            self.rivals = [rival]
        rival = self.rivals[0]
        if host_body:
            rival["body"] = host_body
            rival["prev"] = host_prev or list(host_body)
        rival["dir"] = valid_dir(p1.get("d"), rival["dir"])
        rival["score"] = safe_int(p1.get("s", rival["score"]), rival["score"])
        rival["skin"] = host_skin
        rival["colors"] = host_colors
        rival["cheats"] = host_flags
        rival["revives"] = 1 if host_flags.get("revive") else 0

        self.food = tuple(msg["food"]) if msg.get("food") else None
        sp = msg.get("sp")
        self.special = ({"pos": tuple(sp["pos"]), "left": float(sp.get("left", 0)),
                         "ttl": float(sp.get("ttl", 7.5))} if sp else None)
        pu = msg.get("pu")
        self.powerup = ({"pos": tuple(pu["pos"]), "kind": pu.get("kind", "shield"),
                         "left": float(pu.get("left", 0)),
                         "ttl": float(pu.get("ttl", 9.0))} if pu else None)
        eff = msg.get("eff") or {}
        self.effects = {k: float(eff.get(k, 0.0)) for k in EFFECT_INFO}
        tl = msg.get("tl")
        self.time_left = float(tl) if tl is not None else None
        self.run_time = float(msg.get("rt", self.run_time))
        self.interval = float(msg.get("iv", self.interval))
        self.t_render = 0.0
        self.net_have_state = True

    def _net_end(self, winner, reason="crash"):
        if self.mode != "net" or self.net_role != "host" or self.net_over:
            return
        self.net_over = True
        self.net_winner = winner
        self.net_won = (winner == 1)
        self.death_reason = reason
        if self.state == "playing":
            self.state = "dead"
            self.dead_at = self.time
            self.prev_snake = list(self.snake)
            self.t_render = 0.0
            if self.settings.get("shake"):
                self.shake = 12.0
            self.flash = 0.9
        self._commit_best()
        self.net.send({"t": "over", "winner": winner, "reason": reason,
                       "s1": self.score,
                       "s2": self.rivals[0]["score"] if self.rivals else 0})

    def _net_end_client(self, msg):
        if self.mode != "net" or self.net_role != "client" or self.net_over \
                or self.state == "dead":
            return
        self.net_over = True
        self.net_winner = safe_int(msg.get("winner", 0), 0)
        self.net_won = (self.net_winner == 2)
        self.score = safe_int(msg.get("s2", self.score), self.score)
        if self.rivals:
            self.rivals[0]["score"] = safe_int(
                msg.get("s1", self.rivals[0]["score"]), self.rivals[0]["score"])
        self.death_reason = msg.get("reason", "crash")
        self.state = "dead"
        self.dead_at = self.time
        self.prev_snake = list(self.snake)
        self.t_render = 0.0
        if self.settings.get("shake"):
            self.shake = 12.0
        self.flash = 0.9
        self._commit_best()

    def _net_disconnect(self):
        if self.state == "playing":
            self.net_lost = True
            self.death_reason = "netlost"
            self.state = "dead"
            self.dead_at = self.time
            self._commit_best()
        self.net_last_role = self.net_role
        self.stop_net()

    def _poll_net_link(self):
        if self.net is None:
            return
        while True:
            try:
                msg = self.net.events.get_nowait()
            except queue.Empty:
                break
            kind = msg.get("t")
            if kind == "input" and self.net_role == "host":
                self._net_apply_input(msg)
            elif kind == "loadout" and self.net_role == "host":
                self._net_apply_loadout(msg)
            elif kind == "state" and self.net_role == "client":
                self._apply_net_state(msg)
            elif kind == "over" and self.net_role == "client":
                self._net_end_client(msg)
            elif kind == "closed":
                self._net_disconnect()
                break

    def _net_client_frame(self, dt):
        self._poll_net_link()
        if self.state != "playing":
            return
        if self.net_have_state:
            self.t_render = min(1.0, self.t_render + dt / 0.05)

    # ------------------------------------------------ игровой цикл
    def loop(self):
        if not self.running:
            return
        started = time.perf_counter()
        dt = min(0.05, started - self.last)
        self.last = started
        try:
            self._loop_errors = 0
            self.update(dt)
            self.render()
        except tk.TclError:
            self.running = False
            return
        except Exception:
            _write_error(traceback.format_exc())
            self._loop_errors += 1
            if self._loop_errors >= 5:
                self.running = False
                return
        if self.running:
            # целимся в ~60 кадров/с
            spent = (time.perf_counter() - started) * 1000.0
            self.root.after(max(1, int(16 - spent)), self.loop)

    def update(self, dt):
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 42)
        self.flash = max(0.0, self.flash - dt * 2.0)
        self.score_pulse = max(0.0, self.score_pulse - dt * 3.5)

        for a in self.ambient:
            a.update(dt)
        self.particles = [p for p in self.particles if p.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]
        self.floats = [f for f in self.floats if f.update(dt)]

        if self.state in ("netwait", "netconnect"):
            self._poll_lobby()
            return

        if self.state != "playing":
            return

        if self.mode == "net":
            if self.net_role == "client":
                self._net_client_frame(dt)
                return
            if self.net_role == "host":
                self._poll_net_link()
                if self.state != "playing":
                    return

        if self.time_left is not None:
            self.time_left = max(0.0, self.time_left - dt)
            if self.time_left <= 0:
                if self.mode == "net" and self.net_role == "host":
                    opp = self.rivals[0]["score"] if self.rivals else 0
                    self._net_end(1 if self.score >= opp else 2, "time")
                else:
                    self.die("time")
                return

        self.run_time += dt

        for key in self.effects:
            if self.effects[key] > 0.0:
                self.effects[key] = max(0.0, self.effects[key] - dt)
                if self.effects[key] == 0.0:
                    self._puff(self.snake[0], EFFECT_INFO[key][1])

        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 1

        if self.special:
            self.special["left"] -= dt
            if self.special["left"] <= 0:
                self._puff(self.special["pos"], GOLD)
                self.special = None

        if self.powerup:
            self.powerup["left"] -= dt
            if self.powerup["left"] <= 0:
                self._puff(self.powerup["pos"], EFFECT_INFO[self.powerup["kind"]][1])
                self.powerup = None

        if self.meteors:
            gone = []
            for cell in list(self.meteors.keys()):
                self.meteors[cell] -= dt
                if self.meteors[cell] <= 0:
                    gone.append(cell)
            for cell in gone:
                del self.meteors[cell]
                self._puff(cell, ORANGE)

        if self.mode == "chaos" and self.event_timer is not None:
            self.event_timer -= dt
            if self.event_timer <= 0:
                self.event_timer = random.uniform(7.0, 10.5)
                self._chaos_event()

        if self.pending_eats:
            waiting = []
            for pe in self.pending_eats:
                pe["delay"] -= dt
                if pe["delay"] <= 0:
                    self._eating_fx(pe["cell"], pe["color"], pe["text"], pe["tcolor"])
                else:
                    waiting.append(pe)
            self.pending_eats = waiting

        self.acc += dt
        steps = 0
        while self.acc >= self.interval and steps < 4 and self.state == "playing":
            self.acc -= self.interval
            self.step()
            if self.mode in ("bots", "net") and self.state == "playing":
                self._step_rivals()
            steps += 1
        if self.state == "playing":
            self.t_render = min(1.0, self.acc / self.interval)
            if self.mode == "bots":
                self._update_respawns(dt)
            elif self.mode == "net" and self.net_role == "host":
                self._net_host_send(dt)

    def step(self):
        if self.queue:
            self.dir = self.queue.pop(0)
        dx, dy = self.dir
        hx, hy = self.snake[0]
        head = (hx + dx, hy + dy)

        outside = not (0 <= head[0] < COLS and 0 <= head[1] < ROWS)
        invincible = self.effects.get("shield", 0.0) > 0.0
        ghost = bool(self.cheats.get("ghost"))
        if outside and (self.wrap or invincible or ghost):
            head = (head[0] % COLS, head[1] % ROWS)
            outside = False

        eat_normal = self.food is not None and head == self.food
        eat_special = self.special is not None and head == self.special["pos"]
        eat_power = self.powerup is not None and head == self.powerup["pos"]
        grow = (1 if eat_normal else 0) + (2 if eat_special else 0)

        body = self.snake if grow else self.snake[:-1]
        body_blocked = head in body
        world_blocked = (head in self.walls or head in self.meteors
                         or head in self._rival_cells())
        if outside or (body_blocked and not invincible) or \
                (world_blocked and not invincible and not ghost):
            self.die()
            return

        self.prev_snake = list(self.snake)
        self.snake.insert(0, head)
        if grow:
            for _ in range(grow - 1):
                self.snake.append(self.snake[-1])
        else:
            self.snake.pop()

        if eat_normal:
            self._eat_food(head)
        if eat_special:
            self._eat_special(head)
        if eat_power:
            self._eat_power(head)

        base = max(self.min_int, self.base_int - self.ramp * (len(self.snake) - 4))
        scale = 1.0
        if self.effects.get("slow", 0.0) > 0.0:
            scale *= 1.42
        if self.effects.get("surge", 0.0) > 0.0:
            scale *= 0.78
        self.interval = max(0.062, min(0.38, base * scale))

    def _eat_food(self, cell):
        if self.combo_timer > 0:
            self.combo = min(5, self.combo + 1)
        else:
            self.combo = 1
        self.combo_timer = 2.5 if self.mode in ("blitz", "chaos") else 3.0
        self.max_combo = max(self.max_combo, self.combo)
        mult = 2 if self.effects.get("double", 0.0) > 0.0 else 1
        gain = 10 * self.combo * mult * self.score_mult
        self.score += gain
        self.score_pulse = 1.0
        self.apples += 1
        self._new_food()
        every = self.special_every
        if self.apples % every == 0 and self.special is None:
            self._new_special()
        if self.mode != "net" and self.apples % self.power_every == 0 \
                and self.powerup is None:
            self._new_power()
        text = "+%d" % gain + ("  x%d" % self.combo if self.combo > 1 else "")
        self.pending_eats.append({"cell": cell, "color": "#ff5d8f", "text": text,
                                  "tcolor": "#ffd0dd", "delay": self.interval,
                                  "special": False})
        self.play_sound("eat")

    def _eat_special(self, cell):
        mult = 2 if self.effects.get("double", 0.0) > 0.0 else 1
        gain = 30 * max(1, self.combo) * mult * self.score_mult
        self.score += gain
        self.score_pulse = 1.0
        self.stars += 1
        self.special = None
        if self.settings.get("shake"):
            self.shake = max(self.shake, 5.0)
        self.pending_eats.append({"cell": cell, "color": GOLD, "text": "+%d  *" % gain,
                                  "tcolor": "#fff0b8", "delay": self.interval,
                                  "special": True})
        self.play_sound("special")

    def _eat_power(self, cell):
        kind = self.powerup["kind"] if self.powerup else "shield"
        self.powerup = None
        dur = POWER_DURATION.get(kind, 8.0)
        self.effects[kind] = max(self.effects.get(kind, 0.0), dur)
        gain = 15 * self.score_mult
        self.score += gain
        self.score_pulse = 1.0
        self.powers += 1
        color = EFFECT_INFO[kind][1]
        if self.settings.get("shake"):
            self.shake = max(self.shake, 3.0)
        self.pending_eats.append({"cell": cell, "color": color,
                                  "text": POWER_TEXT.get(kind, "БОНУС") + "  +%d" % gain,
                                  "tcolor": mix(color, "#ffffff", 0.45),
                                  "delay": self.interval, "special": False,
                                  "pkind": kind})
        self.play_sound("special")

    def _spawn_meteors(self, count):
        head = self.snake[0]
        blocked = set(self.snake) | self.walls | set(self.meteors)
        if self.food:
            blocked.add(self.food)
        if self.special:
            blocked.add(self.special["pos"])
        if self.powerup:
            blocked.add(self.powerup["pos"])
        placed = 0
        for _ in range(140):
            if placed >= count:
                break
            cell = (random.randrange(COLS), random.randrange(ROWS))
            if cell in blocked:
                continue
            if abs(cell[0] - head[0]) + abs(cell[1] - head[1]) < 5:
                continue
            self.meteors[cell] = random.uniform(7.0, 9.5)
            blocked.add(cell)
            placed += 1

    def _chaos_event(self):
        kind = random.choice(CHAOS_EVENTS)
        cx, cy = FX + FIELD_W / 2, FY + 38
        if kind == "meteor":
            self._spawn_meteors(random.randint(3, 5))
            self.floats.append(FloatText(cx, cy, "МЕТЕОРИТЫ!", ORANGE))
            if self.settings.get("shake"):
                self.shake = max(self.shake, 5.0)
            self.play_sound("special")
        elif kind == "surge":
            self.effects["surge"] = max(self.effects.get("surge", 0.0), 5.0)
            self.floats.append(FloatText(cx, cy, "ТУРБО!", GOLD))
            self.play_sound("menu")
        else:
            if self.special is None:
                self._new_special()
                self.floats.append(FloatText(cx, cy, "ЗВЕЗДОПАД!", GOLD))
            else:
                self._spawn_meteors(2)
                self.floats.append(FloatText(cx, cy, "МЕТЕОРИТЫ!", ORANGE))
            self.play_sound("menu")

    def _center_of(self, cell):
        return FX + (cell[0] + 0.5) * CELL, FY + (cell[1] + 0.5) * CELL

    def _eating_fx(self, cell, color, text, text_color):
        x, y = self._center_of(cell)
        if self.settings.get("particles"):
            for _ in range(16):
                self.particles.append(Particle(x, y, color))
            self.rings.append(Ring(x, y, color))
        self.floats.append(FloatText(x, y - 10, text, text_color))
        self.flash = max(self.flash, 0.8)

    def _puff(self, cell, color):
        if not self.settings.get("particles"):
            return
        x, y = self._center_of(cell)
        for _ in range(10):
            self.particles.append(Particle(x, y, color))

    def _respawn_player(self):
        cells = self._free_cells()
        random.shuffle(cells)
        for cell in cells:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                body = []
                ok = True
                for i in range(4):
                    c = (cell[0] - d[0] * i, cell[1] - d[1] * i)
                    if self.wrap:
                        c = (c[0] % COLS, c[1] % ROWS)
                    elif not (0 <= c[0] < COLS and 0 <= c[1] < ROWS):
                        ok = False
                        break
                    if c in self.walls or c in self.meteors or \
                            c in self._rival_cells():
                        ok = False
                        break
                    body.append(c)
                if ok:
                    self.snake = body
                    self.prev_snake = list(body)
                    self.dir = d
                    self.queue = []
                    return True
        return False

    def die(self, reason="crash"):
        if self.state != "playing":
            return
        if self.revives > 0 and reason != "time" and self._respawn_player():
            self.revives -= 1
            self.combo = 1
            self.combo_timer = 0.0
            self.acc = 0.0
            self.t_render = 0.0
            self.queue = []
            x, y = self._center_of(self.snake[0])
            self.rings.append(Ring(x, y, GOLD, rmax=60, ttl=0.6))
            self.floats.append(FloatText(x, y - 18, "ВТОРОЙ ШАНС!", GOLD))
            self.flash = 0.7
            self.play_sound("special")
            return
        self.state = "dead"
        self.death_reason = reason
        self.dead_at = self.time
        self.prev_snake = list(self.snake)
        self.t_render = 0.0
        if self.settings.get("shake"):
            self.shake = 15.0
        self.flash = 1.0
        self.combo = 1
        self.combo_timer = 0.0
        self.effects = {k: 0.0 for k in EFFECT_INFO}

        head_x, head_y = self._center_of(self.snake[0])
        if self.settings.get("particles"):
            for seg in self.snake:
                x, y = self._center_of(seg)
                self.particles.append(Particle(x, y, mix(CYAN, VIOLET, random.random())))
            for _ in range(24):
                self.particles.append(Particle(head_x, head_y, MAGENTA))
            self.rings.append(Ring(head_x, head_y, MAGENTA, rmax=95, ttl=0.6))

        for pe in self.pending_eats:
            self._eating_fx(pe["cell"], pe["color"], pe["text"], pe["tcolor"])
        self.pending_eats = []

        if self.mode == "net" and self.net_role == "host":
            self._net_end(2, reason)
        else:
            self._commit_best()
        self.play_sound("die")

    def _commit_best(self):
        if self.score > self.bests.get(self.mode, 0):
            self.bests[self.mode] = self.score
            self.new_record = True
            self.save_game()
        else:
            self.new_record = False
        self.grant_coins()

    # ------------------------------------------------ ввод
    def on_key(self, e):
        ks = e.keysym.lower()
        up = ks in ("up", "w", "ц")
        down = ks in ("down", "s", "ы")
        left = ks in ("left", "a", "ф")
        right = ks in ("right", "d", "в")
        enter = ks in ("space", "return", "kp_enter")

        if self.state == "menu":
            if up:
                self.menu_sel = (self.menu_sel - 1) % 5
                self.play_sound("menu")
            elif down:
                self.menu_sel = (self.menu_sel + 1) % 5
                self.play_sound("menu")
            elif enter:
                self._menu_action()
            elif ks == "escape":
                self.close()
            elif ks in ("1", "2", "3", "4", "5", "6"):
                self._pick_mode(int(ks) - 1)

        elif self.state == "modes":
            if up or down:
                step = -1 if up else 1
                self.modes_sel = (self.modes_sel + step) % len(MODES)
                self.play_sound("menu")
            elif enter:
                self._pick_mode(self.modes_sel)
            elif ks in ("1", "2", "3", "4", "5", "6"):
                self._pick_mode(int(ks) - 1)
            elif ks == "escape":
                self.back_to_menu()

        elif self.state == "netmenu":
            if up:
                self.net_menu_sel = (self.net_menu_sel - 1) % 3
                self.play_sound("menu")
            elif down:
                self.net_menu_sel = (self.net_menu_sel + 1) % 3
                self.play_sound("menu")
            elif enter:
                self._net_menu_action()
            elif ks == "escape":
                self.back_to_menu()

        elif self.state in ("netwait", "netconnect"):
            if ks == "escape":
                self.stop_net()
                self.state = "netmenu"
                self.net_status = ""
                self.play_sound("menu")

        elif self.state == "shop":
            count = self._shop_item_count()
            if ks in ("d", "в"):
                self.claim_daily()
            elif left:
                self.shop_tab = (self.shop_tab - 1) % 3
                self.shop_sel = 0
                self.shop_status = ""
                self.play_sound("menu")
            elif right:
                self.shop_tab = (self.shop_tab + 1) % 3
                self.shop_sel = 0
                self.shop_status = ""
                self.play_sound("menu")
            elif up:
                self.shop_sel = (self.shop_sel - 1) % count
                self.play_sound("menu")
            elif down:
                self.shop_sel = (self.shop_sel + 1) % count
                self.play_sound("menu")
            elif enter:
                self._shop_action()
            elif ks == "escape":
                self.back_to_menu()

        elif self.state == "settings":
            rows = len(SETTING_ROWS) + 2
            if up:
                self.settings_sel = (self.settings_sel - 1) % rows
                self.reset_confirm = False
            elif down:
                self.settings_sel = (self.settings_sel + 1) % rows
                self.reset_confirm = False
            elif left:
                self._cycle_setting(-1)
            elif right:
                self._cycle_setting(1)
            elif enter:
                if self.settings_sel < len(SETTING_ROWS):
                    self._cycle_setting(1)
                elif self.settings_sel == len(SETTING_ROWS):
                    self._reset_records()
                else:
                    self.back_to_menu()
            elif ks == "escape":
                self.back_to_menu()

        elif self.state == "playing":
            d = DIR_KEYS.get(ks)
            if self.mode == "net":
                if d:
                    if self.net_role == "host":
                        self.enqueue_dir(d)
                    elif self.net_role == "client" and self.net_have_state:
                        self._net_send_dir(d)
                    return
                if ks == "escape":
                    self.leave_net()
                return
            if d:
                self.enqueue_dir(d)
                return
            if ks in ("space", "p", "з"):
                self.state = "paused"
            elif ks == "escape":
                self.to_menu()
            elif ks in ("r", "к"):
                self.start_game()

        elif self.state == "paused":
            if ks in ("space", "p", "з", "return"):
                self.state = "playing"
            elif ks == "escape":
                self.to_menu()
            elif ks in ("r", "к"):
                self.start_game()

        elif self.state == "dead":
            if self.time - self.dead_at < 0.45:
                return
            if self.mode == "net":
                if ks in ("space", "return", "kp_enter", "escape"):
                    self.leave_net()
                elif ks in ("m", "ь"):
                    self.leave_net()
                    self.open_modes()
                return
            if ks in ("space", "return", "kp_enter", "r", "к"):
                self.start_game()
            elif ks in ("m", "ь"):
                self.open_modes()
            elif ks == "escape":
                self.to_menu()

    def _menu_action(self):
        if self.menu_sel == 0:
            self.start_game()
        elif self.menu_sel == 1:
            self.open_modes()
        elif self.menu_sel == 2:
            self.open_shop()
        elif self.menu_sel == 3:
            self.open_settings()
        else:
            self.close()

    def _pick_mode(self, idx):
        if not (0 <= idx < len(MODES)):
            return
        self.modes_sel = idx
        self.mode = MODES[idx][0]
        self.save_game()
        if self.mode == "net":
            self.open_netmenu()
        else:
            self.start_game()

    def _setting_value(self, key):
        if key == "speed":
            return self.settings["speed"]
        if key == "specials":
            return self.settings["specials"]
        if key == "wrap":
            return "Телепорт" if self.settings["wrap"] else "Смертельные"
        return "Вкл" if self.settings.get(key) else "Выкл"

    def _cycle_setting(self, delta):
        if self.settings_sel >= len(SETTING_ROWS):
            return
        key = SETTING_ROWS[self.settings_sel][0]
        if key == "speed":
            names = list(SPEED_NAMES)
            cur = names.index(self.settings["speed"]) if self.settings["speed"] in names else 1
            self.settings["speed"] = names[(cur + delta) % len(names)]
        elif key == "specials":
            names = list(SPECIAL_NAMES)
            cur = names.index(self.settings["specials"]) if self.settings["specials"] in names else 1
            self.settings["specials"] = names[(cur + delta) % len(names)]
        else:
            self.settings[key] = not self.settings.get(key)
        self._after_setting(key)

    def _after_setting(self, key):
        if key == "grid":
            self._refresh_grid()
        elif key == "particles" and not self.settings["particles"]:
            self.particles.clear()
            self.rings.clear()
        elif key == "sound" and self.settings["sound"]:
            self.play_sound("special")
        elif key == "wrap":
            # стены/телепорт применятся в следующем забеге
            pass
        self.save_game()

    def _reset_records(self):
        if not self.reset_confirm:
            self.reset_confirm = True
            return
        self.bests = {m[0]: 0 for m in MODES}
        self.reset_confirm = False
        self.save_game()
        self.play_sound("die")

    def enqueue_dir(self, d):
        last = self.queue[-1] if self.queue else self.dir
        if d == last or (d[0] == -last[0] and d[1] == -last[1]):
            return
        if len(self.queue) < 2:
            self.queue.append(d)

    def on_blur(self, _event=None):
        if self.state == "playing" and self.mode != "net":
            self.state = "paused"
    # ------------------------------------------------ рисование: обёртки
    def _o(self, *a, **kw):
        kw["tags"] = "dyn"
        return self.canvas.create_oval(*a, **kw)

    def _l(self, *a, **kw):
        kw["tags"] = "dyn"
        return self.canvas.create_line(*a, **kw)

    def _p(self, *a, **kw):
        kw["tags"] = "dyn"
        return self.canvas.create_polygon(*a, **kw)

    def _t(self, *a, **kw):
        kw["tags"] = "dyn"
        return self.canvas.create_text(*a, **kw)

    def _a(self, *a, **kw):
        kw["tags"] = "dyn"
        return self.canvas.create_arc(*a, **kw)

    def rrect(self, x0, y0, x1, y1, r=10, fill="", outline="", width=1):
        return self._p(*rr_pts(x0, y0, x1, y1, r), fill=fill,
                       outline=outline or fill, width=width,
                       smooth=True, splinesteps=4)

    # ------------------------------------------------ статичный фон
    def _draw_static(self):
        c = self.canvas
        for y in range(0, WIN_H, 4):
            col = mix(BG_TOP, BG_BOT, y / WIN_H)
            c.create_rectangle(0, y, WIN_W, y + 4, fill=col, outline="")

        # мягкое свечение вокруг поля
        for pad, t, w in ((13, 0.05, 3), (20, 0.025, 2)):
            c.create_polygon(*rr_pts(FX - 14 - pad, FY - 14 - pad,
                                     FX + FIELD_W + 14 + pad, FY + FIELD_H + 14 + pad, 22),
                             fill="", outline=mix("#060b16", CYAN, t),
                             width=w, smooth=True)
        # рамка
        c.create_polygon(*rr_pts(FX - 14, FY - 14, FX + FIELD_W + 14, FY + FIELD_H + 14, 20),
                         fill="#060b16", outline="#0e1b30", width=1, smooth=True)
        # поле
        c.create_rectangle(FX, FY, FX + FIELD_W, FY + FIELD_H,
                           fill=FIELD_BG, outline="#16243d", width=2)
        self._refresh_grid()

        # угловые скобки
        L, off = 26, 6
        corners = (
            ((FX - off, FY + L), (FX - off, FY - off), (FX + L, FY - off), CYAN),
            ((FX + FIELD_W - L, FY - off), (FX + FIELD_W + off, FY - off),
             (FX + FIELD_W + off, FY + L), VIOLET),
            ((FX - off, FY + FIELD_H - L), (FX - off, FY + FIELD_H + off),
             (FX + L, FY + FIELD_H + off), VIOLET),
            ((FX + FIELD_W - L, FY + FIELD_H + off), (FX + FIELD_W + off, FY + FIELD_H + off),
             (FX + FIELD_W + off, FY + FIELD_H - L), CYAN),
        )
        for *pts, col in corners:
            flat = [v for p in pts for v in p]
            c.create_line(*flat, fill=mix(col, BG_TOP, 0.72), width=6,
                          capstyle="round", joinstyle="round")
            c.create_line(*flat, fill=col, width=2.5,
                          capstyle="round", joinstyle="round")

        # подписи HUD рисуются динамически (см. draw_hud)

        c.create_text(WIN_W // 2, FY + FIELD_H + 36,
                      text="← ↑ → ↓  /  WASD — движение      •      "
                           "ПРОБЕЛ — пауза      •      R — заново      •      ESC — меню",
                      font=(F_UI, 9), fill="#42526f")

    def _refresh_grid(self):
        self.canvas.delete("staticgrid")
        if not self.settings.get("grid", True):
            return
        for i in range(COLS + 1):
            x = FX + i * CELL
            self.canvas.create_line(x, FY, x, FY + FIELD_H,
                                    fill="#0b182a", tags="staticgrid")
        for j in range(ROWS + 1):
            y = FY + j * CELL
            self.canvas.create_line(FX, y, FX + FIELD_W, y,
                                    fill="#0b182a", tags="staticgrid")

    # ------------------------------------------------ змейка
    def _segments(self, body, prev_body, ox, oy, t):
        pts, cols, sizes = [], [], []
        n = len(body)
        if not prev_body:
            prev_body = body
        for i, cell in enumerate(body):
            prev = prev_body[i] if i < len(prev_body) else prev_body[-1]
            if abs(cell[0] - prev[0]) > 1 or abs(cell[1] - prev[1]) > 1:
                gx, gy = cell            # телепорт сквозь край: без растягивания
            else:
                gx = prev[0] + (cell[0] - prev[0]) * t
                gy = prev[1] + (cell[1] - prev[1]) * t
            pts.append((FX + (gx + 0.5) * CELL + ox, FY + (gy + 0.5) * CELL + oy))
            f = i / max(1, n - 1)
            if f < 0.5:
                col = mix(HEAD_C, MID_C, f * 2)
            else:
                col = mix(MID_C, TAIL_C, (f - 0.5) * 2)
            cols.append(col)
            sizes.append(CELL * 0.92 - (CELL * 0.92 - CELL * 0.58) * (f ** 0.75))
        return pts, cols, sizes

    def draw_walls(self, ox, oy):
        for gx, gy in self.walls:
            x = FX + (gx + 0.5) * CELL + ox
            y = FY + (gy + 0.5) * CELL + oy
            self.rrect(x - CELL / 2 + 2.5, y - CELL / 2 + 2.5,
                       x + CELL / 2 - 2.5, y + CELL / 2 - 2.5, 6,
                       fill="#0d1830", outline="#24365e", width=2)
            self.rrect(x - 6, y - 6, x + 6, y + 6, 4,
                       fill="", outline=mix(VIOLET, FIELD_BG, 0.62), width=1)

    def draw_meteors(self, ox, oy):
        for (gx, gy), ttl in self.meteors.items():
            if ttl < 1.3 and math.sin(self.time * 18 + gx) < 0:
                continue
            x = FX + (gx + 0.5) * CELL + ox
            y = FY + (gy + 0.5) * CELL + oy
            pulse = 0.5 + 0.5 * math.sin(self.time * 7.5 + gx * 0.8 + gy * 0.5)
            s = CELL / 2 - 2.5
            self.rrect(x - s - 4, y - s - 4, x + s + 4, y + s + 4, 9,
                       fill=mix(FIELD_BG, ORANGE, 0.10 + 0.12 * pulse), outline="")
            self.rrect(x - s, y - s, x + s, y + s, 7,
                       fill=mix("#3a1908", ORANGE, 0.30 + 0.28 * pulse),
                       outline=mix(ORANGE, "#ffe2bd", 0.20 + 0.45 * pulse),
                       width=2)
            self._o(x - 4.5, y - 4.5, x + 4.5, y + 4.5,
                    fill=mix(ORANGE, "#fff1d6", 0.55), outline="")

    def draw_snake(self, ox, oy, t):
        palette = self._skin_palette(self.player_skin, self.time)
        if self.mode in ("bots", "net"):
            label = "ТЫ"
        else:
            label = None
        self._draw_snake(self.snake, self.prev_snake, self.dir,
                         palette, ox, oy, t, label)

    def draw_rivals(self, ox, oy, t):
        for rival in self.rivals:
            if rival["alive"] and rival["body"]:
                skin = rival.get("skin")
                palette = (self._skin_palette(skin, self.time)
                           if skin else rival["colors"])
                self._draw_snake(rival["body"], rival["prev"], rival["dir"],
                                 palette, ox, oy, t, rival["name"])

    def _draw_snake(self, body, prev_body, direction, palette, ox, oy, t, label=None):
        if not body:
            return
        pts, cols, sizes = self._segments(body, prev_body, ox, oy, t)
        n = len(pts)
        head_c, mid_c, tail_c = palette[0], palette[1], palette[2]

        for i in range(n):
            f = i / max(1, n - 1)
            if f < 0.5:
                cols[i] = mix(head_c, mid_c, f * 2)
            else:
                cols[i] = mix(mid_c, tail_c, (f - 0.5) * 2)

        for i in range(n - 1, 0, -1):
            x1, y1 = pts[i]
            x2, y2 = pts[i - 1]
            if abs(x2 - x1) > CELL * 1.6 or abs(y2 - y1) > CELL * 1.6:
                continue                 # разрыв на краю при телепорте
            self._l(x1, y1, x2, y2,
                    fill=mix(cols[i], FIELD_BG, 0.10),
                    width=max(4, int(min(sizes[i], sizes[i - 1]) * 0.98)),
                    capstyle="round")

        for i in range(n - 1, -1, -1):
            x, y = pts[i]
            s = sizes[i]
            self.rrect(x - s / 2 - 3.5, y - s / 2 - 3.5, x + s / 2 + 3.5, y + s / 2 + 3.5,
                       r=(s + 7) / 2.6, fill=mix(cols[i], FIELD_BG, 0.82), outline="")
            self.rrect(x - s / 2, y - s / 2, x + s / 2, y + s / 2,
                       r=s / 2.6, fill=cols[i], outline="")

        hx, hy = pts[0]
        dx, dy = direction
        px, py = -dy, dx

        # язык
        if math.sin(self.time * 3.1) > 0.55:
            bx, by = hx + dx * (sizes[0] / 2 + 1), hy + dy * (sizes[0] / 2 + 1)
            ex, ey = bx + dx * 8, by + dy * 8
            self._l(bx, by, ex, ey, fill="#ff7fb0", width=2, capstyle="round")
            for side in (-1, 1):
                self._l(ex, ey, ex + dx * 4 + px * 3.2 * side,
                        ey + dy * 4 + py * 3.2 * side,
                        fill="#ff7fb0", width=2, capstyle="round")

        # глаза
        for side in (-1, 1):
            ex = hx + dx * 3.5 + px * 5.2 * side
            ey = hy + dy * 3.5 + py * 5.2 * side
            self._o(ex - 4.2, ey - 4.2, ex + 4.2, ey + 4.2, fill="#f4ffff", outline="")
            qx = ex + dx * 1.3
            qy = ey + dy * 1.3
            self._o(qx - 2.1, qy - 2.1, qx + 2.1, qy + 2.1, fill="#06121f", outline="")

        if label:
            ly = max(FY + 9, hy - 17)
            self._t(hx, ly, text=label, font=(F_UI, 7, "bold"),
                    fill=mix(mid_c, "#ffffff", 0.35))

    # ------------------------------------------------ еда
    def _draw_apple(self, x, y):
        pulse = 0.5 + 0.5 * math.sin(self.time * 5.2)
        base = 10.5 + 1.4 * pulse
        for rr, t in ((base + 9, 0.12), (base + 4.5, 0.26), (base + 1.5, 0.5)):
            self._o(x - rr, y - rr, x + rr, y + rr,
                    fill=mix("#ff4d79", FIELD_BG, 1 - t), outline="")
        self._o(x - base, y - base, x + base, y + base,
                fill="#ff4d79", outline="")
        self._o(x - base * 0.55, y - base * 0.62,
                x - base * 0.55 + 5, y - base * 0.62 + 5,
                fill="#ffc6d6", outline="")
        self._p(x + 1, y - base - 2, x + 8, y - base - 7, x + 9, y - base + 1,
                fill="#6bff9e", outline="")

    def _draw_star(self, x, y, left=None, ttl=None):
        for rr, t in ((24, 0.10), (19, 0.22)):
            self._o(x - rr, y - rr, x + rr, y + rr,
                    fill=mix(GOLD, FIELD_BG, 1 - t), outline="")
        rot = self.time * 1.6
        pts = []
        for k in range(10):
            ang = rot + k * math.pi / 5
            rad = 12.5 if k % 2 == 0 else 5.8
            pts.extend((x + math.cos(ang) * rad, y + math.sin(ang) * rad))
        self._p(*pts, fill=GOLD, outline="#fff3c0", width=1)
        self._o(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill="#fffbe6", outline="")
        if left is not None and ttl:
            self._a(x - 17, y - 17, x + 17, y + 17, start=90,
                    extent=-360 * left / ttl, style="arc",
                    outline=MAGENTA if left < 2.4 else GOLD, width=2)

    def _draw_power(self, x, y, kind, left=None, ttl=None):
        color = EFFECT_INFO.get(kind, ("", CYAN))[1]
        for rr, t in ((23, 0.10), (18, 0.20)):
            self._o(x - rr, y - rr, x + rr, y + rr,
                    fill=mix(color, FIELD_BG, 1 - t), outline="")
        rot = -self.time * 1.4
        outer, inner = [], []
        for k in range(6):
            ang = rot + k * math.pi / 3
            outer.extend((x + math.cos(ang) * 12.4, y + math.sin(ang) * 12.4))
            inner.extend((x + math.cos(ang) * 8.0, y + math.sin(ang) * 8.0))
        self._p(*outer, fill=mix(color, FIELD_BG, 0.22),
                outline=mix(color, "#ffffff", 0.55), width=1.5)
        self._p(*inner, fill=mix(color, "#ffffff", 0.18), outline="")
        glyph = {"shield": "Щ", "double": "×2", "slow": "З"}.get(kind, "?")
        self._t(x, y, text=glyph,
                font=(F_UI, 8 if kind == "double" else 9, "bold"),
                fill="#07101d")
        if left is not None and ttl:
            self._a(x - 16, y - 16, x + 16, y + 16, start=90,
                    extent=-360 * left / ttl, style="arc",
                    outline=MAGENTA if left < 2.4 else color, width=2)

    def draw_food(self, ox, oy):
        # «съеденное» ещё рисуется, пока голова визуально доползает до клетки
        for pe in self.pending_eats:
            x, y = self._center_of(pe["cell"])
            if pe.get("pkind"):
                self._draw_power(x + ox, y + oy, pe["pkind"])
            elif pe["special"]:
                self._draw_star(x + ox, y + oy)
            else:
                self._draw_apple(x + ox, y + oy)

        if self.food:
            x, y = self._center_of(self.food)
            self._draw_apple(x + ox, y + oy)

        pu = self.powerup
        if pu:
            left, ttl = max(0.0, pu["left"]), pu["ttl"]
            if not (left < 2.4 and math.sin(self.time * 20) < 0):
                x, y = self._center_of(pu["pos"])
                self._draw_power(x + ox, y + oy, pu["kind"], left, ttl)

        sp = self.special
        if sp:
            x, y = self._center_of(sp["pos"])
            left, ttl = max(0.0, sp["left"]), sp["ttl"]
            if left < 2.4 and math.sin(self.time * 20) < 0:
                return
            self._draw_star(x + ox, y + oy, left, ttl)
    # ------------------------------------------------ HUD
    def draw_hud(self):
        title = MODE_NAMES.get(self.mode, "")
        if self.mode == "net" and self.net_role:
            title += " · " + ("ХОСТ" if self.net_role == "host" else "ГОСТЬ")
        elif self.mode == "bots":
            title += " · " + "  ".join(
                "%s %d" % (r["name"], r["score"]) for r in self.rivals)
        self._t(62, 4, text=title, anchor="nw",
                font=(F_UI, 8, "bold"), fill="#3f6384")
        self._t(738, 4, text="◆ %d" % self.eco["coins"], anchor="ne",
                font=(F_UI, 9, "bold"), fill=GOLD)

        if self.mode == "blitz":
            third_label = "ВРЕМЯ"
        elif self.mode == "net":
            third_label = "ВРЕМЯ"
        elif self.mode == "bots":
            third_label = "СОПЕРНИК"
        else:
            third_label = "ДЛИНА"
        for label, x in (("СЧЁТ", 62), ("РЕКОРД", 248), (third_label, 452),
                         ("СКОРОСТЬ", 612)):
            self._t(x, 24, text=label, anchor="nw",
                    font=(F_UI, 9, "bold"), fill=MUTED)

        pulse = self.score_pulse
        if pulse > 0.03:
            self._t(62, 38, text=str(self.score), anchor="nw",
                    font=(F_TITLE, 32 + int(7 * pulse)), fill="#bfefff")
        self._t(62, 38, text=str(self.score), anchor="nw",
                font=(F_TITLE, 30), fill=TEXT)
        self._t(248, 40, text=str(self.best), anchor="nw",
                font=(F_TITLE, 25), fill="#c8dcf7")

        if self.mode in ("blitz", "net") and self.time_left is not None:
            secs = max(0, int(math.ceil(self.time_left)))
            col = TEXT
            if secs <= 10 and math.sin(self.time * 9) > 0:
                col = "#ff6b93"
            self._t(452, 40, text="%d:%02d" % (secs // 60, secs % 60), anchor="nw",
                    font=(F_TITLE, 25), fill=col)
        elif self.mode == "bots":
            best_rival = max([r["score"] for r in self.rivals] or [0])
            self._t(452, 40, text=str(best_rival), anchor="nw",
                    font=(F_TITLE, 25), fill="#c8dcf7")
        else:
            self._t(452, 40, text=str(len(self.snake)), anchor="nw",
                    font=(F_TITLE, 25), fill="#c8dcf7")

        span = max(0.0001, self.base_int - self.min_int)
        frac = (self.base_int - self.interval) / span
        filled = 1 + int(round(frac * 4))
        filled = max(1, min(5, filled))
        for i in range(5):
            x = 616 + i * 26
            col = mix(CYAN, MAGENTA, i / 4.0) if i < filled else "#1a2a45"
            self._p(*rr_pts(x, 56, x + 20, 66, 5), fill=col, outline="", smooth=True)

        if self.combo >= 2:
            full = 2.5 if self.mode in ("blitz", "chaos") else 3.0
            k = max(0.0, min(1.0, self.combo_timer / full))
            bx = 178
            self.rrect(bx, 46, bx + 54, 72, 9,
                       fill=mix(MAGENTA, BG_TOP, 0.78),
                       outline=mix(MAGENTA, BG_TOP, 0.3))
            self._t(bx + 27, 58, text="×%d" % self.combo,
                    font=(F_UI, 13, "bold"), fill="#ffd7e8")
            if k > 0.01:
                self._p(*rr_pts(bx, 75, bx + 54 * k, 78, 1.5),
                        fill=MAGENTA, outline="", smooth=False)

        self._draw_effects()
        active = self.active_cheat_ids()
        if active:
            self._t(738, 86,
                    text="ЧИТЫ · " + " · ".join(CHEAT_BY_ID[c]["chip"]
                                                for c in active),
                    anchor="e", font=(F_UI, 7, "bold"),
                    fill=mix(VIOLET, "#ffffff", 0.25))

    def _draw_effects(self):
        active = [(k, v) for k, v in self.effects.items() if v > 0.01]
        if not active:
            return
        w, gap, h = 88, 8, 16
        total = len(active) * w + (len(active) - 1) * gap
        x = WIN_W / 2 - total / 2
        y0 = 676
        for key, value in active:
            label, color = EFFECT_INFO[key]
            self.rrect(x, y0, x + w, y0 + h, 7,
                       fill=mix("#081220", color, 0.16),
                       outline=mix("#1b3350", color, 0.60))
            self._t(x + 9, y0 + h / 2, text=label, anchor="w",
                    font=(F_UI, 7, "bold"), fill=color)
            self._t(x + w - 9, y0 + h / 2, text="%.1f" % value, anchor="e",
                    font=(F_UI, 7, "bold"), fill=mix(color, "#ffffff", 0.40))
            x += w + gap

    # ------------------------------------------------ кадр
    def render(self):
        self.canvas.delete("dyn")
        for a in self.ambient:
            a.draw(self.canvas)

        if self.shake > 0.3:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
        else:
            ox = oy = 0.0

        if self.flash > 0.02:
            col = mix("#16243d", MAGENTA if self.state == "dead" else CYAN,
                      min(1.0, self.flash))
            self.rrect(FX - 2, FY - 2, FX + FIELD_W + 2, FY + FIELD_H + 2, 8,
                       fill="", outline=col,
                       width=max(1, int(2 + 4 * self.flash)))

        self.draw_walls(ox, oy)
        self.draw_meteors(ox, oy)
        self.draw_food(ox, oy)
        if self.state in ("playing", "paused", "dead"):
            self.draw_rivals(ox, oy, self.t_render)
        self.draw_snake(ox, oy, self.t_render)
        for p in self.particles:
            p.draw(self.canvas)
        for r in self.rings:
            r.draw(self.canvas)
        for f in self.floats:
            f.draw(self.canvas)

        self.draw_hud()
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "modes":
            self.draw_modes()
        elif self.state == "shop":
            self.draw_shop()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "paused":
            self.draw_pause()
        elif self.state == "netmenu":
            self.draw_netmenu()
        elif self.state in ("netwait", "netconnect"):
            self.draw_netwait()
        elif self.state == "dead" and self.time - self.dead_at > 0.45:
            self.draw_gameover()
        if self.state == "playing" and self.mode == "net" and \
                self.net_role == "client" and not self.net_have_state:
            self._t(WIN_W / 2, FY + FIELD_H / 2, text="ПОДКЛЮЧЕНИЕ К ХОСТУ...",
                    font=(F_TITLE, 18, "bold"), fill=CYAN)

    # ------------------------------------------------ вспомогательное для панелей
    def _panel(self, x0, y0, x1, y1, r=24):
        self.rrect(x0, y0, x1, y1, r, fill=PANEL_BG, outline="#17294a", width=2)
        # мягкие цветные пятна, не выходящие за панель
        r1 = min(150.0, (x1 - x0) * 0.30, (y1 - y0) * 0.32)
        cx1, cy1 = x0 + r1 + 10, y0 + r1 + 8
        for i in range(6):
            rr = r1 * (1 - i * 0.15)
            self._o(cx1 - rr, cy1 - rr, cx1 + rr, cy1 + rr,
                    fill=mix(PANEL_BG, "#0f3d5c", 0.03 + 0.02 * i), outline="")
        r2 = min(155.0, (x1 - x0) * 0.32, (y1 - y0) * 0.34)
        cx2, cy2 = x1 - r2 - 10, y1 - r2 - 6
        for i in range(6):
            rr = r2 * (1 - i * 0.15)
            self._o(cx2 - rr, cy2 - rr, cx2 + rr, cy2 + rr,
                    fill=mix(PANEL_BG, "#4a1846", 0.026 + 0.018 * i), outline="")

    def _glow_text(self, x, y, text, size, color, glow):
        for d, k in ((6, 0.80), (3, 0.58)):
            self._t(x, y, text=text, font=(F_TITLE, size + d, "bold"),
                    fill=mix(glow, PANEL_BG, k))
        self._t(x, y, text=text, font=(F_TITLE, size, "bold"), fill=color)

    def _button(self, cx, cy, w, h, label, pulse=0.0, hot=None, active=True):
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        hot = CYAN if hot is None else hot
        if active:
            for pad in (9, 5):
                self.rrect(x0 - pad, y0 - pad, x1 + pad, y1 + pad, 12 + pad,
                           fill="", outline=mix(PANEL_BG, hot, 0.10 + 0.12 * pulse),
                           width=2)
            fill = mix("#0a1b2c", "#123f57", 0.30 + 0.45 * pulse)
            outline = mix("#1e5a70", hot, 0.35 + 0.5 * pulse)
            text_col = mix("#bfe9f5", "#ffffff", 0.35 + 0.5 * pulse)
        else:
            fill = "#070f1b"
            outline = "#152a42"
            text_col = "#6f86a1"
        self.rrect(x0, y0, x1, y1, 12, fill=fill, outline=outline, width=2)
        self._t(cx, cy, text=label, font=(F_UI, 12, "bold"), fill=text_col)

    # ------------------------------------------------ магазин
    def draw_shop(self):
        x0, y0 = FX + 12, FY + 12
        x1, y1 = FX + FIELD_W - 12, FY + FIELD_H - 12
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        self._t(x0 + 28, y0 + 30, text="МАГАЗИН НЕОНОВ", anchor="w",
                font=(F_TITLE, 18, "bold"), fill=HEAD_C)

        daily = self.daily_status()
        if daily["claimed"]:
            dtext, dcol = "БОНУС ДНЯ ПОЛУЧЕН", MUTED
        else:
            dtext = "БОНУС ДНЯ  +%d ◆  ·  D" % daily["reward"]
            dcol = GOLD
        self.rrect(x1 - 392, y0 + 14, x1 - 158, y0 + 42, 10,
                   fill=mix(PANEL_BG, GOLD, 0.07),
                   outline=mix("#2a2414", GOLD, 0.33))
        self._t((x1 - 392 + x1 - 158) / 2, y0 + 28, text=dtext,
                font=(F_UI, 8, "bold"), fill=dcol)

        self.rrect(x1 - 150, y0 + 14, x1 - 16, y0 + 42, 10,
                   fill=mix(PANEL_BG, GOLD, 0.12),
                   outline=mix("#3a2c12", GOLD, 0.45))
        self._t(x1 - 83, y0 + 28, text="◆ %d" % self.eco["coins"],
                font=(F_TITLE, 13, "bold"), fill=GOLD)

        tabs = ("СКИНЫ", "ЧИТЫ", "КОДЫ")
        tw, th, gap = 150, 28, 10
        total = len(tabs) * tw + (len(tabs) - 1) * gap
        tx = cx - total / 2
        for i, label in enumerate(tabs):
            active = (i == self.shop_tab)
            bx0 = tx + i * (tw + gap)
            bx1 = bx0 + tw
            self.rrect(bx0, y0 + 54, bx1, y0 + 54 + th, 9,
                       fill=mix("#081220", CYAN, 0.16 if active else 0.03),
                       outline=mix("#16304a", CYAN, 0.62 if active else 0.18),
                       width=2 if active else 1)
            self._t((bx0 + bx1) / 2, y0 + 68, text=label,
                    font=(F_UI, 9, "bold"),
                    fill="#c9f4ff" if active else "#5b7694")

        if self.shop_tab == 0:
            self._draw_shop_skins(x0, y0, x1)
        elif self.shop_tab == 1:
            self._draw_shop_cheats(x0, y0, x1)
        else:
            self._draw_shop_codes(cx, y0)

        if self.shop_status:
            self._t(cx, y0 + 448, text=self.shop_status,
                    font=(F_UI, 9, "bold"), fill=self.shop_status_color)
        self._t(cx, y0 + 472,
                text="← → — раздел    ↑ ↓ — выбор    Enter — действие    "
                     "D — бонус дня    Esc — меню",
                font=(F_UI, 8), fill=MUTED)

    def _draw_shop_skins(self, x0, y0, x1):
        row_h = 40
        top = y0 + 102
        for i, skin in enumerate(SKINS):
            ry0 = top + i * row_h
            ry1 = ry0 + row_h - 5
            selected = (i == self.shop_sel)
            owned = skin["id"] in self.eco["skins"]
            current = self.eco["skin"] == skin["id"]
            self.rrect(x0 + 26, ry0, x1 - 26, ry1, 9,
                       fill=mix("#081220", CYAN, 0.13 if selected else 0.03),
                       outline=mix("#16304a", CYAN,
                                   0.55 if selected else 0.12),
                       width=2 if selected else 1)
            head, mid, _tail = skin["colors"]
            self.rrect(x0 + 38, ry0 + 10, x0 + 56, ry1 - 10, 5,
                       fill=mid, outline=head)
            self._t(x0 + 68, ry0 + 6, text=skin["name"], anchor="nw",
                    font=(F_UI, 9, "bold"),
                    fill="#e6fbff" if selected else "#a9c6dd")
            self._t(x0 + 68, ry0 + 22, text=skin["desc"], anchor="nw",
                    font=(F_UI, 8), fill="#62809f")
            if current:
                state, col = "ВЫБРАН", CYAN
            elif owned:
                state, col = "ВЫБРАТЬ", MUTED
            elif self.eco["coins"] >= skin["price"]:
                state, col = "%d ◆" % skin["price"], GOLD
            else:
                state, col = "%d ◆" % skin["price"], "#8a6a6a"
            self._t(x1 - 42, (ry0 + ry1) / 2, text=state, anchor="e",
                    font=(F_UI, 9, "bold"), fill=col)

    def _draw_shop_cheats(self, x0, y0, x1):
        row_h = 50
        top = y0 + 102
        for i, cheat in enumerate(CHEATS):
            ry0 = top + i * row_h
            ry1 = ry0 + row_h - 6
            selected = (i == self.shop_sel)
            owned = cheat["id"] in self.eco["ownedCheats"]
            enabled = owned and self.eco["cheats"].get(cheat["id"])
            hot = GOLD if enabled else CYAN
            self.rrect(x0 + 26, ry0, x1 - 26, ry1, 9,
                       fill=mix("#081220", hot, 0.12 if selected else 0.03),
                       outline=mix("#16304a", hot,
                                   0.55 if selected else 0.12),
                       width=2 if selected else 1)
            self.rrect(x0 + 38, ry0 + 10, x0 + 112, ry1 - 10, 7,
                       fill=mix(PANEL_BG, hot, 0.18 if enabled else 0.07),
                       outline=mix("#16304a", hot, 0.45 if enabled else 0.18))
            self._t(x0 + 75, (ry0 + ry1) / 2, text=cheat["icon"],
                    font=(F_TITLE, 12, "bold"),
                    fill=GOLD if enabled else "#8fb2c9")
            self._t(x0 + 124, ry0 + 9, text=cheat["name"], anchor="nw",
                    font=(F_UI, 9, "bold"),
                    fill="#e6fbff" if selected else "#a9c6dd")
            self._t(x0 + 124, ry0 + 24, text=cheat["desc"], anchor="nw",
                    font=(F_UI, 7), fill="#5d7fa3")
            if not owned:
                if self.eco["coins"] >= cheat["price"]:
                    state, col = "%d ◆" % cheat["price"], GOLD
                else:
                    state, col = "%d ◆" % cheat["price"], "#8a6a6a"
            elif enabled:
                state, col = "ВКЛЮЧЁН", GOLD
            else:
                state, col = "ВЫКЛЮЧЕН", MUTED
            self._t(x1 - 42, (ry0 + ry1) / 2, text=state, anchor="e",
                    font=(F_UI, 9, "bold"), fill=col)
        self._t((x0 + x1) / 2, y0 + 382,
                text="Читы действуют во всех режимах, включая сетевую игру.",
                font=(F_UI, 8, "italic"), fill="#4f6a8a")

    def _draw_shop_codes(self, cx, y0):
        card_x0, card_x1 = cx - 260, cx + 260
        card_y0, card_y1 = y0 + 108, y0 + 396
        self.rrect(card_x0, card_y0, card_x1, card_y1, 18,
                   fill=mix(PANEL_BG, GOLD, 0.035),
                   outline=mix("#233350", GOLD, 0.24), width=2)
        self._glow_text(cx, card_y0 + 36, "ПРОМОКОДЫ", 22, GOLD, "#6a4310")

        lines = (
            "Введите промокод из README или секретный код из игры.",
            "Код даёт неоны, скин или чит — один раз на сохранение.",
            "Если предмет уже куплен, начислим компенсацию неонами.",
        )
        for i, line in enumerate(lines):
            self._t(cx, card_y0 + 72 + i * 22, text=line,
                    font=(F_UI, 9), fill="#6f86a1")

        pulse = 0.5 + 0.5 * math.sin(self.time * 3.4)
        self._button(cx, card_y0 + 166, 320, 40, "ENTER — ВВЕСТИ КОД", pulse)

        used = len(self.eco["usedCodes"])
        self._t(cx, card_y0 + 212, text="АКТИВИРОВАНО КОДОВ: %d" % used,
                font=(F_TITLE, 11, "bold"), fill=CYAN)

        daily = self.daily_status()
        if daily["claimed"]:
            line = "Бонус дня уже получен · серия %d" % daily["streak"]
            col = MUTED
        else:
            line = "Бонус дня: +%d ◆ · нажмите D" % daily["reward"]
            col = GOLD
        self._t(cx, card_y0 + 244, text=line, font=(F_UI, 9, "bold"), fill=col)
        self._t(cx, card_y0 + 268,
                text="Серия растёт при ежедневном входе: 40 → 100 ◆",
                font=(F_UI, 8), fill="#4f6a8a")

    # ------------------------------------------------ меню
    def draw_menu(self):
        x0, y0 = FX + 12, FY + 12
        x1, y1 = FX + FIELD_W - 12, FY + FIELD_H - 12
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        self._t(cx, y0 + 38, text="К Л А С С И К А   В   Н Е О Н Е",
                font=(F_UI, 9, "bold"), fill="#4f7298")
        self._glow_text(cx, y0 + 90, "NEON SNAKE", 40, HEAD_C, "#0e5c78")
        self._t(cx, y0 + 134, text="собирай свет — не врезайся в стены",
                font=(F_UI, 10, "italic"), fill="#5f7d9e")

        coin_chip = "◆ %d" % self.eco["coins"]
        self.rrect(x1 - 150, y0 + 14, x1 - 16, y0 + 42, 10,
                   fill=mix(PANEL_BG, GOLD, 0.12),
                   outline=mix("#3a2c12", GOLD, 0.45))
        self._t(x1 - 83, y0 + 28, text=coin_chip,
                font=(F_TITLE, 13, "bold"), fill=GOLD)

        self._demo_snake(cx, y0 + 178)

        pulse = 0.5 + 0.5 * math.sin(self.time * 3.2)
        labels = ("ИГРАТЬ", "МИНИ-ИГРЫ", "МАГАЗИН", "НАСТРОЙКИ", "ВЫХОД")
        for i, label in enumerate(labels):
            selected = (i == self.menu_sel)
            hot = MAGENTA if i == 4 else CYAN
            self._button(cx, y0 + 228 + i * 42, 330, 34, label,
                         pulse if selected else 0.0, hot=hot,
                         active=selected)

        self._t(cx, y0 + 436,
                text="РЕКОРД  ·  %s    %d" % (MODE_NAMES.get(self.mode, ""), self.best),
                font=(F_TITLE, 13, "bold"), fill=GOLD)
        skin_name = SKIN_BY_ID.get(self.eco["skin"], SKINS[0])["name"]
        self._t(cx, y0 + 458,
                text="СКИН: %s   ·   ЧИТЫ: %d" %
                     (skin_name, len(self.active_cheat_ids())),
                font=(F_UI, 8, "bold"), fill="#5f7d9e")
        self._t(cx, y0 + 478, text="↑ ↓ — выбор        Enter — открыть        Esc — выход",
                font=(F_UI, 9), fill=MUTED)

    def _demo_snake(self, cx, cy):
        n, gap = 15, 22
        x0 = cx - (n - 1) * gap / 2
        pts = []
        for i in range(n):
            pts.append((x0 + i * gap, cy + math.sin(self.time * 1.8 + i * 0.45) * 7))

        for i in range(n - 1, 0, -1):
            f = i / (n - 1)
            col = mix(TAIL_C, HEAD_C, 1 - f)
            self._l(pts[i][0], pts[i][1], pts[i - 1][0], pts[i - 1][1],
                    fill=mix(col, PANEL_BG, 0.15),
                    width=max(4, int(13 - 5 * f)), capstyle="round")

        for i in range(n - 1, -1, -1):
            f = i / (n - 1)
            col = mix(HEAD_C, TAIL_C, f)
            s = 13.5 - 5.5 * f
            x, y = pts[i]
            self.rrect(x - s / 2 - 3, y - s / 2 - 3, x + s / 2 + 3, y + s / 2 + 3,
                       r=(s + 6) / 2.6, fill=mix(col, PANEL_BG, 0.82), outline="")
            self.rrect(x - s / 2, y - s / 2, x + s / 2, y + s / 2,
                       r=s / 2.6, fill=col, outline="")

        hx, hy = pts[-1]
        for side in (-1, 1):
            ex, ey = hx + 3.5, hy + side * 4.2
            self._o(ex - 2.6, ey - 2.6, ex + 2.6, ey + 2.6, fill="#f4ffff", outline="")
            self._o(ex - 0.4, ey - 1.4, ex + 1.8, ey + 0.8, fill="#06121f", outline="")

    # ------------------------------------------------ пауза
    def draw_pause(self):
        x0, y0 = FX + 150, FY + 155
        x1, y1 = FX + FIELD_W - 150, FY + FIELD_H - 145
        self._panel(x0, y0, x1, y1, 22)
        cx = (x0 + x1) / 2
        self._glow_text(cx, y0 + 60, "ПАУЗА", 30, CYAN, "#0e5c78")
        pulse = 0.5 + 0.5 * math.sin(self.time * 3.0)
        self._button(cx, y0 + 128, 250, 46, "ПРОБЕЛ — ПРОДОЛЖИТЬ", pulse)
        self._t(cx, y0 + 178, text="ESC — в меню      R — заново",
                font=(F_UI, 9), fill=MUTED)

    # ------------------------------------------------ сетевое лобби
    def draw_netmenu(self):
        x0, y0 = FX + 120, FY + 96
        x1, y1 = FX + FIELD_W - 120, FY + FIELD_H - 96
        self._panel(x0, y0, x1, y1, 22)
        cx = (x0 + x1) / 2
        self._glow_text(cx, y0 + 40, "СЕТЕВАЯ ИГРА", 24, CYAN, "#0e5c78")
        self._t(cx, y0 + 68, text="локальная сеть · TCP · один хост и один гость",
                font=(F_UI, 9, "italic"), fill="#5f7d9e")

        pulse = 0.5 + 0.5 * math.sin(self.time * 3.2)
        labels = ("СОЗДАТЬ ИГРУ (ХОСТ)", "ПОДКЛЮЧИТЬСЯ", "НАЗАД")
        for i, label in enumerate(labels):
            selected = (i == self.net_menu_sel)
            hot = MAGENTA if i == 2 else CYAN
            self._button(cx, y0 + 116 + i * 50, 310, 38, label,
                         pulse if selected else 0.0, hot=hot, active=selected)

        self._t(cx, y0 + 244, text="порт %d" % self.net_port,
                font=(F_UI, 8), fill="#435572")
        self._t(cx, y0 + 262,
                text="хост сообщает свой IP, гость вводит его вручную",
                font=(F_UI, 8), fill="#5f7d9e")
        if self.net_status:
            self._t(cx, y0 + 284, text=self.net_status,
                    font=(F_UI, 8, "bold"), fill="#ff8fc0", width=x1 - x0 - 40)
        self._t(cx, y0 + 306, text="↑ ↓ — выбор      Enter — открыть      Esc — назад",
                font=(F_UI, 9), fill=MUTED)

    def draw_netwait(self):
        x0, y0 = FX + 120, FY + 110
        x1, y1 = FX + FIELD_W - 120, FY + FIELD_H - 110
        self._panel(x0, y0, x1, y1, 22)
        cx = (x0 + x1) / 2
        waiting = self.state == "netwait"
        if waiting:
            self._glow_text(cx, y0 + 44, "ОЖИДАНИЕ ИГРОКА", 22, CYAN, "#0e5c78")
            self._t(cx, y0 + 78, text="запусти игру на другом ПК и подключись",
                    font=(F_UI, 9, "italic"), fill="#5f7d9e")
            self._t(cx, y0 + 120, text="IP ХОСТА", font=(F_UI, 8, "bold"),
                    fill=MUTED)
            self._t(cx, y0 + 150, text="%s:%d" % (self.net_lan_ip, self.net_port),
                    font=(F_TITLE, 22, "bold"), fill=GOLD)
            self._t(cx, y0 + 190,
                    text="на другом ПК: МИНИ-ИГРЫ → СЕТЕВАЯ ИГРА → ПОДКЛЮЧИТЬСЯ",
                    font=(F_UI, 8), fill="#6d86a6", width=x1 - x0 - 50)
            dots = "." * (1 + int(self.time * 2) % 3)
            self._t(cx, y0 + 228, text="ЖДЁМ" + dots,
                    font=(F_UI, 10, "bold"), fill=mix(CYAN, "#ffffff", 0.3))
        else:
            self._glow_text(cx, y0 + 44, "ПОДКЛЮЧЕНИЕ", 22, VIOLET, "#3a1a66")
            self._t(cx, y0 + 78, text="хост: %s:%d" % (self.net_ip, self.net_port),
                    font=(F_UI, 10), fill="#8fa9c8")
            dots = "." * (1 + int(self.time * 2) % 3)
            self._t(cx, y0 + 128, text="СОЕДИНЯЕМСЯ" + dots,
                    font=(F_UI, 11, "bold"), fill=mix(VIOLET, "#ffffff", 0.35))
        self._t(cx, y0 + 270, text="Esc — отмена", font=(F_UI, 9), fill=MUTED)

    # ------------------------------------------------ мини-игры
    def draw_modes(self):
        x0, y0 = FX + 34, FY + 14
        x1, y1 = FX + FIELD_W - 34, FY + FIELD_H - 12
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        self._glow_text(cx, y0 + 32, "МИНИ-ИГРЫ", 24, CYAN, "#0e5c78")
        self._t(cx, y0 + 58, text="выбери режим — и вперёд",
                font=(F_UI, 9, "italic"), fill="#5f7d9e")

        accents = (CYAN, VIOLET, MAGENTA, ORANGE, "#6bff9e", BLUE)
        pulse = 0.5 + 0.5 * math.sin(self.time * 3.4)
        for i, (key, name, desc) in enumerate(MODES):
            accent = accents[i % len(accents)]
            t0 = y0 + 76 + i * 58
            t1 = t0 + 52
            sel = (i == self.modes_sel)

            if sel:
                for pad in (5, 3):
                    self.rrect(x0 + 20 - pad, t0 - pad, x1 - 20 + pad, t1 + pad,
                               11 + pad, fill="",
                               outline=mix(PANEL_BG, accent, 0.12 + 0.16 * pulse),
                               width=2)
            self.rrect(x0 + 20, t0, x1 - 20, t1, 11,
                       fill=mix("#070f1b", accent, 0.05 + (0.05 if sel else 0.0)),
                       outline=mix("#152a42", accent,
                                   0.55 + 0.4 * pulse if sel else 0.22),
                       width=2)
            self.rrect(x0 + 32, t0 + 10, x0 + 36, t1 - 10, 2, fill=accent)

            self._t(x0 + 46, (t0 + t1) / 2, text=str(i + 1), anchor="w",
                    font=(F_UI, 8, "bold"), fill="#3f6384")
            self._t(x0 + 64, t0 + 7, text=name, anchor="nw",
                    font=(F_TITLE, 12, "bold"),
                    fill=TEXT if sel else "#a9c1d8")
            self._t(x0 + 64, t0 + 29, text=desc, anchor="nw",
                    font=(F_UI, 8), fill="#6d86a6" if sel else "#536a88",
                    width=x1 - x0 - 210)

            self._t(x1 - 38, t0 + 8, text="РЕКОРД", anchor="ne",
                    font=(F_UI, 7, "bold"), fill="#4f6a8a")
            self._t(x1 - 38, t0 + 26, text=str(self.bests.get(key, 0)), anchor="ne",
                    font=(F_TITLE, 15), fill=GOLD if sel else "#c8b06a")

        self._t(cx, y0 + 444,
                text="↑ ↓ — выбор      Enter / 1..6 — начать      Esc — назад",
                font=(F_UI, 9), fill=MUTED)
        self._t(cx, y0 + 464, text="сетевой режим: один игрок создаёт игру, второй подключается по IP",
                font=(F_UI, 8), fill="#435572")

    # ------------------------------------------------ настройки
    def draw_settings(self):
        x0, y0 = FX + 34, FY + 16
        x1, y1 = FX + FIELD_W - 34, FY + 504
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        self._glow_text(cx, y0 + 38, "НАСТРОЙКИ", 24, CYAN, "#0e5c78")
        self._t(cx, y0 + 66,
                text="← → — изменить      ↑ ↓ — строка      Esc — назад",
                font=(F_UI, 8), fill="#5f7d9e")

        rx0, rx1 = x0 + 20, x1 - 20
        top, step, rh = y0 + 86, 37, 31

        for i, (key, label, _names) in enumerate(SETTING_ROWS):
            t0 = top + i * step
            t1 = t0 + rh
            sel = (i == self.settings_sel)
            value = self._setting_value(key).upper()

            if key == "wrap":
                accent = VIOLET if self.settings["wrap"] else "#ff7a9c"
            elif key == "specials":
                accent = GOLD
            elif key == "speed":
                accent = CYAN
            else:
                accent = CYAN if self.settings.get(key) else MUTED

            self.rrect(rx0, t0, rx1, t1, 10,
                       fill=mix("#070f1b", "#0f3d5c", 0.55 if sel else 0.0),
                       outline=mix("#132540", CYAN, 0.55 if sel else 0.10),
                       width=2 if sel else 1)
            if sel:
                self.rrect(rx0, t0, rx0 + 4, t1, 2, fill=CYAN)

            self._t(rx0 + 16, (t0 + t1) / 2, text=label, anchor="w",
                    font=(F_UI, 9, "bold"),
                    fill=TEXT if sel else "#93aac3")

            vx1 = rx1 - 10
            vx0 = vx1 - 210
            self.rrect(vx0, t0 + 5, vx1, t1 - 5, 8,
                       fill=mix("#0a1626", accent, 0.10),
                       outline=mix("#1b3350", accent, 0.45 if sel else 0.25))
            self._t((vx0 + vx1) / 2, (t0 + t1) / 2, text=value,
                    font=(F_UI, 8, "bold"), fill=accent)
            if sel:
                self._t(vx0 + 14, (t0 + t1) / 2, text="‹",
                        font=(F_UI, 10, "bold"), fill="#8fd7e8")
                self._t(vx1 - 14, (t0 + t1) / 2, text="›",
                        font=(F_UI, 10, "bold"), fill="#8fd7e8")

        # сброс рекордов
        t0 = top + len(SETTING_ROWS) * step
        t1 = t0 + rh
        sel = (self.settings_sel == len(SETTING_ROWS))
        self.rrect(rx0, t0, rx1, t1, 10,
                   fill=mix("#070f1b", "#3a1026", 0.65 if sel else 0.0),
                   outline=mix("#132540", MAGENTA, 0.70 if sel else 0.16),
                   width=2 if sel else 1)
        if sel:
            self.rrect(rx0, t0, rx0 + 4, t1, 2, fill=MAGENTA)
        self._t(rx0 + 16, (t0 + t1) / 2, text="СБРОСИТЬ РЕКОРДЫ", anchor="w",
                font=(F_UI, 9, "bold"), fill=TEXT if sel else "#93aac3")
        note = "ТОЧНО? ENTER" if self.reset_confirm else "ENTER"
        self._t(rx1 - 18, (t0 + t1) / 2, text=note, anchor="e",
                font=(F_UI, 8, "bold"), fill=MAGENTA if sel else "#8a6a80")

        # назад
        t0 = top + (len(SETTING_ROWS) + 1) * step
        t1 = t0 + rh
        sel = (self.settings_sel == len(SETTING_ROWS) + 1)
        self.rrect(rx0, t0, rx1, t1, 10,
                   fill=mix("#070f1b", "#0f3d5c", 0.55 if sel else 0.0),
                   outline=mix("#132540", CYAN, 0.55 if sel else 0.10),
                   width=2 if sel else 1)
        self._t(cx, (t0 + t1) / 2, text="НАЗАД В МЕНЮ",
                font=(F_UI, 9, "bold"), fill=TEXT if sel else "#93aac3")

        self._t(cx, y0 + 446, text="настройки сохраняются автоматически",
                font=(F_UI, 8), fill="#435572")
        self._t(cx, y0 + 464, text="звук — системные сигналы Windows",
                font=(F_UI, 8), fill="#374864")

    # ------------------------------------------------ конец игры
    def draw_gameover(self):
        if self.mode == "net":
            self._draw_net_gameover()
            return
        w, h = 460, 380
        x0 = (WIN_W - w) / 2
        y0 = FY + (FIELD_H - h) / 2
        x1, y1 = x0 + w, y0 + h
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        if self.death_reason == "time":
            self._glow_text(cx, y0 + 40, "ВРЕМЯ ВЫШЛО", 24, "#ffc46b", "#6a4310")
        else:
            self._glow_text(cx, y0 + 40, "ИГРА ОКОНЧЕНА", 24, "#ff8fc0", "#6a1740")
        secs = max(0, int(self.run_time))
        self._t(cx, y0 + 68,
                text="%s   ·   %d:%02d" % (MODE_NAMES.get(self.mode, ""),
                                          secs // 60, secs % 60),
                font=(F_UI, 9, "bold"), fill="#6f86a1")

        self._t(cx, y0 + 88, text="СЧЁТ", font=(F_UI, 9, "bold"), fill=MUTED)
        self._glow_text(cx, y0 + 128, str(self.score), 44, TEXT, "#12657a")

        self._t(cx, y0 + 174, text="РЕКОРД   %d" % self.best,
                font=(F_TITLE, 13, "bold"), fill=GOLD)
        if self.new_record:
            pulse = 0.5 + 0.5 * math.sin(self.time * 6.0)
            self._t(cx, y0 + 198, text="★  Н О В Ы Й   Р Е К О Р Д  ★",
                    font=(F_UI, 9, "bold"),
                    fill=mix("#8a6a2a", "#ffe9a3", 0.35 + 0.65 * pulse))
        else:
            self._t(cx, y0 + 198, text="ещё немного — и рекорд твой",
                    font=(F_UI, 9, "italic"), fill="#4d6584")

        stats = (("ЯБЛОКИ", str(self.apples), TEXT),
                 ("ЗВЁЗДЫ", str(self.stars), GOLD),
                 ("БОНУСЫ", str(self.powers), VIOLET),
                 ("КОМБО", "×%d" % self.max_combo, MAGENTA))
        for i, (label, value, color) in enumerate(stats):
            sx = cx - 150 + i * 100
            self._t(sx, y0 + 226, text=label,
                    font=(F_UI, 7, "bold"), fill="#4f6a8a")
            self._t(sx, y0 + 244, text=value,
                    font=(F_TITLE, 15, "bold"), fill=color)

        pulse = 0.5 + 0.5 * math.sin(self.time * 3.4)
        if self.reward_coins:
            extra = ("  ·  рекорд +%d" % self.reward_record_bonus
                     if self.reward_record_bonus else "")
            self._t(cx, y0 + 264, text="+%d ◆%s" % (self.reward_coins, extra),
                    font=(F_UI, 10, "bold"), fill=GOLD)
        self._button(cx, y0 + 296, 300, 46, "ПРОБЕЛ — ЕЩЁ РАЗ", pulse)
        self._t(cx, y0 + 340, text="M — мини-игры      ESC — меню",
                font=(F_UI, 9), fill=MUTED)

    def _draw_net_gameover(self):
        w, h = 470, 360
        x0 = (WIN_W - w) / 2
        y0 = FY + (FIELD_H - h) / 2
        x1, y1 = x0 + w, y0 + h
        self._panel(x0, y0, x1, y1, 24)
        cx = (x0 + x1) / 2

        opp = self.rivals[0]["score"] if self.rivals else 0
        if self.net_lost:
            title, color, glow = "СВЯЗЬ ПОТЕРЯНА", "#ffc46b", "#6a4310"
        elif self.net_won:
            title, color, glow = "ПОБЕДА!", "#7dffc0", "#0d6a4a"
        else:
            title, color, glow = "ПОРАЖЕНИЕ", "#ff8fc0", "#6a1740"
        self._glow_text(cx, y0 + 42, title, 30, color, glow)
        self._t(cx, y0 + 74,
                text="СЕТЕВАЯ ИГРА   ·   %s" %
                     ("ХОСТ" if (self.net_role or self.net_last_role) == "host"
                      else "ГОСТЬ"),
                font=(F_UI, 9, "bold"), fill="#6f86a1")

        self._t(cx - 105, y0 + 112, text="ТЫ", font=(F_UI, 9, "bold"), fill=CYAN)
        self._glow_text(cx - 105, y0 + 152, str(self.score), 38, TEXT, "#12657a")
        self._t(cx + 105, y0 + 112, text="СОПЕРНИК", font=(F_UI, 9, "bold"),
                fill=MAGENTA)
        self._glow_text(cx + 105, y0 + 152, str(opp), 38, "#ffd0dd", "#6a1740")

        if not self.net_lost:
            self._t(cx, y0 + 204,
                    text=("ты собрал больше" if self.net_won else
                          "соперник оказался быстрее"),
                    font=(F_UI, 9, "italic"), fill="#5f7d9e")
        else:
            self._t(cx, y0 + 204, text="игрок отключился или сеть недоступна",
                    font=(F_UI, 9, "italic"), fill="#5f7d9e")

        self._t(cx, y0 + 232, text="РЕКОРД РЕЖИМА   %d" % self.best,
                font=(F_TITLE, 12, "bold"), fill=GOLD)

        pulse = 0.5 + 0.5 * math.sin(self.time * 3.4)
        if self.reward_coins:
            self._t(cx, y0 + 252, text="+%d ◆" % self.reward_coins,
                    font=(F_UI, 10, "bold"), fill=GOLD)
        self._button(cx, y0 + 286, 320, 46, "ПРОБЕЛ — В МЕНЮ", pulse)
        self._t(cx, y0 + 330, text="M — мини-игры      ESC — меню",
                font=(F_UI, 9), fill=MUTED)


# ---------------------------------------------------------------- запуск
def main():
    try:
        game = Game()
    except Exception:
        text = traceback.format_exc()
        path = _write_error(text)
        last = text.strip().splitlines()[-1]
        try:
            from tkinter import messagebox
            box = tk.Tk()
            box.withdraw()
            messagebox.showerror(
                "NEON SNAKE",
                "Не удалось запустить игру.\n\n%s\n\nПодробности: %s"
                % (last, path or "—"))
            box.destroy()
        except Exception:
            pass
        return 1

    try:
        os.remove(_error_log_path())
    except OSError:
        pass

    try:
        game.root.mainloop()
    finally:
        game.save_game()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



