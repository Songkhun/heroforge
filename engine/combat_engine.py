"""Combat rules: stacks, turn order, damage, retaliation, spells, and the battle AI.

Rendering and animation live in scenes/combat_screen.py; this module only changes state.
"""
import json
import random
from dataclasses import dataclass, field

from engine.creature import CREATURES, unit_name
from engine import skills as SK
from engine.hex_grid import (GRID_COLS, GRID_ROWS, hex_neighbors, hex_distance,
                             get_reachable, find_hex_path)

# Shared spell table (main.SPELLS is this dict), keyed by display name ("Lightning Bolt").
SPELLS = {}


def load_spells_data(json_path):
    with open(json_path) as f:
        data = json.load(f)
    SPELLS.clear()
    SPELLS.update(data)
    return SPELLS


def spell_key(name):
    return name.lower().replace(" ", "_")


@dataclass
class CombatStack:
    creature_key: str
    count: int
    hp_remaining: int
    side: str                      # "attacker" | "defender"
    hex_pos: tuple = (0, 0)
    has_acted: bool = False
    has_retaliated: bool = False
    is_defending: bool = False
    wait_flag: bool = False
    speed_override: int = 0        # speed modifier from Haste/Slow/Blizzard
    atk_modifier: int = 0          # Bloodlust/Weakness
    def_modifier: int = 0          # Stone Skin
    hero_attack: int = 0           # commanding hero's attack/defense bonus
    hero_defense: int = 0
    slot: int = -1                 # army/garrison slot this stack came from
    start_count: int = 0
    dmg_mode: str = "normal"       # "max" (Bless) | "min" (Curse)
    effects: set = field(default_factory=set)   # spell keys active on this stack
    # from the commanding hero's skills and artifacts (set by build_side)
    hp_bonus: int = 0              # extra health per unit
    speed_bonus: int = 0
    melee_bonus: float = 0.0       # Offense, fraction (+0.1 = +10%)
    ranged_bonus: float = 0.0      # Archery
    damage_reduction: float = 0.0  # Armorer
    luck: int = 0
    morale: int = 0
    morale_used: bool = False      # one bonus move per round

    def __post_init__(self):
        if self.hp_remaining <= 0:
            self.hp_remaining = self.unit_hp
        if not self.start_count:
            self.start_count = self.count

    @property
    def unit_hp(self):
        return self.creature["hp"] + self.hp_bonus

    @property
    def creature(self):
        return CREATURES[self.creature_key]

    @property
    def name(self):
        return self.creature["name"]

    @property
    def initiative(self):
        return self.creature["initiative"]

    @property
    def effective_speed(self):
        return max(1, self.creature["speed"] + self.speed_override + self.speed_bonus)

    @property
    def total_hp(self):
        if self.count <= 0:
            return 0
        return self.count * self.unit_hp - (self.unit_hp - self.hp_remaining)

    @property
    def is_alive(self):
        return self.count > 0

    @property
    def is_ranged(self):
        return self.creature["is_ranged"]

    @property
    def is_flying(self):
        return self.creature["is_flying"]

    def has(self, ability):
        return ability in self.creature["abilities"]

    @property
    def effective_attack(self):
        return self.creature["attack"] + self.atk_modifier + self.hero_attack

    @property
    def effective_defense(self):
        base = self.creature["defense"] + self.def_modifier + self.hero_defense
        return int(base * 1.3) if self.is_defending else base

    @property
    def killed(self):
        return self.start_count - self.count

    def take_damage(self, damage):
        """Apply damage to the stack (top unit first). Returns units killed."""
        damage = max(0, int(damage))
        if damage <= 0 or self.count <= 0:
            return 0
        hp = self.unit_hp
        remaining = self.total_hp - damage
        if remaining <= 0:
            killed, self.count, self.hp_remaining = self.count, 0, 0
            return killed
        new_count = (remaining + hp - 1) // hp
        killed = self.count - new_count
        self.count = new_count
        self.hp_remaining = remaining - (new_count - 1) * hp
        return killed

    def heal(self, amount, revive=False):
        """Restore HP; with revive, dead units (up to start_count) come back. Returns units revived."""
        hp = self.unit_hp
        cap = (self.start_count if revive else self.count) * hp
        new_total = min(cap, self.total_hp + int(amount))
        if new_total <= 0:
            return 0
        before = self.count
        self.count = (new_total + hp - 1) // hp
        self.hp_remaining = new_total - (self.count - 1) * hp
        return self.count - before


@dataclass
class CombatState:
    attacker_hero: object                  # Hero
    defender_hero: object = None           # Hero, or None vs. neutrals / ungarrisoned towns
    attacker_stacks: list = field(default_factory=list)
    defender_stacks: list = field(default_factory=list)
    turn_order: list = field(default_factory=list)
    current_idx: int = 0
    round: int = 1
    combat_log: list = field(default_factory=list)
    phase: str = "player_move"
    player_side: str = "attacker"
    hero_cast: dict = field(default_factory=lambda: {"attacker": False, "defender": False})

    @property
    def active_stack(self):
        if 0 <= self.current_idx < len(self.turn_order):
            return self.turn_order[self.current_idx]
        return None

    @property
    def all_alive_attacker(self):
        return [s for s in self.attacker_stacks if s.is_alive]

    @property
    def all_alive_defender(self):
        return [s for s in self.defender_stacks if s.is_alive]

    @property
    def all_alive_stacks(self):
        return self.all_alive_attacker + self.all_alive_defender

    def hero_of(self, side):
        return self.attacker_hero if side == "attacker" else self.defender_hero

    def stacks_of(self, side):
        return self.all_alive_attacker if side == "attacker" else self.all_alive_defender

    def enemies_of(self, stack):
        return self.all_alive_defender if stack.side == "attacker" else self.all_alive_attacker

    def log(self, msg):
        self.combat_log.extend(msg.split("\n"))
        del self.combat_log[:-50]

    def build_turn_order(self):
        """Alive stacks by initiative (highest first); waiting stacks go last."""
        alive = self.all_alive_stacks
        alive.sort(key=lambda s: (s.wait_flag, -s.initiative, s.side != "attacker", s.slot))
        self.turn_order = alive
        self.current_idx = 0

    def new_round(self):
        self.round += 1
        for s in self.all_alive_stacks:
            s.has_acted = s.has_retaliated = s.wait_flag = s.morale_used = False
        self.hero_cast = {"attacker": False, "defender": False}
        self.build_turn_order()
        self.log(f"— Round {self.round} —")

    def advance_to_next(self):
        """Move to the next stack that can still act; starts a new round when needed."""
        self.current_idx += 1
        while True:
            while self.current_idx < len(self.turn_order):
                s = self.turn_order[self.current_idx]
                if s.is_alive and not s.has_acted:
                    s.is_defending = False   # defend lasts until the stack's next turn
                    return s
                self.current_idx += 1
            if not self.all_alive_attacker or not self.all_alive_defender:
                return None
            self.new_round()   # resets has_acted and current_idx; loop picks the first stack

    def wait_active(self):
        """Move the active stack to the end of this round's order."""
        s = self.active_stack
        s.wait_flag = True
        self.turn_order.pop(self.current_idx)
        self.turn_order.append(s)
        self.current_idx -= 1
        return self.advance_to_next()

    def get_stack_at(self, col, row):
        return next((s for s in self.all_alive_stacks if s.hex_pos == (col, row)), None)

    def occupied_hexes(self):
        return {s.hex_pos: s for s in self.all_alive_stacks}

    def enemy_hexes_of(self, stack):
        return {s.hex_pos for s in self.enemies_of(stack)}


class CombatEngine:
    # ── damage ──
    @staticmethod
    def _multiplier(attacker, defender):
        diff = attacker.effective_attack - defender.effective_defense
        return 1.0 + 0.05 * diff if diff >= 0 else 1.0 / (1.0 + 0.025 * -diff)

    @staticmethod
    def _base_roll(stack):
        lo, hi = stack.creature["damage_min"], stack.creature["damage_max"]
        if stack.dmg_mode == "max":
            return hi
        if stack.dmg_mode == "min":
            return lo
        return random.randint(lo, hi)

    @staticmethod
    def _situational(attacker, defender, ranged):
        f = 1.0
        if not ranged and attacker.is_ranged:
            f *= 0.5                       # shooters fight poorly in melee
        if ranged and "air_shield" in defender.effects:
            f *= 0.75
        if attacker.has("hate_undead") and defender.has("undead"):
            f *= 1.5
        f *= 1 + (attacker.ranged_bonus if ranged else attacker.melee_bonus)
        f *= 1 - defender.damage_reduction
        return f

    @classmethod
    def calculate_damage(cls, attacker, defender, ranged=False):
        mult = cls._multiplier(attacker, defender) * cls._situational(attacker, defender, ranged)
        return max(1, int(cls._base_roll(attacker) * attacker.count * mult))

    @classmethod
    def damage_range(cls, attacker, defender, ranged=False):
        """(min, max) damage preview for tooltips."""
        mult = cls._multiplier(attacker, defender) * cls._situational(attacker, defender, ranged)
        lo, hi = attacker.creature["damage_min"], attacker.creature["damage_max"]
        if attacker.dmg_mode == "max":
            lo = hi
        elif attacker.dmg_mode == "min":
            hi = lo
        return max(1, int(lo * attacker.count * mult)), max(1, int(hi * attacker.count * mult))

    @staticmethod
    def can_shoot(state, stack):
        """Shooters may shoot unless an enemy stands next to them."""
        if not stack.is_ranged:
            return False
        enemy = state.enemy_hexes_of(stack)
        return not any(nb in enemy for nb in hex_neighbors(*stack.hex_pos))

    # ── attacks ──
    @classmethod
    def _strike(cls, state, attacker, defender, verb, ranged):
        before = defender.count
        damage = cls.calculate_damage(attacker, defender, ranged)
        lucky = attacker.luck > 0 and random.random() < attacker.luck * 0.1
        if lucky:
            damage *= 2
        killed = defender.take_damage(damage)
        msg = ("Lucky! " if lucky else "") + (f"{attacker.count} {unit_name(attacker.creature_key, attacker.count)} {verb} "
               f"{before} {unit_name(defender.creature_key, before)} for {damage} ({killed} killed)")
        return msg, damage, killed, ({"lucky"} if lucky else set())

    @classmethod
    def do_melee_attack(cls, state, attacker, defender):
        """Melee with one retaliation per round. Returns a list of hit events for floaters:
        [(target_stack, damage, killed), ...]; the log gets the text."""
        hits = []
        strikes = 2 if attacker.has("double_strike") else 1
        lines = []
        for i in range(strikes):
            if not (attacker.is_alive and defender.is_alive):
                break
            msg, dmg, k, tags = cls._strike(state, attacker, defender, "attack" if i == 0 else "strike again", False)
            lines.append(msg)
            hits.append((defender, dmg, k, tags))
            if (i == 0 and defender.is_alive and not defender.has_retaliated
                    and not attacker.has("no_retaliation")):
                rmsg, rdmg, rk, rtags = cls._strike(state, defender, attacker, "retaliate against", False)
                lines.append("  >> " + rmsg)
                hits.append((attacker, rdmg, rk, rtags))
                if not defender.has("unlimited_retaliation"):
                    defender.has_retaliated = True
        attacker.has_acted = True
        state.log("\n".join(lines))
        return hits

    @classmethod
    def do_ranged_attack(cls, state, attacker, defender):
        hits = []
        shots = 2 if attacker.has("double_shot") else 1
        lines = []
        for i in range(shots):
            if not defender.is_alive:
                break
            msg, dmg, k, tags = cls._strike(state, attacker, defender, "shoot" if i == 0 else "shoot again at", True)
            lines.append(msg)
            hits.append((defender, dmg, k, tags))
        attacker.has_acted = True
        state.log("\n".join(lines))
        return hits

    # ── spells ──
    @staticmethod
    def spell_damage(spell, hero):
        """Damage/healing amount, including the hero's school skill (Fire Magic etc.)."""
        power = hero.stat("power")
        if spell.get("scales_with_power", True):
            base = spell["base_value"] * power
        else:
            base = spell["base_value"] + 10 * power
        bonus = SK.skill_value(hero, SK.SCHOOL_SKILL.get(spell["school"], ""))
        return int(base * (1 + bonus / 100))

    @staticmethod
    def combat_spells(hero):
        """Spells the hero knows that work in battle."""
        return [n for n in hero.spells if n in SPELLS
                and spell_key(n) not in ("earthquake", "quicksand", "dimension_door")]

    @classmethod
    def can_cast(cls, state, side):
        hero = state.hero_of(side)
        if hero is None or state.hero_cast[side]:
            return False
        return any(hero.mana >= SPELLS[n]["mana_cost"] for n in cls.combat_spells(hero))

    @classmethod
    def spell_targets(cls, state, side, spell_name):
        """Hexes that are valid targets; None means the spell needs no target."""
        sp = SPELLS[spell_name]
        if sp["target"] == "all":
            return None
        key = spell_key(spell_name)
        friendly = sp["effect_type"] == "buff" or key == "resurrection"
        if sp["target"] == "area":
            return {s.hex_pos for s in state.all_alive_stacks}
        pool = state.stacks_of(side) if friendly else (
            state.all_alive_defender if side == "attacker" else state.all_alive_attacker)
        if key == "resurrection":
            pool = [s for s in state.attacker_stacks + state.defender_stacks
                    if s.side == side and s.count < s.start_count]
        return {s.hex_pos for s in pool if key not in s.effects or sp["effect_type"] == "damage"}

    @classmethod
    def cast_spell(cls, state, side, spell_name, target_hex=None):
        """Pay mana and apply the spell. Returns hit events for floaters."""
        hero = state.hero_of(side)
        sp = SPELLS[spell_name]
        if not hero.spend_mana(sp["mana_cost"]):
            return []
        state.hero_cast[side] = True
        key = spell_key(spell_name)
        target = None
        if target_hex is not None:
            target = state.get_stack_at(*target_hex)
            if target is None and key == "resurrection":
                target = next((s for s in state.attacker_stacks + state.defender_stacks
                               if s.hex_pos == tuple(target_hex) and s.side == side), None)
        hits = []
        if sp["effect_type"] == "damage":
            dmg = cls.spell_damage(sp, hero)
            if sp["target"] == "all":
                victims = state.all_alive_stacks
            elif key == "frost_ring":
                victims = [s for s in state.all_alive_stacks if s.hex_pos in hex_neighbors(*target_hex)]
            elif sp["target"] == "area":
                radius = 2 if key == "inferno" else 1
                victims = [s for s in state.all_alive_stacks if hex_distance(s.hex_pos, target_hex) <= radius]
            elif key == "chain_lightning":
                victims, cur = [target], target
                pool = [s for s in state.all_alive_stacks if s is not target]
                for _ in range(3):
                    if not pool:
                        break
                    cur = min(pool, key=lambda s: hex_distance(s.hex_pos, cur.hex_pos))
                    pool.remove(cur)
                    victims.append(cur)
            else:
                victims = [target]
            parts = []
            for i, v in enumerate(victims):
                d = dmg // (2 ** i) if key == "chain_lightning" else dmg
                k = v.take_damage(d)
                hits.append((v, d, k))
                parts.append(f"{v.name} -{d} ({k} killed)")
                if key == "blizzard" and v.is_alive:
                    v.speed_override -= 2
            msg = f"{hero.name} casts {spell_name}! " + ", ".join(parts) if parts else f"{hero.name} casts {spell_name}, hitting nothing."
        else:
            msg = cls.do_spell(state, hero, spell_name, target)
        state.log(msg)
        cls._eagle_eye(state, side, spell_name)
        return hits

    @staticmethod
    def _eagle_eye(state, caster_side, spell_name):
        """The opposing hero may learn a spell it sees cast (Eagle Eye, limited by Wisdom)."""
        watcher = state.hero_of("defender" if caster_side == "attacker" else "attacker")
        chance = SK.skill_value(watcher, "Eagle Eye")
        if (chance and spell_name not in watcher.spells and watcher.can_learn_spell(SPELLS[spell_name])
                and random.random() < chance / 100):
            watcher.add_spell(spell_name)
            state.log(f"{watcher.name}'s Eagle Eye learns {spell_name}!")

    @staticmethod
    def do_spell(state, caster_hero, spell_name, target_stack):
        """Single-target buff / debuff / special. Returns the log message."""
        sp = SPELLS[spell_name]
        key = spell_key(spell_name)
        t = target_stack
        if key == "resurrection":
            revived = t.heal(CombatEngine.spell_damage(sp, caster_hero), revive=True)
            return f"{caster_hero.name} casts Resurrection: {revived} {t.name} rise again!"
        t.effects.add(key)
        if key == "haste":
            t.speed_override += 3
        elif key == "slow":
            t.speed_override -= 3
        elif key == "bless":
            t.dmg_mode = "max"
        elif key == "curse":
            t.dmg_mode = "min"
        elif key == "bloodlust":
            t.atk_modifier += 3
        elif key == "weakness":
            t.atk_modifier -= 3
        elif key == "stone_skin":
            t.def_modifier += 3
        # air_shield is read from t.effects in damage calculation
        return f"{caster_hero.name} casts {spell_name} on {t.name}"

    # ── battle flow ──
    @staticmethod
    def check_victory(state):
        if not state.all_alive_defender:
            return "attacker"
        if not state.all_alive_attacker:
            return "defender"
        return None

    @staticmethod
    def setup_positions(state):
        rows = [1, 3, 5, 7, 9, 2, 4]
        for i, s in enumerate(state.attacker_stacks):
            s.hex_pos = (1, rows[i % 7])
        for i, s in enumerate(state.defender_stacks):
            s.hex_pos = (GRID_COLS - 2, rows[i % 7])

    @staticmethod
    def roll_morale(state, stack):
        """After acting, a living (non-undead) stack with morale may act again once per round."""
        if (stack.is_alive and stack.morale > 0 and not stack.morale_used and not stack.has("undead")
                and CombatEngine.check_victory(state) is None and random.random() < stack.morale * 0.1):
            stack.morale_used = True
            stack.has_acted = False
            state.log(f"High morale! {unit_name(stack.creature_key, stack.count)} act again.")
            return True
        return False

    @classmethod
    def auto_resolve(cls, state, max_rounds=40):
        """Fight to the end with the AI controlling both sides (no animation).

        Returns the winning side. If neither side wins in time the defender holds.
        """
        state.build_turn_order()
        while cls.check_victory(state) is None and state.round <= max_rounds:
            s = state.active_stack
            if s is None:
                break
            act = cls.ai_action(state, s)
            if act["path"]:
                s.hex_pos = act["path"][-1]
            if act["target"] and act["target"].is_alive:
                (cls.do_ranged_attack if act["ranged"] else cls.do_melee_attack)(state, s, act["target"])
            elif act["defend"]:
                s.is_defending = True
            s.has_acted = True
            if not cls.roll_morale(state, s):
                state.advance_to_next()
        return cls.check_victory(state) or "defender"

    @staticmethod
    def xp_for_kills(stacks):
        return sum(s.creature["xp_value"] * s.killed for s in stacks)

    # ── movement helpers ──
    @staticmethod
    def reachable(state, stack):
        occ = set(state.occupied_hexes()) - {stack.hex_pos}
        return get_reachable(*stack.hex_pos, stack.effective_speed, occ, stack.is_flying)

    @staticmethod
    def path_to(state, stack, dest):
        if stack.is_flying:
            return [tuple(dest)]
        occ = set(state.occupied_hexes()) - {stack.hex_pos}
        return find_hex_path(stack.hex_pos, dest, occ)

    @classmethod
    def ai_action(cls, state, stack):
        """Decide an action for a computer-controlled stack.

        Returns {"path": [...], "target": CombatStack|None, "ranged": bool, "defend": bool}.
        """
        enemies = state.enemies_of(stack)
        act = {"path": [], "target": None, "ranged": False, "defend": False}
        if not enemies:
            act["defend"] = True
            return act
        threat = lambda e: e.effective_attack * e.count * (e.creature["damage_min"] + e.creature["damage_max"])
        if cls.can_shoot(state, stack):
            act.update(target=max(enemies, key=threat), ranged=True)
            return act
        adjacent = [e for e in enemies if e.hex_pos in hex_neighbors(*stack.hex_pos)]
        if adjacent:
            act["target"] = max(adjacent, key=threat)
            return act
        reach = cls.reachable(state, stack)
        best = None
        for e in sorted(enemies, key=lambda e: hex_distance(stack.hex_pos, e.hex_pos)):
            stands = [h for h in hex_neighbors(*e.hex_pos) if h in reach]
            if stands:
                stand = min(stands, key=lambda h: hex_distance(stack.hex_pos, h))
                best = (stand, e)
                break
        if best:
            act["path"] = cls.path_to(state, stack, best[0])
            act["target"] = best[1]
            return act
        # can't reach anyone this turn: get as close as possible to the nearest enemy
        nearest = min(enemies, key=lambda e: hex_distance(stack.hex_pos, e.hex_pos))
        if reach:
            dest = min(reach, key=lambda h: (hex_distance(h, nearest.hex_pos), hex_distance(h, stack.hex_pos)))
            if hex_distance(dest, nearest.hex_pos) < hex_distance(stack.hex_pos, nearest.hex_pos):
                act["path"] = cls.path_to(state, stack, dest)
                return act
        act["defend"] = True
        return act


def build_side(units, side, hero=None):
    """CombatStacks from an army/garrison list of CreatureStack|None (slot index kept).

    The commanding hero's primary stats, skills and artifacts are applied here, once
    at the start of each battle.
    """
    out = []
    for i, cs in enumerate(units):
        if cs and cs.count > 0:
            st = CombatStack(cs.creature, cs.count, cs.hp_remaining, side, slot=i)
            if hero:
                st.hero_attack, st.hero_defense = hero.stat("attack"), hero.stat("defense")
                st.hp_bonus = hero.artifact_bonus("hp")
                st.speed_bonus = hero.artifact_bonus("speed")
                st.melee_bonus = SK.skill_value(hero, "Offense") / 100
                st.ranged_bonus = SK.skill_value(hero, "Archery") / 100
                st.damage_reduction = SK.skill_value(hero, "Armorer") / 100
                st.luck = SK.skill_value(hero, "Luck")
                st.morale = SK.skill_value(hero, "Leadership") + SK.skill_value(hero, "Morale")
                if cs.hp_remaining >= CREATURES[cs.creature]["hp"]:
                    st.hp_remaining = st.unit_hp   # healthy units get the artifact bonus
            out.append(st)
    return out
