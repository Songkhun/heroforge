"""Hero map token and portrait."""
import math

import pygame

from config import FACTION_COLORS, C_RED, C_GOLD, C_BG2, C_BDR, C_TXT
from art.ui_art import blit


def _sword(surf, cx, cy, s, col):
    pygame.draw.line(surf, col, (cx, cy - s), (cx, cy + s * 0.6), max(2, int(s / 4)))
    pygame.draw.line(surf, col, (cx - s * 0.45, cy + s * 0.25), (cx + s * 0.45, cy + s * 0.25), max(2, int(s / 5)))


def _skull(surf, cx, cy, s, col):
    pygame.draw.circle(surf, col, (int(cx), int(cy - s * 0.15)), int(s * 0.6))
    pygame.draw.rect(surf, col, (cx - s * 0.35, cy + s * 0.2, s * 0.7, s * 0.45))
    for ex in (-0.25, 0.25):
        pygame.draw.circle(surf, (20, 15, 25), (int(cx + ex * s), int(cy - s * 0.15)), max(1, int(s * 0.17)))


def faction_symbol(surf, cx, cy, s, faction, col):
    (_skull if faction == "necropolis" else _sword)(surf, cx, cy, s, col)


def draw_hero_on_map(surf, cx, cy, faction, owner, t, selected=False):
    """Round banner token: faction color for the player, red for the enemy."""
    cy = cy + math.sin(t * 2) * 2
    col = FACTION_COLORS.get(faction, (150, 150, 150)) if owner == "player" else C_RED
    r = 15
    pygame.draw.ellipse(surf, (20, 25, 20), (cx - 13, cy + 14, 26, 7))   # ground shadow
    pygame.draw.circle(surf, (25, 25, 35), (int(cx), int(cy)), r + 2)
    pygame.draw.circle(surf, col, (int(cx), int(cy)), r)
    ring = C_GOLD if selected else (240, 240, 250)
    pygame.draw.circle(surf, ring, (int(cx), int(cy)), r, 2)
    faction_symbol(surf, cx, cy, 9, faction, (250, 248, 240))
    if selected:
        pulse = 0.5 + 0.5 * math.sin(t * 5)
        pygame.draw.circle(surf, C_GOLD, (int(cx), int(cy)), int(r + 4 + pulse * 2), 1)


def draw_hero_portrait(surf, rect, faction, name, font=None, owner="player"):
    """Simple face in a framed panel, faction symbol above the head."""
    rect = pygame.Rect(rect)
    col = FACTION_COLORS.get(faction, (150, 150, 150))
    pygame.draw.rect(surf, C_BG2, rect, border_radius=8)
    bg = tuple(int(c * 0.45) for c in col)
    pygame.draw.rect(surf, bg, rect.inflate(-6, -6), border_radius=6)
    cx = rect.centerx
    head_r = rect.w * 0.22
    hy = rect.y + rect.h * 0.55
    # shoulders (clipped to the frame)
    old_clip = surf.get_clip()
    surf.set_clip(rect.inflate(-6, -6).clip(old_clip))
    pygame.draw.ellipse(surf, col, (cx - rect.w * 0.36, rect.bottom - rect.h * 0.22, rect.w * 0.72, rect.h * 0.4))
    surf.set_clip(old_clip)
    skin = (215, 185, 160) if faction == "castle" else (190, 195, 205)
    pygame.draw.circle(surf, skin, (cx, int(hy)), int(head_r))
    pygame.draw.circle(surf, (40, 30, 30), (cx, int(hy)), int(head_r), 1)
    eye = (40, 60, 120) if faction == "castle" else (120, 255, 160)
    for ex in (-0.35, 0.35):
        pygame.draw.circle(surf, eye, (int(cx + ex * head_r), int(hy - head_r * 0.1)), max(2, int(head_r * 0.13)))
    pygame.draw.arc(surf, (90, 50, 50), (cx - head_r * 0.4, hy + head_r * 0.15, head_r * 0.8, head_r * 0.5), math.pi * 1.1, math.pi * 1.9, 2)
    faction_symbol(surf, cx, rect.y + rect.h * 0.18, rect.w * 0.1, faction, C_GOLD)
    pygame.draw.rect(surf, C_RED if owner == "enemy" else C_BDR, rect, 2, border_radius=8)
    if font and name:
        blit(surf, name, font, C_TXT, cx, rect.bottom + 2, "center")
