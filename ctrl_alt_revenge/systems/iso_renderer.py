# systems/iso_renderer.py — Fake-3D isometric rendering for the 2D world
"""Renders the side-scrolling game world using an isometric projection.

The simulation stays 2D (entity.x, entity.y as in side-scroller logic), but
the visual presentation uses a 2:1 isometric projection. The world's X axis
becomes a diagonal axis, and we add a fake third dimension (depth into the
screen) that scales with horizontal position for a 3D-like effect.

Tile diamonds replace tile squares. Sprites are drawn as billboards (always
facing camera) with elliptical shadows beneath them.

This is a renderer, not a physics system — gameplay is unchanged.
"""
import pygame
import math
from ctrl_alt_revenge.settings import (
    TILE_SIZE, INTERNAL_WIDTH, INTERNAL_HEIGHT,
    COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_NEON_PURPLE,
)


# Iso projection constants: 2:1 ratio (classic isometric)
ISO_TILE_W = 24   # half-diamond width
ISO_TILE_H = 12   # half-diamond height
ISO_DEPTH = 0.6   # how much "into the screen" the world tilts


def world_to_iso(x, y, z=0):
    """Project world coords (pixel, side-scroller) to iso screen coords.

    x: horizontal world position (pixels)
    y: vertical world position (pixels) — going DOWN = into ground
    z: fake depth offset (0 = on the main plane, +ve = forward)

    Returns (sx, sy) for blitting.
    """
    # Standard iso: screen_x = (x - y) * cos(30°), screen_y = (x + y) * sin(30°)
    # But our 'y' is vertical (gravity) not depth, so:
    # - Treat tile_x as iso X, tile_y as iso Z (depth)
    # - Use world y as height directly
    iso_x = x - y * ISO_DEPTH
    iso_y = y * ISO_DEPTH * 0.5  # squashed Y
    return int(iso_x), int(iso_y)


class IsoRenderer:
    """Renders the world from PlayState in isometric perspective.

    Call render(play_state, surface) instead of normal draw.
    """

    def __init__(self):
        self._tile_diamond_cache = {}
        self._floor_pattern = None
        self._build_floor()

    def _build_floor(self):
        """Pre-render the iso floor tile diamond for ground/platform tiles."""
        diamond = pygame.Surface((ISO_TILE_W * 2 + 2, ISO_TILE_H * 2 + 2),
                                 pygame.SRCALPHA)
        # 4 corner points of diamond
        cx, cy = ISO_TILE_W + 1, ISO_TILE_H + 1
        points = [
            (cx, cy - ISO_TILE_H),       # top
            (cx + ISO_TILE_W, cy),        # right
            (cx, cy + ISO_TILE_H),        # bottom
            (cx - ISO_TILE_W, cy),        # left
        ]
        pygame.draw.polygon(diamond, (50, 45, 75), points)
        pygame.draw.polygon(diamond, (75, 70, 110), points, 1)
        # Center highlight
        pygame.draw.circle(diamond, (65, 60, 95), (cx, cy), 4)
        self._floor_diamond = diamond

        # Platform diamond (neon top)
        plat = pygame.Surface((ISO_TILE_W * 2 + 2, ISO_TILE_H * 2 + 2),
                              pygame.SRCALPHA)
        pygame.draw.polygon(plat, (0, 100, 130), points)
        pygame.draw.polygon(plat, COLOR_NEON_BLUE, points, 1)
        self._platform_diamond = plat

        # Wall diamond (block-shaped, taller)
        wall = pygame.Surface((ISO_TILE_W * 2 + 2, ISO_TILE_H * 2 + 4),
                              pygame.SRCALPHA)
        cy2 = ISO_TILE_H + 1
        # Top face (diamond)
        top_points = [
            (cx, cy2 - ISO_TILE_H + 2),
            (cx + ISO_TILE_W, cy2 + 2),
            (cx, cy2 + ISO_TILE_H + 2),
            (cx - ISO_TILE_W, cy2 + 2),
        ]
        pygame.draw.polygon(wall, (60, 55, 95), top_points)
        pygame.draw.polygon(wall, (90, 85, 130), top_points, 1)
        self._wall_diamond = wall

        # Boss floor: orange diamond
        boss = pygame.Surface((ISO_TILE_W * 2 + 2, ISO_TILE_H * 2 + 2),
                              pygame.SRCALPHA)
        pygame.draw.polygon(boss, (90, 30, 30), points)
        pygame.draw.polygon(boss, COLOR_NEON_ORANGE, points, 1)
        self._boss_diamond = boss

    def get_tile_diamond(self, visual_type):
        """Return cached iso diamond for the given visual tile type."""
        if visual_type == 3:
            return self._platform_diamond
        if visual_type == 2:
            return self._wall_diamond
        if visual_type == 6:
            return self._boss_diamond
        return self._floor_diamond

    def render(self, play_state, surface, camera_offset):
        """Render the play state in isometric view.

        camera_offset: from camera.get_offset() — used to determine
                       which tiles to render (visible range).
        """
        surface.fill(COLOR_BG_NIGHT)

        # Background parallax — draw simple gradient + neon haze
        self._draw_iso_background(surface)

        level = play_state.level_data
        if not level:
            return

        visual = level["visual"]
        collision = level["collision"]
        h = level["height"]
        w = level["width"]

        # Camera centered on player in iso space
        player_iso_x, player_iso_y = world_to_iso(
            play_state.player.x, play_state.player.y
        )
        offset_x = INTERNAL_WIDTH // 2 - player_iso_x
        offset_y = INTERNAL_HEIGHT // 2 - player_iso_y - 30

        # Determine visible range in world tiles (rough estimate)
        # In iso, more tiles are visible than in 2D
        cx_world = play_state.player.x
        cy_world = play_state.player.y
        col_start = max(0, int((cx_world // TILE_SIZE) - 12))
        col_end = min(w, int((cx_world // TILE_SIZE) + 14))
        row_start = max(0, int((cy_world // TILE_SIZE) - 10))
        row_end = min(h, int((cy_world // TILE_SIZE) + 6))

        # Draw tiles back-to-front (sorted by row+col for proper depth)
        draw_list = []
        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                tile_visual = visual[row][col]
                if tile_visual == 0:
                    continue
                tile_collision = collision[row][col]
                if tile_collision == 0:
                    continue
                wx = col * TILE_SIZE
                wy = row * TILE_SIZE
                ix, iy = world_to_iso(wx, wy)
                draw_x = ix + offset_x - ISO_TILE_W
                draw_y = iy + offset_y - ISO_TILE_H
                draw_list.append((row + col, draw_x, draw_y, tile_visual))

        # Sort by depth (back to front)
        draw_list.sort(key=lambda d: d[0])
        for _, dx, dy, vt in draw_list:
            tile = self.get_tile_diamond(vt)
            surface.blit(tile, (dx, dy))

        # Collect all entities for depth sorting
        ent_list = []

        # Player
        ent_list.append((play_state.player, 'player'))
        # Enemies
        for e in play_state.enemies:
            if e.alive:
                ent_list.append((e, 'enemy'))

        # Sort entities by world y (deeper = drawn first)
        # In iso, larger y = closer to camera
        ent_list.sort(key=lambda t: t[0].y)

        for ent, kind in ent_list:
            self._draw_entity_iso(surface, ent, offset_x, offset_y)

        # HUD on top (call existing)
        try:
            implant_info = play_state.implants.get_equipped_info()
            chips_val = play_state.game.perks.chips if hasattr(play_state.game, 'perks') else None
            popup = (play_state.last_chip_drop, play_state.chip_drop_timer) \
                if play_state.chip_drop_timer > 0 else None
            play_state.hud.draw(surface, play_state.player, implant_info,
                                play_state.player.heat,
                                chips=chips_val, chip_popup=popup)
        except Exception:
            pass

        # Iso mode indicator (small)
        font = pygame.font.SysFont("consolas", 8)
        label = font.render("[ISO]", False, COLOR_NEON_PURPLE)
        surface.blit(label, (4, INTERNAL_HEIGHT - 12))

    def _draw_iso_background(self, surface):
        """Simple iso-friendly background — vertical gradient."""
        for y in range(INTERNAL_HEIGHT):
            t = y / INTERNAL_HEIGHT
            r = int(13 + (35 - 13) * t)
            g = int(11 + (30 - 11) * t)
            b = int(43 + (75 - 43) * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (INTERNAL_WIDTH, y))

    def _draw_entity_iso(self, surface, entity, offset_x, offset_y):
        """Draw an entity as a billboard sprite with iso shadow."""
        if not entity.image:
            return

        # Iso-project the entity's foot position
        foot_x = entity.x + entity.collision_width // 2
        foot_y = entity.y + entity.collision_height
        ix, iy = world_to_iso(foot_x, foot_y)
        draw_x = ix + offset_x
        draw_y = iy + offset_y

        # Shadow ellipse beneath
        shadow_w = entity.collision_width
        shadow_surf = pygame.Surface((shadow_w + 4, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100),
                           (0, 0, shadow_w + 4, 8))
        surface.blit(shadow_surf, (draw_x - shadow_w // 2 - 2, draw_y - 4))

        # Sprite as billboard (centered horizontally on foot, extending up)
        sprite_w = entity.image.get_width()
        sprite_h = entity.image.get_height()
        sprite_x = draw_x - sprite_w // 2
        sprite_y = draw_y - sprite_h + 2

        # I-frame blink for player
        if hasattr(entity, 'iframes') and entity.iframes > 0:
            if int(entity.iframes) % 4 < 2:
                return

        surface.blit(entity.image, (sprite_x, sprite_y))
