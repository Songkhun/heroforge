"""Hero screen: portrait and stats, secondary skills, spellbook, army, artifacts."""
import pygame

import main
from config import (SW, SH, FACTION_COLORS, C_BG0, C_BG1, C_BG2, C_BDR, C_GOLD, C_TXT, C_SUB,
                    C_HINT, C_GRN, C_RED, C_BLUE, C_PURP)
from art.ui_art import Button, blit, blit_wrap, panel, hp_bar
from art import creature_art, hero_art
from engine import skills as SK
from engine.creature import unit_name
from scenes.scene_manager import SM

HEAD_H = 48
SCHOOL_COLORS = {"earth": (170, 120, 60), "air": (150, 200, 240), "fire": (230, 90, 50), "water": (70, 130, 230)}
STAT_ICONS = {"attack": (210, 70, 60), "defense": (90, 140, 210), "power": (170, 110, 230), "knowledge": (90, 190, 130)}
# paper-doll layout: (slot, column, row) — columns -1/0/1 around the center
DOLL = [("misc1", -1, 0), ("head", 0, 0), ("misc2", 1, 0),
        ("cloak", -1, 1), ("neck", 0, 1),
        ("hand_r", -1, 2), ("torso", 0, 2), ("hand_l", 1, 2),
        ("ring1", -1, 3), ("boot", 0, 3), ("ring2", 1, 3)]
SLOT_LABEL = {"head": "Head", "neck": "Neck", "torso": "Torso", "cloak": "Cloak", "hand_r": "R. Hand",
              "hand_l": "L. Hand", "ring1": "Ring", "ring2": "Ring", "boot": "Boots", "misc1": "Misc", "misc2": "Misc"}
SPELL_ROW = 30


class HeroScreen:
    def __init__(self):
        self.t = 0.0
        self.hero = None

    def on_enter(self, hero=None, **kw):
        F = main.F
        self.hero = hero
        self.spell_scroll = 0
        self.spell_sel = None
        self.btn_close = Button((SW - 120, 7, 108, 34), "Close", F["sm"], (70, 30, 30), tc=(255, 200, 190))

    def close(self):
        SM.go("adventure_map")

    # ── geometry ──
    def spell_rect(self):
        return pygame.Rect(410, 452, 380, SH - 452 - 12)

    def doll_rect(self, slot):
        col, row = next((c, r) for s, c, r in DOLL if s == slot)
        cx = 1040 + col * 80
        return pygame.Rect(cx - 28, 486 + row * 64, 56, 56)

    def backpack_rect(self, i):
        return pygame.Rect(1150, 500 + i * 26, 120, 22)

    # ── interface ──
    def update(self, dt):
        self.t += dt
        mx, my = pygame.mouse.get_pos()
        self.btn_close.update(mx, my)
        h = self.hero
        if (self.spell_rect().collidepoint(mx, my)
                or any(self.doll_rect(s).collidepoint(mx, my) and h.artifacts.get(s) for s, _, _ in DOLL)
                or any(self.backpack_rect(i).collidepoint(mx, my) for i in range(len(h.backpack)))):
            from art.ui_art import request_hand
            request_hand()

    def handle(self, ev):
        h = self.hero
        if self.btn_close.clicked(ev) or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_h)):
            self.close()
            return
        if ev.type == pygame.MOUSEWHEEL and self.spell_rect().collidepoint(pygame.mouse.get_pos()):
            max_scroll = max(0, len(h.spells) * SPELL_ROW - self.spell_rect().h + 8)
            self.spell_scroll = max(0, min(max_scroll, self.spell_scroll - ev.y * SPELL_ROW))
            return
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
            return
        mx, my = ev.pos
        sr = self.spell_rect()
        if sr.collidepoint(mx, my):
            i = (my - sr.y - 4 + self.spell_scroll) // SPELL_ROW
            name = h.spells[i] if 0 <= i < len(h.spells) else None
            self.spell_sel = None if name == self.spell_sel else name
            return
        self.spell_sel = None
        for slot, _, _ in DOLL:
            if self.doll_rect(slot).collidepoint(mx, my) and h.artifacts.get(slot):
                h.unequip(slot)
                return
        for i in range(len(h.backpack)):
            if self.backpack_rect(i).collidepoint(mx, my):
                h.equip_from_backpack(i)
                return

    # ── drawing ──
    def draw(self, surf):
        F, h = main.F, self.hero
        surf.fill(C_BG0)
        pygame.draw.rect(surf, C_BG1, (0, 0, SW, HEAD_H))
        pygame.draw.line(surf, C_BDR, (0, HEAD_H - 1), (SW, HEAD_H - 1), 2)
        r = blit(surf, h.name, F["lg"], C_GOLD, 16, 8)
        blit(surf, f"Level {h.level}", F["md"], C_TXT, r.right + 16, 13)
        blit(surf, "H / Esc to close · click artifacts to take off, backpack items to wear", F["ti"], C_HINT,
             SW - 140, 17, "right")
        self.btn_close.draw(surf)
        for x in (400, 800):
            pygame.draw.line(surf, C_BDR, (x, HEAD_H), (x, SH), 1)
        self.draw_left(surf)
        self.draw_center(surf)
        self.draw_right(surf)
        self.draw_tooltips(surf)

    def draw_left(self, surf):
        F, h = main.F, self.hero
        hero_art.draw_hero_portrait(surf, (100, HEAD_H + 16, 200, 200), h.faction, None, owner=h.owner)
        y = HEAD_H + 228
        blit(surf, h.name, F["lg"], C_GOLD, 200, y, "center")
        col = FACTION_COLORS.get(h.faction, C_SUB)
        blit(surf, f"{h.faction.title()} {h.hero_class}", F["sm"], col, 200, y + 34, "center")
        y += 66
        blit(surf, f"Experience {h.xp:,} / {h.xp_next:,}", F["sm"], C_SUB, 30, y)
        prev = 0 if h.level == 1 else _xp_prev(h.level)
        hp_bar(surf, (30, y + 22, 340, 12), h.xp - prev, max(1, h.xp_next - prev), C_GOLD)
        y += 52
        for i, stat in enumerate(("attack", "defense", "power", "knowledge")):
            cx, cy = 30 + (i % 2) * 180, y + (i // 2) * 64
            pygame.draw.circle(surf, STAT_ICONS[stat], (cx + 18, cy + 22), 18)
            _stat_icon(surf, stat, cx + 18, cy + 22)
            blit(surf, stat.title(), F["ti"], C_SUB, cx + 44, cy + 4)
            bonus = h.artifact_bonus(stat)
            blit(surf, f"{h.stat(stat)}" + (f" (+{bonus})" if bonus else ""), F["lg"], C_TXT, cx + 44, cy + 18)
        y += 140
        blit(surf, f"Movement {h.movement_points}/{h.movement_max}", F["sm"], C_TXT, 30, y)
        hp_bar(surf, (30, y + 22, 340, 10), h.movement_points, max(1, h.movement_max), C_GRN)
        blit(surf, f"Mana {h.mana}/{h.mana_max}", F["sm"], C_BLUE, 30, y + 44)
        hp_bar(surf, (30, y + 66, 340, 10), h.mana, max(1, h.mana_max), C_BLUE)
        blit(surf, f"Can learn spells up to level {SK.max_spell_level(h)}", F["ti"], C_HINT, 30, y + 88)

    def draw_center(self, surf):
        F, h = main.F, self.hero
        mx, my = pygame.mouse.get_pos()
        blit(surf, "SECONDARY SKILLS", F["sm"], C_GOLD, 412, HEAD_H + 12)
        skills = list(h.skills.items())
        for i in range(SK.MAX_SKILLS):
            r = pygame.Rect(410 + (i % 2) * 192, HEAD_H + 40 + (i // 2) * 74, 184, 66)
            if i < len(skills):
                name, lvl = skills[i]
                panel(surf, r, C_BG2, C_BDR, br=8)
                col = SK.SKILL_COLORS.get(name, C_SUB)
                pygame.draw.circle(surf, col, (r.x + 26, r.centery), 18)
                blit(surf, name[0], F["md"], (20, 20, 20), r.x + 26, r.centery - 12, "center")
                blit(surf, name, _bold(14), C_TXT, r.x + 52, r.y + 10)
                badge = F["ti"].render(SK.LEVEL_NAMES[lvl], True, (20, 20, 20))
                br = badge.get_rect(topleft=(r.x + 52, r.y + 36)).inflate(10, 4)
                pygame.draw.rect(surf, [C_SUB, C_GOLD, C_GRN][lvl - 1], br, border_radius=8)
                surf.blit(badge, badge.get_rect(center=br.center))
            else:
                pygame.draw.rect(surf, (55, 60, 75), r, 1, border_radius=8)
                blit(surf, "—", F["md"], C_HINT, r.centerx, r.centery - 12, "center")
        blit(surf, f"SPELLBOOK ({len(h.spells)})", F["sm"], C_GOLD, 412, 424)
        sr = self.spell_rect()
        panel(surf, sr, C_BG1, C_BDR, br=8)
        old = surf.get_clip()
        surf.set_clip(sr.inflate(-4, -4))
        for i, name in enumerate(h.spells):
            sp = main.SPELLS.get(name)
            if not sp:
                continue
            y = sr.y + 4 + i * SPELL_ROW - self.spell_scroll
            row = pygame.Rect(sr.x + 4, y, sr.w - 8, SPELL_ROW - 2)
            if name == self.spell_sel or row.collidepoint(mx, my):
                pygame.draw.rect(surf, C_BG2, row, border_radius=5)
            pygame.draw.circle(surf, SCHOOL_COLORS[sp["school"]], (row.x + 14, row.centery), 6)
            blit(surf, name, F["sm"], C_TXT, row.x + 28, row.y + 5)
            blit(surf, f"L{sp['level']}", F["ti"], C_HINT, row.right - 90, row.y + 7)
            blit(surf, f"{sp['mana_cost']} mana", F["ti"], C_BLUE, row.right - 10, row.y + 7, "right")
        surf.set_clip(old)
        if not h.spells:
            blit(surf, "No spells known. Visit a Mage Guild.", F["sm"], C_HINT, sr.x + 14, sr.y + 14)

    def draw_right(self, surf):
        F, h = main.F, self.hero
        blit(surf, "ARMY", F["sm"], C_GOLD, 812, HEAD_H + 12)
        for i in range(7):
            r = pygame.Rect(810, HEAD_H + 34 + i * 52, 460, 48)
            st = h.army[i]
            if not st:
                pygame.draw.rect(surf, (55, 60, 75), r, 1, border_radius=8)
                blit(surf, "Empty", F["ti"], C_HINT, r.x + 60, r.y + 16)
                continue
            panel(surf, r, C_BG2, C_BDR, br=8)
            creature_art.draw_creature(surf, r.x + 28, r.centery - 2, st.creature, self.t, size=46)
            blit(surf, f"{st.count} {unit_name(st.creature, st.count)}", F["sm"], C_TXT, r.x + 60, r.y + 6)
            d = st.data
            blit(surf, f"ATK {d['attack']} DEF {d['defense']} DMG {d['damage_min']}-{d['damage_max']} SPD {d['speed']}",
                 F["ti"], C_SUB, r.x + 60, r.y + 28)
            blit(surf, f"HP {st.hp_remaining}/{st.unit_hp}", F["ti"], C_TXT, r.right - 130, r.y + 8)
            hp_bar(surf, (r.right - 130, r.y + 28, 118, 9), st.hp_remaining, st.unit_hp)
        blit(surf, "ARTIFACTS", F["sm"], C_GOLD, 812, 446)
        for slot, _, _ in DOLL:
            r = self.doll_rect(slot)
            art = h.artifacts.get(slot)
            if art:
                panel(surf, r, (52, 40, 78), C_PURP, br=8, bw=2)
                _gem(surf, r.centerx, r.y + 18, self.t)
                _two_lines(surf, art["name"], r)
            else:
                pygame.draw.rect(surf, (45, 50, 64), r, border_radius=8)
                pygame.draw.rect(surf, (70, 76, 92), r, 1, border_radius=8)
                blit(surf, SLOT_LABEL[slot], F["ti"], C_HINT, r.centerx, r.centery - 8, "center")
        blit(surf, f"Backpack ({len(h.backpack)})", F["ti"], C_SUB, 1150, 482)
        for i, art in enumerate(h.backpack[:10]):
            r = self.backpack_rect(i)
            pygame.draw.rect(surf, C_BG2, r, border_radius=4)
            name = art["name"] if len(art["name"]) <= 16 else art["name"][:15] + "."
            blit(surf, name, F["ti"], C_TXT, r.x + 5, r.y + 3)

    def tooltip(self):
        h = self.hero
        mx, my = pygame.mouse.get_pos()
        if self.spell_sel and self.spell_sel in main.SPELLS:
            sp = main.SPELLS[self.spell_sel]
            return (f"{self.spell_sel} — {sp['school'].title()} level {sp['level']}, {sp['mana_cost']} mana. "
                    f"{sp['description']}")
        for slot, _, _ in DOLL:
            if self.doll_rect(slot).collidepoint(mx, my) and h.artifacts.get(slot):
                return _art_text(h.artifacts[slot])
        for i, art in enumerate(h.backpack[:10]):
            if self.backpack_rect(i).collidepoint(mx, my):
                return _art_text(art) + " (click to wear)"
        for i, st in enumerate(h.army):
            if st and pygame.Rect(810, HEAD_H + 34 + i * 52, 460, 48).collidepoint(mx, my):
                return creature_art.creature_tooltip(st.creature, st.count)
        skills = list(h.skills.items())
        for i, (name, lvl) in enumerate(skills):
            r = pygame.Rect(410 + (i % 2) * 192, HEAD_H + 40 + (i // 2) * 74, 184, 66)
            if r.collidepoint(mx, my) and name in SK.SKILLS:
                nxt = f" Next: {SK.describe(name, lvl + 1)}." if lvl < 3 else ""
                return f"{SK.LEVEL_NAMES[lvl]} {name}: {SK.describe(name, lvl)}.{nxt}"
        return None

    def draw_tooltips(self, surf):
        text = self.tooltip()
        if not text:
            return
        F = main.F
        mx, my = pygame.mouse.get_pos()
        w = 320
        h = blit_wrap(pygame.Surface((1, 1)), text, F["ti"], C_TXT, 0, 0, w - 20) + 12
        r = pygame.Rect(mx + 16, my + 12, w, h)
        if r.right > SW - 4:
            r.right = mx - 12
        if r.bottom > SH - 4:
            r.bottom = my - 8
        panel(surf, r, (14, 18, 28), C_GOLD, br=6)
        blit_wrap(surf, text, F["ti"], C_TXT, r.x + 10, r.y + 6, w - 20)


def _two_lines(surf, text, r):
    """Artifact name in at most two small centered lines inside slot rect `r`."""
    font = _plain(11)
    words, lines = text.split(" "), [""]
    for w in words:
        test = f"{lines[-1]} {w}".strip()
        if font.size(test)[0] <= r.w - 4 or not lines[-1]:
            lines[-1] = test
        elif len(lines) < 2:
            lines.append(w)
        else:
            lines[-1] = lines[-1].rstrip(".") + "…" if not lines[-1].endswith("…") else lines[-1]
            break
    for i, line in enumerate(lines):
        while font.size(line)[0] > r.w - 4 and len(line) > 3:
            line = line[:-2] + "…"
        img = font.render(line, True, C_TXT)
        surf.blit(img, img.get_rect(midtop=(r.centerx, r.y + 29 + i * 12)))


def _plain(size):
    key = ("p", size)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("arial,helvetica,dejavusans", size)
    return _fonts[key]


def _art_text(art):
    bonus = ", ".join(f"+{v} {k}" for k, v in art.get("bonus", {}).items())
    special = f" — {art['special']}" if art.get("special") else ""
    return f"{art['name']}: {bonus}{special}"


def _xp_prev(level):
    from engine.hero import xp_for_level
    return xp_for_level(level - 1)


def _gem(surf, cx, cy, t):
    pts = [(cx, cy - 9), (cx + 7, cy), (cx, cy + 9), (cx - 7, cy)]
    pygame.draw.polygon(surf, (200, 140, 255), pts)
    pygame.draw.polygon(surf, (250, 235, 255), [(cx, cy - 9), (cx + 3, cy), (cx, cy)])


def _stat_icon(surf, stat, cx, cy):
    w = (250, 248, 240)
    if stat == "attack":
        pygame.draw.line(surf, w, (cx - 8, cy + 8), (cx + 8, cy - 8), 3)
        pygame.draw.line(surf, w, (cx - 6, cy + 2), (cx - 2, cy + 6), 2)
    elif stat == "defense":
        pygame.draw.polygon(surf, w, [(cx - 8, cy - 8), (cx + 8, cy - 8), (cx + 8, cy), (cx, cy + 9), (cx - 8, cy)], 2)
    elif stat == "power":
        pygame.draw.circle(surf, w, (cx, cy), 7, 2)
        pygame.draw.circle(surf, w, (cx, cy), 2)
    else:
        pygame.draw.rect(surf, w, (cx - 8, cy - 7, 16, 14), 2)
        pygame.draw.line(surf, w, (cx, cy - 7), (cx, cy + 7), 2)


_fonts = {}


def _bold(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("arial,helvetica,dejavusans", size, bold=True)
    return _fonts[size]
