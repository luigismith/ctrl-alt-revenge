# entities/enemies/boss_warden.py — Boss livello 1: 3 fasi
import math
import pygame
from ctrl_alt_revenge.entities.enemy import Enemy
from ctrl_alt_revenge.settings import (
    WARDEN_HP, WARDEN_WIDTH, WARDEN_HEIGHT, WARDEN_PHASE_THRESHOLDS,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM,
)


class BossWarden(Enemy):
    """Boss Warden v2.0 — 3 fasi, melee + drone-spawning + shockwave."""

    def __init__(self, x, y):
        super().__init__(x, y, WARDEN_WIDTH, WARDEN_HEIGHT, WARDEN_HP, 0.8)
        self.init_ai(patrol_range=60, sight_range=200, sight_cone=180)
        self.collision_width = 28
        self.collision_height = 38
        self.contact_damage = 2
        self.anim_speed = 10

        # Fasi
        self.phase = 1
        self.phase_thresholds = WARDEN_PHASE_THRESHOLDS

        # Pattern di attacco
        self.action_timer = 60
        self.current_action = "idle"
        self.action_sequence = ["approach", "melee", "shockwave", "spawn_drones"]
        self.action_index = 0

        # Melee
        self.melee_frame = 0
        self.melee_duration = 20

        # Shockwave
        self.shockwave_active = False
        self.shockwave_timer = 0
        self.shockwave_rects = []

        # Drone spawning
        self.spawned_drones = []
        self.max_drones = 2
        self.spawn_callback = None  # impostato dal livello

        # Arena bounds
        self.arena_left = 0
        self.arena_right = 400

        # Enrage
        self.enraged = False

        # Intro
        self.intro_timer = 120
        self.intro_done = False

    def set_arena(self, left, right):
        self.arena_left = left
        self.arena_right = right

    def _ai_update(self, dt):
        if not self.intro_done:
            self.intro_timer -= dt
            self.vel_x = 0
            self.set_anim("idle")
            if self.intro_timer <= 0:
                self.intro_done = True
            return

        # Aggiorna fase in base a HP
        if self.phase == 1 and self.hp <= self.phase_thresholds[0]:
            self.phase = 2
            self.move_speed = 1.2
        elif self.phase == 2 and self.hp <= self.phase_thresholds[1]:
            self.phase = 3
            self.move_speed = 1.6
            self.enraged = True

        # Timer azione
        self.action_timer -= dt

        if self.action_timer <= 0:
            self._next_action(dt)
        else:
            self._execute_current_action(dt)

        # Animazione fase
        phase_suffix = ""
        if self.phase == 2:
            phase_suffix = "_p2"
        elif self.phase == 3:
            phase_suffix = "_p3"

        # Prova animazione con suffisso fase, fallback a base
        desired_anim = self.current_anim
        suffix = "_right" if self.facing == 1 else "_left"
        if f"{desired_anim}{phase_suffix}{suffix}" in self.sprites:
            self.current_anim = desired_anim + phase_suffix

    def _next_action(self, dt):
        """Passa alla prossima azione nella sequenza."""
        self.action_index = (self.action_index + 1) % len(self.action_sequence)
        self.current_action = self.action_sequence[self.action_index]

        if self.current_action == "approach":
            self.action_timer = 60
        elif self.current_action == "melee":
            self.action_timer = self.melee_duration
            self.melee_frame = 0
        elif self.current_action == "shockwave":
            self.action_timer = 40
            self.shockwave_active = False
        elif self.current_action == "spawn_drones":
            if self.phase >= 2:
                self.action_timer = 50
            else:
                self._next_action(dt)  # skip in fase 1

        # Fase 3: velocizza tutto
        if self.enraged:
            self.action_timer = int(self.action_timer * 0.7)

    def _execute_current_action(self, dt):
        if self.current_action == "approach":
            self._approach(dt)
        elif self.current_action == "melee":
            self._melee_attack(dt)
        elif self.current_action == "shockwave":
            self._shockwave_attack(dt)
        elif self.current_action == "spawn_drones":
            self._spawn_drones(dt)
        else:
            self.vel_x = 0
            self.set_anim("idle")

    def _approach(self, dt):
        """Avvicinati al player."""
        if not self.target:
            return
        dx = self.target.x - self.x
        self.facing = 1 if dx > 0 else -1
        dist = abs(dx)

        if dist > 40:
            self.vel_x = self.facing * self.move_speed
            self.set_anim("walk")
        else:
            self.vel_x = 0
            self.action_timer = 0  # passa all'azione successiva

        # Clamp nell'arena
        self.x = max(self.arena_left, min(self.x, self.arena_right - self.width))

    def _melee_attack(self, dt):
        """Attacco corpo a corpo in 2 fasi."""
        self.vel_x = 0
        progress = 1.0 - (self.action_timer / self.melee_duration)

        if progress < 0.4:
            # Wind-up
            self.set_anim("melee0")
        else:
            # Colpo
            self.set_anim("melee1")
            damage = 2 if self.phase < 3 else 3
            self.activate_hitbox(self.collision_width, 8, 20, 16, damage)

        if self.action_timer <= 2:
            self.deactivate_hitbox()

    def _shockwave_attack(self, dt):
        """Battuta a terra con onda d'urto."""
        self.vel_x = 0
        progress = 1.0 - (self.action_timer / 40)

        if progress < 0.5:
            self.set_anim("melee0")  # carica
            self.shockwave_active = False
            self.shockwave_rects.clear()
        elif not self.shockwave_active:
            self.set_anim("shockwave")
            self.shockwave_active = True
            # Crea rettangoli shockwave che si espandono dal pavimento
            base_y = int(self.y) + self.collision_height - 4
            for i in range(5):
                wave_x = int(self.x) - 20 - i * 30
                wave_x2 = int(self.x) + self.width + i * 30
                self.shockwave_rects.append(
                    pygame.Rect(wave_x, base_y, 20, 8))
                self.shockwave_rects.append(
                    pygame.Rect(wave_x2, base_y, 20, 8))

        if self.action_timer <= 2:
            self.shockwave_active = False
            self.shockwave_rects.clear()

    def _spawn_drones(self, dt):
        """Spawna droni alleati."""
        self.vel_x = 0
        self.set_anim("spawn")

        # Spawna a metà dell'azione
        if 20 < self.action_timer < 25 and self.spawn_callback:
            count = 1 if self.phase == 2 else 2
            self.spawn_callback(int(self.x), int(self.y) - 30, count)

    def take_damage(self, amount, knockback_x=0, knockback_y=0):
        """Override: il boss ha knockback ridotto."""
        result = super().take_damage(amount, knockback_x * 0.2, knockback_y * 0.3)
        if result:
            self.set_anim("hurt")
        return result

    def draw(self, surface, camera_offset=(0, 0)):
        """Disegna il boss con barra HP."""
        super().draw(surface, camera_offset)
        if self.alive and self.intro_done:
            self._draw_hp_bar(surface, camera_offset)
            if self.shockwave_active:
                self._draw_shockwaves(surface, camera_offset)

    def _draw_hp_bar(self, surface, camera_offset):
        """Barra HP del boss in alto al centro della vista."""
        bar_width = 120
        bar_height = 4
        bar_x = (surface.get_width() - bar_width) // 2
        bar_y = 8
        # Sfondo
        pygame.draw.rect(surface, (30, 28, 50), (bar_x, bar_y, bar_width, bar_height))
        # HP
        hp_ratio = self.hp / self.max_hp
        color = COLOR_NEON_ORANGE if self.phase < 3 else COLOR_RED_ALARM
        pygame.draw.rect(surface, color,
                         (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
        # Bordo
        pygame.draw.rect(surface, (245, 241, 216), (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_shockwaves(self, surface, camera_offset):
        """Disegna le onde d'urto a terra."""
        for rect in self.shockwave_rects:
            draw_rect = rect.move(camera_offset[0], camera_offset[1])
            pygame.draw.rect(surface, COLOR_NEON_ORANGE, draw_rect)
