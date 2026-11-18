"""Town screen: illustration (left), Buildings / Garrison tabs (right).

Recruits go straight into the visiting hero's army (or the garrison if there's no hero or
no room), so closing the screen has nothing left to commit.
"""
import pygame

import main
from config import (SW, SH, RESOURCES, RES_COLORS, FACTION_COLORS, C_BG0, C_BG1, C_BG2, C_BDR,
                    C_GOLD, C_TXT, C_SUB, C_HINT, C_GRN, C_RED, C_BLUE, C_PURP)
from art.ui_art import Button, blit, blit_wrap, panel, draw_tooltip, request_hand
from art import creature_art, hero_art, town_art
from engine import sound_engine, world
from engine.resource_manager import ResourceManager as RM
from engine.creature import CREATURES, unit_name
from scenes.scene_manager import SM

HEAD_H = 56
PX = 640                         # right panel x
LIST = pygame.Rect(PX + 10, 132, 610, 660)
ENTRY_H, GROUP_H = 58, 30
GROUPS = ["Income", "Military", "Magic", "Dwellings", "Special"]
ROW_Y0, ROW_H = 132, 60          # recruitment rows
SLOT_W, SLOT_H, SLOT_GAP = 80, 74, 6
HERO_SLOTS_Y, GARRISON_SLOTS_Y = 618, 716


def _bold(size):
    key = ("b", size)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("arial,helvetica,dejavusans", size, bold=True)
    return _fonts[key]


_fonts = {}


def draw_check(surf, x, y, col=C_GRN):
    pygame.draw.lines(surf, col, False, [(x, y + 7), (x + 5, y + 12), (x + 14, y)], 3)


def draw_lock(surf, x, y, col=(150, 150, 160)):
    pygame.draw.arc(surf, col, (x + 2, y, 12, 14), 0, 3.1416, 2)
    pygame.draw.rect(surf, col, (x, y + 7, 16, 11), border_radius=2)


class TownScreen:
    def __init__(self):
        self.t = 0.0
        self.town = self.hero = None

    # ─────────────────────────── setup ───────────────────────────
    def on_enter(self, town=None, hero=None, **kw):
        F = main.F
        self.town, self.hero = town, hero
        self.tab = kw.get("tab", "buildings")
        self.scroll = 0
        self.sel = None
        self.msgs = []
        self.hover_building = None
        self.counts = {tier: 0 for tier in range(1, 8)}
        self.choice = {}                     # tier -> creature key shown in the recruit row
        for tier, keys in town.dwellings().items():
            self.choice[tier] = max(keys, key=lambda k: CREATURES[k]["is_upgraded"])
        self.btn_close = Button((SW - 52, 10, 38, 36), "X", F["md"], (70, 30, 30), tc=(255, 200, 190))
        self.btn_tabs = {"buildings": Button((PX + 10, 64, 200, 36), "BUILDINGS", F["md"]),
                         "garrison": Button((PX + 218, 64, 200, 36), "GARRISON", F["md"])}
        self.btn_recruit_all = Button((SW - 180, ROW_Y0 + 7 * ROW_H + 6, 166, 34), "RECRUIT ALL", F["sm"],
                                      (60, 45, 20), hov=(95, 70, 25), tc=C_GOLD, bdr=C_GOLD)
        self.hotspots = []
        if hero:
            self.visit_mage_guild()

    def say(self, text, col=C_TXT):
        self.msgs.append([text, 3.0, col])
        self.msgs = self.msgs[-3:]

    @property
    def res(self):
        return main.STATE["player_resources"]

    def visit_mage_guild(self):
        """A visiting hero learns the guild's spells and refills mana."""
        if not self.hero or not self.town.mage_level():
            return
        learned, blocked = world.visit_mage_guild(main.STATE, self.hero, self.town, main.SPELLS)
        if learned:
            self.say(f"{self.hero.name} learned: {', '.join(learned)}", C_PURP)
        if blocked:
            self.say(f"Needs more Wisdom for: {', '.join(blocked)}", C_SUB)

    def close(self):
        SM.go("adventure_map")

    # ─────────────────────────── buildings tab ───────────────────────────
    def building_layout(self):
        """[(kind, y_in_content, name)] with kind 'group' or 'entry'."""
        town, out, y = self.town, [], 0
        for g in GROUPS:
            names = [n for n, b in town.defs().items() if b["group"] == g]
            if not names:
                continue
            out.append(("group", y, g))
            y += GROUP_H
            for n in names:
                out.append(("entry", y, n))
                y += ENTRY_H
        return out, y

    def build_button_rect(self, y_content):
        return pygame.Rect(LIST.right - 128, LIST.y + y_content - self.scroll + 8, 110, 30)

    def try_build(self, name):
        town = self.town
        if not town.can_build(name, self.res):
            sound_engine.play("error")
            return
        RM.spend(self.res, town.defs()[name]["cost"])
        town.build(name)
        sound_engine.play("build")
        self.say(f"{name} built!", C_GRN)
        b = town.defs()[name]
        if b["category"] == "dwelling":
            tier = b["tier"]
            self.choice[tier] = b["provides_creature"] if b.get("upgraded") else self.choice.get(tier, b["provides_creature"])
        if b.get("mage_level"):
            self.visit_mage_guild()

    def building_tooltip(self, name):
        b = self.town.defs()[name]
        text = b["effect"]
        if b.get("mage_level"):
            lvl = b["mage_level"]
            offered = [s for s in self.town_guild_preview() if main.SPELLS[s]["level"] == lvl]
            if offered:
                text += ": " + ", ".join(offered)
        if b["category"] == "dwelling":
            c = CREATURES[b["provides_creature"]]
            text += f" · {c['cost']} gold each"
        missing = self.town.missing_prereqs(name)
        if missing:
            text += " · Requires " + ", ".join(missing)
        return f"{name}: {text}"

    def town_guild_preview(self):
        """Spells every guild level of this town would offer (for tooltips)."""
        saved = dict(self.town.buildings)
        for n, b in self.town.defs().items():
            if b.get("mage_level"):
                self.town.buildings[n] = True
        try:
            return self.town.guild_spells(main.SPELLS)
        finally:
            self.town.buildings.clear()
            self.town.buildings.update(saved)

    # ─────────────────────────── garrison tab ───────────────────────────
    def destination(self):
        return self.hero.army if self.hero else self.town.garrison

    def max_affordable(self, tier):
        key = self.choice.get(tier)
        if not key:
            return 0
        pool = self.town.pool.get(str(tier), 0)
        return max(0, min(pool, self.res["gold"] // CREATURES[key]["cost"]))

    def recruit(self, tier, count):
        key = self.choice.get(tier)
        count = min(count, self.max_affordable(tier))
        if not key or count <= 0:
            return 0
        cost = self.town.recruit(key, count, target=self.destination())
        where = f"{self.hero.name}'s army" if self.hero else "the garrison"
        if not cost and self.hero:
            cost = self.town.recruit(key, count)
            where = "the garrison (hero's army is full)"
        if not cost:
            self.say("No free slot for these troops.", C_RED)
            sound_engine.play("error")
            return 0
        self.res["gold"] -= cost["gold"]
        self.counts[tier] = 0
        sound_engine.play("recruit")
        self.say(f"Recruited {count} {unit_name(key, count)} into {where}.", C_GRN)
        return count

    def recruit_all(self):
        total = 0
        for tier in sorted(self.choice, reverse=True):   # best units first
            total += self.recruit(tier, self.max_affordable(tier))
        if not total:
            self.say("Nothing affordable to recruit.", C_SUB)

    def row_widgets(self, tier):
        y = ROW_Y0 + (tier - 1) * ROW_H
        return {"minus": pygame.Rect(SW - 252, y + 16, 28, 28), "count": pygame.Rect(SW - 220, y + 16, 54, 28),
                "plus": pygame.Rect(SW - 162, y + 16, 28, 28), "recruit": pygame.Rect(SW - 126, y + 15, 112, 30),
                "switch": pygame.Rect(PX + 250, y + 6, 70, 20)}

    def slot_rect(self, which, i):
        y = HERO_SLOTS_Y if which == "hero" else GARRISON_SLOTS_Y
        return pygame.Rect(PX + 12 + i * (SLOT_W + SLOT_GAP), y, SLOT_W, SLOT_H)

    def units(self, which):
        return self.hero.army if which == "hero" else self.town.garrison

    def click_slot(self, which, i):
        units = self.units(which)
        if self.sel is None:
            if units[i]:
                self.sel = (which, i)
            return
        sw, si = self.sel
        self.sel = None
        if (sw, si) == (which, i):
            return
        self.move_stack(sw, si, which, i)

    def move_stack(self, sw, si, dw, di):
        src, dst = self.units(sw), self.units(dw)
        a, b = src[si], dst[di]
        if a is None:
            return
        hero_army_after = None
        if self.hero and sw != dw:
            # the hero must keep at least one stack
            if sw == "hero" and (b is None or b.creature == a.creature):
                hero_army_after = sum(1 for s in self.hero.army if s) - 1
            if hero_army_after == 0:
                self.say("A hero can't leave town without an army.", C_RED)
                sound_engine.play("error")
                return
        if b and b.creature == a.creature:
            b.count += a.count
            src[si] = None
        else:
            src[si], dst[di] = b, a

    def shift_selected(self, d):
        if not self.sel:
            return
        which, i = self.sel
        j = i + d
        if 0 <= j < 7:
            units = self.units(which)
            units[i], units[j] = units[j], units[i]
            self.sel = (which, j)

    # ─────────────────────────── scene interface ───────────────────────────
    def update(self, dt):
        self.t += dt
        for m in self.msgs:
            m[1] -= dt
        self.msgs = [m for m in self.msgs if m[1] > 0]
        mx, my = pygame.mouse.get_pos()
        for b in [self.btn_close, self.btn_recruit_all] + list(self.btn_tabs.values()):
            b.update(mx, my)
        self.hover_building = None
        if self.tab == "buildings" and LIST.collidepoint(mx, my):
            layout, _ = self.building_layout()
            for kind, y, name in layout:
                top = LIST.y + y - self.scroll
                if kind == "entry" and top <= my < top + ENTRY_H:
                    self.hover_building = name
        for r, name in self.hotspots:
            if r.collidepoint(mx, my):
                self.hover_building = name
        if self.tab == "buildings" and self.hover_building and LIST.collidepoint(mx, my):
            layout, _ = self.building_layout()
            for kind, y, name in layout:
                if (kind == "entry" and self.build_button_rect(y).collidepoint(mx, my)
                        and self.town.build_status(name, self.res) == "available"):
                    request_hand()
        elif self.tab == "garrison":
            for tier in self.choice:
                if any(r.collidepoint(mx, my) for r in self.row_widgets(tier).values()):
                    request_hand()
            for which in (["hero"] if self.hero else []) + ["garrison"]:
                for i in range(7):
                    if self.slot_rect(which, i).collidepoint(mx, my) and (self.units(which)[i] or self.sel):
                        request_hand()

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.sel:
                    self.sel = None
                else:
                    self.close()
            elif ev.key == pygame.K_LEFT:
                self.shift_selected(-1)
            elif ev.key == pygame.K_RIGHT:
                self.shift_selected(1)
            elif ev.key == pygame.K_TAB:
                self.tab = "garrison" if self.tab == "buildings" else "buildings"
            return
        if ev.type == pygame.MOUSEWHEEL and self.tab == "buildings":
            _, total = self.building_layout()
            self.scroll = max(0, min(max(0, total - LIST.h), self.scroll - ev.y * 40))
            return
        if self.btn_close.clicked(ev):
            self.close()
            return
        for name, b in self.btn_tabs.items():
            if b.clicked(ev):
                self.tab, self.sel = name, None
                return
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button not in (1, 3):
            return
        mx, my = ev.pos
        if self.tab == "buildings":
            if ev.button == 1 and LIST.collidepoint(mx, my):
                layout, _ = self.building_layout()
                for kind, y, name in layout:
                    if kind == "entry" and self.build_button_rect(y).collidepoint(mx, my):
                        self.try_build(name)
                        return
        else:
            self.handle_garrison_click(ev, mx, my)

    def handle_garrison_click(self, ev, mx, my):
        if self.btn_recruit_all.clicked(ev):
            self.recruit_all()
            return
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        for tier in range(1, 8):
            if tier not in self.choice:
                continue
            w = self.row_widgets(tier)
            step = 10 if shift else 1
            if w["minus"].collidepoint(mx, my):
                self.counts[tier] = max(0, self.counts[tier] - step)
            elif w["plus"].collidepoint(mx, my):
                self.counts[tier] = min(self.max_affordable(tier), self.counts[tier] + step)
            elif w["count"].collidepoint(mx, my):
                self.counts[tier] = self.max_affordable(tier)
            elif w["recruit"].collidepoint(mx, my) and self.counts[tier] > 0:
                self.recruit(tier, self.counts[tier])
            elif w["switch"].collidepoint(mx, my):
                keys = self.town.dwellings()[tier]
                if len(keys) > 1:
                    self.choice[tier] = keys[(keys.index(self.choice[tier]) + 1) % len(keys)]
                    self.counts[tier] = min(self.counts[tier], self.max_affordable(tier))
            else:
                continue
            return
        rows = (["hero"] if self.hero else []) + ["garrison"]
        for which in rows:
            for i in range(7):
                if self.slot_rect(which, i).collidepoint(mx, my):
                    if ev.button == 3:
                        self.sel = None
                    else:
                        self.click_slot(which, i)
                    return
        self.sel = None

    # ─────────────────────────── drawing ───────────────────────────
    def draw(self, surf):
        F = main.F
        self.hotspots = town_art.draw_town_view(surf, (0, HEAD_H, PX, SH - HEAD_H), self.town, self.t, F["ti"])
        self.draw_left_overlay(surf)
        pygame.draw.rect(surf, C_BG1, (PX, HEAD_H, SW - PX, SH - HEAD_H))
        pygame.draw.line(surf, C_BDR, (PX, HEAD_H), (PX, SH), 2)
        self.draw_header(surf)
        for name, b in self.btn_tabs.items():
            b.bdr = C_GOLD if self.tab == name else C_BDR
            b.tc = C_GOLD if self.tab == name else C_SUB
            b.draw(surf)
        self.draw_resources(surf)
        if self.tab == "buildings":
            self.draw_buildings(surf)
        else:
            self.draw_garrison(surf)
        self.draw_messages(surf)
        if self.hover_building:
            self.draw_tooltip(surf, self.building_tooltip(self.hover_building))
        elif self.tab == "garrison":
            self.draw_creature_hover(surf)

    def draw_creature_hover(self, surf):
        """Full stats card over a recruit row's creature; a tooltip over army slots."""
        mx, my = pygame.mouse.get_pos()
        for tier in range(1, 8):
            y = ROW_Y0 + (tier - 1) * ROW_H
            if pygame.Rect(PX + 10, y + 2, 300, ROW_H - 4).collidepoint(mx, my):
                key = self.choice.get(tier) or next(k for k, c in CREATURES.items()
                                                    if c["faction"] == self.town.faction and c["tier"] == tier
                                                    and not c["is_upgraded"])
                creature_art.draw_creature_card(surf, key, (mx, my), self.t, main.F)
                return
        for which in (["hero"] if self.hero else []) + ["garrison"]:
            for i in range(7):
                st = self.units(which)[i]
                if st and self.slot_rect(which, i).collidepoint(mx, my):
                    draw_tooltip(surf, creature_art.creature_tooltip(st.creature, st.count), main.F["ti"],
                                 (mx, my - 120))
                    return

    def draw_header(self, surf):
        F, S, town = main.F, main.STATE, self.town
        pygame.draw.rect(surf, C_BG1, (0, 0, SW, HEAD_H))
        pygame.draw.line(surf, C_BDR, (0, HEAD_H - 1), (SW, HEAD_H - 1), 2)
        r = blit(surf, town.name, F["lg"], C_GOLD, 16, 11)
        col = FACTION_COLORS.get(town.faction, C_BDR)
        badge = F["ti"].render(town.faction.upper(), True, (250, 248, 240))
        br = badge.get_rect(midleft=(r.right + 14, r.centery)).inflate(16, 8)
        pygame.draw.rect(surf, col, br, border_radius=10)
        surf.blit(badge, badge.get_rect(center=br.center))
        blit(surf, f"Day {S['day']}, Week {S['week']}, Month {S['month']}", F["md"], C_TXT, SW // 2, 16, "center")
        pygame.draw.circle(surf, RES_COLORS["gold"], (SW - 200, 28), 9)
        blit(surf, f"{self.res['gold']:,}", F["md"], C_TXT, SW - 186, 16)
        self.btn_close.draw(surf)

    def draw_resources(self, surf):
        F = main.F
        x = PX + 430
        for res in RESOURCES[1:]:
            pygame.draw.circle(surf, RES_COLORS[res], (x + 6, 82), 6)
            blit(surf, str(self.res.get(res, 0)), F["ti"], C_TXT, x + 15, 75)
            x += 32 if self.res.get(res, 0) < 100 else 40
        town = self.town
        blit(surf, f"Income +{town.income_per_day():,} gold/day", F["ti"], C_SUB, PX + 12, 108)
        if town.built_today:
            blit(surf, "Already built here today", F["ti"], C_HINT, SW - 14, 108, "right")

    def draw_left_overlay(self, surf):
        F = main.F
        if self.hero:
            r = pygame.Rect(10, HEAD_H + 10, 230, 64)
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            box.fill((10, 12, 20, 190))
            surf.blit(box, r)
            hero_art.draw_hero_portrait(surf, (r.x + 6, r.y + 6, 52, 52), self.hero.faction, None)
            blit(surf, f"{self.hero.name} is visiting", F["sm"], C_GOLD, r.x + 66, r.y + 8)
            blit(surf, f"Mana {self.hero.mana}/{self.hero.mana_max} · {len(self.hero.spells)} spells", F["ti"], C_BLUE, r.x + 66, r.y + 34)

    # buildings
    def draw_buildings(self, surf):
        F, town = main.F, self.town
        layout, total = self.building_layout()
        self.scroll = max(0, min(max(0, total - LIST.h), self.scroll))
        old = surf.get_clip()
        surf.set_clip(LIST)
        mx, my = pygame.mouse.get_pos()
        for kind, y, name in layout:
            top = LIST.y + y - self.scroll
            if top > LIST.bottom or top + ENTRY_H < LIST.y:
                continue
            if kind == "group":
                blit(surf, name.upper(), F["sm"], town_art.GROUP_COLORS[name], LIST.x + 4, top + 8)
                pygame.draw.line(surf, C_BDR, (LIST.x + 90, top + 17), (LIST.right - 20, top + 17), 1)
                continue
            self.draw_entry(surf, name, top, mx, my)
        surf.set_clip(old)
        # scrollbar
        if total > LIST.h:
            track = pygame.Rect(LIST.right - 8, LIST.y, 6, LIST.h)
            pygame.draw.rect(surf, C_BG0, track, border_radius=3)
            th = max(30, LIST.h * LIST.h // total)
            ty = LIST.y + (LIST.h - th) * self.scroll // (total - LIST.h)
            pygame.draw.rect(surf, C_BDR, (track.x, ty, 6, th), border_radius=3)

    def draw_entry(self, surf, name, top, mx, my):
        F, town = main.F, self.town
        b = town.defs()[name]
        status = town.build_status(name, self.res)
        r = pygame.Rect(LIST.x, top + 2, LIST.w - 14, ENTRY_H - 4)
        bg = (26, 32, 46) if status == "built" else C_BG2
        if self.hover_building == name and status != "built":
            bg = (40, 50, 72)
        panel(surf, r, bg, C_BDR, br=8)
        gcol = town_art.GROUP_COLORS[b["group"]]
        if status == "built":
            gcol = tuple(v // 2 for v in gcol)
        pygame.draw.rect(surf, gcol, (r.x + 10, r.y + 9, 36, 36), border_radius=6)
        if b["category"] == "dwelling":
            blit(surf, str(b["tier"]), F["md"], (20, 20, 20), r.x + 28, r.y + 15, "center")
        tc = C_HINT if status == "built" else C_TXT
        blit(surf, name, _bold(15), tc, r.x + 56, r.y + 6)
        # cost
        x = r.x + 56
        for res, amt in b["cost"].items():
            short = self.res.get(res, 0) < amt and status != "built"
            pygame.draw.circle(surf, RES_COLORS[res], (x + 5, r.y + 36), 5)
            img = F["ti"].render(f"{amt:,}", True, C_RED if short else (C_HINT if status == "built" else C_SUB))
            surf.blit(img, (x + 13, r.y + 29))
            x += img.get_width() + 24
        # status (right side)
        rx = r.right - 120
        btn = self.build_button_rect(top - LIST.y + self.scroll)
        if status == "built":
            draw_check(surf, rx + 10, r.y + 16)
            blit(surf, "BUILT", F["sm"], C_GRN, rx + 32, r.y + 14)
        elif status == "locked":
            draw_lock(surf, rx - 4, r.y + 8)
            missing = town.missing_prereqs(name)
            req = ", ".join(missing) if missing else "water next to town"
            blit_wrap(surf, f"Requires: {req}", F["ti"], C_RED, rx + 16, r.y + 6, 110, gap=0)
        else:
            enabled = status == "available"
            hov = enabled and btn.collidepoint(mx, my)
            col = (95, 70, 25) if hov else (60, 45, 20) if enabled else (40, 42, 50)
            pygame.draw.rect(surf, col, btn, border_radius=6)
            pygame.draw.rect(surf, C_GOLD if enabled else C_BDR, btn, 2 if enabled else 1, border_radius=6)
            blit(surf, "BUILD", F["sm"], C_GOLD if enabled else C_HINT, btn.centerx, btn.y + 6, "center")
            if status == "unaffordable":
                need = ", ".join(f"{v:,} {k}" for k, v in town.deficit(name, self.res).items())
                img = F["ti"].render(f"Need {need}", True, C_RED)
                surf.blit(img, img.get_rect(topright=(btn.right, btn.bottom + 1)))
            elif status == "built_today":
                blit(surf, "1 per day", F["ti"], C_HINT, btn.right, btn.bottom + 1, "right")

    # garrison
    def draw_garrison(self, surf):
        F, town = main.F, self.town
        mx, my = pygame.mouse.get_pos()
        total_cost = 0
        dwell_names = {}
        for n, b in town.defs().items():
            if b["category"] == "dwelling" and not b.get("upgraded"):
                dwell_names[b["tier"]] = n
        base_keys = {}
        for k, c in CREATURES.items():
            if c["faction"] == town.faction and not c["is_upgraded"]:
                base_keys[c["tier"]] = k
        for tier in range(1, 8):
            y = ROW_Y0 + (tier - 1) * ROW_H
            row = pygame.Rect(PX + 10, y + 2, SW - PX - 20, ROW_H - 4)
            key = self.choice.get(tier)
            panel(surf, row, C_BG2 if key else (24, 28, 40), C_BDR, br=8)
            show = key or base_keys[tier]
            creature_art.draw_creature(surf, row.x + 30, row.centery - 2, show, self.t if key else 0, size=48)
            c = CREATURES[show]
            blit(surf, c["name"], _bold(15), C_TXT if key else C_HINT, row.x + 64, row.y + 6)
            tb = F["ti"].render(f"T{tier}", True, (20, 20, 20))
            tbr = tb.get_rect(topleft=(row.x + 64 + _bold(15).size(c["name"])[0] + 8, row.y + 7)).inflate(8, 2)
            pygame.draw.rect(surf, C_GOLD if key else C_HINT, tbr, border_radius=6)
            surf.blit(tb, tb.get_rect(center=tbr.center))
            w = self.row_widgets(tier)
            if not key:
                blit(surf, f"Build {dwell_names.get(tier, 'the dwelling')} to recruit", F["ti"], C_HINT, row.x + 64, row.y + 30)
                continue
            if len(town.dwellings()[tier]) > 1:
                hov = w["switch"].collidepoint(mx, my)
                pygame.draw.rect(surf, (60, 50, 90) if hov else (45, 38, 70), w["switch"], border_radius=5)
                blit(surf, "switch", F["ti"], (220, 200, 255), w["switch"].centerx, w["switch"].y + 2, "center")
            avail = town.pool.get(str(tier), 0)
            blit(surf, f"Available: {avail}  (+{town.weekly_growth(tier)}/wk)", F["ti"], C_SUB, row.x + 64, row.y + 30)
            n = self.counts[tier]
            total_cost += n * c["cost"]
            blit(surf, f"{n} × {c['cost']} gold = {n * c['cost']:,}", F["ti"], C_TXT, SW - 262, row.y + 22, "right")
            for name in ("minus", "plus"):
                rr = w[name]
                pygame.draw.rect(surf, (55, 65, 90) if rr.collidepoint(mx, my) else C_BG1, rr, border_radius=5)
                pygame.draw.rect(surf, C_BDR, rr, 1, border_radius=5)
                blit(surf, "-" if name == "minus" else "+", F["md"], C_TXT, rr.centerx, rr.y + 1, "center")
            pygame.draw.rect(surf, C_BG0, w["count"], border_radius=5)
            pygame.draw.rect(surf, C_BDR, w["count"], 1, border_radius=5)
            blit(surf, str(n), F["sm"], C_TXT, w["count"].centerx, w["count"].y + 5, "center")
            ok = n > 0
            rr = w["recruit"]
            pygame.draw.rect(surf, ((95, 70, 25) if rr.collidepoint(mx, my) else (60, 45, 20)) if ok else (40, 42, 50), rr, border_radius=6)
            pygame.draw.rect(surf, C_GOLD if ok else C_BDR, rr, 1, border_radius=6)
            blit(surf, "RECRUIT", F["sm"], C_GOLD if ok else C_HINT, rr.centerx, rr.y + 6, "center")
        # totals
        ty = ROW_Y0 + 7 * ROW_H + 10
        col = C_RED if total_cost > self.res["gold"] else C_TXT
        blit(surf, f"Total cost: {total_cost:,} gold", F["md"], col, PX + 14, ty + 2)
        blit(surf, "shift = ±10 · click count for max", F["ti"], C_HINT, PX + 260, ty + 8)
        self.btn_recruit_all.draw(surf)
        # armies
        if self.hero:
            blit(surf, f"HERO ARMY — {self.hero.name}", F["sm"], C_GOLD, PX + 14, HERO_SLOTS_Y - 20)
            self.draw_slots(surf, "hero", mx, my)
        else:
            blit(surf, "No hero visiting — recruits join the garrison.", F["sm"], C_HINT, PX + 14, HERO_SLOTS_Y + 24)
        blit(surf, "TOWN GARRISON", F["sm"], C_GOLD, PX + 14, GARRISON_SLOTS_Y - 20)
        blit(surf, "click a stack, then a slot to move · ← → shift", F["ti"], C_HINT, SW - 14, GARRISON_SLOTS_Y - 18, "right")
        self.draw_slots(surf, "garrison", mx, my)

    def draw_slots(self, surf, which, mx, my):
        F = main.F
        units = self.units(which)
        for i in range(7):
            r = self.slot_rect(which, i)
            st = units[i]
            selected = self.sel == (which, i)
            if st:
                panel(surf, r, C_BG2, C_GOLD if selected else C_BDR, br=8, bw=2 if selected else 1)
                creature_art.draw_creature(surf, r.centerx, r.y + 32, st.creature, self.t, size=52)
                blit(surf, str(st.count), F["sm"], C_TXT, r.right - 6, r.bottom - 20, "right")
            else:
                hov = self.sel and r.collidepoint(mx, my)
                pygame.draw.rect(surf, (60, 66, 80) if hov else (45, 50, 62), r, 1, border_radius=8)
                blit(surf, "Empty", F["ti"], C_HINT, r.centerx, r.centery - 8, "center")

    def draw_messages(self, surf):
        F = main.F
        y = SH - 40
        for text, left, col in reversed(self.msgs):
            img = F["sm"].render(text, True, col)
            img.set_alpha(int(255 * min(1.0, left * 2)))
            r = img.get_rect(midbottom=(PX // 2, y)).inflate(20, 8)
            bg = pygame.Surface(r.size, pygame.SRCALPHA)
            bg.fill((10, 12, 20, int(210 * min(1.0, left * 2))))
            surf.blit(bg, r)
            surf.blit(img, img.get_rect(center=r.center))
            y -= r.h + 4

    def draw_tooltip(self, surf, text):
        F = main.F
        mx, my = pygame.mouse.get_pos()
        w = 340
        h = blit_wrap(pygame.Surface((1, 1)), text, F["ti"], C_TXT, 0, 0, w - 20) + 12
        r = pygame.Rect(mx + 16, my + 12, w, h)
        if r.right > SW - 4:
            r.right = mx - 12
        if r.bottom > SH - 4:
            r.bottom = my - 8
        panel(surf, r, (14, 18, 28), C_GOLD, br=6)
        blit_wrap(surf, text, F["ti"], C_TXT, r.x + 10, r.y + 6, w - 20)
