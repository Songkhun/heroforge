"""CreatureStack: a number of identical units, the top unit possibly wounded."""
import json
from dataclasses import dataclass

# Shared creature table. main.py's CREATURES is this same dict object.
CREATURES = {}


def load_creatures_data(json_path):
    """Load creatures.json once at startup; fills and returns the shared CREATURES dict."""
    with open(json_path) as f:
        data = json.load(f)
    CREATURES.clear()
    CREATURES.update(data)
    return CREATURES


def plural(name):
    if name.endswith("man"):
        return name[:-3] + "men"
    if name.endswith("Dead"):
        return name
    if name.endswith(("ch", "sh", "s")):
        return name + "es"
    return name + "s"


def unit_name(key, count):
    """'1 Pikeman' / '12 Pikemen' style naming for a creature key."""
    name = CREATURES[key]["name"]
    return name if count == 1 else plural(name)


@dataclass
class CreatureStack:
    creature: str
    count: int
    hp_remaining: int = 0   # HP of the top unit; 0 means "full"

    def __post_init__(self):
        if self.hp_remaining <= 0:
            self.hp_remaining = self.unit_hp

    @property
    def data(self):
        return CREATURES[self.creature]

    @property
    def unit_hp(self):
        return CREATURES[self.creature]["hp"]

    @property
    def name(self):
        return self.data["name"]

    def take_damage(self, amount):
        """Apply damage; returns the number of units killed."""
        amount = max(0, int(amount))
        if amount <= 0 or self.count <= 0:
            return 0
        total = self.total_hp()
        if amount >= total:
            killed = self.count
            self.count = 0
            self.hp_remaining = 0
            return killed
        remaining = total - amount
        new_count = (remaining + self.unit_hp - 1) // self.unit_hp
        killed = self.count - new_count
        self.count = new_count
        self.hp_remaining = remaining - (new_count - 1) * self.unit_hp
        return killed

    def is_alive(self):
        return self.count > 0

    def hp_percent(self):
        return self.hp_remaining / self.unit_hp if self.count else 0.0

    def total_hp(self):
        if self.count <= 0:
            return 0
        return (self.count - 1) * self.unit_hp + self.hp_remaining

    def clone(self):
        return CreatureStack(self.creature, self.count, self.hp_remaining)

    def to_dict(self):
        return {"creature": self.creature, "count": self.count, "hp_remaining": self.hp_remaining}

    @classmethod
    def from_dict(cls, d):
        return cls(d["creature"], d["count"], d.get("hp_remaining", 0))
