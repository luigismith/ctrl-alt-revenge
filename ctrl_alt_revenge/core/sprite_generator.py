# core/sprite_generator.py — Pixel-art sprite generator for CTRL+ALT REVENGE!
# Every sprite drawn pixel-by-pixel with proper outlines, shading, and animation
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

# ---------------------------------------------------------------------------
# Extended palette -- 3-4 tone ramps per material, light from top-left
# ---------------------------------------------------------------------------
# Skin ramp (highlight -> base -> shadow -> deep)
COLOR_SKIN_HIGHLIGHT = (230, 190, 150)
COLOR_SKIN_DEEP = (150, 110, 75)

# Jacket brown ramp
COLOR_JACKET_HIGHLIGHT = (200, 140, 65)
COLOR_JACKET_DEEP = (100, 65, 25)

# Hair gray ramp
COLOR_HAIR_GRAY_LIGHT = (185, 180, 175)
COLOR_HAIR_GRAY_DARK = (120, 115, 110)

# Cyber arm
COLOR_CYBER_ARM = (80, 90, 110)
COLOR_CYBER_ARM_HI = (100, 112, 135)
COLOR_CYBER_ARM_SH = (55, 62, 80)
COLOR_CYBER_GLOW = (0, 229, 255)
COLOR_CYBER_GLOW_DIM = (0, 150, 180)
COLOR_CYBER_GLOW_HALO = (0, 120, 150, 120)

# Eye
COLOR_EYE = (200, 220, 255)

# Thug
COLOR_THUG_SHIRT = (60, 20, 20)
COLOR_THUG_SHIRT_SH = (40, 12, 12)
COLOR_THUG_SKIN = (190, 150, 110)
COLOR_THUG_SKIN_HI = (210, 170, 130)
COLOR_THUG_SKIN_SH = (155, 120, 85)
COLOR_THUG_BANDANA = COLOR_RED_ALARM
COLOR_THUG_BANDANA_SH = (180, 30, 55)
COLOR_BRASS = (200, 180, 80)
COLOR_BRASS_HI = (230, 210, 120)

# Drone
COLOR_DRONE_BODY = (70, 75, 90)
COLOR_DRONE_BODY_HI = (95, 100, 118)
COLOR_DRONE_BODY_SH = (45, 50, 65)
COLOR_DRONE_LIGHT = COLOR_RED_ALARM

# Warden
COLOR_WARDEN_ARMOR = (40, 45, 60)
COLOR_WARDEN_ARMOR_HI = (60, 68, 88)
COLOR_WARDEN_ARMOR_SH = (25, 28, 40)
COLOR_WARDEN_VISOR = COLOR_RED_ALARM
COLOR_WARDEN_TRIM = COLOR_NEON_ORANGE

# Pants ramp
COLOR_PANTS_HI = (65, 70, 78)
COLOR_PANTS_SH = (35, 38, 45)

# Boots ramp
COLOR_BOOTS_HI = (145, 100, 55)
COLOR_BOOTS_SOLE = (50, 35, 18)

# Outline color
OUTLINE = (5, 3, 15)

# Uniform canvas sizes for each character type
GIG_CANVAS_W, GIG_CANVAS_H = 34, 32
THUG_CANVAS_W, THUG_CANVAS_H = 32, 32
DRONE_CANVAS_W, DRONE_CANVAS_H = 32, 20
WARDEN_CANVAS_W, WARDEN_CANVAS_H = 54, 58


# ===================================================================
# Helper functions
# ===================================================================

def _set_pixel(surf, x, y, color):
    """Set a single pixel, with bounds checking."""
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)


def _draw_rect(surf, x, y, w, h, color):
    """Filled rectangle."""
    for py in range(y, y + h):
        for px in range(x, x + w):
            _set_pixel(surf, px, py, color)


def _mirror_h(surf):
    """Horizontal mirror."""
    return pygame.transform.flip(surf, True, False)


def _draw_outline(surf, color=None):
    """Draw a 1px outline around all non-transparent pixels.
    This is the single biggest visual improvement -- characters pop
    against any background."""
    if color is None:
        color = OUTLINE
    w, h = surf.get_size()
    # Collect all opaque pixel positions
    opaque = set()
    for py in range(h):
        for px in range(w):
            if surf.get_at((px, py)).a > 30:
                opaque.add((px, py))
    # For every opaque pixel, check 4-connected neighbours
    outline_pixels = set()
    for (px, py) in opaque:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = px + dx, py + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in opaque:
                outline_pixels.add((nx, ny))
    for (px, py) in outline_pixels:
        surf.set_at((px, py), color)


def _draw_outline_thick(surf, color=None):
    """Draw a 2px outline for boss-sized characters."""
    if color is None:
        color = OUTLINE
    w, h = surf.get_size()
    opaque = set()
    for py in range(h):
        for px in range(w):
            if surf.get_at((px, py)).a > 30:
                opaque.add((px, py))
    outline_pixels = set()
    for (px, py) in opaque:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) <= 2:
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in opaque:
                        outline_pixels.add((nx, ny))
    for (px, py) in outline_pixels:
        surf.set_at((px, py), color)


def _dither_rect(surf, x, y, w, h, col_a, col_b):
    """Checkerboard dither between two colours for gradients."""
    for py in range(y, y + h):
        for px in range(x, x + w):
            c = col_a if (px + py) % 2 == 0 else col_b
            _set_pixel(surf, px, py, c)


# ===================================================================
# GIG -- Protagonist
# Base art 24x32 on 34x32 canvas, ox=5 oy=0
# ===================================================================

def _draw_gig_head(surf, ox, oy, bob=0, ponytail_extra=0):
    """Draw GIG's head at given offset with optional vertical bob."""
    b = bob
    # Hair top (2 rows)
    _draw_rect(surf, 7+ox, 0+b+oy, 8, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 10+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 12+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 7+ox, 1+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 14+ox, 1+b+oy, COLOR_HAIR_GRAY_DARK)
    # Ponytail trailing behind (3-4 px)
    pt_b = ponytail_extra
    _set_pixel(surf, 15+ox, 1+b+oy, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16+ox, 2+b+oy+pt_b, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17+ox, 3+b+oy+pt_b, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17+ox, 4+b+oy+pt_b, COLOR_HAIR_GRAY_LIGHT)

    # Face (8 wide, 6 tall)
    _draw_rect(surf, 7+ox, 2+b+oy, 8, 6, COLOR_SKIN)
    # Highlight top-left of forehead
    _set_pixel(surf, 8+ox, 2+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 9+ox, 2+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 10+ox, 2+b+oy, COLOR_SKIN_HIGHLIGHT)
    # Shadow under jaw
    _draw_rect(surf, 7+ox, 7+b+oy, 8, 1, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 7+ox, 6+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 14+ox, 6+b+oy, COLOR_SKIN_SHADOW)

    # Cybernetic LEFT eye: 2px bright cyan with halo
    _set_pixel(surf, 8+ox, 4+b+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 9+ox, 4+b+oy, COLOR_CYBER_GLOW)
    # Halo around cyber eye
    _set_pixel(surf, 7+ox, 4+b+oy, COLOR_CYBER_GLOW_HALO)
    _set_pixel(surf, 8+ox, 3+b+oy, (0, 150, 200, 80))
    _set_pixel(surf, 9+ox, 3+b+oy, (0, 150, 200, 80))
    _set_pixel(surf, 10+ox, 4+b+oy, (0, 150, 200, 100))
    _set_pixel(surf, 8+ox, 5+b+oy, (0, 120, 160, 60))

    # RIGHT eye: dark pixel
    _set_pixel(surf, 12+ox, 4+b+oy, COLOR_EYE)
    _set_pixel(surf, 13+ox, 4+b+oy, COLOR_BLACK)

    # Eyebrows (angry tilt)
    _set_pixel(surf, 8+ox, 3+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 12+ox, 3+b+oy, COLOR_BLACK)
    _set_pixel(surf, 13+ox, 3+b+oy, COLOR_BLACK)

    # Thick beard (darker skin tones)
    _draw_rect(surf, 7+ox, 6+b+oy, 7, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8+ox, 7+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 9+ox, 7+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 10+ox, 7+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 11+ox, 7+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 7+ox, 7+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 13+ox, 7+b+oy, COLOR_HAIR_GRAY_DARK)


def _draw_gig_torso(surf, ox, oy, bob=0):
    """Jacket, shirt, belt, pockets."""
    b = bob
    # Collar
    _draw_rect(surf, 8+ox, 8+b+oy, 6, 1, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 7+ox, 8+b+oy, COLOR_JACKET_BROWN)
    _set_pixel(surf, 14+ox, 8+b+oy, COLOR_JACKET_BROWN)

    # Main jacket torso: 3-tone shading
    # Shadow left edge
    _draw_rect(surf, 5+ox, 9+b+oy, 2, 10, COLOR_JACKET_SHADOW)
    # Deep shadow far left
    _set_pixel(surf, 5+ox, 10+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 5+ox, 11+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 5+ox, 14+b+oy, COLOR_JACKET_DEEP)
    # Base colour mid torso
    _draw_rect(surf, 7+ox, 9+b+oy, 8, 10, COLOR_JACKET_BROWN)
    # Highlight on right shoulder area
    _draw_rect(surf, 15+ox, 9+b+oy, 2, 3, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 14+ox, 9+b+oy, COLOR_JACKET_HIGHLIGHT)
    # Fill right side
    _draw_rect(surf, 15+ox, 12+b+oy, 2, 7, COLOR_JACKET_BROWN)

    # V-neck dark shirt underneath
    _draw_rect(surf, 9+ox, 9+b+oy, 4, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 10+ox, 12+b+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 11+ox, 12+b+oy, COLOR_DARK_GRAY)

    # Chest pocket (2x3 darker rectangle)
    _draw_rect(surf, 13+ox, 13+b+oy, 2, 3, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 13+ox, 13+b+oy, COLOR_JACKET_DEEP)

    # Lapel line (1px darker line down front of jacket)
    for yy in range(9, 18):
        _set_pixel(surf, 8+ox, yy+b+oy, COLOR_JACKET_SHADOW)

    # Belt
    _draw_rect(surf, 5+ox, 19+b+oy, 12, 1, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 19+b+oy, COLOR_NEON_ORANGE)  # buckle
    _set_pixel(surf, 11+ox, 19+b+oy, COLOR_NEON_ORANGE)


def _draw_gig_cyber_arm(surf, ox, oy, bob=0, glow_phase=0):
    """Left arm -- cybernetic with glow segments."""
    b = bob
    # Upper arm (gunmetal gray, 3-tone)
    _draw_rect(surf, 2+ox, 10+b+oy, 3, 7, COLOR_CYBER_ARM)
    _set_pixel(surf, 2+ox, 10+b+oy, COLOR_CYBER_ARM_SH)
    _set_pixel(surf, 2+ox, 11+b+oy, COLOR_CYBER_ARM_SH)
    _set_pixel(surf, 4+ox, 10+b+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 4+ox, 11+b+oy, COLOR_CYBER_ARM_HI)
    # Hand
    _draw_rect(surf, 2+ox, 17+b+oy, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 4+ox, 17+b+oy, COLOR_CYBER_ARM_HI)

    # 4 glow segments alternating bright/dim
    bright = COLOR_CYBER_GLOW
    dim = COLOR_CYBER_GLOW_DIM
    if glow_phase == 1:
        bright, dim = dim, bright  # swap for animation
    _set_pixel(surf, 3+ox, 11+b+oy, bright)
    _set_pixel(surf, 3+ox, 12+b+oy, dim)
    _set_pixel(surf, 3+ox, 13+b+oy, bright)
    _set_pixel(surf, 3+ox, 14+b+oy, dim)
    _set_pixel(surf, 3+ox, 15+b+oy, bright)
    _set_pixel(surf, 3+ox, 16+b+oy, dim)
    # Glow bleed (1px into adjacent areas)
    _set_pixel(surf, 2+ox, 12+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 4+ox, 13+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 2+ox, 14+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 4+ox, 15+b+oy, (0, 80, 100, 80))


def _draw_gig_human_arm(surf, ox, oy, bob=0):
    """Right arm -- jacket sleeve + human hand."""
    b = bob
    # Sleeve -- highlight on shoulder, shadow below
    _draw_rect(surf, 17+ox, 10+b+oy, 3, 7, COLOR_JACKET_BROWN)
    _set_pixel(surf, 17+ox, 10+b+oy, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 18+ox, 10+b+oy, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 17+ox, 15+b+oy, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 17+ox, 16+b+oy, COLOR_JACKET_SHADOW)
    # Hand
    _draw_rect(surf, 17+ox, 17+b+oy, 3, 2, COLOR_SKIN)
    _set_pixel(surf, 17+ox, 17+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 17+ox, 18+b+oy, COLOR_SKIN_SHADOW)


def _draw_gig_legs(surf, ox, oy, l_off=0, r_off=0):
    """Pants + boots with 2-tone shading."""
    # Left leg
    _draw_rect(surf, 5+ox+l_off, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _set_pixel(surf, 5+ox+l_off, 20+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 6+ox+l_off, 20+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 5+ox+l_off, 25+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 5+ox+l_off, 26+oy, COLOR_PANTS_SH)
    # Right leg
    _draw_rect(surf, 13+ox+r_off, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _set_pixel(surf, 16+ox+r_off, 20+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 13+ox+r_off, 25+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 13+ox+r_off, 26+oy, COLOR_PANTS_SH)

    # Left boot
    _draw_rect(surf, 4+ox+l_off, 27+oy, 5, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 5+ox+l_off, 27+oy, COLOR_BOOTS_HI)  # highlight on toe cap
    _set_pixel(surf, 6+ox+l_off, 27+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 4+ox+l_off, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    # Lace detail
    _set_pixel(surf, 5+ox+l_off, 28+oy, COLOR_BLACK)
    _set_pixel(surf, 7+ox+l_off, 28+oy, COLOR_BLACK)

    # Right boot
    _draw_rect(surf, 13+ox+r_off, 27+oy, 5, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 14+ox+r_off, 27+oy, COLOR_BOOTS_HI)
    _set_pixel(surf, 15+ox+r_off, 27+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 13+ox+r_off, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _set_pixel(surf, 14+ox+r_off, 28+oy, COLOR_BLACK)
    _set_pixel(surf, 16+ox+r_off, 28+oy, COLOR_BLACK)


def _draw_gig_base(surf, facing_right=True, ox=5, oy=0, bob=0, glow_phase=0,
                   ponytail_extra=0, l_off=0, r_off=0):
    """Draw complete GIG base frame."""
    _draw_gig_legs(surf, ox, oy, l_off, r_off)
    _draw_gig_torso(surf, ox, oy, bob)
    _draw_gig_cyber_arm(surf, ox, oy, bob, glow_phase)
    _draw_gig_human_arm(surf, ox, oy, bob)
    _draw_gig_head(surf, ox, oy, bob, ponytail_extra)


def generate_gig_sprites():
    """Generate all animation frames for GIG.
    Returns dict {animation_name: [frame1, frame2, ...]}."""
    sprites = {}
    CW, CH = GIG_CANVAS_W, GIG_CANVAS_H
    ox = (CW - PLAYER_WIDTH) // 2  # 5
    oy = CH - PLAYER_HEIGHT         # 0

    # --- IDLE (4 frames) ---
    idle_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        bob = 0
        glow = 0
        pt = 0
        if f == 1:
            bob = 1  # breathing out, body drops 1px
        elif f == 2:
            glow = 1  # cyber arm glow pulse
        elif f == 3:
            pt = 1  # slight weight shift
        _draw_gig_base(surf, ox=ox, oy=oy, bob=bob, glow_phase=glow,
                       ponytail_extra=pt)
        if f == 2:
            # Extra bright glow on pulse frame
            _set_pixel(surf, 3+ox, 11+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 13+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 15+oy, (0, 255, 255))
        _draw_outline(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frames) ---
    run_frames = []
    # (left_leg_x_off, right_leg_x_off)
    leg_strides = [(0, 0), (3, -3), (0, 0), (-3, 3)]
    bobs = [0, -1, 0, -1]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        lo, ro = leg_strides[f]
        bob = bobs[f]
        pt_bob = 1 if f in (1, 3) else 0

        _draw_gig_legs(surf, ox, oy, lo, ro)

        # Torso with bob
        _draw_gig_torso(surf, ox, oy, bob)

        # Arm pump: arms swing opposite to legs
        arm_y_off = 2 if f in (0, 2) else -2
        # Cyber arm (left)
        _draw_rect(surf, 2+ox, 10+bob+oy, 3, 7, COLOR_CYBER_ARM)
        _set_pixel(surf, 4+ox, 10+bob+oy, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 2+ox, 17+bob+oy-arm_y_off, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 3+ox, 11+bob+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 13+bob+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 3+ox, 15+bob+oy, COLOR_CYBER_GLOW)
        # Human arm (right)
        _draw_rect(surf, 17+ox, 10+bob+oy, 3, 7, COLOR_JACKET_BROWN)
        _set_pixel(surf, 17+ox, 10+bob+oy, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 17+ox, 17+bob+oy+arm_y_off, 3, 2, COLOR_SKIN)

        # Head with bob + ponytail bounce
        _draw_gig_head(surf, ox, oy, bob, pt_bob)

        _draw_outline(surf)
        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (2 frames, legs tucked, arms up) ---
    jump_frames = []
    for jf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        # Tucked legs: boots up higher, knees bent
        _draw_rect(surf, 5+ox, 23+oy, 4, 4, COLOR_PANTS_DARK)
        _set_pixel(surf, 5+ox, 23+oy, COLOR_PANTS_HI)
        _draw_rect(surf, 13+ox, 23+oy, 4, 4, COLOR_PANTS_DARK)
        _set_pixel(surf, 16+ox, 23+oy, COLOR_PANTS_HI)
        # Boots underneath bent legs
        _draw_rect(surf, 4+ox, 27+oy, 5, 4, COLOR_BOOTS_BROWN)
        _set_pixel(surf, 5+ox, 27+oy, COLOR_BOOTS_HI)
        _draw_rect(surf, 4+ox, 30+oy, 5, 1, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 13+ox, 27+oy, 5, 4, COLOR_BOOTS_BROWN)
        _set_pixel(surf, 14+ox, 27+oy, COLOR_BOOTS_HI)
        _draw_rect(surf, 13+ox, 30+oy, 5, 1, COLOR_BOOTS_SOLE)

        # Belt
        _draw_rect(surf, 5+ox, 22+oy, 12, 1, COLOR_BLACK)
        _set_pixel(surf, 10+ox, 22+oy, COLOR_NEON_ORANGE)

        # Torso
        _draw_gig_torso(surf, ox, oy, 0)

        # Arms raised
        adj = 0 if jf == 0 else 1
        _draw_rect(surf, 17+ox, 7+oy+adj, 3, 7, COLOR_JACKET_BROWN)
        _set_pixel(surf, 17+ox, 7+oy+adj, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 17+ox, 14+oy+adj, 3, 2, COLOR_SKIN)
        _draw_rect(surf, 2+ox, 7+oy, 3, 7, COLOR_CYBER_ARM)
        _set_pixel(surf, 4+ox, 7+oy, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 2+ox, 14+oy, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 3+ox, 8+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 10+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 3+ox, 12+oy, COLOR_CYBER_GLOW)

        # Head
        _draw_gig_head(surf, ox, oy, 0, 0)
        # Ponytail flows upward in jump
        _set_pixel(surf, 15+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)

        _draw_outline(surf)
        jump_frames.append(surf)
    sprites["jump_right"] = jump_frames
    sprites["jump_left"] = [_mirror_h(f) for f in jump_frames]

    # --- FALL (2 frames, arms wide, coat flutter) ---
    fall_frames = []
    for ff in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_legs(surf, ox, oy, 0, 0)
        _draw_gig_torso(surf, ox, oy, 0)

        # Arms spread wider than normal
        arm_drop = ff
        _draw_rect(surf, 18+ox, 10+oy+arm_drop, 3, 6, COLOR_JACKET_BROWN)
        _set_pixel(surf, 18+ox, 10+oy+arm_drop, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 18+ox, 16+oy+arm_drop, 3, 2, COLOR_SKIN)
        _draw_rect(surf, 1+ox, 10+oy+arm_drop, 3, 6, COLOR_CYBER_ARM)
        _set_pixel(surf, 3+ox, 10+oy+arm_drop, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 1+ox, 16+oy+arm_drop, 3, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 2+ox, 11+oy+arm_drop, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2+ox, 13+oy+arm_drop, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 2+ox, 15+oy+arm_drop, COLOR_CYBER_GLOW)

        # Coat tail flutter (small triangles at jacket bottom)
        _set_pixel(surf, 5+ox, 19+oy, COLOR_JACKET_SHADOW)
        _set_pixel(surf, 16+ox, 19+oy, COLOR_JACKET_SHADOW)
        if ff == 1:
            _set_pixel(surf, 4+ox, 19+oy, COLOR_JACKET_SHADOW)
            _set_pixel(surf, 17+ox, 19+oy, COLOR_JACKET_SHADOW)

        _draw_gig_head(surf, ox, oy, 0, 0)
        # Ponytail streams up
        _set_pixel(surf, 15+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 16+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
        _set_pixel(surf, 17+ox, 1+oy, COLOR_HAIR_GRAY)

        _draw_outline(surf)
        fall_frames.append(surf)
    sprites["fall_right"] = fall_frames
    sprites["fall_left"] = [_mirror_h(f) for f in fall_frames]

    # --- LAND (2 frames, squash then recover) ---
    land_frames = []
    for lf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if lf == 0:
            # Squash: wide stance, compressed body, shifted down
            # Wide feet
            _draw_rect(surf, 2+ox, 28+oy, 6, 4, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 3+ox, 28+oy, COLOR_BOOTS_HI)
            _draw_rect(surf, 2+ox, 31+oy, 6, 1, COLOR_BOOTS_SOLE)
            _draw_rect(surf, 14+ox, 28+oy, 6, 4, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 15+ox, 28+oy, COLOR_BOOTS_HI)
            _draw_rect(surf, 14+ox, 31+oy, 6, 1, COLOR_BOOTS_SOLE)
            # Squat legs
            _draw_rect(surf, 4+ox, 24+oy, 5, 4, COLOR_PANTS_DARK)
            _set_pixel(surf, 4+ox, 24+oy, COLOR_PANTS_HI)
            _draw_rect(surf, 13+ox, 24+oy, 5, 4, COLOR_PANTS_DARK)
            _set_pixel(surf, 17+ox, 24+oy, COLOR_PANTS_HI)
            _draw_rect(surf, 4+ox, 23+oy, 14, 1, COLOR_BLACK)
            # Compressed torso
            _draw_rect(surf, 5+ox, 14+oy, 12, 9, COLOR_JACKET_BROWN)
            _draw_rect(surf, 5+ox, 14+oy, 2, 9, COLOR_JACKET_SHADOW)
            _draw_rect(surf, 15+ox, 14+oy, 2, 3, COLOR_JACKET_HIGHLIGHT)
            _draw_rect(surf, 9+ox, 14+oy, 4, 3, COLOR_DARK_GRAY)
            # Arms hanging low
            _draw_rect(surf, 17+ox, 15+oy, 3, 5, COLOR_JACKET_BROWN)
            _draw_rect(surf, 17+ox, 20+oy, 3, 2, COLOR_SKIN)
            _draw_rect(surf, 2+ox, 15+oy, 3, 5, COLOR_CYBER_ARM)
            _draw_rect(surf, 2+ox, 20+oy, 3, 2, COLOR_CYBER_ARM)
            _set_pixel(surf, 3+ox, 16+oy, COLOR_CYBER_GLOW)
            _set_pixel(surf, 3+ox, 18+oy, COLOR_CYBER_GLOW_DIM)
            # Compressed head
            _draw_gig_head(surf, ox, oy, 6, 0)
        else:
            # Recovery: basically standing but slight bend
            _draw_gig_base(surf, ox=ox, oy=oy)
            # Slight knee bend (shift left leg 1px)
            _draw_rect(surf, 5+ox, 20+oy, 4, 7, (0, 0, 0, 0))
            _draw_rect(surf, 6+ox, 21+oy, 4, 6, COLOR_PANTS_DARK)
            _set_pixel(surf, 6+ox, 21+oy, COLOR_PANTS_HI)
        _draw_outline(surf)
        land_frames.append(surf)
    sprites["land_right"] = land_frames
    sprites["land_left"] = [_mirror_h(f) for f in land_frames]

    # --- WALL SLIDE (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Right arm reaching up to grab wall
    _draw_rect(surf, 18+ox, 5+oy, 3, 10, COLOR_JACKET_BROWN)
    _set_pixel(surf, 18+ox, 5+oy, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 18+ox, 5+oy, 3, 2, COLOR_SKIN)
    _draw_outline(surf)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Compressed down
    _draw_rect(surf, 4+ox, 28+oy, 5, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 5+ox, 28+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 4+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 13+ox, 28+oy, 5, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 14+ox, 28+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 13+ox, 31+oy, 5, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 5+ox, 24+oy, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 13+ox, 24+oy, 4, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 5+ox, 23+oy, 12, 1, COLOR_BLACK)
    # Short torso
    _draw_rect(surf, 5+ox, 16+oy, 12, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5+ox, 16+oy, 2, 7, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 15+ox, 16+oy, 2, 2, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 9+ox, 16+oy, 4, 3, COLOR_DARK_GRAY)
    # Arms
    _draw_rect(surf, 17+ox, 17+oy, 3, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 17+ox, 22+oy, 3, 2, COLOR_SKIN)
    _draw_rect(surf, 2+ox, 17+oy, 3, 5, COLOR_CYBER_ARM)
    _draw_rect(surf, 2+ox, 22+oy, 3, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 3+ox, 18+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 20+oy, COLOR_CYBER_GLOW_DIM)
    # Head shifted down
    _draw_gig_head(surf, ox, oy, 8, 0)
    _draw_outline(surf)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame, body nearly horizontal) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Feet forward
    _draw_rect(surf, 0+ox, 23+oy, 6, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 1+ox, 23+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 0+ox, 26+oy, 6, 1, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 0+ox, 20+oy, 6, 3, COLOR_PANTS_DARK)
    # Body stretched horizontal
    _draw_rect(surf, 5+ox, 18+oy, 14, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 5+ox, 18+oy, 2, 5, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 17+ox, 18+oy, 2, 2, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 8+ox, 18+oy, 4, 3, COLOR_DARK_GRAY)
    # Head at trailing end
    _draw_rect(surf, 18+ox, 14+oy, 8, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 18+ox, 16+oy, 8, 6, COLOR_SKIN)
    _set_pixel(surf, 19+ox, 16+oy, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 18+ox, 20+oy, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 20+ox, 18+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 21+ox, 18+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 23+ox, 18+oy, COLOR_EYE)
    _draw_outline(surf)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 combo moves, 3 frames each) ---
    for combo_idx in range(3):
        punch_frames = []
        arm_extend = 5 + combo_idx * 3
        arm_y = 13 - combo_idx

        # Frame 0: wind-up (arm pulled back, torso turned)
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            # Torso twist: leading shoulder forward (darken left side more)
            _draw_rect(surf, 5+ox, 10+oy, 3, 8, COLOR_JACKET_DEEP)
            # Pull arm back behind body
            _draw_rect(surf, ox, arm_y+oy, 4, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, ox-2, arm_y+oy, 3, 3, COLOR_SKIN)
            _set_pixel(surf, ox-2, arm_y+oy+1, COLOR_SKIN_SHADOW)
        else:
            # Wind-up for final kick -- leg back
            _draw_rect(surf, 4+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 1: strike -- arm extended, impact lines
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            # Extended punch
            _draw_rect(surf, 19+ox, arm_y+oy, arm_extend, 3, COLOR_JACKET_BROWN)
            _set_pixel(surf, 19+ox, arm_y+oy, COLOR_JACKET_HIGHLIGHT)
            # Fist
            _draw_rect(surf, 19+ox+arm_extend-2, arm_y+oy, 3, 3, COLOR_SKIN)
            _set_pixel(surf, 19+ox+arm_extend, arm_y+oy, COLOR_SKIN_HIGHLIGHT)
            # Impact lines: 2-3 bright orange/yellow dots at fist
            _set_pixel(surf, 19+ox+arm_extend+1, arm_y+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 19+ox+arm_extend+1, arm_y+oy+1, COLOR_YELLOW)
            _set_pixel(surf, 19+ox+arm_extend+2, arm_y+oy+1, COLOR_NEON_ORANGE)
            # Motion trail
            trail = (255, 200, 100, 100)
            _set_pixel(surf, 17+ox, arm_y+oy+1, trail)
            _set_pixel(surf, 16+ox, arm_y+oy+1, trail)
        else:
            # Final combo kick
            _draw_rect(surf, 18+ox, 23+oy, arm_extend+3, 3, COLOR_PANTS_DARK)
            _draw_rect(surf, 18+ox+arm_extend+1, 22+oy, 3, 4, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 18+ox+arm_extend+3, 23+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 18+ox+arm_extend+4, 24+oy, COLOR_YELLOW)
            _set_pixel(surf, 18+ox+arm_extend+3, 24+oy, COLOR_NEON_ORANGE)
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 2: recovery
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_base(surf, ox=ox, oy=oy)
        if combo_idx < 2:
            half_ext = arm_extend // 2
            _draw_rect(surf, 19+ox, arm_y+oy, half_ext, 3, COLOR_JACKET_BROWN)
            _draw_rect(surf, 19+ox+half_ext-1, arm_y+oy, 3, 3, COLOR_SKIN)
        else:
            _draw_rect(surf, 18+ox, 23+oy, 4, 3, COLOR_PANTS_DARK)
            _draw_rect(surf, 21+ox, 22+oy, 3, 4, COLOR_BOOTS_BROWN)
        _draw_outline(surf)
        punch_frames.append(surf)

        sprites[f"punch{combo_idx}_right"] = punch_frames
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(f) for f in punch_frames]

    # --- KICK (3 frames) ---
    kick_frames = []
    # Wind-up
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 4+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
    _draw_outline(surf)
    kick_frames.append(surf)
    # Strike
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 18+ox, 21+oy, 8, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 25+ox, 20+oy, 3, 4, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 28+ox, 22+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 29+ox, 21+oy, COLOR_YELLOW)
    _set_pixel(surf, 28+ox, 21+oy, COLOR_NEON_ORANGE)
    _draw_outline(surf)
    kick_frames.append(surf)
    # Recovery
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 18+ox, 22+oy, 4, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 21+ox, 21+oy, 3, 4, COLOR_BOOTS_BROWN)
    _draw_outline(surf)
    kick_frames.append(surf)
    sprites["kick_right"] = kick_frames
    sprites["kick_left"] = [_mirror_h(f) for f in kick_frames]

    # --- PARRY (1 frame, arms crossed, energy shield) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Arms crossed in front
    _draw_rect(surf, 6+ox, 8+oy, 10, 3, COLOR_CYBER_ARM)
    _set_pixel(surf, 6+ox, 8+oy, COLOR_CYBER_ARM_HI)
    _draw_rect(surf, 6+ox, 8+oy, 10, 1, COLOR_CYBER_GLOW)
    # Energy shield line
    for i in range(10):
        _set_pixel(surf, 5+ox, 6+oy+i, COLOR_NEON_BLUE)
        _set_pixel(surf, 4+ox, 7+oy+i, (0, 200, 255, 80))
    _draw_outline(surf)
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame, red flash on body) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Red flash overlay only on torso
    for py in range(9, 19):
        for px in range(5+ox, 17+ox):
            r, g, b, a = surf.get_at((px, py+oy))
            if a > 0:
                nr = min(255, r + 80)
                surf.set_at((px, py+oy), (nr, max(0, g-30), max(0, b-30), a))
    _draw_outline(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame, cyber arm extended with hologram) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    # Cyber arm extended forward
    _draw_rect(surf, 0+ox, 10+oy, 3, 7, COLOR_CYBER_ARM)
    _set_pixel(surf, 2+ox, 10+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 1+ox, 11+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 1+ox, 13+oy, COLOR_CYBER_GLOW)
    # Hologram (green scanline checkerboard)
    for hy in range(5):
        for hx in range(5):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 9+oy+hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 9+oy+hy, (0, 180, 60, 150))
    _draw_outline(surf)
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ===================================================================
# THUG -- Street enforcer
# Base 22x32 on 32x32 canvas, ox=5 oy=0
# ===================================================================

def _draw_thug_base(surf, alert=False, ox=5, oy=0):
    W, H = THUG_WIDTH, THUG_HEIGHT

    # --- Boots (heavy black) ---
    _draw_rect(surf, 3+ox, 27+oy, 6, 5, COLOR_BLACK)
    _set_pixel(surf, 4+ox, 27+oy, (30, 30, 30))  # highlight on toe
    _set_pixel(surf, 5+ox, 27+oy, (30, 30, 30))
    _draw_rect(surf, 3+ox, 31+oy, 6, 1, (15, 12, 10))  # thick sole
    _draw_rect(surf, 13+ox, 27+oy, 6, 5, COLOR_BLACK)
    _set_pixel(surf, 14+ox, 27+oy, (30, 30, 30))
    _set_pixel(surf, 15+ox, 27+oy, (30, 30, 30))
    _draw_rect(surf, 13+ox, 31+oy, 6, 1, (15, 12, 10))

    # --- Pants ---
    _draw_rect(surf, 5+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _set_pixel(surf, 5+ox, 20+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 5+ox, 26+oy, COLOR_PANTS_SH)
    _draw_rect(surf, 13+ox, 20+oy, 4, 7, COLOR_PANTS_DARK)
    _set_pixel(surf, 16+ox, 20+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 13+ox, 26+oy, COLOR_PANTS_SH)
    # Belt
    _draw_rect(surf, 4+ox, 19+oy, 14, 1, COLOR_BLACK)

    # --- Torso: stockier, wider (14px) ---
    body_color = COLOR_RED_ALARM if alert else COLOR_THUG_SHIRT
    body_sh = (180, 30, 55) if alert else COLOR_THUG_SHIRT_SH
    _draw_rect(surf, 3+ox, 9+oy, 16, 10, body_color)
    # Shadow on left side
    _draw_rect(surf, 3+ox, 9+oy, 3, 10, body_sh)
    # Highlight on right shoulder
    _set_pixel(surf, 17+ox, 9+oy, (80, 30, 30) if not alert else (255, 80, 100))
    _set_pixel(surf, 18+ox, 9+oy, (80, 30, 30) if not alert else (255, 80, 100))
    # Tank top neckline (V shape)
    _draw_rect(surf, 7+ox, 9+oy, 8, 2, COLOR_DARK_GRAY)
    _set_pixel(surf, 9+ox, 11+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 10+ox, 11+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 11+ox, 11+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 12+ox, 11+oy, COLOR_DARK_GRAY)
    # Skull X marking
    marking = (100, 50, 50)
    _set_pixel(surf, 9+ox, 13+oy, marking)
    _set_pixel(surf, 12+ox, 13+oy, marking)
    _set_pixel(surf, 10+ox, 14+oy, marking)
    _set_pixel(surf, 11+ox, 14+oy, marking)
    _set_pixel(surf, 9+ox, 15+oy, marking)
    _set_pixel(surf, 12+ox, 15+oy, marking)

    # --- Arms: muscular, shaded skin ---
    # Right arm
    _draw_rect(surf, 19+ox, 10+oy, 3, 7, COLOR_THUG_SKIN)
    _set_pixel(surf, 19+ox, 10+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 21+ox, 11+oy, COLOR_THUG_SKIN_HI)  # bicep bulge
    _set_pixel(surf, 21+ox, 12+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 19+ox, 17+oy, 3, 2, COLOR_THUG_SKIN)
    # Brass knuckles
    _set_pixel(surf, 19+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 20+ox, 17+oy, COLOR_BRASS_HI)
    _set_pixel(surf, 21+ox, 17+oy, COLOR_BRASS)
    # Left arm
    _draw_rect(surf, 0+ox, 10+oy, 3, 7, COLOR_THUG_SKIN)
    _set_pixel(surf, 0+ox, 10+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 0+ox, 11+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 2+ox, 11+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 0+ox, 17+oy, 3, 2, COLOR_THUG_SKIN)
    _set_pixel(surf, 0+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 1+ox, 17+oy, COLOR_BRASS_HI)
    _set_pixel(surf, 2+ox, 17+oy, COLOR_BRASS)

    # --- Head (10 wide, 7 tall) ---
    _draw_rect(surf, 6+ox, 2+oy, 10, 7, COLOR_THUG_SKIN)
    # Skin shading: highlight top-left, shadow lower-right
    _set_pixel(surf, 7+ox, 2+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 8+ox, 2+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 14+ox, 7+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 15+ox, 7+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 15+ox, 8+oy, COLOR_THUG_SKIN_SH)

    # Red bandana with 2px trailing tail
    _draw_rect(surf, 6+ox, 1+oy, 10, 2, COLOR_THUG_BANDANA)
    _set_pixel(surf, 6+ox, 1+oy, COLOR_THUG_BANDANA_SH)
    _set_pixel(surf, 15+ox, 1+oy, COLOR_THUG_BANDANA_SH)
    _set_pixel(surf, 16+ox, 2+oy, COLOR_THUG_BANDANA)   # tail 1
    _set_pixel(surf, 17+ox, 3+oy, COLOR_THUG_BANDANA)   # tail 2
    _set_pixel(surf, 17+ox, 3+oy, COLOR_THUG_BANDANA_SH)

    # Angry V-shaped eyebrows
    _set_pixel(surf, 8+ox, 3+oy, COLOR_BLACK)
    _set_pixel(surf, 9+ox, 3+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 4+oy, COLOR_BLACK)  # brow angles down
    _set_pixel(surf, 12+ox, 4+oy, COLOR_BLACK)  # other brow
    _set_pixel(surf, 13+ox, 3+oy, COLOR_BLACK)
    _set_pixel(surf, 14+ox, 3+oy, COLOR_BLACK)

    # Beady eyes
    _set_pixel(surf, 9+ox, 5+oy, COLOR_BLACK)
    _set_pixel(surf, 13+ox, 5+oy, COLOR_BLACK)

    # Sneer/mouth
    _set_pixel(surf, 9+ox, 7+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 7+oy, COLOR_BLACK)
    _set_pixel(surf, 11+ox, 7+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 7+oy, COLOR_BLACK)


def generate_thug_sprites():
    sprites = {}
    CW, CH = THUG_CANVAS_W, THUG_CANVAS_H
    ox = (CW - THUG_WIDTH) // 2  # 5
    oy = CH - THUG_HEIGHT          # 0

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy)
        if f == 1:
            # Subtle breathing: 1px shoulder rise
            _set_pixel(surf, 8+ox, 8+oy, COLOR_THUG_SHIRT)
            _set_pixel(surf, 13+ox, 8+oy, COLOR_THUG_SHIRT)
        _draw_outline(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames)
    walk_frames = []
    leg_off = [(0, 0), (2, -2), (0, 0), (-2, 2)]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy)
        lo1, lo2 = leg_off[f]
        # Override feet with offset
        _draw_rect(surf, 3+ox+lo1, 27+oy, 6, 5, COLOR_BLACK)
        _set_pixel(surf, 4+ox+lo1, 27+oy, (30, 30, 30))
        _draw_rect(surf, 3+ox+lo1, 31+oy, 6, 1, (15, 12, 10))
        _draw_rect(surf, 13+ox+lo2, 27+oy, 6, 5, COLOR_BLACK)
        _set_pixel(surf, 14+ox+lo2, 27+oy, (30, 30, 30))
        _draw_rect(surf, 13+ox+lo2, 31+oy, 6, 1, (15, 12, 10))
        _draw_outline(surf)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK (3 frames: wind-up, strike, recovery)
    attack_frames = []
    # Wind-up: arm pulled back behind body
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, ox-2, 13+oy, 4, 3, COLOR_THUG_SKIN)
    _set_pixel(surf, ox-2, 13+oy, COLOR_THUG_SKIN_SH)
    _draw_rect(surf, ox-3, 12+oy, 3, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, ox-3, 12+oy, COLOR_BRASS)
    _set_pixel(surf, ox-1, 12+oy, COLOR_BRASS)
    _set_pixel(surf, ox-2, 12+oy, COLOR_BRASS_HI)
    _draw_outline(surf)
    attack_frames.append(surf)
    # Strike: arm extended, brass knuckle flash
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 21+ox, 13+oy, 6, 3, COLOR_THUG_SKIN)
    _set_pixel(surf, 21+ox, 13+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 26+ox, 12+oy, 3, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, 26+ox, 12+oy, COLOR_BRASS)
    _set_pixel(surf, 27+ox, 12+oy, COLOR_BRASS_HI)
    _set_pixel(surf, 28+ox, 12+oy, COLOR_BRASS)
    # Impact flash
    _set_pixel(surf, 29+ox, 13+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 29+ox, 12+oy, COLOR_YELLOW)
    _set_pixel(surf, 28+ox, 11+oy, COLOR_NEON_ORANGE)
    _draw_outline(surf)
    attack_frames.append(surf)
    # Recovery
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    _draw_rect(surf, 21+ox, 13+oy, 3, 3, COLOR_THUG_SKIN)
    _draw_rect(surf, 23+ox, 12+oy, 3, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, 23+ox, 12+oy, COLOR_BRASS)
    _set_pixel(surf, 25+ox, 12+oy, COLOR_BRASS)
    _draw_outline(surf)
    attack_frames.append(surf)
    sprites["attack_right"] = attack_frames
    sprites["attack_left"] = [_mirror_h(f) for f in attack_frames]

    # ALERT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, alert=True, ox=ox, oy=oy)
    # Exclamation mark above head
    _draw_rect(surf, 10+ox, 0+oy, 2, 1, COLOR_RED_ALARM)
    _draw_outline(surf)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    # Red flash on torso area
    for py in range(9+oy, 19+oy):
        for px in range(3+ox, 19+ox):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 100)
                surf.set_at((px, py), (nr, max(0, g-40), max(0, b-40), a))
    _draw_outline(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (2 frames)
    death_frames = []
    # Stagger
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    # Flash red
    for py in range(CH):
        for px in range(CW):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 60)
                surf.set_at((px, py), (nr, max(0, g-20), max(0, b-20), a))
    _draw_outline(surf)
    death_frames.append(surf)
    # On ground
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_rect(surf, 0+ox, 25+oy, 22, 5, COLOR_THUG_SHIRT)
    _draw_rect(surf, 0+ox, 25+oy, 3, 5, COLOR_THUG_SHIRT_SH)
    _draw_rect(surf, 18+ox, 24+oy, 8, 6, COLOR_THUG_SKIN)
    _set_pixel(surf, 19+ox, 24+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 18+ox, 23+oy, 8, 2, COLOR_THUG_BANDANA)
    _set_pixel(surf, 18+ox, 23+oy, COLOR_THUG_BANDANA_SH)
    _draw_outline(surf)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ===================================================================
# DRONE -- Surveillance drone
# Base 24x14 on 32x20 canvas, ox=4 oy=3
# ===================================================================

def _draw_drone_base(surf, propeller_frame=0, eye_bright=True, ox=4, oy=3):
    w, h = DRONE_WIDTH, DRONE_HEIGHT

    # --- Body: aerodynamic shape (rounded front, tapered back) ---
    # Main body block
    _draw_rect(surf, 6+ox, 5+oy, 12, 6, COLOR_DRONE_BODY)
    # Top curve
    _draw_rect(surf, 7+ox, 4+oy, 10, 1, COLOR_DRONE_BODY)
    _set_pixel(surf, 8+ox, 4+oy, COLOR_DRONE_BODY_HI)
    _set_pixel(surf, 9+ox, 4+oy, COLOR_DRONE_BODY_HI)
    # Bottom curve
    _draw_rect(surf, 7+ox, 11+oy, 10, 1, COLOR_DRONE_BODY)
    # Nose cone (rounded front)
    _set_pixel(surf, 5+ox, 6+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 7+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 8+oy, COLOR_DRONE_BODY)
    # Tapered back
    _set_pixel(surf, 18+ox, 6+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 18+ox, 7+oy, COLOR_DRONE_BODY_SH)

    # Highlight on top-left of body (light source)
    _set_pixel(surf, 7+ox, 5+oy, COLOR_DRONE_BODY_HI)
    _set_pixel(surf, 8+ox, 5+oy, COLOR_DRONE_BODY_HI)
    _set_pixel(surf, 9+ox, 5+oy, COLOR_DRONE_BODY_HI)
    # Shadow on bottom-right
    _set_pixel(surf, 16+ox, 10+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 17+ox, 10+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 15+ox, 10+oy, COLOR_DRONE_BODY_SH)

    # Panel lines (1px darker dividers)
    _set_pixel(surf, 10+ox, 5+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 10+ox, 10+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 14+ox, 5+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 14+ox, 10+oy, COLOR_DRONE_BODY_SH)
    for yy in range(5, 11):
        _set_pixel(surf, 10+ox, yy+oy, COLOR_DRONE_BODY_SH)

    # Ventral panel
    _draw_rect(surf, 8+ox, 9+oy, 8, 2, COLOR_MID_GRAY)

    # Thruster glow underneath
    _set_pixel(surf, 9+ox, 12+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 10+ox, 13+oy, (255, 150, 50, 120))
    _set_pixel(surf, 14+ox, 12+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 13+ox, 13+oy, (255, 150, 50, 120))

    # --- Sensor eye: 2x2 with bright core ---
    if eye_bright:
        eye_core = (255, 80, 80)
        eye_surround = (200, 40, 50)
        eye_outer = (150, 20, 30)
    else:
        eye_core = (150, 30, 40)
        eye_surround = (100, 20, 30)
        eye_outer = (60, 10, 15)
    _draw_rect(surf, 11+ox, 6+oy, 2, 2, eye_core)
    _set_pixel(surf, 10+ox, 6+oy, eye_surround)
    _set_pixel(surf, 13+ox, 6+oy, eye_surround)
    _set_pixel(surf, 10+ox, 7+oy, eye_surround)
    _set_pixel(surf, 13+ox, 7+oy, eye_surround)
    _set_pixel(surf, 10+ox, 5+oy, eye_outer)
    _set_pixel(surf, 13+ox, 8+oy, eye_outer)

    # --- Propeller mounts + blur ---
    # Struts connecting to body
    _set_pixel(surf, 3+ox, 4+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 3+ox, 5+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 20+ox, 4+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 20+ox, 5+oy, COLOR_DARK_GRAY)
    # Propeller blur (semi-transparent, shifts by frame)
    if propeller_frame == 0:
        _draw_rect(surf, 0+ox, 2+oy, 7, 1, (160, 165, 180, 100))
        _draw_rect(surf, 1+ox, 3+oy, 5, 1, (160, 165, 180, 60))
        _draw_rect(surf, 17+ox, 2+oy, 7, 1, (160, 165, 180, 100))
        _draw_rect(surf, 18+ox, 3+oy, 5, 1, (160, 165, 180, 60))
    else:
        _draw_rect(surf, 1+ox, 2+oy, 5, 1, (160, 165, 180, 80))
        _draw_rect(surf, 0+ox, 3+oy, 7, 1, (160, 165, 180, 60))
        _draw_rect(surf, 18+ox, 2+oy, 5, 1, (160, 165, 180, 80))
        _draw_rect(surf, 17+ox, 3+oy, 7, 1, (160, 165, 180, 60))

    # Antenna nubs
    _set_pixel(surf, 7+ox, 1+oy, COLOR_NEON_BLUE)
    _set_pixel(surf, 16+ox, 1+oy, COLOR_NEON_BLUE)
    _set_pixel(surf, 7+ox, 0+oy, (0, 150, 180, 150))
    _set_pixel(surf, 16+ox, 0+oy, (0, 150, 180, 150))


def generate_drone_sprites():
    sprites = {}
    CW, CH = DRONE_CANVAS_W, DRONE_CANVAS_H
    ox = (CW - DRONE_WIDTH) // 2   # 4
    oy = 3  # vertically centered to allow laser below

    # FLY (2 frames)
    fly_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_drone_base(surf, f, eye_bright=(f == 0), ox=ox, oy=oy)
        _draw_outline(surf)
        fly_frames.append(surf)
    sprites["fly_right"] = fly_frames
    sprites["fly_left"] = [_mirror_h(f) for f in fly_frames]

    # SHOOT (1 frame with laser beam)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    for i in range(8):
        ly = DRONE_HEIGHT + oy + i
        if ly < CH:
            _set_pixel(surf, 12+ox, ly, COLOR_RED_ALARM)
            _set_pixel(surf, 11+ox, ly, (255, 46, 77, 80))
            _set_pixel(surf, 13+ox, ly, (255, 46, 77, 80))
    _draw_outline(surf)
    sprites["shoot_right"] = [surf]
    sprites["shoot_left"] = [_mirror_h(surf)]

    # HACKED (ally, green glow replaces red eye)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    _draw_rect(surf, 11+ox, 6+oy, 2, 2, COLOR_GREEN_HACK)
    _set_pixel(surf, 10+ox, 6+oy, (0, 200, 80))
    _set_pixel(surf, 13+ox, 6+oy, (0, 200, 80))
    _set_pixel(surf, 10+ox, 7+oy, (0, 200, 80))
    _set_pixel(surf, 13+ox, 7+oy, (0, 200, 80))
    _draw_outline(surf)
    sprites["hacked_right"] = [surf]
    sprites["hacked_left"] = [_mirror_h(surf)]

    # STUNNED (EMP effect -- sparks above)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, eye_bright=False, ox=ox, oy=oy)
    # Electric sparks
    for i in range(3):
        _set_pixel(surf, 6+ox+i*5, 1+oy, COLOR_YELLOW)
        _set_pixel(surf, 7+ox+i*5, 0+oy, COLOR_YELLOW)
    _draw_outline(surf)
    sprites["stunned_right"] = [surf]
    sprites["stunned_left"] = [_mirror_h(surf)]

    # DEATH (3 frames, progressive explosion)
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
            # Debris
            for i in range(4):
                fx = cx + int(math.cos(i * 1.5 + f) * (radius + 2))
                fy = cy + int(math.sin(i * 1.5 + f) * (radius + 2))
                _set_pixel(surf, fx, fy, COLOR_DRONE_BODY)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames  # explosion is symmetric

    return sprites


# ===================================================================
# WARDEN -- Level 1 Boss
# Base 40x48 on 54x58 canvas, ox=7 oy=10
# ===================================================================

def _draw_warden_base(surf, phase=0, ox=7, oy=10):
    w, h = WARDEN_WIDTH, WARDEN_HEIGHT

    # --- Heavy boots (rows 41-47) ---
    _draw_rect(surf, 6+ox, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 7+ox, 41+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 8+ox, 41+oy, COLOR_WARDEN_ARMOR_HI)
    _draw_rect(surf, 6+ox, 47+oy, 10, 1, COLOR_BLACK)
    _draw_rect(surf, 6+ox, 46+oy, 10, 1, (20, 20, 20))  # tread
    _draw_rect(surf, 24+ox, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 25+ox, 41+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 26+ox, 41+oy, COLOR_WARDEN_ARMOR_HI)
    _draw_rect(surf, 24+ox, 47+oy, 10, 1, COLOR_BLACK)
    _draw_rect(surf, 24+ox, 46+oy, 10, 1, (20, 20, 20))
    # Boot trim
    _draw_rect(surf, 6+ox, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 24+ox, 41+oy, 10, 1, COLOR_WARDEN_TRIM)

    # --- Leg armor (rows 29-40) ---
    _draw_rect(surf, 8+ox, 29+oy, 8, 12, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 24+ox, 29+oy, 8, 12, COLOR_WARDEN_ARMOR)
    # Highlight on top-left of each leg
    _set_pixel(surf, 9+ox, 29+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 10+ox, 29+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 25+ox, 29+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 26+ox, 29+oy, COLOR_WARDEN_ARMOR_HI)
    # Shadow on inner legs
    _set_pixel(surf, 15+ox, 32+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 15+ox, 35+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 24+ox, 32+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 24+ox, 35+oy, COLOR_WARDEN_ARMOR_SH)
    # Knee pads
    _draw_rect(surf, 8+ox, 34+oy, 8, 2, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 24+ox, 34+oy, 8, 2, COLOR_WARDEN_TRIM)
    # Seam lines
    _set_pixel(surf, 12+ox, 30+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 33+oy, COLOR_BLACK)
    _set_pixel(surf, 12+ox, 37+oy, COLOR_BLACK)
    _set_pixel(surf, 28+ox, 30+oy, COLOR_BLACK)
    _set_pixel(surf, 28+ox, 33+oy, COLOR_BLACK)
    _set_pixel(surf, 28+ox, 37+oy, COLOR_BLACK)

    # --- Tech belt ---
    _draw_rect(surf, 7+ox, 27+oy, 26, 2, COLOR_DARK_GRAY)
    _draw_rect(surf, 18+ox, 27+oy, 4, 2, COLOR_NEON_ORANGE)

    # --- Armored torso (rows 12-26) ---
    _draw_rect(surf, 7+ox, 12+oy, 26, 15, COLOR_WARDEN_ARMOR)
    # Chest plate (slightly lighter inner)
    _draw_rect(surf, 9+ox, 13+oy, 22, 10, (50, 55, 70))
    # Highlight top-left of chest
    _set_pixel(surf, 9+ox, 13+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 10+ox, 13+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 11+ox, 13+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 9+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
    # Shadow on bottom-right of chest
    _set_pixel(surf, 29+ox, 21+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 30+ox, 21+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 30+ox, 22+oy, COLOR_WARDEN_ARMOR_SH)
    # Horizontal seam lines
    for sx in range(9, 31):
        _set_pixel(surf, sx+ox, 16+oy, COLOR_BLACK)
        _set_pixel(surf, sx+ox, 20+oy, COLOR_BLACK)
    # Trim lines
    _draw_rect(surf, 9+ox, 13+oy, 22, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 9+ox, 22+oy, 22, 1, COLOR_WARDEN_TRIM)

    # --- Energy core: 4x4 with concentric rings ---
    core_colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_RED_ALARM]
    core_col = core_colors[min(phase, 2)]
    dim_core = tuple(max(0, c - 80) for c in core_col[:3])
    outer_core = tuple(max(0, c - 140) for c in core_col[:3])
    # Outer ring (6x6)
    _draw_rect(surf, 17+ox, 16+oy, 6, 6, outer_core)
    # Mid ring (4x4)
    _draw_rect(surf, 18+ox, 17+oy, 4, 4, dim_core)
    # Inner core (2x2)
    _draw_rect(surf, 19+ox, 18+oy, 2, 2, core_col)

    # --- Shoulder pads (extending 3px past body each side) ---
    _draw_rect(surf, 2+ox, 10+oy, 8, 5, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 30+ox, 10+oy, 8, 5, COLOR_WARDEN_ARMOR)
    # Highlight on top
    _draw_rect(surf, 2+ox, 10+oy, 8, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 30+ox, 10+oy, 8, 1, COLOR_WARDEN_TRIM)
    # Shading on shoulder pads
    _set_pixel(surf, 3+ox, 11+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 4+ox, 11+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 31+ox, 11+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 32+ox, 11+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 8+ox, 14+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 36+ox, 14+oy, COLOR_WARDEN_ARMOR_SH)
    # Shoulder seam
    _set_pixel(surf, 6+ox, 12+oy, COLOR_BLACK)
    _set_pixel(surf, 34+ox, 12+oy, COLOR_BLACK)

    # --- Arms ---
    _draw_rect(surf, 3+ox, 15+oy, 4, 12, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 33+ox, 15+oy, 4, 12, COLOR_WARDEN_ARMOR)
    # Arm highlight
    _set_pixel(surf, 4+ox, 15+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 34+ox, 15+oy, COLOR_WARDEN_ARMOR_HI)
    # Arm shadow
    _set_pixel(surf, 3+ox, 25+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 33+ox, 25+oy, COLOR_WARDEN_ARMOR_SH)
    # Gauntlets
    _draw_rect(surf, 3+ox, 27+oy, 4, 3, COLOR_DARK_GRAY)
    _draw_rect(surf, 33+ox, 27+oy, 4, 3, COLOR_DARK_GRAY)
    # Glow accents on knuckles
    _set_pixel(surf, 4+ox, 28+oy, core_col)
    _set_pixel(surf, 5+ox, 29+oy, core_col)
    _set_pixel(surf, 34+ox, 28+oy, core_col)
    _set_pixel(surf, 35+ox, 29+oy, core_col)

    # --- Helmet (rows 0-11) ---
    _draw_rect(surf, 11+ox, 1+oy, 18, 11, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 12+ox, 0+oy, 16, 1, COLOR_WARDEN_ARMOR)
    # Helmet highlight
    _set_pixel(surf, 12+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 13+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 14+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 12+ox, 2+oy, COLOR_WARDEN_ARMOR_HI)
    # Helmet shadow
    _set_pixel(surf, 27+ox, 10+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 28+ox, 10+oy, COLOR_WARDEN_ARMOR_SH)

    # Visor: horizontal red, brightest pixel in center
    _draw_rect(surf, 12+ox, 5+oy, 16, 3, COLOR_WARDEN_VISOR)
    # Gradient: dimmer at edges, brightest at center
    _set_pixel(surf, 12+ox, 6+oy, (180, 30, 50))
    _set_pixel(surf, 13+ox, 6+oy, (190, 50, 60))
    _set_pixel(surf, 14+ox, 6+oy, (200, 70, 80))
    _set_pixel(surf, 15+ox, 6+oy, (210, 90, 90))
    _set_pixel(surf, 16+ox, 6+oy, (220, 110, 110))
    _draw_rect(surf, 17+ox, 6+oy, 6, 1, (255, 200, 200))  # center brightest
    _set_pixel(surf, 23+ox, 6+oy, (220, 110, 110))
    _set_pixel(surf, 24+ox, 6+oy, (210, 90, 90))
    _set_pixel(surf, 25+ox, 6+oy, (200, 70, 80))
    _set_pixel(surf, 26+ox, 6+oy, (190, 50, 60))
    _set_pixel(surf, 27+ox, 6+oy, (180, 30, 50))

    # Helmet trim
    _draw_rect(surf, 11+ox, 1+oy, 18, 1, COLOR_WARDEN_TRIM)
    # Antenna
    _set_pixel(surf, 19+ox, 0+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 20+ox, 0+oy, COLOR_RED_ALARM)


def generate_warden_sprites():
    sprites = {}
    CW, CH = WARDEN_CANVAS_W, WARDEN_CANVAS_H
    ox = (CW - WARDEN_WIDTH) // 2  # 7
    oy = CH - WARDEN_HEIGHT          # 10

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy)
        if f == 1:
            # Core pulse brighter
            _draw_rect(surf, 19+ox, 18+oy, 2, 2, (0, 255, 255))
        _draw_outline_thick(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames)
    walk_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy)
        off = [0, 2, 0, -2][f]
        # Clear default feet and redraw offset
        _draw_rect(surf, 6+ox, 41+oy, 10, 8, (0, 0, 0, 0))
        _draw_rect(surf, 24+ox, 41+oy, 10, 8, (0, 0, 0, 0))
        _draw_rect(surf, 6+ox+off, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 7+ox+off, 41+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 6+ox+off, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 6+ox+off, 47+oy, 10, 1, COLOR_BLACK)
        _draw_rect(surf, 24+ox-off, 41+oy, 10, 7, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 25+ox-off, 41+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 24+ox-off, 41+oy, 10, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24+ox-off, 47+oy, 10, 1, COLOR_BLACK)
        _draw_outline_thick(surf)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # MELEE (2 attacks, 2 frames each)
    for m_idx in range(2):
        melee_frames = []
        for f in range(2):
            surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
            _draw_warden_base(surf, 0, ox=ox, oy=oy)
            arm_ext = 8 + f * 5 + m_idx * 2
            arm_start_x = WARDEN_WIDTH - 2 + ox
            _draw_rect(surf, arm_start_x, 17+oy, arm_ext, 4, COLOR_WARDEN_ARMOR)
            _set_pixel(surf, arm_start_x, 17+oy, COLOR_WARDEN_ARMOR_HI)
            # Impact glow
            _draw_rect(surf, arm_start_x+arm_ext-3, 16+oy, 6, 6, COLOR_NEON_ORANGE)
            _draw_rect(surf, arm_start_x+arm_ext-2, 17+oy, 4, 4, COLOR_YELLOW)
            _draw_outline_thick(surf)
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
    _draw_outline_thick(surf)
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame, arms raised)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 1, ox=ox, oy=oy)
    _draw_rect(surf, 3+ox, 5+oy, 4, 10, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 4+ox, 5+oy, COLOR_WARDEN_ARMOR_HI)
    _draw_rect(surf, 33+ox, 5+oy, 4, 10, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 34+ox, 5+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 2+ox, 4+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 1+ox, 3+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 37+ox, 4+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 38+ox, 3+oy, COLOR_RED_ALARM)
    _draw_outline_thick(surf)
    sprites["spawn_right"] = [surf]
    sprites["spawn_left"] = [_mirror_h(surf)]

    # PHASE 2: crack marks on armor, core turns orange
    for anim in ["idle", "walk"]:
        p2_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            # Crack pattern on chest (diagonal lines of black)
            crack_pts = [
                (12, 15), (13, 16), (14, 17), (15, 18), (14, 19),
                (26, 14), (27, 15), (28, 16), (27, 17),
                (10, 20), (11, 21), (12, 22),
            ]
            for cx, cy in crack_pts:
                _set_pixel(surf, cx+ox, cy+oy, COLOR_BLACK)
            # Core orange
            _draw_rect(surf, 19+ox, 18+oy, 2, 2, COLOR_NEON_ORANGE)
            _draw_rect(surf, 18+ox, 17+oy, 4, 4, (180, 90, 20))
            _draw_rect(surf, 19+ox, 18+oy, 2, 2, COLOR_NEON_ORANGE)
            p2_frames.append(surf)
        sprites[f"{anim}_p2_right"] = p2_frames
        sprites[f"{anim}_p2_left"] = [_mirror_h(f) for f in p2_frames]

    # PHASE 3: heavy damage, exposed wiring, red core
    for anim in ["idle", "walk"]:
        p3_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            # Many cracks across body
            for cy in range(14, 24):
                _set_pixel(surf, 12+ox + (cy % 4), cy+oy, COLOR_BLACK)
                _set_pixel(surf, 26+ox - (cy % 4), cy+oy, COLOR_BLACK)
            # Damaged shoulder pads (holes)
            _draw_rect(surf, 2+ox, 12+oy, 4, 3, COLOR_BLACK)
            _draw_rect(surf, 34+ox, 12+oy, 4, 3, COLOR_BLACK)
            # Exposed wiring (thin colored lines in gaps)
            _set_pixel(surf, 4+ox, 13+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 5+ox, 14+oy, COLOR_GREEN_HACK)
            _set_pixel(surf, 3+ox, 12+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 35+ox, 13+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 36+ox, 14+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 34+ox, 12+oy, COLOR_GREEN_HACK)
            # Core red + emergency glow
            _draw_rect(surf, 17+ox, 16+oy, 6, 6, (60, 10, 15))
            _draw_rect(surf, 18+ox, 17+oy, 4, 4, (180, 30, 40))
            _draw_rect(surf, 19+ox, 18+oy, 2, 2, COLOR_RED_ALARM)
            # Red emergency lighting on edges
            _set_pixel(surf, 7+ox, 12+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 32+ox, 12+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 7+ox, 25+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 32+ox, 25+oy, COLOR_RED_ALARM)
            p3_frames.append(surf)
        sprites[f"{anim}_p3_right"] = p3_frames
        sprites[f"{anim}_p3_left"] = [_mirror_h(f) for f in p3_frames]

    # HURT (white flash applied to existing sprite)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 0, ox=ox, oy=oy)
    for py in range(CH):
        for px in range(CW):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 100)
                ng = min(255, g + 100)
                nb = min(255, b + 100)
                surf.set_at((px, py), (nr, ng, nb, a))
    _draw_outline_thick(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (4 frames, progressive explosion)
    death_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if f < 2:
            _draw_warden_base(surf, 2, ox=ox, oy=oy)
            for i in range(f + 1):
                cx_e = 14 + i * 10 + ox
                cy_e = 18 + i * 6 + oy
                for dy in range(-4, 5):
                    for dx in range(-4, 5):
                        if dx * dx + dy * dy <= 16:
                            _set_pixel(surf, cx_e + dx, cy_e + dy, COLOR_NEON_ORANGE)
            _draw_outline_thick(surf)
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


# ===================================================================
# OBJECTS
# ===================================================================

def generate_camera_sprite():
    """Surveillance camera 12x8."""
    surf = pygame.Surface((12, 8), pygame.SRCALPHA)
    _draw_rect(surf, 2, 0, 2, 3, COLOR_MID_GRAY)     # mount
    _draw_rect(surf, 0, 3, 8, 5, COLOR_DARK_GRAY)      # body
    # Body shading
    _set_pixel(surf, 1, 3, COLOR_MID_GRAY)
    _set_pixel(surf, 2, 3, COLOR_MID_GRAY)
    _draw_rect(surf, 8, 4, 4, 3, COLOR_MID_GRAY)       # lens
    _set_pixel(surf, 8, 4, (80, 75, 110))
    _draw_rect(surf, 10, 5, 2, 1, COLOR_RED_ALARM)      # LED
    _draw_outline(surf)
    return surf


def generate_terminal_sprite():
    """Hackable terminal 16x16 with scanlines and keyboard."""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Monitor frame
    _draw_rect(surf, 2, 1, 12, 10, COLOR_DARK_GRAY)
    _set_pixel(surf, 3, 1, COLOR_MID_GRAY)  # highlight top-left frame
    _set_pixel(surf, 4, 1, COLOR_MID_GRAY)
    # Screen
    _draw_rect(surf, 3, 2, 10, 8, COLOR_BG_NIGHT)
    # Scanlines (alternating bright/dark green rows)
    for row in range(4):
        y = 3 + row * 2
        bright = COLOR_GREEN_HACK
        dark = (0, 180, 60)
        _draw_rect(surf, 4, y, 6 + (row % 2) * 2, 1, bright if row % 2 == 0 else dark)
    # Blinking cursor
    _draw_rect(surf, 4, 8, 2, 1, COLOR_GREEN_HACK)
    _set_pixel(surf, 4, 8, (0, 255, 100))  # brightest pixel in cursor
    # Status light
    _set_pixel(surf, 13, 9, COLOR_GREEN_HACK)
    # Stand
    _draw_rect(surf, 5, 11, 6, 1, COLOR_MID_GRAY)
    # Keyboard tray
    _draw_rect(surf, 3, 12, 10, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 3, 12, COLOR_MID_GRAY)
    # Dot-pattern keys
    for kx in range(4, 13, 2):
        _set_pixel(surf, kx, 13, COLOR_MID_GRAY)
    for kx in range(5, 12, 2):
        _set_pixel(surf, kx, 14, COLOR_MID_GRAY)
    _draw_outline(surf)
    return surf


def generate_door_sprites():
    """Door/gate 16x32, open and closed states."""
    sprites = {}
    # Closed
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 16, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 1, 1, 14, 30, COLOR_MID_GRAY)
    # Panel lines
    for i in range(4):
        _draw_rect(surf, 1, 1 + i * 8, 14, 1, COLOR_DARK_GRAY)
    # Highlight on top-left panels
    _set_pixel(surf, 2, 2, (80, 75, 110))
    _set_pixel(surf, 2, 10, (80, 75, 110))
    _draw_rect(surf, 7, 14, 2, 2, COLOR_RED_ALARM)  # lock indicator
    _draw_outline(surf)
    sprites["closed"] = surf

    # Open
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 4, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 12, 0, 4, 32, COLOR_DARK_GRAY)
    _set_pixel(surf, 1, 1, COLOR_MID_GRAY)
    _set_pixel(surf, 13, 1, COLOR_MID_GRAY)
    _draw_rect(surf, 1, 14, 2, 2, COLOR_GREEN_HACK)
    _draw_rect(surf, 13, 14, 2, 2, COLOR_GREEN_HACK)
    _draw_outline(surf)
    sprites["open"] = surf

    return sprites


def generate_laser_sprite():
    """Drone laser projectile 6x2."""
    surf = pygame.Surface((6, 2), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 6, 2, COLOR_RED_ALARM)
    _draw_rect(surf, 1, 0, 4, 2, (255, 150, 150))
    _draw_rect(surf, 2, 0, 2, 2, (255, 200, 200))  # bright core
    return surf


def generate_emp_sprite():
    """EMP projectile 8x8, blue circle with glow."""
    surf = pygame.Surface((8, 8), pygame.SRCALPHA)
    cx, cy = 4, 4
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            dist = dx * dx + dy * dy
            if dist <= 4:
                _set_pixel(surf, cx + dx, cy + dy, (0, 255, 255))  # bright core
            elif dist <= 9:
                _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_BLUE)
            elif dist <= 16:
                _set_pixel(surf, cx + dx, cy + dy, (0, 229, 255, 80))  # glow halo
    return surf


def generate_heart_sprite(full=True):
    """Heart for HUD, 9x9. Full = bright red with highlight, Empty = gray outline."""
    surf = pygame.Surface((9, 9), pygame.SRCALPHA)

    heart_pixels = [
        (1, 0), (2, 0), (3, 0), (5, 0), (6, 0), (7, 0),
        (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1),
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2),
        (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3),
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        (3, 6), (4, 6), (5, 6),
        (4, 7),
    ]

    if full:
        # Base red fill
        color = COLOR_RED_ALARM
        for px, py in heart_pixels:
            _set_pixel(surf, px, py, color)
        # Shading: darker on bottom-right
        shadow = (180, 30, 55)
        for px, py in heart_pixels:
            if py >= 4 or px >= 6:
                _set_pixel(surf, px, py, shadow)
        # Re-fill center
        for px, py in heart_pixels:
            if 1 <= py <= 3 and 1 <= px <= 6:
                _set_pixel(surf, px, py, color)
        # Highlight top-left (white glint)
        _set_pixel(surf, 1, 1, (255, 180, 190))
        _set_pixel(surf, 2, 1, (255, 140, 160))
        _set_pixel(surf, 1, 2, (255, 120, 140))
    else:
        # Empty heart: dark gray outline only
        outline_color = (40, 35, 60)
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
    """Various particle effect sprites."""
    particles = {}
    # Spark (cross pattern)
    surf = pygame.Surface((3, 3), pygame.SRCALPHA)
    _set_pixel(surf, 1, 0, COLOR_YELLOW)
    _set_pixel(surf, 0, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 1, COLOR_WHITE_UI)  # bright center
    _set_pixel(surf, 2, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 2, COLOR_YELLOW)
    particles["spark"] = surf

    # Hit effect (larger star pattern)
    surf = pygame.Surface((5, 5), pygame.SRCALPHA)
    _set_pixel(surf, 2, 0, COLOR_NEON_ORANGE)
    _set_pixel(surf, 0, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 4, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 4, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 2, COLOR_YELLOW)  # bright center
    _set_pixel(surf, 1, 1, (255, 180, 50, 150))
    _set_pixel(surf, 3, 1, (255, 180, 50, 150))
    _set_pixel(surf, 1, 3, (255, 180, 50, 150))
    _set_pixel(surf, 3, 3, (255, 180, 50, 150))
    particles["hit"] = surf

    # Dust
    surf = pygame.Surface((2, 2), pygame.SRCALPHA)
    surf.fill((200, 200, 200, 100))
    _set_pixel(surf, 0, 0, (220, 220, 220, 130))
    particles["dust"] = surf

    return particles


def generate_all_sprites():
    """Generate all game sprites, returns a global dictionary."""
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
