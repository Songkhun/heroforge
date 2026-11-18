"""Victory / defeat screen with game statistics."""
import math
import random

import pygame

import main
from config import SW, SH, C_BG1, C_BG2, C_BDR, C_GOLD, C_TXT, C_SUB, C_HINT, C_RED, C_GRN
from art.ui_art import Button, blit, panel
from art import hero_art
from engine import world
from scenes.scene_manager import SM


class EndScreen:
    def __init__(self):
        self.t = 0.0
        self.sparks = []

    def on_enter(self, result="victory", **kw):
        F = main.F
        self.result = result
        self.t = 0.0
        self.sparks = [[random.uniform(0, SW), random.uniform(0, SH), random.uniform(-30, 30),
                        random.uniform(20, 80), random.uniform(0, 6.28)] for _ in range(90)]
        self.btn_new = Button((SW // 2 - 230, SH - 110, 210, 50), "New Game", F["md"], (60, 45, 20),
                              hov=(95, 70, 25), tc=C_GOLD, bdr=C_GOLD)
        self.btn_quit = Button((SW // 2 + 20, SH - 110, 210, 50), "Quit", F["md"])
        S = main.STATE
        heroes = S["player_heroes"]
        # best surviving hero, or remember none
        self.hero = max(heroes, key=lambda h: (h.level, h.xp)) if heroes else None
        from engine import sound_engine
        sound_engine.play("victory" if result == "victory" else "defeat")

    def update(self, dt):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] -= s[3] * dt if self.result == "victory" else -s[3] * dt * 0.5
            if s[1] < -10:
                s[1] = SH + 10
            elif s[1] > SH + 10:
                s[1] = -10
        mx, my = pygame.mouse.get_pos()
        self.btn_new.update(mx, my)
        self.btn_quit.update(mx, my)

    def handle(self, ev):
        if self.btn_new.clicked(ev):
            SM.go("main_menu")
        elif self.btn_quit.clicked(ev):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def draw(self, surf):
        F, S = main.F, main.STATE
        win = self.result == "victory"
        col = C_GOLD if win else C_RED
        for x, y, vx, vy, ph in self.sparks:
            b = 0.5 + 0.5 * math.sin(self.t * 3 + ph)
            c = (int(255 * b), int(200 * b), 80) if win else (int(120 * b), int(60 * b), int(140 * b))
            pygame.draw.circle(surf, c, (int(x), int(y)), 2)
        title = F["title"].render("VICTORY!" if win else "DEFEAT", True, col)
        title = pygame.transform.smoothscale_by(title, 1.5 + 0.03 * math.sin(self.t * 2))
        surf.blit(title, title.get_rect(center=(SW // 2, 110)))
        sub = "The enemy has been vanquished." if win else "Your realm has fallen."
        blit(surf, sub, F["md"], C_SUB, SW // 2, 160, "center")
        st = S.get("stats", {})
        box = panel(surf, (SW // 2 - 420, 210, 400, 330), C_BG1, C_BDR, br=12)
        blit(surf, "CAMPAIGN", F["md"], C_GOLD, box.x + 20, box.y + 16)
        rows = [("Days played", world.days_played(S)),
                ("Battles won", st.get("battles_won", 0)),
                ("Battles lost", st.get("battles_lost", 0)),
                ("Enemy heroes defeated", st.get("enemy_heroes_defeated", 0)),
                ("Enemy creatures slain", st.get("creatures_killed", 0)),
                ("Towns captured", st.get("towns_captured", 0)),
                ("Mines captured", st.get("mines_captured", 0))]
        for i, (k, v) in enumerate(rows):
            y = box.y + 58 + i * 36
            blit(surf, k, F["sm"], C_SUB, box.x + 20, y)
            blit(surf, f"{v:,}", F["md"], C_TXT, box.right - 20, y - 3, "right")
        hb = panel(surf, (SW // 2 + 20, 210, 400, 330), C_BG1, C_BDR, br=12)
        blit(surf, "YOUR HERO", F["md"], C_GOLD, hb.x + 20, hb.y + 16)
        h = self.hero
        if h:
            hero_art.draw_hero_portrait(surf, (hb.x + 20, hb.y + 56, 110, 110), h.faction, None)
            blit(surf, h.name, F["lg"], C_TXT, hb.x + 146, hb.y + 60)
            blit(surf, f"Level {h.level} {h.hero_class}", F["sm"], C_SUB, hb.x + 146, hb.y + 96)
            blit(surf, f"ATK {h.stat('attack')}  DEF {h.stat('defense')}  PWR {h.stat('power')}  KNW {h.stat('knowledge')}",
                 F["ti"], C_TXT, hb.x + 146, hb.y + 124)
            skills = ", ".join(f"{n} {lvl}" for n, lvl in h.skills.items()) or "none"
            spells = ", ".join(h.spells) or "none"
            from art.ui_art import blit_wrap
            yy = hb.y + 184
            yy += blit_wrap(surf, f"Skills: {skills}", F["ti"], C_SUB, hb.x + 20, yy, hb.w - 40)
            blit_wrap(surf, f"Spells learned ({len(h.spells)}): {spells}", F["ti"], C_SUB, hb.x + 20, yy + 6, hb.w - 40)
        else:
            blit(surf, "No hero survived.", F["sm"], C_HINT, hb.x + 20, hb.y + 70)
        self.btn_new.draw(surf)
        self.btn_quit.draw(surf)
