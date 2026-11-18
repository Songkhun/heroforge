"""Brief "Loading..." splash while sounds are synthesized or a new game is built."""
import math

import pygame

import main
from config import SW, SH, C_GOLD, C_SUB
from art.ui_art import blit
from engine import sound_engine
from scenes.scene_manager import SM


class LoadingScreen:
    def __init__(self):
        self.t = 0.0
        self.frames = 0
        self.task = "startup"

    def on_enter(self, task="startup", **kw):
        self.task, self.frames, self.t = task, 0, 0.0

    def update(self, dt):
        self.t += dt
        self.frames += 1
        if self.frames == 3:   # let "Loading..." reach the screen first
            sound_engine.init_sounds()
            if self.task == "new_game":
                main.new_game()
                SM.go("adventure_map", new_game=True)
            else:
                SM.go("main_menu")

    def handle(self, ev):
        pass

    def draw(self, surf):
        F = main.F
        blit(surf, "HeroForge", F["title"], C_GOLD, SW // 2, SH // 2 - 80, "center")
        blit(surf, "Loading" + "." * (1 + self.frames % 3), F["md"], C_SUB, SW // 2, SH // 2, "center")
        for i in range(8):
            a = self.t * 4 + i * math.pi / 4
            c = int(80 + 175 * (i / 7))
            pygame.draw.circle(surf, (c, c * 3 // 4, 40), (int(SW // 2 + math.cos(a) * 26),
                                                           int(SH // 2 + 70 + math.sin(a) * 26)), 4)
