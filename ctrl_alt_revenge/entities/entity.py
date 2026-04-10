# entities/entity.py — Classe base per tutte le entità
import pygame


class Entity:
    """Classe base con posizione, velocità, sprite e collisione."""

    def __init__(self, x, y, width, height):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.collision_width = width
        self.collision_height = height
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.facing = 1  # 1 = destra, -1 = sinistra
        self.alive = True
        self.active = True

        # Flag di collisione (aggiornati dalla fisica)
        self.on_ground = False
        self.on_wall_left = False
        self.on_wall_right = False
        self.hit_ceiling = False
        self.drop_through = False

        # Animazione
        self.current_anim = "idle"
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 8  # frame tra un cambio di sprite
        self.anim_speeds = {}  # velocità per-animazione (override)

        # Sprite
        self.sprites = {}
        self.image = None

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def collision_rect(self):
        return pygame.Rect(int(self.x), int(self.y),
                           self.collision_width, self.collision_height)

    def set_sprites(self, sprites_dict):
        """Imposta il dizionario di sprite."""
        self.sprites = sprites_dict

    def set_anim(self, name):
        """Cambia animazione se diversa dall'attuale."""
        if self.current_anim != name:
            self.current_anim = name
            self.anim_frame = 0
            self.anim_timer = 0

    def update_animation(self, dt=1.0):
        """Avanza l'animazione."""
        suffix = "_right" if self.facing == 1 else "_left"
        anim_key = self.current_anim + suffix

        if anim_key not in self.sprites:
            # Fallback: prova senza suffisso o idle
            anim_key = self.current_anim
            if anim_key not in self.sprites:
                anim_key = "idle" + suffix
                if anim_key not in self.sprites:
                    return

        frames = self.sprites[anim_key]
        if not frames:
            return

        speed = self.anim_speeds.get(self.current_anim, self.anim_speed)
        self.anim_timer += dt
        if self.anim_timer >= speed:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % len(frames)

        self.image = frames[self.anim_frame % len(frames)]

    def update(self, dt=1.0):
        pass

    def draw(self, surface, camera_offset=(0, 0)):
        if self.image and self.active:
            sprite_w = self.image.get_width()
            sprite_h = self.image.get_height()
            # Ancora al centro-basso della collision box
            draw_x = int(self.x) + self.collision_width // 2 - sprite_w // 2 + camera_offset[0]
            draw_y = int(self.y) + self.collision_height - sprite_h + camera_offset[1]
            surface.blit(self.image, (draw_x, draw_y))
