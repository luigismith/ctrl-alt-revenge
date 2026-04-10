# core/camera.py — Camera con scrolling fluido che segue il player
import pygame
from ctrl_alt_revenge.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT, TILE_SIZE


class Camera:
    """Camera 2D che segue il target con lerp e limiti della mappa."""

    def __init__(self, map_width, map_height):
        self.x = 0.0
        self.y = 0.0
        self.map_width = map_width
        self.map_height = map_height
        self.lerp_speed = 0.1
        # Zona morta: il player può muoversi in quest'area senza spostare la camera
        self.deadzone_x = INTERNAL_WIDTH // 6
        self.deadzone_y = INTERNAL_HEIGHT // 6

    def update(self, target_rect, dt=1.0):
        """Aggiorna posizione camera verso il target."""
        target_cx = target_rect.centerx - INTERNAL_WIDTH // 2
        target_cy = target_rect.centery - INTERNAL_HEIGHT // 2

        # Lerp fluido
        self.x += (target_cx - self.x) * self.lerp_speed * dt
        self.y += (target_cy - self.y) * self.lerp_speed * dt

        # Clamp ai bordi della mappa
        self.x = max(0, min(self.x, self.map_width - INTERNAL_WIDTH))
        self.y = max(0, min(self.y, self.map_height - INTERNAL_HEIGHT))

    def apply(self, rect):
        """Restituisce un rettangolo traslato dalla camera."""
        return pygame.Rect(rect.x - int(self.x), rect.y - int(self.y),
                           rect.width, rect.height)

    def apply_pos(self, x, y):
        """Trasla una posizione dalla camera."""
        return int(x - self.x), int(y - self.y)

    def get_offset(self):
        return -int(self.x), -int(self.y)

    def get_visible_rect(self):
        """Rettangolo visibile nel mondo."""
        return pygame.Rect(int(self.x), int(self.y),
                           INTERNAL_WIDTH, INTERNAL_HEIGHT)
