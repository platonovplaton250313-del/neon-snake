#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEON BRAWL: бойцы, снаряды, ИИ и симуляция матча."""

import heapq
import math
import random

from neon_brawl_data import (
    AH, AW, AX, AY, BG, BLUE, BUSH_DEFS, BOT_NAMES, CYAN, DIM, DIFF_CFG,
    DIFFICULTIES, F_MONO, F_TITLE, F_UI, GOLD, GREEN, HEROES, HERO_ORDER,
    LINE, MAGENTA, MINE, MODES, MUTED, PANEL, PANEL2, RED, SPAWN_ZONES, SPAWNS,
    TEAM_COLORS, TEXT, VIOLET, VH, VW, WALL_DEFS,
    angle_to, clamp, dist, fmt_time, hex_points, lerp, mix, norm,
    point_in_rect, point_seg_dist,
)
from neon_brawl_draw import (
    bar, crystal, hero_icon as draw_hero_icon, draw_simple_brawler,
    rrect, text_glow, trophy,
)

# ---------------------------------------------------------------- эффекты
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size",
                 "gravity")

    def __init__(self, x, y, vx, vy, life, color, size=3, gravity=160):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.99
        return self.life > 0


class FloatText:
    __slots__ = ("x", "y", "text", "color", "life", "max_life", "size", "vy",
                 "weight")

    def __init__(self, x, y, text, color=TEXT, size=14, life=0.85, vy=-44,
                 weight="bold"):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = self.max_life = life
        self.size = size
        self.vy = vy
        self.weight = weight

    def update(self, dt):
        self.life -= dt
        self.y += self.vy * dt
        self.vy *= 0.94
        return self.life > 0


class Ring:
    __slots__ = ("x", "y", "r0", "r1", "color", "life", "max_life", "width")

    def __init__(self, x, y, r0, r1, color, life=0.5, width=3):
        self.x, self.y = x, y
        self.r0, self.r1 = r0, r1
        self.color = color
        self.life = self.max_life = life
        self.width = width

    def update(self, dt):
        self.life -= dt
        return self.life > 0


class BeamFx:
    __slots__ = ("x1", "y1", "x2", "y2", "color", "life", "max_life", "width")

    def __init__(self, x1, y1, x2, y2, color, life=0.35, width=10):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.color = color
        self.life = self.max_life = life
        self.width = width

    def update(self, dt):
        self.life -= dt
        return self.life > 0


class Gem:
    def __init__(self, x, y, vx=0.0, vy=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.t = random.uniform(0, 6.28)
        self.rot = random.uniform(0, 6.28)

    def update(self, dt):
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.94
        self.vy *= 0.94
        self.x = clamp(self.x, 24, AW - 24)
        self.y = clamp(self.y, 24, AH - 24)


class Projectile:
    def __init__(self, game, owner, x, y, angle, speed, damage, max_range,
                 radius, color, light, pierce=False, kind="bolt"):
        self.game = game
        self.owner = owner
        self.team = owner.team
        self.x, self.y = x, y
        self.angle = angle
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.color = color
        self.light = light
        self.pierce = pierce
        self.kind = kind
        self.life = max_range / max(1.0, speed)
        self.max_life = self.life
        self.trail = [(x, y)]
        self.hit = set()

    def update(self, dt):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        self.life -= dt
        return (self.life > 0 and -40 < self.x < AW + 40
                and -40 < self.y < AH + 40)


class Lob:
    def __init__(self, game, owner, start, target, damage, splash, color, light):
        self.game = game
        self.owner = owner
        self.sx, self.sy = start
        self.tx, self.ty = target
        self.x, self.y = start
        self.z = 0.0
        self.damage = damage
        self.splash = splash
        self.color = color
        self.light = light
        self.dur = 0.42 + dist(start[0], start[1], target[0], target[1]) / 1250.0
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        p = min(1.0, self.t / self.dur)
        self.x = lerp(self.sx, self.tx, p)
        self.y = lerp(self.sy, self.ty, p)
        self.z = math.sin(math.pi * p) * 72.0
        if p >= 1.0:
            self.game.boom(self.tx, self.ty, self.splash, self.damage,
                           self.owner, self.color, push=120)
            return False
        return True


class DelayedBoom:
    def __init__(self, game, x, y, delay, radius, damage, owner, color):
        self.game = game
        self.x, self.y = x, y
        self.delay = delay
        self.radius = radius
        self.damage = damage
        self.owner = owner
        self.color = color
        self.t = 0.0

    def update(self, dt):
        self.delay -= dt
        self.t += dt
        if self.delay <= 0:
            self.game.boom(self.x, self.y, self.radius, self.damage,
                           self.owner, self.color, push=100)
            return False
        return True


# ---------------------------------------------------------------- боец
class Brawler:
    def __init__(self, game, hero_id, team, name, slot, x, y, is_player=False):
        self.game = game
        self.hero_id = hero_id
        self.hero = HEROES[hero_id]
        self.team = team
        self.name = name
        self.slot = slot
        self.is_player = is_player
        self.x, self.y = x, y
        self.radius = 20.0
        self.vx = self.vy = 0.0
        self.max_hp = self.hero["hp"]
        self.hp = self.max_hp
        self.alive = True
        self.respawn = 0.0
        self.aim = 0.0
        self.move_x = self.move_y = 0.0
        self.ammo = self.hero["ammo"]
        self.reload_acc = 0.0
        self.attack_cd = 0.0
        self.super = 0.0
        self.gadget = 2
        self.gadget_cd = 0.0
        self.status = {"shield": 0.0, "overdrive": 0.0, "invis": 0.0,
                       "invuln": 0.0, "boost": 0.0}
        self.spawn_shield = 2.2
        self.reveal = 0.0
        self.hit_flash = 0.0
        self.last_hit = 99.0
        self.push_x = self.push_y = 0.0
        self.bob = random.uniform(0, 6.28)
        self.recoil = 0.0
        self.kills = 0
        self.deaths = 0
        self.damage_done = 0
        self.gems_collected = 0
        self.carried = 0
        self.supers_used = 0
        self.brain = None if is_player else BotBrain(self)
        if not is_player:
            self.brain.dmg = DIFF_CFG[game.difficulty]["dmg"]

    @property
    def color(self):
        return self.hero["color"]

    @property
    def light(self):
        return self.hero["light"]

    @property
    def team_color(self):
        return TEAM_COLORS[self.team]["main"]

    def outgoing(self, amount):
        if self.brain:
            return amount * self.brain.dmg
        return amount

    def gain_super(self, amount):
        if not self.alive:
            return
        self.super = min(100.0, self.super + amount / self.hero["charge"] * 100.0)

    def in_bush(self):
        if not self.alive:
            return False
        return any(point_in_rect(self.x, self.y, rect)
                   for rect in self.game.bushes)

    def take_damage(self, amount, source=None):
        if not self.alive or self.game.finished:
            return 0
        if self.spawn_shield > 0 or self.status["invuln"] > 0:
            return 0
        if self.status["shield"] > 0:
            amount *= 0.5
        amount = max(1, int(amount))
        self.hp -= amount
        self.last_hit = 0.0
        self.reveal = max(self.reveal, 1.2)
        self.hit_flash = 0.14
        if source:
            source.damage_done += amount
            source.gain_super(amount)
        self.game.texts.append(FloatText(
            self.x, self.y - 26, "-%d" % amount,
            "#ffd7df" if self.team == 0 else "#ffb0bd", 14, 0.7))
        self.game.spark(self.x, self.y, "#ff9fb0", 6, 190, 0.35)
        self.game.shake = min(12.0, self.game.shake + 1.7)
        if self.hp <= 0:
            self.game.kill_brawler(self, source)
        return amount

    def heal(self, amount, source=None, quiet=False):
        if not self.alive or self.hp >= self.max_hp:
            return 0
        healed = min(self.max_hp - self.hp, amount)
        self.hp += healed
        if source:
            source.gain_super(healed * 0.45)
        if not quiet:
            self.game.texts.append(FloatText(
                self.x, self.y - 30, "+%d" % int(healed), GREEN, 14, 0.8))
            self.game.spark(self.x, self.y, GREEN, 5, 130, 0.45)
        return healed


# ---------------------------------------------------------------- ИИ
class BotBrain:
    def __init__(self, owner):
        self.o = owner
        self.game = owner.game
        cfg = DIFF_CFG[self.game.difficulty]
        self.aim_err = cfg["aim"]
        self.react_cfg = cfg["react"]
        self.dmg = cfg["dmg"]
        self.think = 0.0
        self.target = None
        self.react = 0.0
        self.path = []
        self.path_t = 0.0
        self.last_goal = None
        self.strafe = random.choice((-1, 1))
        self.strafe_t = random.uniform(0.8, 2.2)

    def update(self, dt):
        o = self.o
        if not o.alive:
            return
        g = self.game
        self.think -= dt
        self.strafe_t -= dt
        if self.strafe_t <= 0:
            self.strafe *= -1
            self.strafe_t = random.uniform(0.9, 2.3)
        if self.think <= 0:
            self.think = 0.10 + random.random() * 0.08
            found = g.pick_target(o)
            if found is not self.target:
                self.react = self.react_cfg
            self.target = found
        target = self.target
        if target and (not target.alive or not g.can_see(o, target)):
            target = self.target = None
        if o.gadget > 0 and o.gadget_cd <= 0 and o.hp < o.max_hp * 0.34:
            g.use_gadget(o, self.escape_angle())
        if target:
            self.react = max(0.0, self.react - dt)
        goal = self.choose_goal(target)
        if goal is not None:
            self.follow(goal, dt)
        else:
            o.move_x = o.move_y = 0.0
        if target:
            self.fight(target, dt)

    def escape_angle(self):
        goal = SPAWNS[self.o.team][self.o.slot]
        return angle_to(self.o.x, self.o.y, goal[0], goal[1])

    def choose_goal(self, target):
        o = self.o
        g = self.game
        hero = o.hero
        low = o.hp < o.max_hp * 0.34
        if low and hero["super"] != "heal":
            sp = SPAWNS[o.team][o.slot]
            return (sp[0] + random.uniform(-12, 12),
                    sp[1] + random.uniform(-12, 12))
        if g.mode == "gems":
            gem = g.nearest_gem(o)
            if gem is not None and (target is None or g.gem_dist(o, gem) < 290
                                    or o.carried < 3):
                return (gem.x, gem.y)
            if target is None and g.team_gems(o.team) >= 10:
                sp = SPAWNS[o.team][o.slot]
                return (sp[0], sp[1])
        if target:
            d = dist(o.x, o.y, target.x, target.y)
            pref = hero["ai_range"]
            if d > pref * 1.3:
                return (target.x, target.y)
            if d < pref * 0.68:
                ang = math.atan2(o.y - target.y, o.x - target.x)
                return (clamp(o.x + math.cos(ang) * 150, 34, AW - 34),
                        clamp(o.y + math.sin(ang) * 150, 34, AH - 34))
            ang = math.atan2(o.y - target.y, o.x - target.x)
            ang += self.strafe * 0.62
            return (clamp(target.x + math.cos(ang) * pref, 34, AW - 34),
                    clamp(target.y + math.sin(ang) * pref, 34, AH - 34))
        enemy = g.nearest_enemy_any(o)
        if enemy is not None:
            return (enemy.x, enemy.y)
        if g.mode == "gems":
            return MINE
        return (AW / 2, AH / 2)

    def follow(self, goal, dt):
        o = self.o
        g = self.game
        if (self.path_t <= 0 or self.last_goal is None
                or dist(goal[0], goal[1], self.last_goal[0],
                        self.last_goal[1]) > 85):
            self.path = g.find_path((o.x, o.y), goal)
            self.path_t = 0.42 + random.random() * 0.18
            self.last_goal = goal
        self.path_t -= dt
        if self.path:
            wx, wy = self.path[0]
            if dist(o.x, o.y, wx, wy) < 22:
                self.path.pop(0)
                if not self.path:
                    o.move_x = o.move_y = 0.0
                    return
                wx, wy = self.path[0]
            mx, my = norm(wx - o.x, wy - o.y)
            o.move_x, o.move_y = mx, my
        else:
            mx, my = norm(goal[0] - o.x, goal[1] - o.y)
            o.move_x, o.move_y = mx, my

    def fight(self, target, dt):
        o = self.o
        g = self.game
        hero = o.hero
        d = dist(o.x, o.y, target.x, target.y)
        lead_time = (0.42 + d / 1250.0 if hero["attack_kind"] == "lob"
                     else d / max(1.0, hero["bullet_speed"]))
        px = target.x + target.vx * lead_time * 0.72
        py = target.y + target.vy * lead_time * 0.72
        error = self.aim_err * (0.55 + min(1.2, d / 620.0))
        aim = angle_to(o.x, o.y, px, py) + random.uniform(-error, error)
        o.aim = aim
        if g.can_see(o, target) and d <= hero["range"] * 1.03:
            if self.react <= 0 and o.attack_cd <= 0 and o.ammo >= 1:
                g.fire_attack(o, aim, aim_point=(px, py))
        if o.super < 100 or self.react > 0:
            return
        if hero["super"] == "heal":
            hurt = [a for a in g.brawlers
                    if a.alive and a.team == o.team
                    and dist(o.x, o.y, a.x, a.y) < 390
                    and a.hp < a.max_hp * 0.72]
            if hurt:
                g.use_super(o, aim)
            return
        if g.can_see(o, target) and d < 860:
            g.use_super(o, aim, aim_point=(px, py))

    def look_angle(self):
        if self.target:
            return angle_to(self.o.x, self.o.y, self.target.x, self.target.y)
        return self.o.aim

class Match:
    def __init__(self, app, hero_id, mode):
        self.app = app
        self.mode = mode if mode in MODES else "skirmish"
        self.hero_id = hero_id if hero_id in HEROES else "volt"
        self.difficulty = app.save.data["settings"].get("difficulty", "Обычно")
        self.walls = [tuple(w) for w in WALL_DEFS]
        self.bushes = [tuple(b) for b in BUSH_DEFS]
        self.brawlers = []
        self.player = None
        self.projectiles = []
        self.lobs = []
        self.booms = []
        self.gems = []
        self.particles = []
        self.texts = []
        self.rings = []
        self.beams = []
        self.feed = []
        self.t = 0.0
        self.intro = 2.35
        self.time_left = MODES[self.mode]["time"]
        self.finished = False
        self.finished_t = 0.0
        self.winner = None
        self.result = None
        self.reason = ""
        self.recorded = False
        self.shake = 0.0
        self.flash = 0.0
        self.gem_flash = 0.0
        self.gem_timer = 1.1
        self.team_kills = {0: 0, 1: 0}
        self.hold = {0: 0.0, 1: 0.0}
        self.spawn_points = SPAWNS
        self.nav_cell = 32
        self.nav_w = int(math.ceil(AW / self.nav_cell))
        self.nav_h = int(math.ceil(AH / self.nav_cell))
        self.nav_blocked = []
        self._build_nav()
        self._setup_teams()

    # ------------------------------------------------------------ создание
    def _build_nav(self):
        pad = 23.0
        blocked = []
        for cy in range(self.nav_h):
            row = []
            for cx in range(self.nav_w):
                px = cx * self.nav_cell + self.nav_cell / 2
                py = cy * self.nav_cell + self.nav_cell / 2
                row.append(self.point_in_wall(px, py, pad)
                           or px < 26 or py < 26
                           or px > AW - 26 or py > AH - 26)
            blocked.append(row)
        self.nav_blocked = blocked

    def _setup_teams(self):
        rng = random.Random()
        pool = [h for h in HERO_ORDER if h != self.hero_id]
        ally_heroes = rng.sample(pool, 2)
        enemy_heroes = rng.sample(list(HERO_ORDER), 3)
        names = list(BOT_NAMES)
        rng.shuffle(names)

        px, py = self.spawn_points[0][1]
        player = Brawler(self, self.hero_id, 0, "ВЫ", 1, px, py, is_player=True)
        self.player = player
        self.brawlers.append(player)

        ally_slots = ((0, ally_heroes[0]), (2, ally_heroes[1]))
        for slot, hid in ally_slots:
            x, y = self.spawn_points[0][slot]
            self.brawlers.append(Brawler(self, hid, 0, names.pop(), slot, x, y))

        for slot, hid in enumerate(enemy_heroes):
            x, y = self.spawn_points[1][slot]
            self.brawlers.append(Brawler(self, hid, 1, names.pop(), slot, x, y))

    # ------------------------------------------------------------ цикл
    def update(self, dt):
        self.t += dt
        self.shake = max(0.0, self.shake - 34.0 * dt)
        self.flash = max(0.0, self.flash - 2.0 * dt)
        self.update_fx(dt)
        for entry in self.feed:
            entry["ttl"] -= dt
        self.feed = [f for f in self.feed if f["ttl"] > 0]
        if self.finished:
            self.finished_t += dt
            return
        if self.intro > 0:
            self.intro -= dt
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0.0
            self.end_by_time()
            return

        for b in self.brawlers:
            self.tick_brawler(b, dt)
        for b in self.brawlers:
            if not b.alive:
                continue
            if b.brain:
                b.brain.update(dt)
            elif b.is_player:
                self.update_player(b, dt)
        for b in self.brawlers:
            if b.alive:
                self.move_brawler(b, dt)
                self.collect_gems(b)

        self.update_projectiles(dt)
        self.update_lobs(dt)
        self.update_booms(dt)
        self.update_gems(dt)
        if self.mode == "gems":
            self.update_hold(dt)

    def update_player(self, b, dt):
        keys = self.app.keys
        mx = (1 if ("right" in keys or "d" in keys) else 0) - \
             (1 if ("left" in keys or "a" in keys) else 0)
        my = (1 if ("down" in keys or "s" in keys) else 0) - \
             (1 if ("up" in keys or "w" in keys) else 0)
        b.move_x, b.move_y = float(mx), float(my)
        wx = self.app.mouse[0] - AX
        wy = self.app.mouse[1] - AY
        b.aim = math.atan2(wy - b.y, wx - b.x)
        if self.app.fire_held:
            self.fire_attack(b, b.aim, aim_point=(wx, wy))

    def tick_brawler(self, b, dt):
        if not b.alive:
            b.respawn -= dt
            if b.respawn <= 0:
                self.respawn(b)
            return
        for key in b.status:
            if b.status[key] > 0:
                b.status[key] = max(0.0, b.status[key] - dt)
        b.spawn_shield = max(0.0, b.spawn_shield - dt)
        b.attack_cd = max(0.0, b.attack_cd - dt)
        b.gadget_cd = max(0.0, b.gadget_cd - dt)
        b.reveal = max(0.0, b.reveal - dt)
        b.hit_flash = max(0.0, b.hit_flash - dt)
        b.recoil = max(0.0, b.recoil - dt * 8.0)
        b.last_hit += dt
        if b.last_hit > 4.2 and b.hp < b.max_hp:
            b.hp = min(b.max_hp, b.hp + b.max_hp * 0.11 * dt)
        if b.ammo < b.hero["ammo"]:
            b.reload_acc += dt
            if b.reload_acc >= b.hero["reload"]:
                b.reload_acc = 0.0
                b.ammo += 1
        else:
            b.reload_acc = 0.0

    def move_brawler(self, b, dt):
        mx, my = norm(b.move_x, b.move_y)
        speed = b.hero["speed"]
        if b.status["boost"] > 0:
            speed *= 1.6
        dx = (mx * speed + b.push_x) * dt
        dy = (my * speed + b.push_y) * dt
        old_x, old_y = b.x, b.y
        if not self.hits_wall(b.x + dx, b.y, b.radius):
            b.x += dx
        else:
            b.push_x = 0.0
        if not self.hits_wall(b.x, b.y + dy, b.radius):
            b.y += dy
        else:
            b.push_y = 0.0
        b.x = clamp(b.x, b.radius, AW - b.radius)
        b.y = clamp(b.y, b.radius, AH - b.radius)
        inv = 1.0 / max(1e-6, dt)
        b.vx = (b.x - old_x) * inv
        b.vy = (b.y - old_y) * inv
        b.bob += dt * (4.0 + abs(b.vx) * 0.01)
        damp = math.exp(-6.0 * dt)
        b.push_x *= damp
        b.push_y *= damp

    def respawn(self, b):
        x, y = self.spawn_points[b.team][b.slot]
        b.x, b.y = x, y
        b.hp = b.max_hp
        b.alive = True
        b.respawn = 0.0
        b.ammo = b.hero["ammo"]
        b.reload_acc = 0.0
        b.super = 0.0
        b.attack_cd = 0.0
        b.push_x = b.push_y = 0.0
        b.spawn_shield = 2.2
        b.status = {k: 0.0 for k in b.status}
        b.vx = b.vy = 0.0
        self.rings.append(Ring(x, y, 12, 58, TEAM_COLORS[b.team]["main"], 0.5, 2))
        self.burst(x, y, TEAM_COLORS[b.team]["main"], 10, 150, 0.45)

    # ------------------------------------------------------------ бой
    def fire_attack(self, b, angle, aim_point=None):
        if not b.alive or b.attack_cd > 0 or b.ammo < 1:
            return False
        hero = b.hero
        over = b.status["overdrive"] > 0
        if not over:
            b.ammo -= 1
        b.attack_cd = hero["cooldown"] * (0.62 if over else 1.0)
        b.recoil = 1.0
        b.reveal = max(b.reveal, 0.8)
        px = b.x + math.cos(angle) * (b.radius + 12)
        py = b.y + math.sin(angle) * (b.radius + 12)
        damage = b.outgoing(hero["damage"])
        if hero["attack_kind"] == "lob":
            if aim_point is None:
                aim_point = (b.x + math.cos(angle) * hero["range"] * 0.8,
                             b.y + math.sin(angle) * hero["range"] * 0.8)
            tx, ty = aim_point
            d = dist(b.x, b.y, tx, ty)
            if d > hero["range"]:
                tx = b.x + (tx - b.x) / d * hero["range"]
                ty = b.y + (ty - b.y) / d * hero["range"]
            tx = clamp(tx, 18, AW - 18)
            ty = clamp(ty, 18, AH - 18)
            self.lobs.append(Lob(self, b, (b.x, b.y), (tx, ty), damage,
                                 hero.get("splash", 100), b.color, b.light))
        else:
            shots = hero["shots"]
            spread = math.radians(hero.get("spread", 0))
            for i in range(shots):
                if shots > 1:
                    a = angle + (i / (shots - 1) - 0.5) * spread
                else:
                    a = angle + random.uniform(-spread * 0.5, spread * 0.5)
                self.projectiles.append(Projectile(
                    self, b, px, py, a, hero["bullet_speed"], damage,
                    hero["range"], hero["bullet_radius"], b.color, b.light,
                    pierce=(over and hero["super"] == "overdrive"),
                    kind=hero["attack_kind"]))
        self.burst(px, py, b.light, 3, 90, 0.18, size=2)
        self.app.sound.play("heavy" if b.hero_id in ("grom", "iskra") else "shoot")
        return True

    def update_projectiles(self, dt):
        for p in list(self.projectiles):
            alive = p.update(dt)
            if not alive:
                self.projectiles.remove(p)
                continue
            if self.point_in_wall(p.x, p.y):
                self.spark(p.x, p.y, p.light, 4, 130, 0.25)
                self.projectiles.remove(p)
                continue
            if p.x < -20 or p.x > AW + 20 or p.y < -20 or p.y > AH + 20:
                self.projectiles.remove(p)
                continue
            for e in self.brawlers:
                if (not e.alive or e.team == p.team
                        or id(e) in p.hit):
                    continue
                if dist(p.x, p.y, e.x, e.y) <= e.radius + p.radius:
                    e.take_damage(p.damage, p.owner)
                    p.hit.add(id(e))
                    self.burst(p.x, p.y, p.light, 4, 150, 0.25, size=2)
                    self.app.sound.play("hit")
                    if not p.pierce:
                        if p in self.projectiles:
                            self.projectiles.remove(p)
                        break

    def update_lobs(self, dt):
        for lob in list(self.lobs):
            if not lob.update(dt):
                self.lobs.remove(lob)

    def update_booms(self, dt):
        for boom in list(self.booms):
            if not boom.update(dt):
                self.booms.remove(boom)

    def boom(self, x, y, radius, damage, owner, color=None, push=0.0):
        color = color or GOLD
        self.rings.append(Ring(x, y, radius * 0.2, radius, color, 0.45, 4))
        self.rings.append(Ring(x, y, radius * 0.1, radius * 0.72, "#ffffff", 0.24, 2))
        self.burst(x, y, color, 16, 260, 0.55, size=4)
        self.shake = min(14.0, self.shake + 3.4)
        self.app.sound.play("heavy")
        for e in self.brawlers:
            if not e.alive or e.team == owner.team:
                continue
            d = dist(x, y, e.x, e.y)
            if d <= radius + e.radius and self.line_clear(x, y, e.x, e.y):
                e.take_damage(damage, owner)
                if push and e.alive:
                    ang = angle_to(x, y, e.x, e.y)
                    e.push_x += math.cos(ang) * push
                    e.push_y += math.sin(ang) * push

    def collect_gems(self, b):
        if self.mode != "gems" or not b.alive:
            return
        for gem in list(self.gems):
            if dist(b.x, b.y, gem.x, gem.y) <= b.radius + 16:
                self.gems.remove(gem)
                b.carried += 1
                b.gems_collected += 1
                self.texts.append(FloatText(gem.x, gem.y - 14,
                                            "+1", VIOLET, 14, 0.7))
                self.burst(gem.x, gem.y, VIOLET, 7, 130, 0.4, size=2)
                if b.is_player:
                    self.app.sound.play("pickup")
                    self.gem_flash = 0.6

    def update_gems(self, dt):
        if self.mode != "gems" or self.finished:
            return
        self.gem_timer -= dt
        ground = len(self.gems)
        if self.gem_timer <= 0 and ground < 8:
            self.gem_timer = 2.15
            x = MINE[0] + random.uniform(-12, 12)
            y = MINE[1] + random.uniform(-12, 12)
            ang = random.uniform(0, 6.283)
            speed = random.uniform(26, 66)
            self.gems.append(Gem(x, y, math.cos(ang) * speed,
                                 math.sin(ang) * speed))
            self.rings.append(Ring(x, y, 4, 28, VIOLET, 0.35, 2))
        for gem in self.gems:
            gem.update(dt)

    def update_hold(self, dt):
        for team in (0, 1):
            if self.team_gems(team) >= 10:
                self.hold[team] += dt
                if self.hold[team] >= 15.0:
                    self.end_match(team, "КРИСТАЛЛЫ УДЕРЖАНЫ")
                    return
            else:
                self.hold[team] = 0.0

    def kill_brawler(self, victim, killer):
        if not victim.alive or self.finished:
            return
        victim.alive = False
        victim.deaths += 1
        victim.respawn = 4.2
        victim.hp = 0
        victim.push_x = victim.push_y = 0.0
        if victim.carried:
            for _ in range(victim.carried):
                ang = random.uniform(0, 6.283)
                speed = random.uniform(50, 130)
                self.gems.append(Gem(victim.x, victim.y,
                                     math.cos(ang) * speed,
                                     math.sin(ang) * speed))
            victim.carried = 0
        if killer is not None and killer.team != victim.team:
            killer.kills += 1
            self.team_kills[killer.team] += 1
            self.add_feed(killer, victim)
        else:
            self.add_feed(None, victim)
        self.burst(victim.x, victim.y, victim.color, 22, 260, 0.8, size=4)
        self.rings.append(Ring(victim.x, victim.y, 10, 70, victim.light, 0.6, 3))
        self.shake = min(16.0, self.shake + 5.0)
        self.app.sound.play("death")
        if victim.is_player:
            self.flash = 1.0
        if self.mode == "skirmish":
            scoring_team = killer.team if killer else 1 - victim.team
            if self.team_kills[scoring_team] >= 15:
                self.end_match(scoring_team, "15 УНИЧТОЖЕНИЙ")

    def use_super(self, b, angle, aim_point=None):
        if not b.alive or b.super < 100.0:
            return False
        hero = b.hero
        b.super = 0.0
        b.supers_used += 1
        self.app.sound.play("super")
        self.shake = min(18.0, self.shake + 6.0)
        name = hero["super_name"]
        self.texts.append(FloatText(b.x, b.y - 48, name, b.light, 16, 0.9,
                                    vy=-58))
        self.rings.append(Ring(b.x, b.y, 18, 74, b.light, 0.5, 3))
        self.burst(b.x, b.y, b.light, 14, 200, 0.55, size=3)
        kind = hero["super"]
        if kind == "overdrive":
            b.status["overdrive"] = 4.5
            self.rings.append(Ring(b.x, b.y, 20, 100, GOLD, 0.65, 4))
        elif kind == "shockwave":
            self.boom(b.x, b.y, 185, 1400, b, "#ffb35c", push=620)
        elif kind == "beam":
            length = self.clip_ray(b.x, b.y, angle, 950)
            ex = b.x + math.cos(angle) * length
            ey = b.y + math.sin(angle) * length
            self.beams.append(BeamFx(b.x, b.y, ex, ey, b.light, 0.38, 16))
            self.beams.append(BeamFx(b.x, b.y, ex, ey, "#ffffff", 0.22, 5))
            for e in self.brawlers:
                if not e.alive or e.team == b.team:
                    continue
                if (point_seg_dist(e.x, e.y, b.x, b.y, ex, ey)
                        <= 34 + e.radius
                        and self.line_clear(b.x, b.y, e.x, e.y)):
                    e.take_damage(b.outgoing(2300), b)
                    ang = angle_to(b.x, b.y, e.x, e.y)
                    e.push_x += math.cos(ang) * 260
                    e.push_y += math.sin(ang) * 260
            for i in range(24):
                t = i / 23.0
                self.spark(lerp(b.x, ex, t), lerp(b.y, ey, t),
                           b.light, 1, 50, 0.25, size=2)
        elif kind == "heal":
            for ally in self.brawlers:
                if ally.alive and ally.team == b.team \
                        and dist(b.x, b.y, ally.x, ally.y) <= 400:
                    ally.heal(2400, b)
                    ally.status["shield"] = max(ally.status["shield"], 3.0)
                    self.rings.append(Ring(ally.x, ally.y, 16, 50, GREEN, 0.6, 2))
            self.rings.append(Ring(b.x, b.y, 30, 400, GREEN, 0.8, 5))
            self.app.sound.play("heal")
        elif kind == "barrage":
            if aim_point is None:
                aim_point = (b.x + math.cos(angle) * 430,
                             b.y + math.sin(angle) * 430)
            tx = clamp(aim_point[0], 30, AW - 30)
            ty = clamp(aim_point[1], 30, AH - 30)
            for i in range(5):
                ox = tx + random.uniform(-135, 135)
                oy = ty + random.uniform(-120, 120)
                self.booms.append(DelayedBoom(
                    self, clamp(ox, 20, AW - 20), clamp(oy, 20, AH - 20),
                    0.16 + i * 0.13, 105, b.outgoing(520), b, b.color))
        elif kind == "dash":
            ex, ey = self.clip_dash(b.x, b.y, angle, 400)
            for e in self.brawlers:
                if not e.alive or e.team == b.team:
                    continue
                if point_seg_dist(e.x, e.y, b.x, b.y, ex, ey) < 56:
                    e.take_damage(b.outgoing(1600), b)
                    ang = angle_to(b.x, b.y, e.x, e.y)
                    e.push_x += math.cos(ang) * 180
                    e.push_y += math.sin(ang) * 180
            for i in range(14):
                t = i / 13.0
                self.spark(lerp(b.x, ex, t), lerp(b.y, ey, t),
                           b.color, 3, 160, 0.5, size=4)
            b.x, b.y = ex, ey
            b.status["invuln"] = max(b.status["invuln"], 0.45)
            self.rings.append(Ring(ex, ey, 10, 62, b.light, 0.4, 3))
        return True

    def use_gadget(self, b, angle=None):
        if not b.alive or b.gadget <= 0 or b.gadget_cd > 0:
            return False
        b.gadget -= 1
        b.gadget_cd = 0.9
        hero = b.hero
        if angle is None:
            angle = b.aim
        kind = hero["gadget"]
        if kind == "boost":
            b.status["boost"] = 3.0
            self.texts.append(FloatText(b.x, b.y - 36, "УСКОРЕНИЕ",
                                        b.light, 13, 0.7))
            self.burst(b.x, b.y, b.light, 12, 220, 0.4, size=2)
        elif kind == "shield":
            b.status["shield"] = max(b.status["shield"], 4.0)
            self.texts.append(FloatText(b.x, b.y - 36, "БРОНЯ",
                                        CYAN, 13, 0.7))
            self.rings.append(Ring(b.x, b.y, 20, 52, CYAN, 0.55, 3))
        elif kind == "dash":
            ex, ey = self.clip_dash(b.x, b.y, angle, 190)
            for i in range(8):
                t = i / 7.0
                self.spark(lerp(b.x, ex, t), lerp(b.y, ey, t),
                           b.light, 2, 90, 0.35, size=3)
            b.x, b.y = ex, ey
            b.status["invuln"] = max(b.status["invuln"], 0.3)
        elif kind == "heal":
            b.heal(b.max_hp * 0.35, b)
            for ally in self.brawlers:
                if ally is not b and ally.alive and ally.team == b.team \
                        and dist(b.x, b.y, ally.x, ally.y) < 230:
                    ally.heal(ally.max_hp * 0.20, b)
            self.rings.append(Ring(b.x, b.y, 20, 220, GREEN, 0.65, 4))
            self.app.sound.play("heal")
        elif kind == "invis":
            b.status["invis"] = 3.0
            self.texts.append(FloatText(b.x, b.y - 36, "МИРАЖ",
                                        b.light, 13, 0.7))
            self.burst(b.x, b.y, b.color, 14, 120, 0.6, size=3)
        self.app.sound.play("click")
        return True

    # ------------------------------------------------------------ вспомогательное
    def add_feed(self, killer, victim):
        self.feed.insert(0, {
            "killer": killer.name if killer else "",
            "kcolor": killer.light if killer else MUTED,
            "victim": victim.name,
            "vcolor": victim.light,
            "ttl": 4.5,
        })
        self.feed = self.feed[:4]

    def burst(self, x, y, color, count=8, speed=180, life=0.5, size=3,
              gravity=150):
        if not self.app.save.data["settings"].get("particles", True):
            return
        for _ in range(count):
            ang = random.uniform(0, 6.283)
            sp = random.uniform(speed * 0.25, speed)
            self.particles.append(Particle(
                x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                random.uniform(life * 0.55, life), color,
                random.uniform(size * 0.5, size), gravity))
        if len(self.particles) > 280:
            del self.particles[:len(self.particles) - 280]

    def spark(self, x, y, color, count=3, speed=140, life=0.3, size=2):
        self.burst(x, y, color, count, speed, life, size, 60)

    def update_fx(self, dt):
        self.gem_flash = max(0.0, getattr(self, "gem_flash", 0.0) - dt * 1.6)
        for p in list(self.particles):
            if not p.update(dt):
                self.particles.remove(p)
        for t in list(self.texts):
            if not t.update(dt):
                self.texts.remove(t)
        for r in list(self.rings):
            if not r.update(dt):
                self.rings.remove(r)
        for beam in list(self.beams):
            if not beam.update(dt):
                self.beams.remove(beam)

    def clip_ray(self, x, y, angle, max_dist):
        steps = int(max_dist / 12)
        for i in range(1, steps + 1):
            d = i * 12
            if self.point_in_wall(x + math.cos(angle) * d,
                                  y + math.sin(angle) * d):
                return max(0.0, d - 12)
        return max_dist

    def clip_dash(self, x, y, angle, max_dist):
        last_x, last_y = x, y
        steps = int(max_dist / 8)
        for i in range(1, steps + 1):
            d = i * 8
            nx = x + math.cos(angle) * d
            ny = y + math.sin(angle) * d
            if self.hits_wall(nx, ny, 17):
                break
            last_x, last_y = nx, ny
        return last_x, last_y

    def point_in_wall(self, x, y, pad=0.0):
        for wx, wy, ww, wh in self.walls:
            if wx - pad <= x <= wx + ww + pad and wy - pad <= y <= wy + wh + pad:
                return True
        return False

    def hits_wall(self, x, y, r):
        if x < r or y < r or x > AW - r or y > AH - r:
            return True
        for wx, wy, ww, wh in self.walls:
            nx = clamp(x, wx, wx + ww)
            ny = clamp(y, wy, wy + wh)
            if (x - nx) ** 2 + (y - ny) ** 2 < r * r:
                return True
        return False

    def line_clear(self, x1, y1, x2, y2, pad=0.0):
        d = dist(x1, y1, x2, y2)
        steps = max(2, int(d / 10))
        for i in range(1, steps):
            t = i / steps
            if self.point_in_wall(lerp(x1, x2, t), lerp(y1, y2, t), pad):
                return False
        return True

    def can_see(self, viewer, target):
        if not target.alive:
            return False
        if target.status["invis"] > 0:
            return False
        d = dist(viewer.x, viewer.y, target.x, target.y)
        if target.in_bush() and target.reveal <= 0 and d > 205:
            return False
        return self.line_clear(viewer.x, viewer.y, target.x, target.y)

    def pick_target(self, b):
        best = None
        best_score = 1e18
        for e in self.brawlers:
            if not e.alive or e.team == b.team:
                continue
            d = dist(b.x, b.y, e.x, e.y)
            if d > 850 or not self.can_see(b, e):
                continue
            score = d
            if e.carried > 0:
                score -= 80 + e.carried * 12
            if e.hp < e.max_hp * 0.35:
                score -= 55
            if e.is_player:
                score -= 20
            if score < best_score:
                best_score = score
                best = e
        return best

    def nearest_enemy_any(self, b):
        best = None
        best_d = 1e18
        for e in self.brawlers:
            if not e.alive or e.team == b.team:
                continue
            d = dist(b.x, b.y, e.x, e.y)
            if d < best_d:
                best_d = d
                best = e
        return best

    def gem_dist(self, b, gem):
        return dist(b.x, b.y, gem.x, gem.y)

    def nearest_gem(self, b):
        best = None
        best_d = 1e18
        for gem in self.gems:
            d = dist(b.x, b.y, gem.x, gem.y)
            if d < best_d:
                best_d = d
                best = gem
        return best

    def team_gems(self, team):
        return sum(b.carried for b in self.brawlers if b.team == team)

    def score(self, team):
        if self.mode == "gems":
            return self.team_gems(team)
        return self.team_kills[team]

    # ------------------------------------------------------------ навигация
    def _free_cell(self, cx, cy):
        if 0 <= cx < self.nav_w and 0 <= cy < self.nav_h \
                and not self.nav_blocked[cy][cx]:
            return cx, cy
        for radius in range(1, 8):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.nav_w and 0 <= ny < self.nav_h \
                            and not self.nav_blocked[ny][nx]:
                        return nx, ny
        return None

    def find_path(self, start, goal):
        cell = self.nav_cell
        scx = clamp(int(start[0] / cell), 0, self.nav_w - 1)
        scy = clamp(int(start[1] / cell), 0, self.nav_h - 1)
        gcx = clamp(int(goal[0] / cell), 0, self.nav_w - 1)
        gcy = clamp(int(goal[1] / cell), 0, self.nav_h - 1)
        start_cell = self._free_cell(scx, scy)
        goal_cell = self._free_cell(gcx, gcy)
        if start_cell is None or goal_cell is None:
            return []
        sx, sy = start_cell
        gx, gy = goal_cell
        if (sx, sy) == (gx, gy):
            if self.line_clear(start[0], start[1], goal[0], goal[1], 22):
                return [goal]
            return [((gx + 0.5) * cell, (gy + 0.5) * cell)]
        open_heap = [(0.0, 0, sx, sy)]
        came = {}
        gscore = {(sx, sy): 0.0}
        visited = set()
        found = False
        while open_heap:
            _, _, cx, cy = heapq.heappop(open_heap)
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            if (cx, cy) == (gx, gy):
                found = True
                break
            base = gscore[(cx, cy)]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < self.nav_w and 0 <= ny < self.nav_h):
                        continue
                    if self.nav_blocked[ny][nx]:
                        continue
                    if dx and dy:
                        if self.nav_blocked[cy][nx] or self.nav_blocked[ny][cx]:
                            continue
                    step = 1.4142 if (dx and dy) else 1.0
                    ng = base + step
                    if ng < gscore.get((nx, ny), 1e18):
                        gscore[(nx, ny)] = ng
                        came[(nx, ny)] = (cx, cy)
                        hx = abs(nx - gx) + abs(ny - gy)
                        heapq.heappush(open_heap, (ng + hx, len(visited), nx, ny))
        if not found:
            return []
        cells = []
        cur = (gx, gy)
        while cur in came:
            cells.append(cur)
            cur = came[cur]
        cells.append((sx, sy))
        cells.reverse()
        points = [((cx + 0.5) * cell, (cy + 0.5) * cell) for cx, cy in cells]
        goal_pt = goal
        if self.point_in_wall(goal[0], goal[1], 20):
            goal_pt = points[-1]
        raw = [start] + points + [goal_pt]
        out = []
        i = 0
        while i < len(raw) - 1:
            j = len(raw) - 1
            while j > i + 1 and not self.line_clear(
                    raw[i][0], raw[i][1], raw[j][0], raw[j][1], 21):
                j -= 1
            out.append(raw[j])
            i = j
        return out

    # ------------------------------------------------------------ итог матча
    def end_by_time(self):
        s0, s1 = self.score(0), self.score(1)
        if s0 > s1:
            self.end_match(0, "ВРЕМЯ ВЫШЛО")
        elif s1 > s0:
            self.end_match(1, "ВРЕМЯ ВЫШЛО")
        else:
            self.end_match(None, "НИЧЬЯ")

    def end_match(self, winner, reason):
        if self.finished:
            return
        self.finished = True
        self.finished_t = 0.0
        self.winner = winner
        self.reason = reason
        self.result = ("draw" if winner is None
                       else "win" if winner == 0 else "lose")
        self.shake = min(18.0, self.shake + 8.0)
        for b in self.brawlers:
            b.move_x = b.move_y = 0.0
        if winner == 0:
            self.app.sound.play("win")
            self.burst(self.player.x, self.player.y, GOLD, 30, 260, 1.0, size=4)
        elif winner == 1:
            self.app.sound.play("lose")
        else:
            self.app.sound.play("click")

    # ------------------------------------------------------------ отрисовка
    def draw(self, c):
        shake_on = self.app.save.data["settings"].get("shake", True)
        amp = self.shake if shake_on else 0.0
        sx = random.uniform(-amp, amp) * 0.55 if amp else 0.0
        sy = random.uniform(-amp, amp) * 0.55 if amp else 0.0
        ox, oy = AX + sx, AY + sy
        self.draw_arena(c, ox, oy)
        self.draw_gems(c, ox, oy)
        self.draw_brawlers(c, ox, oy)
        self.draw_bushes_over(c, ox, oy)
        self.draw_projectiles(c, ox, oy)
        self.draw_effects(c, ox, oy)
        self.draw_aim(c, ox, oy)
        self.draw_hud(c)
        self.draw_feed(c)
        if self.intro > 0:
            self.draw_intro(c)
        if self.finished:
            self.draw_finish(c)

    def draw_arena(self, c, ox, oy):
        c.create_rectangle(0, 0, 1280, 800, fill=BG, outline="")
        c.create_rectangle(0, 0, 1280, 96, fill="#060d18", outline="")
        c.create_line(0, 96, 1280, 96, fill=LINE)
        for i in range(1, 5):
            c.create_line(0, 96 + i, 1280, 96 + i,
                          fill=mix("#060d18", BG, i / 5.0))
        rrect(c, AX - 14, AY - 14, AX + AW + 14, AY + AH + 14, 20,
              fill="#03070e", outline=LINE, width=1)
        rrect(c, AX - 2, AY - 2, AX + AW + 2, AY + AH + 2, 10,
              fill="#071120", outline="#1e3e66", width=2)
        c.create_rectangle(AX, AY, AX + AW, AY + AH, fill="#081423",
                           outline="")
        for x in range(0, AW + 1, 40):
            col = "#0f2138" if (x // 40) % 4 == 0 else "#0b192b"
            c.create_line(AX + x, AY, AX + x, AY + AH, fill=col)
        for y in range(0, AH + 1, 40):
            col = "#0f2138" if (y // 40) % 4 == 0 else "#0b192b"
            c.create_line(AX, AY + y, AX + AW, AY + y, fill=col)
        for x in range(40, AW, 80):
            for y in range(40, AH, 80):
                c.create_oval(AX + x - 1, AY + y - 1, AX + x + 1, AY + y + 1,
                              fill="#173252", outline="")
        text_glow(c, AX + AW / 2, AY + AH / 2, "NEON BRAWL",
                  (F_TITLE, 46), "#0c2037", glow="#081423", off=0)
        c.create_text(AX + AW / 2, AY + AH / 2 + 36,
                      text="АРЕНА 3×3", font=(F_UI, 11),
                      fill="#123052")
        # базы команд
        for team in (0, 1):
            zx, zy, zw, zh = SPAWN_ZONES[team]
            tx, ty = AX + zx, AY + zy
            info = TEAM_COLORS[team]
            rrect(c, tx, ty, tx + zw, ty + zh, 14,
                  fill=info["main"], stipple="gray12", outline=info["main"],
                  width=2)
            c.create_text(tx + zw / 2, ty + zh - 18,
                          text="БАЗА · " + info["name"],
                          font=(F_UI, 8, "bold"),
                          fill=mix(info["main"], TEXT, 0.35))
            for cx, cy, dx, dy in ((tx + 14, ty + 14, 1, 1),
                                   (tx + zw - 14, ty + 14, -1, 1),
                                   (tx + 14, ty + zh - 14, 1, -1),
                                   (tx + zw - 14, ty + zh - 14, -1, -1)):
                c.create_line(cx, cy, cx + 18 * dx, cy, fill=info["main"])
                c.create_line(cx, cy, cx, cy + 18 * dy, fill=info["main"])
        # центр
        mx, my = AX + MINE[0], AY + MINE[1]
        pulse = 1.0 + 0.06 * math.sin(self.t * 3.0)
        c.create_polygon(hex_points(mx, my, 74), fill="#0b1426",
                         outline="#243b60", width=2)
        c.create_polygon(hex_points(mx, my, 58 * pulse), fill="#121b36",
                         outline=VIOLET if self.mode == "gems" else CYAN,
                         width=2)
        c.create_polygon(hex_points(mx, my, 44), fill="#171542",
                         outline="#4b3b85", width=1)
        if self.mode == "gems":
            crystal(c, mx, my - 2, 17, VIOLET, "#f2e4ff", rot=self.t * 0.6)
            c.create_text(mx, my + 50, text="КРИСТАЛЛЫ",
                          font=(F_UI, 9, "bold"), fill=VIOLET)
        else:
            c.create_text(mx, my, text="✦", font=(F_TITLE, 34), fill=CYAN)
            c.create_text(mx, my + 50, text="СХВАТКА",
                          font=(F_UI, 9, "bold"), fill=MUTED)
        # земля кустов
        for rect in self.bushes:
            bx, by, bw, bh = rect
            rrect(c, AX + bx - 6, AY + by - 4, AX + bx + bw + 6,
                  AY + by + bh + 6, 18, fill="#0a201a", outline="#133629")
            for bx2, by2, br in self.bush_blobs(rect):
                c.create_oval(AX + bx2 - br, AY + by2 - br,
                              AX + bx2 + br, AY + by2 + br,
                              fill="#0d2920", outline="#153f2e")
        # стены
        for wx, wy, ww, wh in self.walls:
            x, y = AX + wx, AY + wy
            rrect(c, x + 5, y + 9, x + ww + 5, y + wh + 9, 7,
                  fill="#02050b", outline="")
            rrect(c, x, y, x + ww, y + wh, 6, fill="#0b172a",
                  outline="#223e5e", width=2)
            rrect(c, x + 2, y - 5, x + ww - 2, y + wh - 13, 5,
                  fill="#152741", outline="#35587f", width=1)
            c.create_line(x + 8, y - 3, x + ww - 8, y - 3,
                          fill="#4c739c")
            for cx, cy in ((x + 9, y + 9), (x + ww - 9, y + 9),
                           (x + 9, y + wh - 9), (x + ww - 9, y + wh - 9)):
                c.create_oval(cx - 2, cy - 2, cx + 2, cy + 2,
                              fill="#2c4b70", outline="")
        # конфетти/брызги финала
        if self.finished and self.winner == 0:
            for i in range(6):
                ang = self.t * 1.2 + i * 1.047
                rr = 120 + 30 * math.sin(self.t * 2 + i)
                px = mx + math.cos(ang) * rr
                py = my + math.sin(ang) * rr * 0.58
                c.create_oval(px - 2, py - 2, px + 2, py + 2,
                              fill=GOLD, outline="")

    def bush_blobs(self, rect):
        bx, by, bw, bh = rect
        out = []
        for i in range(9):
            fx = ((i * 37 + 17) % 93) / 93.0
            fy = ((i * 53 + 11) % 87) / 87.0
            out.append((bx + 10 + fx * (bw - 20),
                        by + 9 + fy * (bh - 18),
                        min(bh, bw) * (0.18 + ((i * 13) % 9) / 45.0)))
        return out

    def draw_bushes_over(self, c, ox, oy):
        for rect in self.bushes:
            bx, by, bw, bh = rect
            for i, (bx2, by2, br) in enumerate(self.bush_blobs(rect)):
                col = mix("#123a2b", "#236b4e", (i % 5) / 5.0)
                c.create_oval(ox + bx2 - br, oy + by2 - br,
                              ox + bx2 + br, oy + by2 + br,
                              fill=col, outline="#0c2b20")
                c.create_oval(ox + bx2 - br * 0.55, oy + by2 - br * 0.62,
                              ox + bx2 - br * 0.12, oy + by2 - br * 0.22,
                              fill="#2d7f5b", outline="")
            c.create_text(ox + bx + bw / 2, oy + by + bh / 2,
                          text="КУСТЫ", font=(F_UI, 7),
                          fill="#1a4c38")
        p = self.player
        if p and p.alive and p.in_bush():
            px, py = ox + p.x, oy + p.y
            c.create_oval(px - 27, py - 27, px + 27, py + 27,
                          outline="#d8f6ff", width=1, dash=(4, 4))
            c.create_text(px, py - 48, text="ВЫ", font=(F_UI, 8, "bold"),
                          fill="#ffffff")

    def draw_gems(self, c, ox, oy):
        for gem in self.gems:
            bob = math.sin(self.t * 3.2 + gem.t) * 4.0
            gx, gy = ox + gem.x, oy + gem.y
            c.create_oval(gx - 13, gy + 7, gx + 13, gy + 15,
                          fill="#0a0a1e", outline="")
            c.create_oval(gx - 18, gy - 18 - bob, gx + 18, gy + 18 - bob,
                          outline=mix(VIOLET, BG, 0.4), width=1)
            crystal(c, gx, gy - 4 - bob, 10, VIOLET, "#f3e7ff",
                    rot=self.t * 0.9)

    def draw_brawlers(self, c, ox, oy):
        for b in self.brawlers:
            if not b.alive:
                continue
            x, y = ox + b.x, oy + b.y
            invis = b.status["invis"] > 0
            draw_simple_brawler(
                c, x, y, b.radius, b.aim, b.hero, b.team_color,
                player=b.is_player, flash=b.hit_flash,
                invis=invis, overdrive=b.status["overdrive"] > 0,
                shield=b.status["shield"] > 0,
                spawn_shield=b.spawn_shield > 0, bob=b.bob)
            if invis and not b.is_player:
                continue
            bw = 54
            bx = x - bw / 2
            by = y - 47 + math.sin(b.bob) * 2
            rrect(c, bx - 1, by - 1, bx + bw + 1, by + 8, 4,
                  fill="#03080f", outline="")
            ratio = b.hp / b.max_hp
            col = b.team_color if b.team == 0 else RED
            bar(c, bx, by, bw, 6, ratio, col, back="#1a2030", radius=3)
            name = "ВЫ" if b.is_player else b.name
            ncol = "#ffffff" if b.is_player else (
                b.light if b.team == 0 else "#ffb9c3")
            c.create_text(x, by - 8, text=name,
                          font=(F_UI, 8, "bold"), fill=ncol)
            if b.carried > 0:
                crystal(c, x - 11, by - 23, 6, VIOLET, "#f1e4ff")
                c.create_text(x + 1, by - 23, text=str(b.carried),
                              anchor="w", font=(F_UI, 9, "bold"),
                              fill="#e8d9ff")
            if b.super >= 100 and not invis:
                c.create_text(x, by - 36, text="★", font=(F_UI, 11, "bold"),
                              fill=GOLD)
            if b.status["boost"] > 0:
                c.create_line(x - 26, y + 8, x - 38, y + 8,
                              fill=mix(b.light, BG, 0.3), width=2)
                c.create_line(x - 26, y + 15, x - 42, y + 15,
                              fill=mix(b.light, BG, 0.5), width=1)

    def draw_projectiles(self, c, ox, oy):
        for p in self.projectiles:
            for i, (tx, ty) in enumerate(p.trail):
                t = i / max(1, len(p.trail))
                rad = max(1.0, p.radius * (0.3 + t * 0.35))
                col = mix(p.color, BG, 0.55 - t * 0.35)
                c.create_oval(ox + tx - rad, oy + ty - rad,
                              ox + tx + rad, oy + ty + rad,
                              fill=col, outline="")
            gx, gy = ox + p.x, oy + p.y
            r = p.radius
            c.create_oval(gx - r * 2.4, gy - r * 2.4, gx + r * 2.4,
                          gy + r * 2.4, outline=mix(p.color, BG, 0.55),
                          width=1)
            c.create_oval(gx - r, gy - r, gx + r, gy + r,
                          fill=p.color, outline=p.light)
            c.create_oval(gx - r * 0.4, gy - r * 0.4, gx + r * 0.4,
                          gy + r * 0.4, fill="#ffffff", outline="")
        for lob in self.lobs:
            sx, sy = ox + lob.sx, oy + lob.sy
            tx, ty = ox + lob.tx, oy + lob.ty
            c.create_line(sx, sy, tx, ty, fill=mix(lob.color, BG, 0.72),
                          dash=(3, 8))
            c.create_oval(tx - lob.splash, ty - lob.splash,
                          tx + lob.splash, ty + lob.splash,
                          outline=mix(lob.color, BG, 0.35), width=1,
                          dash=(4, 6))
            c.create_oval(ox + lob.x - 10, oy + lob.y - 3,
                          ox + lob.x + 10, oy + lob.y + 5,
                          fill="#050a12", outline="")
            gx = ox + lob.x
            gy = oy + lob.y - lob.z
            c.create_oval(gx - 8, gy - 8, gx + 8, gy + 8,
                          fill=lob.color, outline=lob.light, width=2)
            c.create_oval(gx - 3, gy - 3, gx + 3, gy + 3,
                          fill="#ffffff", outline="")
        for boom in self.booms:
            gx, gy = ox + boom.x, oy + boom.y
            pulse = 0.5 + 0.5 * math.sin(boom.t * 22)
            c.create_oval(gx - boom.radius, gy - boom.radius,
                          gx + boom.radius, gy + boom.radius,
                          outline=mix(boom.color, BG, 0.15 + pulse * 0.35),
                          width=2, dash=(4, 6))
            c.create_line(gx - 7, gy, gx + 7, gy, fill=boom.color)
            c.create_line(gx, gy - 7, gx, gy + 7, fill=boom.color)

    def draw_effects(self, c, ox, oy):
        for beam in self.beams:
            t = beam.life / beam.max_life
            width = max(1, int(beam.width * (0.4 + t * 0.8)))
            col = mix(beam.color, BG, 1.0 - t)
            c.create_line(ox + beam.x1, oy + beam.y1,
                          ox + beam.x2, oy + beam.y2,
                          fill=col, width=width, capstyle="round")
            c.create_line(ox + beam.x1, oy + beam.y1,
                          ox + beam.x2, oy + beam.y2,
                          fill="#ffffff" if t > 0.5 else col,
                          width=max(1, width // 4), capstyle="round")
        for ring in self.rings:
            t = 1.0 - ring.life / ring.max_life
            r = lerp(ring.r0, ring.r1, t)
            col = mix(ring.color, BG, 0.15 + t * 0.75)
            c.create_oval(ox + ring.x - r, oy + ring.y - r,
                          ox + ring.x + r, oy + ring.y + r,
                          outline=col, width=max(1, int(ring.width * (1 - t)) or 1))
        for p in self.particles:
            t = p.life / p.max_life
            col = mix(p.color, BG, 1.0 - t * 0.85)
            sz = max(1.0, p.size * t)
            c.create_oval(ox + p.x - sz, oy + p.y - sz,
                          ox + p.x + sz, oy + p.y + sz,
                          fill=col, outline="")
        for text in self.texts:
            t = text.life / text.max_life
            size = max(8, int(text.size * (0.75 + 0.25 * t)))
            x, y = ox + text.x, oy + text.y
            c.create_text(x + 1, y + 1, text=text.text,
                          font=(F_TITLE, size), fill="#02060c",
                          anchor="center")
            c.create_text(x, y, text=text.text,
                          font=(F_TITLE, size),
                          fill=mix(text.color, BG, (1 - t) * 0.55),
                          anchor="center")

    def draw_aim(self, c, ox, oy):
        p = self.player
        if not p or not p.alive:
            return
        wx = self.app.mouse[0] - AX
        wy = self.app.mouse[1] - AY
        if 0 <= wx <= AW and 0 <= wy <= AH:
            d = dist(p.x, p.y, wx, wy)
            if d > 1:
                ux, uy = (wx - p.x) / d, (wy - p.y) / d
                max_d = p.hero["range"]
                if p.hero["attack_kind"] == "lob":
                    tx = p.x + ux * min(d, max_d)
                    ty = p.y + uy * min(d, max_d)
                    c.create_line(ox + p.x + ux * 24, oy + p.y + uy * 24,
                                  ox + tx, oy + ty,
                                  fill=mix(p.light, BG, 0.45), dash=(3, 7))
                    r = p.hero.get("splash", 100)
                    c.create_oval(ox + tx - r, oy + ty - r,
                                  ox + tx + r, oy + ty + r,
                                  outline=mix(p.light, BG, 0.2),
                                  dash=(4, 5), width=1)
                else:
                    ex = p.x + ux * max_d
                    ey = p.y + uy * max_d
                    c.create_line(ox + p.x + ux * 30, oy + p.y + uy * 30,
                                  ox + ex, oy + ey,
                                  fill=mix(p.light, BG, 0.52),
                                  dash=(2, 8), width=1)
            mx, my = self.app.mouse
            ready = p.super >= 100
            c.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                          outline=GOLD if ready else "#d9f6ff", width=1)
            c.create_oval(mx - 2, my - 2, mx + 2, my + 2,
                          fill=GOLD if ready else "#ffffff", outline="")

    def draw_intro(self, c):
        num = max(1, int(math.ceil(self.intro)))
        overlay = "#040912"
        c.create_rectangle(0, 250, VW, 570, fill=overlay, stipple="gray50",
                           outline="")
        text_glow(c, VW / 2, 320, MODES[self.mode]["name"],
                  (F_TITLE, 24), MUTED, off=2)
        text_glow(c, VW / 2, 415, str(num), (F_TITLE, 112), CYAN,
                  glow="#0e4b5c", off=4)
        c.create_text(VW / 2, 490, text="ПРИГОТОВЬСЯ",
                      font=(F_UI, 13, "bold"), fill=TEXT)
        c.create_text(VW / 2, 518, text=MODES[self.mode]["rule"],
                      font=(F_UI, 10), fill=MUTED)

    def draw_finish(self, c):
        names = {"win": ("ПОБЕДА", CYAN), "lose": ("ПОРАЖЕНИЕ", RED),
                 "draw": ("НИЧЬЯ", GOLD)}
        label, col = names.get(self.result, ("ПОБЕДА", CYAN))
        c.create_rectangle(0, 270, VW, 550, fill="#03070e", stipple="gray50",
                           outline="")
        text_glow(c, VW / 2, 360, label, (F_TITLE, 64), col, off=4)
        c.create_text(VW / 2, 420, text=self.reason,
                      font=(F_UI, 13, "bold"), fill=MUTED)
        if self.mode == "skirmish":
            score = "%d : %d" % (self.team_kills[0], self.team_kills[1])
        else:
            score = "%d : %d" % (self.team_gems(0), self.team_gems(1))
        c.create_text(VW / 2, 470, text=score,
                      font=(F_MONO, 30, "bold"), fill=TEXT)

    def draw_hud(self, c):
        # ---- верхняя панель
        c.create_rectangle(0, 90, VW, 96, fill="#08192b", outline="")
        c.create_polygon(hex_points(43, 38, 18), fill="#0a1a2d",
                         outline=CYAN, width=2)
        c.create_text(43, 38, text=MODES[self.mode]["icon"],
                      font=(F_TITLE, 16), fill=CYAN)
        c.create_text(70, 20, text="NEON BRAWL", anchor="w",
                      font=(F_TITLE, 16), fill=TEXT)
        c.create_text(70, 42, text=MODES[self.mode]["name"], anchor="w",
                      font=(F_UI, 11, "bold"), fill=CYAN)
        c.create_text(70, 62, text=MODES[self.mode]["rule"], anchor="w",
                      font=(F_UI, 9), fill=MUTED)
        c.create_text(70, 79, text="СЛОЖНОСТЬ: " + self.difficulty.upper(),
                      anchor="w", font=(F_UI, 8), fill=DIM)

        # счёт команд
        for team, x1, x2 in ((0, 438, 574), (1, 706, 842)):
            info = TEAM_COLORS[team]
            rrect(c, x1, 12, x2, 86, 10, fill=mix(BG, info["main"], 0.10),
                  outline=info["main"], width=2)
            c.create_text((x1 + x2) / 2, 23,
                          text="ВЫ" if team == 0 else "ВРАГИ",
                          font=(F_UI, 9, "bold"), fill=info["light"])
            c.create_text((x1 + x2) / 2, 48, text=str(self.score(team)),
                          font=(F_TITLE, 28), fill=TEXT)
            label = ("УБИЙСТВА" if self.mode == "skirmish"
                     else "КРИСТАЛЛЫ")
            c.create_text((x1 + x2) / 2, 70, text=label,
                          font=(F_UI, 8, "bold"), fill=MUTED)
            if self.mode == "gems":
                hold = self.hold[team]
                bar(c, x1 + 10, 77, x2 - x1 - 20, 4, hold / 15.0,
                    info["main"], back="#0a1524", radius=2)

        # таймер
        urgent = self.time_left <= 30
        tcol = RED if urgent and int(self.t * 3) % 2 == 0 else TEXT
        rrect(c, 584, 12, 696, 86, 10, fill=PANEL2, outline=LINE, width=1)
        c.create_text(640, 23, text="ТАЙМЕР", font=(F_UI, 8, "bold"),
                      fill=MUTED)
        c.create_text(640, 49, text=fmt_time(self.time_left),
                      font=(F_MONO, 24, "bold"), fill=tcol)
        c.create_text(640, 72, text=MODES[self.mode]["rule"],
                      font=(F_UI, 7, "bold"), fill=DIM)
        if self.mode == "gems" and max(self.hold.values()) > 0:
            team = 0 if self.hold[0] >= self.hold[1] else 1
            left = max(0.0, 15.0 - self.hold[team])
            c.create_text(640, 88, text="%s: %.1fс" %
                          (TEAM_COLORS[team]["name"], left),
                          font=(F_UI, 8, "bold"), fill=TEAM_COLORS[team]["light"])

        # правый блок
        c.create_text(VW - 24, 24, text="3 × 3 · АРЕНА", anchor="e",
                      font=(F_UI, 9, "bold"), fill=MUTED)
        c.create_text(VW - 24, 44, text="КУБКИ: %d" % self.app.save.total_trophies(),
                      anchor="e", font=(F_UI, 9), fill=GOLD)
        c.create_text(VW - 24, 63, text="УБИЙСТВ: %d  ·  СМЕРТЕЙ: %d" %
                      (self.player.kills, self.player.deaths),
                      anchor="e", font=(F_UI, 9), fill=DIM)
        c.create_text(VW - 24, 81, text="ESC — ПАУЗА",
                      anchor="e", font=(F_UI, 8), fill=DIM)

        # ---- панель игрока
        p = self.player
        rrect(c, 24, 682, 434, 790, 14, fill=PANEL, outline=LINE, width=1)
        draw_hero_icon(c, 64, 724, 27, p.hero)
        c.create_text(100, 700, text=p.hero["name"], anchor="w",
                      font=(F_TITLE, 16), fill=TEXT)
        c.create_text(100, 720, text=p.hero["role"], anchor="w",
                      font=(F_UI, 8, "bold"), fill=mix(p.color, TEXT, 0.25))
        hp_ratio = max(0.0, p.hp / p.max_hp)
        hpc = GREEN if hp_ratio > 0.55 else GOLD if hp_ratio > 0.3 else RED
        bar(c, 100, 730, 290, 13, hp_ratio, hpc, back="#101b2b", radius=6)
        c.create_text(382, 736, text="%d / %d" % (max(0, int(p.hp)), p.max_hp),
                      anchor="e", font=(F_UI, 8, "bold"), fill=TEXT)
        super_ratio = p.super / 100.0
        bar(c, 100, 750, 200, 8, super_ratio,
            GOLD if p.super >= 100 else p.color, back="#101b2b", radius=4)
        c.create_text(306, 754,
                      text="ГОТОВ" if p.super >= 100 else "%d%%" % int(p.super),
                      anchor="w", font=(F_UI, 8, "bold"),
                      fill=GOLD if p.super >= 100 else MUTED)
        # патроны
        c.create_text(100, 775, text="ЗАРЯД", anchor="w",
                      font=(F_UI, 7, "bold"), fill=DIM)
        for i in range(p.hero["ammo"]):
            px = 140 + i * 15
            col = p.color if i < p.ammo else "#132033"
            rrect(c, px, 768, px + 11, 781, 3, fill=col, outline="")
        # гаджет
        rrect(c, 340, 744, 422, 784, 8, fill=PANEL2,
              outline=p.color if p.gadget > 0 else LINE, width=1)
        c.create_text(352, 757, text="E", font=(F_UI, 9, "bold"), fill=TEXT)
        c.create_text(366, 756, text="ГАДЖЕТ", anchor="w",
                      font=(F_UI, 7, "bold"), fill=MUTED)
        for i in range(p.gadget):
            c.create_oval(356 + i * 14, 773, 362 + i * 14, 779,
                          fill=p.light, outline="")

        # подсказки управления
        rrect(c, 818, 754, VW - 20, 790, 8, fill=PANEL, outline=LINE)
        c.create_text(828, 763, anchor="w", font=(F_UI, 8), fill=MUTED,
                      text="WASD — движение   ЛКМ — огонь   ПКМ / SPACE — супер")
        c.create_text(828, 779, anchor="w", font=(F_UI, 8), fill=MUTED,
                      text="E — гаджет   ESC — пауза   M — звук")

        # возрождение
        if not p.alive:
            rrect(c, 486, 690, 794, 758, 12, fill="#0a0f1c",
                  outline=RED, width=2)
            c.create_text(640, 708, text="ВОЗРОЖДЕНИЕ",
                          font=(F_UI, 9, "bold"), fill=MUTED)
            c.create_text(640, 736, text="%.1f" % max(0.0, p.respawn),
                          font=(F_MONO, 24, "bold"), fill=RED)
            bar(c, 520, 748, 240, 4,
                max(0.0, 1.0 - p.respawn / 4.2), RED,
                back="#1c0b12", radius=2)

        # рамка урона / низкое здоровье
        border_col = None
        if self.flash > 0:
            border_col = mix(BG, RED, min(0.85, self.flash))
        elif hp_ratio < 0.3 and p.alive:
            border_col = mix(BG, "#ff2448", 0.35 + 0.2 * math.sin(self.t * 6))
        if border_col:
            for i in range(3):
                c.create_rectangle(AX - 3 - i, AY - 3 - i,
                                   AX + AW + 3 + i, AY + AH + 3 + i,
                                   outline=border_col, width=2)

        # готовность супера — подсказка
        if p.super >= 100 and p.alive:
            pulse = 0.5 + 0.5 * math.sin(self.t * 5)
            c.create_text(640, 670, text="СУПЕР ГОТОВ · ПКМ / SPACE",
                          font=(F_UI, 9, "bold"),
                          fill=mix(GOLD, BG, 0.15 + pulse * 0.2))

    def draw_feed(self, c):
        for i, entry in enumerate(self.feed):
            y = 108 + i * 25
            x1, x2 = VW - 310, VW - 22
            rrect(c, x1, y, x2, y + 21, 8, fill="#070f1c",
                  outline=mix(LINE, BG, 0.15))
            if entry["killer"]:
                c.create_text(x1 + 10, y + 10, text=entry["killer"],
                              anchor="w", font=(F_UI, 9, "bold"),
                              fill=entry["kcolor"])
                c.create_text((x1 + x2) / 2, y + 10, text="×",
                              font=(F_UI, 9, "bold"), fill=MUTED)
                c.create_text(x2 - 9, y + 10, text=entry["victim"],
                              anchor="e", font=(F_UI, 9, "bold"),
                              fill=entry["vcolor"])
            else:
                c.create_text((x1 + x2) / 2, y + 10,
                              text=entry["victim"], font=(F_UI, 9, "bold"),
                              fill=entry["vcolor"])




