# core/sprite_generator.py — Genera sprite pixel-art per protagonista e nemici
# Ogni sprite è disegnato pixel per pixel sulla palette cyberpunk
import pygame
import math
from ctrl_alt_revenge.settings import (
    COLOR_SKIN, COLOR_SKIN_SHADOW, COLOR_HAIR_GRAY, COLOR_JACKET_BROWN,
    COLOR_JACKET_SHADOW, COLOR_PANTS_DARK, COLOR_BOOTS_BROWN, COLOR_BLACK,
    COLOR_NEON_BLUE, COLOR_NEON_PURPLE, COLOR_NEON_ORANGE, COLOR_RED_ALARM,
    COLOR_WHITE_UI, COLOR_DARK_GRAY, COLOR_MID_GRAY, COLOR_GREEN_HACK,
    COLOR_YELLOW, COLOR_BG_NIGHT,
    PLAYER_WIDTH, PLAYER_HEIGHT, THUG_WIDTH, THUG_HEIGHT,
    DRONE_WIDTH, DRONE_HEIGHT, WARDEN_WIDTH, WARDEN_HEIGHT,
)

# Colori aggiuntivi per dettagli
COLOR_EYE = (200, 220, 255)
COLOR_CYBER_ARM = (80, 90, 110)
COLOR_CYBER_GLOW = COLOR_NEON_BLUE
COLOR_CYBER_GLOW_DIM = (0, 150, 180)
COLOR_THUG_SHIRT = (60, 20, 20)
COLOR_THUG_SKIN = (190, 150, 110)
COLOR_THUG_BANDANA = COLOR_RED_ALARM
COLOR_DRONE_BODY = (70, 75, 90)
COLOR_DRONE_LIGHT = COLOR_RED_ALARM
COLOR_WARDEN_ARMOR = (40, 45, 60)
COLOR_WARDEN_VISOR = COLOR_RED_ALARM
COLOR_WARDEN_TRIM = COLOR_NEON_ORANGE
COLOR_SKIN_HIGHLIGHT = (220, 180, 140)
COLOR_HAIR_GRAY_LIGHT = (175, 170, 165)
COLOR_BOOTS_SOLE = (60, 40, 20)
COLOR_BRASS = (200, 180, 80)


def _set_pixel(surf, x, y, color):
    """Imposta un pixel, controllando i bordi."""
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)


def _draw_rect(surf, x, y, w, h, color):
    """Rettangolo pieno."""
    for py in range(y, y + h):
        for px in range(x, x + w):
            _set_pixel(surf, px, py, color)


def _mirror_h(surf):
    """Specchia orizzontalmente."""
    return pygame.transform.flip(surf, True, False)


# ============================================================
# PROTAGONISTA — GIG
# 24x32 pixel, uomo maturo, barba grigia, giacca marrone,
# braccio cyber sinistro con glow blu
# ============================================================

def _draw_gig_base(surf, facing_right=True):
    """Disegna il frame base di GIG (in piedi, rivolto a destra) a 24x32."""
    W, H = PLAYER_WIDTH, PLAYER_HEIGHT

    # --- Stivali (riga 27-31) ---
    _draw_rect(surf, 4, 27, 5, 5, COLOR_BOOTS_BROWN)   # piede sinistro
    _draw_rect(surf, 13, 27, 5, 5, COLOR_BOOTS_BROWN)   # piede destro
    # Suola
    _draw_rect(surf, 4, 31, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13, 31, 5, 1, COLOR_BOOTS_SOLE)
    # Lacci (alternating dark pixels)
    _set_pixel(surf, 5, 27, COLOR_BLACK)
    _set_pixel(surf, 7, 27, COLOR_BLACK)
    _set_pixel(surf, 6, 28, COLOR_BLACK)
    _set_pixel(surf, 14, 27, COLOR_BLACK)
    _set_pixel(surf, 16, 27, COLOR_BLACK)
    _set_pixel(surf, 15, 28, COLOR_BLACK)

    # --- Pantaloni (riga 20-26) ---
    _draw_rect(surf, 5, 20, 4, 7, COLOR_PANTS_DARK)     # gamba sinistra
    _draw_rect(surf, 13, 20, 4, 7, COLOR_PANTS_DARK)    # gamba destra
    # Cintura
    _draw_rect(surf, 5, 19, 12, 1, COLOR_BLACK)
    _set_pixel(surf, 10, 19, COLOR_NEON_ORANGE)  # fibbia
    _set_pixel(surf, 11, 19, COLOR_NEON_ORANGE)

    # --- Torso / giacca (riga 9-18) ---
    _draw_rect(surf, 5, 9, 12, 10, COLOR_JACKET_BROWN)
    # Ombra giacca lato sinistro
    _draw_rect(surf, 5, 9, 3, 10, COLOR_JACKET_SHADOW)
    # Colletto
    _draw_rect(surf, 7, 8, 8, 1, COLOR_JACKET_BROWN)
    _set_pixel(surf, 6, 8, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 15, 8, COLOR_JACKET_SHADOW)
    # T-shirt sotto (visible V-neck)
    _draw_rect(surf, 8, 9, 6, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 10, 12, COLOR_DARK_GRAY)
    _set_pixel(surf, 11, 12, COLOR_DARK_GRAY)
    # Pocket (darker rect 2x3)
    _draw_rect(surf, 13, 13, 2, 3, COLOR_JACKET_SHADOW)

    # --- Braccio destro (umano) ---
    _draw_rect(surf, 17, 10, 3, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17, 17, 3, 2, COLOR_SKIN)     # mano
    _set_pixel(surf, 17, 17, COLOR_SKIN_SHADOW)     # shadow on hand

    # --- Braccio sinistro (cyber) ---
    _draw_rect(surf, 2, 10, 3, 7, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 17, 3, 2, COLOR_CYBER_ARM)
    # 4 glow segments alternating brightness
    _set_pixel(surf, 2, 11, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 12, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 2, 13, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 14, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 2, 15, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 16, COLOR_CYBER_GLOW_DIM)

    # --- Testa (riga 0-8) ---
    # Skin base
    _draw_rect(surf, 7, 2, 8, 6, COLOR_SKIN)
    # Highlight on forehead
    _set_pixel(surf, 8, 2, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 9, 2, COLOR_SKIN_HIGHLIGHT)
    # Shadow on jaw
    _draw_rect(surf, 7, 6, 8, 1, COLOR_SKIN_SHADOW)

    # Capelli con 2 shades of gray + ponytail
    _draw_rect(surf, 7, 0, 8, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8, 0, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 10, 0, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 12, 0, COLOR_HAIR_GRAY_LIGHT)
    # Ponytail (3-4 pixels trailing)
    _set_pixel(surf, 15, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17, 3, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17, 4, COLOR_HAIR_GRAY_LIGHT)

    # Barba
    _draw_rect(surf, 7, 6, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 8, 7, 4, 1, COLOR_HAIR_GRAY_LIGHT)

    # Occhi
    _set_pixel(surf, 9, 4, COLOR_EYE)     # right eye white
    _set_pixel(surf, 10, 4, COLOR_BLACK)   # right pupil
    _set_pixel(surf, 12, 4, COLOR_EYE)    # left eye white
    _set_pixel(surf, 13, 4, COLOR_BLACK)   # left pupil

    # Cybernetic eye: 2x2 bright blue with 1px glow around it
    _draw_rect(surf, 8, 3, 2, 2, COLOR_NEON_BLUE)
    _set_pixel(surf, 7, 3, (0, 150, 200, 150))    # glow
    _set_pixel(surf, 7, 4, (0, 150, 200, 150))
    _set_pixel(surf, 10, 3, (0, 150, 200, 100))
    _set_pixel(surf, 8, 2, (0, 150, 200, 80))
    _set_pixel(surf, 9, 5, (0, 150, 200, 80))

    # Sopracciglia
    _set_pixel(surf, 9, 3, COLOR_BLACK)
    _set_pixel(surf, 12, 3, COLOR_BLACK)


def generate_gig_sprites():
    """Genera tutti i frame animazione di GIG.
    Restituisce un dizionario {nome_animazione: [frame1, frame2, ...]}
    Ogni frame è disponibile in entrambe le direzioni.
    """
    sprites = {}

    # --- IDLE (2 frame, leggero breathing) ---
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
        _draw_gig_base(surf)
        if f == 1:
            # Breathing: slight shoulder raise
            _set_pixel(surf, 8, 8, COLOR_JACKET_BROWN)
            _set_pixel(surf, 13, 8, COLOR_JACKET_BROWN)
            # Subtle cyber glow pulse
            _set_pixel(surf, 2, 12, COLOR_CYBER_GLOW)
            _set_pixel(surf, 3, 13, COLOR_CYBER_GLOW)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frame with clear leg stride and arm pump) ---
    run_frames = []
    leg_offsets = [(0, 0, 0, 0), (2, -1, -2, 1), (0, 0, 0, 0), (-2, 1, 2, -1)]
    for f in range(4):
        surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
        lox1, loy1, lox2, loy2 = leg_offsets[f]
        bob = -1 if f in (1, 3) else 0

        # Stivali with stride offset
        _draw_rect(surf, 4 + lox1, 27 + loy1, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 13 + lox2, 27 + loy2, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 4 + lox1, 30 + loy1, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 13 + lox2, 30 + loy2, 5, 1, COLOR_BOOTS_SOLE)
        # Laces
        _set_pixel(surf, 5 + lox1, 27 + loy1, COLOR_BLACK)
        _set_pixel(surf, 7 + lox1, 27 + loy1, COLOR_BLACK)
        _set_pixel(surf, 14 + lox2, 27 + loy2, COLOR_BLACK)
        _set_pixel(surf, 16 + lox2, 27 + loy2, COLOR_BLACK)

        # Gambe with stride
        _draw_rect(surf, 5 + lox1, 20, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 13 + lox2, 20, 4, 7, COLOR_PANTS_DARK)
        # Cintura
        _draw_rect(surf, 5, 19 + bob, 12, 1, COLOR_BLACK)
        _set_pixel(surf, 10, 19 + bob, COLOR_NEON_ORANGE)
        _set_pixel(surf, 11, 19 + bob, COLOR_NEON_ORANGE)

        # Torso con bob
        _draw_rect(surf, 5, 9 + bob, 12, 10, COLOR_JACKET_BROWN)
        _draw_rect(surf, 5, 9 + bob, 3, 10, COLOR_JACKET_SHADOW)
        _draw_rect(surf, 7, 8 + bob, 8, 1, COLOR_JACKET_BROWN)
        _draw_rect(surf, 8, 9 + bob, 6, 3, COLOR_DARK_GRAY)
        # Pocket
        _draw_rect(surf, 13, 13 + bob, 2, 3, COLOR_JACKET_SHADOW)

        # Arm pump - human arm
        arm_swing = 2 if f in (0, 2) else -2
        _draw_rect(surf, 17, 10 + bob, 3, 7, COLOR_JACKET_BROWN)
        _draw_rect(surf, 17, 17 + bob + arm_swing, 3, 2, COLOR_SKIN)
        # Cyber arm pumps opposite
        _draw_rect(surf, 2, 10 + bob, 3, 7, COLOR_CYBER_ARM)
        _draw_rect(surf, 2, 17 + bob - arm_swing, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 2, 11 + bob, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3, 13 + bob, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2, 15 + bob, COLOR_CYBER_GLOW)

        # Testa
        _draw_rect(surf, 7, 2 + bob, 8, 6, COLOR_SKIN)
        _set_pixel(surf, 8, 2 + bob, COLOR_SKIN_HIGHLIGHT)
        _set_pixel(surf, 9, 2 + bob, COLOR_SKIN_HIGHLIGHT)
        _draw_rect(surf, 7, 6 + bob, 8, 1, COLOR_SKIN_SHADOW)
        _draw_rect(surf, 7, 0 + bob, 8, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 8, 0 + bob, COLOR_HAIR_GRAY_LIGHT)
        _set_pixel(surf, 10, 0 + bob, COLOR_HAIR_GRAY_LIGHT)
        # Ponytail bounces
        pt_bob = 1 if f in (1, 3) else 0
        _set_pixel(surf, 15, 1 + bob, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16, 2 + bob + pt_bob, COLOR_HAIR_GRAY)
        _set_pixel(surf, 17, 3 + bob + pt_bob, COLOR_HAIR_GRAY)
        # Barba
        _draw_rect(surf, 7, 6 + bob, 6, 2, COLOR_HAIR_GRAY)
        # Eyes
        _set_pixel(surf, 9, 4 + bob, COLOR_EYE)
        _set_pixel(surf, 12, 4 + bob, COLOR_EYE)
        _set_pixel(surf, 10, 4 + bob, COLOR_BLACK)
        _set_pixel(surf, 13, 4 + bob, COLOR_BLACK)
        # Cyber eye
        _draw_rect(surf, 8, 3 + bob, 2, 2, COLOR_NEON_BLUE)

        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (1 frame, gambe raccolte) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Stivali more tucked
    _draw_rect(surf, 4, 25, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 13, 25, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4, 28, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13, 28, 5, 1, COLOR_BOOTS_SOLE)
    # Legs tucked
    _draw_rect(surf, 5, 21, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 13, 21, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 5, 20, 12, 1, COLOR_BLACK)
    # Torso
    _draw_rect(surf, 5, 9, 12, 11, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5, 9, 3, 11, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8, 9, 6, 3, COLOR_DARK_GRAY)
    _draw_rect(surf, 13, 13, 2, 3, COLOR_JACKET_SHADOW)
    # Arms raised
    _draw_rect(surf, 17, 7, 3, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17, 14, 3, 2, COLOR_SKIN)
    _draw_rect(surf, 2, 7, 3, 7, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 14, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 2, 8, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 10, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 2, 12, COLOR_CYBER_GLOW)
    # Testa
    _draw_rect(surf, 7, 2, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 8, 2, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 7, 0, 8, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8, 0, COLOR_HAIR_GRAY_LIGHT)
    _draw_rect(surf, 7, 6, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 9, 4, COLOR_EYE)
    _set_pixel(surf, 12, 4, COLOR_EYE)
    _draw_rect(surf, 8, 3, 2, 2, COLOR_NEON_BLUE)
    # Ponytail flows up
    _set_pixel(surf, 15, 0, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16, 1, COLOR_HAIR_GRAY)
    sprites["jump_right"] = [surf]
    sprites["jump_left"] = [_mirror_h(surf)]

    # --- FALL (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_rect(surf, 4, 27, 5, 5, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 13, 27, 5, 5, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4, 31, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13, 31, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 5, 20, 4, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 13, 20, 4, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 5, 19, 12, 1, COLOR_BLACK)
    _draw_rect(surf, 5, 9, 12, 10, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5, 9, 3, 10, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8, 9, 6, 3, COLOR_DARK_GRAY)
    # Arms spread
    _draw_rect(surf, 18, 10, 3, 6, COLOR_JACKET_BROWN)
    _draw_rect(surf, 18, 16, 3, 2, COLOR_SKIN)
    _draw_rect(surf, 1, 10, 3, 6, COLOR_CYBER_ARM)
    _draw_rect(surf, 1, 16, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 1, 11, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 13, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 1, 15, COLOR_CYBER_GLOW)
    # Testa
    _draw_rect(surf, 7, 2, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 8, 2, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 7, 0, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 7, 6, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 9, 4, COLOR_EYE)
    _set_pixel(surf, 12, 4, COLOR_EYE)
    _draw_rect(surf, 8, 3, 2, 2, COLOR_NEON_BLUE)
    # Ponytail flows up
    _set_pixel(surf, 15, 0, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16, 0, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 17, 1, COLOR_HAIR_GRAY)
    sprites["fall_right"] = [surf]
    sprites["fall_left"] = [_mirror_h(surf)]

    # --- WALL SLIDE (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Right arm reaching up and grabbing wall
    _draw_rect(surf, 18, 5, 3, 10, COLOR_JACKET_BROWN)
    _draw_rect(surf, 18, 5, 3, 2, COLOR_SKIN)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Everything shifted down and compressed
    _draw_rect(surf, 4, 28, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 13, 28, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4, 31, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13, 31, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 5, 24, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 13, 24, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 5, 23, 12, 1, COLOR_BLACK)
    _draw_rect(surf, 5, 16, 12, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5, 16, 3, 7, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8, 16, 6, 3, COLOR_DARK_GRAY)
    # Arms
    _draw_rect(surf, 17, 17, 3, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17, 22, 3, 2, COLOR_SKIN)
    _draw_rect(surf, 2, 17, 3, 5, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 22, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 2, 18, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 20, COLOR_CYBER_GLOW_DIM)
    # Head
    _draw_rect(surf, 7, 10, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 8, 10, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 7, 8, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 7, 14, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 9, 12, COLOR_EYE)
    _set_pixel(surf, 12, 12, COLOR_EYE)
    _draw_rect(surf, 8, 11, 2, 2, COLOR_NEON_BLUE)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH + 4, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Body nearly horizontal, feet forward
    _draw_rect(surf, 0, 23, 6, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 0, 26, 6, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 0, 20, 6, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 5, 18, 14, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5, 18, 3, 5, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8, 18, 6, 3, COLOR_DARK_GRAY)
    # Head at end
    _draw_rect(surf, 18, 16, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 19, 16, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 18, 14, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 18, 20, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 20, 18, COLOR_EYE)
    _set_pixel(surf, 23, 18, COLOR_EYE)
    _draw_rect(surf, 19, 17, 2, 2, COLOR_NEON_BLUE)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 frame combo) with motion trail ---
    for combo_idx in range(3):
        surf = pygame.Surface((PLAYER_WIDTH + 8, PLAYER_HEIGHT), pygame.SRCALPHA)
        _draw_gig_base(surf)
        # Fist extension with 2px motion trail
        arm_extend = 4 + combo_idx * 3
        arm_y = 13 - combo_idx
        if combo_idx < 2:
            # Punch with right arm
            _draw_rect(surf, 19, arm_y, arm_extend, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, 19 + arm_extend - 2, arm_y, 3, 3, COLOR_SKIN)
            # Motion trail (2px swing color)
            trail_color = (255, 200, 100, 120)
            _set_pixel(surf, 19 + arm_extend + 1, arm_y, trail_color)
            _set_pixel(surf, 19 + arm_extend + 2, arm_y + 1, trail_color)
            # Impact flash
            _set_pixel(surf, 19 + arm_extend + 1, arm_y + 1, COLOR_NEON_ORANGE)
            _set_pixel(surf, 19 + arm_extend + 1, arm_y + 2, COLOR_YELLOW)
        else:
            # Final combo kick
            _draw_rect(surf, 18, 23, arm_extend + 3, 3, COLOR_PANTS_DARK)
            _draw_rect(surf, 18 + arm_extend + 1, 22, 3, 4, COLOR_BOOTS_BROWN)
            trail_color = (255, 200, 100, 120)
            _set_pixel(surf, 18 + arm_extend + 4, 23, trail_color)
            _set_pixel(surf, 18 + arm_extend + 5, 24, trail_color)
            _set_pixel(surf, 18 + arm_extend + 4, 24, COLOR_NEON_ORANGE)
        sprites[f"punch{combo_idx}_right"] = [surf]
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(surf)]

    # --- KICK (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH + 8, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    _draw_rect(surf, 18, 21, 8, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 25, 20, 3, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 28, 22, COLOR_NEON_ORANGE)
    _set_pixel(surf, 29, 21, COLOR_YELLOW)
    sprites["kick_right"] = [surf]
    sprites["kick_left"] = [_mirror_h(surf)]

    # --- PARRY (1 frame, guardia alta) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Arms crossed in front
    _draw_rect(surf, 6, 8, 10, 3, COLOR_CYBER_ARM)
    _draw_rect(surf, 6, 8, 10, 1, COLOR_CYBER_GLOW)
    # Energy shield line
    for i in range(10):
        _set_pixel(surf, 5, 6 + i, COLOR_NEON_BLUE)
        _set_pixel(surf, 4, 7 + i, (0, 200, 255, 80))
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame, knockback) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Red flash on torso
    _draw_rect(surf, 5, 9, 12, 10, COLOR_RED_ALARM)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame, cyber arm extended with hologram) ---
    surf = pygame.Surface((PLAYER_WIDTH + 10, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Cyber arm extended
    _draw_rect(surf, 0, 10, 3, 7, COLOR_CYBER_ARM)
    # Hologram (green checkerboard)
    for hy in range(5):
        for hx in range(5):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx + PLAYER_WIDTH, 9 + hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx + PLAYER_WIDTH, 9 + hy, (0, 180, 60, 150))
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ============================================================
# THUG — Scagnozzo umano
# 22x32, stockier build, bandana rossa, maglietta scura
# ============================================================

def generate_thug_sprites():
    sprites = {}

    def _draw_thug_base(surf, alert=False):
        W, H = THUG_WIDTH, THUG_HEIGHT

        # Stivali (riga 27-31)
        _draw_rect(surf, 4, 27, 5, 5, COLOR_BLACK)
        _draw_rect(surf, 13, 27, 5, 5, COLOR_BLACK)

        # Pantaloni (riga 20-26)
        _draw_rect(surf, 5, 20, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 13, 20, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 5, 19, 12, 1, COLOR_BLACK)

        # Torso - stockier, wider shoulders
        body_color = COLOR_RED_ALARM if alert else COLOR_THUG_SHIRT
        _draw_rect(surf, 4, 9, 14, 10, body_color)
        _draw_rect(surf, 7, 9, 8, 3, COLOR_DARK_GRAY)
        # Skull marking (simple X cross in lighter color)
        marking_color = (100, 50, 50)
        _set_pixel(surf, 9, 13, marking_color)
        _set_pixel(surf, 12, 13, marking_color)
        _set_pixel(surf, 10, 14, marking_color)
        _set_pixel(surf, 11, 14, marking_color)
        _set_pixel(surf, 9, 15, marking_color)
        _set_pixel(surf, 12, 15, marking_color)

        # Braccia - wider shoulders
        _draw_rect(surf, 18, 10, 3, 7, body_color)
        _draw_rect(surf, 18, 17, 3, 2, COLOR_THUG_SKIN)
        # Brass knuckle on right hand
        _set_pixel(surf, 18, 17, COLOR_BRASS)
        _set_pixel(surf, 20, 17, COLOR_BRASS)
        _draw_rect(surf, 1, 10, 3, 7, body_color)
        _draw_rect(surf, 1, 17, 3, 2, COLOR_THUG_SKIN)
        # Brass knuckle on left hand
        _set_pixel(surf, 1, 17, COLOR_BRASS)
        _set_pixel(surf, 3, 17, COLOR_BRASS)

        # Testa
        _draw_rect(surf, 6, 2, 10, 7, COLOR_THUG_SKIN)
        # Bandana rossa with 2-pixel tail
        _draw_rect(surf, 6, 1, 10, 2, COLOR_THUG_BANDANA)
        _set_pixel(surf, 16, 2, COLOR_THUG_BANDANA)  # tail pixel 1
        _set_pixel(surf, 17, 3, COLOR_THUG_BANDANA)  # tail pixel 2
        # Occhi minacciosi
        _set_pixel(surf, 9, 4, COLOR_BLACK)
        _set_pixel(surf, 12, 4, COLOR_BLACK)
        # Thick brow
        _draw_rect(surf, 8, 3, 3, 1, COLOR_BLACK)
        _draw_rect(surf, 11, 3, 3, 1, COLOR_BLACK)
        # Mouth/sneer
        _set_pixel(surf, 9, 7, COLOR_BLACK)
        _set_pixel(surf, 10, 7, COLOR_BLACK)
        _set_pixel(surf, 11, 7, COLOR_BLACK)

    # IDLE (2 frame)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
        _draw_thug_base(surf)
        if f == 1:
            _set_pixel(surf, 8, 8, COLOR_THUG_SHIRT)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    leg_off = [(0, 0), (2, -2), (0, 0), (-2, 2)]
    for f in range(4):
        surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
        _draw_thug_base(surf)
        lo1, lo2 = leg_off[f]
        # Override feet with offset
        _draw_rect(surf, 4 + lo1, 27, 5, 5, COLOR_BLACK)
        _draw_rect(surf, 13 + lo2, 27, 5, 5, COLOR_BLACK)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK
    surf = pygame.Surface((THUG_WIDTH + 8, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 20, 13, 6, 3, COLOR_THUG_SHIRT)
    _draw_rect(surf, 25, 12, 3, 4, COLOR_THUG_SKIN)
    # Brass knuckle flash
    _set_pixel(surf, 25, 12, COLOR_BRASS)
    _set_pixel(surf, 27, 12, COLOR_BRASS)
    _set_pixel(surf, 28, 13, COLOR_RED_ALARM)
    sprites["attack_right"] = [surf]
    sprites["attack_left"] = [_mirror_h(surf)]

    # ALERT
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf, alert=True)
    # Exclamation mark above head
    _draw_rect(surf, 10, 0, 2, 1, COLOR_RED_ALARM)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 4, 9, 14, 10, (255, 100, 100, 180))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (2 frame)
    death_frames = []
    # Frame 1: stagger
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 4, 9, 14, 10, (255, 100, 100, 100))
    death_frames.append(surf)
    # Frame 2: on the ground
    surf = pygame.Surface((THUG_WIDTH + 10, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_rect(surf, 0, 25, 26, 5, COLOR_THUG_SHIRT)
    _draw_rect(surf, 22, 24, 8, 6, COLOR_THUG_SKIN)
    _draw_rect(surf, 22, 23, 8, 2, COLOR_THUG_BANDANA)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ============================================================
# DRONE — Drone volante con laser
# 24x14, sleeker profile, wider propellers, pulsing sensor
# ============================================================

def generate_drone_sprites():
    sprites = {}

    def _draw_drone_base(surf, propeller_frame=0, eye_bright=True):
        w, h = DRONE_WIDTH, DRONE_HEIGHT
        # Corpo centrale - sleeker
        _draw_rect(surf, 6, 5, 12, 6, COLOR_DRONE_BODY)
        _draw_rect(surf, 7, 4, 10, 1, COLOR_DRONE_BODY)
        _draw_rect(surf, 7, 11, 10, 1, COLOR_DRONE_BODY)
        # Nose cone
        _set_pixel(surf, 5, 6, COLOR_DRONE_BODY)
        _set_pixel(surf, 5, 7, COLOR_DRONE_BODY)
        _set_pixel(surf, 18, 6, COLOR_DRONE_BODY)
        _set_pixel(surf, 18, 7, COLOR_DRONE_BODY)

        # Pannello ventrale
        _draw_rect(surf, 8, 9, 8, 2, COLOR_MID_GRAY)

        # Thruster glow (orange) under body
        _set_pixel(surf, 9, 12, COLOR_NEON_ORANGE)
        _set_pixel(surf, 10, 13, (255, 150, 50, 150))
        _set_pixel(surf, 14, 12, COLOR_NEON_ORANGE)
        _set_pixel(surf, 13, 13, (255, 150, 50, 150))

        # Pulsing sensor eye
        if eye_bright:
            eye_color = COLOR_DRONE_LIGHT
            eye_dim = (255, 100, 100)
        else:
            eye_color = (180, 30, 50)
            eye_dim = (120, 20, 30)
        _draw_rect(surf, 10, 6, 3, 2, eye_color)
        _set_pixel(surf, 9, 6, eye_dim)
        _set_pixel(surf, 13, 6, eye_dim)

        # Wider propeller blur (6px wide)
        if propeller_frame == 0:
            _draw_rect(surf, 0, 2, 6, 1, (160, 165, 180, 120))
            _draw_rect(surf, 18, 2, 6, 1, (160, 165, 180, 120))
        else:
            _draw_rect(surf, 1, 2, 4, 1, (160, 165, 180, 100))
            _draw_rect(surf, 19, 2, 4, 1, (160, 165, 180, 100))
        # Supporto eliche
        _set_pixel(surf, 3, 3, COLOR_DARK_GRAY)
        _set_pixel(surf, 3, 4, COLOR_DARK_GRAY)
        _set_pixel(surf, 20, 3, COLOR_DARK_GRAY)
        _set_pixel(surf, 20, 4, COLOR_DARK_GRAY)
        # Antenne
        _set_pixel(surf, 5, 1, COLOR_NEON_BLUE)
        _set_pixel(surf, 18, 1, COLOR_NEON_BLUE)

    # FLY (2 frame per propellers + pulsing eye alternation)
    fly_frames = []
    for f in range(2):
        surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
        _draw_drone_base(surf, f, eye_bright=(f == 0))
        fly_frames.append(surf)
    sprites["fly_right"] = fly_frames
    sprites["fly_left"] = [_mirror_h(f) for f in fly_frames]

    # SHOOT (1 frame, con laser)
    surf = pygame.Surface((DRONE_WIDTH + 8, DRONE_HEIGHT + 6), pygame.SRCALPHA)
    _draw_drone_base(surf, 0)
    for i in range(8):
        _set_pixel(surf, 12, DRONE_HEIGHT + i, COLOR_RED_ALARM)
        _set_pixel(surf, 11, DRONE_HEIGHT + i, (255, 46, 77, 100))
        _set_pixel(surf, 13, DRONE_HEIGHT + i, (255, 46, 77, 100))
    sprites["shoot_right"] = [surf]
    sprites["shoot_left"] = [_mirror_h(surf)]

    # HACKED (ally, green glow)
    surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
    _draw_drone_base(surf, 0)
    _draw_rect(surf, 10, 6, 3, 2, COLOR_GREEN_HACK)
    _set_pixel(surf, 9, 6, (0, 200, 80))
    _set_pixel(surf, 13, 6, (0, 200, 80))
    sprites["hacked_right"] = [surf]
    sprites["hacked_left"] = [_mirror_h(surf)]

    # STUNNED (EMP)
    surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, eye_bright=False)
    for i in range(3):
        _set_pixel(surf, 6 + i * 5, 1, COLOR_YELLOW)
        _set_pixel(surf, 7 + i * 5, 0, COLOR_YELLOW)
    sprites["stunned_right"] = [surf]
    sprites["stunned_left"] = [_mirror_h(surf)]

    # DEATH (explosion, 3 frame)
    death_frames = []
    for f in range(3):
        surf = pygame.Surface((DRONE_WIDTH + 4, DRONE_HEIGHT + 4), pygame.SRCALPHA)
        radius = 4 + f * 3
        cx, cy = DRONE_WIDTH // 2, DRONE_HEIGHT // 2
        colors = [COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_YELLOW]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    _set_pixel(surf, cx + dx + 2, cy + dy + 2, colors[f])
        if f > 0:
            for i in range(4):
                fx = cx + int(math.cos(i * 1.5 + f) * (radius + 2))
                fy = cy + int(math.sin(i * 1.5 + f) * (radius + 2))
                _set_pixel(surf, fx + 2, fy + 2, COLOR_DRONE_BODY)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames  # explosion symmetric

    return sprites


# ============================================================
# WARDEN — Boss livello 1
# 40x48, massive armor, shoulder pads, phase system
# ============================================================

def generate_warden_sprites():
    sprites = {}

    def _draw_warden_base(surf, phase=0):
        w, h = WARDEN_WIDTH, WARDEN_HEIGHT

        # Stivali pesanti (riga 41-47)
        _draw_rect(surf, 6, 41, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 24, 41, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 6, 47, 10, 1, COLOR_BLACK)
        _draw_rect(surf, 24, 47, 10, 1, COLOR_BLACK)
        # Trim sugli stivali
        _draw_rect(surf, 6, 41, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24, 41, 10, 1, COLOR_WARDEN_TRIM)

        # Gambali (riga 29-40)
        _draw_rect(surf, 8, 29, 8, 12, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 24, 29, 8, 12, COLOR_WARDEN_ARMOR)
        # Ginocchiere
        _draw_rect(surf, 8, 34, 8, 2, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24, 34, 8, 2, COLOR_WARDEN_TRIM)
        # Armor seam lines on legs
        _set_pixel(surf, 12, 30, COLOR_BLACK)
        _set_pixel(surf, 12, 33, COLOR_BLACK)
        _set_pixel(surf, 28, 30, COLOR_BLACK)
        _set_pixel(surf, 28, 33, COLOR_BLACK)

        # Cintura tech
        _draw_rect(surf, 7, 27, 26, 2, COLOR_DARK_GRAY)
        _draw_rect(surf, 18, 27, 4, 2, COLOR_NEON_ORANGE)

        # Torso corazzato (riga 12-26)
        _draw_rect(surf, 7, 12, 26, 15, COLOR_WARDEN_ARMOR)
        # Piastra pettorale
        _draw_rect(surf, 9, 13, 22, 10, (50, 55, 70))
        # Seam lines on torso
        _set_pixel(surf, 9, 16, COLOR_BLACK)
        _set_pixel(surf, 30, 16, COLOR_BLACK)
        _set_pixel(surf, 9, 20, COLOR_BLACK)
        _set_pixel(surf, 30, 20, COLOR_BLACK)
        # Linee trim
        _draw_rect(surf, 9, 13, 22, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 9, 22, 22, 1, COLOR_WARDEN_TRIM)

        # Core luminoso: 4x4 with 1px gradient ring
        core_colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_RED_ALARM]
        core_col = core_colors[min(phase, 2)]
        # Gradient ring (dimmer version)
        dim_core = tuple(max(0, c - 80) for c in core_col[:3])
        _draw_rect(surf, 17, 16, 6, 6, dim_core)
        # Inner core 4x4
        _draw_rect(surf, 18, 17, 4, 4, core_col)

        # Shoulder pads extending 2px past body
        _draw_rect(surf, 2, 10, 8, 5, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 30, 10, 8, 5, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 2, 10, 8, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 30, 10, 8, 1, COLOR_WARDEN_TRIM)
        # Shoulder seam
        _set_pixel(surf, 6, 12, COLOR_BLACK)
        _set_pixel(surf, 34, 12, COLOR_BLACK)

        # Braccia
        _draw_rect(surf, 3, 15, 4, 12, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 33, 15, 4, 12, COLOR_WARDEN_ARMOR)
        # Guanti
        _draw_rect(surf, 3, 27, 4, 3, COLOR_DARK_GRAY)
        _draw_rect(surf, 33, 27, 4, 3, COLOR_DARK_GRAY)
        # Glow sui guanti
        _set_pixel(surf, 4, 28, core_col)
        _set_pixel(surf, 34, 28, core_col)

        # Testa / elmo (riga 0-11)
        _draw_rect(surf, 11, 1, 18, 11, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 12, 0, 16, 1, COLOR_WARDEN_ARMOR)
        # Visiera: horizontal scanning line brightest in center
        _draw_rect(surf, 12, 5, 16, 3, COLOR_WARDEN_VISOR)
        # Scanning line - brighter in center
        _set_pixel(surf, 14, 6, (200, 80, 80))
        _set_pixel(surf, 16, 6, (220, 100, 100))
        _draw_rect(surf, 18, 6, 4, 1, (255, 180, 180))  # center brightest
        _set_pixel(surf, 22, 6, (220, 100, 100))
        _set_pixel(surf, 24, 6, (200, 80, 80))
        # Trim elmo
        _draw_rect(surf, 11, 1, 18, 1, COLOR_WARDEN_TRIM)
        # Antenna
        _set_pixel(surf, 19, 0, COLOR_RED_ALARM)
        _set_pixel(surf, 20, 0, COLOR_RED_ALARM)

    # IDLE (2 frame)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        if f == 1:
            # Core pulse brighter
            _draw_rect(surf, 18, 17, 4, 4, (0, 240, 255))
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    for f in range(4):
        surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        off = [0, 2, 0, -2][f]
        # Clear feet area and redraw with offset
        _draw_rect(surf, 6, 41, 10, 7, (0, 0, 0, 0))
        _draw_rect(surf, 24, 41, 10, 7, (0, 0, 0, 0))
        _draw_rect(surf, 6 + off, 41, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 24 - off, 41, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 6 + off, 41, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24 - off, 41, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 6 + off, 47, 10, 1, COLOR_BLACK)
        _draw_rect(surf, 24 - off, 47, 10, 1, COLOR_BLACK)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # MELEE ATTACK (2 frame)
    for f in range(2):
        surf = pygame.Surface((WARDEN_WIDTH + 14, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        arm_ext = 8 + f * 5
        _draw_rect(surf, WARDEN_WIDTH - 2, 17, arm_ext, 4, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, WARDEN_WIDTH - 2 + arm_ext - 3, 16, 6, 6, COLOR_NEON_ORANGE)
        _draw_rect(surf, WARDEN_WIDTH - 2 + arm_ext - 2, 17, 4, 4, COLOR_YELLOW)
        sprites[f"melee{f}_right"] = [surf]
        sprites[f"melee{f}_left"] = [_mirror_h(surf)]

    # SHOCKWAVE (1 frame)
    surf = pygame.Surface((WARDEN_WIDTH + 10, WARDEN_HEIGHT + 6), pygame.SRCALPHA)
    _draw_warden_base(surf, 1)
    for i in range(5):
        wave_w = (i + 1) * 7
        alpha = 255 - i * 45
        for wx in range(-wave_w, wave_w):
            _set_pixel(surf, WARDEN_WIDTH // 2 + wx + 5,
                       WARDEN_HEIGHT + i, (*COLOR_NEON_ORANGE[:3], max(0, alpha)))
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame, arms raised)
    surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    _draw_warden_base(surf, 1)
    _draw_rect(surf, 3, 5, 4, 10, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 33, 5, 4, 10, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 2, 4, COLOR_RED_ALARM)
    _set_pixel(surf, 1, 3, COLOR_RED_ALARM)
    _set_pixel(surf, 37, 4, COLOR_RED_ALARM)
    _set_pixel(surf, 38, 3, COLOR_RED_ALARM)
    sprites["spawn_right"] = [surf]
    sprites["spawn_left"] = [_mirror_h(surf)]

    # PHASE 2: crack marks (black pixels breaking armor)
    for anim in ["idle", "walk"]:
        p2_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            # Crack marks on chest
            _set_pixel(surf, 12, 15, COLOR_BLACK)
            _set_pixel(surf, 13, 16, COLOR_BLACK)
            _set_pixel(surf, 14, 17, COLOR_BLACK)
            _set_pixel(surf, 15, 18, COLOR_BLACK)
            _set_pixel(surf, 26, 14, COLOR_BLACK)
            _set_pixel(surf, 27, 15, COLOR_BLACK)
            _set_pixel(surf, 28, 16, COLOR_BLACK)
            # Core orange
            _draw_rect(surf, 18, 17, 4, 4, COLOR_NEON_ORANGE)
            p2_frames.append(surf)
        sprites[f"{anim}_p2_right"] = p2_frames
        sprites[f"{anim}_p2_left"] = [_mirror_h(f) for f in p2_frames]

    # PHASE 3: exposed wiring, red emergency lighting
    for anim in ["idle", "walk"]:
        p3_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            # Many cracks
            for cy in range(14, 24):
                _set_pixel(surf, 12 + (cy % 4), cy, COLOR_BLACK)
                _set_pixel(surf, 26 - (cy % 4), cy, COLOR_BLACK)
            # Damaged shoulder pads
            _draw_rect(surf, 2, 12, 4, 3, COLOR_BLACK)
            _draw_rect(surf, 34, 12, 4, 3, COLOR_BLACK)
            # Exposed wiring (thin colored lines where armor was)
            _set_pixel(surf, 4, 13, COLOR_NEON_BLUE)
            _set_pixel(surf, 5, 14, COLOR_GREEN_HACK)
            _set_pixel(surf, 35, 13, COLOR_NEON_BLUE)
            _set_pixel(surf, 36, 14, COLOR_NEON_ORANGE)
            # Core red
            _draw_rect(surf, 18, 17, 4, 4, COLOR_RED_ALARM)
            # Red emergency lighting on edges
            _set_pixel(surf, 7, 12, COLOR_RED_ALARM)
            _set_pixel(surf, 32, 12, COLOR_RED_ALARM)
            _set_pixel(surf, 7, 25, COLOR_RED_ALARM)
            _set_pixel(surf, 32, 25, COLOR_RED_ALARM)
            p3_frames.append(surf)
        sprites[f"{anim}_p3_right"] = p3_frames
        sprites[f"{anim}_p3_left"] = [_mirror_h(f) for f in p3_frames]

    # HURT
    surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    _draw_warden_base(surf, 0)
    overlay = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 100))
    surf.blit(overlay, (0, 0))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (4 frame, progressive explosion)
    death_frames = []
    for f in range(4):
        surf = pygame.Surface((WARDEN_WIDTH + 10, WARDEN_HEIGHT + 10), pygame.SRCALPHA)
        if f < 2:
            _draw_warden_base(surf, 2)
            for i in range(f + 1):
                cx = 14 + i * 10
                cy = 18 + i * 6
                for dy in range(-4, 5):
                    for dx in range(-4, 5):
                        if dx * dx + dy * dy <= 16:
                            _set_pixel(surf, cx + dx + 5, cy + dy + 5, COLOR_NEON_ORANGE)
        else:
            cx, cy = WARDEN_WIDTH // 2 + 5, WARDEN_HEIGHT // 2 + 5
            radius = 10 + (f - 2) * 8
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    dist_sq = dx * dx + dy * dy
                    if dist_sq <= radius * radius:
                        if dist_sq < (radius // 2) ** 2:
                            _set_pixel(surf, cx + dx, cy + dy, COLOR_YELLOW)
                        elif dist_sq < (radius * 3 // 4) ** 2:
                            _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_ORANGE)
                        else:
                            _set_pixel(surf, cx + dx, cy + dy, COLOR_RED_ALARM)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames

    return sprites


# ============================================================
# OGGETTI VARI: telecamera, terminale, proiettile laser, particelle
# ============================================================

def generate_camera_sprite():
    """Telecamera di sorveglianza 12x8."""
    surf = pygame.Surface((12, 8), pygame.SRCALPHA)
    _draw_rect(surf, 2, 0, 2, 3, COLOR_MID_GRAY)    # supporto
    _draw_rect(surf, 0, 3, 8, 5, COLOR_DARK_GRAY)     # corpo
    _draw_rect(surf, 8, 4, 4, 3, COLOR_MID_GRAY)      # lente
    _draw_rect(surf, 10, 5, 2, 1, COLOR_RED_ALARM)     # LED
    return surf


def generate_terminal_sprite():
    """Terminale hackabile 16x16 with cursor and keyboard tray."""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    _draw_rect(surf, 2, 1, 12, 10, COLOR_DARK_GRAY)    # monitor frame
    _draw_rect(surf, 3, 2, 10, 8, COLOR_BG_NIGHT)       # schermo
    # Testo sullo schermo
    for i in range(3):
        _draw_rect(surf, 4, 3 + i * 2, 6 + (i % 2) * 2, 1, COLOR_GREEN_HACK)
    # Blinking cursor line (static cursor block)
    _draw_rect(surf, 4, 8, 2, 1, COLOR_GREEN_HACK)
    # Base/stand
    _draw_rect(surf, 5, 11, 6, 1, COLOR_MID_GRAY)
    # Keyboard tray (row of small dots)
    _draw_rect(surf, 3, 12, 10, 3, COLOR_DARK_GRAY)
    for kx in range(4, 13, 2):
        _set_pixel(surf, kx, 13, COLOR_MID_GRAY)
    for kx in range(5, 12, 2):
        _set_pixel(surf, kx, 14, COLOR_MID_GRAY)
    # Status light
    _set_pixel(surf, 13, 9, COLOR_GREEN_HACK)
    return surf


def generate_door_sprites():
    """Porta/cancello 16x32, aperta e chiusa."""
    sprites = {}
    # Chiusa
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 16, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 1, 1, 14, 30, COLOR_MID_GRAY)
    for i in range(4):
        _draw_rect(surf, 1, 1 + i * 8, 14, 1, COLOR_DARK_GRAY)
    _draw_rect(surf, 7, 14, 2, 2, COLOR_RED_ALARM)
    sprites["closed"] = surf

    # Aperta
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 4, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 12, 0, 4, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 1, 14, 2, 2, COLOR_GREEN_HACK)
    _draw_rect(surf, 13, 14, 2, 2, COLOR_GREEN_HACK)
    sprites["open"] = surf

    return sprites


def generate_laser_sprite():
    """Proiettile laser del drone, 6x2."""
    surf = pygame.Surface((6, 2), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 6, 2, COLOR_RED_ALARM)
    _draw_rect(surf, 1, 0, 4, 2, (255, 150, 150))
    return surf


def generate_emp_sprite():
    """Proiettile EMP, 8x8 cerchio blu."""
    surf = pygame.Surface((8, 8), pygame.SRCALPHA)
    cx, cy = 4, 4
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if dx * dx + dy * dy <= 9:
                _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_BLUE)
            elif dx * dx + dy * dy <= 16:
                _set_pixel(surf, cx + dx, cy + dy, (0, 229, 255, 100))
    return surf


def generate_heart_sprite(full=True):
    """Cuore per l'HUD, 9x9 with proper curve and 3D highlight."""
    surf = pygame.Surface((9, 9), pygame.SRCALPHA)
    color = COLOR_RED_ALARM if full else COLOR_DARK_GRAY
    outline_color = (180, 30, 50) if full else (20, 18, 40)

    heart_pixels = [
        # Row 0: top bumps
        (1, 0), (2, 0), (3, 0), (5, 0), (6, 0), (7, 0),
        # Row 1
        (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1),
        # Row 2
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2),
        # Row 3
        (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3),
        # Row 4
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        # Row 5
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        # Row 6
        (3, 6), (4, 6), (5, 6),
        # Row 7
        (4, 7),
    ]
    for px, py in heart_pixels:
        _set_pixel(surf, px, py, color)

    if full:
        # 3D highlight in top-left
        _set_pixel(surf, 1, 1, (255, 120, 140))
        _set_pixel(surf, 2, 1, (255, 100, 120))
    else:
        # Empty heart: outline only, dark fill
        for px, py in heart_pixels:
            _set_pixel(surf, px, py, outline_color)
        # Clear interior
        interior = [
            (1, 1), (2, 1), (3, 1), (5, 1), (6, 1), (7, 1),
            (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2),
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
            (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
            (3, 5), (4, 5), (5, 5),
            (4, 6),
        ]
        dark_fill = (15, 13, 35)
        for px, py in interior:
            _set_pixel(surf, px, py, dark_fill)

    return surf


def generate_particle_sprites():
    """Particelle varie per effetti."""
    particles = {}
    # Scintilla
    surf = pygame.Surface((3, 3), pygame.SRCALPHA)
    _set_pixel(surf, 1, 0, COLOR_YELLOW)
    _set_pixel(surf, 0, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 1, COLOR_WHITE_UI)
    _set_pixel(surf, 2, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 2, COLOR_YELLOW)
    particles["spark"] = surf

    # Hit effect
    surf = pygame.Surface((5, 5), pygame.SRCALPHA)
    _set_pixel(surf, 2, 0, COLOR_NEON_ORANGE)
    _set_pixel(surf, 0, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 4, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 4, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 2, COLOR_YELLOW)
    particles["hit"] = surf

    # Polvere
    surf = pygame.Surface((2, 2), pygame.SRCALPHA)
    surf.fill((200, 200, 200, 120))
    particles["dust"] = surf

    return particles


def generate_all_sprites():
    """Genera tutti gli sprite del gioco, restituisce un dizionario globale."""
    all_sprites = {
        "gig": generate_gig_sprites(),
        "thug": generate_thug_sprites(),
        "drone": generate_drone_sprites(),
        "warden": generate_warden_sprites(),
        "camera": generate_camera_sprite(),
        "terminal": generate_terminal_sprite(),
        "doors": generate_door_sprites(),
        "laser": generate_laser_sprite(),
        "emp": generate_emp_sprite(),
        "heart_full": generate_heart_sprite(True),
        "heart_empty": generate_heart_sprite(False),
        "particles": generate_particle_sprites(),
    }
    return all_sprites
