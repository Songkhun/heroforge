"""HeroForge entry point: data loading, global STATE and fonts, game loop.

Scenes use `import main` and read main.STATE / main.F / main.CREATURES at runtime.
"""
import sys

# When run as `python main.py` this module is `__main__`; alias it so `import main`
# elsewhere returns this same module instead of loading a second copy with new globals.
sys.modules.setdefault("main", sys.modules[__name__])

import json
import os

import pygame

from config import SW, SH, FPS, C_BG0
from engine.creature import load_creatures_data
from engine.town import load_buildings_data
from engine.combat_engine import load_spells_data
from engine.hero import load_artifacts_data
from engine import world

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


# Data tables, loaded once. These are the same dict objects the engine modules use.
CREATURES = load_creatures_data(os.path.join(DATA_DIR, "creatures.json"))
BUILDINGS = load_buildings_data(os.path.join(DATA_DIR, "buildings.json"))
SPELLS = load_spells_data(os.path.join(DATA_DIR, "spells.json"))
ARTIFACTS = load_artifacts_data(os.path.join(DATA_DIR, "artifacts.json"))
SCENARIO = _load_json("scenario.json")

# Game state; mutated in place so every module holding a reference sees updates.
STATE = {}
F = {}   # fonts, filled by init_fonts() after pygame.init()


def new_game():
    STATE.clear()
    STATE.update(world.new_game_state(SCENARIO))
    return STATE


def init_fonts():
    face = "arial,helvetica,dejavusans"
    F.update({
        "title": pygame.font.SysFont(face, 48, bold=True),
        "lg": pygame.font.SysFont(face, 28, bold=True),
        "md": pygame.font.SysFont(face, 20, bold=True),
        "sm": pygame.font.SysFont(face, 15),
        "ti": pygame.font.SysFont(face, 13),
    })


def register_scenes():
    from scenes.scene_manager import SM
    from scenes.main_menu import MainMenu
    from scenes.adventure_map import AdventureMap
    from scenes.combat_screen import CombatScreen
    from scenes.town_screen import TownScreen
    from scenes.hero_screen import HeroScreen
    from scenes.end_screen import EndScreen
    from scenes.loading_screen import LoadingScreen
    SM.register("main_menu", MainMenu())
    SM.register("adventure_map", AdventureMap())
    SM.register("combat_screen", CombatScreen())
    SM.register("town_screen", TownScreen())
    SM.register("hero_screen", HeroScreen())
    SM.register("end_screen", EndScreen())
    SM.register("loading", LoadingScreen())
    return SM


def run():
    from art.ui_art import apply_cursor
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("HeroForge")
    init_fonts()
    new_game()
    SM = register_scenes()
    SM.go("loading", task="startup")
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            else:
                SM.handle(ev)
        SM.update(dt)
        apply_cursor()
        screen.fill(C_BG0)
        SM.draw(screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    run()
