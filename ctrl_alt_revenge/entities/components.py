# entities/components.py — Mixin: Health, Hitbox, Hurtbox, AI, Hackable
import pygame
from ctrl_alt_revenge.settings import PLAYER_IFRAMES


class Health:
    """Componente salute con i-frames."""

    def init_health(self, max_hp):
        self.max_hp = max_hp
        self.hp = max_hp
        self.iframes = 0
        self.is_invincible = False

    def take_damage(self, amount, knockback_x=0, knockback_y=0):
        """Subisce danno se non invincibile. Restituisce True se il danno è stato applicato."""
        if self.iframes > 0 or not self.alive:
            return False
        self.hp -= amount
        self.iframes = PLAYER_IFRAMES
        self.vel_x = knockback_x
        self.vel_y = knockback_y
        if self.hp <= 0:
            self.hp = 0
            self.die()
        return True

    def update_iframes(self, dt=1.0):
        if self.iframes > 0:
            self.iframes -= dt
            self.is_invincible = True
        else:
            self.is_invincible = False

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.max_hp)

    def die(self):
        self.alive = False


class Hitbox:
    """Zona di attacco (fa danno)."""

    def init_hitbox(self):
        self.hitbox_active = False
        self.hitbox_rect = pygame.Rect(0, 0, 0, 0)
        self.hitbox_damage = 0

    def activate_hitbox(self, offset_x, offset_y, w, h, damage):
        """Attiva la hitbox relativa alla posizione dell'entità."""
        if self.facing == 1:
            self.hitbox_rect = pygame.Rect(
                int(self.x) + offset_x, int(self.y) + offset_y, w, h)
        else:
            self.hitbox_rect = pygame.Rect(
                int(self.x) - offset_x - w + self.width,
                int(self.y) + offset_y, w, h)
        self.hitbox_damage = damage
        self.hitbox_active = True

    def deactivate_hitbox(self):
        self.hitbox_active = False


class Hurtbox:
    """Zona vulnerabile (riceve danno)."""

    def init_hurtbox(self):
        self.hurtbox_rect = pygame.Rect(0, 0, 0, 0)

    def update_hurtbox(self):
        """Aggiorna la hurtbox alla posizione corrente."""
        self.hurtbox_rect = pygame.Rect(
            int(self.x) + 2, int(self.y) + 2,
            self.collision_width - 4, self.collision_height - 4)


class Hackable:
    """Componente per entità hackerabili."""

    def init_hackable(self, hack_type="generic", hack_difficulty=1):
        self.hackable = True
        self.hacked = False
        self.hack_type = hack_type
        self.hack_difficulty = hack_difficulty
        self.hack_range = 40  # pixel

    def on_hack_success(self):
        """Override per effetto specifico dell'hack."""
        self.hacked = True

    def on_hack_fail(self):
        """Override per effetto del fallimento."""
        pass

    def is_in_hack_range(self, player_x, player_y):
        dist = abs(self.x + self.width / 2 - player_x) + abs(self.y + self.height / 2 - player_y)
        return dist < self.hack_range


class AIComponent:
    """Componente AI base per nemici."""

    def init_ai(self, patrol_range=100, sight_range=120, sight_cone=60):
        self.ai_state = "patrol"  # patrol, chase, attack, stunned, dead
        self.patrol_range = patrol_range
        self.patrol_start_x = self.x
        self.patrol_direction = 1
        self.sight_range = sight_range
        self.sight_cone = sight_cone
        self.alert_timer = 0
        self.attack_cooldown = 0
        self.stun_timer = 0
        self.target = None

    def can_see_target(self, target):
        """Controlla se il nemico vede il target nel cono visivo."""
        if not target.alive:
            return False
        dx = target.x - self.x
        dy = target.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > self.sight_range:
            return False
        # Controlla direzione (cono frontale)
        if self.facing == 1 and dx < 0:
            return False
        if self.facing == -1 and dx > 0:
            return False
        # Stealth: se il target è accovacciato, dimezza la sight range
        if getattr(target, "is_crouching", False):
            if dist > self.sight_range / 2:
                return False
        return True

    def patrol_update(self, dt=1.0):
        """Aggiorna il pattugliamento."""
        if self.ai_state != "patrol":
            return
        self.x += self.patrol_direction * getattr(self, "move_speed", 1.0) * dt
        # Inversione ai bordi del patrol
        if abs(self.x - self.patrol_start_x) > self.patrol_range:
            self.patrol_direction *= -1
            self.facing = self.patrol_direction
