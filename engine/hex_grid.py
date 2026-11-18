"""Hex grid math for combat: even-r offset coordinates, pointy-top hexes.

Even rows are shifted right by half a hex. (col, row) is the offset coordinate;
distance and pixel conversion go through axial/cube coordinates.
Hexes are HEX_W x HEX_H pixels (a vertically squashed regular hex), rows are
0.75 * HEX_H apart.
"""
import heapq
import math

import pygame

GRID_COLS, GRID_ROWS = 15, 11
HEX_W, HEX_H = 56, 50
ROW_STEP = HEX_H * 0.75

# even-r neighbor offsets (redblobgames), indexed by row parity
_NEIGHBORS = {
    0: [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)],     # even rows (shifted right)
    1: [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)],   # odd rows
}


def in_grid(col, row):
    return 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS


def hex_to_pixel(col, row):
    """Center of a hex relative to the grid's top-left corner."""
    px = col * HEX_W + (HEX_W / 2 if row % 2 == 0 else 0) + HEX_W / 2
    py = row * ROW_STEP + HEX_H / 2
    return px, py


def offset_to_axial(col, row):
    return col - (row + (row & 1)) // 2, row


def axial_to_offset(q, r):
    return q + (r + (r & 1)) // 2, r


def _cube_round(q, r):
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return int(rq), int(rr)


def pixel_to_hex(px, py):
    """Hex containing a point (relative to the grid's top-left). May be off-grid."""
    # Axial (0,0) is offset (0,0); undo its pixel position, then unsquash to a regular hex.
    x = (px - HEX_W) / (HEX_W / math.sqrt(3))
    y = (py - HEX_H / 2) / (HEX_H / 2)
    q = math.sqrt(3) / 3 * x - y / 3
    r = 2 / 3 * y
    return axial_to_offset(*_cube_round(q, r))


def hex_neighbors(col, row):
    return [(col + dc, row + dr) for dc, dr in _NEIGHBORS[row & 1] if in_grid(col + dc, row + dr)]


def hex_distance(a, b):
    aq, ar = offset_to_axial(*a)
    bq, br = offset_to_axial(*b)
    dq, dr = aq - bq, ar - br
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def get_reachable(col, row, speed, occupied, flying=False):
    """Hexes a stack can move to this turn (not including its own hex).

    Walkers go around occupied hexes (BFS); flyers only need a free hex within range.
    """
    start = (col, row)
    if flying:
        return {(c, r) for c in range(GRID_COLS) for r in range(GRID_ROWS)
                if (c, r) not in occupied and 0 < hex_distance(start, (c, r)) <= speed}
    seen = {start: 0}
    frontier = [start]
    while frontier:
        nxt = []
        for cur in frontier:
            d = seen[cur]
            if d >= speed:
                continue
            for nb in hex_neighbors(*cur):
                if nb not in seen and nb not in occupied:
                    seen[nb] = d + 1
                    nxt.append(nb)
        frontier = nxt
    seen.pop(start)
    return set(seen)


def get_melee_targets(col, row, reachable, enemy_hexes):
    """Enemy hexes the stack can hit in melee: adjacent now or after a move."""
    stand = set(reachable) | {(col, row)}
    return {e for e in enemy_hexes if any(nb in stand for nb in hex_neighbors(*e))}


def get_ranged_targets(col, row, all_enemy_hexes):
    """Shooters can target any enemy (nothing blocks line of sight)."""
    return set(all_enemy_hexes)


def find_hex_path(start, end, blocked_hexes):
    """A* path from start to end, excluding start and including end. [] if none."""
    start, end = tuple(start), tuple(end)
    if start == end or end in blocked_hexes or not in_grid(*end):
        return []
    heap = [(0, 0, start)]
    came = {start: None}
    g = {start: 0}
    n = 0
    while heap:
        _, _, cur = heapq.heappop(heap)
        if cur == end:
            path = []
            while cur != start:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        for nb in hex_neighbors(*cur):
            if nb in blocked_hexes and nb != end:
                continue
            cost = g[cur] + 1
            if cost < g.get(nb, 1 << 30):
                g[nb] = cost
                came[nb] = cur
                n += 1
                heapq.heappush(heap, (cost + hex_distance(nb, end), n, nb))
    return []


def hex_corners(cx, cy, shrink=0):
    w, h = HEX_W / 2 - shrink, HEX_H / 2 - shrink
    return [(cx, cy - h), (cx + w, cy - h / 2), (cx + w, cy + h / 2),
            (cx, cy + h), (cx - w, cy + h / 2), (cx - w, cy - h / 2)]


def draw_hex(surf, col, row, offset_x, offset_y, fill_col, border_col=None, t=0, width=1):
    """Draw a hex at a grid position. fill_col may be RGBA (alpha blended) or None."""
    cx, cy = hex_to_pixel(col, row)
    cx, cy = cx + offset_x, cy + offset_y
    pts = hex_corners(cx, cy)
    if fill_col is not None:
        if len(fill_col) == 4 and fill_col[3] < 255:
            r = pygame.Rect(cx - HEX_W / 2, cy - HEX_H / 2, HEX_W + 1, HEX_H + 1)
            tmp = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.polygon(tmp, fill_col, [(x - r.x, y - r.y) for x, y in pts])
            surf.blit(tmp, r)
        else:
            pygame.draw.polygon(surf, fill_col[:3], pts)
    if border_col is not None:
        pygame.draw.polygon(surf, border_col, pts, width)
    return cx, cy
