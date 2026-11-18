"""Procedural town illustrations (640x744) with built-building overlays.

draw_town_view(surf, rect, town, t, font) draws the illustration into `rect` and returns
a list of (pygame.Rect, building_name) hotspots in screen coordinates for tooltips.
"""
import math
import random

import pygame

from config import FACTION_COLORS, C_GOLD

W, H = 640, 744
GROUP_COLORS = {"Income": (215, 175, 60), "Military": (190, 80, 70), "Magic": (150, 100, 220),
                "Dwellings": (90, 160, 90), "Special": (80, 150, 200)}
_static_cache = {}


def _sh(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _levels(town):
    """Highest built level per building family (halls, fort, guild)."""
    hall = fort = guild = 0
    for n, b in town.defs().items():
        if town.has(n):
            hall = max(hall, b.get("hall_level", 0))
            fort = max(fort, b.get("fort_level", 0))
            guild = max(guild, b.get("mage_level", 0))
    return hall, fort, guild


# ───────────────────────── Castle ─────────────────────────

def _castle_static(town):
    s = pygame.Surface((W, H))
    hall, fort, guild = _levels(town)
    # sky: light blue top half with soft gradient, hills, ground
    for y in range(0, H // 2 + 40):
        f = y / (H / 2)
        s.fill((int(60 + 40 * f), int(120 + 40 * f), int(190 + 25 * f)), (0, y, W, 1))
    rng = random.Random(3)
    for _ in range(5):   # clouds
        cx, cy = rng.randrange(40, W - 40), rng.randrange(40, 200)
        for dx, r in ((-22, 18), (0, 26), (24, 20)):
            pygame.draw.circle(s, (225, 235, 245), (cx + dx, cy), r)
    pygame.draw.ellipse(s, (70, 120, 70), (-120, 300, 520, 200))
    pygame.draw.ellipse(s, (60, 110, 62), (260, 290, 520, 220))
    s.fill((50, 95, 45), (0, 400, W, H - 400))
    s.fill((40, 80, 30), (0, H - 200, W, 200))
    # behind-the-wall structures: citadel keep (left), hall (center), mage guild (right)
    if fort >= 2:
        keep = pygame.Rect(140, 230, 80, 140)
        pygame.draw.rect(s, (120, 115, 108), keep)
        for i in range(4):
            pygame.draw.rect(s, (120, 115, 108), (keep.x + i * 22, keep.y - 14, 14, 14))
        pygame.draw.rect(s, (40, 35, 35), (keep.centerx - 7, keep.y + 30, 14, 22))
    if hall:
        hw, hh = [0, 90, 120, 140, 160][hall], [0, 60, 110, 150, 180][hall]
        body = pygame.Rect(0, 0, hw, hh)
        body.midbottom = (320, 372)
        pygame.draw.rect(s, (200, 190, 165), body)
        pygame.draw.rect(s, (150, 140, 120), body, 2)
        if hall <= 2:
            pygame.draw.polygon(s, (150, 60, 50), [(body.x - 8, body.y), (body.centerx, body.y - 40), (body.right + 8, body.y)])
        else:
            dome_col = C_GOLD if hall == 4 else (110, 150, 190)
            pygame.draw.ellipse(s, dome_col, (body.centerx - hw * 0.35, body.y - hw * 0.35, hw * 0.7, hw * 0.7))
            pygame.draw.rect(s, (200, 190, 165), (body.x, body.y, hw, 6))
        for i in range(3):
            pygame.draw.rect(s, (60, 70, 100), (body.x + 15 + i * (hw - 30) // 2 - 6, body.y + 20, 12, 18))
    if guild:
        gx, floor_h = 470, 34
        top = 372 - guild * floor_h
        for i in range(guild):
            pygame.draw.rect(s, (130, 110, 160) if i % 2 else (115, 95, 145), (gx - 26 + i * 2, 372 - (i + 1) * floor_h, 52 - i * 4, floor_h))
            pygame.draw.rect(s, (230, 200, 120), (gx - 4, 372 - (i + 1) * floor_h + 10, 8, 12))
        pygame.draw.polygon(s, (70, 50, 120), [(gx - 22, top), (gx, top - 46), (gx + 22, top)])
    # wall with 8 crenellations
    wall = pygame.Rect(0, 350, W, 170)
    trim = (110, 105, 100)
    pygame.draw.rect(s, trim, wall)
    notch_w, gap = 20, (W - 8 * 20) / 8
    for i in range(8):
        x = gap / 2 + i * (notch_w + gap)
        pygame.draw.rect(s, trim, (x, 330, notch_w, 20))
        pygame.draw.rect(s, (90, 85, 80), (x, 330, notch_w, 20), 1)
    for row in range(1, 8):   # brick lines
        y = 350 + row * 21
        pygame.draw.line(s, (98, 93, 88), (0, y), (W, y), 1)
        off = 0 if row % 2 else 20
        for x in range(off, W, 40):
            pygame.draw.line(s, (98, 93, 88), (x, y - 21), (x, y), 1)
    pygame.draw.rect(s, (90, 85, 80), wall, 1)
    if fort >= 3:
        pygame.draw.line(s, C_GOLD, (0, 352), (W, 352), 3)
    # gate + drawbridge + moat
    gate = pygame.Rect(0, 0, 80, 100)
    gate.midbottom = (320, 520)
    pygame.draw.ellipse(s, (35, 70, 140), (180, 528, 280, 34))
    pygame.draw.rect(s, (30, 25, 25), gate, border_top_left_radius=40, border_top_right_radius=40)
    pygame.draw.polygon(s, (120, 80, 45), [(gate.x, 520), (gate.right, 520), (gate.right + 8, 566), (gate.x - 8, 566)])
    for i in range(1, 5):
        y = 520 + i * 9
        pygame.draw.line(s, (90, 60, 35), (gate.x - i * 2, y), (gate.right + i * 2, y), 1)
    # two round towers (rise 50px above the wall top)
    for tx in (100, 540):
        body = pygame.Rect(tx - 50, 300, 100, 220)
        pygame.draw.rect(s, (100, 95, 90), body)
        pygame.draw.rect(s, (125, 120, 115), (body.x, body.y, 100, 110))
        pygame.draw.ellipse(s, (125, 120, 115), (tx - 50, 280, 100, 40))
        pygame.draw.ellipse(s, (90, 85, 80), (tx - 50, 280, 100, 40), 1)
        roof_h = 110 if fort >= 3 else 90
        pygame.draw.polygon(s, (140, 30, 30), [(tx - 56, 300), (tx, 300 - roof_h), (tx + 56, 300)])
        pygame.draw.polygon(s, (110, 20, 20), [(tx, 300 - roof_h), (tx + 56, 300), (tx + 20, 300)])
        for wy in (330, 400):
            pygame.draw.rect(s, (35, 30, 30), (tx - 7, wy, 14, 24), border_top_left_radius=7, border_top_right_radius=7)
    # foreground grass
    s.fill((60, 120, 45), (0, H - 100, W, 100))
    for _ in range(160):
        x, y = rng.randrange(W), rng.randrange(H - 100, H)
        pygame.draw.line(s, (85, 150, 60), (x, y), (x + rng.randint(-2, 2), y - 6), 1)
    return s


def _castle_anim(surf, ox, oy, town, t):
    hall, fort, _ = _levels(town)
    col = FACTION_COLORS.get(town.faction, C_GOLD)
    roof_h = 110 if fort >= 3 else 90
    for i, tx in enumerate((100, 540)):
        top = oy + 300 - roof_h
        pygame.draw.line(surf, (60, 50, 40), (ox + tx, top), (ox + tx, top - 34), 2)
        sway = math.sin(t * 3 + i) * 4
        pygame.draw.polygon(surf, col, [(ox + tx + 1, top - 34), (ox + tx + 26, top - 29 + sway), (ox + tx + 1, top - 22)])


# ───────────────────────── Necropolis ─────────────────────────
SPIRES = [(120, 600, 160, 60), (380, 620, 180, 50), (580, 610, 240, 40)]   # x, base_y, tip_y, base_w


def _skull(s, x, y, r=5):
    pygame.draw.circle(s, (210, 205, 190), (x, y), r)
    pygame.draw.rect(s, (210, 205, 190), (x - r * 0.6, y + r * 0.4, r * 1.2, r * 0.8))
    for ex in (-r // 2.5, r // 2.5):
        pygame.draw.circle(s, (20, 10, 20), (int(x + ex), int(y - 1)), max(1, r // 4))


def _necro_static(town):
    s = pygame.Surface((W, H))
    hall, fort, guild = _levels(town)
    for y in range(H):
        f = y / H
        s.fill((int(20 + 15 * f), int(15 + 8 * f), int(30 + 20 * f)), (0, y, W, 1))
    rng = random.Random(11)
    for _ in range(80):   # stars
        pygame.draw.circle(s, (120, 110, 150), (rng.randrange(W), rng.randrange(0, 300)), 1)
    pygame.draw.circle(s, (200, 210, 170), (520, 90), 34)
    pygame.draw.circle(s, (20, 15, 30), (534, 82), 30)
    s.fill((45, 40, 50), (0, 560, W, H - 560))
    # behind: mausoleum hall (center-left), necromancy tower (center-right)
    if hall:
        hw, hh = [0, 80, 110, 130, 150][hall], [0, 60, 100, 140, 170][hall]
        body = pygame.Rect(0, 0, hw, hh)
        body.midbottom = (250, 575)
        pygame.draw.rect(s, (60, 55, 70), body)
        pygame.draw.polygon(s, (40, 35, 50), [(body.x - 10, body.y), (body.centerx, body.y - 40 - hall * 8), (body.right + 10, body.y)])
        for i in range(hall):
            pygame.draw.rect(s, (25, 20, 30), (body.x + 12 + i * (hw - 24) // max(1, hall), body.y + 20, 10, 28))
        if hall == 4:
            pygame.draw.circle(s, (150, 255, 160), (body.centerx, body.y - 52 - hall * 8 + 12), 6)
    if guild:
        gx, floor_h = 480, 32
        for i in range(guild):
            pygame.draw.rect(s, (70, 55, 90) if i % 2 else (58, 45, 78), (gx - 22 + i * 2, 570 - (i + 1) * floor_h, 44 - i * 4, floor_h))
            pygame.draw.rect(s, (140, 255, 150), (gx - 3, 570 - (i + 1) * floor_h + 10, 6, 10))
    # spires
    for x, base, tip, bw in SPIRES:
        pygame.draw.polygon(s, (14, 10, 18), [(x - bw / 2, base), (x - bw / 6, tip + 60), (x, tip), (x + bw / 6, tip + 60), (x + bw / 2, base)])
        pygame.draw.line(s, (50, 40, 70), (x, tip), (x + bw / 2, base), 1)
        _skull(s, x, base - 18, 7)
    # bare trees
    for tx, ty, hgt in [(40, 600, 110), (230, 615, 90), (470, 605, 120), (615, 620, 80)]:
        top = (tx, ty - hgt)
        pygame.draw.line(s, (75, 55, 40), (tx, ty), top, 4)
        for side in (-1, 1):
            b_end = (tx + side * hgt * 0.35, ty - hgt * 0.8 - 10)
            mid = (tx, ty - hgt * 0.55)
            pygame.draw.line(s, (75, 55, 40), mid, b_end, 3)
            for sub in (-1, 1):
                pygame.draw.line(s, (75, 55, 40), b_end, (b_end[0] + side * 12 + sub * 8, b_end[1] - 18), 2)
    # fences for fort levels
    if fort:
        for x in range(10, W, 26):
            h = 26 + (12 if fort >= 2 and x % 78 == 10 else 0)
            pygame.draw.line(s, (90, 90, 100), (x, 585), (x, 585 - h), 3)
            pygame.draw.polygon(s, (110, 110, 120), [(x - 4, 585 - h), (x, 585 - h - 8), (x + 4, 585 - h)])
            if fort >= 2 and x % 78 == 10:
                _skull(s, x, 585 - h - 12, 5)
        pygame.draw.line(s, (90, 90, 100), (0, 570), (W, 570), 2)
    # crypts
    for cx, cy in [(70, 640), (300, 650), (560, 645)]:
        pygame.draw.polygon(s, (35, 32, 42), [(cx - 34, cy + 30), (cx - 24, cy - 6), (cx + 24, cy - 6), (cx + 34, cy + 30)])
        pygame.draw.polygon(s, (28, 25, 34), [(cx - 28, cy - 6), (cx, cy - 26), (cx + 28, cy - 6)])
        pygame.draw.rect(s, (12, 10, 14), (cx - 8, cy + 8, 16, 22))
        _skull(s, cx, cy - 12, 5)
    return s


def _necro_anim(surf, ox, oy, town, t):
    _, fort, _ = _levels(town)
    for i, (x, base, tip, bw) in enumerate(SPIRES):
        p = 0.5 + 0.5 * math.sin(t * 2 + i * 1.7)
        r = int(14 + 8 * p)
        g = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(g, (180, 255, 140, int(60 + 70 * p)), (r * 2, r * 2), r * 2)
        pygame.draw.circle(g, (230, 255, 190, int(120 + 80 * p)), (r * 2, r * 2), r // 2)
        surf.blit(g, (ox + x - r * 2, oy + tip - r * 2))
    mist = pygame.Surface((W + 200, 100), pygame.SRCALPHA)
    for i in range(3):
        y = 10 + i * 28
        off = int(math.sin(t * 0.4 + i) * 60)
        pygame.draw.rect(mist, (70, 50, 90, 55), (off + 40 + i * 30, y, W + 20, 34), border_radius=17)
    surf.blit(mist, (ox - 100, oy + 580), area=pygame.Rect(0, 0, W + 200, 100))


# ───────────────────────── overlays ─────────────────────────

def _icon(surf, rect, col, label, font, upgraded=False, dark=False):
    body = pygame.Rect(rect.x + 6, rect.y + 16, rect.w - 12, rect.h - 30)
    base = _sh(col, 0.45) if dark else _sh(col, 0.9)
    pygame.draw.rect(surf, base, body)
    roof = C_GOLD if upgraded else (_sh(col, 0.3) if dark else _sh(col, 0.6))
    pygame.draw.polygon(surf, roof, [(body.x - 4, body.y), (body.centerx, rect.y), (body.right + 4, body.y)])
    pygame.draw.rect(surf, (20, 18, 22), (body.centerx - 5, body.bottom - 14, 10, 14))
    pygame.draw.rect(surf, _sh(col, 0.35), body, 1)
    if font:
        img = font.render(label, True, (235, 235, 240))
        bg = pygame.Surface((img.get_width() + 6, img.get_height()), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        r = bg.get_rect(midtop=(rect.centerx, rect.bottom - 13))
        surf.blit(bg, r)
        surf.blit(img, img.get_rect(center=r.center))


def _short(name):
    for long, short in (("Upgraded ", "+"), ("Resource ", ""), ("Riding ", ""), ("Celestial ", ""),
                        ("Cursed ", ""), ("Haunted ", ""), ("Dragon ", ""), ("Black ", "")):
        name = name.replace(long, short)
    return name if len(name) <= 12 else name[:11] + "."


def draw_town_view(surf, rect, town, t, font=None):
    rect = pygame.Rect(rect)
    key = (town.faction, tuple(sorted(n for n in town.defs() if town.has(n))))
    static = _static_cache.get(key)
    if static is None:
        if len(_static_cache) > 16:
            _static_cache.clear()
        static = _static_cache[key] = (_necro_static if town.faction == "necropolis" else _castle_static)(town)
    surf.blit(static, rect, area=pygame.Rect(0, 0, rect.w, rect.h))
    old_clip = surf.get_clip()
    surf.set_clip(rect)
    (_necro_anim if town.faction == "necropolis" else _castle_anim)(surf, rect.x, rect.y, town, t)
    dark = town.faction == "necropolis"
    hotspots = []
    # dwellings: front row, one slot per tier (upgraded shown with a gold roof)
    for tier in range(1, 8):
        built = [(n, b) for n, b in town.defs().items()
                 if b["category"] == "dwelling" and b["tier"] == tier and town.has(n)]
        if not built:
            continue
        name, b = max(built, key=lambda nb: nb[1].get("upgraded", False))
        r = pygame.Rect(rect.x + 14 + (tier - 1) * 88, rect.y + 590, 72, 62)
        label = f"T{tier} " + _short(name.replace("Upgraded ", ""))
        _icon(surf, r, GROUP_COLORS["Dwellings"], label if len(label) <= 11 else label[:10] + ".",
              font, upgraded=b.get("upgraded", False), dark=dark)
        hotspots.append((r, name))
    # other built non-structural buildings: back row along the bottom
    j = 0
    for name, b in town.defs().items():
        if not town.has(name) or b["group"] in ("Dwellings", "Magic", "Military") or b.get("hall_level"):
            continue
        r = pygame.Rect(rect.x + 14 + j * 104, rect.y + 668, 92, 66)
        _icon(surf, r, GROUP_COLORS[b["group"]], _short(name), font, dark=dark)
        hotspots.append((r, name))
        j += 1
    surf.set_clip(old_clip)
    return hotspots
