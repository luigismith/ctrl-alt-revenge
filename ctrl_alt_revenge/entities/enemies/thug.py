# entities/enemies/thug.py — Scagnozzo umano con pattugliamento e attacco melee
import random
from ctrl_alt_revenge.entities.enemy import Enemy
from ctrl_alt_revenge.settings import (
    THUG_HP, THUG_SPEED, THUG_WIDTH, THUG_HEIGHT,
    THUG_SIGHT_RANGE, THUG_SIGHT_CONE,
)


class Thug(Enemy):
    """Nemico umano: pattuglia, vede in cono frontale, attacca corpo a corpo.

    AI behaviors: dodge, block, combo, flank.
    """

    def __init__(self, x, y, patrol_range=100):
        super().__init__(x, y, THUG_WIDTH, THUG_HEIGHT, THUG_HP, THUG_SPEED)
        self.init_ai(patrol_range, THUG_SIGHT_RANGE, THUG_SIGHT_CONE)
        self.attack_range = 18
        self.contact_damage = 1
        self.attack_wind_up = 10  # frame prima del colpo (faster attacks)
        self.attack_wind_timer = 0
        self.chase_speed = THUG_SPEED * 1.5

        # AI-driven behavior state
        self.dodge_timer = 0       # frames remaining in dodge
        self.dodge_vel = 0         # velocity during dodge
        self.block_timer = 0       # frames remaining in block
        self.is_blocking = False
        self.last_hit_landed = False  # track if last attack connected

    def take_damage(self, amount, knockback_x=0, knockback_y=0):
        """Override: block check, then switch to chase after getting hit."""
        # Block: if blocking, take no damage
        if self.is_blocking and self.block_timer > 0:
            return False

        result = super().take_damage(amount, knockback_x, knockback_y)
        if result and self.alive and self.target:
            self.ai_state = "chase"
        return result

    def _try_dodge(self):
        """30% chance to dodge when player is attacking and close."""
        if not self.target:
            return False
        dx = self.target.x - self.x
        dist = abs(dx)
        # Check if player is attacking (has hitbox active or in attack anim)
        player_attacking = getattr(self.target, 'hitbox_active', False)
        if player_attacking and dist < 40 and random.random() < 0.30:
            # Jump back: opposite direction of player
            direction = -1 if dx > 0 else 1
            self.dodge_vel = direction * 4
            self.dodge_timer = 10
            self.ai_state = "dodge"
            return True
        return False

    def _try_block(self):
        """20% chance to block when player attacks and thug faces player."""
        if not self.target:
            return False
        dx = self.target.x - self.x
        facing_player = (dx > 0 and self.facing == 1) or (dx < 0 and self.facing == -1)
        player_attacking = getattr(self.target, 'hitbox_active', False)
        if player_attacking and facing_player and random.random() < 0.20:
            self.block_timer = 15
            self.is_blocking = True
            self.ai_state = "block"
            return True
        return False

    def _try_flank(self):
        """If another thug is near the player on the same side, move to opposite."""
        if not self.target:
            return
        # Check for nearby thugs via the target's reference
        # We look at entities in the scene via the level if available
        scene_enemies = getattr(self.target, '_nearby_enemies', None)
        if scene_enemies is None:
            return
        dx = self.target.x - self.x
        my_side = 1 if dx > 0 else -1  # player is to my right(1) or left(-1)
        for other in scene_enemies:
            if other is self or not other.alive:
                continue
            if not isinstance(other, Thug):
                continue
            other_dx = self.target.x - other.x
            other_dist = abs(other_dx)
            if other_dist > 60:
                continue
            other_side = 1 if other_dx > 0 else -1
            if other_side == my_side:
                # Same side — try to get behind (move to opposite side)
                self.facing = -my_side
                self.vel_x = -my_side * self.chase_speed
                return

    def _ai_update(self, dt):
        # Handle dodge state
        if self.ai_state == "dodge":
            self.dodge_timer -= dt
            self.vel_x = self.dodge_vel
            self.set_anim("walk")
            if self.dodge_timer <= 0:
                self.dodge_timer = 0
                self.dodge_vel = 0
                self.ai_state = "chase"
            return

        # Handle block state
        if self.ai_state == "block":
            self.vel_x = 0
            self.block_timer -= dt
            self.set_anim("idle")
            if self.block_timer <= 0:
                self.block_timer = 0
                self.is_blocking = False
                self.ai_state = "chase"
            return

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

            # Try reactive behaviors first
            if self._try_dodge():
                return
            if self._try_block():
                return

            dx = self.target.x - self.x
            dist = abs(dx)
            self.facing = 1 if dx > 0 else -1
            if dist > self.attack_range:
                self.vel_x = self.facing * self.chase_speed
                self.set_anim("walk")
                # Try flanking when chasing
                self._try_flank()
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

                # Combo: 50% chance to attack again quickly after landing a hit
                if random.random() < 0.50:
                    self.attack_cooldown = 5  # quick follow-up
                else:
                    self.attack_cooldown = 40
                self.ai_state = "chase"
            else:
                self.set_anim("idle")
                # Disattiva hitbox se era attiva
                if self.attack_wind_timer < self.attack_wind_up - 5:
                    self.deactivate_hitbox()
