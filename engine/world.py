"""World-level rules shared by the player UI and the AI: new game, fog, map interactions,
battle results, end of turn and victory."""
from config import START_RESOURCES, VISION_RADIUS
from engine.creature import CreatureStack, CREATURES
from engine.hero import Hero, ARTIFACTS, artifact_item
from engine.map_objects import Mine, ArtifactObj, ResourcePile, NeutralStack, Obelisk
from engine.resource_manager import ResourceManager as RM
from engine.tile_map import TileMap
from engine.town import Town

TOWN_VISION = 4


def new_game_state(scenario):
    """Fresh STATE contents from scenario.json data."""
    tm = TileMap.from_scenario(scenario)
    towns = [Town.from_scenario(d) for d in scenario["towns"]]
    objs = []
    objs += [Mine(d["pos"], d["resource"]) for d in scenario["mines"]]
    for d in scenario["artifacts"]:
        a = ARTIFACTS[d["name"]]
        objs.append(ArtifactObj(d["pos"], d["name"], a["slot"], a["bonus"]))
    objs += [ResourcePile(d["pos"], d["resource"], d["amount"]) for d in scenario["resources"]]
    objs += [NeutralStack(d["pos"], d["creature"], d["count"]) for d in scenario["creatures"]]
    objs += [Obelisk(d["pos"], d["reveal_center"], d.get("radius", 7)) for d in scenario.get("obelisks", [])]
    for t in towns:
        tm.set_object(*t.pos, "town", t)
        x, y = t.pos
        t.near_water = any(tm.in_bounds(x + dx, y + dy) and tm.get(x + dx, y + dy).terrain_type == "water"
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    for o in objs:
        tm.set_object(*o.pos, o.object_type, o)
    heroes = [Hero.from_scenario(d) for d in scenario["heroes"]]
    state = {
        "player_resources": dict(START_RESOURCES),
        "enemy_resources": dict(START_RESOURCES),
        "player_heroes": [h for h in heroes if h.owner == "player"],
        "enemy_heroes": [h for h in heroes if h.owner == "enemy"],
        "towns": towns,
        "map_objects": objs,
        "tile_map": tm,
        "day": 1, "week": 1, "month": 1,
        "turn": "player",
        "selected_hero_idx": 0,
        "game_phase": "playing",
        "stats": default_stats(),
    }
    for h in heroes:
        sync_hero_in_town(state, h)
    update_fog(state)
    return state


def default_stats():
    return {"battles_won": 0, "battles_lost": 0, "enemy_heroes_defeated": 0,
            "creatures_killed": 0, "towns_captured": 0, "mines_captured": 0}


def days_played(state):
    return (state["month"] - 1) * 28 + (state["week"] - 1) * 7 + state["day"]


# ─────────────────────────── queries ───────────────────────────

def update_fog(state):
    """Player vision: each hero (radius + Scouting) plus owned towns."""
    sources = [(h.pos, h.vision(VISION_RADIUS)) for h in state["player_heroes"]]
    sources += [(t.pos, TOWN_VISION) for t in state["towns"] if t.owner == "player"]
    state["tile_map"].update_fog([], VISION_RADIUS, sources)


def town_at(state, pos):
    return next((t for t in state["towns"] if t.pos == tuple(pos)), None)


def hero_at(state, pos):
    pos = tuple(pos)
    return next((h for h in state["player_heroes"] + state["enemy_heroes"] if h.pos == pos), None)


def heroes_of(state, owner):
    return state[f"{owner}_heroes"]


def sync_hero_in_town(state, hero):
    """Keep Town.hero_in_town in step with hero positions."""
    for t in state["towns"]:
        if t.hero_in_town == hero.name and t.pos != hero.pos:
            t.hero_in_town = None
        elif t.pos == hero.pos:
            t.hero_in_town = hero.name


def remove_object(state, obj):
    state["tile_map"].remove_object(*obj.pos)
    if obj in state["map_objects"]:
        state["map_objects"].remove(obj)


def remove_hero(state, hero):
    for key in ("player_heroes", "enemy_heroes"):
        if hero in state[key]:
            state[key].remove(hero)
    for t in state["towns"]:
        if t.hero_in_town == hero.name:
            t.hero_in_town = None
    if state["player_heroes"]:
        state["selected_hero_idx"] = min(max(0, state.get("selected_hero_idx", 0)), len(state["player_heroes"]) - 1)
    else:
        state["selected_hero_idx"] = -1


def is_interaction(state, pos, mover_owner):
    """Tiles a hero acts on from the neighboring tile instead of walking onto."""
    tile = state["tile_map"].get(*pos)
    if hero_at(state, pos):
        return True
    if tile.object_type == "town":
        t = tile.object_data
        return t.owner != mover_owner and bool(t.garrison_stacks())
    return tile.object_type is not None


# ─────────────────────────── map interactions ───────────────────────────

def visit_mage_guild(state, hero, town, spells_table):
    """A hero in a town with a Mage Guild learns its spells (up to its Wisdom limit) and
    refills mana. Returns (learned, too_advanced) spell name lists."""
    if not town.mage_level():
        return [], []
    learned, blocked = [], []
    for s in town.guild_spells(spells_table):
        if s in hero.spells:
            continue
        if hero.can_learn_spell(spells_table[s]):
            hero.add_spell(s)
            learned.append(s)
        else:
            blocked.append(s)
    hero.restore_mana()
    return learned, blocked


def capture_town(state, town, owner):
    if town.owner == owner:
        return False
    town.owner = owner
    if owner == "player":
        state["stats"]["towns_captured"] += 1
    update_fog(state)
    return True


def visit_object(state, hero, pos):
    """Peaceful interaction with the object at `pos` (mine, artifact, pile).

    Returns a list of (text, kind) events; kind is a color hint for the UI:
    gain | artifact | info. Combat objects are handled by the caller.
    """
    tile = state["tile_map"].get(*pos)
    obj = tile.object_data
    res = state[f"{hero.owner}_resources"]
    if isinstance(obj, Mine):
        if obj.owner == hero.owner:
            return [("You already own this mine.", "info")]
        obj.owner = hero.owner
        res[obj.resource_type] += obj.daily_income
        if hero.owner == "player":
            state["stats"]["mines_captured"] += 1
        return [(f"Mine captured! +{obj.daily_income} {obj.resource_type} now and every day.", "gain")]
    if isinstance(obj, ArtifactObj):
        item = artifact_item(obj.artifact_name) if obj.artifact_name in ARTIFACTS else obj.as_item()
        slot = hero.equip(item)
        remove_object(state, obj)
        where = "" if slot else " (to the backpack)"
        return [(f"{hero.name} found the {obj.label()}{where}!", "artifact")]
    if isinstance(obj, ResourcePile):
        res[obj.resource_type] += obj.amount
        remove_object(state, obj)
        return [(f"Picked up {obj.amount} {obj.resource_type}.", "gain")]
    if isinstance(obj, Obelisk):
        if obj.visited:
            return [("This obelisk's secrets are already known.", "info")]
        obj.visited = True
        if hero.owner == "player":
            n = state["tile_map"].reveal(obj.reveal_center, obj.radius)
            update_fog(state)
            return [(f"The obelisk shows a distant land ({n} tiles revealed).", "artifact")]
        return []
    if obj is not None and hasattr(obj, "label"):
        return [(obj.label(), "info")]
    return []


# ─────────────────────────── battles ───────────────────────────

def apply_battle_result(state, cstate, attacker, defender_hero=None, neutral=None, town=None,
                        winner="attacker", retreated=None):
    """Write a finished battle back to the world. Used by the combat screen and auto-battles.

    winner: "attacker" | "defender". retreated: side that fled (it loses its army, its hero lives).
    Returns messages written from the player's point of view.
    """
    from engine.combat_engine import CombatEngine as CE
    msgs = []
    loser = "defender" if winner == "attacker" else "attacker"
    sides = {"attacker": cstate.attacker_stacks, "defender": cstate.defender_stacks}
    heroes = {"attacker": attacker, "defender": defender_hero}

    def write_back(units, stacks):
        for s in stacks:
            if s.is_alive:
                hp = min(s.hp_remaining, CREATURES[s.creature_key]["hp"])
                units[s.slot] = CreatureStack(s.creature_key, s.count, hp)
            else:
                units[s.slot] = None

    # survivors
    for side in ("attacker", "defender"):
        h = heroes[side]
        if side == retreated and h:
            h.army = [None] * 7
            if h.owner == "player":
                msgs.append(f"{h.name} fled the battle, abandoning the army.")
        elif h:
            write_back(h.army, sides[side])
        elif town:
            write_back(town.garrison, sides[side])
        elif neutral:
            neutral.count = sum(s.count for s in sides[side])

    win_hero, lose_hero = heroes[winner], heroes[loser]
    player_won = (win_hero.owner if win_hero else
                  (town.owner if town and winner == "defender" else "neutral")) == "player"
    player_fought = any(h and h.owner == "player" for h in heroes.values()) or (town and town.owner == "player")
    # experience for the winner
    xp = CE.xp_for_kills(sides[loser])
    if win_hero:
        levels = win_hero.gain_xp(xp)
        if win_hero.owner == "player":
            msgs.append(f"Victory! {win_hero.name} gains {xp} XP.")
            if levels:
                msgs.append(f"{win_hero.name} reached level {win_hero.level}!")
    elif player_won:
        msgs.append(f"{town.name}'s garrison held the walls!")
    # the loser's hero (unless it fled), the neutral stack, the town
    if lose_hero and loser != retreated:
        remove_hero(state, lose_hero)
        msgs.append(f"{lose_hero.name} has been defeated!" if lose_hero.owner != "player"
                    else f"{lose_hero.name} was defeated in battle.")
        if lose_hero.owner == "enemy" and player_won:
            state["stats"]["enemy_heroes_defeated"] += 1
    if neutral and winner == "attacker":
        remove_object(state, neutral)
    if town and winner == "attacker":
        if capture_town(state, town, attacker.owner):
            msgs.append(f"{town.name} is now yours!" if attacker.owner == "player"
                        else f"{town.name} has fallen to {attacker.name}!")
    if player_fought:
        state["stats"]["battles_won" if player_won else "battles_lost"] += 1
        enemy_side = loser if player_won else winner
        state["stats"]["creatures_killed"] += sum(s.killed for s in sides[enemy_side])
    update_fog(state)
    return msgs


def auto_battle(state, attacker, defender_hero=None, neutral=None, town=None):
    """Resolve a battle instantly (AI vs neutrals / AI vs AI). Returns (winner, msgs)."""
    from engine.combat_engine import CombatEngine as CE, CombatState, build_side
    cs = CombatState(attacker_hero=attacker, defender_hero=defender_hero, player_side="none")
    cs.attacker_stacks = build_side(attacker.army, "attacker", attacker)
    if defender_hero:
        cs.defender_stacks = build_side(defender_hero.army, "defender", defender_hero)
    elif neutral:
        cs.defender_stacks = build_side([CreatureStack(neutral.creature_key, neutral.count)], "defender")
    else:
        cs.defender_stacks = build_side(town.garrison, "defender")
    CE.setup_positions(cs)
    winner = CE.auto_resolve(cs)
    return winner, apply_battle_result(state, cs, attacker, defender_hero, neutral, town, winner)


# ─────────────────────────── turns ───────────────────────────

def collect_income(state, owner):
    """One day of income for `owner` from towns and mines. Returns the gains dict."""
    res = state[f"{owner}_resources"]
    gains = RM.apply_daily_income(res, state["map_objects"], owner)
    for t in state["towns"]:
        if t.owner == owner:
            town_income = {"gold": t.income_per_day(), **t.resource_income()}
            RM.add(res, town_income)
            for r, amt in town_income.items():
                if amt:
                    gains[r] = gains.get(r, 0) + amt
    return gains


def advance_calendar(state):
    """Next day. Returns True when a new week starts."""
    state["day"] += 1
    if state["day"] <= 7:
        return False
    state["day"] = 1
    state["week"] += 1
    if state["week"] > 4:
        state["week"] = 1
        state["month"] += 1
    return True


def begin_enemy_phase(state):
    state["turn"] = "enemy"
    for h in state["enemy_heroes"]:
        h.refresh_movement()


def finish_end_turn(state):
    """After the enemy has moved: calendar, weekly growth, income, refresh. Returns messages."""
    msgs = []
    state["turn"] = "player"
    new_week = advance_calendar(state)
    for t in state["towns"]:
        t.built_today = False
    if new_week:
        # Weekly event after day 7: creature growth, mana for heroes resting in a town
        for t in state["towns"]:
            t.start_new_week()
        for h in state["player_heroes"] + state["enemy_heroes"]:
            if town_at(state, h.pos):
                h.restore_mana()
        msgs.append(f"Week {state['week']} begins: creatures have multiplied!")
    gains = collect_income(state, "player")
    collect_income(state, "enemy")
    if gains:
        msgs.append("Income: " + ", ".join(f"+{v} {k}" for k, v in gains.items()))
    for h in state["player_heroes"]:
        h.refresh_movement()
        h.mana = min(h.mana_max, h.mana + 1)
    update_fog(state)
    return msgs


def end_turn(state):
    """Whole end of turn without a UI: the enemy's battles are auto-resolved."""
    from engine import ai_player
    begin_enemy_phase(state)
    msgs = ai_player.take_turn(state)
    return msgs + finish_end_turn(state)


def check_victory(state):
    """None | "player" | "enemy". A side is alive while it has a hero or a town."""
    player_alive = bool(state["player_heroes"]) or any(t.owner == "player" for t in state["towns"])
    enemy_alive = bool(state["enemy_heroes"]) or any(t.owner == "enemy" for t in state["towns"])
    if not enemy_alive:
        return "player"
    if not player_alive:
        return "enemy"
    return None
