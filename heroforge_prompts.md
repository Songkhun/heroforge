# HeroForge — Claude Code Session Prompts
## 5 prompts to build a Heroes of Might and Magic III-inspired game

---

## HOW TO USE THESE PROMPTS

1. Create folder: `heroforge/`
2. Copy `CLAUDE.md` into `heroforge/CLAUDE.md`
3. Run `cd heroforge && claude`
4. Paste **Prompt 1** and press Enter
5. Wait for Session 1 to complete fully, then paste **Prompt 2**, etc.
6. Each session builds on the previous one — do them in order.

---

## PROMPT 1 — Foundation + Adventure Map

```
Build the foundation of HeroForge following the project structure in CLAUDE.md.

═══════════════════════════════════════════
PHASE 1A — Configuration and data files
═══════════════════════════════════════════

1. Create config.py with:
   SW=1280, SH=800, FPS=60
   Colors:
     C_BG0=(12,16,24)  C_BG1=(22,28,42)  C_BG2=(32,40,60)
     C_BDR=(55,70,105) C_GOLD=(255,195,55) C_TXT=(220,228,242)
     C_SUB=(140,158,195) C_HINT=(85,102,140) C_GRN=(68,200,115)
     C_RED=(215,75,75) C_BLUE=(95,180,255) C_PURP=(175,110,255)
   Terrain colors:
     TERR_GRASS=(55,100,45) TERR_DIRT=(140,100,65) TERR_WATER=(35,70,160)
     TERR_ROCK=(90,90,105) TERR_SNOW=(210,215,225) TERR_LAVA=(180,60,20)
     TERR_SAND=(195,170,100) TERR_SWAMP=(60,90,60)
   Resource icon colors:
     RES_GOLD=(255,210,50) RES_WOOD=(140,95,50) RES_ORE=(150,140,130)
     RES_MERCURY=(180,70,180) RES_SULFUR=(210,190,50)
     RES_CRYSTAL=(120,180,220) RES_GEMS=(60,185,100)
   Faction colors:
     CASTLE_COL=(180,160,100) NECROPOLIS_COL=(90,80,130)
   TILE_SIZE=48 (pixels per adventure map tile)
   VISION_RADIUS=5 (tiles a hero can see around themselves)

2. Create data/creatures.json — full unit definitions for Castle (14 units, base+upgrade)
   and Necropolis (14 units, base+upgrade) as listed in CLAUDE.md.
   Each creature entry:
   {
     "name": str,
     "upgraded_name": str,
     "faction": "castle"|"necropolis",
     "tier": 1-7,
     "attack": int, "defense": int,
     "damage_min": int, "damage_max": int,
     "hp": int,
     "speed": int,       (movement hexes per combat turn)
     "initiative": int,  (higher = acts sooner)
     "cost": int,        (gold per unit)
     "weekly_growth": int,
     "xp_value": int,    (= tier * 25)
     "is_ranged": bool,
     "is_flying": bool,
     "size": 1,          (use 2 only for Bone Dragon / Ghost Dragon)
     "abilities": []     (e.g. ["no_retaliation","undead","hate_undead"])
   }
   Castle creature stats (use these exact values):
   pikeman:         atk=4  def=5  dmg=1-3   hp=10  spd=4  ini=10 cost=60   grow=20
   halberdier:      atk=6  def=5  dmg=2-3   hp=10  spd=5  ini=11 cost=65   grow=20
   archer:          atk=6  def=3  dmg=2-3   hp=10  spd=4  ini=12 cost=100  grow=12 ranged
   marksman:        atk=6  def=3  dmg=2-3   hp=10  spd=6  ini=12 cost=150  grow=12 ranged (double shot ability)
   griffin:         atk=8  def=8  dmg=3-6   hp=25  spd=9  ini=14 cost=200  grow=8  flying
   royal_griffin:   atk=9  def=9  dmg=4-7   hp=30  spd=10 ini=16 cost=240  grow=8  flying (unlimited retaliation)
   swordsman:       atk=10 def=12 dmg=6-9   hp=35  spd=5  ini=11 cost=300  grow=7
   crusader:        atk=12 def=12 dmg=8-10  hp=35  spd=6  ini=13 cost=350  grow=7  (strikes twice)
   monk:            atk=12 def=7  dmg=10-12 hp=30  spd=5  ini=12 cost=400  grow=5  ranged
   zealot:          atk=12 def=10 dmg=10-12 hp=30  spd=7  ini=14 cost=450  grow=5  ranged (no range penalty)
   cavalier:        atk=15 def=15 dmg=15-25 hp=70  spd=8  ini=11 cost=600  grow=4
   champion:        atk=16 def=16 dmg=20-25 hp=80  spd=9  ini=13 cost=750  grow=4  (jousting bonus)
   angel:           atk=20 def=20 dmg=20-50 hp=200 spd=12 ini=16 cost=3000 grow=1  flying (casts resurrection)
   archangel:       atk=20 def=20 dmg=30-50 hp=250 spd=14 ini=18 cost=5000 grow=1  flying (raises dead, aura of fear)
   Necropolis creature stats:
   skeleton:        atk=5  def=4  dmg=1-3   hp=6   spd=5  ini=11 cost=60   grow=20 undead
   skeleton_warrior:atk=6  def=6  dmg=2-3   hp=6   spd=6  ini=13 cost=65   grow=20 undead (shields)
   walking_dead:    atk=5  def=5  dmg=2-3   hp=15  spd=3  ini=8  cost=98   grow=15 undead slow
   zombie:          atk=5  def=5  dmg=2-4   hp=20  spd=4  ini=9  cost=115  grow=15 undead (disease)
   wight:           atk=7  def=7  dmg=3-7   hp=18  spd=6  ini=13 cost=200  grow=9  undead flying (drain mana)
   wraith:          atk=7  def=7  dmg=3-8   hp=18  spd=8  ini=15 cost=250  grow=9  undead flying (drain mana)
   vampire:         atk=10 def=9  dmg=5-8   hp=40  spd=8  ini=13 cost=360  grow=6  undead flying no_retaliation
   vampire_lord:    atk=10 def=10 dmg=5-10  hp=40  spd=9  ini=15 cost=500  grow=6  undead flying no_retaliation (life drain)
   lich:            atk=13 def=10 dmg=11-15 hp=30  spd=5  ini=12 cost=550  grow=4  undead ranged (cloud attack)
   power_lich:      atk=13 def=10 dmg=13-17 hp=40  spd=7  ini=14 cost=700  grow=4  undead ranged (cloud attack)
   black_knight:    atk=16 def=16 dmg=15-30 hp=120 spd=7  ini=12 cost=1200 grow=3  undead (curses on attack)
   dread_knight:    atk=18 def=18 dmg=15-30 hp=130 spd=8  ini=14 cost=1500 grow=3  undead (curses, death stare)
   bone_dragon:     atk=17 def=15 dmg=25-50 hp=180 spd=9  ini=11 cost=1800 grow=2  undead flying size=2
   ghost_dragon:    atk=19 def=17 dmg=25-50 hp=200 spd=11 ini=13 cost=3000 grow=2  undead flying size=2 (aging ability)

3. Create data/buildings.json with Castle + Necropolis buildings.
   Each building:
   {
     "name": str, "faction": str,
     "cost": {"gold":int, "wood":int, "ore":int, ...},
     "prerequisite": [building_name, ...],
     "effect": str,
     "provides_creature": str|null,
     "category": "income"|"military"|"magic"|"dwelling"|"special"
   }
   Castle buildings:
   - Village Hall → Town Hall → City Hall → Capitol (income 500→1000→2000→4000/day)
   - Blacksmith (buy war machines), Tavern (morale +1, hire heroes)
   - Mage Guild Level 1-5 (each level adds more spells; req: previous level)
   - Fort → Citadel → Castle (wall defenses for combat)
   - Marketplace (resource trading), Resource Silo (+1 ore/day)
   - Shipyard (requires water adjacent to town)
   - Dwellings Tier 1-7 (base) + Upgraded versions (each upgraded req: base built)
   Necropolis buildings: mirror structure with undead-themed names.
   Special Necropolis building: Undead Transformer (converts living troops to skeletons after combat)

4. Create data/spells.json with 20 spells (5 per school):
   Earth: Slow(-3 speed, def), Stone Skin(+3 def), Quicksand(impassable hex), Earthquake(damages walls), Implosion(300+dmg single)
   Air: Haste(+3 speed), Air Shield(-25% ranged dmg taken), Lightning Bolt(25×power dmg), Chain Lightning(jumps 4 targets), Dimension Door(teleport hero)
   Fire: Curse(-dmg to min), Bloodlust(+3 atk), Fireball(25×power dmg area), Armageddon(50×power ALL stacks), Inferno(100 dmg fire)
   Water: Bless(+dmg to max), Weakness(-3 atk), Frost Ring(10×power dmg ring), Blizzard(10×power area slow), Resurrection(revive friendly units)
   Each spell: { "name", "school", "level":1-5, "mana_cost", "effect_type":"damage"|"buff"|"debuff"|"special", "base_value":int, "target":"single"|"all_enemies"|"all"|"area"|"tile", "description" }

5. Create data/scenario.json with a 32×32 starting map:
   - Full terrain grid as 32×32 array of terrain type strings
   - 2 starting towns: Castle at (5,5), Necropolis at (26,26)
   - 2 neutral towns: at (16,8) and (14,24)
   - Mines: 4 gold mines, 2 wood mines, 2 ore mines, 1 each specialty resource
   - 8 neutral creature stacks guarding mines (mixed tiers 1-3)
   - 6 artifact pickups scattered around
   - 4 resource piles (bonus starting resources)
   - 2 player heroes: player hero at (6,5), enemy hero at (25,26)
   - Terrain: mostly grass with dirt paths, water lake in center (~10 water tiles),
     rock formations near edges, forest patches (use "rough" for trees)
   Format: { "terrain": [[str]*32]*32, "towns": [...], "mines": [...], "creatures": [...], "artifacts": [...], "heroes": [...], "resources": [...] }

═══════════════════════════════════════════
PHASE 1B — Entity and engine classes
═══════════════════════════════════════════

6. Create engine/hero.py:
   Hero dataclass with all fields from CLAUDE.md data models section.
   Methods:
     add_to_army(creature_key, count) → bool  (finds empty slot)
     remove_from_army(slot_idx)
     has_movement() → bool
     spend_movement(cost)
     refresh_movement()  (called at start of player turn, terrain-aware formula)
     gain_xp(amount)
     level_up()          (increase stat, trigger skill choice popup)
     add_spell(spell_name)
     spend_mana(amount) → bool
     restore_mana()      (called in town or end of week)
     army_power() → int  (sum of atk × hp × count per stack, used by AI)
   Class method: from_scenario(data_dict) → Hero

7. Create engine/creature.py:
   CreatureStack dataclass.
   Methods:
     take_damage(amount) → int  (returns number of units killed)
     is_alive() → bool
     hp_percent() → float
     total_hp() → int
     clone() → CreatureStack
   Also: load_creatures_data(json_path) → dict (called once at startup)

8. Create engine/town.py:
   Town dataclass.
   Methods:
     can_build(building_name, player_resources) → bool  (checks cost + prereqs)
     build(building_name) → dict  (returns resource cost spent)
     available_to_recruit() → dict  (creature_key → count in pool)
     recruit(creature_key, count) → dict  (returns cost, updates pool)
     start_new_week()  (refill growth pools based on built dwellings)
     income_per_day() → int  (gold from income buildings)
   Class method: from_scenario(data_dict) → Town

9. Create engine/tile_map.py:
   Tile namedtuple: terrain_type, object_type, object_data, is_passable, is_explored, is_visible
   TileMap class:
     grid: 2D list of Tiles (32×32)
     Methods:
       get(x,y) → Tile
       set_object(x,y,obj_type,obj_data)
       remove_object(x,y)
       update_fog(heroes_list, vision_radius=VISION_RADIUS)
         → marks tiles within vision_radius of each hero as visible
         → tiles previously visible but now out of range: explored but not visible
         → tiles never seen: unexplored
       get_passable_neighbors(x,y) → list of (x,y)
       is_passable(x,y) → bool
       movement_cost(x,y) → int  (grass=1,dirt=1,rough=2,rock=3,water=impassable)
   Class method: from_scenario(scenario_dict) → TileMap

10. Create engine/map_objects.py:
    MapObject base class and subclasses:
      Mine(resource_type, owner, daily_income)
      ArtifactObj(artifact_name, slot_type, bonus_dict)
      ResourcePile(resource_type, amount)
      Dwelling(creature_key, available_count, weekly_growth)
      NeutralStack(creature_key, count, is_aggressive)
    Each has: pos, object_type, is_passable=False

11. Create art/ui_art.py with:
    blit(surf, text, font, color, x, y, align="left")
    blit_wrap(surf, text, font, color, x, y, max_w, gap=3) → int (height used)
    panel(surf, rect, col=None, bdr=None, br=10, bw=1)
    hp_bar(surf, rect, hp, hp_max, col)
    class Button:
      __init__(rect, label, font, col, hov, tc, br)
      draw(surf), update(mx,my), clicked(ev)

═══════════════════════════════════════════
PHASE 1C — Adventure Map Scene
═══════════════════════════════════════════

12. Create art/terrain_art.py:
    draw_tile(surf, rect, terrain_type, t)
    Each terrain type drawn procedurally:
    - grass: fill C_TERR_GRASS + scatter 30 darker 2px dots + 3 short random lines (blades)
    - dirt: fill TERR_DIRT + crosshatch pattern (2 sets of 4 parallel lines 8px apart)
    - water: fill TERR_WATER + 2 animated sine wave lines (y = base + sin(x*0.1 + t) * 3)
    - rock: fill TERR_ROCK + draw 2-3 random grey polygons (jagged rock shapes, 4-6 vertices)
    - snow: fill TERR_SNOW + 8 random white circle sparkles (r=1-2)
    - lava: fill TERR_LAVA + 3 orange crack lines (polyline, 3-4 segments)
    - sand: fill TERR_SAND + 20 tiny dot clusters (r=1)
    - swamp: fill TERR_SWAMP + 3 small oval puddles (semi-transparent blue)
    - rough (forest): fill dark green + 3 circle tree tops (r=8-12, darker green)

13. Create art/creature_art.py:
    draw_creature(surf, cx, cy, creature_key, t, count, size=48)
    Draw each creature type as a recognizable 36×36 shape:
    - pikeman/halberdier: tall humanoid (rect body, circle head) + diagonal spear line
    - archer/marksman: humanoid + bow shape (arc line)
    - griffin/royal_griffin: lion body ellipse + eagle wing triangles on top
    - swordsman/crusader: wider humanoid + sword rectangle
    - monk/zealot: robed figure (tall trapezoid) + halo circle
    - cavalier/champion: horse body + mounted rider (two stacked ellipses)
    - angel/archangel: humanoid + 2 large wing triangles + halo
    - skeleton/skeleton_warrior: thin white humanoid with dot eyes, thin line limbs
    - walking_dead/zombie: wider humanoid, grey-green, hunched
    - wight/wraith: floating torso + flowing bottom (triangle) + glowing eyes
    - vampire/vampire_lord: dark humanoid + cape polygon behind
    - lich/power_lich: floating torso + purple glow + no legs + staff
    - black_knight/dread_knight: heavy armored humanoid (wider rect) + sword
    - bone_dragon/ghost_dragon: horizontal ellipse body + spine triangles + wings
    Draw count badge: small circle bottom-right + white number text
    Active stack: animated gold border pulse (brightness cycles sin(t*3))

14. Create art/hero_art.py:
    draw_hero_on_map(surf, cx, cy, faction, owner, t)
      Draw as colored circle (faction color if player, red if enemy)
      + faction symbol inside (sword for Castle, skull for Necropolis)
      + subtle bob animation (y += sin(t*2)*2)
    draw_hero_portrait(surf, rect, faction, name, font)
      Draw simple face in a panel: circle head, two eyes, faction symbol above

15. Create scenes/scene_manager.py:
    SM class:
      register(name, scene), go(name, **kw), update(dt), draw(surf), handle(ev)

16. Create scenes/adventure_map.py — the main game screen:

    LAYOUT:
    - TOP HUD (y=0 to y=56): 7 resource icons + amounts, day counter "Day 3, Week 1, Month 1", End Turn button (right side)
    - MAP AREA (y=56 to y=680): scrollable tile grid with camera
    - BOTTOM PANEL (y=680 to y=800): selected hero info (left) + army display (right)

    MAP RENDERING:
    - Camera position: (cam_x, cam_y) in tile units, clamped to map bounds
    - Visible tiles: from (cam_x, cam_y) to (cam_x + SW//TILE_SIZE + 1, cam_y + SH//TILE_SIZE + 1)
    - For each visible tile at (tx, ty):
        pixel_x = (tx - cam_x) * TILE_SIZE
        pixel_y = (ty - cam_y) * TILE_SIZE + 56  (offset for HUD)
        tile_rect = Rect(pixel_x, pixel_y, TILE_SIZE, TILE_SIZE)
        1. Draw terrain (from terrain_art.py)
        2. Draw object if present (mine icon, town silhouette, artifact gem, etc.)
        3. Apply fog overlay:
           - unexplored: black fill
           - explored not visible: semi-transparent grey (50% alpha) using a surface with SRCALPHA
           - visible: nothing
    - Draw heroes on top of tiles at their positions
    - Draw movement path preview as dotted line when hovering (player hero selected)

    TOWN DRAWING on tile (placeholder until town_screen.py built):
      Draw castle silhouette: grey rect body + 2 round towers (circles) + crenellated top (5 small rects)
      Color tint by faction. Owner banner flag above.

    MINE DRAWING on tile:
      Small brown building shape (rect) + resource color dot above

    HERO MOVEMENT:
    - Click selects nearest hero if none selected
    - With hero selected, click on passable tile: A* pathfind to target
    - Movement costs: grass=1, dirt=1, rough=2, rock=3, water=impassable
    - Hero stops when movement_points reach 0
    - Moving onto town tile: SM.go("town_screen", town=town, hero=hero)
    - Moving onto unowned mine: capture it (set owner, trigger daily income)
    - Moving onto neutral creature stack: SM.go("combat_screen", attacker=hero, defender_stack=stack)
    - Moving onto enemy hero: SM.go("combat_screen", attacker=hero, defender_hero=hero2)
    - Moving onto artifact: pick up (add to hero artifacts), remove from map

    A* PATHFINDING (implement in tile_map.py or adventure_map.py):
      Standard A* on the tile grid, heuristic = Manhattan distance
      Returns list of (x,y) tiles to traverse

    SCROLL: WASD keys move camera. Mouse at screen edge also scrolls (optional).
    Camera follows selected hero when it moves.

    BOTTOM PANEL:
    - Left 400px: hero portrait (from hero_art) + name + HP of army + movement remaining
    - Right 880px: 7 army slots showing creature sprite + count. Click slot = show creature stats.

    TOP HUD:
    - Resource icons (small colored circles + labels): gold wood ore mercury sulfur crystal gems
    - Day/Week/Month counter
    - "END TURN" button (right side, gold border)
    - On End Turn: SM logic → trigger enemy AI → advance day counter → refresh heroes

17. Create scenes/main_menu.py:
    Draw title "HeroForge" (large, centered) + subtitle "A Strategy Game"
    Animated particle stars floating in background
    Buttons: "New Game", "Load Game", "Quit"
    New Game → SM.go("adventure_map") with scenario loaded
    Load Game → load save if exists, else show "No save found"

18. Create main.py:
    - Load all JSON data at startup into module-level CREATURES, BUILDINGS, SPELLS dicts
    - Load scenario.json and build TileMap, Hero list, Town list
    - STATE dict:
        player_resources: {"gold":2000,"wood":20,"ore":20,"mercury":2,"sulfur":2,"crystal":2,"gems":2}
        player_heroes: [Hero], enemy_heroes: [Hero]
        towns: [Town], map_objects: [MapObject]
        tile_map: TileMap
        day: 1, week: 1, month: 1
        turn: "player" | "enemy"
        selected_hero_idx: int
        game_phase: "playing" | "victory" | "defeat"
    - Initialize pygame, create screen 1280×800
    - Create font dict F with 'title'(48,bold), 'lg'(28,bold), 'md'(20,bold), 'sm'(15), 'ti'(13)
    - Register all scenes with SM, start with SM.go("main_menu")
    - Game loop: handle events → SM.update(dt) → screen.fill(C_BG0) → SM.draw(screen) → flip

Build Phase 1A, 1B, 1C in order. After each phase verify the game runs without errors.
Final result: a scrollable adventure map with fog of war, 2 heroes you can move around, towns and mines visible, resources tracking in HUD, End Turn button working.
```

---

## PROMPT 2 — Combat Grid

```
The adventure map works. Now add the tactical hex-grid combat system to HeroForge.

Build in this order:
1. engine/hex_grid.py
2. engine/combat_engine.py
3. art/creature_art.py (update draw_creature for combat scale)
4. scenes/combat_screen.py

═══════════════════════════════════════════
engine/hex_grid.py — Hex coordinate math
═══════════════════════════════════════════

Use EVEN-R offset coordinates (flat-top hexes shifted on even rows).
HEX_W=56, HEX_H=50 (hex pixel dimensions).

Implement these functions:

hex_to_pixel(col, row) → (px, py)
  flat-top hex centers, even-r offset formula:
  px = col * HEX_W + (HEX_W // 2 if row % 2 else 0) + HEX_W // 2
  py = row * (HEX_H * 3 // 4) + HEX_H // 2

pixel_to_hex(px, py) → (col, row)
  inverse of hex_to_pixel — nearest hex to pixel point

hex_neighbors(col, row) → list of (col,row)
  6 neighbors using even-r offset neighbor tables

hex_distance(a, b) → int
  convert both to cube coords, return max(|dx|,|dy|,|dz|)

get_reachable(col, row, speed, occupied) → set of (col,row)
  BFS from (col,row) up to `speed` steps, skip `occupied` hexes
  Return all reachable hexes (not including start)

get_melee_targets(col, row, side, occupied_hexes, enemy_hexes) → set
  Return hexes the stack at (col,row) can reach for melee:
  all hexes adjacent to ANY enemy stack hex

get_ranged_targets(col, row, all_enemy_hexes) → set
  Return all enemy hexes (ranged can target anywhere not blocked)

find_hex_path(start, end, blocked_hexes) → list of (col,row)
  A* pathfinding on hex grid
  Returns path from start to end (excluding start, including end)
  Returns [] if no path

draw_hex(surf, col, row, offset_x, offset_y, fill_col, border_col=None, t=0)
  Draw a filled flat-top hexagon at the given grid position.
  offset_x, offset_y = screen offset for the grid top-left
  Optional border_col for highlighted hexes.

═══════════════════════════════════════════
engine/combat_engine.py — Battle resolver
═══════════════════════════════════════════

@dataclass CombatStack:
  creature_key: str
  count: int
  hp_remaining: int     (HP of top unit in stack)
  side: str             ("attacker" or "defender")
  hex_pos: tuple        (col, row) on combat grid
  has_acted: bool       (this round)
  has_retaliated: bool  (this round — reset each new round)
  is_defending: bool    (Defend action active)
  wait_flag: bool       (waiting for later in round)
  speed_override: int   (for Haste/Slow spells; -1 = use creature base)
  atk_modifier: int     (from Bloodlust/Weakness spells)
  def_modifier: int     (from Stone Skin/Curse spells)
  
  Properties:
    creature: dict        (looked up from CREATURES by creature_key)
    initiative: int       (creature["initiative"])
    effective_speed: int  (creature["speed"] + speed_override modifier)
    total_hp: int         (count * creature["hp"] - (creature["hp"] - hp_remaining))
    is_alive: bool        (count > 0)
    
  Methods:
    take_damage(damage: int) → int  (returns units killed)
      kills = damage // creature["hp"]
      remainder = damage % creature["hp"]
      count -= kills
      if count > 0: hp_remaining -= remainder
      if hp_remaining <= 0 and count > 0: count -= 1; hp_remaining = creature["hp"]
      return kills
    effective_attack: int (creature["attack"] + atk_modifier)
    effective_defense: int (creature["defense"] + def_modifier * (1.3 if is_defending else 1))

@dataclass CombatState:
  attacker_hero: dict (Hero data)
  defender_hero: dict (Hero data, or None for vs neutral creatures)
  attacker_stacks: list of CombatStack  (up to 7, placed left side)
  defender_stacks: list of CombatStack  (up to 7, placed right side)
  turn_order: list of CombatStack       (sorted by initiative desc, rebuilt each round)
  current_idx: int                      (index into turn_order)
  round: int
  combat_log: list of str               (last 10 events shown)
  
  Properties:
    active_stack: CombatStack
    all_alive_attacker: list of CombatStack
    all_alive_defender: list of CombatStack
    all_alive_stacks: list
    
  Methods:
    build_turn_order()
      Sort all alive stacks by initiative descending.
      Stacks with wait_flag=True go to end of list.
    
    advance_to_next()
      Increment current_idx. If past end → new round:
        round += 1, reset has_acted/has_retaliated/wait_flag on all, rebuild turn_order.
    
    get_stack_at(col, row) → CombatStack|None
    
    occupied_hexes() → dict of (col,row) → CombatStack
    
    enemy_hexes_of(stack) → set of (col,row)  (enemy side stacks' positions)

class CombatEngine:

  calculate_damage(attacker: CombatStack, defender: CombatStack) → int:
    atk_diff = attacker.effective_attack - defender.effective_defense
    if atk_diff >= 0:
      multiplier = 1.0 + 0.05 * atk_diff
    else:
      multiplier = 1.0 / (1.0 + 0.025 * abs(atk_diff))
    base_dmg = random.randint(attacker.creature["damage_min"], attacker.creature["damage_max"])
    total = int(base_dmg * attacker.count * multiplier)
    return max(1, total)

  do_melee_attack(state: CombatState, attacker: CombatStack, defender: CombatStack) → str:
    damage = calculate_damage(attacker, defender)
    killed = defender.take_damage(damage)
    attacker.has_acted = True
    log_msg = f"{attacker.count} {attacker.creature['name']} attack {defender.count+killed} {defender.creature['name']} for {damage} damage ({killed} killed)"
    
    # Retaliation: if defender alive and hasn't retaliated this round
    if defender.is_alive and not defender.has_retaliated and not attacker.creature.get("no_retaliation"):
      ret_dmg = calculate_damage(defender, attacker)
      ret_killed = attacker.take_damage(ret_dmg)
      defender.has_retaliated = True
      log_msg += f"\n  ↩ {defender.count+ret_killed} {defender.creature['name']} retaliate for {ret_dmg} ({ret_killed} killed)"
    
    state.combat_log.append(log_msg)
    return log_msg

  do_ranged_attack(state, attacker, defender) → str:
    # Same damage formula, NO retaliation
    damage = calculate_damage(attacker, defender)
    killed = defender.take_damage(damage)
    attacker.has_acted = True
    log_msg = f"{attacker.count} {attacker.creature['name']} shoot {defender.count+killed} {defender.creature['name']} for {damage} ({killed} killed)"
    state.combat_log.append(log_msg)
    return log_msg

  do_spell(state, caster_hero, spell_name, target_stack) → str:
    spell = SPELLS[spell_name]
    power = caster_hero["power"]
    
    if spell["effect_type"] == "damage":
      total_dmg = spell["base_value"] * power
      killed = target_stack.take_damage(total_dmg)
      return f"Hero casts {spell_name}! {total_dmg} damage to {target_stack.creature['name']} ({killed} killed)"
    
    elif spell["effect_type"] == "buff":
      if spell_name == "haste":
        target_stack.speed_override += 3
      elif spell_name == "bless":
        target_stack.creature["damage_min"] = target_stack.creature["damage_max"]
      elif spell_name == "bloodlust":
        target_stack.atk_modifier += 3
      elif spell_name == "stone_skin":
        target_stack.def_modifier += 3
      return f"Hero casts {spell_name} on {target_stack.creature['name']}"
    
    elif spell["effect_type"] == "debuff":
      if spell_name == "slow": target_stack.speed_override -= 3
      elif spell_name == "curse": target_stack.creature["damage_max"] = target_stack.creature["damage_min"]
      elif spell_name == "weakness": target_stack.atk_modifier -= 3
      return f"Hero casts {spell_name} on {target_stack.creature['name']}"

  check_victory(state) → None|"attacker"|"defender":
    if not any(s.is_alive for s in state.defender_stacks): return "attacker"
    if not any(s.is_alive for s in state.attacker_stacks): return "defender"
    return None

  setup_positions(state):
    # Place attacker stacks on left side (col 0-1), defender on right (col 13-14)
    attacker_rows = [1,3,5,7,9,2,4]
    defender_rows = [1,3,5,7,9,2,4]
    for i,stack in enumerate([s for s in state.attacker_stacks if s]):
      stack.hex_pos = (1, attacker_rows[i])
    for i,stack in enumerate([s for s in state.defender_stacks if s]):
      stack.hex_pos = (13, defender_rows[i])

═══════════════════════════════════════════
scenes/combat_screen.py — Battle scene
═══════════════════════════════════════════

LAYOUT (1280×800):
- TOP BAR (y=0 to y=44): "BATTLE: [attacker] vs [defender]", round counter
- GRID AREA (x=0 to x=840, y=44 to y=750): 15×11 hex grid
  Grid offset: grid_x = 20, grid_y = 60 (screen offset for hex (0,0) center)
- RIGHT PANEL (x=848 to x=1280, y=44 to y=800):
  - Active unit name + HP bar + stats (top 150px)
  - Battle log: last 8 events (middle area)
  - Action buttons (bottom):
      [WAIT] [DEFEND] [CAST SPELL] [RETREAT]

HEX GRID RENDER:
- For each hex (col 0-14, row 0-10):
    base_col = C_BG2 (dark slate)
    if hex reachable by active stack: overlay C_BLUE tint (semi-transparent rect)
    if hex is attackable target: overlay C_RED tint
    if hex has stack: draw creature sprite centered (use draw_creature from art)
    if active stack at this hex: draw gold pulse border
    Draw hex outline: thin grey lines (draw_hex with border)
    
- Grid visual helpers:
    Center line separator: thin grey vertical line between col 7 and 8 (battlefield midline)

PHASE STATE MACHINE:
state.phase: "player_move"|"player_attack"|"animating"|"ai_turn"|"spell_select"|"victory"|"defeat"

on_enter(attacker_hero, defender_hero=None, defender_stack=None):
  Build CombatState from hero armies
  If defender is a neutral stack (not hero): create single-stack defender side
  Call combat_engine.setup_positions(state)
  Build turn_order
  Set phase based on whether first stack belongs to player

"player_move" phase:
  - Compute reachable hexes for active stack
  - Mouse hover shows path as dotted line
  - Click reachable hex: move stack there (remove from occupied, add at new pos)
    After move: if adjacent to enemy → phase stays player_attack
                else → has_acted=True, advance_to_next(), determine next phase
  - Click enemy hex: if in melee/ranged range → go to attack
  - Click WAIT: stack.wait_flag=True, move to end of order, advance
  - Click DEFEND: stack.is_defending=True, has_acted=True, advance

"player_attack" phase:
  - Highlight attackable hexes in red
  - Click enemy stack: do_melee_attack or do_ranged_attack
  - Trigger "animating" phase (1.0s)

"animating" phase:
  - anim_timer counts down
  - On end: advance to next stack, set phase

"ai_turn" phase (active stack belongs to enemy):
  Simple AI:
    1. Find nearest player stack
    2. If creature is ranged and enemy visible: shoot (do_ranged_attack)
    3. Else if adjacent: melee attack
    4. Else: move toward nearest enemy (find_hex_path, move as far as speed allows)
  After AI action: advance, determine next phase
  Brief pause 0.4s between AI actions

"spell_select" phase:
  - Right panel shows spell list with mana costs
  - Valid targets highlighted on grid
  - Click target: cast spell, return to previous phase

"victory" / "defeat":
  - Overlay panel: "VICTORY!" or "DEFEATED"
  - Show losses for both sides (units killed)
  - XP gained (sum of tier*25 per enemy unit killed)
  - Continue button → back to adventure map, update hero armies

PROCEDURAL BATTLE BACKGROUND:
Draw before grid:
- Sky gradient: dark blue gradient (3 horizontal rect bands, slightly different blues)
- Ground line at y=580: brown/grey dividing sky from earth
- Rocky terrain texture at bottom 170px: scattered grey polygon shapes

ACTIVE STACK INDICATOR:
- Gold border on current stack's hex (draw_hex with C_GOLD border, animated brightness)
- Stack glows slightly (brighter color)

DAMAGE FLOATER:
- When damage dealt: create float entry {text, x, y, lifetime=1.5, color}
- Each frame: y -= 40*dt, lifetime -= dt, alpha = lifetime/1.5
- Draw on top of all other elements

RETREAT:
- Player can retreat: loses all troops, hero survives with no army
- SM.go("adventure_map") with hero army cleared

After building, test combat by walking player hero onto a neutral creature tile on the adventure map.
```

---

## PROMPT 3 — Town Screen

```
Adventure map and combat work. Now add the town screen to HeroForge.

Build scenes/town_screen.py.

═══════════════════════════════════════════
LAYOUT (full-screen overlay, 1280×800)
═══════════════════════════════════════════

HEADER (y=0 to y=56):
  Left: town name (large) + faction badge
  Center: day counter
  Right: X close button (returns to adventure map) + player gold display

LEFT PANEL — TOWN ILLUSTRATION (x=0 to x=640, y=56 to y=800):
  Procedural illustrated town background based on faction.
  Building icons overlay on the town image when built.

CENTER/RIGHT PANEL (x=640 to x=1280, y=56 to y=800):
  Two tabs: [BUILDINGS] [GARRISON]
  Tab content below.

═══════════════════════════════════════════
TOWN ILLUSTRATION (procedural art)
═══════════════════════════════════════════

CASTLE illustration (draw on a 640×744 surface at x=0, y=56):
  Sky: fill light blue (60,120,190) top half
  Ground: fill dark green (40,80,30) bottom 200px
  Stone wall: large grey polygon across full width at y=350
    Shape: flat top with 8 crenellations (each 20px wide, 20px tall notches)
    Fill: (110,105,100) with thin (90,85,80) outline
  Gate: dark rectangle (80px wide, 100px tall) centered at wall base
  Drawbridge: brown rect descending from gate
  2 round towers at x=100 and x=540, extending 50px above wall top:
    Circle r=50, fill (100,95,90), lighter grey top half
    Conical pointed roof: triangle above each tower, fill (140,30,30) (red)
  Banner/flag on each tower top: small rect on a line, faction color, slight sway animation
  Windows: small dark rectangles on towers
  Moat water: thin blue oval strip in front of gate
  Foreground grass: brighter green at bottom 100px

NECROPOLIS illustration:
  Sky: near-black purple (20,15,30)
  Ground: dark grey-brown (45,40,50)
  2-3 tall dark spires (narrow black polygons, tapering to sharp points)
    Spire 1: x=120, base at y=600, tip at y=160, width 60px at base
    Spire 2: x=380, base at y=620, tip at y=180, width 50px at base
    Spire 3: x=580, base at y=610, tip at y=240, width 40px at base
  Mist layer: 3 semi-transparent dark purple rectangles at ground level (y=580-680)
  Dead bare trees: brown branching lines (3-4 trees, each 2 branches with 2 sub-branches)
  Crypts: small dark trapezoid structures scattered at ground level
  Skull decorations: small circles + 2 dot eyes scattered on crypts and spire bases
  Eerie glow at spire tips: soft yellow/green circle (pulsing with t)

═══════════════════════════════════════════
BUILDINGS TAB
═══════════════════════════════════════════

Scrollable list of buildings grouped:
  Group 1: "Income" (Town Hall chain, Marketplace, etc.)
  Group 2: "Military" (Fort→Castle chain)
  Group 3: "Magic" (Mage Guild chain)
  Group 4: "Dwellings" (all 7 tier buildings + upgrades)
  Group 5: "Special" (Tavern, Blacksmith, Shipyard, etc.)

Each building entry (height=58, full width of right panel):
  Left icon: colored square matching building category
  Name: bold 15px
  Cost breakdown: show each resource with colored icon + amount
  Status indicator (right side):
    BUILT (green ✓): greyed background, no buttons
    LOCKED (grey lock): show "Requires: [prereq name]" in small red text
    AVAILABLE (can afford): bright BUILD button (gold border, clickable)
    CAN'T AFFORD (not enough resources): BUILD button disabled, show deficit in red

Scroll: mouse wheel scrolls the list. Show scrollbar on right.

On BUILD clicked:
  Deduct resources from player (STATE["player_resources"])
  Set town.buildings[building_name] = True
  Play simple "construction" sound (synthesized ding)
  Refresh building list display

═══════════════════════════════════════════
GARRISON TAB
═══════════════════════════════════════════

Upper section — RECRUITMENT (y=56 to y=500):
  For each of 7 creature tiers:
    Row height = 60px
    Left: creature sprite (from creature_art, 48×48)
    Center: creature name + tier badge
    Available: "Available: 12" (from town's current growth pool)
    Cost: "12 × 60 gold = 720"
    Right: [-] [count input] [+] buttons + RECRUIT button
    Disabled (grey) if dwelling not built or count=0

  Bottom of section: Running total "Total cost: 1,840 gold"
  RECRUIT ALL button (recruit maximum affordable from each dwelling)

Lower section — GARRISON (y=500 to y=800):
  Label "TOWN GARRISON"
  7 large slots (each 80px wide, showing creature sprite + count)
  Empty slots show grey outline + "Empty" text
  If a hero is in town: show "Hero Army" section above with hero's 7 slots
  Click to select slot, drag to rearrange (or just left/right arrow to shift)

═══════════════════════════════════════════
WEEKLY GROWTH MECHANIC
═══════════════════════════════════════════

Growth pool = accumulated weekly growth for each dwelling.
When player ends turn on day 7:
  town.start_new_week() is called for each town
  For each built dwelling: growth_pool[creature_key] += creature["weekly_growth"]
  Upgraded dwellings give 25% more growth.

Recruit draws from growth_pool — cannot exceed pool.
Un-recruited creatures DO accumulate (pool grows each week).

═══════════════════════════════════════════
INTEGRATION
═══════════════════════════════════════════

Connect to adventure_map.py:
  When player hero moves onto a town tile (or enters owned town):
    If town.owner == "player": SM.go("town_screen", town=town, hero=hero)
    If town.owner == "enemy": trigger combat against garrison

on_enter(town, hero=None):
  Store town and hero references
  Load building states from town.buildings
  Build growth pools

on_close():
  Any recruited units → add to hero.army if hero present, else garrison
  Return to SM.go("adventure_map")

Build this scene and connect it. After this prompt the game should be:
  Fully playable from map → enter town → build buildings → recruit units → close → fight on map.
```

---

## PROMPT 4 — Hero System + AI

```
Map, combat, and towns all work. Now add the full hero progression system and a working AI opponent.

═══════════════════════════════════════════
HERO SCREEN (scenes/hero_screen.py)
═══════════════════════════════════════════

Access: press H key on adventure map, or click hero portrait in bottom panel.

LAYOUT (full-screen):
  HEADER (y=0 to y=48): hero name + "Level X" + Close button

  LEFT PANEL (x=0 to x=400, y=48 to y=800):
    Large hero portrait (draw_hero_portrait, 200×200, centered)
    Name + faction + class
    XP bar: current/needed
    Primary stats with colored icons:
      ⚔ Attack: N      🛡 Defense: N
      🔮 Power: N      📚 Knowledge: N
    Movement: N/N remaining
    Mana: N/N remaining

  CENTER PANEL (x=400 to x=800, y=48 to y=800):
    Section "SECONDARY SKILLS" (top 350px):
      Up to 8 skill slots (or fewer if not learned yet)
      Each shows: skill icon (simple shape) + skill name + level badge (Basic/Advanced/Expert)
      Empty slots show grey outline + "—"
    Section "SPELLBOOK" (bottom 400px):
      Scrollable list of known spells
      Each row: spell name + school color dot + mana cost
      Click spell to see description in tooltip

  RIGHT PANEL (x=800 to x=1280, y=48 to y=800):
    Section "ARMY" (top 380px):
      7 army slots, each 52px tall
      Show: creature sprite + name + count + HP bar
      Empty = grey outline
    Section "ARTIFACTS" (bottom 380px):
      11 artifact slots in body shape layout:
        Row 1: Head (center)
        Row 2: Neck (center)
        Row 3: Torso (center)
        Row 4: Cloak (center)
        Row 5: Right Hand, Left Hand (side by side)
        Row 6: Ring 1, Ring 2 (side by side)
        Row 7: Boot (center)
        Row 8: Misc1, Misc2 (side by side)
      Each slot: 56×56, shows artifact name if equipped else slot icon
      Hover: tooltip with artifact bonus

═══════════════════════════════════════════
HERO LEVEL-UP SYSTEM
═══════════════════════════════════════════

XP thresholds:
  xp_next = round(1000 * level * 1.2)  for each level
  Level 1→2: 1000 XP, Level 2→3: 2400, Level 3→4: 4320... etc.

On level_up():
  level += 1
  Choose primary stat to increase:
    Castle heroes: 60% chance attack or defense, 40% power or knowledge
    Necropolis heroes: 50% power or knowledge, 50% attack or defense
  Increase chosen stat by 1
  Increase mana_max: knowledge * 10
  Show level-up popup:
    "LEVEL UP! Now Level N"
    "Primary stat +1: Attack is now X"
    "Choose a secondary skill:" → show 3 random options as buttons
    Player clicks to learn/improve one skill

Skill learning:
  If new skill: add to skills dict at level 1 (Basic)
  If existing skill level 1 → 2 (Advanced): +bonus effects
  If existing skill level 2 → 3 (Expert): +maximum bonus
  Max 8 secondary skills per hero

SECONDARY SKILL EFFECTS:
  Logistics:    Lv1=+10%, Lv2=+20%, Lv3=+30% movement points
  Archery:      Lv1=+10%, Lv2=+25%, Lv3=+50% ranged damage
  Leadership:   Lv1=+1, Lv2=+2, Lv3=+3 morale to all stacks
  Wisdom:       Lv1=can learn Lv3 spells, Lv2=Lv4, Lv3=Lv5
  Earth/Fire/Air/Water Magic: Lv1=+25%, Lv2=+50%, Lv3=+100% spell power for that school
  Tactics:      Place stacks anywhere on own side before battle starts (Lv1=3 rows, Lv2=4, Lv3=5)
  Offense:      Lv1=+10%, Lv2=+20%, Lv3=+30% melee damage
  Armorer:      Lv1=+5%, Lv2=+10%, Lv3=+15% damage reduction
  Luck:         Lv1=+1, Lv2=+2, Lv3=+3 luck (10% per point to deal double damage)
  Morale:       Same as Luck but for getting an extra move
  Scouting:     Lv1=+2, Lv2=+4, Lv3=+6 tiles vision radius
  Eagle Eye:    Lv1=20%, Lv2=40%, Lv3=60% chance to learn enemy spells cast in combat

Apply skill effects in combat_engine.py where relevant (check hero.skills dict).

═══════════════════════════════════════════
ARTIFACT SYSTEM
═══════════════════════════════════════════

Add 15 simple artifacts to data/artifacts.json:
  {
    "artifact_name": {
      "slot": "head"|"neck"|"torso"|"cloak"|"hand"|"ring"|"boot"|"misc",
      "bonus": {"attack":N,"defense":N,"power":N,"knowledge":N,"movement":N,"mana":N},
      "special": str (optional special ability description),
      "cost": int (for shop/random generation)
    }
  }

Examples:
  "Helm of Swift Mind": head, +2 knowledge, 1500g
  "Necklace of Swiftness": neck, +1 speed to all, 2000g
  "Armor of Wonder": torso, +1atk +1def +1pow +1kno, 10000g
  "Cape of Velocity": cloak, +1 speed, 1000g
  "Sword of Hellfire": hand, +3 attack, 3000g
  "Ring of Vitality": ring, +1 to all creature HP/unit, 2500g
  "Boots of Speed": boot, +2 movement, 1500g
  ...

When hero picks up artifact on map: add to appropriate slot (or backpack if full).
Apply artifact bonuses to hero stats at start of each battle.

═══════════════════════════════════════════
RESOURCE MANAGER (engine/resource_manager.py)
═══════════════════════════════════════════

class ResourceManager:
  RESOURCES = ["gold","wood","ore","mercury","sulfur","crystal","gems"]
  MINE_INCOME = {"gold_mine":1000,"wood_mine":2,"ore_mine":2,
                  "mercury_mine":1,"sulfur_mine":1,"crystal_mine":1,"gems_mine":1}
  
  @staticmethod
  def can_afford(player_resources, cost_dict) → bool
  
  @staticmethod
  def spend(player_resources, cost_dict) → bool
    # Returns False if can't afford, True + deducts if can
  
  @staticmethod
  def add(player_resources, income_dict)
  
  @staticmethod
  def daily_income(owned_mines) → dict
    # Sum up income from all mines with owner=="player"
  
  @staticmethod
  def apply_daily_income(player_resources, owned_mines)
    # Called once per day at start of player turn

HUD resource display (update adventure_map.py):
  When resources change: flash "+1000 gold" text briefly in HUD area

═══════════════════════════════════════════
AI OPPONENT (engine/ai_player.py)
═══════════════════════════════════════════

class AIPlayer:
  enemy_heroes: list
  enemy_towns: list

  def take_turn(state: STATE):
    """Called when adventure_map advances to enemy phase."""
    
    # For each enemy hero, in army strength descending order:
    for hero in sorted(enemy_heroes, key=lambda h: h.army_power(), reverse=True):
      if hero.movement_points <= 0:
        continue
      
      action = choose_action(hero, state)
      execute_action(hero, action, state)

  def choose_action(hero, state) → dict:
    """Priority-based decision making."""
    
    # Priority 1: If in a town, recruit and build
    town_at = get_town_at(hero.pos, state)
    if town_at and town_at.owner == "enemy":
      return {"type":"recruit_and_build","town":town_at}
    
    # Priority 2: If army is weak (< 30% of potential), go to nearest own town
    max_power = estimate_max_power(hero.faction)
    if hero.army_power() < max_power * 0.3:
      nearest_town = nearest_own_town(hero, state)
      if nearest_town:
        return {"type":"move_toward","target":nearest_town.pos,"reason":"restock"}
    
    # Priority 3: If nearest enemy hero within 12 tiles AND we're stronger, attack
    nearest_enemy = nearest_entity(hero, state.player_heroes)
    if nearest_enemy:
      dist = manhattan_distance(hero.pos, nearest_enemy.pos)
      if dist <= 12 and hero.army_power() > nearest_enemy.army_power() * 0.8:
        return {"type":"attack_hero","target":nearest_enemy}
    
    # Priority 4: Capture nearest uncaptured mine within 8 tiles
    nearest_mine = nearest_uncaptured_mine(hero, state.map_objects)
    if nearest_mine:
      dist = manhattan_distance(hero.pos, nearest_mine.pos)
      if dist <= 8:
        return {"type":"move_toward","target":nearest_mine.pos,"reason":"mine"}
    
    # Priority 5: Move toward nearest enemy town
    nearest_p_town = nearest_entity(hero, [t for t in state.towns if t.owner=="player"])
    if nearest_p_town:
      return {"type":"move_toward","target":nearest_p_town.pos,"reason":"attack_town"}
    
    # Default: explore (move toward unexplored tile)
    unexplored = find_nearest_unexplored(hero, state.tile_map)
    if unexplored:
      return {"type":"move_toward","target":unexplored,"reason":"explore"}
    
    return {"type":"wait"}

  def execute_action(hero, action, state):
    if action["type"] == "move_toward":
      # Pathfind toward target, move as many tiles as movement allows
      path = a_star(hero.pos, action["target"], state.tile_map)
      steps = min(len(path), tiles_hero_can_move(hero))
      move_hero_along_path(hero, path[:steps], state)
    
    elif action["type"] == "attack_hero":
      target = action["target"]
      path = a_star(hero.pos, target.pos, state.tile_map)
      if len(path) == 1:  # adjacent
        trigger_combat(hero, target, state)  # launches combat_screen, AI side resolves
      else:
        steps = min(len(path)-1, tiles_hero_can_move(hero))
        move_hero_along_path(hero, path[:steps], state)
    
    elif action["type"] == "recruit_and_build":
      town = action["town"]
      # Build cheapest affordable military building
      for building in affordable_buildings(town, state.enemy_resources):
        if building["category"] in ("dwelling","military"):
          town.build(building["name"])
          break
      # Recruit half of available creatures
      for creature_key, available in town.available_to_recruit().items():
        cost_per = CREATURES[creature_key]["cost"]
        can_buy = min(available, state.enemy_resources["gold"] // cost_per // 2 + 1)
        if can_buy > 0:
          town.recruit(creature_key, can_buy)
          hero.add_to_army(creature_key, can_buy)

  def ai_combat_action(combat_state, ai_stack):
    """Called during combat when it's an AI-controlled stack's turn."""
    if not ai_stack.is_alive: return
    
    # Ranged AI: shoot nearest enemy
    if ai_stack.creature["is_ranged"]:
      targets = get_ranged_targets(ai_stack.hex_pos, enemy_hexes(ai_stack, combat_state))
      if targets:
        nearest = min(targets, key=lambda pos: hex_distance(ai_stack.hex_pos, pos))
        target_stack = combat_state.get_stack_at(*nearest)
        if target_stack:
          combat_engine.do_ranged_attack(combat_state, ai_stack, target_stack)
          return
    
    # Melee AI: find and attack nearest enemy
    enemy_positions = enemy_hexes(ai_stack, combat_state)
    if not enemy_positions: return
    
    nearest_enemy_pos = min(enemy_positions, key=lambda p: hex_distance(ai_stack.hex_pos, p))
    if hex_distance(ai_stack.hex_pos, nearest_enemy_pos) <= 1:
      target = combat_state.get_stack_at(*nearest_enemy_pos)
      if target:
        combat_engine.do_melee_attack(combat_state, ai_stack, target)
    else:
      # Move toward nearest enemy
      path = find_hex_path(ai_stack.hex_pos, nearest_enemy_pos, 
                           blocked={s.hex_pos for s in combat_state.all_alive_stacks if s != ai_stack})
      speed = ai_stack.effective_speed
      if path:
        new_pos = path[min(speed-1, len(path)-2)]  # stop adjacent to target if possible
        ai_stack.hex_pos = new_pos
      ai_stack.has_acted = True

═══════════════════════════════════════════
VICTORY CONDITIONS
═══════════════════════════════════════════

Check after each end of enemy turn in adventure_map.py:

def check_victory(state) → None|"player"|"enemy":
  player_alive = len(state.player_heroes) > 0 or any(t.owner=="player" for t in state.towns)
  enemy_alive  = len(state.enemy_heroes) > 0 or any(t.owner=="enemy" for t in state.towns)
  if not enemy_alive:  return "player"
  if not player_alive: return "enemy"
  return None

If victory:
  SM.go("end_screen", result="victory"|"defeat")

Create scenes/end_screen.py:
  Show "VICTORY!" or "DEFEAT" in large text
  Show stats: turns played, enemies defeated, towns captured
  Show final hero stats (level reached, spells learned)
  Buttons: "New Game" → SM.go("main_menu"), "Quit"

After this prompt the game is a complete playable loop:
  Map → Town (build + recruit) → Move → Combat → Level up → AI fights back → Victory/Defeat.
```

---

## PROMPT 5 — Polish + Save/Load

```
The core game loop works. Now polish HeroForge into a finished game.

═══════════════════════════════════════════
1. SMOOTH HERO MOVEMENT ANIMATION
═══════════════════════════════════════════

In adventure_map.py, replace instant teleport with smooth tile-to-tile animation:

class HeroMoveAnimation:
  hero: Hero
  path: list of (x,y)
  current_step: int
  progress: float (0.0 to 1.0)
  speed: float = 3.0  (tiles per second)
  
  def update(dt):
    progress += dt * speed
    if progress >= 1.0:
      hero.pos = path[current_step]
      current_step += 1
      progress = 0.0
    if current_step >= len(path): done = True
  
  def draw_pos() → (px, py):
    start = tile_to_pixel(path[current_step - 1])
    end   = tile_to_pixel(path[current_step])
    return lerp(start, end, progress)

Block player input while animation is playing.
Show movement path as faded dotted line before confirming.

═══════════════════════════════════════════
2. COMBAT ANIMATIONS
═══════════════════════════════════════════

In combat_screen.py:

class AttackAnimation:
  Attacker stack moves toward defender by 1/3 of the distance (0.3s), then returns (0.2s).
  Use lerp between home_hex_pixel and target_hex_pixel.

class DamageFlash:
  Defender hex flashes white for 0.15s when hit.
  Then fades back to normal color.

class SpellEffect:
  "damage" spells: expanding circle at target hex (r grows 0→30 over 0.4s, fades)
  "buff" spells: rising green particles from target
  "debuff" spells: falling purple particles on target

class StackDeathAnimation:
  When a stack dies: scale creature sprite down to 0 over 0.5s, then remove.
  Scatter 5-8 small grey particles outward.

class FloatingText:
  Damage numbers float up and fade (already partially done, polish this).
  Also: "MISSED!", "IMMUNE!", spell names when cast.

═══════════════════════════════════════════
3. SYNTHESIZED SOUND EFFECTS
═══════════════════════════════════════════

Create engine/sound_engine.py using pygame.sndarray + numpy:

def make_sound(freq, duration, wave="sine", volume=0.3, fade_out=True) → pygame.Sound:
  sample_rate = 44100
  t = numpy.linspace(0, duration, int(sample_rate * duration))
  if wave == "sine":    wave_data = numpy.sin(2 * numpy.pi * freq * t)
  elif wave == "square": wave_data = numpy.sign(numpy.sin(2 * numpy.pi * freq * t))
  elif wave == "noise":  wave_data = numpy.random.uniform(-1, 1, len(t))
  if fade_out:
    envelope = numpy.linspace(1, 0, len(t)) ** 2
    wave_data *= envelope
  wave_data = (wave_data * 32767 * volume).astype(numpy.int16)
  stereo = numpy.column_stack([wave_data, wave_data])
  sound = pygame.sndarray.make_sound(stereo)
  return sound

SOUNDS dict (create once at startup, store in STATE):
  "click":        make_sound(800, 0.08, "sine", 0.2)
  "move":         make_sound(400, 0.12, "sine", 0.15)  — softer, lower
  "sword_hit":    mix of two sounds: make_sound(200,0.1,"square") + make_sound(1500,0.05,"noise")
  "spell_cast":   rising tone: freq sweeps 300→900 Hz over 0.4s
  "gold_pickup":  make_sound(1200, 0.2, "sine", 0.3) + make_sound(1500, 0.15, "sine", 0.2) (layered)
  "build":        make_sound(600, 0.3, "sine", 0.3) fades out slowly
  "victory":      short melody: 523Hz(0.2s) + 659Hz(0.2s) + 784Hz(0.4s) (C,E,G triad)
  "defeat":       descending: 400Hz(0.3s) + 300Hz(0.3s) + 200Hz(0.5s)
  "level_up":     ascending arpeggiated: 440,554,659,880 Hz, each 0.15s

Play sounds at appropriate moments (button click, hero move, attack, spell, etc.)
If numpy not available: skip sounds gracefully with try/except.

═══════════════════════════════════════════
4. MINIMAP (art/minimap.py)
═══════════════════════════════════════════

class Minimap:
  rect: pygame.Rect (positioned bottom-right of adventure map, 160×120)
  
  def draw(surf, tile_map, heroes, towns, camera_pos):
    # Background
    pygame.draw.rect(surf, C_BG0, rect)
    pygame.draw.rect(surf, C_BDR, rect, 1)
    
    px_per_tile_x = rect.width  / tile_map.width
    px_per_tile_y = rect.height / tile_map.height
    
    # Draw terrain (1px per tile)
    for y in range(tile_map.height):
      for x in range(tile_map.width):
        tile = tile_map.get(x,y)
        if not tile.is_explored:
          col = (10,10,10)
        else:
          col = TERR_COLORS[tile.terrain_type]
          if not tile.is_visible:
            col = tuple(c//2 for c in col)  # darken unexplored
        px = rect.x + int(x * px_per_tile_x)
        py = rect.y + int(y * px_per_tile_y)
        surf.set_at((px, py), col)
    
    # Towns: small squares
    for town in towns:
      tx = rect.x + int(town.pos[0] * px_per_tile_x)
      ty = rect.y + int(town.pos[1] * px_per_tile_y)
      col = (0,100,255) if town.owner=="player" else (200,0,0) if town.owner=="enemy" else (150,150,150)
      pygame.draw.rect(surf, col, (tx-2, ty-2, 4, 4))
    
    # Heroes: dots
    for hero in heroes:
      hx = rect.x + int(hero.pos[0] * px_per_tile_x)
      hy = rect.y + int(hero.pos[1] * px_per_tile_y)
      col = (100,200,255) if hero.owner=="player" else (255,100,100)
      pygame.draw.circle(surf, col, (hx,hy), 2)
    
    # Camera viewport rectangle
    cam_rect = pygame.Rect(
      rect.x + int(camera_pos[0] * px_per_tile_x),
      rect.y + int(camera_pos[1] * px_per_tile_y),
      int((SW // TILE_SIZE) * px_per_tile_x),
      int(((SH-56-120) // TILE_SIZE) * px_per_tile_y)
    )
    pygame.draw.rect(surf, C_GOLD, cam_rect, 1)
    
    # Click minimap to scroll main view to that location
    # (handle in adventure_map.py handle() method)

═══════════════════════════════════════════
5. SAVE / LOAD SYSTEM (engine/save_load.py)
═══════════════════════════════════════════

SAVE_FILE = "heroforge_save.json"

def save_game(state):
  data = {
    "day": state["day"], "week": state["week"], "month": state["month"],
    "player_resources": state["player_resources"],
    "player_heroes": [serialize_hero(h) for h in state["player_heroes"]],
    "enemy_heroes":  [serialize_hero(h) for h in state["enemy_heroes"]],
    "towns": [serialize_town(t) for t in state["towns"]],
    "map_objects": [serialize_obj(o) for o in state["map_objects"]],
    "tile_explored": [[state["tile_map"].get(x,y).is_explored for x in range(32)] for y in range(32)],
  }
  with open(SAVE_FILE, "w") as f:
    json.dump(data, f, indent=2)

def load_game() → dict|None:
  if not os.path.exists(SAVE_FILE): return None
  with open(SAVE_FILE) as f:
    return json.load(f)
  # Reconstruct STATE from loaded data

def serialize_hero(hero) → dict:
  # Convert Hero object to plain dict (all fields serializable)
  # army: list of {creature_key, count, hp_remaining} or null

Connect to main_menu.py:
  "Load Game" → try load_game(), show "No save found" message if file missing

Connect to adventure_map.py:
  Ctrl+S → save_game(STATE)
  Show "Game Saved" flash message for 2 seconds

═══════════════════════════════════════════
6. SCENARIO ENRICHMENT
═══════════════════════════════════════════

Update data/scenario.json to have a richer, more interesting 32×32 map:

Terrain features:
  - River of water tiles running diagonally from (0,15) to (20,5), 2 tiles wide
  - Mountain range (rock tiles) along eastern edge x=28-31
  - Forest patches (rough terrain) at 4-5 locations
  - Desert patch (sand tiles) in southwest corner
  - Snow terrain in northeast corner

Object placement:
  - 2 "shortcut" crossing points in the river (passable tiles)
  - Neutral towns at (15,15) flanked by level 3-4 creature stacks (guards)
  - 10 neutral creature stacks guarding mines, varied tier 1-5
  - 3 artifact locations in hard-to-reach places (past water or creature guards)
  - 2 obelisk locations (they reveal map area when visited)
  - Shipyard near river for water travel

Starting heroes:
  Player: Knight hero (Castle), starts with 10 pikemen + 5 archers, Logistics skill
  Enemy:  Death Knight (Necropolis), starts with 20 skeletons + 5 walking dead, Earth Magic skill

═══════════════════════════════════════════
7. POLISH CHECKLIST
═══════════════════════════════════════════

After implementing above features, run through this checklist:

UI/UX:
  [ ] All buttons have hover states (lighter color)
  [ ] All interactive elements have cursor change (pygame.SYSTEM_CURSOR_HAND)
  [ ] Resource amounts never go negative (clamp in spend())
  [ ] Tooltip on every creature (name, stats) on hover
  [ ] Tooltip on buildings (effect + cost) on hover
  [ ] Loading screen while generating new game (brief splash with "Loading...")

Combat:
  [ ] Turn order panel always visible in right panel
  [ ] Ranged units can't shoot into melee if adjacent enemy (penalty or block)
  [ ] Spells grayed out if not enough mana
  [ ] Retreat confirmation dialog ("Are you sure? You will lose all troops.")

Adventure Map:
  [ ] Camera smooth scroll when following hero
  [ ] "Next Hero" button (Tab key) cycles through heroes with movement remaining
  [ ] Hero exhausted indicator (grey out portrait when no movement)
  [ ] Right-click on map object shows info tooltip (not action)

Town:
  [ ] Hover over creature in recruitment shows full stats panel
  [ ] Gold display in header updates live when spending in recruitment
  [ ] Buildings greyed correctly when prerequisites unmet

Performance:
  [ ] Cache terrain tile renders (redraw only when camera moves or fog changes)
  [ ] Limit fog-of-war recalculation to once per hero move (not every frame)

Final check: play for at least 10 turns, verify AI makes sensible moves,
one complete combat runs correctly, town building + recruitment works,
save/load preserves full game state.
```

---

## NOTES FOR BEST RESULTS

**Session length**: Each prompt typically takes 20-40 minutes of Claude Code work.
If a session gets interrupted, start a new session and paste: 
"Continue building HeroForge — here's where we left off: [describe what was completed]"

**Testing after each session**:
- Session 1: `python main.py` → map appears, hero moves, fog works
- Session 2: Walk hero onto creature tile → combat opens, can fight
- Session 3: Walk hero into town → town screen opens, can build
- Session 4: Hero levels up, enemy AI moves on its turn
- Session 5: Ctrl+S saves, music plays, smooth animations

**If something breaks**: Ask Claude Code to "Fix the error in [filename]: [paste error message]"

**Extending the game later**:
- Add faction 3 (Tower: mage/wizard theme) → copy Necropolis structure in creatures.json + buildings.json
- Add campaign: create campaign.json with 5 scenario entries, add campaign_map.py scene
- Add multiplayer: split end-turn into 2 player phases with separate fog-of-war
- Add random map generator: engine/mapgen.py using cellular automata for terrain
