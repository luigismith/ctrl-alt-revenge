# entities/player.py — GIG: movimento, parkour, hack, combat
import pygame
from ctrl_alt_revenge.entities.entity import Entity
from ctrl_alt_revenge.entities.components import Health, Hitbox, Hurtbox
from ctrl_alt_revenge.settings import (
    PLAYER_SPEED, PLAYER_JUMP_FORCE, PLAYER_JUMP_CUT,
    PLAYER_WALL_SLIDE_SPEED, PLAYER_WALL_JUMP_FORCE_X, PLAYER_WALL_JUMP_FORCE_Y,
    COYOTE_TIME, JUMP_BUFFER, PLAYER_HP,
    PLAYER_WIDTH, PLAYER_HEIGHT, PUNCH_DAMAGE, KICK_DAMAGE,
    COMBO_WINDOW, PARRY_WINDOW, KNOCKBACK_FORCE_X, KNOCKBACK_FORCE_Y,
    DIR_LEFT, DIR_RIGHT,
)


class Player(Entity, Health, Hitbox, Hurtbox):
    """Protagonista GIG con movimento completo, parkour, combat e hack."""

    def __init__(self, x, y):
        Entity.__init__(self, x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.init_health(PLAYER_HP)
        self.init_hitbox()
        self.init_hurtbox()

        self.collision_width = 14
        self.collision_height = 28
        # Offset per centrare la collision box nello sprite
        self.col_offset_x = (PLAYER_WIDTH - self.collision_width) // 2

        # Parkour
        self.can_double_jump = False  # sbloccato da innesto
        self.has_double_jumped = False
        self.is_wall_sliding = False
        self.wall_jump_timer = 0
        self.ledge_grabbing = False

        # Coyote time e jump buffer
        self.coyote_timer = 0
        self.jump_buffer_timer = 0

        # Accovacciamento e slide
        self.is_crouching = False
        self.is_sliding = False
        self.slide_timer = 0
        self.slide_duration = 20  # frame

        # Combat
        self.combo_count = 0
        self.combo_timer = 0
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_duration = 10  # frame per ogni colpo
        self.is_parrying = False
        self.parry_timer = 0
        self.parry_success = False

        # Hacking
        self.nearby_hackable = None
        self.is_hacking = False

        # Innesti attivi
        self.implants = {}
        self.bullet_time_active = False
        self.bullet_time_timer = 0
        self.emp_cooldown = 0
        self.thermal_vision = False

        # Heat
        self.heat = 0.0

        # Stato per animazione
        self._was_on_ground = False
        self.land_timer = 0

    def update(self, input_mgr, dt=1.0):
        """Aggiornamento completo del player."""
        self.update_iframes(dt)
        self.update_hurtbox()

        if not self.alive:
            self.set_anim("hurt")
            self.update_animation(dt)
            return

        # Timer vari
        if self.wall_jump_timer > 0:
            self.wall_jump_timer -= dt
        if self.emp_cooldown > 0:
            self.emp_cooldown -= dt
        if self.combo_timer > 0:
            self.combo_timer -= dt
        else:
            self.combo_count = 0

        # Coyote time
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
            self.has_double_jumped = False
        else:
            if self.coyote_timer > 0:
                self.coyote_timer -= dt

        # Jump buffer
        if input_mgr.is_just_pressed("jump"):
            self.jump_buffer_timer = JUMP_BUFFER
        elif self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt

        # Se in attacco, gestisci il timer
        if self.is_attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.anim_speed = 8  # restore default anim speed
                self.deactivate_hitbox()
            elif self.attack_timer < 3:
                # Allow canceling attack recovery into new attack or jump
                self.anim_speed = 8  # restore default anim speed
                if input_mgr.is_just_pressed("punch"):
                    self._do_attack("punch")
                elif input_mgr.is_just_pressed("kick"):
                    self._do_attack("kick")
                elif input_mgr.is_just_pressed("jump"):
                    self.is_attacking = False
                    self.deactivate_hitbox()
                else:
                    self.update_animation(dt)
                    return
            else:
                self.update_animation(dt)
                return  # non processa input durante attacco

        # Parry
        if self.is_parrying:
            self.parry_timer -= dt
            if self.parry_timer <= 0:
                self.is_parrying = False
            self.update_animation(dt)
            return

        # Slide
        if self.is_sliding:
            self.slide_timer -= dt
            if self.slide_timer <= 0:
                self.is_sliding = False
                old_bottom = self.y + self.collision_height
                self.collision_height = 28
                self.y = old_bottom - self.collision_height
            else:
                self.set_anim("slide")
                self.update_animation(dt)
                return

        # --- MOVIMENTO ---
        move_x = input_mgr.get_axis_x()

        # Non muovere durante wall jump
        if self.wall_jump_timer <= 0:
            if move_x != 0:
                self.vel_x = move_x * PLAYER_SPEED
                self.facing = move_x
            else:
                # Decelerazione
                self.vel_x *= 0.7
                if abs(self.vel_x) < 0.1:
                    self.vel_x = 0

        # Accovacciamento (aggiusta y per mantenere i piedi fissi)
        if input_mgr.is_held("down") and self.on_ground and not self.is_sliding:
            if not self.is_crouching:
                old_bottom = self.y + self.collision_height
                self.collision_height = 18
                self.y = old_bottom - self.collision_height
            self.is_crouching = True
            # Slide: giù + salto mentre si corre
            if input_mgr.is_just_pressed("jump") and abs(self.vel_x) > 1.5:
                old_bottom = self.y + self.collision_height
                self.is_sliding = True
                self.slide_timer = self.slide_duration
                self.vel_x = self.facing * PLAYER_SPEED * 1.8
                self.collision_height = 14
                self.y = old_bottom - self.collision_height
        else:
            if self.is_crouching:
                old_bottom = self.y + self.collision_height
                self.collision_height = 28
                self.y = old_bottom - self.collision_height
            self.is_crouching = False

        # --- SALTO ---
        can_jump = self.coyote_timer > 0 or self.on_ground
        want_jump = self.jump_buffer_timer > 0

        if want_jump and can_jump and not self.is_crouching:
            self.vel_y = PLAYER_JUMP_FORCE
            self.coyote_timer = 0
            self.jump_buffer_timer = 0
            self.on_ground = False
        elif want_jump and not can_jump:
            # Doppio salto (se sbloccato)
            if self.can_double_jump and not self.has_double_jumped and not self.is_wall_sliding:
                self.vel_y = PLAYER_JUMP_FORCE * 0.85
                self.has_double_jumped = True
                self.jump_buffer_timer = 0
            # Wall jump
            elif self.is_wall_sliding:
                if self.on_wall_right:
                    self.vel_x = -PLAYER_WALL_JUMP_FORCE_X
                    self.facing = DIR_LEFT
                else:
                    self.vel_x = PLAYER_WALL_JUMP_FORCE_X
                    self.facing = DIR_RIGHT
                self.vel_y = PLAYER_WALL_JUMP_FORCE_Y
                self.wall_jump_timer = 8
                self.is_wall_sliding = False
                self.jump_buffer_timer = 0

        # Jump cut (salto variabile)
        if input_mgr.is_just_released("jump") and self.vel_y < PLAYER_JUMP_CUT:
            self.vel_y = PLAYER_JUMP_CUT

        # Wall slide
        self.is_wall_sliding = False
        if not self.on_ground and self.vel_y > 0:
            if (self.on_wall_left and input_mgr.is_held("left")) or \
               (self.on_wall_right and input_mgr.is_held("right")):
                self.is_wall_sliding = True
                self.vel_y = min(self.vel_y, PLAYER_WALL_SLIDE_SPEED)

        # Drop through (piattaforme one-way)
        self.drop_through = input_mgr.is_held("down") and input_mgr.is_just_pressed("jump") and self.on_ground

        # --- COMBAT ---
        if input_mgr.is_just_pressed("punch"):
            self._do_attack("punch")
        elif input_mgr.is_just_pressed("kick"):
            self._do_attack("kick")

        # Parry
        if input_mgr.is_just_pressed("parry"):
            self.is_parrying = True
            self.parry_timer = PARRY_WINDOW
            self.parry_success = False
            self.set_anim("parry")

        # Landing detection
        if self.on_ground and not self._was_on_ground and self.vel_y >= 0:
            self.land_timer = 6
        if self.land_timer > 0:
            self.land_timer -= dt

        # --- ANIMAZIONE ---
        self._update_anim_state()
        self.update_animation(dt)

        self._was_on_ground = self.on_ground

    def _do_attack(self, attack_type):
        """Esegue un attacco."""
        self.is_attacking = True
        self.attack_timer = self.attack_duration
        self.anim_speed = 3  # faster attack animations

        if attack_type == "punch":
            if self.combo_timer > 0 and self.combo_count < 3:
                self.combo_count += 1
            else:
                self.combo_count = 0
            self.combo_timer = COMBO_WINDOW
            damage = PUNCH_DAMAGE
            if self.combo_count == 2:
                damage = KICK_DAMAGE  # ultimo colpo della combo fa più danno
            self.set_anim(f"punch{self.combo_count}")
            self.activate_hitbox(self.collision_width, 4, 14, 10, damage)
        else:
            self.set_anim("kick")
            self.activate_hitbox(self.collision_width, 8, 16, 8, KICK_DAMAGE)
            self.combo_count = 0
            self.combo_timer = 0

    def _update_anim_state(self):
        """Determina l'animazione corrente in base allo stato."""
        if self.is_attacking or self.is_parrying or self.is_sliding:
            return  # gestiti altrove

        if self.iframes > 0 and not self.on_ground:
            self.set_anim("hurt")
        elif self.land_timer > 0 and self.on_ground:
            self.set_anim("land")
        elif self.is_wall_sliding:
            self.set_anim("wall_slide")
        elif self.is_crouching:
            self.set_anim("crouch")
        elif not self.on_ground:
            if self.vel_y < 0:
                self.set_anim("jump")
            else:
                self.set_anim("fall")
        elif abs(self.vel_x) > 0.5:
            self.set_anim("run")
        else:
            self.set_anim("idle")

    def update_hurtbox(self):
        """Hurtbox aggiornata con offset corretto."""
        self.hurtbox_rect = pygame.Rect(
            int(self.x) + 2, int(self.y) + 2,
            self.collision_width - 4, self.collision_height - 4)

    def draw(self, surface, camera_offset=(0, 0)):
        """Disegna il player con effetto lampeggio durante i-frames."""
        if not self.active:
            return
        # Lampeggio invincibilità
        if self.iframes > 0 and int(self.iframes) % 4 < 2:
            return

        if self.image:
            sprite_w = self.image.get_width()
            sprite_h = self.image.get_height()
            # Centrato sul fondo della collision box (come Entity.draw)
            draw_x = int(self.x) + self.collision_width // 2 - sprite_w // 2 + camera_offset[0]
            draw_y = int(self.y) + self.collision_height - sprite_h + camera_offset[1]
            surface.blit(self.image, (draw_x, draw_y))
