# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# HeroForge: Turn-Based Strategy Game
## Inspired by Heroes of Might and Magic III

---

## Source of Truth & Workflow
- The game is built in 5 sequential sessions defined in `heroforge_prompts.md`
  (1: Foundation + Adventure Map, 2: Combat Grid, 3: Town Screen, 4: Hero System + AI, 5: Polish + Save/Load).
  Each session builds on the previous one; check what exists before starting one.
- `heroforge_prompts.md` holds the exact numbers (creature stats, colors, layout pixel offsets,
  building costs, spell effects, save format). Use those values instead of inventing new ones;
  this file is only the summary.
- Update **Build Status** at the bottom when a session is finished.

## Commands
- Environment: project-local venv at `.venv/` (pygame 2.6.1). Create with
  `python3 -m venv .venv && .venv/bin/pip install pygame`. Session 5's `engine/sound_engine.py`
  also uses `numpy` (see Known Spec Conflicts).
- Run: `.venv/bin/python main.py`
- No test suite or linter is set up. Verify by running the game and checking the session's goal:
  - S1: map renders, hero moves, fog of war updates
  - S2: walking onto a neutral creature tile opens combat, and the battle can be finished
  - S3: walking into a town opens the town screen, and building and recruiting work
  - S4: hero levels up, enemy AI moves on its turn
  - S5: Ctrl+S saves to `heroforge_save.json`, sounds play, animations are smooth
- Test scripts from earlier sessions live outside the repo (they're not committed). The pattern:
  run the AI turn to completion with a frame loop while `SM.scenes["adventure_map"].ai_gen` is set,
  because End Turn is no longer instant.
- Headless check without a window: `SDL_VIDEODRIVER=dummy .venv/bin/python -c "import main"`
  imports and loads all data. To drive scenes headlessly: `pygame.init()`, `set_mode`,
  `main.init_fonts()`, `main.new_game()`, `SM = main.register_scenes()`, then call
  `SM.handle(event)` / `SM.update(dt)` / `SM.draw(screen)` and `pygame.image.save` screenshots.
  Keep the game loop inside `run()` under `if __name__ == "__main__":` so this keeps working.

## Architecture Notes
- Flow: `main.py` loads JSON into `CREATURES`/`BUILDINGS`/`SPELLS`/`SCENARIO`. `main.new_game()`
  fills `STATE` from `engine/world.new_game_state()` (resources for player *and* enemy, heroes,
  towns, map_objects, tile_map, day/week/month, turn, selected_hero_idx, game_phase).
  `STATE` and `F` are mutated in place (`clear()`/`update()`), never rebound.
- Shared globals: `main.py` aliases itself with `sys.modules.setdefault("main", ...)`, so scenes
  can `import main` and read `main.STATE` / `main.F` **at runtime** (not at import time). Never use
  `from main import STATE`, because it captures the object too early.
- Data tables live in the engine: `engine/creature.CREATURES` and `engine/town.BUILDINGS` are
  the same dict objects as `main.CREATURES` / `main.BUILDINGS`, so engine code never imports main.
  `BUILDINGS` is `{faction: {building_name: def}}`. Buildings carry extra machine-readable keys
  (`income_gold`, `income_res`, `fort_level`, `growth_bonus`, `mage_level`, `tier`, `upgraded`).
- `SM` is a class used directly (`SM.go(...)`, classmethods). `SM.go` returns False for an
  unregistered scene, and `adventure_map.go_or_toast` uses that for scenes not built yet.
  Calls: `SM.go("combat_screen", attacker=hero, defender_stack=NeutralStack |
  defender_hero=Hero | defender_town=Town)`, `SM.go("town_screen", town=t, hero=h)`,
  `SM.go("adventure_map", messages=[...])` (toasts on return; `new_game=True` recenters).
- Map interaction: every map object blocks movement. The hero acts on it from the adjacent tile
  (mines, piles, artifacts, neutral stacks, enemy heroes, garrisoned non-player towns). The hero
  walks *onto* own or ungarrisoned towns, which captures empty towns. Right-clicking an owned
  town opens its screen without moving (the visiting hero is whoever stands on it).
- Towns: `Town.build_status()` → built | locked | built_today | unaffordable | available (one
  build per town per day; `requires_water` buildings need `Town.near_water`, set at new game).
  `Town.recruit(key, n, target=army_list)` merges into any 7-slot list (`town.place_in`). The town
  screen sends recruits straight to the visiting hero (garrison as fallback), so closing commits
  nothing. Upgraded dwelling = +25% growth, then the Citadel/Castle bonus (`Town.weekly_growth`).
  The Mage Guild teaches a fixed per-town, seeded spell pick (`Town.guild_spells`); visiting heroes
  learn them and refill mana on entering. Buildings JSON has `group` (the Buildings-tab heading).
  A hero can't hand its last stack to the garrison.
- Sound: `engine/sound_engine.py` synthesizes with the stdlib `array` module (no numpy).
  `make_sound(freq, duration, wave, volume, fade_out)` has Session 5's signature; `play(name)`
  caches named effects. Everything no-ops if the mixer can't start.
- `engine/world.py` holds the rules both the player UI and the AI use:
  - map interactions: `visit_object`, `capture_town`, `visit_mage_guild`, `is_interaction`
  - battles: `apply_battle_result` (the only place a battle's outcome reaches the world; the
    combat screen and `auto_battle` both call it), `remove_hero`, `check_victory`
  - turns: `begin_enemy_phase` → AI → `finish_end_turn`, which advances the day, runs weekly
    growth after day 7, pays income to both sides, then refreshes movement and fog.
    `world.end_turn(state)` runs all of that headlessly, auto-resolving the enemy's battles.
  - game stats live in `STATE["stats"]`.
- Enemy turn on the map: `AIPlayer(state).run_turn()` is a *generator* of events: `("step", hero,
  pos)`, `("msg", text)`, `("combat", kwargs)`. `AdventureMap.step_ai` plays it out. Visible steps
  are animated. A `combat` event opens `combat_screen` with the player defending, and the
  generator resumes when the map is re-entered (`ai_gen` survives `on_enter`). Battles that don't
  involve the player (AI vs neutral stacks or towns) are resolved inside the generator with
  `world.auto_battle` → `CombatEngine.auto_resolve`. Player input is blocked while `ai_gen` is set.
  The AI sees the whole map (no fog).
- Heroes/progression: XP needed for the next level is `round(1000·L·1.2^(L-1))` (cumulative
  `hero.xp`). On level-up: primary stat by faction odds (`MIGHT_CHANCE`), then player heroes queue
  a 3-option skill choice in `hero.levelup_queue`, which the adventure map shows as a modal popup.
  AI heroes pick at once (`ai_pick_skill`). Skill values and texts live in `engine/skills.py`
  (`skill_value(hero, name)`). Wisdom caps learnable spell level (2 without it). Navigation and
  Diplomacy are never offered because they have no effect yet.
- Skill/artifact effects in battle are applied once in `combat_engine.build_side` onto
  `CombatStack` fields: `hp_bonus`, `speed_bonus`, `melee_bonus`, `ranged_bonus`,
  `damage_reduction`, `luck`, `morale`. Luck = 10%/point double damage. Morale = 10%/point
  extra action once per round; undead are immune. Tactics = a `tactics` placement phase before
  round 1. Eagle Eye works in `cast_spell`. School skills scale `spell_damage`.
- Artifacts: `data/artifacts.json` uses generic slots (`hand`/`ring`/`misc` map to two hero
  slots via `hero.SLOT_TYPES`). Bonus keys: attack, defense, power, knowledge, movement, mana,
  speed, hp. Scenario pickups reference artifacts by name. A full slot sends the item to
  `hero.backpack`. `ResourceManager` (engine/resource_manager.py) handles spending and income.
- Adventure map rendering: the whole map's static terrain is pre-rendered once into one surface
  (`terrain_layer`), and the fog into another rebuilt only when `TileMap.fog_version` changes
  (`fog_layer`). Each frame blits the visible slice of both and draws animated water, objects and
  heroes in between. Call `tm.reveal()` / `update_fog()` (they bump `fog_version`); never edit
  tiles without doing so.
- Map controls: the first click plans a route (solid), the second click on the same goal walks it
  (`HeroMoveAnimation`, `MOVE_SPEED` tiles/s). The camera glides toward `cam_tx/cam_ty`; use
  `center_on()` / `follow()`, not `cam_x` directly. Right-click shows info only. Keys: H hero
  screen, T cycles owned towns, Tab next hero with movement left, Ctrl+S save, Esc menu.
- Save/load (`engine/save_load.py`): saves to `heroforge_save.json` in the project root. The file
  holds terrain, explored flags, all objects, heroes, towns, resources, calendar and stats, so it
  doesn't depend on `scenario.json`. Writes go to a temporary file and then replace the save.
  **Any new field on Hero/Town/map objects or in STATE must be added to the
  serialize/deserialize functions.** `Hero(**d)` breaks on unknown keys, so prefer explicit
  defaults. `STATE["stats"]` is merged over `world.default_stats()` on load.
- Sound: `sound_engine.init_sounds()` builds the `SOUNDS` table (the loading screen calls it).
  Call `sound_engine.play(name)`. Buttons play "click" automatically (`Button.sound`). Sounds are
  kept out of STATE because STATE is JSON-saved.
- UI helpers: `ui_art.request_hand()` from a scene's update() shows the hand cursor this frame
  (Buttons do it themselves; the main loop calls `apply_cursor()`). `ui_art.draw_tooltip()`,
  `creature_art.creature_tooltip()` and `draw_creature_card()` are the shared hover widgets.
  Avoid non-Latin glyphs (✓ ☠ ↩ …) in rendered text: the default fonts show them as boxes.
- Combat effects live in `art/combat_fx.py` (AttackAnimation, DamageFlash, SpellEffect,
  StackDeathAnimation, FloatingText). Engine hit events are `(stack, damage, killed, tags)`, where
  tags may contain "lucky". `CombatScreen.add_hits` turns them into effects.
- Map objects include `Obelisk` (visiting reveals a radius around `reveal_center`). The scenario
  was generated by a one-off script that checks reachability: the 3 pocket artifacts can only be
  reached by beating a guard. Boats are not implemented: the river has two fords, and the Shipyard
  is just a building.
- Recruit pools are per tier (`Town.pool[str(tier)]`), shared by base and upgraded creatures.
- Adventure map uses square tiles (A* with a Manhattan heuristic, in `tile_map.py`). Combat uses
  a separate even-r offset hex grid (`hex_grid.py`). Don't mix the two coordinate systems.
- Hex grid: even-r offset, **pointy-top** hexes, *even* rows shifted right (Prompt 2's formula
  shifted odd rows and called them flat-top; the project convention won). Hexes are 56×50
  (squashed). `pixel_to_hex` unsquashes and rounds in cube space, so it's exact. Distance goes
  through axial coordinates. The grid is 868px wide, so the combat right panel starts at x=880.
- Combat split: `engine/combat_engine.py` only changes state (`CombatStack`, `CombatState`,
  `CombatEngine` static methods, `ai_action`, `build_side`, `SPELLS` registry). `scenes/
  combat_screen.py` decides when things happen: an action *queue* of `move`/`attack`/`spell`/
  `pause` steps, run during phase `animating`, then a callback (`end_stack_turn`,
  `after_player_move`, `after_cast`). Engine attack/spell calls return `(stack, dmg, killed)` hits,
  which the scene turns into floaters.
- Combat sides: `CombatState.player_side` is "attacker" when the attacking hero is the player's,
  else "defender", so the enemy can attack the player (Session 4). Each `CombatStack.slot` maps
  back to the army/garrison slot. `CombatScreen.apply_result()` writes survivors back, removes
  defeated neutral stacks or heroes, captures towns, awards XP and returns via
  `SM.go("adventure_map", messages=...)`.
- Combat rules beyond the spec: commanding hero's attack/defense are added to its stacks. Defend
  is ×1.3 total defense until the stack's next turn. A shooter with an adjacent enemy must melee at
  half damage. Abilities implemented: `no_retaliation`, `unlimited_retaliation`, `double_strike`,
  `double_shot`, `hate_undead` (×1.5). A hero may cast once per round, and the enemy hero AI casts too.
  Bless/Curse use per-stack `dmg_mode`; never mutate `CREATURES` entries. Spell keys are
  `spell_key(name)` (e.g. "lightning_bolt"). `SPELLS` itself is keyed by display name. Damage spells
  do `base_value × power`, except where `scales_with_power` is false (Implosion, Inferno):
  `base + 10 × power`. Size-2 dragons still occupy one hex.

## Known Spec Conflicts (ask the user or resolve explicitly)
- (Resolved) "pygame ONLY" vs Session 5's numpy-based `sound_engine.py`: the sound engine already
  exists without numpy. Extend it in Session 5 rather than switching to `pygame.sndarray`.
- (Resolved) Snow, lava and sand cost 2 and swamp costs 3, set in `config.TERRAIN_COST`
  next to the spec's grass/dirt/rough/rock/water values.
- The save format hardcodes `range(32)` for the fog grid. Use the tile_map's own dimensions.

---

## What This Is
A turn-based strategy game in Python + pygame featuring:
- Adventure map exploration with fog of war
- Town building and army recruitment
- Tactical hex-grid combat
- Hero progression (levels, skills, spells, artifacts)
- 2 player factions (Castle + Necropolis) vs AI opponent
- 7 resources, day/week/month turn system

## Tech Stack
- Python 3.x + pygame ONLY — no other dependencies
- All graphics procedural (zero image files)
- JSON data files for units, buildings, spells, map
- JSON save/load for game persistence

---

## Project Structure

```
heroforge/
├── CLAUDE.md
├── main.py                # Entry, GameLoop, font dict F, global STATE
├── config.py              # SW=1280 SH=800 FPS=60, C_* colors, constants
│
├── data/
│   ├── creatures.json     # Unit stats by faction + tier (Castle + Necropolis)
│   ├── buildings.json     # Town structures, costs, prerequisites, effects
│   ├── spells.json        # 20 spells across 4 magic schools
│   └── scenario.json      # 32×32 starting map layout
│
├── scenes/
│   ├── scene_manager.py   # SM class: register/go/update/draw/handle
│   ├── main_menu.py
│   ├── adventure_map.py   # World map, hero movement, fog of war
│   ├── town_screen.py     # Building, garrison, recruitment
│   ├── combat_screen.py   # Hex grid battle
│   ├── hero_screen.py     # Hero stats, skills, artifacts
│   └── end_screen.py      # Victory / defeat
│
├── engine/
│   ├── hero.py            # Hero entity + methods
│   ├── creature.py        # CreatureStack
│   ├── town.py            # Town entity + building/recruitment methods
│   ├── map_objects.py     # Mine, artifact, dwelling, resource pile
│   ├── hex_grid.py        # Hex coordinate math + pathfinding (A*)
│   ├── tile_map.py        # Adventure map tile grid + fog of war
│   ├── combat_engine.py   # CombatState, CombatStack, battle resolver
│   ├── ai_player.py       # Computer opponent turn logic
│   └── save_load.py       # JSON save/load
│
└── art/
    ├── terrain_art.py     # Draw tile types procedurally
    ├── creature_art.py    # Procedural unit sprites (14 types)
    ├── hero_art.py        # Hero portraits + map sprite
    └── ui_art.py          # Reusable UI: Btn, blit, panel, hp_bar
```

---

## Code Conventions

- Scene interface: `on_enter(**kw)`, `update(dt)`, `draw(surf)`, `handle(ev)`
- Global STATE dict at module level in main.py
- Colors: `C_*` constants in config.py
- Font dict in main.py: `F = {'lg':..., 'md':..., 'sm':..., 'ti':..., 'title':...}`
- Helper `blit(surf, text, font, color, x, y, align)` in art/ui_art.py
- Helper `panel(surf, rect, col, bdr, br)` in art/ui_art.py
- Hex grid: use offset coordinates (even-r, pointy-top; see Architecture Notes)
- All timers use dt (seconds since last frame)
- JSON data loaded once at startup in main.py, stored in module-level dicts
- `CREATURES`, `BUILDINGS`, `SPELLS` dicts are global in main.py

---

## Two Factions

### Castle (order / light)
| Tier | Base            | Upgraded        |
|------|-----------------|-----------------|
| 1    | Pikeman         | Halberdier       |
| 2    | Archer          | Marksman         |
| 3    | Griffin         | Royal Griffin    |
| 4    | Swordsman       | Crusader         |
| 5    | Monk            | Zealot           |
| 6    | Cavalier        | Champion         |
| 7    | Angel           | Archangel        |

### Necropolis (undead / dark)
| Tier | Base            | Upgraded         |
|------|-----------------|------------------|
| 1    | Skeleton        | Skeleton Warrior  |
| 2    | Walking Dead    | Zombie            |
| 3    | Wight           | Wraith            |
| 4    | Vampire         | Vampire Lord      |
| 5    | Lich            | Power Lich        |
| 6    | Black Knight    | Dread Knight      |
| 7    | Bone Dragon     | Ghost Dragon      |

---

## Core Data Models

### Hero
```python
{
  "name": str,
  "faction": "castle" | "necropolis",
  "level": int, "xp": int, "xp_next": int,
  "attack": int, "defense": int, "power": int, "knowledge": int,
  "skills": {skill_name: 1|2|3},   # 1=basic 2=advanced 3=expert
  "army": [CreatureStack|None]*7,
  "artifacts": {"head","neck","torso","cloak","hand_r","hand_l","ring1","ring2","boot","misc1","misc2"},
  "spells": [str],
  "mana": int, "mana_max": int,
  "movement_points": int, "movement_max": int,
  "pos": (int,int),  # tile coords on adventure map
  "owner": "player"|"enemy"
}
```

### CreatureStack
```python
{
  "creature": str,    # key into CREATURES dict
  "count": int,
  "hp_remaining": int   # HP of the top unit in the stack
}
```

### Town
```python
{
  "faction": str, "name": str,
  "pos": (int,int), "owner": str,
  "buildings": {building_name: bool},
  "garrison": [CreatureStack|None]*7,
  "hero_in_town": str|None   # hero name
}
```

---

## Resources (7)
`gold, wood, ore, mercury, sulfur, crystal, gems`

Starting amounts: gold=2000, wood=20, ore=20, others=2 each.

Daily mine income:
- Gold mine: +1000/day
- Wood/Ore mine: +2/day
- Specialty mine (mercury/sulfur/crystal/gems): +1/day

---

## Turn Structure
- Day-based turns (days 1–7 form one week)
- Each turn: player moves heroes, builds in towns, then ends turn
- Enemy AI takes its turn automatically between player turns
- Day 7: weekly event (creature growth, new mana if hero in town)
- Victory: all enemy heroes defeated AND all enemy towns captured

---

## Combat System Overview
- 15×11 hex grid (attacker on left cols 0–6, defender on right cols 8–14)
- Initiative-based turn order (highest goes first each round)
- Actions: Move, Melee Attack, Ranged Attack, Cast Spell, Defend, Wait
- Melee damage formula:
  - `atk_bonus = max(0, attacker.attack - defender.defense) * 0.05`
  - `def_penalty = max(0, defender.defense - attacker.attack) * 0.025`
  - `damage = random(min_dmg, max_dmg) * count * (1 + atk_bonus - def_penalty)`
- Retaliation: defender attacks back once per round (if alive)
- Stacks die when their total HP reaches 0
- XP per kill: `creature.tier * 25` per unit killed

---

## Magic Schools (4)
- **Earth**: Slow, Stone Skin, Quicksand, Earthquake, Implosion
- **Air**: Haste, Air Shield, Lightning Bolt, Chain Lightning, Dimension Door
- **Fire**: Curse, Bloodlust, Fireball, Armageddon, Inferno
- **Water**: Bless, Weakness, Frost Ring, Blizzard, Resurrection

---

## Adventure Map Objects
`town, gold_mine, wood_mine, ore_mine, mercury_mine, sulfur_mine, crystal_mine, gems_mine, artifact, creature_stack, resource_pile, dwelling, obelisk`

---

## Secondary Skills (selectable on level-up)
Logistics, Archery, Leadership, Wisdom,
Earth Magic, Fire Magic, Air Magic, Water Magic,
Tactics, Offense, Armorer, Luck, Morale,
Navigation, Scouting, Diplomacy, Eagle Eye

---

## Build Status
[x] Session 1 — Foundation + Adventure Map (data files, engine entities, adventure map, main menu)
[x] Session 2 — Combat Grid (hex grid, combat engine, combat screen, battle AI)
[x] Session 3 — Town Screen (illustrations, building, recruitment, garrison management)
[x] Session 4 — Hero System + AI (hero screen, level-ups, skills, artifacts, AI opponent, end screen)
[x] Session 5 — Polish + Save/Load (animations, sounds, minimap, save/load, new scenario, UX checklist)

Data files were generated by a one-off script and are now edited directly.
Unit names come from the spec; building, hero, town and artifact names are original.
