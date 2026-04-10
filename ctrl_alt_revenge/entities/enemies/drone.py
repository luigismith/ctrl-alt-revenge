# entities/enemies/drone.py — Drone volante con traiettoria sinusoidale e laser
import math
import random
from ctrl_alt_revenge.entities.enemy import Enemy
from ctrl_alt_revenge.entities.components import Hackable
from ctrl_alt_revenge.settings import (
    DRONE_HP, DRONE_SPEED, DRONE_WIDTH, DRONE_HEIGHT,
    DRONE_SIGHT_RANGE, DRONE_SHOOT_COOLDOWN,
)


class Drone(Enemy, Hackable):
    """Drone volante: vola in sinusoide, spara laser telegrafato.

    AI behaviors: strafe, retreat when low HP, dive bomb.
    """

    def __init__(self, x, y, patrol_range=120):
        super().__init__(x, y, DRONE_WIDTH, DRONE_HEIGHT, DRONE_HP, DRONE_SPEED)
        self.init_ai(patrol_range, DRONE_SIGHT_RANGE, 90)
        self.init_hackable("drone", 1)
        self.hack_range = 50

        self.base_y = y
        self.hover_amplitude = 15
        self.hover_speed = 0.05
        self.hover_timer = 0.0

        self.shoot_cooldown = 0
        self.shoot_telegraph = 0
        self.is_shooting = False
        self.laser_active = False
        self.laser_rect = None

        self.hacked_timer = 0
        self.hacked_ally = False
        self.anim_speed = 4  # eliche veloci
        self.anim_speeds = {
            "fly": 4,
            "hacked": 4,
            "shoot": 8,
            "death": 8,
            "stunned": 8,
        }

        # AI-driven behavior state
        self.strafe_dir = 1 if random.random() > 0.5 else -1
        self.strafe_speed = DRONE_SPEED * 0.4
        self.is_retreating = False
        self.dive_bombing = False
        self.dive_target_x = 0
        self.dive_target_y = 0
        self.dive_timer = 0
        self.attack_cycle_count = 0

    def _ai_update(self, dt):
        if self.hacked_ally:
            self._hacked_behavior(dt)
            return

        # Hover sinusoidale
        if not self.dive_bombing:
            self.hover_timer += self.hover_speed * dt
            hover_offset = math.sin(self.hover_timer) * self.hover_amplitude
            self.y = self.base_y + hover_offset

        self.laser_active = False
        self.laser_rect = None

        # Retreat behavior: when HP = 1, fly higher and extend range
        if self.hp <= 1 and not self.is_retreating:
            self.is_retreating = True
            self.base_y -= 30  # fly higher
            self.sight_range = int(self.sight_range * 1.5)  # increase shoot range

        if self.ai_state == "patrol":
            self.patrol_update(dt)
            # Non cade: il drone vola
            self.vel_y = 0
            self.on_ground = True  # impedisce la gravità
            self.set_anim("fly")
            if self.target and self.can_see_target(self.target):
                self.ai_state = "chase"

        elif self.ai_state == "chase":
            if not self.target or not self.target.alive:
                self.ai_state = "patrol"
                return
            dx = self.target.x - self.x
            dist = abs(dx)
            self.facing = 1 if dx > 0 else -1

            if dist > 60:
                self.vel_x = self.facing * self.move_speed
            else:
                self.vel_x = 0

            self.vel_y = 0
            self.on_ground = True
            self.set_anim("fly")

            # Spara se in raggio e cooldown pronto
            if dist < self.sight_range and self.shoot_cooldown <= 0:
                self.attack_cycle_count += 1
                # Dive bomb: 10% chance per attack cycle
                if random.random() < 0.10 and self.target:
                    self.ai_state = "dive_bomb"
                    self.dive_bombing = True
                    self.dive_target_x = self.target.x
                    self.dive_target_y = self.target.y
                    self.dive_timer = 20
                    self.vel_x = 0
                else:
                    self.ai_state = "shooting"
                    self.shoot_telegraph = 20  # frame di telegraph
                    self.vel_x = 0

            if dist > self.sight_range * 1.5:
                self.ai_state = "patrol"
                self.patrol_start_x = self.x

        elif self.ai_state == "shooting":
            # Strafe: slowly move perpendicular to player while shooting
            self.vel_y = 0
            self.on_ground = True
            self.vel_x = self.strafe_dir * self.strafe_speed
            self.shoot_telegraph -= dt

            if self.shoot_telegraph <= 0:
                # Sparo!
                self.laser_active = True
                # Laser verso il basso
                self.laser_rect = self._create_laser()
                self.set_anim("shoot")
                self.shoot_cooldown = DRONE_SHOOT_COOLDOWN
                # Flip strafe direction for next time
                self.strafe_dir *= -1
                self.ai_state = "chase"
            else:
                # Telegraph: lampeggio
                self.set_anim("fly")

        elif self.ai_state == "dive_bomb":
            # Dive toward player quickly
            self.on_ground = True
            self.dive_timer -= dt
            dx = self.dive_target_x - self.x
            dy = self.dive_target_y - self.y
            speed = self.move_speed * 3.0
            dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
            self.vel_x = (dx / dist) * speed
            # Move Y directly since drones fly
            self.y += (dy / dist) * speed * dt
            self.set_anim("fly")
            # Activate hitbox during dive
            self.activate_hitbox(self.width, 0, self.width, self.height, 1)
            if self.dive_timer <= 0 or dist < 10:
                # End dive
                self.dive_bombing = False
                self.deactivate_hitbox()
                self.shoot_cooldown = DRONE_SHOOT_COOLDOWN
                self.base_y = self.y - 20  # recover to near current height
                self.ai_state = "chase"

    def _create_laser(self):
        """Crea il rettangolo del laser sotto il drone."""
        import pygame
        lx = int(self.x) + self.width // 2 - 2
        ly = int(self.y) + self.height
        return pygame.Rect(lx, ly, 4, 80)

    def _hacked_behavior(self, dt):
        """Quando è stato hackerato, segue il player e spara ai nemici."""
        self.hacked_timer -= dt
        if self.hacked_timer <= 0:
            self.hacked_ally = False
            return

        self.hover_timer += self.hover_speed * dt
        hover_offset = math.sin(self.hover_timer) * 8
        self.set_anim("hacked" if "hacked_right" in self.sprites or "hacked_left" in self.sprites else "fly")
        self.on_ground = True
        self.vel_y = 0

        if self.target:
            # Vola sopra il player
            target_x = self.target.x - 10
            target_y = self.target.y - 40 + hover_offset
            dx = target_x - self.x
            dy = target_y - self.y
            self.x += dx * 0.05 * dt
            self.y += dy * 0.05 * dt
            self.facing = self.target.facing

    def on_hack_success(self):
        """Il drone diventa alleato per 8 secondi."""
        self.hacked = True
        self.hacked_ally = True
        self.hacked_timer = 8 * 60  # 8 secondi in frame
        self.ai_state = "patrol"

    def on_hack_fail(self):
        self.ai_state = "chase"

    def can_see_target(self, target):
        """I droni vedono in tutte le direzioni."""
        if not target.alive:
            return False
        dx = target.x - self.x
        dy = target.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        max_range = self.sight_range
        if getattr(target, "is_crouching", False):
            max_range /= 2
        return dist < max_range
