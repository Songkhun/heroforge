"""Global constants: screen, colors, map and gameplay tuning."""

SW, SH, FPS = 1280, 800, 60

# UI colors
C_BG0 = (12, 16, 24)
C_BG1 = (22, 28, 42)
C_BG2 = (32, 40, 60)
C_BDR = (55, 70, 105)
C_GOLD = (255, 195, 55)
C_TXT = (220, 228, 242)
C_SUB = (140, 158, 195)
C_HINT = (85, 102, 140)
C_GRN = (68, 200, 115)
C_RED = (215, 75, 75)
C_BLUE = (95, 180, 255)
C_PURP = (175, 110, 255)

# Terrain colors
TERR_GRASS = (55, 100, 45)
TERR_DIRT = (140, 100, 65)
TERR_WATER = (35, 70, 160)
TERR_ROCK = (90, 90, 105)
TERR_SNOW = (210, 215, 225)
TERR_LAVA = (180, 60, 20)
TERR_SAND = (195, 170, 100)
TERR_SWAMP = (60, 90, 60)
TERR_ROUGH = (35, 75, 35)

# Resource icon colors
RES_GOLD = (255, 210, 50)
RES_WOOD = (140, 95, 50)
RES_ORE = (150, 140, 130)
RES_MERCURY = (180, 70, 180)
RES_SULFUR = (210, 190, 50)
RES_CRYSTAL = (120, 180, 220)
RES_GEMS = (60, 185, 100)

RESOURCES = ["gold", "wood", "ore", "mercury", "sulfur", "crystal", "gems"]
RES_COLORS = {"gold": RES_GOLD, "wood": RES_WOOD, "ore": RES_ORE, "mercury": RES_MERCURY,
              "sulfur": RES_SULFUR, "crystal": RES_CRYSTAL, "gems": RES_GEMS}
START_RESOURCES = {"gold": 2000, "wood": 20, "ore": 20,
                   "mercury": 2, "sulfur": 2, "crystal": 2, "gems": 2}
MINE_INCOME = {"gold": 1000, "wood": 2, "ore": 2,
               "mercury": 1, "sulfur": 1, "crystal": 1, "gems": 1}

# Faction colors
CASTLE_COL = (180, 160, 100)
NECROPOLIS_COL = (90, 80, 130)
FACTION_COLORS = {"castle": CASTLE_COL, "necropolis": NECROPOLIS_COL}
OWNER_COLORS = {"player": C_BLUE, "enemy": C_RED, "neutral": (150, 150, 150)}

# Adventure map
TILE_SIZE = 48
VISION_RADIUS = 5
HUD_H = 56                 # top HUD height
MAP_BOTTOM = 680           # bottom panel starts here
MAP_VIEW_H = MAP_BOTTOM - HUD_H

# Movement cost per terrain; None = impassable.
# grass/dirt/rough/rock/water come from the spec; the rest are our own choices.
TERRAIN_COST = {"grass": 1, "dirt": 1, "rough": 2, "rock": 3, "water": None,
                "snow": 2, "sand": 2, "swamp": 3, "lava": 2}

# Hero movement points per day: base + slowest-creature bonus (see Hero.refresh_movement)
HERO_BASE_MOVEMENT = 12
