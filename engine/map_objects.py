"""Adventure-map objects. All block movement; heroes interact from an adjacent tile."""
from config import MINE_INCOME
from engine.creature import CREATURES, plural


class MapObject:
    object_type = "object"
    is_passable = False

    def __init__(self, pos):
        self.pos = tuple(pos)

    def label(self):
        return self.object_type.replace("_", " ").title()


class Mine(MapObject):
    def __init__(self, pos, resource_type, owner=None, daily_income=None):
        super().__init__(pos)
        self.resource_type = resource_type
        self.owner = owner
        self.daily_income = daily_income if daily_income is not None else MINE_INCOME[resource_type]
        self.object_type = f"{resource_type}_mine"

    def label(self):
        who = {"player": "yours", "enemy": "enemy"}.get(self.owner, "unclaimed")
        return f"{self.resource_type.title()} Mine (+{self.daily_income}/day, {who})"


class ArtifactObj(MapObject):
    object_type = "artifact"

    def __init__(self, pos, artifact_name, slot_type, bonus_dict):
        super().__init__(pos)
        self.artifact_name = artifact_name
        self.slot_type = slot_type
        self.bonus = dict(bonus_dict)

    def as_item(self):
        return {"name": self.artifact_name, "slot": self.slot_type, "bonus": dict(self.bonus)}

    def label(self):
        bonus = ", ".join(f"+{v} {k}" for k, v in self.bonus.items())
        return f"{self.artifact_name} ({bonus})"


class ResourcePile(MapObject):
    object_type = "resource_pile"

    def __init__(self, pos, resource_type, amount):
        super().__init__(pos)
        self.resource_type = resource_type
        self.amount = amount

    def label(self):
        return f"{self.amount} {self.resource_type}"


class Dwelling(MapObject):
    object_type = "dwelling"

    def __init__(self, pos, creature_key, available_count, weekly_growth):
        super().__init__(pos)
        self.creature_key = creature_key
        self.available_count = available_count
        self.weekly_growth = weekly_growth

    def label(self):
        return f"{CREATURES[self.creature_key]['name']} Dwelling ({self.available_count} available)"


class Obelisk(MapObject):
    """Visiting reveals a region of the map (centered on `reveal_center`)."""
    object_type = "obelisk"

    def __init__(self, pos, reveal_center, radius=7, visited=False):
        super().__init__(pos)
        self.reveal_center = tuple(reveal_center)
        self.radius = radius
        self.visited = visited

    def label(self):
        return "Obelisk (visited)" if self.visited else "Obelisk — visit to reveal a distant region"


def size_word(n):
    for limit, word in [(4, "A few"), (9, "Several"), (19, "A pack of"), (49, "Lots of"),
                        (99, "A horde of"), (249, "A throng of")]:
        if n <= limit:
            return word
    return "A legion of"


class NeutralStack(MapObject):
    object_type = "creature_stack"

    def __init__(self, pos, creature_key, count, is_aggressive=True):
        super().__init__(pos)
        self.creature_key = creature_key
        self.count = count
        self.is_aggressive = is_aggressive

    def label(self):
        return f"{size_word(self.count)} {plural(CREATURES[self.creature_key]['name'])}"
