"""Adventure map: scrolling tile view, fog of war, hero movement, map interactions,
the enemy's turn, minimap, level-up popup and saving."""
import pygame

import main
from config import (SW, SH, TILE_SIZE, HUD_H, MAP_BOTTOM, MAP_VIEW_H, RESOURCES, RES_COLORS,
                    C_BG0, C_BG1, C_BG2, C_BDR, C_GOLD, C_TXT, C_SUB, C_HINT, C_GRN, C_RED,
                    C_BLUE, C_PURP)
from art.ui_art import Button, blit, blit_wrap, panel, hp_bar, draw_tooltip, request_hand
from art import terrain_art, creature_art, hero_art
from art.minimap import Minimap
from engine import world, save_load, sound_engine, skills as SK
from engine.ai_player import AIPlayer
from engine.creature import unit_name
from engine.map_objects import Mine, ArtifactObj, ResourcePile, NeutralStack, Dwelling, Obelisk
from scenes.scene_manager import SM

TS = TILE_SIZE
MOVE_SPEED = 5.0          # tiles per second while walking (Prompt 5 suggested 3.0)
AI_STEP_TIME = 0.16       # seconds per visible enemy step
SCROLL_SPEED = 14         # tiles per second (keys / screen edge)
CAMERA_EASE = 8.0         # how fast the camera glides to its target
EDGE_SCROLL = 6           # px from screen edge that scrolls the camera
SLOT_W, SLOT_X0 = 118, 420
PORTRAIT = pygame.Rect(14, MAP_BOTTOM + 12, 96, 96)


def _tile_variant(x, y):
    return (x * 7 + y * 13 + (x * y) % 5) % 4


def lerp(a, b, f):
    return a + (b - a) * f


class HeroMoveAnimation:
    """Smooth tile-to-tile walking. The scene decides each step (cost, interaction) via
    can_step(); update() returns the tile just reached so the scene can apply it."""

    def __init__(self, hero, path, speed=MOVE_SPEED):
        self.hero, self.path = hero, list(path)
        self.current_step = 0
        self.progress = 0.0
        self.speed = speed
        self.start = hero.pos
        self.stepping = False      # a step has been approved and is animating
        self.done = False

    @property
    def next_tile(self):
        return self.path[self.current_step] if self.current_step < len(self.path) else None

    def update(self, dt):
        if not self.stepping:
            return None
        self.progress += dt * self.speed
        if self.progress < 1.0:
            return None
        reached = self.path[self.current_step]
        self.current_step += 1
        self.progress = 0.0
        self.stepping = False
        if self.current_step >= len(self.path):
            self.done = True
        return reached

    def draw_pos(self):
        """Tile-space position (fractional while between tiles)."""
        if not self.stepping or self.current_step >= len(self.path):
            return self.hero.pos
        a = self.path[self.current_step - 1] if self.current_step else self.start
        b = self.path[self.current_step]
        return lerp(a[0], b[0], self.progress), lerp(a[1], b[1], self.progress)


class AdventureMap:
    def __init__(self):
        self.t = 0.0
        self.cam_x = self.cam_y = 0.0
        self.cam_tx = self.cam_ty = 0.0     # camera glides toward this target
        self.hover = None
        self.preview = []                   # faded path under the mouse: [(pos, reachable)]
        self.planned = None                 # (goal, [(pos, reachable)]) awaiting a 2nd click
        self.walk = None                    # HeroMoveAnimation
        self.toasts = []                    # [[text, time_left, color]]
        self.popup = None                   # creature stack shown in the stats popup
        self.info = None                    # right-click info text
        self.btn_end = self.btn_next = None
        self.ai_gen = None                  # running enemy turn (AIPlayer.run_turn generator)
        self.ai_wait = 0.0
        self.ai_anim = None                 # visible enemy step being animated
        self.res_last = None                # resources last frame, for HUD "+1000" flashes
        self.res_flash = []
        self.res_x = {}
        self.lvl_buttons = []
        self.lvl_sound_for = None
        self.minimap = Minimap((SW - 172, MAP_BOTTOM - 132, 160, 120))
        self._terrain = self._terrain_key = None
        self._fog = self._fog_key = None
        self.town_cycle = 0

    # ─────────────────────────── helpers ───────────────────────────
    @property
    def S(self):
        return main.STATE

    def hero(self):
        hs = self.S["player_heroes"]
        i = self.S.get("selected_hero_idx", -1)
        return hs[i] if 0 <= i < len(hs) else None

    def busy(self):
        return self.walk is not None or self.ai_gen is not None

    def toast(self, text, color=C_TXT, secs=3.0):
        self.toasts.append([text, secs, color])
        self.toasts = self.toasts[-4:]

    def tile_at_screen(self, mx, my):
        if not (HUD_H <= my < MAP_BOTTOM) or self.minimap.rect.collidepoint(mx, my):
            return None
        tx = int(mx / TS + self.cam_x)
        ty = int((my - HUD_H) / TS + self.cam_y)
        return (tx, ty) if self.S["tile_map"].in_bounds(tx, ty) else None

    def tile_to_screen(self, x, y):
        return (x - self.cam_x) * TS, (y - self.cam_y) * TS + HUD_H

    def _clamp(self, x, y):
        tm = self.S["tile_map"]
        return max(0.0, min(x, tm.w - SW / TS)), max(0.0, min(y, tm.h - MAP_VIEW_H / TS))

    def center_on(self, pos, instant=False):
        self.cam_tx, self.cam_ty = self._clamp(pos[0] + 0.5 - SW / TS / 2, pos[1] + 0.5 - MAP_VIEW_H / TS / 2)
        if instant:
            self.cam_x, self.cam_y = self.cam_tx, self.cam_ty

    def follow(self, pos, margin=3):
        """Glide the camera so pos stays at least `margin` tiles from the view edge."""
        vw, vh = SW / TS, MAP_VIEW_H / TS
        tx, ty = self.cam_tx, self.cam_ty
        if pos[0] < tx + margin:
            tx = pos[0] - margin
        elif pos[0] + 1 > tx + vw - margin:
            tx = pos[0] + 1 - vw + margin
        if pos[1] < ty + margin:
            ty = pos[1] - margin
        elif pos[1] + 1 > ty + vh - margin:
            ty = pos[1] + 1 - vh + margin
        self.cam_tx, self.cam_ty = self._clamp(tx, ty)

    # ─────────────────────────── scene interface ───────────────────────────
    def on_enter(self, **kw):
        F = main.F
        self.btn_end = Button((SW - 160, 9, 148, 38), "END TURN", F["md"], (60, 45, 20),
                              hov=(95, 70, 25), tc=C_GOLD, bdr=C_GOLD)
        self.btn_next = Button((292, MAP_BOTTOM + 10, 112, 26), "NEXT HERO", F["ti"])
        self.walk, self.planned, self.popup, self.info = None, None, None, None
        self.preview = []
        if kw.get("new_game"):
            self.toasts, self.ai_gen, self.ai_anim, self.res_last = [], None, None, None
            h = self.hero()
            if h:
                self.center_on(h.pos, instant=True)
            if not kw.get("loaded"):
                self.toast("Day 1 — explore the land, claim mines, conquer the enemy!", C_GOLD, 4)
        for msg in kw.get("messages", []):
            self.toast(msg)
        world.update_fog(self.S)
        self.check_game_over()

    def check_game_over(self):
        result = world.check_victory(self.S)
        if result:
            self.ai_gen = None
            self.S["game_phase"] = "victory" if result == "player" else "defeat"
            SM.go("end_screen", result=self.S["game_phase"])
            return True
        return False

    def update(self, dt):
        self.t += dt
        for tst in self.toasts:
            tst[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        self.update_res_flash(dt)
        mx, my = pygame.mouse.get_pos()
        self.btn_end.enabled = self.ai_gen is None
        self.btn_next.enabled = self.ai_gen is None and len(self.S["player_heroes"]) > 0
        for b in [self.btn_end, self.btn_next] + self.lvl_buttons:
            b.update(mx, my)
        if self.minimap.rect.collidepoint(mx, my) or (PORTRAIT.collidepoint(mx, my) and self.hero()):
            request_hand()
        if self.ai_gen is not None:
            self.step_ai(dt)
        # manual scroll: WASD / arrows / screen edge (moves the target too)
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_META):
            dx = dy = 0          # Ctrl+S saves, it shouldn't also scroll
        if pygame.mouse.get_focused():
            if mx < EDGE_SCROLL: dx = -1
            elif mx > SW - EDGE_SCROLL: dx = 1
            if my < EDGE_SCROLL: dy = -1
            elif my > SH - EDGE_SCROLL: dy = 1
        if dx or dy:
            self.cam_tx, self.cam_ty = self._clamp(self.cam_x + dx * SCROLL_SPEED * dt,
                                                   self.cam_y + dy * SCROLL_SPEED * dt)
            self.cam_x, self.cam_y = self.cam_tx, self.cam_ty
        else:
            f = min(1.0, dt * CAMERA_EASE)
            self.cam_x = lerp(self.cam_x, self.cam_tx, f)
            self.cam_y = lerp(self.cam_y, self.cam_ty, f)
        # hover + faded path preview
        hov = self.tile_at_screen(mx, my) if not (self.popup or self.info) else None
        if hov != self.hover:
            self.hover = hov
            self.update_preview()
        if self.walk:
            self.update_walk(dt)
        if self.ai_anim:
            self.ai_anim["t"] += dt

    # ─────────────────────────── movement ───────────────────────────
    def blocked_tiles(self, mover):
        tm = self.S["tile_map"]
        blocked = {h.pos for h in self.S["player_heroes"] + self.S["enemy_heroes"] if h is not mover}
        blocked |= {(x, y) for y in range(tm.h) for x in range(tm.w) if not tm.get(x, y).is_explored}
        return blocked

    def plan_path(self, goal):
        """[(pos, reachable_today)] from the selected hero to goal, or []."""
        h = self.hero()
        tm = self.S["tile_map"]
        if not h or not goal or goal == h.pos or not tm.get(*goal).is_explored:
            return []
        path = tm.find_path(h.pos, goal, self.blocked_tiles(h))
        pts, left = [], h.movement_points
        for i, p in enumerate(path):
            interact = i == len(path) - 1 and self.is_interaction(p)
            if not interact:
                left -= tm.movement_cost(*p)
            pts.append((p, left >= 0 and (h.movement_points > 0 or not interact)))
        return pts

    def update_preview(self):
        self.preview = [] if self.busy() else self.plan_path(self.hover)

    def is_interaction(self, pos):
        return world.is_interaction(self.S, pos, "player")

    def click_tile(self, pos):
        """First click plans a route (shown solid); clicking the same goal again walks it."""
        h = self.hero()
        if self.planned and self.planned[0] == pos:
            path = [p for p, _ in self.planned[1]]
            self.planned = None
            self.walk = HeroMoveAnimation(h, path)
            self.preview = []
            return
        pts = self.plan_path(pos)
        if not pts:
            self.toast("No path there.", C_SUB, 1.5)
            self.planned = None
            return
        self.planned = (pos, pts)

    def update_walk(self, dt):
        anim, h, tm = self.walk, self.walk.hero, self.S["tile_map"]
        if not anim.stepping:
            nxt = anim.next_tile
            if nxt is None:
                self.walk = None
                return
            last = anim.current_step == len(anim.path) - 1
            if last and self.is_interaction(nxt):
                self.walk = None
                if h.movement_points > 0:
                    self.interact(h, nxt)
                else:
                    self.toast("Not enough movement left today.", C_SUB, 2)
                self.update_preview()
                return
            if world.hero_at(self.S, nxt):
                self.walk = None
                self.toast("Someone is in the way.", C_SUB, 2)
                return
            cost = tm.movement_cost(*nxt)
            if cost is None or cost > h.movement_points:
                self.walk = None
                self.toast("Path blocked." if cost is None else
                           "Out of movement points — end the turn to continue.", C_SUB, 2)
                self.update_preview()
                return
            anim.cost = cost
            anim.stepping = True
        reached = anim.update(dt)
        if reached is None:
            return
        h.spend_movement(anim.cost)
        h.pos = reached
        sound_engine.play("move")
        world.sync_hero_in_town(self.S, h)
        world.update_fog(self.S)       # once per step, not per frame
        self.follow(reached)
        if tm.get(*reached).object_type == "town":
            self.walk = None
            self.enter_town(h, tm.get(*reached).object_data)
        elif anim.done:
            self.walk = None
        if not self.walk:
            self.update_preview()

    def hero_draw_pos(self, h):
        if self.walk and self.walk.hero is h:
            return self.walk.draw_pos()
        a = self.ai_anim
        if a and a["hero"] is h and a["t"] < a["dur"]:
            f = a["t"] / a["dur"]
            return lerp(a["from"][0], a["to"][0], f), lerp(a["from"][1], a["to"][1], f)
        return h.pos

    # ─────────────────────────── interactions ───────────────────────────
    def enter_town(self, hero, town):
        old = town.owner
        if world.capture_town(self.S, town, "player"):
            self.toast(f"{town.name} captured{' from the enemy' if old == 'enemy' else ''}!", C_GRN)
            if self.check_game_over():
                return
        SM.go("town_screen", town=town, hero=hero)

    def interact(self, hero, pos):
        S, tm = self.S, self.S["tile_map"]
        other = world.hero_at(S, pos)
        if other:
            if other.owner == "enemy":
                SM.go("combat_screen", attacker=hero, defender_hero=other)
            else:
                self.toast(f"{other.name} greets {hero.name}.", C_SUB, 2)
            return
        tile = tm.get(*pos)
        obj = tile.object_data
        if tile.object_type == "town":   # enemy/neutral town with a garrison
            SM.go("combat_screen", attacker=hero, defender_town=obj)
        elif isinstance(obj, (Mine, ArtifactObj, ResourcePile, Obelisk)):
            colors = {"gain": C_GRN, "artifact": C_PURP, "info": C_SUB}
            for text, kind in world.visit_object(S, hero, pos):
                self.toast(text, colors.get(kind, C_TXT), 3)
                if kind == "gain":
                    sound_engine.play("gold_pickup")
                elif kind == "artifact":
                    sound_engine.play("spell_cast")
        elif isinstance(obj, NeutralStack):
            SM.go("combat_screen", attacker=hero, defender_stack=obj)
        elif isinstance(obj, Dwelling):
            self.toast(obj.label(), C_SUB, 2)

    def open_next_town(self):
        towns = [t for t in self.S["towns"] if t.owner == "player"]
        if not towns:
            self.toast("You have no towns.", C_SUB, 2)
            return
        town = towns[self.town_cycle % len(towns)]
        self.town_cycle += 1
        visitor = next((h for h in self.S["player_heroes"] if h.pos == town.pos), None)
        SM.go("town_screen", town=town, hero=visitor)

    def save(self):
        if self.busy():
            self.toast("Wait until everyone has stopped moving to save.", C_SUB, 2)
            return
        try:
            save_load.save_game(self.S)
            self.toast("Game Saved", C_GRN, 2)
            sound_engine.play("build")
        except OSError as e:
            self.toast(f"Save failed: {e}", C_RED, 3)

    # ─────────────────────────── enemy turn ───────────────────────────
    def end_turn(self):
        if self.busy() or self.levelup_hero():
            return
        world.begin_enemy_phase(self.S)
        self.ai_gen = AIPlayer(self.S).run_turn()
        self.ai_wait = 0.0
        self.preview, self.planned = [], None

    def step_ai(self, dt):
        """Play the enemy turn: visible moves glide one tile at a time, battles with the
        player open the combat screen (the turn resumes when we come back)."""
        if self.ai_wait > 0:
            self.ai_wait -= dt
            return
        self.ai_anim = None
        tm = self.S["tile_map"]
        for _ in range(500):
            try:
                ev = next(self.ai_gen)
            except StopIteration:
                self.finish_enemy_turn()
                return
            if ev[0] == "step":
                hero, pos = ev[1], ev[2]
                prev = getattr(hero, "_last_seen", None)
                if tm.get(*pos).is_visible:
                    self.follow(pos, margin=4)
                    self.ai_wait = AI_STEP_TIME
                    src = prev if prev and abs(prev[0] - pos[0]) + abs(prev[1] - pos[1]) == 1 else pos
                    self.ai_anim = {"hero": hero, "from": src, "to": pos, "t": 0.0, "dur": AI_STEP_TIME}
                    hero._last_seen = pos
                    return
                hero._last_seen = pos
            elif ev[0] == "msg":
                self.toast(ev[1], C_RED, 3.5)
            elif ev[0] == "combat":
                kw = ev[1]
                target = kw.get("defender_hero") or kw.get("defender_town")
                self.toast(f"{kw['attacker'].name} attacks {target.name}!", C_RED, 3)
                SM.go("combat_screen", **kw)
                return

    def finish_enemy_turn(self):
        self.ai_gen, self.ai_anim = None, None
        for h in self.S["enemy_heroes"]:
            h._last_seen = None
        for msg in world.finish_end_turn(self.S):
            self.toast(msg, C_GOLD, 3.5)
        S = self.S
        self.toast(f"Day {S['day']}, Week {S['week']}, Month {S['month']}", C_TXT, 2)
        if self.check_game_over():
            return
        h = self.hero()
        if h:
            self.follow(h.pos)
        self.update_preview()

    # ─────────────────────────── level-up popup ───────────────────────────
    def levelup_hero(self):
        return next((h for h in self.S["player_heroes"] if h.levelup_queue), None)

    def build_levelup_buttons(self, hero):
        F = main.F
        rec = hero.levelup_queue[0]
        self.lvl_buttons = []
        for i, name in enumerate(rec["options"]):
            b = Button((SW // 2 - 250, SH // 2 - 30 + i * 62, 500, 54), "", F["sm"], C_BG2)
            b.skill, b.level = name, hero.skills.get(name, 0) + 1
            self.lvl_buttons.append(b)
        if not rec["options"]:
            b = Button((SW // 2 - 80, SH // 2 + 60, 160, 44), "OK", F["md"], C_BG2)
            b.skill = None
            self.lvl_buttons.append(b)
        if self.lvl_sound_for is not rec:
            self.lvl_sound_for = rec
            sound_engine.play("level_up")

    def choose_levelup(self, hero, skill):
        if skill:
            hero.learn_skill(skill)
            self.toast(f"{hero.name} learned {SK.LEVEL_NAMES[hero.skills[skill]]} {skill}.", C_PURP)
        hero.levelup_queue.pop(0)
        self.lvl_buttons = []
        world.update_fog(self.S)

    # ─────────────────────────── resource flashes ───────────────────────────
    def update_res_flash(self, dt):
        res = self.S["player_resources"]
        if self.res_last is not None:
            for r in RESOURCES:
                d = res.get(r, 0) - self.res_last.get(r, 0)
                if d and r in self.res_x:
                    self.res_flash.append([f"{d:+,}", self.res_x[r], 1.6, C_GRN if d > 0 else C_RED])
        self.res_last = dict(res)
        for f in self.res_flash:
            f[2] -= dt
        self.res_flash = [f for f in self.res_flash if f[2] > 0]

    # ─────────────────────────── input ───────────────────────────
    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 3:
            self.info = None
            return
        if self.ai_gen is not None:
            return   # enemy turn in progress
        lh = self.levelup_hero()
        if lh:
            if not self.lvl_buttons:
                self.build_levelup_buttons(lh)
            for b in self.lvl_buttons:
                if b.clicked(ev):
                    self.choose_levelup(lh, b.skill)
                    return
            return
        if ev.type == pygame.KEYDOWN:
            self.handle_key(ev)
            return
        if ev.type != pygame.MOUSEBUTTONDOWN:
            return
        if self.popup:
            self.popup = None
            return
        if ev.button == 3:
            self.info = self.info_text(self.tile_at_screen(*ev.pos), ev.pos)
            return
        if self.btn_end.clicked(ev):
            self.end_turn()
            return
        if self.btn_next.clicked(ev):
            self.cycle_hero()
            return
        if ev.button != 1 or self.walk:
            return
        mx, my = ev.pos
        mm = self.minimap.tile_at(ev.pos, self.S["tile_map"])
        if mm:
            self.center_on(mm)
            return
        if my >= MAP_BOTTOM:
            self.click_panel(mx, my)
            return
        pos = self.tile_at_screen(mx, my)
        if not pos:
            return
        heroes = self.S["player_heroes"]
        for i, h in enumerate(heroes):
            if h.pos == pos:
                if self.hero() is h and world.town_at(self.S, pos):
                    self.enter_town(h, world.town_at(self.S, pos))   # click own hero in town: open it
                    return
                self.S["selected_hero_idx"] = i
                self.planned = None
                self.update_preview()
                return
        h = self.hero()
        if h is None:
            if heroes:   # select the nearest hero to the click
                i = min(range(len(heroes)), key=lambda i: abs(heroes[i].pos[0] - pos[0]) + abs(heroes[i].pos[1] - pos[1]))
                self.S["selected_hero_idx"] = i
                self.update_preview()
            return
        if not self.S["tile_map"].get(*pos).is_explored:
            return
        self.click_tile(pos)

    def handle_key(self, ev):
        ctrl = ev.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
        if ev.key == pygame.K_s and ctrl:
            self.save()
        elif ev.key == pygame.K_h and self.hero():
            SM.go("hero_screen", hero=self.hero())
        elif ev.key == pygame.K_t:
            self.open_next_town()
        elif ev.key == pygame.K_ESCAPE:
            if self.popup or self.planned:
                self.popup, self.planned = None, None
            else:
                SM.go("main_menu")
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.end_turn()
        elif ev.key == pygame.K_SPACE and self.hero():
            self.center_on(self.hero().pos)
        elif ev.key == pygame.K_TAB:
            self.cycle_hero()

    def cycle_hero(self):
        """Next hero that can still move (any hero if all are exhausted)."""
        hs = self.S["player_heroes"]
        if not hs:
            return
        cur = self.S.get("selected_hero_idx", -1)
        order = [(cur + k) % len(hs) for k in range(1, len(hs) + 1)]
        i = next((j for j in order if hs[j].movement_points > 0), order[0])
        self.S["selected_hero_idx"] = i
        self.planned = None
        self.center_on(hs[i].pos)
        self.update_preview()

    def click_panel(self, mx, my):
        h = self.hero()
        if not h or not (MAP_BOTTOM + 10 <= my <= SH - 10):
            return
        if PORTRAIT.collidepoint(mx, my):
            SM.go("hero_screen", hero=h)
            return
        i = (mx - SLOT_X0) // SLOT_W
        if mx >= SLOT_X0 and 0 <= i < 7 and h.army[i]:
            self.popup = h.army[i]

    def info_text(self, pos, mouse):
        """Right-click information about whatever is on a tile."""
        if not pos:
            return None
        S, tm = self.S, self.S["tile_map"]
        tile = tm.get(*pos)
        if not tile.is_explored:
            return ("Unexplored land.", mouse)
        h = world.hero_at(S, pos)
        obj = tile.object_data
        if h and (h.owner == "player" or tile.is_visible):
            army = ", ".join(f"{s.count} {unit_name(s.creature, s.count)}" for s in h.stacks())
            text = f"{h.name}, level {h.level} {h.faction.title()} {h.hero_class} ({h.owner})."
            text += f" Army: {army}." if h.owner == "player" else f" Army strength about {h.army_power():,}."
            return (text, mouse)
        if tile.object_type == "town":
            gar = ", ".join(f"{s.count} {unit_name(s.creature, s.count)}" for s in obj.garrison_stacks()) or "none"
            text = f"{obj.name} — {obj.faction.title()} town owned by {obj.owner}. Garrison: {gar}."
            if obj.owner == "player":
                text += f" Income {obj.income_per_day():,} gold/day. (Press T to open your towns.)"
            return (text, mouse)
        if isinstance(obj, NeutralStack):
            return (f"{obj.label()}. " + creature_art.creature_tooltip(obj.creature_key), mouse)
        if obj is not None:
            return (obj.label(), mouse)
        cost = tm.movement_cost(*pos)
        return (f"{tile.terrain_type.title()}: " + (f"movement cost {cost}." if cost else "impassable."), mouse)

    # ─────────────────────────── drawing ───────────────────────────
    def draw(self, surf):
        self.draw_map(surf)
        self.minimap.draw(surf, self.S["tile_map"], self.S["player_heroes"] + self.S["enemy_heroes"],
                          self.S["towns"], (self.cam_x, self.cam_y))
        self.draw_hud(surf)
        self.draw_bottom(surf)
        self.draw_toasts(surf)
        if self.ai_gen is not None:
            F = main.F
            r = pygame.Rect(0, 0, 260, 34)
            r.midtop = (SW // 2, MAP_BOTTOM - 46)
            panel(surf, r, (50, 18, 18), C_RED, br=8)
            blit(surf, "Enemy turn" + "." * (1 + int(self.t * 3) % 3), F["md"], C_RED, r.centerx, r.y + 5, "center")
        if self.popup:
            self.draw_popup(surf, self.popup)
        if self.info:
            draw_tooltip(surf, self.info[0], main.F["sm"], self.info[1], w=360, border=C_BLUE)
        lh = self.levelup_hero()
        if lh and self.ai_gen is None:
            if not self.lvl_buttons:
                self.build_levelup_buttons(lh)
            self.draw_levelup(surf, lh)

    def draw_levelup(self, surf, hero):
        F = main.F
        rec = hero.levelup_queue[0]
        shade = pygame.Surface((SW, SH), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surf.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 580, 420)
        box.center = (SW // 2, SH // 2)
        panel(surf, box, C_BG1, C_GOLD, br=14, bw=2)
        hero_art.draw_hero_portrait(surf, (box.x + 24, box.y + 22, 80, 80), hero.faction, None)
        blit(surf, f"LEVEL UP! {hero.name} is now Level {rec['level']}", F["md"], C_GOLD, box.x + 122, box.y + 28)
        blit(surf, f"Primary stat +1: {rec['stat'].title()} is now {rec['value']}", F["sm"], C_GRN, box.x + 122, box.y + 62)
        blit(surf, "Choose a secondary skill:" if rec["options"] else "No skills left to learn.",
             F["sm"], C_TXT, box.x + 24, box.y + 118)
        mx, my = pygame.mouse.get_pos()
        for b in self.lvl_buttons:
            b.update(mx, my)
            if b.skill is None:
                b.label = "OK"
                b.draw(surf)
                continue
            b.draw(surf)
            col = SK.SKILL_COLORS.get(b.skill, C_SUB)
            pygame.draw.circle(surf, col, (b.rect.x + 28, b.rect.centery), 14)
            blit(surf, b.skill[0], F["md"], (20, 20, 20), b.rect.x + 28, b.rect.centery - 12, "center")
            blit(surf, f"{SK.LEVEL_NAMES[b.level]} {b.skill}", F["md"], C_TXT, b.rect.x + 54, b.rect.y + 6)
            blit(surf, SK.describe(b.skill, b.level), F["ti"], C_SUB, b.rect.x + 54, b.rect.y + 32)

    def terrain_layer(self):
        """The whole map's static terrain, rendered once per map."""
        tm = self.S["tile_map"]
        if self._terrain_key != id(tm):
            layer = pygame.Surface((tm.w * TS, tm.h * TS))
            for y in range(tm.h):
                for x in range(tm.w):
                    terrain_art.draw_static_tile(layer, (x * TS, y * TS, TS, TS), tm.get(x, y).terrain_type,
                                                 _tile_variant(x, y))
            self._terrain, self._terrain_key = layer, id(tm)
        return self._terrain

    def fog_layer(self):
        """Black for unexplored, translucent grey for explored-but-unseen; rebuilt on fog change."""
        tm = self.S["tile_map"]
        key = (id(tm), tm.fog_version)
        if self._fog_key != key:
            layer = pygame.Surface((tm.w * TS, tm.h * TS), pygame.SRCALPHA)
            for y in range(tm.h):
                for x in range(tm.w):
                    t = tm.get(x, y)
                    if not t.is_explored:
                        layer.fill((4, 5, 8, 255), (x * TS, y * TS, TS, TS))
                    elif not t.is_visible:
                        layer.fill((10, 12, 20, 128), (x * TS, y * TS, TS, TS))
            self._fog, self._fog_key = layer, key
        return self._fog

    def draw_map(self, surf):
        S, tm, t = self.S, self.S["tile_map"], self.t
        view = pygame.Rect(0, HUD_H, SW, MAP_VIEW_H)
        surf.set_clip(view)
        surf.fill(C_BG0, view)
        ox, oy = round(self.cam_x * TS), round(self.cam_y * TS)
        surf.blit(self.terrain_layer(), (0, HUD_H), pygame.Rect(ox, oy, SW, MAP_VIEW_H))
        x0, y0 = int(self.cam_x), int(self.cam_y)
        x1, y1 = min(tm.w, x0 + SW // TS + 2), min(tm.h, y0 + MAP_VIEW_H // TS + 2)
        for ty in range(y0, y1):          # animated water on visible tiles only
            for tx in range(x0, x1):
                tile = tm.get(tx, ty)
                if tile.terrain_type == "water" and tile.is_explored:
                    px, py = self.tile_to_screen(tx, ty)
                    terrain_art.draw_water_waves(surf, (round(px), round(py), TS, TS), t, phase_x=tx * TS)
        objs = [(town.pos, town) for town in S["towns"]] + [(o.pos, o) for o in S["map_objects"]]
        for (ox_, oy_), obj in sorted(objs, key=lambda p: p[0][1]):
            if x0 - 1 <= ox_ < x1 and y0 - 1 <= oy_ < y1 and tm.get(ox_, oy_).is_explored:
                px, py = self.tile_to_screen(ox_, oy_)
                self.draw_object(surf, pygame.Rect(round(px), round(py), TS, TS), obj)
        if self.planned:
            self.draw_path(surf, self.planned[1], faded=False)
        if self.preview and not (self.planned and self.preview[-1][0] == self.planned[0]):
            self.draw_path(surf, self.preview, faded=True)
        sel = self.hero()
        for h in S["player_heroes"] + S["enemy_heroes"]:
            if h.owner != "player" and not tm.get(*h.pos).is_visible:
                continue
            fx, fy = self.hero_draw_pos(h)
            sx, sy = self.tile_to_screen(fx, fy)
            hero_art.draw_hero_on_map(surf, sx + TS / 2, sy + TS / 2 - 4, h.faction, h.owner, t, h is sel)
        surf.blit(self.fog_layer(), (0, HUD_H), pygame.Rect(ox, oy, SW, MAP_VIEW_H))
        if self.hover and tm.get(*self.hover).is_explored:
            px, py = self.tile_to_screen(*self.hover)
            pygame.draw.rect(surf, (255, 255, 255), (round(px), round(py), TS, TS), 1)
        surf.set_clip(None)
        self.draw_tooltip(surf)

    def draw_path(self, surf, pts, faded):
        h = self.hero()
        if not h or not pts:
            return
        layer = pygame.Surface((SW, MAP_VIEW_H), pygame.SRCALPHA)
        alpha = 110 if faded else 255
        prev = self.tile_to_screen(*h.pos)
        prev = (prev[0] + TS / 2, prev[1] + TS / 2 - HUD_H)
        for i, (p, ok) in enumerate(pts):
            sx, sy = self.tile_to_screen(*p)
            cur = (sx + TS / 2, sy + TS / 2 - HUD_H)
            col = (*(C_GRN if ok else C_RED), alpha)
            for k in range(1, 4):
                f = k / 4
                pygame.draw.circle(layer, col, (int(lerp(prev[0], cur[0], f)), int(lerp(prev[1], cur[1], f))),
                                   2 if faded else 3)
            if i == len(pts) - 1:
                pygame.draw.circle(layer, col, (int(cur[0]), int(cur[1])), 8, 2)
                pygame.draw.line(layer, col, (cur[0] - 5, cur[1] - 5), (cur[0] + 5, cur[1] + 5), 2)
                pygame.draw.line(layer, col, (cur[0] - 5, cur[1] + 5), (cur[0] + 5, cur[1] - 5), 2)
            prev = cur
        surf.blit(layer, (0, HUD_H))

    def draw_object(self, surf, rect, obj):
        t = self.t
        if hasattr(obj, "garrison"):   # Town
            terrain_art.draw_town(surf, rect, obj.faction, obj.owner, t)
        elif isinstance(obj, Mine):
            terrain_art.draw_mine(surf, rect, obj.resource_type, obj.owner)
        elif isinstance(obj, ArtifactObj):
            terrain_art.draw_artifact(surf, rect, t)
        elif isinstance(obj, ResourcePile):
            terrain_art.draw_resource_pile(surf, rect, obj.resource_type)
        elif isinstance(obj, NeutralStack):
            creature_art.draw_creature(surf, rect.centerx, rect.centery, obj.creature_key, t, size=TS, facing=-1)
        elif isinstance(obj, Obelisk):
            terrain_art.draw_obelisk(surf, rect, obj.visited, t)
        elif isinstance(obj, Dwelling):
            terrain_art.draw_mine(surf, rect, "wood")

    def tooltip_text(self):
        if not self.hover:
            return None
        S, tm = self.S, self.S["tile_map"]
        tile = tm.get(*self.hover)
        if not tile.is_explored:
            return None
        h = world.hero_at(S, self.hover)
        if h and (h.owner == "player" or tile.is_visible):
            return f"{h.name} — level {h.level} {h.faction.title()} hero ({h.owner})"
        if tile.object_type == "town":
            t = tile.object_data
            return f"{t.name} — {t.faction.title()} town ({t.owner})"
        obj = tile.object_data
        if isinstance(obj, NeutralStack):
            c = main.CREATURES[obj.creature_key]
            return (f"{obj.label()} · ATK {c['attack']} DEF {c['defense']} DMG {c['damage_min']}-{c['damage_max']}"
                    f" HP {c['hp']} · right-click for details")
        if obj is not None:
            return obj.label()
        cost = tm.movement_cost(*self.hover)
        return f"{tile.terrain_type.title()}" + (f" (move cost {cost})" if cost else " (impassable)")

    def draw_tooltip(self, surf):
        text = self.tooltip_text()
        if self.planned and not self.walk:
            text = (text + " · " if text else "") + "click the flagged tile again to go"
        if not text:
            return
        F = main.F
        w = F["sm"].size(text)[0] + 20
        r = pygame.Rect(10, MAP_BOTTOM - 34, w, 26)
        panel(surf, r, (14, 18, 28), C_BDR, br=6)
        blit(surf, text, F["sm"], C_TXT, r.x + 10, r.y + 4)

    def draw_hud(self, surf):
        S, F = self.S, main.F
        pygame.draw.rect(surf, C_BG1, (0, 0, SW, HUD_H))
        pygame.draw.line(surf, C_BDR, (0, HUD_H - 1), (SW, HUD_H - 1), 2)
        res = S["player_resources"]
        x = 14
        for r in RESOURCES:
            col = RES_COLORS[r]
            pygame.draw.circle(surf, col, (x + 9, 28), 9)
            pygame.draw.circle(surf, (20, 20, 20), (x + 9, 28), 9, 1)
            blit(surf, r.title(), F["ti"], C_HINT, x + 24, 9)
            blit(surf, f"{res.get(r, 0):,}", F["md"], C_TXT, x + 24, 23)
            self.res_x[r] = x + 24
            x += 128 if r == "gold" else 108
        blit(surf, f"Day {S['day']}, Week {S['week']}, Month {S['month']}", F["md"], C_GOLD, SW - 180, 17, "right")
        self.btn_end.draw(surf)
        for text, x, life, col in self.res_flash:
            img = F["sm"].render(text, True, col)
            img.set_alpha(int(255 * min(1.0, life)))
            surf.blit(img, (x, HUD_H + 2 - int((1.6 - life) * 14)))

    def draw_bottom(self, surf):
        F = main.F
        pygame.draw.rect(surf, C_BG1, (0, MAP_BOTTOM, SW, SH - MAP_BOTTOM))
        pygame.draw.line(surf, C_BDR, (0, MAP_BOTTOM), (SW, MAP_BOTTOM), 2)
        h = self.hero()
        if not h:
            blit(surf, "No hero selected — click a hero (or press Tab).", F["md"], C_SUB, 20, MAP_BOTTOM + 45)
            return
        hero_art.draw_hero_portrait(surf, PORTRAIT, h.faction, None, owner=h.owner)
        if h.movement_points <= 0:     # exhausted: grey the portrait
            grey = pygame.Surface(PORTRAIT.size, pygame.SRCALPHA)
            grey.fill((30, 32, 40, 165))
            surf.blit(grey, PORTRAIT)
            blit(surf, "Exhausted", F["ti"], C_TXT, PORTRAIT.centerx, PORTRAIT.bottom - 20, "center")
        x = 124
        blit(surf, h.name, F["lg"], C_GOLD, x, MAP_BOTTOM + 8)
        blit(surf, f"Level {h.level} {h.hero_class}   XP {h.xp}/{h.xp_next}", F["ti"], C_SUB, x, MAP_BOTTOM + 42)
        stats = f"ATK {h.stat('attack')}  DEF {h.stat('defense')}  PWR {h.stat('power')}  KNW {h.stat('knowledge')}"
        blit(surf, stats, F["ti"], C_TXT, x, MAP_BOTTOM + 60)
        blit(surf, f"Army HP {h.army_hp():,}", F["ti"], C_TXT, x, MAP_BOTTOM + 78)
        blit(surf, f"Mana {h.mana}/{h.mana_max}", F["ti"], C_BLUE, x + 140, MAP_BOTTOM + 78)
        blit(surf, f"Move {h.movement_points}/{h.movement_max}", F["ti"], C_TXT, x, MAP_BOTTOM + 96)
        hp_bar(surf, (x + 100, MAP_BOTTOM + 99, 160, 10), h.movement_points, max(1, h.movement_max), C_GRN)
        self.btn_next.draw(surf)
        mx, my = pygame.mouse.get_pos()
        hovered = None
        for i in range(7):
            r = pygame.Rect(SLOT_X0 + i * SLOT_W, MAP_BOTTOM + 10, SLOT_W - 8, SH - MAP_BOTTOM - 20)
            st = h.army[i]
            panel(surf, r, C_BG2 if st else C_BG0, C_BDR, br=8)
            if st:
                creature_art.draw_creature(surf, r.centerx, r.y + 42, st.creature, self.t, size=64)
                blit(surf, st.name, F["ti"], C_SUB, r.centerx, r.bottom - 22, "center")
                badge = F["md"].render(str(st.count), True, C_TXT)
                surf.blit(badge, badge.get_rect(topright=(r.right - 6, r.y + 4)))
                if r.collidepoint(mx, my) and not self.popup:
                    hovered = st
                    request_hand()
        if hovered:
            draw_tooltip(surf, creature_art.creature_tooltip(hovered.creature, hovered.count), F["ti"],
                         (mx, min(my, SH - 120)))

    def draw_toasts(self, surf):
        F = main.F
        y = HUD_H + 10
        for text, left, col in self.toasts:
            img = F["sm"].render(text, True, col)
            img.set_alpha(int(255 * min(1.0, left * 2)))
            r = img.get_rect(midtop=(SW // 2, y)).inflate(24, 10)
            bg = pygame.Surface(r.size, pygame.SRCALPHA)
            bg.fill((10, 12, 20, int(200 * min(1.0, left * 2))))
            surf.blit(bg, r)
            surf.blit(img, img.get_rect(center=r.center))
            y += r.h + 4

    def draw_popup(self, surf, st):
        F = main.F
        d = st.data
        shade = pygame.Surface((SW, SH), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        surf.blit(shade, (0, 0))
        r = pygame.Rect(0, 0, 460, 330)
        r.center = (SW // 2, SH // 2)
        panel(surf, r, C_BG1, C_GOLD, br=12, bw=2)
        creature_art.draw_creature(surf, r.x + 80, r.y + 100, st.creature, self.t, size=110)
        blit(surf, d["name"], F["lg"], C_GOLD, r.x + 160, r.y + 20)
        blit(surf, f"{d['faction'].title()} · Tier {d['tier']} · x{st.count}", F["sm"], C_SUB, r.x + 160, r.y + 56)
        rows = [("Attack", d["attack"]), ("Defense", d["defense"]),
                ("Damage", f"{d['damage_min']}-{d['damage_max']}"), ("Health", f"{st.hp_remaining}/{d['hp']}"),
                ("Speed", d["speed"]), ("Initiative", d["initiative"]),
                ("Cost", f"{d['cost']} gold"), ("Growth", f"{d['weekly_growth']}/week")]
        for i, (k, v) in enumerate(rows):
            y = r.y + 88 + i * 22
            blit(surf, k, F["sm"], C_SUB, r.x + 160, y)
            blit(surf, v, F["sm"], C_TXT, r.right - 24, y, "right")
        tags = (["Ranged"] if d["is_ranged"] else []) + (["Flying"] if d["is_flying"] else []) + \
               [a.replace("_", " ").title() for a in d["abilities"]]
        if tags:
            blit_wrap(surf, " · ".join(tags), F["ti"], C_PURP, r.x + 24, r.bottom - 52, r.w - 48)
        blit(surf, "click anywhere to close", F["ti"], C_HINT, r.centerx, r.bottom - 22, "center")
