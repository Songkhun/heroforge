"""Procedural terrain tiles and adventure-map object icons."""
import math
import random

import pygame

from config import (TERR_GRASS, TERR_DIRT, TERR_WATER, TERR_ROCK, TERR_SNOW, TERR_LAVA,
                    TERR_SAND, TERR_SWAMP, TERR_ROUGH, RES_COLORS, FACTION_COLORS,
                    OWNER_COLORS, C_GOLD)

TERRAIN_COLORS = {"grass": TERR_GRASS, "dirt": TERR_DIRT, "water": TERR_WATER,
                  "rock": TERR_ROCK, "snow": TERR_SNOW, "lava": TERR_LAVA,
                  "sand": TERR_SAND, "swamp": TERR_SWAMP, "rough": TERR_ROUGH}
VARIANTS = 4
_cache = {}


def _shade(col, f):
    return tuple(max(0, min(255, int(c * f))) for c in col)


def _render_static(terrain, size, variant):
    """Static part of a tile, drawn once per (terrain, size, variant) and cached."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    rng = random.Random(f"{terrain}{variant}")
    base = TERRAIN_COLORS.get(terrain, TERR_GRASS)
    s.fill(base)
    k = size / 48
    if terrain == "grass":
        for _ in range(30):
            pygame.draw.circle(s, _shade(base, 0.75), (rng.randrange(size), rng.randrange(size)), max(1, int(k)))
        for _ in range(3):
            x, y = rng.randrange(4, size - 4), rng.randrange(8, size - 2)
            pygame.draw.line(s, _shade(base, 1.35), (x, y), (x + rng.randint(-2, 2), y - int(6 * k)), 1)
    elif terrain == "dirt":
        c = _shade(base, 0.85)
        off = rng.randrange(8)
        for i in range(4):
            p = int((off + i * 8 + 6) * k)
            pygame.draw.line(s, c, (p, 0), (0, p), 1)
            pygame.draw.line(s, c, (size - p, 0), (size, p), 1)
    elif terrain == "rock":
        for _ in range(rng.randint(2, 3)):
            cx, cy = rng.randrange(8, size - 8), rng.randrange(8, size - 8)
            n = rng.randint(4, 6)
            r = rng.randint(6, 12) * k
            pts = [(cx + math.cos(a) * r * rng.uniform(0.6, 1.1),
                    cy + math.sin(a) * r * rng.uniform(0.6, 1.1))
                   for a in (i * 2 * math.pi / n for i in range(n))]
            pygame.draw.polygon(s, _shade(base, rng.uniform(1.1, 1.4)), pts)
            pygame.draw.polygon(s, _shade(base, 0.6), pts, 1)
    elif terrain == "snow":
        for _ in range(8):
            pygame.draw.circle(s, (255, 255, 255), (rng.randrange(size), rng.randrange(size)), rng.randint(1, 2))
    elif terrain == "lava":
        for _ in range(3):
            x, y = rng.randrange(size), rng.randrange(size)
            pts = [(x, y)]
            for _ in range(rng.randint(3, 4)):
                x += rng.randint(-10, 10) * k
                y += rng.randint(-10, 10) * k
                pts.append((x, y))
            pygame.draw.lines(s, (255, 150, 40), False, pts, 2)
    elif terrain == "sand":
        for _ in range(20):
            x, y = rng.randrange(size), rng.randrange(size)
            for dx, dy in ((0, 0), (2, 1), (1, 2)):
                pygame.draw.circle(s, _shade(base, 0.8), (x + dx, y + dy), 1)
    elif terrain == "swamp":
        for _ in range(3):
            w, h = rng.randint(10, 16) * k, rng.randint(5, 8) * k
            r = pygame.Rect(rng.randrange(0, int(size - w)), rng.randrange(0, int(size - h)), w, h)
            pygame.draw.ellipse(s, (60, 100, 150, 140), r)
    elif terrain == "rough":
        for _ in range(3):
            r = int(rng.randint(8, 12) * k)
            c = (rng.randrange(r, size - r), rng.randrange(r, size - r))
            pygame.draw.circle(s, (20, 50, 22), (c[0] + 2, c[1] + 2), r)
            pygame.draw.circle(s, (28, 62, 28), c, r)
            pygame.draw.circle(s, (45, 90, 40), (c[0] - r // 3, c[1] - r // 3), r // 3)
    return s


def draw_tile(surf, rect, terrain_type, t, variant=0):
    """Draw one terrain tile. `variant` (0..3) picks a cached random layout."""
    rect = pygame.Rect(rect)
    key = (terrain_type, rect.w, variant % VARIANTS)
    img = _cache.get(key)
    if img is None:
        img = _cache[key] = _render_static(terrain_type, rect.w, variant % VARIANTS)
    surf.blit(img, rect)
    if terrain_type == "water":
        draw_water_waves(surf, rect, t)


def draw_static_tile(surf, rect, terrain_type, variant=0):
    """The cacheable part of a tile (no animation)."""
    rect = pygame.Rect(rect)
    key = (terrain_type, rect.w, variant % VARIANTS)
    img = _cache.get(key)
    if img is None:
        img = _cache[key] = _render_static(terrain_type, rect.w, variant % VARIANTS)
    surf.blit(img, rect)


def draw_water_waves(surf, rect, t, phase_x=None):
    """Two animated sine-wave highlights; phase_x keeps waves continuous across tiles."""
    rect = pygame.Rect(rect)
    light = (70, 115, 205)
    px = rect.x if phase_x is None else phase_x
    for i, base in enumerate((rect.h * 0.35, rect.h * 0.72)):
        pts = [(rect.x + x, rect.y + base + math.sin((px + x) * 0.1 + t * 2 + i * 2) * 3)
               for x in range(0, rect.w + 1, 4)]
        pygame.draw.lines(surf, light, False, pts, 1)


# ─────────────────────────── map object icons ───────────────────────────

def draw_town(surf, rect, faction, owner, t=0):
    """Castle silhouette tinted by faction, with an owner banner."""
    rect = pygame.Rect(rect)
    tint = FACTION_COLORS.get(faction, (150, 150, 150))
    body_col = _shade(((140 + tint[0]) // 2, (140 + tint[1]) // 2, (145 + tint[2]) // 2), 1)
    dark = _shade(body_col, 0.6)
    cx, by = rect.centerx, rect.bottom - 4
    w = int(rect.w * 0.6)
    body = pygame.Rect(0, 0, w, int(rect.h * 0.38))
    body.midbottom = (cx, by)
    tr = max(4, rect.w // 8)
    for tx in (body.left, body.right):
        pygame.draw.rect(surf, body_col, (tx - tr, body.top - tr, tr * 2, body.h + tr))
        pygame.draw.circle(surf, body_col, (tx, body.top - tr), tr)
        pygame.draw.circle(surf, dark, (tx, body.top - tr), tr, 1)
    pygame.draw.rect(surf, body_col, body)
    cw = w // 9
    for i in range(5):
        pygame.draw.rect(surf, body_col, (body.left + cw * (2 * i), body.top - cw, cw, cw))
    gate = pygame.Rect(0, 0, w // 4, body.h // 2 + 2)
    gate.midbottom = body.midbottom
    pygame.draw.rect(surf, (30, 25, 25), gate, border_top_left_radius=6, border_top_right_radius=6)
    pygame.draw.rect(surf, dark, body, 1)
    # banner
    fx, fy = cx, body.top - cw - 2
    pygame.draw.line(surf, (60, 50, 40), (fx, fy), (fx, fy - 14), 2)
    wave = math.sin(t * 4) * 2
    pygame.draw.polygon(surf, OWNER_COLORS.get(owner, (150, 150, 150)),
                        [(fx + 1, fy - 14), (fx + 12, fy - 11 + wave), (fx + 1, fy - 8)])


def draw_mine(surf, rect, resource, owner=None):
    rect = pygame.Rect(rect)
    hut = pygame.Rect(0, 0, int(rect.w * 0.56), int(rect.h * 0.36))
    hut.midbottom = (rect.centerx, rect.bottom - 6)
    pygame.draw.rect(surf, (110, 75, 45), hut)
    pygame.draw.polygon(surf, (80, 50, 30), [(hut.left - 3, hut.top), (hut.centerx, hut.top - 9),
                                             (hut.right + 3, hut.top)])
    door = pygame.Rect(0, 0, hut.w // 3, hut.h - 4)
    door.midbottom = hut.midbottom
    pygame.draw.rect(surf, (25, 18, 12), door)
    col = RES_COLORS.get(resource, C_GOLD)
    pygame.draw.circle(surf, col, (rect.centerx, hut.top - 16), 6)
    pygame.draw.circle(surf, (20, 20, 20), (rect.centerx, hut.top - 16), 6, 1)
    if owner in OWNER_COLORS and owner != "neutral":
        fx = hut.right - 2
        pygame.draw.line(surf, (60, 50, 40), (fx, hut.top), (fx, hut.top - 14), 2)
        pygame.draw.rect(surf, OWNER_COLORS[owner], (fx + 1, hut.top - 14, 8, 5))


def draw_artifact(surf, rect, t=0):
    rect = pygame.Rect(rect)
    cx, cy = rect.centerx, rect.centery + math.sin(t * 3) * 2
    r = rect.w * 0.22
    pts = [(cx, cy - r * 1.3), (cx + r, cy), (cx, cy + r * 1.3), (cx - r, cy)]
    glow = int(40 + 30 * (1 + math.sin(t * 4)))
    pygame.draw.circle(surf, (glow + 120, glow + 80, 255), (int(cx), int(cy)), int(r * 1.5), 1)
    pygame.draw.polygon(surf, (190, 120, 255), pts)
    pygame.draw.polygon(surf, (250, 230, 255), [(cx, cy - r * 1.3), (cx + r * 0.5, cy), (cx, cy)])
    pygame.draw.polygon(surf, (60, 30, 90), pts, 1)


def draw_resource_pile(surf, rect, resource):
    rect = pygame.Rect(rect)
    col = RES_COLORS.get(resource, C_GOLD)
    cx, by = rect.centerx, rect.bottom - 10
    for dx, dy, r in ((-7, 0, 6), (6, 0, 6), (0, -6, 6), (-1, 2, 5)):
        pygame.draw.circle(surf, _shade(col, 0.7), (cx + dx, by + dy + 1), r)
        pygame.draw.circle(surf, col, (cx + dx, by + dy), r)
        pygame.draw.circle(surf, _shade(col, 1.3), (cx + dx - 2, by + dy - 2), 2)


def draw_obelisk(surf, rect, visited, t=0):
    """Tall stone pillar; unvisited obelisks glow."""
    rect = pygame.Rect(rect)
    cx, by = rect.centerx, rect.bottom - 6
    pygame.draw.rect(surf, (70, 66, 80), (cx - 12, by - 6, 24, 6))
    pts = [(cx - 7, by - 6), (cx - 5, by - 34), (cx, by - 42), (cx + 5, by - 34), (cx + 7, by - 6)]
    pygame.draw.polygon(surf, (120, 115, 135) if not visited else (90, 88, 98), pts)
    pygame.draw.polygon(surf, (50, 48, 60), pts, 1)
    glow = (190, 140, 255) if not visited else (110, 100, 130)
    pygame.draw.line(surf, glow, (cx, by - 30), (cx, by - 14), 2)
    if not visited:
        a = int(70 + 60 * (0.5 + 0.5 * math.sin(t * 3)))
        g = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(g, (190, 140, 255, a), (15, 15), 12)
        surf.blit(g, (cx - 15, by - 50))
