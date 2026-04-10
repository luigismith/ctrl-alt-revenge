# entities/enemies/thug.py — Scagnozzo umano con pattugliamento e attacco melee
from ctrl_alt_revenge.entities.enemy import Enemy
from ctrl_alt_revenge.settings import (
    THUG_HP, THUG_SPEED, THUG_WIDTH, THUG_HEIGHT,
    THUG_SIGHT_RANGE, THUG_SIGHT_CONE,
)


class Thug(Enemy):
    """Nemico umano: pattuglia, vede in cono frontale, attacca corpo a corpo."""

    def __init__(self, x, y, patrol_range=100):
        super().__init__(x, y, THUG_WIDTH, THUG_HEIGHT, THUG_HP, THUG_SPEED)
        self.init_ai(patrol_range, THUG_SIGHT_RANGE, THUG_SIGHT_CONE)
        self.attack_range = 18
        self.contact_damage = 1
        self.attack_wind_up = 15  # frame prima del colpo
        self.attack_wind_timer = 0
        self.chase_speed = THUG_SPEED * 1.5

    def _ai_update(self, dt):
        if self.ai_state == "patrol":
            self.patrol_update(dt)
            self.set_anim("walk")
            if self.target and self.can_see_target(self.target):
                self.ai_state = "alert"
                self.alert_timer = 30

        elif self.ai_state == "alert":
            self.vel_x = 0
            self.alert_timer -= dt
            self.set_anim("alert")
            if self.alert_timer <= 0:
                self.ai_state = "chase"

        elif self.ai_state == "chase":
            if not self.target or not self.target.alive:
                self.ai_state = "patrol"
                return
            dx = self.target.x - self.x
            dist = abs(dx)
            self.facing = 1 if dx > 0 else -1
            if dist > self.attack_range:
                self.vel_x = self.facing * self.chase_speed
                self.set_anim("walk")
            else:
                self.vel_x = 0
                if self.attack_cooldown <= 0:
                    self.ai_state = "attack"
                    self.attack_wind_timer = self.attack_wind_up
            # Perde il target se troppo lontano
            if dist > self.sight_range * 1.5:
                self.ai_state = "patrol"
                self.patrol_start_x = self.x

        elif self.ai_state == "attack":
            self.vel_x = 0
            self.attack_wind_timer -= dt
            if self.attack_wind_timer <= 0:
                self.set_anim("attack")
                self.activate_hitbox(self.collision_width, 4, 12, 10, self.contact_damage)
                self.attack_cooldown = 40
                self.ai_state = "chase"
            else:
                self.set_anim("idle")
                # Disattiva hitbox se era attiva
                if self.attack_wind_timer < self.attack_wind_up - 5:
                    self.deactivate_hitbox()
