"""Hero entity: stats, army, artifacts, spells, movement, level-ups."""
import json
import random
from dataclasses import dataclass, field

from config import HERO_BASE_MOVEMENT
from engine.creature import CreatureStack, CREATURES
from engine import skills as SK

ARTIFACT_SLOTS = ["head", "neck", "torso", "cloak", "hand_r", "hand_l",
                  "ring1", "ring2", "boot", "misc1", "misc2"]
# generic slot type in artifacts.json -> concrete hero slots it may occupy
SLOT_TYPES = {"hand": ["hand_r", "hand_l"], "ring": ["ring1", "ring2"], "misc": ["misc1", "misc2"]}
PRIMARY_STATS = ["attack", "defense", "power", "knowledge"]
# chance that a level-up raises attack/defense (otherwise power/knowledge)
MIGHT_CHANCE = {"castle": 0.6, "necropolis": 0.5}
HERO_CLASS = {"castle": "Knight", "necropolis": "Death Knight"}

# Shared artifact table (main.ARTIFACTS is this dict).
ARTIFACTS = {}


def load_artifacts_data(json_path):
    with open(json_path) as f:
        data = json.load(f)
    ARTIFACTS.clear()
    ARTIFACTS.update(data)
    return ARTIFACTS


def artifact_item(name):
    """Artifact dict as carried by a hero: {name, slot, bonus, special}."""
    a = ARTIFACTS[name]
    return {"name": name, "slot": a["slot"], "bonus": dict(a["bonus"]), "special": a.get("special", "")}


def xp_for_level(level):
    """Total XP needed to go from `level` to `level + 1`: 1000, 2400, 4320, 6912, ..."""
    return round(1000 * level * 1.2 ** (level - 1))


@dataclass
class Hero:
    name: str
    faction: str
    owner: str = "player"
    level: int = 1
    xp: int = 0
    xp_next: int = 1000
    attack: int = 1
    defense: int = 1
    power: int = 1
    knowledge: int = 1
    skills: dict = field(default_factory=dict)
    army: list = field(default_factory=lambda: [None] * 7)
    artifacts: dict = field(default_factory=lambda: {s: None for s in ARTIFACT_SLOTS})
    backpack: list = field(default_factory=list)   # artifacts whose slot was full
    spells: list = field(default_factory=list)
    mana: int = 0
    mana_max: int = 0
    movement_points: int = 0
    movement_max: int = 0
    pos: tuple = (0, 0)
    levelup_queue: list = field(default_factory=list)   # pending level-up choices (player heroes)

    @property
    def pending_levelups(self):
        return len(self.levelup_queue)

    @property
    def hero_class(self):
        return HERO_CLASS.get(self.faction, "Hero")

    # ── derived stats ──
    def artifact_bonus(self, stat):
        return sum((a or {}).get("bonus", {}).get(stat, 0) for a in self.artifacts.values())

    def stat(self, name):
        """Primary stat including artifact bonuses."""
        return getattr(self, name) + self.artifact_bonus(name)

    def compute_mana_max(self):
        return self.stat("knowledge") * 10 + self.artifact_bonus("mana")

    # ── army ──
    def add_to_army(self, creature_key, count):
        """Merge into a matching stack, else use the first empty slot. False if no room."""
        for s in self.army:
            if s and s.creature == creature_key:
                s.count += count
                return True
        for i, s in enumerate(self.army):
            if s is None:
                self.army[i] = CreatureStack(creature_key, count)
                return True
        return False

    def remove_from_army(self, slot_idx):
        stack = self.army[slot_idx]
        self.army[slot_idx] = None
        return stack

    def stacks(self):
        return [s for s in self.army if s and s.is_alive()]

    def army_hp(self):
        return sum(s.total_hp() for s in self.stacks())

    def army_power(self):
        """Rough strength estimate used by the AI: sum of attack x hp x count."""
        return sum(CREATURES[s.creature]["attack"] * CREATURES[s.creature]["hp"] * s.count
                   for s in self.stacks())

    # ── movement ──
    def has_movement(self):
        return self.movement_points > 0

    def spend_movement(self, cost):
        self.movement_points = max(0, self.movement_points - cost)

    def compute_movement_max(self):
        """Base points + slowest-creature bonus, scaled by Logistics, plus artifacts.

        Per-tile terrain cost is applied when moving (TileMap.movement_cost).
        """
        stacks = self.stacks()
        slowest = min((CREATURES[s.creature]["speed"] for s in stacks), default=5)
        pts = HERO_BASE_MOVEMENT + max(0, min(slowest, 11) - 3)
        pts = int(pts * (1 + SK.skill_value(self, "Logistics") / 100))
        return pts + self.artifact_bonus("movement")

    def refresh_movement(self):
        self.movement_max = self.compute_movement_max()
        self.movement_points = self.movement_max

    def vision(self, base):
        return base + SK.skill_value(self, "Scouting")

    # ── progression ──
    def gain_xp(self, amount):
        """Add XP; returns number of levels gained."""
        self.xp += int(amount)
        gained = 0
        while self.xp >= self.xp_next:
            self.level_up()
            gained += 1
        return gained

    def level_up(self, stat=None):
        """Raise level and one primary stat (faction-weighted), then queue a skill choice.

        Player heroes get a popup (levelup_queue); computer heroes pick immediately.
        Returns the level-up record.
        """
        self.level += 1
        self.xp_next = xp_for_level(self.level)
        if stat is None:
            pair = ("attack", "defense") if random.random() < MIGHT_CHANCE.get(self.faction, 0.5) else ("power", "knowledge")
            stat = random.choice(pair)
        setattr(self, stat, getattr(self, stat) + 1)
        self.mana_max = self.compute_mana_max()
        cands = SK.candidate_skills(self)
        record = {"level": self.level, "stat": stat, "value": getattr(self, stat),
                  "options": random.sample(cands, min(3, len(cands)))}
        if self.owner == "player":
            self.levelup_queue.append(record)
        elif record["options"]:
            self.learn_skill(self.ai_pick_skill(record["options"]))
        return record

    def ai_pick_skill(self, options):
        """Computer heroes prefer upgrading what they have, then combat skills."""
        pref = ["Offense", "Armorer", "Leadership", "Archery", "Luck", "Morale", "Wisdom",
                "Earth Magic", "Logistics", "Tactics", "Fire Magic", "Air Magic", "Water Magic",
                "Scouting", "Eagle Eye"]
        return min(options, key=lambda n: (n not in self.skills, pref.index(n) if n in pref else 99))

    def learn_skill(self, name):
        """New skill at Basic, or raise an existing one (max Expert). False if not possible."""
        if name in self.skills:
            if self.skills[name] >= 3:
                return False
            self.skills[name] += 1
        else:
            if len(self.skills) >= SK.MAX_SKILLS:
                return False
            self.skills[name] = 1
        if name == "Logistics":
            self.movement_max = self.compute_movement_max()
        return True

    # ── magic ──
    def can_learn_spell(self, spell):
        return spell["level"] <= SK.max_spell_level(self)

    def add_spell(self, spell_name):
        if spell_name not in self.spells:
            self.spells.append(spell_name)

    def spend_mana(self, amount):
        if self.mana < amount:
            return False
        self.mana -= amount
        return True

    def restore_mana(self):
        self.mana_max = self.compute_mana_max()
        self.mana = self.mana_max

    # ── artifacts ──
    def equip(self, artifact):
        """Put an artifact dict ({name, slot, bonus}) in a free matching slot, else the backpack.

        Returns the hero slot used, or None if it went to the backpack.
        """
        slot = artifact.get("slot")
        for s in SLOT_TYPES.get(slot, [slot]):
            if s in self.artifacts and self.artifacts[s] is None:
                self.artifacts[s] = artifact
                self._artifacts_changed()
                return s
        self.backpack.append(artifact)
        return None

    def equip_from_backpack(self, idx):
        """Wear a backpack item, swapping out whatever is in its first slot."""
        art = self.backpack.pop(idx)
        slots = SLOT_TYPES.get(art["slot"], [art["slot"]])
        target = next((s for s in slots if self.artifacts.get(s) is None), slots[0])
        old = self.artifacts.get(target)
        self.artifacts[target] = art
        if old:
            self.backpack.append(old)
        self._artifacts_changed()

    def unequip(self, slot):
        art = self.artifacts.get(slot)
        if art:
            self.artifacts[slot] = None
            self.backpack.append(art)
            self._artifacts_changed()

    def _artifacts_changed(self):
        self.mana_max = self.compute_mana_max()
        self.mana = min(self.mana, self.mana_max)
        self.movement_max = self.compute_movement_max()

    @classmethod
    def from_scenario(cls, d):
        h = cls(name=d["name"], faction=d["faction"], owner=d.get("owner", "player"),
                attack=d.get("attack", 1), defense=d.get("defense", 1),
                power=d.get("power", 1), knowledge=d.get("knowledge", 1),
                skills=dict(d.get("skills", {})), spells=list(d.get("spells", [])),
                pos=tuple(d["pos"]))
        for key, count in d.get("army", []):
            h.add_to_army(key, count)
        h.xp_next = xp_for_level(h.level)
        h.restore_mana()
        h.refresh_movement()
        return h
