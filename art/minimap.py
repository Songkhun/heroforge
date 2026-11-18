"""Adventure-map minimap: terrain under the fog, towns, heroes and the camera frame."""
import pygame

from config import C_BG0, C_BDR, C_GOLD, TILE_SIZE, SW, MAP_VIEW_H
from art.terrain_art import TERRAIN_COLORS

TOWN_COLORS = {"player": (0, 100, 255), "enemy": (200, 0, 0)}


class Minimap:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self._terrain = None
        self._key = None

    def _scale(self, tm):
        return self.rect.w / tm.w, self.rect.h / tm.h

    def _terrain_layer(self, tm):
        """Cached tile colors; rebuilt only when the fog changes."""
        key = (tm.fog_version, id(tm))
        if self._key != key:
            sx, sy = self._scale(tm)
            surf = pygame.Surface(self.rect.size)
            surf.fill(C_BG0)
            for y in range(tm.h):
                for x in range(tm.w):
                    t = tm.get(x, y)
                    if not t.is_explored:
                        col = (10, 10, 10)
                    else:
                        col = TERRAIN_COLORS.get(t.terrain_type, (80, 80, 80))
                        if not t.is_visible:
                            col = tuple(c // 2 for c in col)   # explored but out of sight
                    surf.fill(col, (int(x * sx), int(y * sy), int((x + 1) * sx) - int(x * sx),
                                    int((y + 1) * sy) - int(y * sy)))
            self._terrain, self._key = surf, key
        return self._terrain

    def draw(self, surf, tile_map, heroes, towns, camera_pos):
        r = self.rect
        surf.blit(self._terrain_layer(tile_map), r)
        sx, sy = self._scale(tile_map)
        for town in towns:
            if not tile_map.get(*town.pos).is_explored:
                continue
            tx, ty = r.x + int((town.pos[0] + 0.5) * sx), r.y + int((town.pos[1] + 0.5) * sy)
            pygame.draw.rect(surf, TOWN_COLORS.get(town.owner, (150, 150, 150)), (tx - 3, ty - 3, 6, 6))
        for hero in heroes:
            if hero.owner != "player" and not tile_map.get(*hero.pos).is_visible:
                continue
            hx, hy = r.x + int((hero.pos[0] + 0.5) * sx), r.y + int((hero.pos[1] + 0.5) * sy)
            pygame.draw.circle(surf, (100, 200, 255) if hero.owner == "player" else (255, 100, 100), (hx, hy), 3)
        cam = pygame.Rect(r.x + int(camera_pos[0] * sx), r.y + int(camera_pos[1] * sy),
                          int(SW / TILE_SIZE * sx), int(MAP_VIEW_H / TILE_SIZE * sy))
        pygame.draw.rect(surf, C_GOLD, cam.clip(r), 1)
        pygame.draw.rect(surf, C_BDR, r, 1)

    def tile_at(self, pos, tile_map):
        """Map tile under a screen point on the minimap, or None."""
        if not self.rect.collidepoint(pos):
            return None
        sx, sy = self._scale(tile_map)
        return int((pos[0] - self.rect.x) / sx), int((pos[1] - self.rect.y) / sy)
