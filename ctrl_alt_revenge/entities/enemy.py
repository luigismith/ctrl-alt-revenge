# entities/enemy.py — Classe base nemico
import pygame
from ctrl_alt_revenge.entities.entity import Entity
from ctrl_alt_revenge.entities.components import Health, Hitbox, Hurtbox, AIComponent


class Enemy(Entity, Health, Hitbox, Hurtbox, AIComponent):
    """Classe base per tutti i nemici."""

    def __init__(self, x, y, width, height, hp, speed):
        Entity.__init__(self, x, y, width, height)
        self.init_health(hp)
        self.init_hitbox()
        self.init_hurtbox()
        self.init_ai()
        self.collision_width = width - 2
        self.collision_height = height
        self.move_speed = speed
        self.contact_damage = 1
        self.score_value = 100

    def update_hurtbox(self):
        self.hurtbox_rect = pygame.Rect(
            int(self.x) + 1, int(self.y) + 1,
            self.collision_width - 2, self.collision_height - 2)

    def update(self, dt=1.0, player=None):
        if not self.alive:
            self.update_animation(dt)
            return

        self.update_iframes(dt)
        self.update_hurtbox()

        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.ai_state = "stunned"
            self.vel_x = 0
            self.set_anim("stunned" if "stunned" in self._get_anim_keys() else "hurt")
            self.update_animation(dt)
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        if player and player.alive:
            self.target = player
            self._ai_update(dt)

        self.update_animation(dt)

    def _ai_update(self, dt):
        """Logica AI — override nelle sottoclassi."""
        pass

    def _get_anim_keys(self):
        return set(self.sprites.keys())

    def stun(self, duration):
        """Stordisce il nemico."""
        self.stun_timer = duration
        self.ai_state = "stunned"

    def die(self):
        self.alive = False
        self.set_anim("death")
        self.vel_x = 0
        self.vel_y = 0
        self.hitbox_active = False
