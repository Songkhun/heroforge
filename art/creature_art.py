"""Procedural creature sprites: 14 body types, upgraded units get brighter colors and gold trim."""
import math

import pygame

from config import C_GOLD
from engine.creature import CREATURES

# creature key -> (body type, main color)
LOOK = {
    "pikeman": ("pike", (150, 160, 185)), "halberdier": ("pike", (175, 185, 210)),
    "archer": ("archer", (70, 130, 70)), "marksman": ("archer", (90, 160, 90)),
    "griffin": ("griffin", (190, 150, 80)), "royal_griffin": ("griffin", (220, 180, 90)),
    "swordsman": ("sword", (140, 140, 160)), "crusader": ("sword", (200, 60, 60)),
    "monk": ("monk", (150, 110, 70)), "zealot": ("monk", (200, 150, 90)),
    "cavalier": ("rider", (120, 90, 60)), "champion": ("rider", (160, 120, 80)),
    "angel": ("angel", (235, 235, 245)), "archangel": ("angel", (255, 240, 200)),
    "skeleton": ("skeleton", (225, 220, 200)), "skeleton_warrior": ("skeleton", (240, 235, 215)),
    "walking_dead": ("zombie", (110, 135, 95)), "zombie": ("zombie", (125, 150, 105)),
    "wight": ("wraith", (150, 165, 190)), "wraith": ("wraith", (120, 130, 175)),
    "vampire": ("vampire", (70, 50, 70)), "vampire_lord": ("vampire", (95, 40, 70)),
    "lich": ("lich", (170, 150, 200)), "power_lich": ("lich", (190, 160, 230)),
    "black_knight": ("knight", (55, 55, 70)), "dread_knight": ("knight", (70, 45, 60)),
    "bone_dragon": ("dragon", (220, 210, 190)), "ghost_dragon": ("dragon", (150, 170, 200)),
}


def _sh(col, f):
    return tuple(max(0, min(255, int(c * f))) for c in col)


def _humanoid(s, cx, cy, k, col, wide=1.0, head=(225, 190, 160), bob=0.0):
    """Generic standing figure: legs, body, head. Returns (shoulder_y, head_center)."""
    bw, bh = 10 * k * wide, 14 * k
    top = cy - 6 * k + bob
    for lx in (-3 * wide, 3 * wide):
        pygame.draw.line(s, _sh(col, 0.6), (cx + lx * k, top + bh), (cx + lx * k, cy + 17 * k), max(2, int(3 * k)))
    body = pygame.Rect(0, 0, bw, bh)
    body.midtop = (cx, top)
    pygame.draw.rect(s, col, body, border_radius=int(3 * k))
    pygame.draw.rect(s, _sh(col, 0.55), body, 1, border_radius=int(3 * k))
    hc = (cx, top - 5 * k)
    pygame.draw.circle(s, head, hc, 5 * k)
    pygame.draw.circle(s, _sh(head, 0.6), hc, 5 * k, 1)
    return top + 2 * k, hc


def _wings(s, cx, cy, k, col, span=16, up=14, flap=0.0):
    for side in (-1, 1):
        pts = [(cx + side * 2 * k, cy - 2 * k),
               (cx + side * span * k, cy - (up + flap) * k),
               (cx + side * (span - 4) * k, cy + 4 * k)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, _sh(col, 0.6), pts, 1)


def _draw_body(s, kind, cx, cy, k, col, t, up):
    bob = math.sin(t * 2.5) * 1.2 * k
    trim = C_GOLD if up else _sh(col, 0.5)
    if kind == "pike":
        sh, hc = _humanoid(s, cx, cy, k, col, bob=bob)
        pygame.draw.line(s, (120, 90, 50), (cx - 9 * k, cy + 16 * k), (cx + 11 * k, cy - 18 * k), max(2, int(2 * k)))
        tip = [(cx + 11 * k, cy - 18 * k), (cx + 9 * k, cy - 12 * k), (cx + 13 * k, cy - 13 * k)]
        pygame.draw.polygon(s, (220, 220, 230) if not up else C_GOLD, tip)
        pygame.draw.rect(s, trim, (hc[0] - 5 * k, hc[1] - 6 * k, 10 * k, 3 * k))
    elif kind == "archer":
        sh, hc = _humanoid(s, cx, cy, k, col, bob=bob)
        bow = pygame.Rect(cx + 2 * k, cy - 14 * k + bob, 14 * k, 24 * k)
        pygame.draw.arc(s, (130, 90, 40) if not up else C_GOLD, bow, -math.pi / 2, math.pi / 2, max(2, int(2 * k)))
        pygame.draw.line(s, (230, 230, 230), bow.midtop, bow.midbottom, 1)
        pygame.draw.polygon(s, _sh(col, 0.7), [(hc[0] - 6 * k, hc[1] - 2 * k), (hc[0] + 6 * k, hc[1] - 2 * k), (hc[0], hc[1] - 10 * k)])
    elif kind == "griffin":
        body = pygame.Rect(0, 0, 26 * k, 13 * k)
        body.center = (cx, cy + 4 * k)
        for lx in (-8, -3, 4, 9):
            pygame.draw.line(s, _sh(col, 0.6), (cx + lx * k, cy + 8 * k), (cx + lx * k, cy + 17 * k), max(2, int(2 * k)))
        _wings(s, cx, cy + 2 * k + bob, k, _sh(col, 1.15), span=17, up=16, flap=math.sin(t * 6) * 3)
        pygame.draw.ellipse(s, col, body)
        pygame.draw.ellipse(s, _sh(col, 0.55), body, 1)
        hc = (cx + 13 * k, cy - 3 * k)
        pygame.draw.circle(s, (240, 240, 235), hc, 5 * k)
        pygame.draw.polygon(s, C_GOLD, [(hc[0] + 4 * k, hc[1] - 1 * k), (hc[0] + 10 * k, hc[1] + 1 * k), (hc[0] + 4 * k, hc[1] + 3 * k)])
        pygame.draw.circle(s, (20, 20, 20), (hc[0] + 1 * k, hc[1] - 1 * k), max(1, int(k)))
        if up:
            pygame.draw.polygon(s, C_GOLD, [(hc[0] - 4 * k, hc[1] - 4 * k), (hc[0] - 2 * k, hc[1] - 9 * k), (hc[0], hc[1] - 4 * k), (hc[0] + 2 * k, hc[1] - 9 * k), (hc[0] + 4 * k, hc[1] - 4 * k)])
    elif kind == "sword":
        sh, hc = _humanoid(s, cx, cy, k, col, wide=1.4, head=(190, 190, 205), bob=bob)
        pygame.draw.rect(s, (225, 225, 235), (cx + 9 * k, cy - 16 * k + bob, 3 * k, 20 * k))
        pygame.draw.rect(s, trim, (cx + 6 * k, cy + 2 * k + bob, 9 * k, 2 * k))
        shield = pygame.Rect(cx - 15 * k, cy - 6 * k + bob, 9 * k, 13 * k)
        pygame.draw.rect(s, (200, 200, 210) if up else (90, 100, 140), shield, border_radius=int(4 * k))
        if up:
            pygame.draw.line(s, (200, 40, 40), (shield.centerx, shield.top + 2), (shield.centerx, shield.bottom - 2), 2)
            pygame.draw.line(s, (200, 40, 40), (shield.left + 2, shield.centery - 2), (shield.right - 2, shield.centery - 2), 2)
    elif kind == "monk":
        top = cy - 8 * k + bob
        robe = [(cx - 4 * k, top), (cx + 4 * k, top), (cx + 10 * k, cy + 17 * k), (cx - 10 * k, cy + 17 * k)]
        pygame.draw.polygon(s, col, robe)
        pygame.draw.polygon(s, _sh(col, 0.55), robe, 1)
        hc = (cx, top - 5 * k)
        pygame.draw.circle(s, (225, 190, 160), hc, 5 * k)
        pygame.draw.ellipse(s, C_GOLD if up else (250, 230, 140), (hc[0] - 7 * k, hc[1] - 10 * k, 14 * k, 4 * k), 2)
        pygame.draw.line(s, (120, 90, 50), (cx + 9 * k, cy - 14 * k), (cx + 9 * k, cy + 17 * k), max(2, int(2 * k)))
        pygame.draw.circle(s, (255, 240, 160), (cx + 9 * k, cy - 15 * k), 3 * k)
    elif kind == "rider":
        horse = pygame.Rect(0, 0, 28 * k, 12 * k)
        horse.center = (cx - 1 * k, cy + 5 * k)
        for lx in (-11, -6, 5, 10):
            pygame.draw.line(s, _sh(col, 0.6), (cx + lx * k, cy + 9 * k), (cx + lx * k, cy + 18 * k), max(2, int(2 * k)))
        pygame.draw.ellipse(s, col, horse)
        pygame.draw.ellipse(s, col, (cx + 10 * k, cy - 6 * k, 9 * k, 13 * k))   # horse head
        rider = pygame.Rect(0, 0, 10 * k, 13 * k)
        rider.midbottom = (cx - 2 * k, cy + 1 * k + bob)
        pygame.draw.ellipse(s, (170, 170, 190) if not up else (210, 210, 225), rider)
        pygame.draw.circle(s, (200, 200, 210), (cx - 2 * k, rider.top - 3 * k), 4 * k)
        pygame.draw.line(s, (200, 200, 210), (cx + 2 * k, cy - 2 * k + bob), (cx + 20 * k, cy - 10 * k), max(2, int(2 * k)))
        pygame.draw.rect(s, trim, (cx - 8 * k, cy + 2 * k, 12 * k, 3 * k))
    elif kind == "angel":
        _wings(s, cx, cy - 2 * k + bob, k, (250, 250, 255), span=18, up=18, flap=math.sin(t * 3) * 2)
        sh, hc = _humanoid(s, cx, cy, k, col, head=(240, 210, 180), bob=bob)
        pygame.draw.ellipse(s, C_GOLD, (hc[0] - 7 * k, hc[1] - 10 * k, 14 * k, 4 * k), 2)
        pygame.draw.rect(s, (230, 230, 240), (cx + 7 * k, cy - 10 * k + bob, 2 * k, 18 * k))
        if up:
            pygame.draw.circle(s, (255, 230, 150), (int(cx), int(cy)), int(19 * k), 1)
    elif kind == "skeleton":
        top = cy - 7 * k + bob
        w = max(1, int(2 * k))
        pygame.draw.line(s, col, (cx, top), (cx, cy + 6 * k), w)
        for i in range(3):
            pygame.draw.line(s, col, (cx - 4 * k, top + (2 + i * 3) * k), (cx + 4 * k, top + (2 + i * 3) * k), 1)
        for lx in (-4, 4):
            pygame.draw.line(s, col, (cx, cy + 6 * k), (cx + lx * k, cy + 17 * k), w)
            pygame.draw.line(s, col, (cx, top + 2 * k), (cx + lx * 2 * k, cy + 2 * k), w)
        hc = (cx, top - 4 * k)
        pygame.draw.circle(s, col, hc, 5 * k)
        for ex in (-2, 2):
            pygame.draw.circle(s, (20, 10, 10), (hc[0] + ex * k, hc[1]), max(1, int(1.3 * k)))
        pygame.draw.line(s, (170, 170, 180), (cx + 8 * k, cy - 8 * k), (cx + 8 * k, cy + 8 * k), w)
        if up:
            pygame.draw.circle(s, (120, 110, 90), (int(cx - 9 * k), int(cy + 1 * k)), int(5 * k))
            pygame.draw.circle(s, C_GOLD, (int(cx - 9 * k), int(cy + 1 * k)), int(5 * k), 1)
    elif kind == "zombie":
        hunch = cx + 2 * k
        sh, hc = _humanoid(s, hunch, cy + 2 * k, k, col, wide=1.4, head=_sh(col, 1.2), bob=bob * 0.5)
        pygame.draw.line(s, _sh(col, 1.1), (hunch + 6 * k, cy - 2 * k), (hunch + 14 * k, cy - 1 * k), max(2, int(2 * k)))
        pygame.draw.circle(s, (200, 40, 40), (hc[0] + 2 * k, hc[1]), max(1, int(k)))
        pygame.draw.rect(s, (90, 70, 60), (hunch - 7 * k, cy + 4 * k, 14 * k, 4 * k))
    elif kind == "wraith":
        float_y = math.sin(t * 2) * 2 * k
        top = cy - 10 * k + float_y
        cloth = [(cx - 8 * k, top + 4 * k), (cx + 8 * k, top + 4 * k), (cx + 4 * k + math.sin(t * 4) * 2 * k, cy + 17 * k),
                 (cx, cy + 12 * k), (cx - 5 * k + math.sin(t * 4 + 1) * 2 * k, cy + 17 * k)]
        pygame.draw.polygon(s, col, cloth)
        pygame.draw.polygon(s, _sh(col, 0.5), cloth, 1)
        hc = (cx, top)
        pygame.draw.circle(s, _sh(col, 0.4), hc, 6 * k)
        glow = (120, 255, 200) if not up else (255, 120, 120)
        for ex in (-2, 2):
            pygame.draw.circle(s, glow, (hc[0] + ex * k, hc[1]), max(1, int(1.4 * k)))
        if up:
            pygame.draw.line(s, (180, 180, 190), (cx + 9 * k, cy - 14 * k), (cx + 6 * k, cy + 10 * k), max(2, int(2 * k)))
            pygame.draw.arc(s, (210, 210, 220), (cx + 4 * k, cy - 18 * k, 14 * k, 10 * k), 0, math.pi, 2)
    elif kind == "vampire":
        cape = [(cx - 5 * k, cy - 8 * k + bob), (cx + 5 * k, cy - 8 * k + bob), (cx + 14 * k, cy + 17 * k), (cx - 14 * k, cy + 17 * k)]
        pygame.draw.polygon(s, (120, 20, 30) if not up else (160, 20, 40), cape)
        sh, hc = _humanoid(s, cx, cy, k, col, head=(215, 205, 210), bob=bob)
        pygame.draw.polygon(s, (30, 20, 30), [(hc[0] - 5 * k, hc[1] - 2 * k), (hc[0], hc[1] - 6 * k), (hc[0] + 5 * k, hc[1] - 2 * k)])
        for ex in (-2, 2):
            pygame.draw.circle(s, (220, 30, 30), (hc[0] + ex * k, hc[1]), max(1, int(k)))
        if up:
            pygame.draw.polygon(s, C_GOLD, [(hc[0] - 6 * k, hc[1] + 5 * k), (hc[0], hc[1] + 9 * k), (hc[0] + 6 * k, hc[1] + 5 * k)], 1)
    elif kind == "lich":
        float_y = math.sin(t * 2) * 2 * k
        glow = pygame.Surface((int(40 * k), int(40 * k)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (170, 90, 255, 60 + int(30 * math.sin(t * 3))), glow.get_rect().center, int(18 * k))
        s.blit(glow, glow.get_rect(center=(cx, cy)))
        top = cy - 9 * k + float_y
        robe = [(cx - 6 * k, top), (cx + 6 * k, top), (cx + 9 * k, cy + 9 * k + float_y), (cx, cy + 14 * k + float_y), (cx - 9 * k, cy + 9 * k + float_y)]
        pygame.draw.polygon(s, col, robe)
        pygame.draw.polygon(s, _sh(col, 0.5), robe, 1)
        hc = (cx, top - 4 * k)
        pygame.draw.circle(s, (225, 220, 200), hc, 5 * k)
        for ex in (-2, 2):
            pygame.draw.circle(s, (120, 255, 120), (hc[0] + ex * k, hc[1]), max(1, int(k)))
        pygame.draw.line(s, (90, 70, 60), (cx - 11 * k, cy - 16 * k), (cx - 11 * k, cy + 12 * k), max(2, int(2 * k)))
        pygame.draw.circle(s, C_GOLD if up else (140, 255, 140), (cx - 11 * k, cy - 17 * k), 3 * k)
    elif kind == "knight":
        sh, hc = _humanoid(s, cx, cy, k, col, wide=1.6, head=_sh(col, 1.3), bob=bob)
        pygame.draw.rect(s, (200, 40, 40) if not up else (255, 80, 40), (hc[0] - 4 * k, hc[1] - 1 * k, 8 * k, 2 * k))
        pygame.draw.polygon(s, _sh(col, 1.6), [(hc[0] - 2 * k, hc[1] - 5 * k), (hc[0], hc[1] - 12 * k), (hc[0] + 2 * k, hc[1] - 5 * k)])
        pygame.draw.rect(s, (160, 160, 175), (cx + 11 * k, cy - 17 * k + bob, 3 * k, 24 * k))
        pygame.draw.rect(s, trim, (cx + 8 * k, cy + 5 * k + bob, 9 * k, 2 * k))
    elif kind == "dragon":
        float_y = math.sin(t * 2) * 1.5 * k
        body = pygame.Rect(0, 0, 32 * k, 14 * k)
        body.center = (cx, cy + 4 * k + float_y)
        _wings(s, cx - 2 * k, cy + float_y, k, _sh(col, 0.85), span=18, up=18, flap=math.sin(t * 4) * 3)
        pygame.draw.ellipse(s, col, body)
        for i in range(5):
            x = body.left + 6 * k + i * 5 * k
            pygame.draw.polygon(s, _sh(col, 0.7), [(x - 2 * k, body.top + 2), (x, body.top - 5 * k), (x + 2 * k, body.top + 2)])
        pygame.draw.line(s, col, (body.left + 2, body.centery), (body.left - 8 * k, body.centery + 6 * k), max(2, int(3 * k)))
        hc = (body.right + 3 * k, body.top - 2 * k)
        pygame.draw.line(s, col, (body.right - 4 * k, body.centery), hc, max(3, int(4 * k)))
        pygame.draw.ellipse(s, col, (hc[0] - 3 * k, hc[1] - 4 * k, 10 * k, 7 * k))
        pygame.draw.circle(s, (120, 255, 200) if up else (255, 80, 60), (hc[0] + 3 * k, hc[1] - 2 * k), max(1, int(1.3 * k)))
        for lx in (-9, 8):
            pygame.draw.line(s, _sh(col, 0.7), (cx + lx * k, body.bottom - 2), (cx + lx * k, cy + 18 * k), max(2, int(2 * k)))
        if up:
            ghost = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(ghost, (150, 200, 255, 50), body.inflate(8 * k, 8 * k))
            s.blit(ghost, (0, 0))


def draw_creature(surf, cx, cy, creature_key, t, count=None, size=48, active=False, facing=1,
                  glow=0.0, flash=0.0, border=None):
    """Draw a creature sprite centered at (cx, cy) inside a size x size box.

    count: shows a badge bottom-right when not None.
    active: pulsing gold square border (map/army use; combat draws its own hex border).
    facing: 1 = faces right, -1 = mirrored (left).
    glow: 0..1 brightens the sprite (combat: active stack). flash: 0..1 red hit tint.
    border: badge border color (defaults to gold); combat uses side colors.
    """
    kind, col = LOOK.get(creature_key, ("pike", (150, 150, 150)))
    up = CREATURES.get(creature_key, {}).get("is_upgraded", False)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    k = size / 48
    _draw_body(s, kind, size / 2, size / 2, k, col, t, up)
    if glow > 0:
        add = int(70 * glow)
        s.fill((add, add, int(add * 0.6), 0), special_flags=pygame.BLEND_RGBA_ADD)
    if flash > 0:
        tint = pygame.Surface((size, size), pygame.SRCALPHA)
        tint.fill((255, int(255 * (1 - flash)), int(255 * (1 - flash)), 255))
        s.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if facing < 0:
        s = pygame.transform.flip(s, True, False)
    surf.blit(s, (cx - size / 2, cy - size / 2))
    if active:
        b = 0.5 + 0.5 * math.sin(t * 3)
        c = tuple(int(v * (0.55 + 0.45 * b)) for v in C_GOLD)
        pygame.draw.rect(surf, c, (cx - size / 2, cy - size / 2, size, size), 2, border_radius=6)
    if count is not None:
        font = _badge_font(size)
        txt = font.render(str(count), True, (255, 255, 255))
        r = max(txt.get_width() // 2 + 4, int(8 * k))
        bx, by = int(cx + size / 2 - r), int(cy + size / 2 - r * 0.8)
        pygame.draw.circle(surf, (35, 45, 80), (bx, by), r)
        pygame.draw.circle(surf, border or C_GOLD, (bx, by), r, 1)
        surf.blit(txt, txt.get_rect(center=(bx, by)))


_fonts = {}


def _badge_font(size):
    fs = max(11, int(size / 4))
    if fs not in _fonts:
        _fonts[fs] = pygame.font.SysFont("arial,helvetica,dejavusans", fs, bold=True)
    return _fonts[fs]


def creature_tooltip(key, count=None):
    """One-paragraph stats text for hover tooltips."""
    c = CREATURES[key]
    head = f"{count} × {c['name']}" if count else c["name"]
    tags = (["Ranged"] if c["is_ranged"] else []) + (["Flying"] if c["is_flying"] else []) + \
           [a.replace("_", " ").title() for a in c["abilities"]]
    text = (f"{head} — {c['faction'].title()} tier {c['tier']}. ATK {c['attack']}  DEF {c['defense']}  "
            f"DMG {c['damage_min']}-{c['damage_max']}  HP {c['hp']}  SPD {c['speed']}  INIT {c['initiative']}")
    if tags:
        text += ". " + ", ".join(tags)
    return text


def draw_creature_card(surf, key, pos, t, fonts, count=None):
    """Full stats panel (sprite + stat table) drawn near `pos`; fonts = main.F."""
    from art.ui_art import panel, blit, blit_wrap
    from config import C_BG1, C_GOLD, C_SUB, C_TXT, C_PURP
    c = CREATURES[key]
    w, h = 300, 236
    sw, sh = surf.get_size()
    r = pygame.Rect(pos[0] + 18, pos[1] - 20, w, h)
    if r.right > sw - 4:
        r.right = pos[0] - 14
    r.clamp_ip(surf.get_rect())
    panel(surf, r, C_BG1, C_GOLD, br=10, bw=2)
    draw_creature(surf, r.x + 52, r.y + 62, key, t, size=86)
    blit(surf, c["name"], fonts["md"], C_GOLD, r.x + 100, r.y + 12)
    blit(surf, f"{c['faction'].title()} · Tier {c['tier']}" + (f" · x{count}" if count else ""), fonts["ti"], C_SUB,
         r.x + 100, r.y + 38)
    rows = [("Attack", c["attack"]), ("Defense", c["defense"]), ("Damage", f"{c['damage_min']}-{c['damage_max']}"),
            ("Health", c["hp"]), ("Speed", c["speed"]), ("Initiative", c["initiative"]),
            ("Cost", f"{c['cost']} gold"), ("Growth", f"{c['weekly_growth']}/wk")]
    for i, (k, v) in enumerate(rows):
        x = r.x + 100 + (i % 2) * 100
        y = r.y + 62 + (i // 2) * 30
        blit(surf, k, fonts["ti"], C_SUB, x, y)
        blit(surf, v, fonts["sm"], C_TXT, x, y + 13)
    tags = (["Ranged"] if c["is_ranged"] else []) + (["Flying"] if c["is_flying"] else []) + \
           [a.replace("_", " ").title() for a in c["abilities"]]
    if tags:
        blit_wrap(surf, " · ".join(tags), fonts["ti"], C_PURP, r.x + 14, r.bottom - 42, w - 28)
