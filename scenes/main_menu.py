"""Title screen: New Game / Load Game / Quit over drifting stars."""
import math
import os
import random

import pygame

import main
from config import SW, SH, C_BG1, C_BG2, C_GOLD, C_SUB, C_HINT, C_RED, C_TXT
from art.ui_art import Button, blit
from scenes.scene_manager import SM

SAVE_FILE = "heroforge_save.json"


class MainMenu:
    def __init__(self):
        self.t = 0.0
        self.stars = [[random.uniform(0, SW), random.uniform(0, SH),
                       random.uniform(6, 30), random.uniform(0.6, 2.2), random.uniform(0, 6.28)]
                      for _ in range(140)]
        self.buttons = None
        self.msg = ""
        self.msg_t = 0.0

    def on_enter(self, **kw):
        F = main.F
        bw, bh, x = 280, 54, SW // 2 - 140
        self.buttons = {
            "new": Button((x, 380, bw, bh), "New Game", F["md"], C_BG2, tc=C_GOLD, bdr=C_GOLD),
            "load": Button((x, 450, bw, bh), "Load Game", F["md"], C_BG2),
            "quit": Button((x, 520, bw, bh), "Quit", F["md"], C_BG2),
        }
        self.msg = kw.get("message", "")
        self.msg_t = 3.0 if self.msg else 0

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        for s in self.stars:
            s[1] -= s[2] * dt
            if s[1] < 0:
                s[0], s[1] = random.uniform(0, SW), SH
        mx, my = pygame.mouse.get_pos()
        for b in self.buttons.values():
            b.update(mx, my)

    def draw(self, surf):
        for x, y, spd, r, ph in self.stars:
            b = int(140 + 110 * (0.5 + 0.5 * math.sin(self.t * 2 + ph)))
            pygame.draw.circle(surf, (b, b, min(255, b + 30)), (int(x), int(y)), max(1, int(r)))
        F = main.F
        glow = 0.5 + 0.5 * math.sin(self.t * 1.5)
        title_col = tuple(int(c * (0.85 + 0.15 * glow)) for c in C_GOLD)
        big = pygame.transform.smoothscale_by(F["title"].render("HeroForge", True, title_col), 1.6)
        surf.blit(big, big.get_rect(center=(SW // 2, 210)))
        blit(surf, "A Strategy Game", F["md"], C_SUB, SW // 2, 270, "center")
        pygame.draw.line(surf, C_BG2, (SW // 2 - 200, 320), (SW // 2 + 200, 320), 1)
        for b in self.buttons.values():
            b.draw(surf)
        if self.msg_t > 0:
            blit(surf, self.msg, F["sm"], C_RED, SW // 2, 595, "center")
        blit(surf, "WASD scroll · click twice to move · H hero · T towns · Tab next hero · Enter end turn · Ctrl+S save",
             F["ti"], C_HINT, SW // 2, SH - 30, "center")

    def handle(self, ev):
        if self.buttons["new"].clicked(ev):
            SM.go("loading", task="new_game")
        elif self.buttons["load"].clicked(ev):
            self.load_game()
        elif self.buttons["quit"].clicked(ev):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def load_game(self):
        if not os.path.exists(os.path.join(main.BASE_DIR, SAVE_FILE)):
            self.msg, self.msg_t = "No save found", 2.5
            return
        try:
            from engine import save_load
        except ImportError:
            self.msg, self.msg_t = "Loading saves isn't available yet", 2.5
            return
        try:
            state = save_load.load_game()
        except (OSError, ValueError, KeyError, TypeError):
            self.msg, self.msg_t = "The save file is damaged and can't be loaded.", 3
            return
        if not state:
            self.msg, self.msg_t = "No save found", 2.5
            return
        main.STATE.clear()
        main.STATE.update(state)
        SM.go("adventure_map", new_game=True, loaded=True,
              messages=[f"Game loaded — Day {state['day']}, Week {state['week']}, Month {state['month']}."])
