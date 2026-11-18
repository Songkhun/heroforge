"""Adventure map tile grid, fog of war and A* pathfinding (square tiles, 4-way)."""
import heapq
from collections import namedtuple

from config import TERRAIN_COST, VISION_RADIUS

Tile = namedtuple("Tile", "terrain_type object_type object_data is_passable is_explored is_visible")


class TileMap:
    def __init__(self, terrain):
        self.h = len(terrain)
        self.w = len(terrain[0])
        self.grid = [[Tile(t, None, None, TERRAIN_COST.get(t) is not None, False, False)
                      for t in row] for row in terrain]
        self.fog_version = 0   # bumped whenever fog changes, for render caches

    # ── access ──
    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x, y):
        return self.grid[y][x]

    def _set(self, x, y, **kw):
        self.grid[y][x] = self.grid[y][x]._replace(**kw)

    def set_object(self, x, y, obj_type, obj_data):
        self._set(x, y, object_type=obj_type, object_data=obj_data)

    def remove_object(self, x, y):
        self._set(x, y, object_type=None, object_data=None)

    # ── fog of war ──
    def update_fog(self, heroes_list, vision_radius=VISION_RADIUS, extra_sources=()):
        """Recompute visibility from heroes (and extra (pos, radius) sources like towns).

        Visible tiles become explored; explored tiles stay explored when out of sight.
        """
        sources = [(h.pos, vision_radius) for h in heroes_list] + list(extra_sources)
        visible = set()
        for (hx, hy), r in sources:
            for y in range(max(0, hy - r), min(self.h, hy + r + 1)):
                for x in range(max(0, hx - r), min(self.w, hx + r + 1)):
                    if (x - hx) ** 2 + (y - hy) ** 2 <= r * r + r:
                        visible.add((x, y))
        for y in range(self.h):
            for x in range(self.w):
                t = self.grid[y][x]
                vis = (x, y) in visible
                if t.is_visible != vis or (vis and not t.is_explored):
                    self.grid[y][x] = t._replace(is_visible=vis, is_explored=t.is_explored or vis)
        self.fog_version += 1

    def reveal(self, center, radius):
        """Mark a circular area explored (not visible). Returns the number of new tiles."""
        cx, cy = center
        n = 0
        for y in range(max(0, cy - radius), min(self.h, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.w, cx + radius + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius + radius and not self.grid[y][x].is_explored:
                    self.grid[y][x] = self.grid[y][x]._replace(is_explored=True)
                    n += 1
        self.fog_version += 1
        return n

    # ── movement ──
    def is_passable(self, x, y):
        """Terrain is walkable and no object occupies the tile."""
        if not self.in_bounds(x, y):
            return False
        t = self.grid[y][x]
        return t.is_passable and t.object_type is None

    def movement_cost(self, x, y):
        return TERRAIN_COST.get(self.grid[y][x].terrain_type)

    def neighbors(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def get_passable_neighbors(self, x, y):
        return [p for p in self.neighbors(x, y) if self.is_passable(*p)]

    def find_path(self, start, goal, blocked=frozenset()):
        """A* (Manhattan heuristic). Returns tiles to step through, excluding `start`.

        `goal` may hold an object (town, mine, creatures...) or a hero in `blocked`;
        such tiles can be the last step but are never walked through. [] if unreachable.
        """
        start, goal = tuple(start), tuple(goal)
        if start == goal or not self.in_bounds(*goal) or not self.get(*goal).is_passable:
            return []
        open_heap = [(0, 0, start)]
        came = {start: None}
        g = {start: 0}
        n = 0
        while open_heap:
            _, _, cur = heapq.heappop(open_heap)
            if cur == goal:
                path = []
                while cur != start:
                    path.append(cur)
                    cur = came[cur]
                return path[::-1]
            for nb in self.neighbors(*cur):
                if nb != goal and (not self.is_passable(*nb) or nb in blocked):
                    continue
                cost = g[cur] + self.movement_cost(*nb)
                if cost < g.get(nb, 1 << 30):
                    g[nb] = cost
                    came[nb] = cur
                    n += 1
                    h = abs(nb[0] - goal[0]) + abs(nb[1] - goal[1])
                    heapq.heappush(open_heap, (cost + h, n, nb))
        return []

    def path_cost(self, path):
        return sum(self.movement_cost(*p) for p in path)

    @classmethod
    def from_scenario(cls, scenario_dict):
        return cls(scenario_dict["terrain"])
