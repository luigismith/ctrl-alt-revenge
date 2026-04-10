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

# Uniform canvas sizes for each character type
GIG_CANVAS_W, GIG_CANVAS_H = 34, 32
THUG_CANVAS_W, THUG_CANVAS_H = 32, 32
DRONE_CANVAS_W, DRONE_CANVAS_H = 32, 20
WARDEN_CANVAS_W, WARDEN_CANVAS_H = 54, 58


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
# Base 24x32, uniform canvas 34x32
# ============================================================

def _draw_gig_base(surf, facing_right=True, ox=5, oy=0):
    """Disegna il frame base di GIG (in piedi, rivolto a destra).
    ox/oy offset to center base art on larger canvas."""
    W, H = PLAYER_WIDTH, PLAYER_HEIGHT

    # --- Stivali (riga 27-31) ---
    _draw_rect(surf, 4+ox, 27+oy, 5, 5, COLOR_BOOTS_BROWN)   # piede sinistro
    _draw_rect(surf, 13+ox, 27+oy, 5, 5, COLOR_BOOTS_BROWN)   # piede destro
    # Suola
    _draw_rect(surf, 4+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    # Lacci (alternating dark pixels)
    _set_pixel(surf, 5+ox, 27+oy, COLOR_BLACK)
    _set_pixel(surf, 7+ox, 27+oy, COLOR_BLACK)
    _set_pixel(surf, 6+ox, 28+oy, COLOR_BLACK)
    _set_pixel(surf, 14+ox, 27+oy, COLOR_BLACK)
    _set_pixel(surf, 16+ox, 27+oy, COLOR_BLACK)
    _set_pixel(surf, 15+ox, 28+oy, COLOR_BLACK)

    # --- Pantaloni (riga 20-26) ---
    _draw_rect(surf, 5+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)     # gamba sinistra
    _draw_rect(surf, 13+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)    # gamba destra
    # Cintura
    _draw_rect(surf, 5+ox, 19+oy, 12, 1, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 19+oy, COLOR_NEON_ORANGE)  # fibbia
    _set_pixel(surf, 11+ox, 19+oy, COLOR_NEON_ORANGE)

    # --- Torso / giacca (riga 9-18) ---
    _draw_rect(surf, 5+ox, 9+oy, 12, 10, COLOR_JACKET_BROWN)
    # Ombra giacca lato sinistro
    _draw_rect(surf, 5+ox, 9+oy, 3, 10, COLOR_JACKET_SHADOW)
    # Colletto
    _draw_rect(surf, 7+ox, 8+oy, 8, 1, COLOR_JACKET_BROWN)
    _set_pixel(surf, 6+ox, 8+oy, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 15+ox, 8+oy, COLOR_JACKET_SHADOW)
    # T-shirt sotto (visible V-neck)
    _draw_rect(surf, 8+ox, 9+oy, 6, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 10+ox, 12+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 11+ox, 12+oy, COLOR_DARK_GRAY)
    # Pocket (darker rect 2x3)
    _draw_rect(surf, 13+ox, 13+oy, 2, 3, COLOR_JACKET_SHADOW)

    # --- Braccio destro (umano) ---
    _draw_rect(surf, 17+ox, 10+oy, 3, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17+ox, 17+oy, 3, 2, COLOR_SKIN)     # mano
    _set_pixel(surf, 17+ox, 17+oy, COLOR_SKIN_SHADOW)     # shadow on hand

    # --- Braccio sinistro (cyber) ---
    _draw_rect(surf, 2+ox, 10+oy, 3, 7, COLOR_CYBER_ARM)
    _draw_rect(surf, 2+ox, 17+oy, 3, 2, COLOR_CYBER_ARM)
    # 4 glow segments alternating brightness
    _set_pixel(surf, 2+ox, 11+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 12+oy, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 2+ox, 13+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 14+oy, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 2+ox, 15+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 16+oy, COLOR_CYBER_GLOW_DIM)

    # --- Testa (riga 0-8) ---
    # Skin base
    _draw_rect(surf, 7+ox, 2+oy, 8, 6, COLOR_SKIN)
    # Highlight on forehead
    _set_pixel(surf, 8+ox, 2+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 9+ox, 2+oy, COLOR_SKIN_HIGHLIGHT)
    # Shadow on jaw
    _draw_rect(surf, 7+ox, 6+oy, 8, 1, COLOR_SKIN_SHADOW)

    # Capelli con 2 shades of gray + ponytail
    _draw_rect(surf, 7+ox, 0+oy, 8, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 10+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 12+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
    # Ponytail (3-4 pixels trailing)
    _set_pixel(surf, 15+ox, 1+oy, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16+ox, 2+oy, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17+ox, 3+oy, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17+ox, 4+oy, COLOR_HAIR_GRAY_LIGHT)

    # Barba
    _draw_rect(surf, 7+ox, 6+oy, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 8+ox, 7+oy, 4, 1, COLOR_HAIR_GRAY_LIGHT)

    # Occhi
    _set_pixel(surf, 9+ox, 4+oy, COLOR_EYE)     # right eye white
    _set_pixel(surf, 10+ox, 4+oy, COLOR_BLACK)   # right pupil
    _set_pixel(surf, 12+ox, 4+oy, COLOR_EYE)    # left eye white
    _set_pixel(surf, 13+ox, 4+oy, COLOR_BLACK)   # left pupil

    # Cybernetic eye: 2x2 bright blue with 1px glow around it
    _draw_rect(surf, 8+ox, 3+oy, 2, 2, COLOR_NEON_BLUE)
    _set_pixel(surf, 7+ox, 3+oy, (0, 150, 200, 150))    # glow
    _set_pixel(surf, 7+ox, 4+oy, (0, 150, 200, 150))
    _set_pixel(surf, 10+ox, 3+oy, (0, 150, 200, 100))
    _set_pixel(surf, 8+ox, 2+oy, (0, 150, 200, 80))
    _set_pixel(surf, 9+ox, 5+oy, (0, 150, 200, 80))

    # Sopracciglia
    _set_pixel(surf, 9+ox, 3+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 3+oy, COLOR_BLACK)


def generate_gig_sprites():
    """Genera tutti i frame animazione di GIG.
    Restituisce un dizionario {nome_animazione: [frame1, frame2, ...]}
    Ogni frame è disponibile in entrambe le direzioni.
    """
    sprites = {}
    CW, CH = GIG_CANVAS_W, GIG_CANVAS_H
    ox = (CW - PLAYER_WIDTH) // 2  # 5
    oy = CH - PLAYER_HEIGHT         # 0

    # --- IDLE (4 frame) ---
    idle_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if f == 1:
            # Breathing: slight shoulder raise
            _set_pixel(surf, 8+ox, 8+oy, COLOR_JACKET_BROWN)
            _set_pixel(surf, 13+ox, 8+oy, COLOR_JACKET_BROWN)
            # Subtle cyber glow pulse
            _set_pixel(surf, 2+ox, 12+oy, COLOR_CYBER_GLOW)
            _set_pixel(surf, 3+ox, 13+oy, COLOR_CYBER_GLOW)
        elif f == 2:
            # Cyber arm glow brightest
            _set_pixel(surf, 2+ox, 11+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 12+oy, (0, 255, 255))
            _set_pixel(surf, 2+ox, 13+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 14+oy, (0, 255, 255))
            _set_pixel(surf, 2+ox, 15+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 16+oy, (0, 255, 255))
        elif f == 3:
            # Slight weight shift (1px leg offset)
            _draw_rect(surf, 5+ox, 20+oy, 4, 7, (0, 0, 0, 0))  # clear left leg
            _draw_rect(surf, 6+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)  # shift right 1px
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frame with clear leg stride and arm pump) ---
    run_frames = []
    leg_offsets = [(0, 0, 0, 0), (2, -1, -2, 1), (0, 0, 0, 0), (-2, 1, 2, -1)]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        lox1, loy1, lox2, loy2 = leg_offsets[f]
        bob = -1 if f in (1, 3) else 0

        # Stivali with stride offset
        _draw_rect(surf, 4+ox + lox1, 27+oy + loy1, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 13+ox + lox2, 27+oy + loy2, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 4+ox + lox1, 30+oy + loy1, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 13+ox + lox2, 30+oy + loy2, 5, 1, COLOR_BOOTS_SOLE)
        # Laces
        _set_pixel(surf, 5+ox + lox1, 27+oy + loy1, COLOR_BLACK)
        _set_pixel(surf, 7+ox + lox1, 27+oy + loy1, COLOR_BLACK)
        _set_pixel(surf, 14+ox + lox2, 27+oy + loy2, COLOR_BLACK)
        _set_pixel(surf, 16+ox + lox2, 27+oy + loy2, COLOR_BLACK)

        # Gambe with stride
        _draw_rect(surf, 5+ox + lox1, 20+oy, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 13+ox + lox2, 20+oy, 4, 7, COLOR_PANTS_DARK)
        # Cintura
        _draw_rect(surf, 5+ox, 19+oy + bob, 12, 1, COLOR_BLACK)
        _set_pixel(surf, 10+ox, 19+oy + bob, COLOR_NEON_ORANGE)
        _set_pixel(surf, 11+ox, 19+oy + bob, COLOR_NEON_ORANGE)

        # Torso con bob
        _draw_rect(surf, 5+ox, 9+oy + bob, 12, 10, COLOR_JACKET_BROWN)
        _draw_rect(surf, 5+ox, 9+oy + bob, 3, 10, COLOR_JACKET_SHADOW)
        _draw_rect(surf, 7+ox, 8+oy + bob, 8, 1, COLOR_JACKET_BROWN)
        _draw_rect(surf, 8+ox, 9+oy + bob, 6, 3, COLOR_DARK_GRAY)
        # Pocket
        _draw_rect(surf, 13+ox, 13+oy + bob, 2, 3, COLOR_JACKET_SHADOW)

        # Arm pump - human arm
        arm_swing = 2 if f in (0, 2) else -2
        _draw_rect(surf, 17+ox, 10+oy + bob, 3, 7, COLOR_JACKET_BROWN)
        _draw_rect(surf, 17+ox, 17+oy + bob + arm_swing, 3, 2, COLOR_SKIN)
        # Cyber arm pumps opposite
        _draw_rect(surf, 2+ox, 10+oy + bob, 3, 7, COLOR_CYBER_ARM)
        _draw_rect(surf, 2+ox, 17+oy + bob - arm_swing, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 2+ox, 11+oy + bob, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 13+oy + bob, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2+ox, 15+oy + bob, COLOR_CYBER_GLOW)

        # Testa
        _draw_rect(surf, 7+ox, 2+oy + bob, 8, 6, COLOR_SKIN)
        _set_pixel(surf, 8+ox, 2+oy + bob, COLOR_SKIN_HIGHLIGHT)
        _set_pixel(surf, 9+ox, 2+oy + bob, COLOR_SKIN_HIGHLIGHT)
        _draw_rect(surf, 7+ox, 6+oy + bob, 8, 1, COLOR_SKIN_SHADOW)
        _draw_rect(surf, 7+ox, 0+oy + bob, 8, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 8+ox, 0+oy + bob, COLOR_HAIR_GRAY_LIGHT)
        _set_pixel(surf, 10+ox, 0+oy + bob, COLOR_HAIR_GRAY_LIGHT)
        # Ponytail bounces
        pt_bob = 1 if f in (1, 3) else 0
        _set_pixel(surf, 15+ox, 1+oy + bob, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16+ox, 2+oy + bob + pt_bob, COLOR_HAIR_GRAY)
        _set_pixel(surf, 17+ox, 3+oy + bob + pt_bob, COLOR_HAIR_GRAY)
        # Barba
        _draw_rect(surf, 7+ox, 6+oy + bob, 6, 2, COLOR_HAIR_GRAY)
        # Eyes
        _set_pixel(surf, 9+ox, 4+oy + bob, COLOR_EYE)
        _set_pixel(surf, 12+ox, 4+oy + bob, COLOR_EYE)
        _set_pixel(surf, 10+ox, 4+oy + bob, COLOR_BLACK)
        _set_pixel(surf, 13+ox, 4+oy + bob, COLOR_BLACK)
        # Cyber eye
        _draw_rect(surf, 8+ox, 3+oy + bob, 2, 2, COLOR_NEON_BLUE)

        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (2 frames, gambe raccolte) ---
    jump_frames = []
    for jf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        # Stivali more tucked
        _draw_rect(surf, 4+ox, 25+oy, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 13+ox, 25+oy, 5, 4, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 4+ox, 28+oy, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 13+ox, 28+oy, 5, 1, COLOR_BOOTS_SOLE)
        # Legs tucked
        _draw_rect(surf, 5+ox, 21+oy, 4, 4, COLOR_PANTS_DARK)
        _draw_rect(surf, 13+ox, 21+oy, 4, 4, COLOR_PANTS_DARK)
        _draw_rect(surf, 5+ox, 20+oy, 12, 1, COLOR_BLACK)
        # Torso
        _draw_rect(surf, 5+ox, 9+oy, 12, 11, COLOR_JACKET_BROWN)
        _draw_rect(surf, 5+ox, 9+oy, 3, 11, COLOR_JACKET_SHADOW)
        _draw_rect(surf, 8+ox, 9+oy, 6, 3, COLOR_DARK_GRAY)
        _draw_rect(surf, 13+ox, 13+oy, 2, 3, COLOR_JACKET_SHADOW)
        # Arms raised
        arm_adj = 0 if jf == 0 else 1
        _draw_rect(surf, 17+ox, 7+oy+arm_adj, 3, 7, COLOR_JACKET_BROWN)
        _draw_rect(surf, 17+ox, 14+oy+arm_adj, 3, 2, COLOR_SKIN)
        _draw_rect(surf, 2+ox, 7+oy, 3, 7, COLOR_CYBER_ARM)
        _draw_rect(surf, 2+ox, 14+oy, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 2+ox, 8+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 10+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 2+ox, 12+oy, COLOR_CYBER_GLOW)
        # Testa
        _draw_rect(surf, 7+ox, 2+oy, 8, 6, COLOR_SKIN)
        _set_pixel(surf, 8+ox, 2+oy, COLOR_SKIN_HIGHLIGHT)
        _draw_rect(surf, 7+ox, 0+oy, 8, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 8+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
        _draw_rect(surf, 7+ox, 6+oy, 6, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 9+ox, 4+oy, COLOR_EYE)
        _set_pixel(surf, 12+ox, 4+oy, COLOR_EYE)
        _draw_rect(surf, 8+ox, 3+oy, 2, 2, COLOR_NEON_BLUE)
        # Ponytail flows up
        _set_pixel(surf, 15+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16+ox, 1+oy, COLOR_HAIR_GRAY)
        jump_frames.append(surf)
    sprites["jump_right"] = jump_frames
    sprites["jump_left"] = [_mirror_h(f) for f in jump_frames]

    # --- FALL (2 frames) ---
    fall_frames = []
    for ff in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_rect(surf, 4+ox, 27+oy, 5, 5, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 13+ox, 27+oy, 5, 5, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 4+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 13+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 5+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 13+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 5+ox, 19+oy, 12, 1, COLOR_BLACK)
        _draw_rect(surf, 5+ox, 9+oy, 12, 10, COLOR_JACKET_BROWN)
        _draw_rect(surf, 5+ox, 9+oy, 3, 10, COLOR_JACKET_SHADOW)
        _draw_rect(surf, 8+ox, 9+oy, 6, 3, COLOR_DARK_GRAY)
        # Arms spread - slightly lower in frame 1
        arm_drop = 0 if ff == 0 else 1
        _draw_rect(surf, 18+ox, 10+oy+arm_drop, 3, 6, COLOR_JACKET_BROWN)
        _draw_rect(surf, 18+ox, 16+oy+arm_drop, 3, 2, COLOR_SKIN)
        _draw_rect(surf, 1+ox, 10+oy+arm_drop, 3, 6, COLOR_CYBER_ARM)
        _draw_rect(surf, 1+ox, 16+oy+arm_drop, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 1+ox, 11+oy+arm_drop, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2+ox, 13+oy+arm_drop, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 1+ox, 15+oy+arm_drop, COLOR_CYBER_GLOW)
        # Testa
        _draw_rect(surf, 7+ox, 2+oy, 8, 6, COLOR_SKIN)
        _set_pixel(surf, 8+ox, 2+oy, COLOR_SKIN_HIGHLIGHT)
        _draw_rect(surf, 7+ox, 0+oy, 8, 2, COLOR_HAIR_GRAY)
        _draw_rect(surf, 7+ox, 6+oy, 6, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 9+ox, 4+oy, COLOR_EYE)
        _set_pixel(surf, 12+ox, 4+oy, COLOR_EYE)
        _draw_rect(surf, 8+ox, 3+oy, 2, 2, COLOR_NEON_BLUE)
        # Ponytail flows up
        _set_pixel(surf, 15+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
        _set_pixel(surf, 17+ox, 1+oy, COLOR_HAIR_GRAY)
        fall_frames.append(surf)
    sprites["fall_right"] = fall_frames
    sprites["fall_left"] = [_mirror_h(f) for f in fall_frames]

    # --- LAND (2 frames, body compressed then returning) ---
    land_frames = []
    for lf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if lf == 0:
            # Compressed: shorter torso, wide stance, body shifted down
            _draw_rect(surf, 2+ox, 28+oy, 6, 4, COLOR_BOOTS_BROWN)   # wide left foot
            _draw_rect(surf, 14+ox, 28+oy, 6, 4, COLOR_BOOTS_BROWN)  # wide right foot
            _draw_rect(surf, 2+ox, 31+oy, 6, 1, COLOR_BOOTS_SOLE)
            _draw_rect(surf, 14+ox, 31+oy, 6, 1, COLOR_BOOTS_SOLE)
            _draw_rect(surf, 4+ox, 24+oy, 5, 4, COLOR_PANTS_DARK)
            _draw_rect(surf, 13+ox, 24+oy, 5, 4, COLOR_PANTS_DARK)
            _draw_rect(surf, 4+ox, 23+oy, 14, 1, COLOR_BLACK)
            # Shorter torso
            _draw_rect(surf, 5+ox, 14+oy, 12, 9, COLOR_JACKET_BROWN)
            _draw_rect(surf, 5+ox, 14+oy, 3, 9, COLOR_JACKET_SHADOW)
            _draw_rect(surf, 8+ox, 14+oy, 6, 3, COLOR_DARK_GRAY)
            # Arms
            _draw_rect(surf, 17+ox, 15+oy, 3, 5, COLOR_JACKET_BROWN)
            _draw_rect(surf, 17+ox, 20+oy, 3, 2, COLOR_SKIN)
            _draw_rect(surf, 2+ox, 15+oy, 3, 5, COLOR_CYBER_ARM)
            _draw_rect(surf, 2+ox, 20+oy, 3, 2, COLOR_CYBER_ARM)
            _set_pixel(surf, 2+ox, 16+oy, COLOR_CYBER_GLOW)
            _set_pixel(surf, 3+ox, 18+oy, COLOR_CYBER_GLOW_DIM)
            # Head
            _draw_rect(surf, 7+ox, 8+oy, 8, 6, COLOR_SKIN)
            _set_pixel(surf, 8+ox, 8+oy, COLOR_SKIN_HIGHLIGHT)
            _draw_rect(surf, 7+ox, 6+oy, 8, 2, COLOR_HAIR_GRAY)
            _draw_rect(surf, 7+ox, 12+oy, 6, 2, COLOR_HAIR_GRAY)
            _set_pixel(surf, 9+ox, 10+oy, COLOR_EYE)
            _set_pixel(surf, 12+ox, 10+oy, COLOR_EYE)
            _draw_rect(surf, 8+ox, 9+oy, 2, 2, COLOR_NEON_BLUE)
        else:
            # Returning to standing - use base
            _draw_gig_base(surf, ox=ox, oy=oy)
            # Slight knee bend remains
            _draw_rect(surf, 5+ox, 20+oy, 4, 7, (0, 0, 0, 0))
            _draw_rect(surf, 5+ox, 21+oy, 4, 6, COLOR_PANTS_DARK)
        land_frames.append(surf)
    sprites["land_right"] = land_frames
    sprites["land_left"] = [_mirror_h(f) for f in land_frames]

    # --- WALL SLIDE (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Right arm reaching up and grabbing wall
    _draw_rect(surf, 18+ox, 5+oy, 3, 10, COLOR_JACKET_BROWN)
    _draw_rect(surf, 18+ox, 5+oy, 3, 2, COLOR_SKIN)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Everything shifted down and compressed
    _draw_rect(surf, 4+ox, 28+oy, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 13+ox, 28+oy, 5, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 5+ox, 24+oy, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 13+ox, 24+oy, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 5+ox, 23+oy, 12, 1, COLOR_BLACK)
    _draw_rect(surf, 5+ox, 16+oy, 12, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5+ox, 16+oy, 3, 7, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8+ox, 16+oy, 6, 3, COLOR_DARK_GRAY)
    # Arms
    _draw_rect(surf, 17+ox, 17+oy, 3, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17+ox, 22+oy, 3, 2, COLOR_SKIN)
    _draw_rect(surf, 2+ox, 17+oy, 3, 5, COLOR_CYBER_ARM)
    _draw_rect(surf, 2+ox, 22+oy, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 2+ox, 18+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 20+oy, COLOR_CYBER_GLOW_DIM)
    # Head
    _draw_rect(surf, 7+ox, 10+oy, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 8+ox, 10+oy, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 7+ox, 8+oy, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 7+ox, 14+oy, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 9+ox, 12+oy, COLOR_EYE)
    _set_pixel(surf, 12+ox, 12+oy, COLOR_EYE)
    _draw_rect(surf, 8+ox, 11+oy, 2, 2, COLOR_NEON_BLUE)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Body nearly horizontal, feet forward
    _draw_rect(surf, 0+ox, 23+oy, 6, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 0+ox, 26+oy, 6, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 0+ox, 20+oy, 6, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 5+ox, 18+oy, 14, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5+ox, 18+oy, 3, 5, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 8+ox, 18+oy, 6, 3, COLOR_DARK_GRAY)
    # Head at end
    _draw_rect(surf, 18+ox, 16+oy, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 19+ox, 16+oy, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 18+ox, 14+oy, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 18+ox, 20+oy, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 20+ox, 18+oy, COLOR_EYE)
    _set_pixel(surf, 23+ox, 18+oy, COLOR_EYE)
    _draw_rect(surf, 19+ox, 17+oy, 2, 2, COLOR_NEON_BLUE)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 combo moves, 3 frames each: wind-up, strike, recovery) ---
    for combo_idx in range(3):
        punch_frames = []
        arm_extend = 4 + combo_idx * 3
        arm_y = 13 - combo_idx

        # Frame 0: wind-up (arm pulled back)
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            # Pull arm back
            _draw_rect(surf, ox - 2, arm_y+oy, 4, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, ox - 3, arm_y+oy, 3, 3, COLOR_SKIN)
        else:
            # Wind-up for final kick - leg pulled back
            _draw_rect(surf, 4+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
        punch_frames.append(surf)

        # Frame 1: existing strike
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            # Punch with right arm
            _draw_rect(surf, 19+ox, arm_y+oy, arm_extend, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, 19+ox + arm_extend - 2, arm_y+oy, 3, 3, COLOR_SKIN)
            # Motion trail
            trail_color = (255, 200, 100, 120)
            _set_pixel(surf, 19+ox + arm_extend + 1, arm_y+oy, trail_color)
            _set_pixel(surf, 19+ox + arm_extend + 2, arm_y+oy + 1, trail_color)
            # Impact flash
            _set_pixel(surf, 19+ox + arm_extend + 1, arm_y+oy + 1, COLOR_NEON_ORANGE)
            _set_pixel(surf, 19+ox + arm_extend + 1, arm_y+oy + 2, COLOR_YELLOW)
        else:
            # Final combo kick
            _draw_rect(surf, 18+ox, 23+oy, arm_extend + 3, 3, COLOR_PANTS_DARK)
            _draw_rect(surf, 18+ox + arm_extend + 1, 22+oy, 3, 4, COLOR_BOOTS_BROWN)
            trail_color = (255, 200, 100, 120)
            _set_pixel(surf, 18+ox + arm_extend + 4, 23+oy, trail_color)
            _set_pixel(surf, 18+ox + arm_extend + 5, 24+oy, trail_color)
            _set_pixel(surf, 18+ox + arm_extend + 4, 24+oy, COLOR_NEON_ORANGE)
        punch_frames.append(surf)

        # Frame 2: recovery (arm returning)
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            # Arm partially extended, returning
            half_ext = arm_extend // 2
            _draw_rect(surf, 19+ox, arm_y+oy, half_ext, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, 19+ox + half_ext - 1, arm_y+oy, 3, 3, COLOR_SKIN)
        else:
            # Leg returning from kick
            _draw_rect(surf, 18+ox, 23+oy, 4, 3, COLOR_PANTS_DARK)
            _draw_rect(surf, 21+ox, 22+oy, 3, 4, COLOR_BOOTS_BROWN)
        punch_frames.append(surf)

        sprites[f"punch{combo_idx}_right"] = punch_frames
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(f) for f in punch_frames]

    # --- KICK (3 frames: wind-up, strike, recovery) ---
    kick_frames = []
    # Frame 0: wind-up
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Pull leg back slightly
    _draw_rect(surf, 4+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
    kick_frames.append(surf)
    # Frame 1: strike
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 18+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 25+ox, 20+oy, 3, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 28+ox, 22+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 29+ox, 21+oy, COLOR_YELLOW)
    kick_frames.append(surf)
    # Frame 2: recovery
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 18+ox, 22+oy, 4, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 21+ox, 21+oy, 3, 4, COLOR_BOOTS_BROWN)
    kick_frames.append(surf)
    sprites["kick_right"] = kick_frames
    sprites["kick_left"] = [_mirror_h(f) for f in kick_frames]

    # --- PARRY (1 frame, guardia alta) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Arms crossed in front
    _draw_rect(surf, 6+ox, 8+oy, 10, 3, COLOR_CYBER_ARM)
    _draw_rect(surf, 6+ox, 8+oy, 10, 1, COLOR_CYBER_GLOW)
    # Energy shield line
    for i in range(10):
        _set_pixel(surf, 5+ox, 6+oy + i, COLOR_NEON_BLUE)
        _set_pixel(surf, 4+ox, 7+oy + i, (0, 200, 255, 80))
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame, knockback) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Red flash on torso
    _draw_rect(surf, 5+ox, 9+oy, 12, 10, COLOR_RED_ALARM)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame, cyber arm extended with hologram) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Cyber arm extended
    _draw_rect(surf, 0+ox, 10+oy, 3, 7, COLOR_CYBER_ARM)
    # Hologram (green checkerboard)
    for hy in range(5):
        for hx in range(5):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx + PLAYER_WIDTH + ox, 9+oy + hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx + PLAYER_WIDTH + ox, 9+oy + hy, (0, 180, 60, 150))
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ============================================================
# THUG — Scagnozzo umano
# Base 22x32, uniform canvas 32x32
# ============================================================

def _draw_thug_base(surf, alert=False, ox=5, oy=0):
    W, H = THUG_WIDTH, THUG_HEIGHT

    # Stivali (riga 27-31)
    _draw_rect(surf, 4+ox, 27+oy, 5, 5, COLOR_BLACK)
    _draw_rect(surf, 13+ox, 27+oy, 5, 5, COLOR_BLACK)

    # Pantaloni (riga 20-26)
    _draw_rect(surf, 5+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 13+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 5+ox, 19+oy, 12, 1, COLOR_BLACK)

    # Torso - stockier, wider shoulders
    body_color = COLOR_RED_ALARM if alert else COLOR_THUG_SHIRT
    _draw_rect(surf, 4+ox, 9+oy, 14, 10, body_color)
    _draw_rect(surf, 7+ox, 9+oy, 8, 3, COLOR_DARK_GRAY)
    # Skull marking (simple X cross in lighter color)
    marking_color = (100, 50, 50)
    _set_pixel(surf, 9+ox, 13+oy, marking_color)
    _set_pixel(surf, 12+ox, 13+oy, marking_color)
    _set_pixel(surf, 10+ox, 14+oy, marking_color)
    _set_pixel(surf, 11+ox, 14+oy, marking_color)
    _set_pixel(surf, 9+ox, 15+oy, marking_color)
    _set_pixel(surf, 12+ox, 15+oy, marking_color)

    # Braccia - wider shoulders
    _draw_rect(surf, 18+ox, 10+oy, 3, 7, body_color)
    _draw_rect(surf, 18+ox, 17+oy, 3, 2, COLOR_THUG_SKIN)
    # Brass knuckle on right hand
    _set_pixel(surf, 18+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 20+ox, 17+oy, COLOR_BRASS)
    _draw_rect(surf, 1+ox, 10+oy, 3, 7, body_color)
    _draw_rect(surf, 1+ox, 17+oy, 3, 2, COLOR_THUG_SKIN)
    # Brass knuckle on left hand
    _set_pixel(surf, 1+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 3+ox, 17+oy, COLOR_BRASS)

    # Testa
    _draw_rect(surf, 6+ox, 2+oy, 10, 7, COLOR_THUG_SKIN)
    # Bandana rossa with 2-pixel tail
    _draw_rect(surf, 6+ox, 1+oy, 10, 2, COLOR_THUG_BANDANA)
    _set_pixel(surf, 16+ox, 2+oy, COLOR_THUG_BANDANA)  # tail pixel 1
    _set_pixel(surf, 17+ox, 3+oy, COLOR_THUG_BANDANA)  # tail pixel 2
    # Occhi minacciosi
    _set_pixel(surf, 9+ox, 4+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 4+oy, COLOR_BLACK)
    # Thick brow
    _draw_rect(surf, 8+ox, 3+oy, 3, 1, COLOR_BLACK)
    _draw_rect(surf, 11+ox, 3+oy, 3, 1, COLOR_BLACK)
    # Mouth/sneer
    _set_pixel(surf, 9+ox, 7+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 7+oy, COLOR_BLACK)
    _set_pixel(surf, 11+ox, 7+oy, COLOR_BLACK)


def generate_thug_sprites():
    sprites = {}
    CW, CH = THUG_CANVAS_W, THUG_CANVAS_H
    ox = (CW - THUG_WIDTH) // 2  # 5
    oy = CH - THUG_HEIGHT         # 0

    # IDLE (2 frame)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy)
        if f == 1:
            _set_pixel(surf, 8+ox, 8+oy, COLOR_THUG_SHIRT)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    leg_off = [(0, 0), (2, -2), (0, 0), (-2, 2)]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy)
        lo1, lo2 = leg_off[f]
        # Override feet with offset
        _draw_rect(surf, 4+ox + lo1, 27+oy, 5, 5, COLOR_BLACK)
        _draw_rect(surf, 13+ox + lo2, 27+oy, 5, 5, COLOR_BLACK)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK (3 frames: wind-up, strike, recovery)
    attack_frames = []
    # Frame 0: wind-up (arm pulled back)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    # Pull arm back behind body
    _draw_rect(surf, ox - 2, 13+oy, 4, 3, COLOR_THUG_SHIRT)
    _draw_rect(surf, ox - 3, 12+oy, 3, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, ox - 3, 12+oy, COLOR_BRASS)
    _set_pixel(surf, ox - 1, 12+oy, COLOR_BRASS)
    attack_frames.append(surf)
    # Frame 1: strike (existing)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 20+ox, 13+oy, 6, 3, COLOR_THUG_SHIRT)
    _draw_rect(surf, 25+ox, 12+oy, 3, 4, COLOR_THUG_SKIN)
    # Brass knuckle flash
    _set_pixel(surf, 25+ox, 12+oy, COLOR_BRASS)
    _set_pixel(surf, 27+ox, 12+oy, COLOR_BRASS)
    _set_pixel(surf, 28+ox, 13+oy, COLOR_RED_ALARM)
    attack_frames.append(surf)
    # Frame 2: recovery
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    # Arm partially extended, returning
    _draw_rect(surf, 20+ox, 13+oy, 3, 3, COLOR_THUG_SHIRT)
    _draw_rect(surf, 22+ox, 12+oy, 3, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, 22+ox, 12+oy, COLOR_BRASS)
    _set_pixel(surf, 24+ox, 12+oy, COLOR_BRASS)
    attack_frames.append(surf)
    sprites["attack_right"] = attack_frames
    sprites["attack_left"] = [_mirror_h(f) for f in attack_frames]

    # ALERT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, alert=True, ox=ox, oy=oy)
    # Exclamation mark above head
    _draw_rect(surf, 10+ox, 0+oy, 2, 1, COLOR_RED_ALARM)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 4+ox, 9+oy, 14, 10, (255, 100, 100, 180))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (2 frame)
    death_frames = []
    # Frame 1: stagger
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 4+ox, 9+oy, 14, 10, (255, 100, 100, 100))
    death_frames.append(surf)
    # Frame 2: on the ground
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_rect(surf, 0+ox, 25+oy, 26, 5, COLOR_THUG_SHIRT)
    _draw_rect(surf, 22+ox, 24+oy, 8, 6, COLOR_THUG_SKIN)
    _draw_rect(surf, 22+ox, 23+oy, 8, 2, COLOR_THUG_BANDANA)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ============================================================
# DRONE — Drone volante con laser
# Base 24x14, uniform canvas 32x20
# ============================================================

def _draw_drone_base(surf, propeller_frame=0, eye_bright=True, ox=4, oy=3):
    w, h = DRONE_WIDTH, DRONE_HEIGHT
    # Corpo centrale - sleeker
    _draw_rect(surf, 6+ox, 5+oy, 12, 6, COLOR_DRONE_BODY)
    _draw_rect(surf, 7+ox, 4+oy, 10, 1, COLOR_DRONE_BODY)
    _draw_rect(surf, 7+ox, 11+oy, 10, 1, COLOR_DRONE_BODY)
    # Nose cone
    _set_pixel(surf, 5+ox, 6+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 7+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 18+ox, 6+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 18+ox, 7+oy, COLOR_DRONE_BODY)

    # Pannello ventrale
    _draw_rect(surf, 8+ox, 9+oy, 8, 2, COLOR_MID_GRAY)

    # Thruster glow (orange) under body
    _set_pixel(surf, 9+ox, 12+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 10+ox, 13+oy, (255, 150, 50, 150))
    _set_pixel(surf, 14+ox, 12+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 13+ox, 13+oy, (255, 150, 50, 150))

    # Pulsing sensor eye
    if eye_bright:
        eye_color = COLOR_DRONE_LIGHT
        eye_dim = (255, 100, 100)
    else:
        eye_color = (180, 30, 50)
        eye_dim = (120, 20, 30)
    _draw_rect(surf, 10+ox, 6+oy, 3, 2, eye_color)
    _set_pixel(surf, 9+ox, 6+oy, eye_dim)
    _set_pixel(surf, 13+ox, 6+oy, eye_dim)

    # Wider propeller blur (6px wide)
    if propeller_frame == 0:
        _draw_rect(surf, 0+ox, 2+oy, 6, 1, (160, 165, 180, 120))
        _draw_rect(surf, 18+ox, 2+oy, 6, 1, (160, 165, 180, 120))
    else:
        _draw_rect(surf, 1+ox, 2+oy, 4, 1, (160, 165, 180, 100))
        _draw_rect(surf, 19+ox, 2+oy, 4, 1, (160, 165, 180, 100))
    # Supporto eliche
    _set_pixel(surf, 3+ox, 3+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 3+ox, 4+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 20+ox, 3+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 20+ox, 4+oy, COLOR_DARK_GRAY)
    # Antenne
    _set_pixel(surf, 5+ox, 1+oy, COLOR_NEON_BLUE)
    _set_pixel(surf, 18+ox, 1+oy, COLOR_NEON_BLUE)


def generate_drone_sprites():
    sprites = {}
    CW, CH = DRONE_CANVAS_W, DRONE_CANVAS_H
    ox = (CW - DRONE_WIDTH) // 2   # 4
    oy = CH - DRONE_HEIGHT          # 6... but shoot needs laser below
    # For drone, we want base art vertically centered-ish to allow laser below
    # shoot surface was (32, 20) with laser going below body
    # base is 14px tall, canvas is 20px, so oy=3 leaves 3px above and 3px below
    oy = 3

    # FLY (2 frame per propellers + pulsing eye alternation)
    fly_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_drone_base(surf, f, eye_bright=(f == 0), ox=ox, oy=oy)
        fly_frames.append(surf)
    sprites["fly_right"] = fly_frames
    sprites["fly_left"] = [_mirror_h(f) for f in fly_frames]

    # SHOOT (1 frame, con laser)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    for i in range(8):
        ly = DRONE_HEIGHT + oy + i
        if ly < CH:
            _set_pixel(surf, 12+ox, ly, COLOR_RED_ALARM)
            _set_pixel(surf, 11+ox, ly, (255, 46, 77, 100))
            _set_pixel(surf, 13+ox, ly, (255, 46, 77, 100))
    sprites["shoot_right"] = [surf]
    sprites["shoot_left"] = [_mirror_h(surf)]

    # HACKED (ally, green glow)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    _draw_rect(surf, 10+ox, 6+oy, 3, 2, COLOR_GREEN_HACK)
    _set_pixel(surf, 9+ox, 6+oy, (0, 200, 80))
    _set_pixel(surf, 13+ox, 6+oy, (0, 200, 80))
    sprites["hacked_right"] = [surf]
    sprites["hacked_left"] = [_mirror_h(surf)]

    # STUNNED (EMP)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, eye_bright=False, ox=ox, oy=oy)
    for i in range(3):
        _set_pixel(surf, 6+ox + i * 5, 1+oy, COLOR_YELLOW)
        _set_pixel(surf, 7+ox + i * 5, 0+oy, COLOR_YELLOW)
    sprites["stunned_right"] = [surf]
    sprites["stunned_left"] = [_mirror_h(surf)]

    # DEATH (explosion, 3 frame)
    death_frames = []
    for f in range(3):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        radius = 4 + f * 3
        cx, cy = CW // 2, CH // 2
        colors = [COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_YELLOW]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    _set_pixel(surf, cx + dx, cy + dy, colors[f])
        if f > 0:
            for i in range(4):
                fx = cx + int(math.cos(i * 1.5 + f) * (radius + 2))
                fy = cy + int(math.sin(i * 1.5 + f) * (radius + 2))
                _set_pixel(surf, fx, fy, COLOR_DRONE_BODY)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames  # explosion symmetric

    return sprites


# ============================================================
# WARDEN — Boss livello 1
# Base 40x48, uniform canvas 54x58
# ============================================================

def _draw_warden_base(surf, phase=0, ox=7, oy=10):
    w, h = WARDEN_WIDTH, WARDEN_HEIGHT

    # Stivali pesanti (riga 41-47)
    _draw_rect(surf, 6+ox, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 24+ox, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 6+ox, 47+oy, 10, 1, COLOR_BLACK)
    _draw_rect(surf, 24+ox, 47+oy, 10, 1, COLOR_BLACK)
    # Trim sugli stivali
    _draw_rect(surf, 6+ox, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 24+ox, 41+oy, 10, 1, COLOR_WARDEN_TRIM)

    # Gambali (riga 29-40)
    _draw_rect(surf, 8+ox, 29+oy, 8, 12, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 24+ox, 29+oy, 8, 12, COLOR_WARDEN_ARMOR)
    # Ginocchiere
    _draw_rect(surf, 8+ox, 34+oy, 8, 2, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 24+ox, 34+oy, 8, 2, COLOR_WARDEN_TRIM)
    # Armor seam lines on legs
    _set_pixel(surf, 12+ox, 30+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 33+oy, COLOR_BLACK)
    _set_pixel(surf, 28+ox, 30+oy, COLOR_BLACK)
    _set_pixel(surf, 28+ox, 33+oy, COLOR_BLACK)

    # Cintura tech
    _draw_rect(surf, 7+ox, 27+oy, 26, 2, COLOR_DARK_GRAY)
    _draw_rect(surf, 18+ox, 27+oy, 4, 2, COLOR_NEON_ORANGE)

    # Torso corazzato (riga 12-26)
    _draw_rect(surf, 7+ox, 12+oy, 26, 15, COLOR_WARDEN_ARMOR)
    # Piastra pettorale
    _draw_rect(surf, 9+ox, 13+oy, 22, 10, (50, 55, 70))
    # Seam lines on torso
    _set_pixel(surf, 9+ox, 16+oy, COLOR_BLACK)
    _set_pixel(surf, 30+ox, 16+oy, COLOR_BLACK)
    _set_pixel(surf, 9+ox, 20+oy, COLOR_BLACK)
    _set_pixel(surf, 30+ox, 20+oy, COLOR_BLACK)
    # Linee trim
    _draw_rect(surf, 9+ox, 13+oy, 22, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 9+ox, 22+oy, 22, 1, COLOR_WARDEN_TRIM)

    # Core luminoso: 4x4 with 1px gradient ring
    core_colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_RED_ALARM]
    core_col = core_colors[min(phase, 2)]
    # Gradient ring (dimmer version)
    dim_core = tuple(max(0, c - 80) for c in core_col[:3])
    _draw_rect(surf, 17+ox, 16+oy, 6, 6, dim_core)
    # Inner core 4x4
    _draw_rect(surf, 18+ox, 17+oy, 4, 4, core_col)

    # Shoulder pads extending 2px past body
    _draw_rect(surf, 2+ox, 10+oy, 8, 5, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 30+ox, 10+oy, 8, 5, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 2+ox, 10+oy, 8, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 30+ox, 10+oy, 8, 1, COLOR_WARDEN_TRIM)
    # Shoulder seam
    _set_pixel(surf, 6+ox, 12+oy, COLOR_BLACK)
    _set_pixel(surf, 34+ox, 12+oy, COLOR_BLACK)

    # Braccia
    _draw_rect(surf, 3+ox, 15+oy, 4, 12, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 33+ox, 15+oy, 4, 12, COLOR_WARDEN_ARMOR)
    # Guanti
    _draw_rect(surf, 3+ox, 27+oy, 4, 3, COLOR_DARK_GRAY)
    _draw_rect(surf, 33+ox, 27+oy, 4, 3, COLOR_DARK_GRAY)
    # Glow sui guanti
    _set_pixel(surf, 4+ox, 28+oy, core_col)
    _set_pixel(surf, 34+ox, 28+oy, core_col)

    # Testa / elmo (riga 0-11)
    _draw_rect(surf, 11+ox, 1+oy, 18, 11, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 12+ox, 0+oy, 16, 1, COLOR_WARDEN_ARMOR)
    # Visiera: horizontal scanning line brightest in center
    _draw_rect(surf, 12+ox, 5+oy, 16, 3, COLOR_WARDEN_VISOR)
    # Scanning line - brighter in center
    _set_pixel(surf, 14+ox, 6+oy, (200, 80, 80))
    _set_pixel(surf, 16+ox, 6+oy, (220, 100, 100))
    _draw_rect(surf, 18+ox, 6+oy, 4, 1, (255, 180, 180))  # center brightest
    _set_pixel(surf, 22+ox, 6+oy, (220, 100, 100))
    _set_pixel(surf, 24+ox, 6+oy, (200, 80, 80))
    # Trim elmo
    _draw_rect(surf, 11+ox, 1+oy, 18, 1, COLOR_WARDEN_TRIM)
    # Antenna
    _set_pixel(surf, 19+ox, 0+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 20+ox, 0+oy, COLOR_RED_ALARM)


def generate_warden_sprites():
    sprites = {}
    CW, CH = WARDEN_CANVAS_W, WARDEN_CANVAS_H
    ox = (CW - WARDEN_WIDTH) // 2  # 7
    oy = CH - WARDEN_HEIGHT          # 10

    # IDLE (2 frame)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy)
        if f == 1:
            # Core pulse brighter
            _draw_rect(surf, 18+ox, 17+oy, 4, 4, (0, 240, 255))
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy)
        off = [0, 2, 0, -2][f]
        # Clear feet area and redraw with offset
        _draw_rect(surf, 6+ox, 41+oy, 10, 7, (0, 0, 0, 0))
        _draw_rect(surf, 24+ox, 41+oy, 10, 7, (0, 0, 0, 0))
        _draw_rect(surf, 6+ox + off, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 24+ox - off, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 6+ox + off, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24+ox - off, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 6+ox + off, 47+oy, 10, 1, COLOR_BLACK)
        _draw_rect(surf, 24+ox - off, 47+oy, 10, 1, COLOR_BLACK)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # MELEE ATTACK (2 animations, 2 frames each: strike, follow-through)
    for m_idx in range(2):
        melee_frames = []
        for f in range(2):
            surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
            _draw_warden_base(surf, 0, ox=ox, oy=oy)
            arm_ext = 8 + f * 5 + m_idx * 2
            # Arms extend to the right edge of canvas - absolute position
            arm_start_x = WARDEN_WIDTH - 2 + ox
            _draw_rect(surf, arm_start_x, 17+oy, arm_ext, 4, COLOR_WARDEN_ARMOR)
            _draw_rect(surf, arm_start_x + arm_ext - 3, 16+oy, 6, 6, COLOR_NEON_ORANGE)
            _draw_rect(surf, arm_start_x + arm_ext - 2, 17+oy, 4, 4, COLOR_YELLOW)
            melee_frames.append(surf)
        sprites[f"melee{m_idx}_right"] = melee_frames
        sprites[f"melee{m_idx}_left"] = [_mirror_h(f) for f in melee_frames]

    # SHOCKWAVE (1 frame)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 1, ox=ox, oy=oy)
    for i in range(5):
        wave_w = (i + 1) * 7
        alpha = 255 - i * 45
        for wx in range(-wave_w, wave_w):
            px = CW // 2 + wx
            py = WARDEN_HEIGHT + oy + i
            if 0 <= px < CW and 0 <= py < CH:
                _set_pixel(surf, px, py, (*COLOR_NEON_ORANGE[:3], max(0, alpha)))
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame, arms raised)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 1, ox=ox, oy=oy)
    _draw_rect(surf, 3+ox, 5+oy, 4, 10, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 33+ox, 5+oy, 4, 10, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 2+ox, 4+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 1+ox, 3+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 37+ox, 4+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 38+ox, 3+oy, COLOR_RED_ALARM)
    sprites["spawn_right"] = [surf]
    sprites["spawn_left"] = [_mirror_h(surf)]

    # PHASE 2: crack marks (black pixels breaking armor)
    for anim in ["idle", "walk"]:
        p2_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            # Crack marks on chest
            _set_pixel(surf, 12+ox, 15+oy, COLOR_BLACK)
            _set_pixel(surf, 13+ox, 16+oy, COLOR_BLACK)
            _set_pixel(surf, 14+ox, 17+oy, COLOR_BLACK)
            _set_pixel(surf, 15+ox, 18+oy, COLOR_BLACK)
            _set_pixel(surf, 26+ox, 14+oy, COLOR_BLACK)
            _set_pixel(surf, 27+ox, 15+oy, COLOR_BLACK)
            _set_pixel(surf, 28+ox, 16+oy, COLOR_BLACK)
            # Core orange
            _draw_rect(surf, 18+ox, 17+oy, 4, 4, COLOR_NEON_ORANGE)
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
                _set_pixel(surf, 12+ox + (cy % 4), cy+oy, COLOR_BLACK)
                _set_pixel(surf, 26+ox - (cy % 4), cy+oy, COLOR_BLACK)
            # Damaged shoulder pads
            _draw_rect(surf, 2+ox, 12+oy, 4, 3, COLOR_BLACK)
            _draw_rect(surf, 34+ox, 12+oy, 4, 3, COLOR_BLACK)
            # Exposed wiring (thin colored lines where armor was)
            _set_pixel(surf, 4+ox, 13+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 5+ox, 14+oy, COLOR_GREEN_HACK)
            _set_pixel(surf, 35+ox, 13+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 36+ox, 14+oy, COLOR_NEON_ORANGE)
            # Core red
            _draw_rect(surf, 18+ox, 17+oy, 4, 4, COLOR_RED_ALARM)
            # Red emergency lighting on edges
            _set_pixel(surf, 7+ox, 12+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 32+ox, 12+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 7+ox, 25+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 32+ox, 25+oy, COLOR_RED_ALARM)
            p3_frames.append(surf)
        sprites[f"{anim}_p3_right"] = p3_frames
        sprites[f"{anim}_p3_left"] = [_mirror_h(f) for f in p3_frames]

    # HURT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 0, ox=ox, oy=oy)
    # Apply white flash only where pixels are non-transparent
    for py in range(CH):
        for px in range(CW):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 100)
                ng = min(255, g + 100)
                nb = min(255, b + 100)
                surf.set_at((px, py), (nr, ng, nb, a))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (4 frame, progressive explosion)
    death_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if f < 2:
            _draw_warden_base(surf, 2, ox=ox, oy=oy)
            for i in range(f + 1):
                cx = 14 + i * 10 + ox
                cy = 18 + i * 6 + oy
                for dy in range(-4, 5):
                    for dx in range(-4, 5):
                        if dx * dx + dy * dy <= 16:
                            _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_ORANGE)
        else:
            cx, cy = CW // 2, CH // 2
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
