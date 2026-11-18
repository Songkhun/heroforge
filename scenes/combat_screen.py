"""Tactical hex-grid battle scene.

Phases: player_move -> (player_attack) -> animating -> next stack;  ai_turn -> animating;
spell_select (hero casting);  victory / defeat (result overlay, then back to the map).
"""
import math
import random

import pygame

import main
from config import (SW, SH, C_BG0, C_BG1, C_BG2, C_BDR, C_GOLD, C_TXT, C_SUB, C_HINT,
                    C_GRN, C_RED, C_BLUE, C_PURP)
from art.ui_art import Button, blit, blit_wrap, panel, hp_bar
from art import creature_art, hero_art
from engine import world
from engine.creature import CreatureStack, unit_name
from engine.combat_engine import (CombatEngine as CE, CombatState, SPELLS, build_side)
from engine import skills as SK
from engine import sound_engine
from art.combat_fx import AttackAnimation, DamageFlash, SpellEffect, StackDeathAnimation, FloatingText
from engine.hex_grid import (GRID_COLS, GRID_ROWS, HEX_W, HEX_H, hex_to_pixel, pixel_to_hex,
                             hex_neighbors, in_grid, draw_hex, get_melee_targets)
from engine.map_objects import NeutralStack
from scenes.scene_manager import SM

TOP_H = 44
GX, GY = 6, 150                   # screen offset of the grid's top-left corner
PANEL_X = 880                     # right panel (grid is 868px wide)
HORIZON = 128
SPRITE = 62
STEP_T = 0.09                     # seconds per hex while walking
FLY_T = 0.35                      # seconds for a flyer's whole hop
ATTACK_T = 1.0
AI_PAUSE = 0.4
SIDE_COL = {"player": C_BLUE, "enemy": C_RED}
# centered start rows for 1..7 stacks
START_ROWS = {1: [5], 2: [3, 7], 3: [1, 5, 9], 4: [1, 3, 7, 9], 5: [1, 3, 5, 7, 9],
              6: [0, 2, 4, 6, 8, 10], 7: [1, 3, 5, 7, 9, 2, 8]}


def hex_center(pos):
    x, y = hex_to_pixel(*pos)
    return x + GX, y + GY


class CombatScreen:
    def __init__(self):
        self.t = 0.0
        self.bg = None
        self.state = None

    # ─────────────────────────── setup ───────────────────────────
    def on_enter(self, attacker=None, attacker_hero=None, defender_hero=None, defender_stack=None,
                 defender_town=None, **kw):
        F = main.F
        hero = attacker or attacker_hero
        self.att_hero, self.def_hero = hero, defender_hero
        self.neutral, self.town = defender_stack, defender_town
        st = CombatState(attacker_hero=hero, defender_hero=defender_hero)
        st.attacker_stacks = build_side(hero.army, "attacker", hero)
        if defender_hero:
            st.defender_stacks = build_side(defender_hero.army, "defender", defender_hero)
            self.def_name = defender_hero.name
        elif defender_stack:
            st.defender_stacks = build_side([CreatureStack(defender_stack.creature_key, defender_stack.count)],
                                            "defender")
            self.def_name = defender_stack.label()
        else:
            st.defender_stacks = build_side(defender_town.garrison, "defender")
            self.def_name = f"{defender_town.name} garrison"
        st.player_side = "attacker" if hero.owner == "player" else "defender"
        CE.setup_positions(st)
        for side in (st.attacker_stacks, st.defender_stacks):
            rows = START_ROWS[len(side)] if side else []
            for s, r in zip(side, rows):
                s.hex_pos = (s.hex_pos[0], r)
        self.state = st
        self.queue, self.anim, self.after_queue = [], None, None
        self.texts, self.flash, self.remains = [], {}, []
        self.fx, self.deaths, self.attack_anim = [], [], None
        self.confirm_retreat = False
        self.reach, self.attackable, self.spell_hexes = set(), set(), set()
        self.hover, self.moved = None, False
        self.ai_timer = 0.0
        self.pending_spell, self.prev_phase = None, None
        self.result = None
        self.result_btn = None
        self.spell_buttons = []
        bx, by, bw, bh = PANEL_X + 14, SH - 104, 186, 40
        self.btn = {
            "wait": Button((bx, by, bw, bh), "WAIT", F["md"]),
            "defend": Button((bx + bw + 8, by, bw, bh), "DEFEND", F["md"]),
            "spell": Button((bx, by + bh + 8, bw, bh), "CAST SPELL", F["md"], (45, 30, 70), tc=(215, 185, 255)),
            "retreat": Button((bx + bw + 8, by + bh + 8, bw, bh), "RETREAT", F["md"], (70, 30, 30), tc=(255, 190, 180)),
        }
        self.btn_cancel = Button((PANEL_X + 14, SH - 152, 380, 36), "Cancel spell", F["sm"])
        self.btn_yes = Button((SW // 2 - 170, SH // 2 + 30, 160, 44), "Retreat", F["md"], (90, 30, 30), tc=(255, 200, 190))
        self.btn_no = Button((SW // 2 + 10, SH // 2 + 30, 160, 44), "Keep fighting", F["sm"])
        self.btn_start = Button((PANEL_X + 24, 520, 360, 42), "START BATTLE", F["md"], (60, 45, 20),
                                hov=(95, 70, 25), tc=C_GOLD, bdr=C_GOLD)
        st.log(f"Battle! {hero.name} vs {self.def_name}")
        self.tactics_cols, self.tactics_sel = set(), None
        cols = SK.skill_value(self.player_hero(), "Tactics")
        if cols:
            rng = range(cols) if st.player_side == "attacker" else range(GRID_COLS - cols, GRID_COLS)
            self.tactics_cols = set(rng)
            st.phase = "tactics"
            st.log(f"Tactics: arrange your troops in the first {cols} columns.")
        else:
            self.start_battle()

    def start_battle(self):
        st = self.state
        self.tactics_cols, self.tactics_sel = set(), None
        st.log("— Round 1 —")
        st.build_turn_order()
        if st.active_stack:
            st.active_stack.is_defending = False
        self.begin_turn()

    def tactics_click(self, pos):
        st = self.state
        s = st.get_stack_at(*pos)
        if s and self.is_player(s):
            self.tactics_sel = None if self.tactics_sel is s else s
        elif self.tactics_sel and not s and pos[0] in self.tactics_cols:
            self.tactics_sel.hex_pos = pos
            self.tactics_sel = None

    # ─────────────────────────── helpers ───────────────────────────
    def is_player(self, stack):
        return stack.side == self.state.player_side

    def side_color(self, stack):
        return SIDE_COL["player" if self.is_player(stack) else "enemy"]

    def hex_at_mouse(self, mx, my):
        if mx >= PANEL_X - 6:
            return None
        pos = pixel_to_hex(mx - GX, my - GY)
        return pos if in_grid(*pos) else None

    def compute_options(self):
        st, s = self.state, self.state.active_stack
        self.reach, self.attackable = set(), set()
        if not s or not self.is_player(s):
            return
        enemy = st.enemy_hexes_of(s)
        if self.moved:
            self.attackable = {e for e in enemy if e in hex_neighbors(*s.hex_pos)}
            return
        self.reach = CE.reachable(st, s)
        if CE.can_shoot(st, s):
            self.attackable = set(enemy)
        else:
            self.attackable = get_melee_targets(*s.hex_pos, self.reach, enemy)

    def stand_hex_for(self, target, mx, my):
        """Where the active stack should stand to melee `target` (nearest to the mouse)."""
        s = self.state.active_stack
        if target.hex_pos in hex_neighbors(*s.hex_pos):
            return None
        options = [h for h in hex_neighbors(*target.hex_pos) if h in self.reach]
        if not options:
            return None
        return min(options, key=lambda h: (hex_center(h)[0] - mx) ** 2 + (hex_center(h)[1] - my) ** 2)

    def say(self, text, pos, color, big=False, dy=-40):
        x, y = hex_center(pos)
        self.texts.append(FloatingText(text, x, y + dy, color, big=big))

    def add_hits(self, hits):
        """Turn engine hit events (stack, damage, killed[, tags]) into floaters, flashes and deaths."""
        for hit in hits:
            stack, dmg, killed = hit[:3]
            tags = hit[3] if len(hit) > 3 else set()
            text = f"-{dmg}" + (f"  ({killed} slain)" if killed else "")
            self.say(text, stack.hex_pos, C_RED if self.is_player(stack) else C_GOLD)
            if "lucky" in tags:
                self.say("LUCKY!", stack.hex_pos, C_GRN, big=True, dy=-64)
            self.flash[id(stack)] = 0.45
            self.fx.append(DamageFlash(stack.hex_pos, GX, GY))
            if not stack.is_alive:
                x, y = hex_center(stack.hex_pos)
                self.deaths.append(StackDeathAnimation(stack.creature_key, x, y - 12,
                                                       1 if stack.side == "attacker" else -1, SPRITE))
                self.remains.append((stack.hex_pos, stack.creature_key))
                sound_engine.play("death")
        return hits

    # ─────────────────────────── turn flow ───────────────────────────
    def begin_turn(self):
        st = self.state
        if self.check_end():
            return
        s = st.active_stack
        self.moved = False
        self.pending_spell = None
        if s is None:
            self.check_end()
            return
        if self.is_player(s):
            st.phase = "player_move"
            self.compute_options()
        else:
            st.phase = "ai_turn"
            self.ai_timer = AI_PAUSE
            self.reach, self.attackable = set(), set()

    def end_stack_turn(self):
        st = self.state
        s = st.active_stack
        if s:
            s.has_acted = True
        if self.check_end():
            return
        if s and CE.roll_morale(st, s):
            self.say("MORALE!", s.hex_pos, C_GRN, big=True, dy=-56)
            self.begin_turn()   # same stack goes again
            return
        st.advance_to_next()
        self.begin_turn()

    def check_end(self):
        st = self.state
        winner = CE.check_victory(st)
        if winner and not self.result:
            self.finish(winner)
            return True
        return bool(self.result)

    def run_queue(self, steps, after):
        self.queue = list(steps)
        self.after_queue = after
        self.anim = None
        self.state.phase = "animating"

    # ── player actions ──
    def player_click_hex(self, pos, mx, my):
        st, s = self.state, self.state.active_stack
        target = st.get_stack_at(*pos)
        if target and target.side != s.side and pos in self.attackable:
            if not self.moved and CE.can_shoot(st, s):
                self.run_queue([{"kind": "attack", "att": s, "tgt": target, "ranged": True}], self.end_stack_turn)
                return
            stand = self.stand_hex_for(target, mx, my)
            steps = []
            if stand:
                steps.append({"kind": "move", "stack": s, "path": CE.path_to(st, s, stand)})
            steps.append({"kind": "attack", "att": s, "tgt": target, "ranged": False})
            self.run_queue(steps, self.end_stack_turn)
        elif pos in self.reach and st.phase == "player_move":
            self.run_queue([{"kind": "move", "stack": s, "path": CE.path_to(st, s, pos)}], self.after_player_move)

    def after_player_move(self):
        st, s = self.state, self.state.active_stack
        if st.enemy_hexes_of(s) & set(hex_neighbors(*s.hex_pos)):
            self.moved = True
            st.phase = "player_attack"
            self.compute_options()
        else:
            self.end_stack_turn()

    def defend(self):
        s = self.state.active_stack
        s.is_defending = True
        self.state.log(f"{s.name} defend.")
        self.end_stack_turn()

    def wait(self):
        s = self.state.active_stack
        self.state.log(f"{s.name} wait.")
        self.state.wait_active()
        self.begin_turn()

    def retreat(self):
        self.state.log(f"{self.att_hero.name if self.state.player_side == 'attacker' else self.def_hero.name} retreats!")
        self.finish("retreat")

    # ── spells ──
    def player_hero(self):
        return self.state.hero_of(self.state.player_side)

    def open_spellbook(self):
        F, hero = main.F, self.player_hero()
        self.prev_phase = self.state.phase
        self.state.phase = "spell_select"
        self.pending_spell, self.spell_hexes = None, set()
        self.spell_buttons = []
        y = 346
        for name in CE.combat_spells(hero):
            sp = SPELLS[name]
            b = Button((PANEL_X + 14, y, 380, 34), f"{name}  ·  {sp['mana_cost']} mana", F["sm"], (40, 30, 62),
                       tc=(225, 205, 255))
            b.enabled = hero.mana >= sp["mana_cost"] and (CE.spell_targets(self.state, self.state.player_side, name) != set())
            b.spell = name
            self.spell_buttons.append(b)
            y += 38

    def choose_spell(self, name):
        targets = CE.spell_targets(self.state, self.state.player_side, name)
        if targets is None:
            self.cast(name, None)
        else:
            self.pending_spell, self.spell_hexes = name, targets

    def cast(self, name, pos):
        side = self.state.player_side
        self.state.phase = "animating"

        def apply():
            return self.add_hits(CE.cast_spell(self.state, side, name, pos))
        self.run_queue([{"kind": "spell", "fn": apply, "name": name, "pos": pos}], self.after_cast)

    def after_cast(self):
        st = self.state
        self.pending_spell, self.spell_hexes = None, set()
        if self.check_end():
            return
        s = st.active_stack
        if s is None or not s.is_alive:
            st.advance_to_next()
            self.begin_turn()
            return
        st.phase = self.prev_phase if self.prev_phase in ("player_move", "player_attack") else "player_move"
        self.compute_options()

    def cancel_spell(self):
        self.pending_spell, self.spell_hexes = None, set()
        self.state.phase = self.prev_phase or "player_move"

    # ── AI ──
    def ai_spell_step(self, side):
        """Enemy hero casts once per round if it can: damage > debuff > buff."""
        st = self.state
        if not CE.can_cast(st, side):
            return None
        hero = st.hero_of(side)
        foes = st.all_alive_attacker if side == "defender" else st.all_alive_defender
        mine = st.stacks_of(side)
        strongest = lambda pool: max(pool, key=lambda s: s.effective_attack * s.count * s.creature["damage_max"])
        order = {"damage": 0, "debuff": 1, "buff": 2}
        for name in sorted(CE.combat_spells(hero), key=lambda n: order.get(SPELLS[n]["effect_type"], 3)):
            sp = SPELLS[name]
            if hero.mana < sp["mana_cost"] or sp["effect_type"] == "special":
                continue
            targets = CE.spell_targets(st, side, name)
            if targets is None:
                continue   # skip all-board spells: the AI would hit its own troops
            pool = [s for s in (mine if sp["effect_type"] == "buff" else foes) if s.hex_pos in targets]
            if not pool:
                continue
            pos = strongest(pool).hex_pos

            def apply(name=name, pos=pos):
                return self.add_hits(CE.cast_spell(st, side, name, pos))
            return {"kind": "spell", "fn": apply, "name": name, "pos": pos}
        return None

    def run_ai(self):
        st, s = self.state, self.state.active_stack
        steps = []
        spell = self.ai_spell_step(s.side)
        if spell:
            steps.append(spell)
        act = CE.ai_action(st, s)
        if act["path"]:
            steps.append({"kind": "move", "stack": s, "path": act["path"]})
        if act["target"]:
            steps.append({"kind": "attack", "att": s, "tgt": act["target"], "ranged": act["ranged"]})
        if act["defend"] and not steps:
            s.is_defending = True
            st.log(f"{s.name} defend.")
        if not steps:
            steps.append({"kind": "pause", "dur": 0.2})
        self.run_queue(steps, self.end_stack_turn)

    # ─────────────────────────── animation ───────────────────────────
    def start_step(self, step):
        step["t"] = 0.0
        k = step["kind"]
        if k == "move":
            path = step["path"]
            if not path:
                step["dur"] = 0
            else:
                step["from"] = step["stack"].hex_pos
                step["dur"] = FLY_T if step["stack"].is_flying else STEP_T * len(path)
        elif k == "attack":
            a, d = step["att"], step["tgt"]
            if not (a.is_alive and d.is_alive):
                step["dur"] = 0
                return
            hits = CE.do_ranged_attack(self.state, a, d) if step["ranged"] else CE.do_melee_attack(self.state, a, d)
            step["hits"] = hits
            step["dur"] = ATTACK_T
            if step["ranged"]:
                step["proj"] = (hex_center(a.hex_pos), hex_center(d.hex_pos))
                self.pending_hits = hits     # floaters appear when the arrow lands
                sound_engine.play("shoot")
            else:
                self.attack_anim = AttackAnimation(a, hex_center(a.hex_pos), hex_center(d.hex_pos))
                self.add_hits(hits)
                sound_engine.play("sword_hit")
        elif k == "spell":
            sp = SPELLS[step["name"]]
            sound_engine.play("spell_cast")
            target_pos = step.get("pos")
            hits = step["fn"]() or []
            kind = {"damage": "damage", "buff": "buff", "debuff": "debuff"}.get(sp["effect_type"], "buff")
            spots = [h[0].hex_pos for h in hits] if kind == "damage" and hits else ([target_pos] if target_pos else [])
            if not spots:
                spots = [(GRID_COLS // 2, GRID_ROWS // 2)]
            for pos in spots:
                x, y = hex_center(pos)
                self.fx.append(SpellEffect(kind, x, y - 10))
            self.say(f"{step['name']}!", spots[0], C_PURP, big=True, dy=-70)
            step["dur"] = 0.8
        else:
            step.setdefault("dur", 0.3)

    def update_anim(self, dt):
        if self.anim is None:
            if not self.queue:
                cb, self.after_queue = self.after_queue, None
                if cb:
                    cb()
                return
            self.anim = self.queue.pop(0)
            self.start_step(self.anim)
        a = self.anim
        a["t"] += dt
        if a["kind"] == "attack" and a.get("proj") and a["t"] >= 0.3 and getattr(self, "pending_hits", None):
            self.add_hits(self.pending_hits)
            self.pending_hits = None
        if a["t"] >= a["dur"]:
            if a["kind"] == "move" and a["path"]:
                a["stack"].hex_pos = a["path"][-1]
            self.anim = None

    def stack_draw_pos(self, s):
        """Screen position, interpolated while moving or lunging."""
        a = self.anim
        if a and a["kind"] == "move" and a["stack"] is s and a["path"] and a["dur"]:
            f = min(1.0, a["t"] / a["dur"])
            if s.is_flying:
                (x0, y0), (x1, y1) = hex_center(a["from"]), hex_center(a["path"][-1])
                return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * 30
            pts = [a["from"]] + a["path"]
            seg = min(len(pts) - 2, int(f * (len(pts) - 1)))
            lf = f * (len(pts) - 1) - seg
            (x0, y0), (x1, y1) = hex_center(pts[seg]), hex_center(pts[seg + 1])
            return x0 + (x1 - x0) * lf, y0 + (y1 - y0) * lf
        if self.attack_anim and self.attack_anim.stack is s:
            return self.attack_anim.offset_pos()
        return hex_center(s.hex_pos)

    # ─────────────────────────── results ───────────────────────────
    def finish(self, winner):
        """winner: 'attacker' | 'defender' | 'retreat' (the player fled)."""
        st = self.state
        ps = st.player_side
        es = "defender" if ps == "attacker" else "attacker"
        if winner == "retreat":
            outcome, self.winner_side, self.retreated = "retreat", es, ps
        else:
            outcome, self.winner_side, self.retreated = ("victory" if winner == ps else "defeat"), winner, None
        player_stacks = st.attacker_stacks if ps == "attacker" else st.defender_stacks
        enemy_stacks = st.defender_stacks if ps == "attacker" else st.attacker_stacks
        xp = CE.xp_for_kills(enemy_stacks) if outcome == "victory" and self.player_hero() else 0
        self.result = {"outcome": outcome, "xp": xp,
                       "player_losses": [(s.creature_key, s.killed) for s in player_stacks if s.killed],
                       "enemy_losses": [(s.creature_key, s.killed) for s in enemy_stacks if s.killed],
                       "enemy_side": es}
        st.phase = "defeat" if outcome != "victory" else "victory"
        sound_engine.play("victory" if outcome == "victory" else "defeat")
        F = main.F
        self.result_btn = Button((SW // 2 - 110, SH // 2 + 150, 220, 46), "Continue", F["md"], (60, 45, 20),
                                 hov=(95, 70, 25), tc=C_GOLD, bdr=C_GOLD)

    def apply_result(self):
        """Write the outcome back to the world and return to the adventure map."""
        msgs = world.apply_battle_result(main.STATE, self.state, self.att_hero, self.def_hero,
                                         self.neutral, self.town, self.winner_side, self.retreated)
        SM.go("adventure_map", messages=msgs)

    # ─────────────────────────── scene interface ───────────────────────────
    def update(self, dt):
        self.t += dt
        st = self.state
        self.texts = [f for f in self.texts if f.update(dt)]
        self.fx = [f for f in self.fx if f.update(dt)]
        self.deaths = [d for d in self.deaths if d.update(dt)]
        if self.attack_anim and not self.attack_anim.update(dt):
            self.attack_anim = None
        for k in list(self.flash):
            self.flash[k] -= dt
            if self.flash[k] <= 0:
                del self.flash[k]
        mx, my = pygame.mouse.get_pos()
        self.hover = self.hex_at_mouse(mx, my)
        s = st.active_stack
        player_turn = st.phase in ("player_move", "player_attack")
        self.btn["wait"].enabled = player_turn and not self.moved and s is not None and not s.wait_flag
        self.btn["defend"].enabled = player_turn
        self.btn["spell"].enabled = player_turn and CE.can_cast(st, st.player_side)
        self.btn["retreat"].enabled = player_turn and self.player_hero() is not None
        for b in list(self.btn.values()) + self.spell_buttons + [self.btn_cancel, self.btn_start, self.btn_yes, self.btn_no] + ([self.result_btn] if self.result_btn else []):
            b.update(mx, my)
        if st.phase == "animating":
            self.update_anim(dt)
        elif st.phase == "ai_turn":
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self.run_ai()

    def handle(self, ev):
        st = self.state
        if st.phase in ("victory", "defeat"):
            if (self.result_btn and self.result_btn.clicked(ev)) or (
                    ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE)):
                self.apply_result()
            return
        if self.confirm_retreat:
            if self.btn_yes.clicked(ev):
                self.confirm_retreat = False
                self.retreat()
            elif self.btn_no.clicked(ev) or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                self.confirm_retreat = False
            return
        if st.phase == "spell_select":
            if self.btn_cancel.clicked(ev) or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE) or (
                    ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3):
                self.cancel_spell()
                return
            for b in self.spell_buttons:
                if b.clicked(ev):
                    self.choose_spell(b.spell)
                    return
            if self.pending_spell and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = self.hex_at_mouse(*ev.pos)
                if pos in self.spell_hexes:
                    self.cast(self.pending_spell, pos)
            return
        if st.phase == "tactics":
            if self.btn_start.clicked(ev) or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN):
                self.start_battle()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = self.hex_at_mouse(*ev.pos)
                if pos:
                    self.tactics_click(pos)
            return
        if st.phase not in ("player_move", "player_attack"):
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_d and self.btn["defend"].enabled:
                self.defend()
            elif ev.key == pygame.K_w and self.btn["wait"].enabled:
                self.wait()
            elif ev.key == pygame.K_c and self.btn["spell"].enabled:
                self.open_spellbook()
            return
        if self.btn["wait"].clicked(ev):
            self.wait()
        elif self.btn["defend"].clicked(ev):
            self.defend()
        elif self.btn["spell"].clicked(ev):
            self.open_spellbook()
        elif self.btn["retreat"].clicked(ev):
            self.confirm_retreat = True
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            pos = self.hex_at_mouse(*ev.pos)
            if pos:
                self.player_click_hex(pos, *ev.pos)

    # ─────────────────────────── drawing ───────────────────────────
    def build_background(self):
        bg = pygame.Surface((PANEL_X, SH))
        bands = [(16, 24, 52), (22, 34, 70), (30, 46, 88)]
        bh = (HORIZON - TOP_H) / len(bands)
        for i, c in enumerate(bands):
            pygame.draw.rect(bg, c, (0, TOP_H + i * bh, PANEL_X, bh + 1))
        rng = random.Random(7)
        for _ in range(6):   # distant hills
            x = rng.randrange(-80, PANEL_X)
            w = rng.randrange(160, 320)
            pygame.draw.ellipse(bg, (36, 44, 58), (x, HORIZON - 26, w, 60))
        pygame.draw.rect(bg, (58, 64, 48), (0, HORIZON, PANEL_X, SH - HORIZON))
        for _ in range(500):   # earth speckle
            x, y = rng.randrange(PANEL_X), rng.randrange(HORIZON, SH)
            c = rng.choice([(66, 72, 52), (50, 56, 42), (72, 70, 56)])
            pygame.draw.circle(bg, c, (x, y), rng.randint(1, 3))
        pygame.draw.line(bg, (110, 100, 80), (0, HORIZON), (PANEL_X, HORIZON), 2)
        for _ in range(45):   # rocky strip at the bottom
            cx, cy = rng.randrange(PANEL_X), rng.randrange(SH - 170, SH)
            n, r = rng.randint(4, 6), rng.randint(5, 16)
            pts = [(cx + math.cos(a) * r * rng.uniform(0.6, 1.1), cy + math.sin(a) * r * rng.uniform(0.5, 0.9))
                   for a in (i * 2 * math.pi / n for i in range(n))]
            g = rng.randint(85, 125)
            pygame.draw.polygon(bg, (g, g, g + 8), pts)
            pygame.draw.polygon(bg, (g - 40, g - 40, g - 34), pts, 1)
        return bg

    def draw(self, surf):
        if self.bg is None:
            self.bg = self.build_background()
        surf.blit(self.bg, (0, 0))
        self.draw_grid(surf)
        for f in self.fx:
            if isinstance(f, DamageFlash):
                f.draw(surf)
        self.draw_stacks(surf)
        for d in self.deaths:
            d.draw(surf, self.t)
        for f in self.fx:
            if not isinstance(f, DamageFlash):
                f.draw(surf)
        self.draw_projectiles(surf)
        for f in self.texts:
            f.draw(surf, main.F["md"])
        self.draw_tooltip(surf)
        self.draw_top(surf)
        self.draw_panel(surf)
        if self.confirm_retreat:
            self.draw_confirm(surf)
        if self.state.phase in ("victory", "defeat"):
            self.draw_result(surf)

    def draw_confirm(self, surf):
        F = main.F
        shade = pygame.Surface((SW, SH), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surf.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 420, 190)
        box.center = (SW // 2, SH // 2)
        panel(surf, box, C_BG1, C_RED, br=12, bw=2)
        blit(surf, "Are you sure?", F["lg"], C_RED, box.centerx, box.y + 20, "center")
        blit(surf, "You will lose all troops.", F["sm"], C_TXT, box.centerx, box.y + 64, "center")
        self.btn_yes.draw(surf)
        self.btn_no.draw(surf)

    def draw_grid(self, surf):
        st = self.state
        active = st.active_stack
        targets = self.spell_hexes if st.phase == "spell_select" else self.attackable
        preview_path, stand = [], None
        if self.hover and st.phase in ("player_move", "player_attack") and active:
            tgt = st.get_stack_at(*self.hover)
            if tgt and self.hover in self.attackable and not CE.can_shoot(st, active):
                stand = self.stand_hex_for(tgt, *pygame.mouse.get_pos())
                if stand:
                    preview_path = CE.path_to(st, active, stand)
            elif self.hover in self.reach:
                preview_path = CE.path_to(st, active, self.hover)
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                pos = (c, r)
                fill = (*C_BG2, 150)
                if c in self.tactics_cols and not st.get_stack_at(c, r):
                    fill = (*C_GRN, 60)
                if pos in self.reach:
                    fill = (*C_BLUE, 70)
                if pos in targets:
                    fill = (*(C_PURP if st.phase == "spell_select" else C_RED), 110)
                if pos == stand:
                    fill = (*C_GOLD, 90)
                draw_hex(surf, c, r, GX, GY, fill, (88, 96, 112))
        if self.hover and (self.hover in self.reach or self.hover in targets):
            draw_hex(surf, *self.hover, GX, GY, None, (240, 240, 250), width=2)
        # midline between the two deployment zones
        mid = GX + (hex_to_pixel(7, 0)[0] + hex_to_pixel(8, 1)[0]) / 2
        pygame.draw.line(surf, (120, 125, 135), (mid, GY + 4), (mid, GY + HEX_H * 0.75 * (GRID_ROWS - 1) + HEX_H - 4), 1)
        for pos, key in self.remains:
            if not st.get_stack_at(*pos):
                x, y = hex_center(pos)
                pygame.draw.line(surf, (70, 66, 60), (x - 8, y - 4), (x + 8, y + 8), 3)
                pygame.draw.line(surf, (70, 66, 60), (x + 8, y - 4), (x - 8, y + 8), 3)
        if self.tactics_sel:
            draw_hex(surf, *self.tactics_sel.hex_pos, GX, GY, None, C_GOLD, width=3)
        if active and active.is_alive and st.phase != "tactics":
            b = 0.55 + 0.45 * math.sin(self.t * 4)
            draw_hex(surf, *active.hex_pos, GX, GY, None, tuple(int(v * b) for v in C_GOLD), width=3)
        # dotted path preview
        if preview_path and active:
            prev = hex_center(active.hex_pos)
            for p in preview_path:
                cur = hex_center(p)
                for k in range(1, 4):
                    f = k / 4
                    pygame.draw.circle(surf, C_TXT, (int(prev[0] + (cur[0] - prev[0]) * f),
                                                     int(prev[1] + (cur[1] - prev[1]) * f)), 2)
                prev = cur

    def draw_stacks(self, surf):
        st = self.state
        active = st.active_stack
        for s in sorted(st.all_alive_stacks, key=lambda s: self.stack_draw_pos(s)[1]):
            x, y = self.stack_draw_pos(s)
            glow = (0.35 + 0.25 * math.sin(self.t * 4)) if s is active else 0
            creature_art.draw_creature(surf, x, y - 12, s.creature_key, self.t, count=s.count, size=SPRITE,
                                       facing=1 if s.side == "attacker" else -1, glow=glow,
                                       flash=min(1.0, self.flash.get(id(s), 0) * 2.2),
                                       border=self.side_color(s))
            if s.is_defending:
                pygame.draw.circle(surf, C_BLUE, (int(x - 22), int(y + 10)), 6, 2)

    def draw_projectiles(self, surf):
        a = self.anim
        if not (a and a["kind"] == "attack" and a.get("proj") and a["t"] < 0.3):
            return
        (x0, y0), (x1, y1) = a["proj"]
        f = a["t"] / 0.3
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * 40 - 14
        ang = math.atan2(y1 - y0, x1 - x0)
        dx, dy = math.cos(ang) * 10, math.sin(ang) * 10
        pygame.draw.line(surf, (240, 230, 200), (x - dx, y - dy), (x + dx, y + dy), 3)
        pygame.draw.circle(surf, C_GOLD, (int(x + dx), int(y + dy)), 3)

    def draw_queue(self, surf, x0, y):
        """Upcoming stacks this round, in the right panel."""
        st, F = self.state, main.F
        blit(surf, f"Turn order · round {st.round}", F["ti"], C_SUB, x0 + 14, y)
        upcoming = [s for s in st.turn_order[max(0, st.current_idx):] if s.is_alive and not s.has_acted]
        x = x0 + 12
        for i, s in enumerate(upcoming[:8]):
            r = pygame.Rect(x, y + 18, 44, 46)
            panel(surf, r, C_BG2 if i else (70, 58, 24), self.side_color(s), br=6, bw=2 if i == 0 else 1)
            creature_art.draw_creature(surf, r.centerx, r.centery - 4, s.creature_key, self.t, size=38,
                                       facing=1 if s.side == "attacker" else -1)
            blit(surf, str(s.count), F["ti"], C_TXT, r.right - 3, r.bottom - 15, "right")
            x += 48
        if not upcoming:
            blit(surf, "—", F["sm"], C_HINT, x0 + 14, y + 30)

    def tooltip_text(self):
        st = self.state
        if not self.hover:
            return None
        s = st.get_stack_at(*self.hover)
        active = st.active_stack
        if st.phase == "spell_select" and self.pending_spell and self.hover in self.spell_hexes:
            sp = SPELLS[self.pending_spell]
            if sp["effect_type"] == "damage":
                return f"Cast {self.pending_spell}: {CE.spell_damage(sp, self.player_hero())} damage"
            return f"Cast {self.pending_spell}" + (f" on {s.name}" if s else "")
        if s and active and self.hover in self.attackable and st.phase in ("player_move", "player_attack"):
            ranged = not self.moved and CE.can_shoot(st, active)
            lo, hi = CE.damage_range(active, s, ranged)
            hp = s.creature["hp"]
            verb = "Shoot" if ranged else "Attack"
            extra = " ×2" if (ranged and active.has("double_shot")) or (not ranged and active.has("double_strike")) else ""
            return (f"{verb} {s.name}: {lo}-{hi} damage{extra}, "
                    f"kills {min(s.count, lo // hp)}-{min(s.count, hi // hp)}")
        if s:
            return (f"{s.count} {s.name}  ·  HP {s.hp_remaining}/{s.creature['hp']}  ·  "
                    f"ATK {s.effective_attack}  DEF {s.effective_defense}  SPD {s.effective_speed}")
        if self.hover in self.reach:
            return "Move here"
        return None

    def draw_tooltip(self, surf):
        text = self.tooltip_text()
        if not text:
            return
        F = main.F
        w = F["sm"].size(text)[0] + 20
        r = pygame.Rect(12, SH - 140, w, 26)
        panel(surf, r, (14, 18, 28), C_BDR, br=6)
        blit(surf, text, F["sm"], C_TXT, r.x + 10, r.y + 4)

    def draw_top(self, surf):
        st, F = self.state, main.F
        pygame.draw.rect(surf, C_BG1, (0, 0, SW, TOP_H))
        pygame.draw.line(surf, C_BDR, (0, TOP_H - 1), (SW, TOP_H - 1), 2)
        blit(surf, f"BATTLE: {self.att_hero.name} vs {self.def_name}", F["md"], C_GOLD, 16, 11)
        blit(surf, f"Round {st.round}", F["md"], C_TXT, PANEL_X - 16, 11, "right")
        if st.phase == "ai_turn" or (st.phase == "animating" and st.active_stack and not self.is_player(st.active_stack)):
            blit(surf, "Enemy turn…", F["sm"], C_RED, SW - 16, 14, "right")
        elif st.phase in ("player_move", "player_attack", "spell_select"):
            blit(surf, "Your turn", F["sm"], C_GRN, SW - 16, 14, "right")

    def draw_panel(self, surf):
        st, F = self.state, main.F
        x0 = PANEL_X
        pygame.draw.rect(surf, C_BG1, (x0, TOP_H, SW - x0, SH - TOP_H))
        pygame.draw.line(surf, C_BDR, (x0, TOP_H), (x0, SH), 2)
        s = st.active_stack
        # active unit card (top ~150px)
        card = pygame.Rect(x0 + 10, TOP_H + 10, SW - x0 - 20, 150)
        panel(surf, card, C_BG2, self.side_color(s) if s else C_BDR, br=10)
        if s and s.is_alive:
            creature_art.draw_creature(surf, card.x + 54, card.y + 62, s.creature_key, self.t, size=88,
                                       facing=1 if s.side == "attacker" else -1)
            who = "Your" if self.is_player(s) else "Enemy"
            blit(surf, f"{s.count} {s.name}", F["md"], C_GOLD, card.x + 110, card.y + 10)
            blit(surf, f"{who} stack · Tier {s.creature['tier']}", F["ti"], C_SUB, card.x + 110, card.y + 36)
            hp_bar(surf, (card.x + 110, card.y + 56, 240, 12), s.hp_remaining, s.creature["hp"])
            blit(surf, f"HP {s.hp_remaining}/{s.creature['hp']}  (total {s.total_hp})", F["ti"], C_TXT, card.x + 110, card.y + 72)
            d = s.creature
            blit(surf, f"ATK {s.effective_attack}  DEF {s.effective_defense}  DMG {d['damage_min']}-{d['damage_max']}",
                 F["ti"], C_TXT, card.x + 110, card.y + 92)
            tags = [f"SPD {s.effective_speed}", f"INIT {s.initiative}"] + (["Ranged"] if s.is_ranged else []) + \
                   (["Flying"] if s.is_flying else []) + [e.replace("_", " ").title() for e in sorted(s.effects)] + \
                   (["Defending"] if s.is_defending else [])
            blit_wrap(surf, " · ".join(tags), F["ti"], C_PURP, card.x + 110, card.y + 110, card.w - 120)
        # hero mana line
        hero = self.player_hero()
        y = card.bottom + 10
        if hero:
            blit(surf, f"{hero.name}  ·  Mana {hero.mana}/{hero.mana_max}  ·  Power {hero.stat('power')}",
                 F["sm"], C_BLUE, x0 + 14, y)
            if st.hero_cast[st.player_side]:
                blit(surf, "(cast this round)", F["ti"], C_HINT, SW - 14, y + 2, "right")
        y += 28
        self.draw_queue(surf, x0, y)
        y += 72
        if st.phase == "tactics":
            box = pygame.Rect(x0 + 10, y + 6, SW - x0 - 20, 578 - y)
            panel(surf, box, (40, 34, 18), C_GOLD, br=8)
            blit(surf, "TACTICS", F["md"], C_GOLD, box.x + 12, box.y + 10)
            blit_wrap(surf, "Click one of your stacks, then a free green hex to move it there. "
                            "Press START BATTLE (or Enter) when ready.", F["sm"], C_TXT, box.x + 12, box.y + 42, box.w - 24)
            self.btn_start.draw(surf)
        elif st.phase == "spell_select":
            blit(surf, "Spellbook" if not self.pending_spell else f"{self.pending_spell}: pick a target",
                 F["md"], C_PURP, x0 + 14, y)
            if not self.pending_spell:
                for b in self.spell_buttons:
                    b.draw(surf)
                if not self.spell_buttons:
                    blit(surf, "No battle spells known.", F["sm"], C_SUB, x0 + 14, y + 40)
            else:
                blit_wrap(surf, SPELLS[self.pending_spell]["description"], F["sm"], C_TXT, x0 + 14, y + 36, 370)
            self.btn_cancel.draw(surf)
        else:
            blit(surf, "Battle log", F["sm"], C_SUB, x0 + 14, y)
            log_rect = pygame.Rect(x0 + 10, y + 22, SW - x0 - 20, SH - 128 - (y + 22))
            panel(surf, log_rect, C_BG0, C_BDR, br=8)
            lines = st.combat_log[-200:]
            out, ly = [], log_rect.bottom - 8
            # draw newest at the bottom, wrapping long lines, until the box is full
            for line in reversed(lines):
                h = self._wrapped_height(line, F["ti"], log_rect.w - 16)
                ly -= h
                if ly < log_rect.y + 6:
                    break
                out.append((line, ly))
            for line, ly2 in out:
                col = C_GOLD if line.startswith("—") else C_SUB if line.startswith("  >>") else C_TXT
                blit_wrap(surf, line, F["ti"], col, log_rect.x + 8, ly2, log_rect.w - 16, gap=1)
        for b in self.btn.values():
            b.draw(surf)
        blit(surf, "W wait · D defend · C cast", F["ti"], C_HINT, x0 + 14, SH - 122)

    @staticmethod
    def _wrapped_height(text, font, max_w):
        lines, line = 1, ""
        for word in text.split(" "):
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= max_w or not line:
                line = test
            else:
                lines += 1
                line = word
        return lines * (font.get_linesize() + 1)

    def draw_result(self, surf):
        F, r = main.F, self.result
        shade = pygame.Surface((SW, SH), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surf.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 620, 420)
        box.center = (SW // 2, SH // 2)
        good = r["outcome"] == "victory"
        panel(surf, box, C_BG1, C_GOLD if good else C_RED, br=14, bw=2)
        title = {"victory": "VICTORY!", "defeat": "DEFEATED", "retreat": "RETREAT"}[r["outcome"]]
        blit(surf, title, F["title"], C_GOLD if good else C_RED, box.centerx, box.y + 20, "center")
        for i, (label, losses) in enumerate((("Your losses", r["player_losses"]), ("Enemy losses", r["enemy_losses"]))):
            x = box.x + 30 + i * 300
            blit(surf, label, F["md"], C_TXT, x, box.y + 92)
            if not losses:
                blit(surf, "none", F["sm"], C_HINT, x, box.y + 128)
            for j, (key, n) in enumerate(losses[:7]):
                yy = box.y + 124 + j * 30
                creature_art.draw_creature(surf, x + 14, yy + 10, key, self.t, size=30)
                blit(surf, f"{n} {unit_name(key, n)}", F["sm"], C_SUB, x + 36, yy + 2)
        if good:
            blit(surf, f"Experience gained: {r['xp']}", F["md"], C_GRN, box.centerx, box.bottom - 116, "center")
        elif r["outcome"] == "retreat":
            blit(surf, "Your hero escapes, but the army is lost.", F["sm"], C_SUB, box.centerx, box.bottom - 112, "center")
        self.result_btn.draw(surf)
