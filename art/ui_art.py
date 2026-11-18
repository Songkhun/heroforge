"""Reusable UI drawing helpers: text, panels, bars, buttons."""
import pygame

from config import C_BG1, C_BG2, C_BDR, C_TXT, C_GRN, C_GOLD, C_RED

# ── cursor: anything interactive under the mouse asks for the hand cursor this frame ──
_want_hand = False
_cursor_now = None


def request_hand():
    global _want_hand
    _want_hand = True


def apply_cursor():
    """Called once per frame by the main loop after scenes update."""
    global _want_hand, _cursor_now
    want = pygame.SYSTEM_CURSOR_HAND if _want_hand else pygame.SYSTEM_CURSOR_ARROW
    _want_hand = False
    if want != _cursor_now:
        try:
            pygame.mouse.set_cursor(want)
        except (pygame.error, TypeError):
            pass
        _cursor_now = want


def draw_tooltip(surf, text, font, pos=None, w=320, border=None):
    """Word-wrapped tooltip box near the mouse (kept on screen)."""
    mx, my = pos or pygame.mouse.get_pos()
    h = blit_wrap(pygame.Surface((1, 1)), text, font, C_TXT, 0, 0, w - 20) + 12
    sw, sh = surf.get_size()
    r = pygame.Rect(mx + 16, my + 12, w, h)
    if r.right > sw - 4:
        r.right = mx - 12
    if r.bottom > sh - 4:
        r.bottom = my - 8
    panel(surf, r, (14, 18, 28), border or C_GOLD, br=6)
    blit_wrap(surf, text, font, C_TXT, r.x + 10, r.y + 6, w - 20)
    return r


def blit(surf, text, font, color, x, y, align="left"):
    """Draw text. align: left | center | right (x is that edge/center; y is the top).

    Returns the drawn rect.
    """
    img = font.render(str(text), True, color)
    r = img.get_rect()
    if align == "center":
        r.midtop = (x, y)
    elif align == "right":
        r.topright = (x, y)
    else:
        r.topleft = (x, y)
    surf.blit(img, r)
    return r


def blit_wrap(surf, text, font, color, x, y, max_w, gap=3):
    """Word-wrapped text within max_w. Returns the height used."""
    line_h = font.get_linesize()
    used = 0
    for para in str(text).split("\n"):
        line = ""
        for word in para.split(" "):
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= max_w or not line:
                line = test
            else:
                blit(surf, line, font, color, x, y + used)
                used += line_h + gap
                line = word
        blit(surf, line, font, color, x, y + used)
        used += line_h + gap
    return used


def panel(surf, rect, col=None, bdr=None, br=10, bw=1):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, col or C_BG1, rect, border_radius=br)
    if bw:
        pygame.draw.rect(surf, bdr or C_BDR, rect, bw, border_radius=br)
    return rect


def hp_bar(surf, rect, hp, hp_max, col=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, (20, 20, 28), rect, border_radius=3)
    frac = max(0.0, min(1.0, hp / hp_max)) if hp_max else 0
    if col is None:
        col = C_GRN if frac > 0.5 else C_GOLD if frac > 0.25 else C_RED
    if frac > 0:
        fill = rect.copy()
        fill.width = max(1, int(rect.width * frac))
        pygame.draw.rect(surf, col, fill, border_radius=3)
    pygame.draw.rect(surf, C_BDR, rect, 1, border_radius=3)


def lighten(col, amt=30):
    return tuple(min(255, c + amt) for c in col)


class Button:
    def __init__(self, rect, label, font, col=C_BG2, hov=None, tc=C_TXT, br=8, bdr=C_BDR):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.col = col
        self.hov = hov or lighten(col, 25)
        self.tc = tc
        self.br = br
        self.bdr = bdr
        self.hovered = False
        self.enabled = True
        self.sound = "click"

    def update(self, mx, my):
        self.hovered = self.enabled and self.rect.collidepoint(mx, my)
        if self.hovered:
            request_hand()

    def draw(self, surf):
        col = self.hov if self.hovered else self.col
        tc = self.tc if self.enabled else (100, 105, 120)
        pygame.draw.rect(surf, col, self.rect, border_radius=self.br)
        pygame.draw.rect(surf, self.bdr, self.rect, 2 if self.hovered else 1, border_radius=self.br)
        img = self.font.render(self.label, True, tc)
        surf.blit(img, img.get_rect(center=self.rect.center))

    def clicked(self, ev):
        hit = (self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
               and self.rect.collidepoint(ev.pos))
        if hit and self.sound:
            from engine import sound_engine
            sound_engine.play(self.sound)
        return hit
