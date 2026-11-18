"""Battle visual effects: attack lunges, hex flashes, spell particles, deaths, floating text.

Each effect has update(dt) -> bool (False when finished) and draw(surf).
"""
import math
import random

import pygame

from art import creature_art
from engine.hex_grid import draw_hex


def lerp(a, b, f):
    return a + (b - a) * f


class AttackAnimation:
    """Attacker moves 1/3 of the way to the target (0.3s), then returns (0.2s)."""
    OUT, BACK = 0.3, 0.2

    def __init__(self, stack, home_px, target_px):
        self.stack, self.home, self.target = stack, home_px, target_px
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        return self.t < self.OUT + self.BACK

    def offset_pos(self):
        if self.t < self.OUT:
            f = self.t / self.OUT / 3
        else:
            f = max(0.0, 1 - (self.t - self.OUT) / self.BACK) / 3
        return lerp(self.home[0], self.target[0], f), lerp(self.home[1], self.target[1], f)


class DamageFlash:
    """The hit stack's hex flashes white for 0.15s, then fades back."""
    DUR, FADE = 0.15, 0.25

    def __init__(self, hex_pos, gx, gy):
        self.hex, self.gx, self.gy = hex_pos, gx, gy
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        return self.t < self.DUR + self.FADE

    def draw(self, surf):
        a = 230 if self.t < self.DUR else int(230 * (1 - (self.t - self.DUR) / self.FADE))
        draw_hex(surf, *self.hex, self.gx, self.gy, (255, 255, 255, max(0, a)))


class Particle:
    def __init__(self, x, y, vx, vy, life, col, r=3, gravity=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.col, self.r, self.g = col, r, gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.g * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        a = max(0, int(255 * self.life / self.max_life))
        s = pygame.Surface((self.r * 2 + 2, self.r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, a), (self.r + 1, self.r + 1), self.r)
        surf.blit(s, (self.x - self.r, self.y - self.r))


class SpellEffect:
    """damage: expanding ring (r 0->30 over 0.4s); buff: rising green particles;
    debuff: falling purple particles."""

    def __init__(self, kind, x, y):
        self.kind, self.x, self.y = kind, x, y
        self.t = 0.0
        self.parts = []
        if kind == "buff":
            self.parts = [Particle(x + random.uniform(-20, 20), y + random.uniform(0, 20), random.uniform(-8, 8),
                                   random.uniform(-70, -40), random.uniform(0.6, 1.0), (110, 240, 130), 3)
                          for _ in range(16)]
        elif kind == "debuff":
            self.parts = [Particle(x + random.uniform(-22, 22), y - random.uniform(30, 50), random.uniform(-6, 6),
                                   random.uniform(40, 70), random.uniform(0.6, 1.0), (190, 110, 255), 3)
                          for _ in range(16)]

    def update(self, dt):
        self.t += dt
        self.parts = [p for p in self.parts if p.update(dt)]
        return self.t < 0.4 if self.kind == "damage" else bool(self.parts)

    def draw(self, surf):
        if self.kind == "damage":
            f = min(1.0, self.t / 0.4)
            r = max(1, int(30 * f))
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 160, 60, int(230 * (1 - f))), (r + 4, r + 4), r, 4)
            pygame.draw.circle(ring, (255, 230, 150, int(120 * (1 - f))), (r + 4, r + 4), max(1, r // 2))
            surf.blit(ring, (self.x - r - 4, self.y - r - 4))
        for p in self.parts:
            p.draw(surf)


class StackDeathAnimation:
    """The sprite shrinks to nothing over 0.5s while grey dust scatters outward."""
    DUR = 0.5

    def __init__(self, creature_key, x, y, facing, size):
        self.key, self.x, self.y, self.facing, self.size = creature_key, x, y, facing, size
        self.t = 0.0
        self.parts = []
        for _ in range(random.randint(5, 8)):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(40, 90)
            self.parts.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp - 20, random.uniform(0.4, 0.7),
                                       (150, 150, 155), random.randint(2, 4), gravity=120))

    def update(self, dt):
        self.t += dt
        self.parts = [p for p in self.parts if p.update(dt)]
        return self.t < self.DUR or bool(self.parts)

    def draw(self, surf, t):
        f = 1 - min(1.0, self.t / self.DUR)
        if f > 0.02:
            size = max(2, int(self.size * f))
            creature_art.draw_creature(surf, self.x, self.y + (1 - f) * 14, self.key, t, size=size,
                                       facing=self.facing, flash=0.6)
        for p in self.parts:
            p.draw(surf)


class FloatingText:
    """Rises 40px/s and fades over its lifetime; pops in slightly larger at the start."""

    def __init__(self, text, x, y, color, life=1.5, big=False):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life = self.max_life = life
        self.big = big

    def update(self, dt):
        self.y -= 40 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, font):
        age = self.max_life - self.life
        scale = 1.0 + max(0.0, 0.35 - age) * 1.2
        if self.big:
            scale *= 1.15
        img = font.render(self.text, True, self.color)
        out = font.render(self.text, True, (0, 0, 0))
        if abs(scale - 1.0) > 0.01:
            img = pygame.transform.smoothscale_by(img, scale)
            out = pygame.transform.smoothscale_by(out, scale)
        a = int(255 * max(0.0, min(1.0, self.life / self.max_life * 1.6)))
        img.set_alpha(a)
        out.set_alpha(a)
        r = img.get_rect(center=(self.x, self.y))
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            surf.blit(out, r.move(dx, dy))
        surf.blit(img, r)
