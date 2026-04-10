# systems/physics.py — AABB, gravità, collisioni con tilemap
import pygame
from ctrl_alt_revenge.settings import GRAVITY, MAX_FALL_SPEED, TILE_SIZE


class AABB:
    """Bounding box per collisioni."""
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def left(self): return self.x
    @property
    def right(self): return self.x + self.w
    @property
    def top(self): return self.y
    @property
    def bottom(self): return self.y + self.h
    @property
    def centerx(self): return self.x + self.w / 2
    @property
    def centery(self): return self.y + self.h / 2

    def overlaps(self, other):
        return (self.left < other.right and self.right > other.left and
                self.top < other.bottom and self.bottom > other.top)

    def intersection(self, other):
        """Restituisce la profondità di penetrazione come (dx, dy)."""
        if not self.overlaps(other):
            return 0, 0
        dx_right = other.right - self.left
        dx_left = self.right - other.left
        dy_bottom = other.bottom - self.top
        dy_top = self.bottom - other.top

        dx = dx_right if dx_right < dx_left else -dx_left
        dy = dy_bottom if dy_bottom < dy_top else -dy_top

        if abs(dx) < abs(dy):
            return dx, 0
        return 0, dy


class PhysicsSystem:
    """Gestisce gravità e collisioni con la tilemap."""

    def __init__(self, level_data):
        self.solid_tiles = []  # lista di Rect per le tile solide
        self.one_way_tiles = []  # piattaforme attraversabili dal basso
        self._build_collision_map(level_data)

    def _build_collision_map(self, level_data):
        """Costruisce la mappa di collisione dal livello."""
        self.solid_tiles.clear()
        self.one_way_tiles.clear()
        if level_data is None:
            return
        for row_idx, row in enumerate(level_data.get("collision", [])):
            for col_idx, tile in enumerate(row):
                if tile == 1:  # solido
                    self.solid_tiles.append(
                        pygame.Rect(col_idx * TILE_SIZE, row_idx * TILE_SIZE,
                                    TILE_SIZE, TILE_SIZE)
                    )
                elif tile == 2:  # one-way platform
                    self.one_way_tiles.append(
                        pygame.Rect(col_idx * TILE_SIZE, row_idx * TILE_SIZE,
                                    TILE_SIZE, TILE_SIZE)
                    )

    def rebuild(self, level_data):
        self._build_collision_map(level_data)

    def apply_gravity(self, entity, dt=1.0):
        """Applica gravità all'entità."""
        entity.vel_y += GRAVITY * dt
        if entity.vel_y > MAX_FALL_SPEED:
            entity.vel_y = MAX_FALL_SPEED

    def move_and_collide(self, entity, dt=1.0):
        """Muove l'entità e risolve collisioni. Restituisce i flag di collisione."""
        on_ground = False
        on_wall_left = False
        on_wall_right = False
        hit_ceiling = False

        # Movimento orizzontale
        entity.x += entity.vel_x * dt
        entity_rect = pygame.Rect(round(entity.x), round(entity.y),
                                  entity.collision_width, entity.collision_height)

        for tile_rect in self.solid_tiles:
            if entity_rect.colliderect(tile_rect):
                if entity.vel_x > 0:
                    entity.x = tile_rect.left - entity.collision_width
                    on_wall_right = True
                elif entity.vel_x < 0:
                    entity.x = tile_rect.right
                    on_wall_left = True
                entity.vel_x = 0
                entity_rect.x = int(entity.x)

        # Movimento verticale
        entity.y += entity.vel_y * dt
        # Usa round per evitare problemi di precisione sub-pixel
        ey = round(entity.y)
        entity_rect = pygame.Rect(int(entity.x), ey,
                                  entity.collision_width, entity.collision_height)

        for tile_rect in self.solid_tiles:
            if entity_rect.colliderect(tile_rect):
                if entity.vel_y > 0:
                    entity.y = float(tile_rect.top - entity.collision_height)
                    on_ground = True
                elif entity.vel_y < 0:
                    entity.y = float(tile_rect.bottom)
                    hit_ceiling = True
                entity.vel_y = 0
                entity_rect.y = int(entity.y)

        # One-way platforms (solo cadendo dall'alto)
        if entity.vel_y >= 0 and not getattr(entity, "drop_through", False):
            entity_rect = pygame.Rect(round(entity.x), round(entity.y),
                                      entity.collision_width, entity.collision_height)
            for tile_rect in self.one_way_tiles:
                if entity_rect.colliderect(tile_rect):
                    # Solo se i piedi sono vicini alla cima della piattaforma
                    if (entity_rect.bottom - tile_rect.top) < TILE_SIZE // 2 + 2:
                        entity.y = tile_rect.top - entity.collision_height
                        entity.vel_y = 0
                        on_ground = True

        entity.on_ground = on_ground
        entity.on_wall_left = on_wall_left
        entity.on_wall_right = on_wall_right
        entity.hit_ceiling = hit_ceiling

        return on_ground, on_wall_left, on_wall_right, hit_ceiling

    def check_overlap(self, rect1, rect2):
        """Controlla se due rettangoli si sovrappongono."""
        return rect1.colliderect(rect2)

    def raycast_horizontal(self, start_x, start_y, direction, max_dist):
        """Lancia un raggio orizzontale, restituisce la distanza al primo muro."""
        step = TILE_SIZE // 2
        dist = 0
        while dist < max_dist:
            check_x = start_x + direction * dist
            check_rect = pygame.Rect(int(check_x), int(start_y), 1, 1)
            for tile_rect in self.solid_tiles:
                if check_rect.colliderect(tile_rect):
                    return dist
            dist += step
        return max_dist
