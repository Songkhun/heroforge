"""Computer opponent for the adventure map.

AIPlayer.run_turn() is a generator of events so the UI can show the enemy moving and stop
for battles the player must fight:
    ("step", hero, pos)    an enemy hero moved one tile
    ("combat", kwargs)     a battle involving the player: kwargs for SM.go("combat_screen", ...)
    ("msg", text)          something the player should hear about
After a "combat" event the consumer fights the battle, then resumes the generator.
take_turn(state) runs a whole turn headlessly, auto-resolving those battles.
"""
from engine import world
from engine.combat_engine import SPELLS, CombatEngine
from engine.creature import CREATURES
from engine.map_objects import Mine, ArtifactObj, ResourcePile, NeutralStack
from engine.resource_manager import ResourceManager as RM

OWNER = "enemy"
ATTACK_RANGE = 12       # tiles: consider attacking player heroes this close
LOOT_RANGE = 8          # tiles: go for mines / piles / artifacts this close
NEUTRAL_RANGE = 6       # tiles: fight much weaker neutral stacks this close


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def stack_power(key, count):
    c = CREATURES[key]
    return c["attack"] * c["hp"] * count


def estimate_max_power(faction):
    """Power of a 'healthy' army: one week's growth of the faction's tier 1-4 base units."""
    return sum(stack_power(k, c["weekly_growth"]) for k, c in CREATURES.items()
               if c["faction"] == faction and not c["is_upgraded"] and c["tier"] <= 4)


class AIPlayer:
    def __init__(self, state):
        self.state = state

    # ─────────────────────────── helpers ───────────────────────────
    @property
    def res(self):
        return self.state[f"{OWNER}_resources"]

    def alive(self, hero):
        return hero in self.state["enemy_heroes"]

    def blocked_for(self, hero):
        return {h.pos for h in self.state["player_heroes"] + self.state["enemy_heroes"] if h is not hero}

    def path(self, hero, target):
        return self.state["tile_map"].find_path(hero.pos, target, self.blocked_for(hero))

    def nearest_reachable(self, hero, targets, max_dist=None):
        """Closest target (by path length) among `targets` [(pos, payload)]."""
        best = None
        for pos, payload in sorted(targets, key=lambda t: manhattan(hero.pos, t[0])):
            if max_dist is not None and manhattan(hero.pos, pos) > max_dist:
                break
            p = self.path(hero, pos)
            if p and (best is None or len(p) < len(best[2])):
                best = (pos, payload, p)
                if len(p) <= manhattan(hero.pos, pos) + 2:
                    break   # close to optimal already
        return best

    # ─────────────────────────── turn ───────────────────────────
    def run_turn(self):
        S = self.state
        for town in [t for t in S["towns"] if t.owner == OWNER]:
            self.build_in(town)
            if S["day"] == 7 and not town.hero_in_town:
                # end of week: spare gold (above a reserve) goes into the garrison
                for key, n in self.recruit_plan(town, max(0, self.res["gold"] - 3000)):
                    spent = town.recruit(key, n)
                    if spent:
                        RM.spend(self.res, spent)
        for hero in sorted(list(S["enemy_heroes"]), key=lambda h: h.army_power(), reverse=True):
            done_town = False
            for _ in range(12):   # action budget per hero
                if not self.alive(hero) or hero.movement_points <= 0:
                    break
                action = self.choose_action(hero, done_town)
                if action["type"] == "recruit_and_build":
                    for ev in self.recruit_and_build(hero, action["town"]):
                        yield ev
                    done_town = True
                    continue
                if action["type"] == "wait":
                    break
                progressed = yield from self.execute_move(hero, action["target"])
                if not progressed:
                    break

    def choose_action(self, hero, done_town):
        S = self.state
        here = world.town_at(S, hero.pos)
        # 1. in our own town: recruit and build
        if here and here.owner == OWNER and not done_town:
            return {"type": "recruit_and_build", "town": here}
        power = hero.army_power()
        own_towns = [t for t in S["towns"] if t.owner == OWNER]
        # 2. weak army: go home to restock
        if power < estimate_max_power(hero.faction) * 0.3 and own_towns and not here:
            best = self.nearest_reachable(hero, [(t.pos, t) for t in own_towns])
            if best:
                return {"type": "move_toward", "target": best[0], "reason": "restock"}
        # 2b. a nearby town has enough affordable recruits to be worth the trip
        if not here:
            worth = [(t.pos, t) for t in own_towns if manhattan(hero.pos, t.pos) <= 12
                     and self.recruit_value(t) > max(power, 1) * 0.4]
            best = self.nearest_reachable(hero, worth)
            if best:
                return {"type": "move_toward", "target": best[0], "reason": "restock"}
        # 3. a player hero nearby and we're stronger: attack
        foes = [(h.pos, h) for h in S["player_heroes"]
                if manhattan(hero.pos, h.pos) <= ATTACK_RANGE and power > h.army_power() * 0.8]
        best = self.nearest_reachable(hero, foes)
        if best:
            return {"type": "move_toward", "target": best[0], "reason": "attack_hero"}
        # 4. grab mines we don't own, resource piles and artifacts close by
        loot = [(o.pos, o) for o in S["map_objects"]
                if (isinstance(o, Mine) and o.owner != OWNER) or isinstance(o, (ResourcePile, ArtifactObj))]
        best = self.nearest_reachable(hero, loot, LOOT_RANGE)
        if best:
            return {"type": "move_toward", "target": best[0], "reason": "loot"}
        # 5. clear much weaker neutral stacks for experience
        weak = [(o.pos, o) for o in S["map_objects"] if isinstance(o, NeutralStack)
                and stack_power(o.creature_key, o.count) * 1.5 < power]
        best = self.nearest_reachable(hero, weak, NEUTRAL_RANGE)
        if best:
            return {"type": "move_toward", "target": best[0], "reason": "neutral"}
        # 6. march on the player's towns, or neutral towns we can take
        towns = [(t.pos, t) for t in S["towns"] if t.owner == "player" or (
            t.owner == "neutral" and sum(stack_power(s.creature, s.count) for s in t.garrison_stacks()) * 1.3 < power)]
        best = self.nearest_reachable(hero, towns)
        if best:
            return {"type": "move_toward", "target": best[0], "reason": "attack_town"}
        # 7. nothing worth doing (the AI sees the whole map, so there's nothing to explore)
        return {"type": "wait"}

    # ─────────────────────────── actions ───────────────────────────
    def execute_move(self, hero, target):
        """Walk toward `target`, interacting with it on arrival. Generator; returns True if
        anything happened."""
        S, tm = self.state, self.state["tile_map"]
        path = self.path(hero, target)
        if not path:
            return False
        moved = False
        for i, p in enumerate(path):
            last = i == len(path) - 1
            if last and world.is_interaction(S, p, OWNER):
                if hero.movement_points <= 0:
                    return moved
                yield from self.interact(hero, p)
                return True
            cost = tm.movement_cost(*p)
            if cost is None or cost > hero.movement_points:
                return moved
            hero.spend_movement(cost)
            hero.pos = p
            moved = True
            world.sync_hero_in_town(S, hero)
            yield ("step", hero, p)
            town = world.town_at(S, p)
            if town:
                if town.owner != OWNER:
                    was_player = town.owner == "player"
                    world.capture_town(S, town, OWNER)
                    if was_player:
                        yield ("msg", f"{hero.name} captured {town.name}!")
                return True
        return moved

    def interact(self, hero, pos):
        S = self.state
        tile = S["tile_map"].get(*pos)
        other = world.hero_at(S, pos)
        if other and other.owner == "player":
            hero.movement_points = 0
            yield ("combat", {"attacker": hero, "defender_hero": other})
            return
        obj = tile.object_data
        if tile.object_type == "town":
            hero.movement_points = 0
            if obj.owner == "player":
                yield ("combat", {"attacker": hero, "defender_town": obj})
            else:
                winner, msgs = world.auto_battle(S, hero, town=obj)
            return
        if isinstance(obj, NeutralStack):
            hero.movement_points = 0
            winner, msgs = world.auto_battle(S, hero, neutral=obj)
            for m in msgs:
                yield ("msg", m)
            return
        for text, kind in world.visit_object(S, hero, pos):
            if isinstance(obj, Mine) and obj.owner == OWNER and S["tile_map"].get(*pos).is_visible:
                yield ("msg", f"{hero.name} seized a {obj.resource_type} mine!")

    def recruit_plan(self, town, gold):
        """[(creature_key, count)] best-first purchases from the town's pools within `gold`."""
        plan = []
        for tier in sorted(town.dwellings(), reverse=True):
            key = max(town.dwellings()[tier], key=lambda k: CREATURES[k]["is_upgraded"])
            n = min(town.pool.get(str(tier), 0), gold // CREATURES[key]["cost"])
            if n > 0:
                plan.append((key, n))
                gold -= n * CREATURES[key]["cost"]
        return plan

    def recruit_value(self, town):
        return sum(stack_power(k, n) for k, n in self.recruit_plan(town, self.res["gold"]))

    def build_in(self, town):
        """One building per town per day: dwellings/military first, then income."""
        if town.built_today:
            return None
        options = [n for n in town.defs() if town.can_build(n, self.res)]
        if not options:
            return None
        rank = {"dwelling": 0, "military": 1, "income": 2}
        name = min(options, key=lambda n: (rank.get(town.defs()[n]["category"], 3),
                                           town.defs()[n]["cost"].get("gold", 0)))
        if RM.spend(self.res, town.defs()[name]["cost"]):
            town.build(name)
            return name
        return None

    def recruit_and_build(self, hero, town):
        """Build if possible, recruit the best units we can afford straight into the hero's
        army, then visit the Mage Guild."""
        self.build_in(town)
        for key, n in self.recruit_plan(town, self.res["gold"]):
            spent = town.recruit(key, n, target=hero.army)
            if spent:
                RM.spend(self.res, spent)
        world.visit_mage_guild(self.state, hero, town, SPELLS)
        return []


def take_turn(state):
    """Run the whole enemy turn without a UI (battles with the player are auto-resolved).
    Returns messages for the HUD."""
    msgs = []
    gen = AIPlayer(state).run_turn()
    for ev in gen:
        if ev[0] == "msg":
            msgs.append(ev[1])
        elif ev[0] == "combat":
            kw = ev[1]
            _, battle_msgs = world.auto_battle(state, kw["attacker"], defender_hero=kw.get("defender_hero"),
                                               neutral=kw.get("defender_stack"), town=kw.get("defender_town"))
            msgs += battle_msgs
    return msgs


def ai_combat_action(combat_state, ai_stack):
    """Decide and apply one stack's battle action instantly (used for auto-battles)."""
    if not ai_stack.is_alive:
        return
    act = CombatEngine.ai_action(combat_state, ai_stack)
    if act["path"]:
        ai_stack.hex_pos = act["path"][-1]
    if act["target"]:
        (CombatEngine.do_ranged_attack if act["ranged"] else CombatEngine.do_melee_attack)(
            combat_state, ai_stack, act["target"])
    ai_stack.has_acted = True
