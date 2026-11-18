"""JSON save/load of the whole game state.

The save holds everything needed to rebuild STATE without the scenario file: terrain,
explored tiles, every map object, heroes, towns, resources, calendar and stats.
"""
import json
import os

from engine import world
from engine.creature import CreatureStack
from engine.hero import Hero
from engine.map_objects import Mine, ArtifactObj, ResourcePile, Dwelling, NeutralStack, Obelisk
from engine.tile_map import TileMap
from engine.town import Town

SAVE_FILE = "heroforge_save.json"
SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SAVE_FILE)
VERSION = 1


def _stacks(units):
    return [s.to_dict() if s else None for s in units]


def _unstacks(data):
    return [CreatureStack.from_dict(d) if d else None for d in data]


def serialize_hero(h):
    return {
        "name": h.name, "faction": h.faction, "owner": h.owner,
        "level": h.level, "xp": h.xp, "xp_next": h.xp_next,
        "attack": h.attack, "defense": h.defense, "power": h.power, "knowledge": h.knowledge,
        "skills": dict(h.skills), "army": _stacks(h.army),
        "artifacts": dict(h.artifacts), "backpack": list(h.backpack), "spells": list(h.spells),
        "mana": h.mana, "mana_max": h.mana_max,
        "movement_points": h.movement_points, "movement_max": h.movement_max,
        "pos": list(h.pos), "levelup_queue": list(h.levelup_queue),
    }


def deserialize_hero(d):
    d = dict(d)
    d["army"] = _unstacks(d["army"])
    d["pos"] = tuple(d["pos"])
    return Hero(**d)


def serialize_town(t):
    return {"faction": t.faction, "name": t.name, "pos": list(t.pos), "owner": t.owner,
            "buildings": dict(t.buildings), "garrison": _stacks(t.garrison), "hero_in_town": t.hero_in_town,
            "pool": dict(t.pool), "built_today": t.built_today, "near_water": t.near_water}


def deserialize_town(d):
    d = dict(d)
    d["garrison"] = _unstacks(d["garrison"])
    d["pos"] = tuple(d["pos"])
    return Town(**d)


def serialize_obj(o):
    base = {"pos": list(o.pos)}
    if isinstance(o, Mine):
        return {**base, "type": "mine", "resource": o.resource_type, "owner": o.owner, "income": o.daily_income}
    if isinstance(o, ArtifactObj):
        return {**base, "type": "artifact", "name": o.artifact_name, "slot": o.slot_type, "bonus": o.bonus}
    if isinstance(o, ResourcePile):
        return {**base, "type": "resource_pile", "resource": o.resource_type, "amount": o.amount}
    if isinstance(o, Dwelling):
        return {**base, "type": "dwelling", "creature": o.creature_key, "available": o.available_count,
                "growth": o.weekly_growth}
    if isinstance(o, NeutralStack):
        return {**base, "type": "creature_stack", "creature": o.creature_key, "count": o.count,
                "aggressive": o.is_aggressive}
    if isinstance(o, Obelisk):
        return {**base, "type": "obelisk", "reveal_center": list(o.reveal_center), "radius": o.radius,
                "visited": o.visited}
    raise TypeError(f"can't save map object {o!r}")


def deserialize_obj(d):
    t, pos = d["type"], d["pos"]
    if t == "mine":
        return Mine(pos, d["resource"], d["owner"], d["income"])
    if t == "artifact":
        return ArtifactObj(pos, d["name"], d["slot"], d["bonus"])
    if t == "resource_pile":
        return ResourcePile(pos, d["resource"], d["amount"])
    if t == "dwelling":
        return Dwelling(pos, d["creature"], d["available"], d["growth"])
    if t == "creature_stack":
        return NeutralStack(pos, d["creature"], d["count"], d["aggressive"])
    if t == "obelisk":
        return Obelisk(pos, d["reveal_center"], d["radius"], d["visited"])
    raise ValueError(f"unknown map object type {t}")


def save_game(state, path=SAVE_PATH):
    tm = state["tile_map"]
    data = {
        "version": VERSION,
        "day": state["day"], "week": state["week"], "month": state["month"],
        "turn": state["turn"], "game_phase": state["game_phase"],
        "selected_hero_idx": state.get("selected_hero_idx", 0),
        "player_resources": state["player_resources"],
        "enemy_resources": state["enemy_resources"],
        "stats": state.get("stats", {}),
        "player_heroes": [serialize_hero(h) for h in state["player_heroes"]],
        "enemy_heroes": [serialize_hero(h) for h in state["enemy_heroes"]],
        "towns": [serialize_town(t) for t in state["towns"]],
        "map_objects": [serialize_obj(o) for o in state["map_objects"]],
        "terrain": [[tm.get(x, y).terrain_type for x in range(tm.w)] for y in range(tm.h)],
        "tile_explored": [[tm.get(x, y).is_explored for x in range(tm.w)] for y in range(tm.h)],
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)   # never leave a half-written save behind
    return path


def load_game(path=SAVE_PATH):
    """Rebuild a STATE dict from the save file; None if there is no save."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    tm = TileMap(data["terrain"])
    for y, row in enumerate(data["tile_explored"]):
        for x, explored in enumerate(row):
            if explored:
                tm.grid[y][x] = tm.grid[y][x]._replace(is_explored=True)
    towns = [deserialize_town(d) for d in data["towns"]]
    objs = [deserialize_obj(d) for d in data["map_objects"]]
    for t in towns:
        tm.set_object(*t.pos, "town", t)
    for o in objs:
        tm.set_object(*o.pos, o.object_type, o)
    state = {
        "player_resources": data["player_resources"],
        "enemy_resources": data["enemy_resources"],
        "player_heroes": [deserialize_hero(d) for d in data["player_heroes"]],
        "enemy_heroes": [deserialize_hero(d) for d in data["enemy_heroes"]],
        "towns": towns, "map_objects": objs, "tile_map": tm,
        "day": data["day"], "week": data["week"], "month": data["month"],
        "turn": data.get("turn", "player"), "game_phase": data.get("game_phase", "playing"),
        "selected_hero_idx": data.get("selected_hero_idx", 0),
        "stats": {**world.default_stats(), **data.get("stats", {})},
    }
    world.update_fog(state)
    return state
