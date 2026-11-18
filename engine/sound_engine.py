"""Synthesized sound effects without numpy (stdlib `array`), so the game stays pygame-only.

SOUNDS holds every effect, built once by init_sounds() (the loading screen calls it).
play(name) is safe to call anywhere: it does nothing if the mixer is unavailable.
Sound objects live here rather than in STATE because STATE is saved to JSON.
"""
import array
import math
import random

import pygame

SOUNDS = {}
_ready = None


def _mixer_ready():
    global _ready
    if _ready is None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            _ready = bool(pygame.mixer.get_init())
        except pygame.error:
            _ready = False
    return _ready


def _samples(freq, duration, wave="sine", volume=0.3, fade_out=True, freq_end=None):
    """Mono int samples. freq_end makes a linear frequency sweep."""
    rate = pygame.mixer.get_init()[0]
    n = max(1, int(rate * duration))
    amp = 32767 * volume
    out = []
    phase = 0.0
    for i in range(n):
        f = freq if freq_end is None else freq + (freq_end - freq) * i / n
        phase += 2 * math.pi * f / rate
        if wave == "square":
            v = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == "noise":
            v = random.uniform(-1, 1)
        else:
            v = math.sin(phase)
        env = (1 - i / n) ** 2 if fade_out else 1.0
        if i < 64:   # tiny attack ramp avoids clicks
            env *= i / 64
        out.append(int(v * amp * env))
    return out


def _to_sound(mono):
    channels = pygame.mixer.get_init()[2]
    data = array.array("h")
    for s in mono:
        s = max(-32768, min(32767, s))
        for _ in range(channels):
            data.append(s)
    return pygame.mixer.Sound(buffer=data.tobytes())


def make_sound(freq, duration, wave="sine", volume=0.3, fade_out=True):
    """Synthesize one tone (sine | square | noise). Returns a Sound, or None without audio."""
    if not _mixer_ready():
        return None
    try:
        return _to_sound(_samples(freq, duration, wave, volume, fade_out))
    except pygame.error:
        return None


def _mix(*parts):
    """Sum several sample lists (layered sounds)."""
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def _seq(*parts):
    """Concatenate sample lists (melodies)."""
    out = []
    for p in parts:
        out += p
    return out


def init_sounds():
    """Build the SOUNDS table once (a fraction of a second of pure-Python synthesis)."""
    if SOUNDS or not _mixer_ready():
        return
    S = _samples
    recipes = {
        "click": lambda: S(800, 0.08, "sine", 0.2),
        "move": lambda: S(400, 0.12, "sine", 0.15),
        "sword_hit": lambda: _mix(S(200, 0.1, "square", 0.18), S(1500, 0.05, "noise", 0.15)),
        "shoot": lambda: _mix(S(900, 0.09, "sine", 0.12, freq_end=500), S(2500, 0.04, "noise", 0.06)),
        "spell_cast": lambda: S(300, 0.4, "sine", 0.25, freq_end=900),
        "gold_pickup": lambda: _mix(S(1200, 0.2, "sine", 0.3), S(1500, 0.15, "sine", 0.2)),
        "build": lambda: _mix(S(600, 0.45, "sine", 0.3), S(1200, 0.3, "sine", 0.08)),
        "recruit": lambda: _mix(S(520, 0.12, "sine", 0.2), S(780, 0.16, "sine", 0.15)),
        "victory": lambda: _seq(S(523, 0.2, "sine", 0.3), S(659, 0.2, "sine", 0.3), S(784, 0.4, "sine", 0.3)),
        "defeat": lambda: _seq(S(400, 0.3, "sine", 0.3), S(300, 0.3, "sine", 0.3), S(200, 0.5, "sine", 0.3)),
        "level_up": lambda: _seq(*[S(f, 0.15, "sine", 0.25) for f in (440, 554, 659, 880)]),
        "error": lambda: S(180, 0.15, "square", 0.08),
        "death": lambda: S(220, 0.35, "sine", 0.2, freq_end=90),
    }
    for name, make in recipes.items():
        try:
            SOUNDS[name] = _to_sound(make())
        except pygame.error:
            SOUNDS[name] = None


def play(name):
    if not SOUNDS:
        init_sounds()
    snd = SOUNDS.get(name)
    if snd:
        try:
            snd.play()
        except pygame.error:
            pass
