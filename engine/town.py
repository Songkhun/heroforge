"""Town entity: buildings, garrison, weekly creature growth and recruitment."""
import json
import random
from dataclasses import dataclass, field

from engine.creature import CreatureStack, CREATURES

# Shared building table {faction: {name: building}}. main.py's BUILDINGS is this dict.
BUILDINGS = {}


def load_buildings_data(json_path):
    with open(json_path) as f:
        data = json.load(f)
    BUILDINGS.clear()
    BUILDINGS.update(data)
    return BUILDINGS


def place_in(units, creature_key, count):
    """Merge `count` units into a 7-slot army list (matching stack first, else an empty
    slot). Returns False if there's no room."""
    for s in units:
        if s and s.creature == creature_key:
            s.count += count
            return True
    for i, s in enumerate(units):
        if s is None:
            units[i] = CreatureStack(creature_key, count)
            return True
    return False


@dataclass
class Town:
    faction: str
    name: str
    pos: tuple
    owner: str = "neutral"
    buildings: dict = field(default_factory=dict)   # name -> bool
    garrison: list = field(default_factory=lambda: [None] * 7)
    hero_in_town: str = None
    pool: dict = field(default_factory=dict)        # tier -> creatures available to recruit
    built_today: bool = False
    near_water: bool = False                         # set by world.new_game_state (shipyards)

    def defs(self):
        return BUILDINGS.get(self.faction, {})

    def has(self, name):
        return self.buildings.get(name, False)

    def build_status(self, building_name, player_resources):
        """'built' | 'locked' | 'built_today' | 'unaffordable' | 'available'."""
        b = self.defs()[building_name]
        if self.has(building_name):
            return "built"
        if self.missing_prereqs(building_name) or (b.get("requires_water") and not self.near_water):
            return "locked"
        if self.built_today:
            return "built_today"
        if self.deficit(building_name, player_resources):
            return "unaffordable"
        return "available"

    def missing_prereqs(self, building_name):
        return [p for p in self.defs()[building_name]["prerequisite"] if not self.has(p)]

    def deficit(self, building_name, player_resources):
        """{resource: amount short} for this building's cost."""
        cost = self.defs()[building_name]["cost"]
        return {r: amt - player_resources.get(r, 0) for r, amt in cost.items()
                if player_resources.get(r, 0) < amt}

    def can_build(self, building_name, player_resources):
        return (building_name in self.defs()
                and self.build_status(building_name, player_resources) == "available")

    def build(self, building_name):
        """Mark as built; returns the cost dict for the caller to deduct."""
        b = self.defs()[building_name]
        self.buildings[building_name] = True
        self.built_today = True
        if b["category"] == "dwelling" and not b.get("upgraded"):
            self.pool.setdefault(str(b["tier"]), CREATURES[b["provides_creature"]]["weekly_growth"])
        return dict(b["cost"])

    def dwellings(self):
        """{tier: [creature keys recruitable at that tier]} for built dwellings."""
        out = {}
        for name, b in self.defs().items():
            if b["category"] == "dwelling" and self.has(name):
                out.setdefault(b["tier"], []).append(b["provides_creature"])
        return out

    def available_to_recruit(self):
        """creature_key -> count. Base and upgraded units share a tier's pool."""
        return {key: self.pool.get(str(tier), 0)
                for tier, keys in self.dwellings().items() for key in keys}

    def recruit(self, creature_key, count, target=None):
        """Take units from the pool into `target` (an army list, e.g. a visiting hero's)
        or the garrison. Returns the gold cost for the caller to pay; {} if the pool is
        empty or there's no free/matching slot.
        """
        tier = str(CREATURES[creature_key]["tier"])
        count = min(count, self.pool.get(tier, 0))
        if count <= 0:
            return {}
        units = self.garrison if target is None else target
        if not place_in(units, creature_key, count):
            return {}
        self.pool[tier] -= count
        return {"gold": CREATURES[creature_key]["cost"] * count}

    def has_upgraded_dwelling(self, tier):
        return any(b["category"] == "dwelling" and b.get("upgraded") and b["tier"] == tier and self.has(n)
                   for n, b in self.defs().items())

    def mage_level(self):
        return max((b.get("mage_level", 0) for n, b in self.defs().items() if self.has(n)), default=0)

    def guild_spells(self, spells_table):
        """Spells offered by this town's Mage Guild: a fixed per-town pick for each level
        (3, 3, 2, 2, 1 spells for levels 1-5), only for levels already built."""
        per_level = {1: 3, 2: 3, 3: 2, 4: 2, 5: 1}
        rng = random.Random(self.name)
        out = []
        for lvl in range(1, self.mage_level() + 1):
            names = sorted(n for n, s in spells_table.items() if s["level"] == lvl)
            out += sorted(rng.sample(names, min(per_level[lvl], len(names))))
        return out

    def growth_bonus(self):
        return max((b.get("growth_bonus", 0) for n, b in self.defs().items() if self.has(n)), default=0)

    def weekly_growth(self, tier):
        """Units added to a tier's pool each week: base growth, +25% with the upgraded
        dwelling, then the Citadel/Castle bonus."""
        keys = self.dwellings().get(tier)
        if not keys:
            return 0
        base = next((k for k in keys if not CREATURES[k]["is_upgraded"]), keys[0])
        grow = CREATURES[base]["weekly_growth"]
        if self.has_upgraded_dwelling(tier):
            grow *= 1.25
        return int(grow * (1 + self.growth_bonus() / 100))

    def start_new_week(self):
        """Un-recruited units carry over; growth adds on top."""
        for tier in self.dwellings():
            self.pool[str(tier)] = self.pool.get(str(tier), 0) + self.weekly_growth(tier)

    def income_per_day(self):
        return max((b.get("income_gold", 0) for n, b in self.defs().items() if self.has(n)), default=0)

    def resource_income(self):
        """Daily non-gold income from buildings like the Resource Silo."""
        out = {}
        for n, b in self.defs().items():
            if self.has(n):
                for r, amt in b.get("income_res", {}).items():
                    out[r] = out.get(r, 0) + amt
        return out

    def fort_level(self):
        return max((b.get("fort_level", 0) for n, b in self.defs().items() if self.has(n)), default=0)

    def garrison_stacks(self):
        return [s for s in self.garrison if s and s.is_alive()]

    @classmethod
    def from_scenario(cls, d):
        t = cls(faction=d["faction"], name=d["name"], pos=tuple(d["pos"]),
                owner=d.get("owner", "neutral"))
        for name in t.defs():
            t.buildings[name] = False
        for name in d.get("buildings", []):
            t.buildings[name] = True
        for i, (key, count) in enumerate(d.get("garrison", [])[:7]):
            t.garrison[i] = CreatureStack(key, count)
        t.start_new_week()   # initial recruit pool
        return t
