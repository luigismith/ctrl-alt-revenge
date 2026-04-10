# core/sprite_generator.py — Pixel-art sprite generator for CTRL+ALT REVENGE!
# Every sprite drawn pixel-by-pixel with proper outlines, shading, and animation
# Golden Axe / Cadillacs & Dinosaurs scale: ~48-64px tall characters
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

# Uniform canvas sizes for each character type (doubled from original)
GIG_CANVAS_W, GIG_CANVAS_H = 44, 48
THUG_CANVAS_W, THUG_CANVAS_H = 42, 48
DRONE_CANVAS_W, DRONE_CANVAS_H = 40, 24
WARDEN_CANVAS_W, WARDEN_CANVAS_H = 64, 72


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
    """Draw a 1px outline around all non-transparent pixels."""
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
# Base art 32x48 on 44x48 canvas, ox=6 oy=0
# Head: 12px wide, 12px tall. Torso: 14px wide.
# Cyber arm: 6px wide with glow segments. Legs: 4px wide each.
# Boots with lacing, belt with buckle, ponytail trailing 4-5px.
# ===================================================================

def _draw_gig_head(surf, ox, oy, bob=0, ponytail_extra=0):
    """Draw GIG's head. Head: 12px wide (ox+8..ox+19), 12px tall (rows 0-11)."""
    b = bob
    # --- Hair top (rows 0-2): 12px wide ---
    _draw_rect(surf, 8+ox, 0+b+oy, 12, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 9+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 11+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 13+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 15+ox, 0+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _draw_rect(surf, 8+ox, 2+b+oy, 12, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 8+ox, 2+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 19+ox, 2+b+oy, COLOR_HAIR_GRAY_DARK)

    # --- Ponytail: 4-5px trailing behind head ---
    pt_b = ponytail_extra
    _set_pixel(surf, 20+ox, 1+b+oy, COLOR_HAIR_GRAY)
    _set_pixel(surf, 21+ox, 1+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 21+ox, 2+b+oy+pt_b, COLOR_HAIR_GRAY)
    _set_pixel(surf, 22+ox, 2+b+oy+pt_b, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 22+ox, 3+b+oy+pt_b, COLOR_HAIR_GRAY)
    _set_pixel(surf, 23+ox, 4+b+oy+pt_b, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 23+ox, 5+b+oy+pt_b, COLOR_HAIR_GRAY)
    _set_pixel(surf, 24+ox, 6+b+oy+pt_b, COLOR_HAIR_GRAY_DARK)

    # --- Face (12 wide, 8 tall, rows 3-10) ---
    _draw_rect(surf, 8+ox, 3+b+oy, 12, 8, COLOR_SKIN)
    # Highlight top-left of forehead
    _set_pixel(surf, 9+ox, 3+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 10+ox, 3+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 11+ox, 3+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 12+ox, 3+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 8+ox, 4+b+oy, COLOR_SKIN_HIGHLIGHT)
    _set_pixel(surf, 9+ox, 4+b+oy, COLOR_SKIN_HIGHLIGHT)
    # Shadow right edge and under jaw
    _set_pixel(surf, 19+ox, 7+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 19+ox, 8+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 19+ox, 9+b+oy, COLOR_SKIN_SHADOW)
    _draw_rect(surf, 8+ox, 10+b+oy, 12, 1, COLOR_SKIN_SHADOW)

    # --- Cybernetic LEFT eye: 2x2 bright cyan at (9,5)-(10,6) ---
    _draw_rect(surf, 9+ox, 5+b+oy, 2, 2, COLOR_CYBER_GLOW)
    # Halo around cyber eye
    _set_pixel(surf, 8+ox, 5+b+oy, COLOR_CYBER_GLOW_HALO)
    _set_pixel(surf, 8+ox, 6+b+oy, (0, 120, 160, 60))
    _set_pixel(surf, 9+ox, 4+b+oy, (0, 150, 200, 80))
    _set_pixel(surf, 10+ox, 4+b+oy, (0, 150, 200, 80))
    _set_pixel(surf, 11+ox, 5+b+oy, (0, 150, 200, 100))
    _set_pixel(surf, 11+ox, 6+b+oy, (0, 120, 160, 60))
    _set_pixel(surf, 9+ox, 7+b+oy, (0, 100, 130, 40))
    _set_pixel(surf, 10+ox, 7+b+oy, (0, 100, 130, 40))

    # --- RIGHT eye: 2px wide at (16,5)-(17,5) ---
    _set_pixel(surf, 16+ox, 5+b+oy, COLOR_EYE)
    _set_pixel(surf, 17+ox, 5+b+oy, COLOR_EYE)
    _set_pixel(surf, 17+ox, 6+b+oy, COLOR_BLACK)
    _set_pixel(surf, 16+ox, 6+b+oy, COLOR_BLACK)

    # --- Eyebrows (angry, separate pixels) ---
    _set_pixel(surf, 9+ox, 4+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 10+ox, 4+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 11+ox, 4+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 15+ox, 4+b+oy, COLOR_BLACK)
    _set_pixel(surf, 16+ox, 4+b+oy, COLOR_BLACK)
    _set_pixel(surf, 17+ox, 4+b+oy, COLOR_BLACK)

    # --- Nose hint ---
    _set_pixel(surf, 14+ox, 7+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 14+ox, 8+b+oy, COLOR_SKIN_DEEP)

    # --- Beard: shaped jawline (rows 8-11) with individual strands ---
    # Row 8: beard starts
    _set_pixel(surf, 9+ox, 8+b+oy, COLOR_HAIR_GRAY)
    _draw_rect(surf, 10+ox, 8+b+oy, 7, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 17+ox, 8+b+oy, COLOR_HAIR_GRAY_DARK)
    # Row 9: fuller beard
    _draw_rect(surf, 9+ox, 9+b+oy, 9, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 10+ox, 9+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 12+ox, 9+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 14+ox, 9+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 9+ox, 9+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 17+ox, 9+b+oy, COLOR_HAIR_GRAY_DARK)
    # Row 10: jawline defined
    _draw_rect(surf, 10+ox, 10+b+oy, 7, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 11+ox, 10+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 13+ox, 10+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 10+ox, 10+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 16+ox, 10+b+oy, COLOR_HAIR_GRAY_DARK)
    # Row 11: chin point (narrower, 5px centered)
    _draw_rect(surf, 11+ox, 11+b+oy, 5, 1, COLOR_HAIR_GRAY)
    _set_pixel(surf, 12+ox, 11+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 14+ox, 11+b+oy, COLOR_HAIR_GRAY_LIGHT)
    _set_pixel(surf, 11+ox, 11+b+oy, COLOR_HAIR_GRAY_DARK)
    _set_pixel(surf, 15+ox, 11+b+oy, COLOR_HAIR_GRAY_DARK)


def _draw_gig_torso(surf, ox, oy, bob=0):
    """Jacket, shirt, belt, pockets. Torso spans rows 12-28, 14px wide."""
    b = bob
    # --- Collar: 2px lighter at neckline ---
    _draw_rect(surf, 11+ox, 12+b+oy, 8, 2, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 9+ox, 12+b+oy, COLOR_JACKET_BROWN)
    _set_pixel(surf, 10+ox, 12+b+oy, COLOR_JACKET_BROWN)
    _set_pixel(surf, 19+ox, 12+b+oy, COLOR_JACKET_BROWN)
    _set_pixel(surf, 20+ox, 12+b+oy, COLOR_JACKET_BROWN)

    # --- Main jacket torso: 3-tone shading (rows 14-27) ---
    # Shadow left edge (3px)
    _draw_rect(surf, 7+ox, 14+b+oy, 3, 14, COLOR_JACKET_SHADOW)
    # Deep shadow accents
    _set_pixel(surf, 7+ox, 15+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 7+ox, 17+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 7+ox, 20+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 7+ox, 23+b+oy, COLOR_JACKET_DEEP)
    # Base colour mid torso
    _draw_rect(surf, 10+ox, 14+b+oy, 11, 14, COLOR_JACKET_BROWN)
    # Highlight on right shoulder area
    _draw_rect(surf, 21+ox, 14+b+oy, 3, 4, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 20+ox, 14+b+oy, COLOR_JACKET_HIGHLIGHT)
    # Fill right side
    _draw_rect(surf, 21+ox, 18+b+oy, 3, 10, COLOR_JACKET_BROWN)

    # V-neck dark shirt underneath
    _draw_rect(surf, 12+ox, 14+b+oy, 6, 4, COLOR_DARK_GRAY)
    _set_pixel(surf, 14+ox, 18+b+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 15+ox, 18+b+oy, COLOR_DARK_GRAY)

    # Chest pocket (3x4 darker rectangle)
    _draw_rect(surf, 18+ox, 18+b+oy, 3, 4, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 18+ox, 18+b+oy, COLOR_JACKET_DEEP)
    _set_pixel(surf, 18+ox, 19+b+oy, COLOR_JACKET_DEEP)

    # Lapel lines (2px darker line down front of jacket)
    for yy in range(14, 26):
        _set_pixel(surf, 11+ox, yy+b+oy, COLOR_JACKET_SHADOW)
        _set_pixel(surf, 12+ox, yy+b+oy, COLOR_JACKET_SHADOW)

    # --- Belt with buckle (3px wide orange/metal) ---
    _draw_rect(surf, 7+ox, 28+b+oy, 18, 1, COLOR_BLACK)
    _set_pixel(surf, 14+ox, 28+b+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 15+ox, 28+b+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 16+ox, 28+b+oy, COLOR_NEON_ORANGE)


def _draw_gig_cyber_arm(surf, ox, oy, bob=0, glow_phase=0):
    """Left arm -- cybernetic, 6px wide with glow segments, each 2px wide."""
    b = bob
    # Upper arm (gunmetal gray, 6px wide, 3-tone)
    _draw_rect(surf, 1+ox, 14+b+oy, 6, 10, COLOR_CYBER_ARM)
    # Highlight on top-right
    _set_pixel(surf, 6+ox, 14+b+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 6+ox, 15+b+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 5+ox, 14+b+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 5+ox, 15+b+oy, COLOR_CYBER_ARM_HI)
    # Shadow on bottom-left
    _set_pixel(surf, 1+ox, 22+b+oy, COLOR_CYBER_ARM_SH)
    _set_pixel(surf, 1+ox, 23+b+oy, COLOR_CYBER_ARM_SH)
    _set_pixel(surf, 2+ox, 23+b+oy, COLOR_CYBER_ARM_SH)
    # Hand (fist shape, 6px wide)
    _draw_rect(surf, 1+ox, 24+b+oy, 6, 3, COLOR_CYBER_ARM)
    _set_pixel(surf, 6+ox, 24+b+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 5+ox, 24+b+oy, COLOR_CYBER_ARM_HI)

    # 6 glow segments along center column, each 2px wide, alternating
    bright = COLOR_CYBER_GLOW
    dim = COLOR_CYBER_GLOW_DIM
    if glow_phase == 1:
        bright, dim = dim, bright
    for i, col in enumerate([bright, dim, bright, dim, bright, dim]):
        _set_pixel(surf, 3+ox, 15+i+b+oy, col)
        _set_pixel(surf, 4+ox, 15+i+b+oy, col)
    # Glow bleed (soft halo on sides)
    _set_pixel(surf, 2+ox, 16+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 5+ox, 17+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 2+ox, 18+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 5+ox, 19+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 2+ox, 20+b+oy, (0, 80, 100, 80))
    _set_pixel(surf, 5+ox, 21+b+oy, (0, 80, 100, 80))


def _draw_gig_human_arm(surf, ox, oy, bob=0):
    """Right arm -- jacket sleeve + human hand, 4px wide."""
    b = bob
    # Sleeve
    _draw_rect(surf, 24+ox, 14+b+oy, 4, 10, COLOR_JACKET_BROWN)
    _set_pixel(surf, 24+ox, 14+b+oy, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 25+ox, 14+b+oy, COLOR_JACKET_HIGHLIGHT)
    _set_pixel(surf, 24+ox, 22+b+oy, COLOR_JACKET_SHADOW)
    _set_pixel(surf, 24+ox, 23+b+oy, COLOR_JACKET_SHADOW)
    # Hand
    _draw_rect(surf, 24+ox, 24+b+oy, 4, 3, COLOR_SKIN)
    _set_pixel(surf, 24+ox, 24+b+oy, COLOR_SKIN_SHADOW)
    _set_pixel(surf, 24+ox, 25+b+oy, COLOR_SKIN_SHADOW)


def _draw_gig_left_leg(surf, ox, oy, l_off=0):
    """Draw GIG's left leg (pants + boot)."""
    _draw_rect(surf, 8+ox+l_off, 29+oy, 4, 10, COLOR_PANTS_DARK)
    _set_pixel(surf, 8+ox+l_off, 29+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 9+ox+l_off, 29+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 8+ox+l_off, 37+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 8+ox+l_off, 38+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 9+ox+l_off, 34+oy, COLOR_PANTS_HI)
    # Left boot
    _draw_rect(surf, 7+ox+l_off, 39+oy, 5, 7, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 8+ox+l_off, 39+oy, COLOR_BOOTS_HI)
    _set_pixel(surf, 9+ox+l_off, 39+oy, COLOR_BOOTS_HI)
    _set_pixel(surf, 10+ox+l_off, 39+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 7+ox+l_off, 46+oy, 5, 2, COLOR_BOOTS_SOLE)
    _set_pixel(surf, 9+ox+l_off, 40+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox+l_off, 41+oy, COLOR_BLACK)
    _set_pixel(surf, 9+ox+l_off, 42+oy, COLOR_BLACK)


def _draw_gig_right_leg(surf, ox, oy, r_off=0):
    """Draw GIG's right leg (pants + boot)."""
    _draw_rect(surf, 18+ox+r_off, 29+oy, 4, 10, COLOR_PANTS_DARK)
    _set_pixel(surf, 21+ox+r_off, 29+oy, COLOR_PANTS_HI)
    _set_pixel(surf, 18+ox+r_off, 37+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 18+ox+r_off, 38+oy, COLOR_PANTS_SH)
    _set_pixel(surf, 20+ox+r_off, 34+oy, COLOR_PANTS_HI)
    # Right boot
    _draw_rect(surf, 18+ox+r_off, 39+oy, 5, 7, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 19+ox+r_off, 39+oy, COLOR_BOOTS_HI)
    _set_pixel(surf, 20+ox+r_off, 39+oy, COLOR_BOOTS_HI)
    _set_pixel(surf, 21+ox+r_off, 39+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 18+ox+r_off, 46+oy, 5, 2, COLOR_BOOTS_SOLE)
    _set_pixel(surf, 20+ox+r_off, 40+oy, COLOR_BLACK)
    _set_pixel(surf, 19+ox+r_off, 41+oy, COLOR_BLACK)
    _set_pixel(surf, 20+ox+r_off, 42+oy, COLOR_BLACK)


def _draw_gig_legs(surf, ox, oy, l_off=0, r_off=0):
    """Pants + boots with 2-tone shading. Each leg 4px wide, boots 5px wide with sole."""
    _draw_gig_left_leg(surf, ox, oy, l_off)
    _draw_gig_right_leg(surf, ox, oy, r_off)


def _draw_gig_base(surf, facing_right=True, ox=6, oy=0, bob=0, glow_phase=0,
                   ponytail_extra=0, l_off=0, r_off=0,
                   skip_right_arm=False, skip_left_arm=False,
                   skip_legs=False, skip_right_leg=False, skip_left_leg=False):
    """Draw complete GIG base frame. Use skip flags to omit body parts
    that will be redrawn in a different pose by animation frames."""
    if not skip_legs:
        if skip_left_leg:
            # Draw only right leg
            _draw_gig_right_leg(surf, ox, oy, r_off)
        elif skip_right_leg:
            # Draw only left leg
            _draw_gig_left_leg(surf, ox, oy, l_off)
        else:
            _draw_gig_legs(surf, ox, oy, l_off, r_off)
    _draw_gig_torso(surf, ox, oy, bob)
    if not skip_left_arm:
        _draw_gig_cyber_arm(surf, ox, oy, bob, glow_phase)
    if not skip_right_arm:
        _draw_gig_human_arm(surf, ox, oy, bob)
    _draw_gig_head(surf, ox, oy, bob, ponytail_extra)


def generate_gig_sprites():
    """Generate all animation frames for GIG."""
    sprites = {}
    CW, CH = GIG_CANVAS_W, GIG_CANVAS_H
    ox = (CW - PLAYER_WIDTH) // 2  # 6
    oy = CH - PLAYER_HEIGHT         # 0

    # --- IDLE (4 frames) ---
    idle_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        bob = 0
        glow = 0
        pt = 0
        if f == 1:
            bob = 1
        elif f == 2:
            glow = 1
        elif f == 3:
            pt = 1
        _draw_gig_base(surf, ox=ox, oy=oy, bob=bob, glow_phase=glow,
                       ponytail_extra=pt)
        if f == 2:
            _set_pixel(surf, 3+ox, 15+oy, (0, 255, 255))
            _set_pixel(surf, 4+ox, 15+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 17+oy, (0, 255, 255))
            _set_pixel(surf, 4+ox, 17+oy, (0, 255, 255))
            _set_pixel(surf, 3+ox, 19+oy, (0, 255, 255))
            _set_pixel(surf, 4+ox, 19+oy, (0, 255, 255))
        _draw_outline(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frames) ---
    run_frames = []
    leg_strides = [(0, 0), (4, -4), (0, 0), (-4, 4)]
    bobs = [0, -1, 0, -1]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        lo, ro = leg_strides[f]
        bob = bobs[f]
        pt_bob = 1 if f in (1, 3) else 0

        _draw_gig_legs(surf, ox, oy, lo, ro)
        _draw_gig_torso(surf, ox, oy, bob)

        # Arm pump
        arm_y_off = 3 if f in (0, 2) else -3
        # Cyber arm (left, 6px wide)
        _draw_rect(surf, 1+ox, 14+bob+oy, 6, 10, COLOR_CYBER_ARM)
        _set_pixel(surf, 6+ox, 14+bob+oy, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 1+ox, 24+bob+oy-arm_y_off, 6, 3, COLOR_CYBER_ARM)
        _set_pixel(surf, 3+ox, 15+bob+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 4+ox, 15+bob+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 17+bob+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 4+ox, 17+bob+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 3+ox, 19+bob+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 4+ox, 19+bob+oy, COLOR_CYBER_GLOW)
        # Human arm (right)
        _draw_rect(surf, 24+ox, 14+bob+oy, 4, 10, COLOR_JACKET_BROWN)
        _set_pixel(surf, 24+ox, 14+bob+oy, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 24+ox, 24+bob+oy+arm_y_off, 4, 3, COLOR_SKIN)

        _draw_gig_head(surf, ox, oy, bob, pt_bob)
        _draw_outline(surf)
        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (2 frames) ---
    jump_frames = []
    for jf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        # Tucked legs
        _draw_rect(surf, 8+ox, 33+oy, 4, 6, COLOR_PANTS_DARK)
        _set_pixel(surf, 8+ox, 33+oy, COLOR_PANTS_HI)
        _draw_rect(surf, 18+ox, 33+oy, 4, 6, COLOR_PANTS_DARK)
        _set_pixel(surf, 21+ox, 33+oy, COLOR_PANTS_HI)
        # Boots
        _draw_rect(surf, 7+ox, 39+oy, 5, 5, COLOR_BOOTS_BROWN)
        _set_pixel(surf, 8+ox, 39+oy, COLOR_BOOTS_HI)
        _draw_rect(surf, 7+ox, 44+oy, 5, 2, COLOR_BOOTS_SOLE)
        _draw_rect(surf, 18+ox, 39+oy, 5, 5, COLOR_BOOTS_BROWN)
        _set_pixel(surf, 19+ox, 39+oy, COLOR_BOOTS_HI)
        _draw_rect(surf, 18+ox, 44+oy, 5, 2, COLOR_BOOTS_SOLE)

        # Belt
        _draw_rect(surf, 7+ox, 32+oy, 18, 1, COLOR_BLACK)
        _set_pixel(surf, 14+ox, 32+oy, COLOR_NEON_ORANGE)
        _set_pixel(surf, 15+ox, 32+oy, COLOR_NEON_ORANGE)

        _draw_gig_torso(surf, ox, oy, 0)

        # Arms raised
        adj = 0 if jf == 0 else 1
        _draw_rect(surf, 24+ox, 9+oy+adj, 4, 10, COLOR_JACKET_BROWN)
        _set_pixel(surf, 24+ox, 9+oy+adj, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 24+ox, 19+oy+adj, 4, 3, COLOR_SKIN)
        _draw_rect(surf, 1+ox, 9+oy, 6, 10, COLOR_CYBER_ARM)
        _set_pixel(surf, 6+ox, 9+oy, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 1+ox, 19+oy, 6, 3, COLOR_CYBER_ARM)
        _set_pixel(surf, 3+ox, 10+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 4+ox, 10+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 12+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 4+ox, 12+oy, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 3+ox, 14+oy, COLOR_CYBER_GLOW)
        _set_pixel(surf, 4+ox, 14+oy, COLOR_CYBER_GLOW)

        _draw_gig_head(surf, ox, oy, 0, 0)
        # Ponytail flows upward
        _set_pixel(surf, 20+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 21+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)

        _draw_outline(surf)
        jump_frames.append(surf)
    sprites["jump_right"] = jump_frames
    sprites["jump_left"] = [_mirror_h(f) for f in jump_frames]

    # --- FALL (2 frames) ---
    fall_frames = []
    for ff in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_gig_legs(surf, ox, oy, 0, 0)
        _draw_gig_torso(surf, ox, oy, 0)

        arm_drop = ff
        _draw_rect(surf, 25+ox, 14+oy+arm_drop, 4, 9, COLOR_JACKET_BROWN)
        _set_pixel(surf, 25+ox, 14+oy+arm_drop, COLOR_JACKET_HIGHLIGHT)
        _draw_rect(surf, 25+ox, 23+oy+arm_drop, 4, 3, COLOR_SKIN)
        _draw_rect(surf, 0+ox, 14+oy+arm_drop, 6, 9, COLOR_CYBER_ARM)
        _set_pixel(surf, 5+ox, 14+oy+arm_drop, COLOR_CYBER_ARM_HI)
        _draw_rect(surf, 0+ox, 23+oy+arm_drop, 6, 3, COLOR_CYBER_ARM)
        _set_pixel(surf, 2+ox, 15+oy+arm_drop, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 15+oy+arm_drop, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2+ox, 17+oy+arm_drop, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 3+ox, 17+oy+arm_drop, COLOR_CYBER_GLOW_DIM)
        _set_pixel(surf, 2+ox, 19+oy+arm_drop, COLOR_CYBER_GLOW)
        _set_pixel(surf, 3+ox, 19+oy+arm_drop, COLOR_CYBER_GLOW)

        # Coat tail flutter
        _set_pixel(surf, 7+ox, 27+oy, COLOR_JACKET_SHADOW)
        _set_pixel(surf, 22+ox, 27+oy, COLOR_JACKET_SHADOW)
        if ff == 1:
            _set_pixel(surf, 6+ox, 27+oy, COLOR_JACKET_SHADOW)
            _set_pixel(surf, 23+ox, 27+oy, COLOR_JACKET_SHADOW)

        _draw_gig_head(surf, ox, oy, 0, 0)
        _set_pixel(surf, 20+ox, 0+oy, COLOR_HAIR_GRAY)
        _set_pixel(surf, 21+ox, 0+oy, COLOR_HAIR_GRAY_LIGHT)
        _set_pixel(surf, 22+ox, 1+oy, COLOR_HAIR_GRAY)

        _draw_outline(surf)
        fall_frames.append(surf)
    sprites["fall_right"] = fall_frames
    sprites["fall_left"] = [_mirror_h(f) for f in fall_frames]

    # --- LAND (2 frames) ---
    land_frames = []
    for lf in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if lf == 0:
            # Squash: wide stance
            _draw_rect(surf, 4+ox, 41+oy, 6, 5, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 5+ox, 41+oy, COLOR_BOOTS_HI)
            _draw_rect(surf, 4+ox, 46+oy, 6, 2, COLOR_BOOTS_SOLE)
            _draw_rect(surf, 20+ox, 41+oy, 6, 5, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 21+ox, 41+oy, COLOR_BOOTS_HI)
            _draw_rect(surf, 20+ox, 46+oy, 6, 2, COLOR_BOOTS_SOLE)
            # Squat legs
            _draw_rect(surf, 7+ox, 35+oy, 4, 6, COLOR_PANTS_DARK)
            _set_pixel(surf, 7+ox, 35+oy, COLOR_PANTS_HI)
            _draw_rect(surf, 19+ox, 35+oy, 4, 6, COLOR_PANTS_DARK)
            _set_pixel(surf, 22+ox, 35+oy, COLOR_PANTS_HI)
            _draw_rect(surf, 5+ox, 34+oy, 20, 1, COLOR_BLACK)
            # Compressed torso
            _draw_rect(surf, 7+ox, 20+oy, 18, 14, COLOR_JACKET_BROWN)
            _draw_rect(surf, 7+ox, 20+oy, 3, 14, COLOR_JACKET_SHADOW)
            _draw_rect(surf, 22+ox, 20+oy, 3, 4, COLOR_JACKET_HIGHLIGHT)
            _draw_rect(surf, 12+ox, 20+oy, 6, 4, COLOR_DARK_GRAY)
            # Arms hanging
            _draw_rect(surf, 24+ox, 22+oy, 4, 8, COLOR_JACKET_BROWN)
            _draw_rect(surf, 24+ox, 30+oy, 4, 3, COLOR_SKIN)
            _draw_rect(surf, 1+ox, 22+oy, 6, 8, COLOR_CYBER_ARM)
            _draw_rect(surf, 1+ox, 30+oy, 6, 3, COLOR_CYBER_ARM)
            _set_pixel(surf, 3+ox, 23+oy, COLOR_CYBER_GLOW)
            _set_pixel(surf, 4+ox, 23+oy, COLOR_CYBER_GLOW)
            _set_pixel(surf, 3+ox, 25+oy, COLOR_CYBER_GLOW_DIM)
            _set_pixel(surf, 4+ox, 25+oy, COLOR_CYBER_GLOW_DIM)
            _draw_gig_head(surf, ox, oy, 8, 0)
        else:
            _draw_gig_base(surf, ox=ox, oy=oy, skip_left_leg=True)
            # Slight knee bend on left leg
            _draw_rect(surf, 9+ox, 30+oy, 4, 9, COLOR_PANTS_DARK)
            _set_pixel(surf, 9+ox, 30+oy, COLOR_PANTS_HI)
            # Left boot shifted
            _draw_rect(surf, 8+ox, 39+oy, 5, 7, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 9+ox, 39+oy, COLOR_BOOTS_HI)
            _set_pixel(surf, 10+ox, 39+oy, COLOR_BOOTS_HI)
            _set_pixel(surf, 11+ox, 39+oy, COLOR_BOOTS_HI)
            _draw_rect(surf, 8+ox, 46+oy, 5, 2, COLOR_BOOTS_SOLE)
        _draw_outline(surf)
        land_frames.append(surf)
    sprites["land_right"] = land_frames
    sprites["land_left"] = [_mirror_h(f) for f in land_frames]

    # --- WALL SLIDE (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_right_arm=True)
    # Right arm reaching up to grip wall
    _draw_rect(surf, 25+ox, 6+oy, 4, 14, COLOR_JACKET_BROWN)
    _set_pixel(surf, 25+ox, 6+oy, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 25+ox, 6+oy, 4, 3, COLOR_SKIN)
    _draw_outline(surf)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_rect(surf, 7+ox, 41+oy, 5, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 8+ox, 41+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 7+ox, 46+oy, 5, 2, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 18+ox, 41+oy, 5, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 19+ox, 41+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 18+ox, 46+oy, 5, 2, COLOR_BOOTS_SOLE)
    # Legs
    _draw_rect(surf, 8+ox, 35+oy, 4, 6, COLOR_PANTS_DARK)
    _draw_rect(surf, 18+ox, 35+oy, 4, 6, COLOR_PANTS_DARK)
    _draw_rect(surf, 7+ox, 34+oy, 18, 1, COLOR_BLACK)
    # Torso
    _draw_rect(surf, 7+ox, 22+oy, 18, 12, COLOR_JACKET_BROWN)
    _draw_rect(surf, 7+ox, 22+oy, 3, 12, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 22+ox, 22+oy, 3, 3, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 12+ox, 22+oy, 6, 4, COLOR_DARK_GRAY)
    # Arms
    _draw_rect(surf, 24+ox, 24+oy, 4, 8, COLOR_JACKET_BROWN)
    _draw_rect(surf, 24+ox, 32+oy, 4, 3, COLOR_SKIN)
    _draw_rect(surf, 1+ox, 24+oy, 6, 8, COLOR_CYBER_ARM)
    _draw_rect(surf, 1+ox, 32+oy, 6, 3, COLOR_CYBER_ARM)
    _set_pixel(surf, 3+ox, 25+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 4+ox, 25+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 27+oy, COLOR_CYBER_GLOW_DIM)
    _set_pixel(surf, 4+ox, 27+oy, COLOR_CYBER_GLOW_DIM)
    # Head
    _draw_gig_head(surf, ox, oy, 10, 0)
    _draw_outline(surf)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame, body nearly horizontal) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Feet forward
    _draw_rect(surf, 0+ox, 33+oy, 6, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 1+ox, 33+oy, COLOR_BOOTS_HI)
    _draw_rect(surf, 0+ox, 38+oy, 6, 2, COLOR_BOOTS_SOLE)
    _draw_rect(surf, 0+ox, 29+oy, 6, 4, COLOR_PANTS_DARK)
    # Body horizontal
    _draw_rect(surf, 6+ox, 26+oy, 20, 7, COLOR_JACKET_BROWN)
    _draw_rect(surf, 6+ox, 26+oy, 3, 7, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 24+ox, 26+oy, 2, 3, COLOR_JACKET_HIGHLIGHT)
    _draw_rect(surf, 10+ox, 26+oy, 6, 4, COLOR_DARK_GRAY)
    # Head at trailing end
    _draw_rect(surf, 25+ox, 20+oy, 10, 3, COLOR_HAIR_GRAY)
    _draw_rect(surf, 25+ox, 23+oy, 10, 8, COLOR_SKIN)
    _set_pixel(surf, 26+ox, 23+oy, COLOR_SKIN_HIGHLIGHT)
    _draw_rect(surf, 25+ox, 29+oy, 8, 3, COLOR_HAIR_GRAY)
    _set_pixel(surf, 27+ox, 25+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 28+ox, 25+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 31+ox, 25+oy, COLOR_EYE)
    _set_pixel(surf, 32+ox, 25+oy, COLOR_EYE)
    _draw_outline(surf)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 combo moves, 3 frames each) ---
    for combo_idx in range(3):
        punch_frames = []
        arm_extend = 7 + combo_idx * 4
        arm_y = 18 - combo_idx * 2

        # Frame 0: wind-up
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if combo_idx < 2:
            # Punch wind-up: skip right arm (will draw pulled back)
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_arm=True)
            # Right arm pulled back behind body
            _draw_rect(surf, ox, arm_y+oy, 6, 4, COLOR_JACKET_BROWN)
            _draw_rect(surf, ox-3, arm_y+oy, 4, 4, COLOR_SKIN)
            _set_pixel(surf, ox-3, arm_y+oy+1, COLOR_SKIN_SHADOW)
        else:
            # Kick wind-up: skip right leg
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
            # Right leg pulled back
            _draw_rect(surf, 5+ox, 30+oy, 12, 4, COLOR_PANTS_DARK)
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 1: strike
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if combo_idx < 2:
            # Punch strike: skip right arm (will draw extended forward)
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_arm=True)
            _draw_rect(surf, 26+ox, arm_y+oy, arm_extend, 4, COLOR_JACKET_BROWN)
            _set_pixel(surf, 26+ox, arm_y+oy, COLOR_JACKET_HIGHLIGHT)
            _draw_rect(surf, 26+ox+arm_extend-3, arm_y+oy, 4, 4, COLOR_SKIN)
            _set_pixel(surf, 26+ox+arm_extend, arm_y+oy, COLOR_SKIN_HIGHLIGHT)
            _set_pixel(surf, 26+ox+arm_extend+1, arm_y+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 26+ox+arm_extend+1, arm_y+oy+1, COLOR_YELLOW)
            _set_pixel(surf, 26+ox+arm_extend+2, arm_y+oy+1, COLOR_NEON_ORANGE)
            trail = (255, 200, 100, 100)
            _set_pixel(surf, 24+ox, arm_y+oy+1, trail)
            _set_pixel(surf, 23+ox, arm_y+oy+1, trail)
        else:
            # Kick strike: skip right leg (will draw extended forward)
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
            _draw_rect(surf, 24+ox, 33+oy, arm_extend+4, 4, COLOR_PANTS_DARK)
            _draw_rect(surf, 24+ox+arm_extend+2, 32+oy, 4, 5, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 24+ox+arm_extend+5, 33+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 24+ox+arm_extend+6, 34+oy, COLOR_YELLOW)
            _set_pixel(surf, 24+ox+arm_extend+5, 34+oy, COLOR_NEON_ORANGE)
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 2: recovery
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if combo_idx < 2:
            # Punch recovery: skip right arm (halfway retracted)
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_arm=True)
            half_ext = arm_extend // 2
            _draw_rect(surf, 26+ox, arm_y+oy, half_ext, 4, COLOR_JACKET_BROWN)
            _draw_rect(surf, 26+ox+half_ext-2, arm_y+oy, 4, 4, COLOR_SKIN)
        else:
            # Kick recovery: skip right leg
            _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
            _draw_rect(surf, 24+ox, 33+oy, 5, 4, COLOR_PANTS_DARK)
            _draw_rect(surf, 28+ox, 32+oy, 4, 5, COLOR_BOOTS_BROWN)
        _draw_outline(surf)
        punch_frames.append(surf)

        sprites[f"punch{combo_idx}_right"] = punch_frames
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(f) for f in punch_frames]

    # --- KICK (3 frames) ---
    kick_frames = []
    # Wind-up: right leg pulled back
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
    _draw_rect(surf, 5+ox, 30+oy, 12, 4, COLOR_PANTS_DARK)
    _draw_outline(surf)
    kick_frames.append(surf)
    # Strike: right leg extended forward
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
    _draw_rect(surf, 24+ox, 30+oy, 12, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 34+ox, 29+oy, 4, 5, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 38+ox, 31+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 39+ox, 30+oy, COLOR_YELLOW)
    _set_pixel(surf, 38+ox, 30+oy, COLOR_NEON_ORANGE)
    _draw_outline(surf)
    kick_frames.append(surf)
    # Recovery: right leg retracting
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_right_leg=True)
    _draw_rect(surf, 24+ox, 31+oy, 5, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 28+ox, 30+oy, 4, 5, COLOR_BOOTS_BROWN)
    _draw_outline(surf)
    kick_frames.append(surf)
    sprites["kick_right"] = kick_frames
    sprites["kick_left"] = [_mirror_h(f) for f in kick_frames]

    # --- PARRY (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_left_arm=True)
    # Cyber arm raised in guard position
    _draw_rect(surf, 8+ox, 10+oy, 14, 4, COLOR_CYBER_ARM)
    _set_pixel(surf, 8+ox, 10+oy, COLOR_CYBER_ARM_HI)
    _draw_rect(surf, 8+ox, 10+oy, 14, 1, COLOR_CYBER_GLOW)
    for i in range(14):
        _set_pixel(surf, 7+ox, 8+oy+i, COLOR_NEON_BLUE)
        _set_pixel(surf, 6+ox, 9+oy+i, (0, 200, 255, 80))
    _draw_outline(surf)
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy)
    for py in range(12, 28):
        for px in range(7+ox, 24+ox):
            r, g, b, a = surf.get_at((px, py+oy))
            if a > 0:
                nr = min(255, r + 80)
                surf.set_at((px, py+oy), (nr, max(0, g-30), max(0, b-30), a))
    _draw_outline(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_gig_base(surf, ox=ox, oy=oy, skip_left_arm=True)
    # Cyber arm extended forward for hacking
    _draw_rect(surf, 0+ox, 14+oy, 6, 10, COLOR_CYBER_ARM)
    _set_pixel(surf, 5+ox, 14+oy, COLOR_CYBER_ARM_HI)
    _set_pixel(surf, 2+ox, 15+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 15+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2+ox, 17+oy, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3+ox, 17+oy, COLOR_CYBER_GLOW)
    for hy in range(6):
        for hx in range(6):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 12+oy+hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 12+oy+hy, (0, 180, 60, 150))
    _draw_outline(surf)
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ===================================================================
# THUG -- Street enforcer
# Base 30x48 on 42x48 canvas, ox=6 oy=0
# Bulkier build: 16px wide torso. Bandana with folds.
# Visible muscular arms with 2-tone shading. Tank top.
# Brass knuckles on fists. Heavy combat boots.
# ===================================================================

def _draw_thug_base(surf, alert=False, ox=6, oy=0,
                    skip_right_arm=False, skip_left_arm=False,
                    skip_legs=False):
    """Draw complete thug base. Use skip flags to omit body parts for animation."""
    W, H = THUG_WIDTH, THUG_HEIGHT

    if not skip_legs:
        # --- Boots (heavy black, 8px wide each) ---
        _draw_rect(surf, 2+ox, 39+oy, 8, 7, COLOR_BLACK)
        _set_pixel(surf, 3+ox, 39+oy, (30, 30, 30))
        _set_pixel(surf, 4+ox, 39+oy, (30, 30, 30))
        _set_pixel(surf, 5+ox, 39+oy, (30, 30, 30))
        _draw_rect(surf, 2+ox, 46+oy, 8, 2, (15, 12, 10))
        _draw_rect(surf, 18+ox, 39+oy, 8, 7, COLOR_BLACK)
        _set_pixel(surf, 19+ox, 39+oy, (30, 30, 30))
        _set_pixel(surf, 20+ox, 39+oy, (30, 30, 30))
        _set_pixel(surf, 21+ox, 39+oy, (30, 30, 30))
        _draw_rect(surf, 18+ox, 46+oy, 8, 2, (15, 12, 10))

        # --- Pants (6px each leg) ---
        _draw_rect(surf, 5+ox, 29+oy, 6, 10, COLOR_PANTS_DARK)
        _set_pixel(surf, 5+ox, 29+oy, COLOR_PANTS_HI)
        _set_pixel(surf, 6+ox, 29+oy, COLOR_PANTS_HI)
        _set_pixel(surf, 5+ox, 38+oy, COLOR_PANTS_SH)
        _draw_rect(surf, 17+ox, 29+oy, 6, 10, COLOR_PANTS_DARK)
        _set_pixel(surf, 22+ox, 29+oy, COLOR_PANTS_HI)
        _set_pixel(surf, 17+ox, 38+oy, COLOR_PANTS_SH)

    # Belt
    _draw_rect(surf, 3+ox, 28+oy, 22, 1, COLOR_BLACK)

    # --- Torso: 16px wide with wide shoulders ---
    body_color = COLOR_RED_ALARM if alert else COLOR_THUG_SHIRT
    body_sh = (180, 30, 55) if alert else COLOR_THUG_SHIRT_SH
    _draw_rect(surf, 4+ox, 14+oy, 20, 14, body_color)
    # Shoulder shelf
    _draw_rect(surf, 1+ox, 12+oy, 26, 3, body_color)
    # Shadow on left
    _draw_rect(surf, 1+ox, 12+oy, 4, 16, body_sh)
    # Highlight on right shoulder
    _set_pixel(surf, 25+ox, 12+oy, (80, 30, 30) if not alert else (255, 80, 100))
    _set_pixel(surf, 26+ox, 12+oy, (80, 30, 30) if not alert else (255, 80, 100))
    # Narrower waist
    _set_pixel(surf, 4+ox, 27+oy, (0, 0, 0, 0))
    _set_pixel(surf, 23+ox, 27+oy, (0, 0, 0, 0))
    # Tank top neckline (V shape)
    _draw_rect(surf, 9+ox, 12+oy, 10, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 12+ox, 15+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 13+ox, 15+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 14+ox, 15+oy, COLOR_DARK_GRAY)
    _set_pixel(surf, 15+ox, 15+oy, COLOR_DARK_GRAY)
    # Skull X marking
    marking = (100, 50, 50)
    _set_pixel(surf, 11+ox, 19+oy, marking)
    _set_pixel(surf, 16+ox, 19+oy, marking)
    _set_pixel(surf, 12+ox, 20+oy, marking)
    _set_pixel(surf, 15+ox, 20+oy, marking)
    _set_pixel(surf, 13+ox, 21+oy, marking)
    _set_pixel(surf, 14+ox, 21+oy, marking)
    _set_pixel(surf, 12+ox, 22+oy, marking)
    _set_pixel(surf, 15+ox, 22+oy, marking)
    _set_pixel(surf, 11+ox, 23+oy, marking)
    _set_pixel(surf, 16+ox, 23+oy, marking)

    # --- Arms: muscular, 4px wide ---
    if not skip_right_arm:
        # Right arm
        _draw_rect(surf, 27+ox, 14+oy, 4, 10, COLOR_THUG_SKIN)
        _set_pixel(surf, 27+ox, 14+oy, COLOR_THUG_SKIN_SH)
        _set_pixel(surf, 30+ox, 15+oy, COLOR_THUG_SKIN_HI)
        _set_pixel(surf, 30+ox, 16+oy, COLOR_THUG_SKIN_HI)
        _set_pixel(surf, 30+ox, 17+oy, COLOR_THUG_SKIN_HI)
        _set_pixel(surf, 27+ox, 20+oy, COLOR_THUG_SKIN_SH)
        _set_pixel(surf, 27+ox, 21+oy, COLOR_THUG_SKIN_SH)
        # Right fist + brass knuckles
        _draw_rect(surf, 27+ox, 24+oy, 4, 3, COLOR_THUG_SKIN)
        _set_pixel(surf, 27+ox, 24+oy, COLOR_BRASS)
        _set_pixel(surf, 28+ox, 24+oy, COLOR_BRASS_HI)
        _set_pixel(surf, 29+ox, 24+oy, COLOR_BRASS)
        _set_pixel(surf, 30+ox, 24+oy, COLOR_BRASS)

    if not skip_left_arm:
        # Left arm
        _draw_rect(surf, -3+ox, 14+oy, 4, 10, COLOR_THUG_SKIN)
        _set_pixel(surf, -3+ox, 14+oy, COLOR_THUG_SKIN_SH)
        _set_pixel(surf, -3+ox, 15+oy, COLOR_THUG_SKIN_SH)
        _set_pixel(surf, 0+ox, 15+oy, COLOR_THUG_SKIN_HI)
        _set_pixel(surf, 0+ox, 16+oy, COLOR_THUG_SKIN_HI)
        _set_pixel(surf, 0+ox, 17+oy, COLOR_THUG_SKIN_HI)
        # Left fist + brass knuckles
        _draw_rect(surf, -3+ox, 24+oy, 4, 3, COLOR_THUG_SKIN)
        _set_pixel(surf, -3+ox, 24+oy, COLOR_BRASS)
        _set_pixel(surf, -2+ox, 24+oy, COLOR_BRASS_HI)
        _set_pixel(surf, -1+ox, 24+oy, COLOR_BRASS)
        _set_pixel(surf, 0+ox, 24+oy, COLOR_BRASS)

    # --- Head (12 wide, 10 tall) ---
    _draw_rect(surf, 8+ox, 2+oy, 12, 10, COLOR_THUG_SKIN)
    _set_pixel(surf, 9+ox, 2+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 10+ox, 2+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 11+ox, 2+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 8+ox, 3+oy, COLOR_THUG_SKIN_HI)
    _set_pixel(surf, 18+ox, 10+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 19+ox, 10+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 19+ox, 11+oy, COLOR_THUG_SKIN_SH)

    # --- Bandana with fold lines ---
    _draw_rect(surf, 8+ox, 0+oy, 12, 3, COLOR_THUG_BANDANA)
    _set_pixel(surf, 8+ox, 0+oy, COLOR_THUG_BANDANA_SH)
    _set_pixel(surf, 19+ox, 0+oy, COLOR_THUG_BANDANA_SH)
    # Fold lines
    _set_pixel(surf, 11+ox, 1+oy, (255, 80, 100))
    _set_pixel(surf, 12+ox, 1+oy, (255, 80, 100))
    _set_pixel(surf, 15+ox, 1+oy, (255, 80, 100))
    _set_pixel(surf, 16+ox, 1+oy, (255, 80, 100))
    # Knot + trailing tail
    _set_pixel(surf, 20+ox, 1+oy, COLOR_THUG_BANDANA)
    _set_pixel(surf, 21+ox, 2+oy, COLOR_THUG_BANDANA)
    _set_pixel(surf, 22+ox, 3+oy, COLOR_THUG_BANDANA)
    _set_pixel(surf, 22+ox, 4+oy, COLOR_THUG_BANDANA_SH)
    _set_pixel(surf, 23+ox, 5+oy, COLOR_THUG_BANDANA_SH)
    _set_pixel(surf, 23+ox, 6+oy, COLOR_THUG_BANDANA_SH)

    # --- Thick angry eyebrows ---
    _set_pixel(surf, 9+ox, 4+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 4+oy, COLOR_BLACK)
    _set_pixel(surf, 10+ox, 5+oy, COLOR_BLACK)
    _set_pixel(surf, 18+ox, 4+oy, COLOR_BLACK)
    _set_pixel(surf, 17+ox, 4+oy, COLOR_BLACK)
    _set_pixel(surf, 17+ox, 5+oy, COLOR_BLACK)

    # Beady eyes
    _set_pixel(surf, 10+ox, 6+oy, COLOR_BLACK)
    _set_pixel(surf, 11+ox, 6+oy, COLOR_BLACK)
    _set_pixel(surf, 17+ox, 6+oy, COLOR_BLACK)
    _set_pixel(surf, 16+ox, 6+oy, COLOR_BLACK)

    # --- Scowl ---
    _draw_rect(surf, 12+ox, 9+oy, 4, 1, COLOR_BLACK)
    _set_pixel(surf, 11+ox, 9+oy, COLOR_THUG_SKIN_SH)
    _set_pixel(surf, 16+ox, 9+oy, COLOR_THUG_SKIN_SH)


def generate_thug_sprites():
    sprites = {}
    CW, CH = THUG_CANVAS_W, THUG_CANVAS_H
    ox = (CW - THUG_WIDTH) // 2  # 6
    oy = CH - THUG_HEIGHT          # 0

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy)
        if f == 1:
            _set_pixel(surf, 10+ox, 11+oy, COLOR_THUG_SHIRT)
            _set_pixel(surf, 17+ox, 11+oy, COLOR_THUG_SHIRT)
        _draw_outline(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames)
    walk_frames = []
    leg_off = [(0, 0), (3, -3), (0, 0), (-3, 3)]
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_thug_base(surf, ox=ox, oy=oy, skip_legs=True)
        lo1, lo2 = leg_off[f]
        # Draw legs with stride offsets
        _draw_rect(surf, 5+ox+lo1, 29+oy, 6, 10, COLOR_PANTS_DARK)
        _set_pixel(surf, 5+ox+lo1, 29+oy, COLOR_PANTS_HI)
        _set_pixel(surf, 6+ox+lo1, 29+oy, COLOR_PANTS_HI)
        _draw_rect(surf, 17+ox+lo2, 29+oy, 6, 10, COLOR_PANTS_DARK)
        _set_pixel(surf, 22+ox+lo2, 29+oy, COLOR_PANTS_HI)
        # Boots with stride offsets
        _draw_rect(surf, 2+ox+lo1, 39+oy, 8, 7, COLOR_BLACK)
        _set_pixel(surf, 3+ox+lo1, 39+oy, (30, 30, 30))
        _draw_rect(surf, 2+ox+lo1, 46+oy, 8, 2, (15, 12, 10))
        _draw_rect(surf, 18+ox+lo2, 39+oy, 8, 7, COLOR_BLACK)
        _set_pixel(surf, 19+ox+lo2, 39+oy, (30, 30, 30))
        _draw_rect(surf, 18+ox+lo2, 46+oy, 8, 2, (15, 12, 10))
        _draw_outline(surf)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK (3 frames)
    attack_frames = []
    # Wind-up: right arm pulled back
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy, skip_right_arm=True)
    # Right arm pulled back behind body
    _draw_rect(surf, ox-3, 18+oy, 5, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, ox-3, 18+oy, COLOR_THUG_SKIN_SH)
    _draw_rect(surf, ox-4, 17+oy, 4, 5, COLOR_THUG_SKIN)
    _set_pixel(surf, ox-4, 17+oy, COLOR_BRASS)
    _set_pixel(surf, ox-2, 17+oy, COLOR_BRASS)
    _set_pixel(surf, ox-3, 17+oy, COLOR_BRASS_HI)
    _draw_outline(surf)
    attack_frames.append(surf)
    # Strike: right arm fully extended forward
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy, skip_right_arm=True)
    _draw_rect(surf, 27+ox, 18+oy, 8, 4, COLOR_THUG_SKIN)
    _set_pixel(surf, 27+ox, 18+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 34+ox, 17+oy, 4, 5, COLOR_THUG_SKIN)
    _set_pixel(surf, 34+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 35+ox, 17+oy, COLOR_BRASS_HI)
    _set_pixel(surf, 36+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 37+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 38+ox, 18+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 38+ox, 17+oy, COLOR_YELLOW)
    _set_pixel(surf, 37+ox, 16+oy, COLOR_NEON_ORANGE)
    _draw_outline(surf)
    attack_frames.append(surf)
    # Recovery: right arm retracting
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy, skip_right_arm=True)
    _draw_rect(surf, 27+ox, 18+oy, 4, 4, COLOR_THUG_SKIN)
    _draw_rect(surf, 30+ox, 17+oy, 4, 5, COLOR_THUG_SKIN)
    _set_pixel(surf, 30+ox, 17+oy, COLOR_BRASS)
    _set_pixel(surf, 33+ox, 17+oy, COLOR_BRASS)
    _draw_outline(surf)
    attack_frames.append(surf)
    sprites["attack_right"] = attack_frames
    sprites["attack_left"] = [_mirror_h(f) for f in attack_frames]

    # ALERT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, alert=True, ox=ox, oy=oy)
    _draw_rect(surf, 13+ox, 0+oy, 2, 1, COLOR_RED_ALARM)
    _draw_outline(surf)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
    for py in range(12+oy, 28+oy):
        for px in range(1+ox, 27+ox):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 100)
                surf.set_at((px, py), (nr, max(0, g-40), max(0, b-40), a))
    _draw_outline(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (2 frames)
    death_frames = []
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_thug_base(surf, ox=ox, oy=oy)
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
    _draw_rect(surf, 0+ox, 37+oy, 28, 7, COLOR_THUG_SHIRT)
    _draw_rect(surf, 0+ox, 37+oy, 4, 7, COLOR_THUG_SHIRT_SH)
    _draw_rect(surf, 22+ox, 35+oy, 10, 9, COLOR_THUG_SKIN)
    _set_pixel(surf, 23+ox, 35+oy, COLOR_THUG_SKIN_HI)
    _draw_rect(surf, 22+ox, 33+oy, 10, 3, COLOR_THUG_BANDANA)
    _set_pixel(surf, 22+ox, 33+oy, COLOR_THUG_BANDANA_SH)
    _draw_outline(surf)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ===================================================================
# DRONE -- Surveillance drone
# Base 32x20 on 40x24 canvas, ox=4 oy=2
# Aerodynamic body with dithered curves, two 8px propeller blurs,
# 3x3 red sensor core with dim ring, panel lines, antenna, running lights
# ===================================================================

def _draw_drone_base(surf, propeller_frame=0, eye_bright=True, ox=4, oy=2):
    w, h = DRONE_WIDTH, DRONE_HEIGHT

    # --- Body: aerodynamic shape ---
    # Core body: widest section (rows 7-13)
    _draw_rect(surf, 6+ox, 7+oy, 20, 7, COLOR_DRONE_BODY)
    # Taper top (rows 4-6)
    _draw_rect(surf, 9+ox, 4+oy, 14, 3, COLOR_DRONE_BODY)
    # Taper bottom (rows 14-15)
    _draw_rect(surf, 9+ox, 14+oy, 14, 2, COLOR_DRONE_BODY)
    # Nose cone
    _set_pixel(surf, 5+ox, 8+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 9+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 10+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 5+ox, 11+oy, COLOR_DRONE_BODY)
    _set_pixel(surf, 4+ox, 9+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 4+ox, 10+oy, COLOR_DRONE_BODY_SH)
    # Tapered tail
    _set_pixel(surf, 26+ox, 7+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 26+ox, 8+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 26+ox, 9+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 26+ox, 10+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 26+ox, 11+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 27+ox, 8+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 27+ox, 9+oy, COLOR_DRONE_BODY_SH)
    _set_pixel(surf, 27+ox, 10+oy, COLOR_DRONE_BODY_SH)

    # Highlight on top-left
    _draw_rect(surf, 9+ox, 4+oy, 4, 1, COLOR_DRONE_BODY_HI)
    _draw_rect(surf, 6+ox, 7+oy, 4, 1, COLOR_DRONE_BODY_HI)
    _set_pixel(surf, 7+ox, 8+oy, COLOR_DRONE_BODY_HI)
    # Shadow on bottom-right
    _draw_rect(surf, 22+ox, 13+oy, 4, 1, COLOR_DRONE_BODY_SH)

    # Panel lines (3 sections)
    for yy in range(5, 14):
        _set_pixel(surf, 13+ox, yy+oy, COLOR_DRONE_BODY_SH)
        _set_pixel(surf, 19+ox, yy+oy, COLOR_DRONE_BODY_SH)

    # Ventral panel
    _draw_rect(surf, 10+ox, 13+oy, 12, 1, COLOR_MID_GRAY)

    # Thruster glow
    _set_pixel(surf, 12+ox, 16+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 13+ox, 17+oy, (255, 150, 50, 120))
    _set_pixel(surf, 20+ox, 16+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 19+ox, 17+oy, (255, 150, 50, 120))

    # --- Sensor eye: 3x3 core with 1px ring ---
    if eye_bright:
        eye_core = (255, 80, 80)
        eye_surround = (200, 40, 50)
        eye_outer = (150, 20, 30)
    else:
        eye_core = (150, 30, 40)
        eye_surround = (100, 20, 30)
        eye_outer = (60, 10, 15)
    # 3x3 core
    _draw_rect(surf, 14+ox, 8+oy, 3, 3, eye_core)
    # Surround ring
    _set_pixel(surf, 13+ox, 8+oy, eye_surround)
    _set_pixel(surf, 13+ox, 9+oy, eye_surround)
    _set_pixel(surf, 13+ox, 10+oy, eye_surround)
    _set_pixel(surf, 17+ox, 8+oy, eye_surround)
    _set_pixel(surf, 17+ox, 9+oy, eye_surround)
    _set_pixel(surf, 17+ox, 10+oy, eye_surround)
    _set_pixel(surf, 14+ox, 7+oy, eye_surround)
    _set_pixel(surf, 15+ox, 7+oy, eye_surround)
    _set_pixel(surf, 16+ox, 7+oy, eye_surround)
    _set_pixel(surf, 14+ox, 11+oy, eye_surround)
    _set_pixel(surf, 15+ox, 11+oy, eye_surround)
    _set_pixel(surf, 16+ox, 11+oy, eye_surround)
    # Outer corners
    _set_pixel(surf, 13+ox, 7+oy, eye_outer)
    _set_pixel(surf, 17+ox, 7+oy, eye_outer)
    _set_pixel(surf, 13+ox, 11+oy, eye_outer)
    _set_pixel(surf, 17+ox, 11+oy, eye_outer)

    # --- Propeller mounts + 8px blur ---
    _draw_rect(surf, 2+ox, 4+oy, 3, 4, COLOR_DARK_GRAY)
    _set_pixel(surf, 2+ox, 4+oy, COLOR_MID_GRAY)
    _draw_rect(surf, 27+ox, 4+oy, 3, 4, COLOR_DARK_GRAY)
    _set_pixel(surf, 27+ox, 4+oy, COLOR_MID_GRAY)
    _set_pixel(surf, 3+ox, 4+oy, COLOR_MID_GRAY)
    _set_pixel(surf, 28+ox, 4+oy, COLOR_MID_GRAY)

    if propeller_frame == 0:
        _draw_rect(surf, 0+ox, 1+oy, 8, 1, (160, 165, 180, 120))
        _draw_rect(surf, 1+ox, 2+oy, 6, 1, (160, 165, 180, 70))
        _draw_rect(surf, 0+ox, 3+oy, 8, 1, (160, 165, 180, 40))
        _draw_rect(surf, 24+ox, 1+oy, 8, 1, (160, 165, 180, 120))
        _draw_rect(surf, 25+ox, 2+oy, 6, 1, (160, 165, 180, 70))
        _draw_rect(surf, 24+ox, 3+oy, 8, 1, (160, 165, 180, 40))
    else:
        _draw_rect(surf, 1+ox, 1+oy, 6, 1, (160, 165, 180, 90))
        _draw_rect(surf, 0+ox, 2+oy, 8, 1, (160, 165, 180, 80))
        _draw_rect(surf, 1+ox, 3+oy, 6, 1, (160, 165, 180, 40))
        _draw_rect(surf, 25+ox, 1+oy, 6, 1, (160, 165, 180, 90))
        _draw_rect(surf, 24+ox, 2+oy, 8, 1, (160, 165, 180, 80))
        _draw_rect(surf, 25+ox, 3+oy, 6, 1, (160, 165, 180, 40))

    # Antenna + running lights
    _set_pixel(surf, 9+ox, 1+oy, COLOR_NEON_BLUE)
    _set_pixel(surf, 22+ox, 1+oy, COLOR_NEON_BLUE)
    _set_pixel(surf, 9+ox, 0+oy, (0, 150, 180, 150))
    _set_pixel(surf, 22+ox, 0+oy, (0, 150, 180, 150))
    # Running lights on tips
    _set_pixel(surf, 6+ox, 7+oy, (0, 200, 255, 120))
    _set_pixel(surf, 25+ox, 7+oy, (255, 80, 80, 120))


def generate_drone_sprites():
    sprites = {}
    CW, CH = DRONE_CANVAS_W, DRONE_CANVAS_H
    ox = (CW - DRONE_WIDTH) // 2   # 4
    oy = (CH - DRONE_HEIGHT) // 2  # 2

    # FLY (2 frames)
    fly_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_drone_base(surf, f, eye_bright=(f == 0), ox=ox, oy=oy)
        _draw_outline(surf)
        fly_frames.append(surf)
    sprites["fly_right"] = fly_frames
    sprites["fly_left"] = [_mirror_h(f) for f in fly_frames]

    # SHOOT (1 frame)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    for i in range(10):
        ly = DRONE_HEIGHT + oy + i
        if ly < CH:
            _set_pixel(surf, 16+ox, ly, COLOR_RED_ALARM)
            _set_pixel(surf, 15+ox, ly, (255, 46, 77, 80))
            _set_pixel(surf, 17+ox, ly, (255, 46, 77, 80))
    _draw_outline(surf)
    sprites["shoot_right"] = [surf]
    sprites["shoot_left"] = [_mirror_h(surf)]

    # HACKED
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, ox=ox, oy=oy)
    _draw_rect(surf, 14+ox, 8+oy, 3, 3, COLOR_GREEN_HACK)
    _set_pixel(surf, 13+ox, 8+oy, (0, 200, 80))
    _set_pixel(surf, 17+ox, 8+oy, (0, 200, 80))
    _set_pixel(surf, 13+ox, 10+oy, (0, 200, 80))
    _set_pixel(surf, 17+ox, 10+oy, (0, 200, 80))
    _draw_outline(surf)
    sprites["hacked_right"] = [surf]
    sprites["hacked_left"] = [_mirror_h(surf)]

    # STUNNED
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, eye_bright=False, ox=ox, oy=oy)
    for i in range(3):
        _set_pixel(surf, 8+ox+i*6, 1+oy, COLOR_YELLOW)
        _set_pixel(surf, 9+ox+i*6, 0+oy, COLOR_YELLOW)
    _draw_outline(surf)
    sprites["stunned_right"] = [surf]
    sprites["stunned_left"] = [_mirror_h(surf)]

    # DEATH (3 frames)
    death_frames = []
    for f in range(3):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        radius = 5 + f * 4
        cx, cy = CW // 2, CH // 2
        colors = [COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_YELLOW]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    _set_pixel(surf, cx + dx, cy + dy, colors[f])
        if f > 0:
            for i in range(4):
                fx = cx + int(math.cos(i * 1.5 + f) * (radius + 3))
                fy = cy + int(math.sin(i * 1.5 + f) * (radius + 3))
                _set_pixel(surf, fx, fy, COLOR_DRONE_BODY)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames

    return sprites


# ===================================================================
# WARDEN -- Level 1 Boss
# Base 48x64 on 64x72 canvas, ox=8 oy=4
# MASSIVE armored figure. Helmet 16px wide with 8px gradient visor.
# Shoulder pads 5-6px past body. 6x6 energy core with 4-tone gradient.
# Armored gauntlets 6x5 with glowing knuckles. 3px tread boots.
# Phase 2: cracks. Phase 3: exposed wiring, red core.
# ===================================================================

def _draw_warden_base(surf, phase=0, ox=8, oy=4,
                      skip_right_arm=False, skip_left_arm=False,
                      skip_legs=False):
    """Draw complete warden base. Use skip flags to omit body parts for animation."""
    w, h = WARDEN_WIDTH, WARDEN_HEIGHT

    if not skip_legs:
        # --- Heavy boots (rows 55-63) ---
        _draw_rect(surf, 6+ox, 55+oy, 14, 9, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 7+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 8+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 9+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 10+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 6+ox, 63+oy, 14, 1, COLOR_BLACK)
        _draw_rect(surf, 6+ox, 61+oy, 14, 2, (20, 20, 20))  # 3px tread
        _draw_rect(surf, 28+ox, 55+oy, 14, 9, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 29+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 30+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 31+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 32+ox, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 28+ox, 63+oy, 14, 1, COLOR_BLACK)
        _draw_rect(surf, 28+ox, 61+oy, 14, 2, (20, 20, 20))
        # Boot trim
        _draw_rect(surf, 6+ox, 55+oy, 14, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 28+ox, 55+oy, 14, 1, COLOR_WARDEN_TRIM)

        # --- Leg armor (rows 39-54): wider thighs ---
        _draw_rect(surf, 8+ox, 39+oy, 12, 16, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 28+ox, 39+oy, 12, 16, COLOR_WARDEN_ARMOR)
        # Highlight
        _set_pixel(surf, 9+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 10+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 11+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 29+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 30+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 31+ox, 39+oy, COLOR_WARDEN_ARMOR_HI)
        # Shadow
        for y_s in range(42, 54, 3):
            _set_pixel(surf, 19+ox, y_s+oy, COLOR_WARDEN_ARMOR_SH)
            _set_pixel(surf, 28+ox, y_s+oy, COLOR_WARDEN_ARMOR_SH)
        # Knee pads
        _draw_rect(surf, 8+ox, 46+oy, 12, 2, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 28+ox, 46+oy, 12, 2, COLOR_WARDEN_TRIM)
        # Seam lines
        for y_s in [40, 44, 50]:
            _set_pixel(surf, 14+ox, y_s+oy, COLOR_BLACK)
            _set_pixel(surf, 34+ox, y_s+oy, COLOR_BLACK)

    # --- Tech belt ---
    _draw_rect(surf, 8+ox, 37+oy, 32, 2, COLOR_DARK_GRAY)
    _draw_rect(surf, 22+ox, 37+oy, 4, 2, COLOR_NEON_ORANGE)

    # --- Armored torso (rows 16-36) ---
    _draw_rect(surf, 8+ox, 16+oy, 32, 21, COLOR_WARDEN_ARMOR)
    # Chest plate
    _draw_rect(surf, 10+ox, 17+oy, 28, 14, (50, 55, 70))
    # Highlight top-left
    _set_pixel(surf, 10+ox, 17+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 11+ox, 17+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 12+ox, 17+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 13+ox, 17+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 10+ox, 18+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 10+ox, 19+oy, COLOR_WARDEN_ARMOR_HI)
    # Shadow bottom-right
    _set_pixel(surf, 36+ox, 29+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 37+ox, 29+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 37+ox, 30+oy, COLOR_WARDEN_ARMOR_SH)
    # Seam lines
    for sx in range(10, 38):
        _set_pixel(surf, sx+ox, 22+oy, COLOR_BLACK)
        _set_pixel(surf, sx+ox, 28+oy, COLOR_BLACK)
    # Trim
    _draw_rect(surf, 10+ox, 17+oy, 28, 1, COLOR_WARDEN_TRIM)
    _draw_rect(surf, 10+ox, 30+oy, 28, 1, COLOR_WARDEN_TRIM)

    # --- Energy core: 6x6 with 4-tone gradient ---
    core_colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_RED_ALARM]
    core_col = core_colors[min(phase, 2)]
    dim1 = tuple(max(0, c - 40) for c in core_col[:3])
    dim2 = tuple(max(0, c - 90) for c in core_col[:3])
    dim3 = tuple(max(0, c - 140) for c in core_col[:3])
    dim4 = tuple(max(0, c - 180) for c in core_col[:3])
    # Dim outer ring (10x10)
    _draw_rect(surf, 19+ox, 20+oy, 10, 10, dim4)
    # Outer ring (8x8)
    _draw_rect(surf, 20+ox, 21+oy, 8, 8, dim3)
    # Mid ring (6x6)
    _draw_rect(surf, 21+ox, 22+oy, 6, 6, dim2)
    # Inner ring (4x4)
    _draw_rect(surf, 22+ox, 23+oy, 4, 4, dim1)
    # Core (2x2) brightest
    _draw_rect(surf, 23+ox, 24+oy, 2, 2, core_col)

    # --- Shoulder pads (5-6px past body each side) ---
    if not skip_left_arm:
        _draw_rect(surf, 1+ox, 13+oy, 11, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 1+ox, 13+oy, 11, 1, COLOR_WARDEN_TRIM)
        _set_pixel(surf, 2+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 3+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 4+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 5+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 10+ox, 19+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 11+ox, 19+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 6+ox, 16+oy, COLOR_BLACK)
    if not skip_right_arm:
        _draw_rect(surf, 36+ox, 13+oy, 11, 7, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 36+ox, 13+oy, 11, 1, COLOR_WARDEN_TRIM)
        _set_pixel(surf, 37+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 38+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 39+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 40+ox, 14+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 45+ox, 19+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 46+ox, 19+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 42+ox, 16+oy, COLOR_BLACK)

    # --- Arms (6px wide) ---
    if not skip_left_arm:
        _draw_rect(surf, 2+ox, 20+oy, 6, 16, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 3+ox, 20+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 4+ox, 20+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 2+ox, 34+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 7+ox, 34+oy, COLOR_WARDEN_ARMOR_SH)
    if not skip_right_arm:
        _draw_rect(surf, 40+ox, 20+oy, 6, 16, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 41+ox, 20+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 42+ox, 20+oy, COLOR_WARDEN_ARMOR_HI)
        _set_pixel(surf, 40+ox, 34+oy, COLOR_WARDEN_ARMOR_SH)
        _set_pixel(surf, 45+ox, 34+oy, COLOR_WARDEN_ARMOR_SH)

    # --- Gauntlets: 6x5 with glow knuckles ---
    if not skip_left_arm:
        _draw_rect(surf, 2+ox, 36+oy, 6, 5, COLOR_DARK_GRAY)
        _set_pixel(surf, 2+ox, 36+oy, COLOR_MID_GRAY)
        _set_pixel(surf, 3+ox, 36+oy, core_col)
        _set_pixel(surf, 4+ox, 36+oy, core_col)
        _set_pixel(surf, 5+ox, 36+oy, core_col)
        _set_pixel(surf, 6+ox, 36+oy, core_col)
    if not skip_right_arm:
        _draw_rect(surf, 40+ox, 36+oy, 6, 5, COLOR_DARK_GRAY)
        _set_pixel(surf, 45+ox, 36+oy, COLOR_MID_GRAY)
        _set_pixel(surf, 41+ox, 36+oy, core_col)
        _set_pixel(surf, 42+ox, 36+oy, core_col)
        _set_pixel(surf, 43+ox, 36+oy, core_col)
        _set_pixel(surf, 44+ox, 36+oy, core_col)

    # --- Helmet (rows 0-15): 16px wide ---
    _draw_rect(surf, 14+ox, 1+oy, 20, 15, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 16+ox, 0+oy, 16, 1, COLOR_WARDEN_ARMOR)
    # Highlight
    _set_pixel(surf, 15+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 16+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 17+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 18+ox, 1+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 15+ox, 2+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 15+ox, 3+oy, COLOR_WARDEN_ARMOR_HI)
    # Shadow
    _set_pixel(surf, 32+ox, 14+oy, COLOR_WARDEN_ARMOR_SH)
    _set_pixel(surf, 33+ox, 14+oy, COLOR_WARDEN_ARMOR_SH)

    # Visor: 8px wide with gradient brightness
    visor_y = 7
    _draw_rect(surf, 16+ox, visor_y+oy, 16, 4, COLOR_WARDEN_VISOR)
    # Gradient: dim edges, bright center
    _set_pixel(surf, 16+ox, visor_y+1+oy, (180, 30, 50))
    _set_pixel(surf, 17+ox, visor_y+1+oy, (190, 50, 60))
    _set_pixel(surf, 18+ox, visor_y+1+oy, (200, 70, 80))
    _set_pixel(surf, 19+ox, visor_y+1+oy, (210, 90, 90))
    _set_pixel(surf, 20+ox, visor_y+1+oy, (220, 110, 110))
    _draw_rect(surf, 21+ox, visor_y+1+oy, 6, 1, (255, 200, 200))
    _set_pixel(surf, 27+ox, visor_y+1+oy, (220, 110, 110))
    _set_pixel(surf, 28+ox, visor_y+1+oy, (210, 90, 90))
    _set_pixel(surf, 29+ox, visor_y+1+oy, (200, 70, 80))
    _set_pixel(surf, 30+ox, visor_y+1+oy, (190, 50, 60))
    _set_pixel(surf, 31+ox, visor_y+1+oy, (180, 30, 50))

    # Helmet trim
    _draw_rect(surf, 14+ox, 1+oy, 20, 1, COLOR_WARDEN_TRIM)
    # Antenna
    _set_pixel(surf, 23+ox, 0+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 24+ox, 0+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 25+ox, 0+oy, COLOR_RED_ALARM)


def generate_warden_sprites():
    sprites = {}
    CW, CH = WARDEN_CANVAS_W, WARDEN_CANVAS_H
    ox = (CW - WARDEN_WIDTH) // 2  # 8
    oy = CH - WARDEN_HEIGHT          # 8 -> adjusted: (72-64)//2 = 4... let me use CH - WARDEN_HEIGHT = 72-64=8
    # Actually oy = CH - WARDEN_HEIGHT = 72 - 64 = 8, but the spec says (72-64)//2=4
    # Use 4 to center vertically for shockwave effects below
    oy = (CH - WARDEN_HEIGHT) // 2  # 4

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy)
        if f == 1:
            _draw_rect(surf, 23+ox, 24+oy, 2, 2, (0, 255, 255))
        _draw_outline_thick(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames)
    walk_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        _draw_warden_base(surf, 0, ox=ox, oy=oy, skip_legs=True)
        off = [0, 3, 0, -3][f]
        # Draw leg armor with stride offsets
        _draw_rect(surf, 8+ox+off, 39+oy, 12, 16, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 9+ox+off, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 8+ox+off, 46+oy, 12, 2, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 28+ox-off, 39+oy, 12, 16, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 29+ox-off, 39+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 28+ox-off, 46+oy, 12, 2, COLOR_WARDEN_TRIM)
        # Boots with stride offsets
        _draw_rect(surf, 6+ox+off, 55+oy, 14, 9, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 7+ox+off, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 6+ox+off, 55+oy, 14, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 6+ox+off, 63+oy, 14, 1, COLOR_BLACK)
        _draw_rect(surf, 6+ox+off, 61+oy, 14, 2, (20, 20, 20))
        _draw_rect(surf, 28+ox-off, 55+oy, 14, 9, COLOR_WARDEN_ARMOR)
        _set_pixel(surf, 29+ox-off, 55+oy, COLOR_WARDEN_ARMOR_HI)
        _draw_rect(surf, 28+ox-off, 55+oy, 14, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 28+ox-off, 63+oy, 14, 1, COLOR_BLACK)
        _draw_rect(surf, 28+ox-off, 61+oy, 14, 2, (20, 20, 20))
        _draw_outline_thick(surf)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # MELEE (2 attacks, 2 frames each)
    for m_idx in range(2):
        melee_frames = []
        for f in range(2):
            surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
            _draw_warden_base(surf, 0, ox=ox, oy=oy, skip_right_arm=True)
            # Right arm extended for melee strike
            arm_ext = 10 + f * 6 + m_idx * 3
            arm_start_x = WARDEN_WIDTH - 2 + ox
            _draw_rect(surf, arm_start_x, 23+oy, arm_ext, 5, COLOR_WARDEN_ARMOR)
            _set_pixel(surf, arm_start_x, 23+oy, COLOR_WARDEN_ARMOR_HI)
            _draw_rect(surf, arm_start_x+arm_ext-4, 22+oy, 8, 8, COLOR_NEON_ORANGE)
            _draw_rect(surf, arm_start_x+arm_ext-3, 23+oy, 6, 6, COLOR_YELLOW)
            _draw_outline_thick(surf)
            melee_frames.append(surf)
        sprites[f"melee{m_idx}_right"] = melee_frames
        sprites[f"melee{m_idx}_left"] = [_mirror_h(f) for f in melee_frames]

    # SHOCKWAVE (1 frame)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 1, ox=ox, oy=oy)
    for i in range(6):
        wave_w = (i + 1) * 8
        alpha = 255 - i * 40
        for wx in range(-wave_w, wave_w):
            px = CW // 2 + wx
            py = WARDEN_HEIGHT + oy + i
            if 0 <= px < CW and 0 <= py < CH:
                _set_pixel(surf, px, py, (*COLOR_NEON_ORANGE[:3], max(0, alpha)))
    _draw_outline_thick(surf)
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame)
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_warden_base(surf, 1, ox=ox, oy=oy, skip_left_arm=True, skip_right_arm=True)
    # Both arms raised
    _draw_rect(surf, 2+ox, 7+oy, 6, 13, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 3+ox, 7+oy, COLOR_WARDEN_ARMOR_HI)
    _draw_rect(surf, 40+ox, 7+oy, 6, 13, COLOR_WARDEN_ARMOR)
    _set_pixel(surf, 41+ox, 7+oy, COLOR_WARDEN_ARMOR_HI)
    _set_pixel(surf, 1+ox, 6+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 0+ox, 5+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 46+ox, 6+oy, COLOR_RED_ALARM)
    _set_pixel(surf, 47+ox, 5+oy, COLOR_RED_ALARM)
    _draw_outline_thick(surf)
    sprites["spawn_right"] = [surf]
    sprites["spawn_left"] = [_mirror_h(surf)]

    # PHASE 2: cracks, orange core
    for anim in ["idle", "walk"]:
        p2_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            crack_pts = [
                (14, 20), (15, 21), (16, 22), (17, 23), (16, 24),
                (32, 19), (33, 20), (34, 21), (33, 22),
                (12, 27), (13, 28), (14, 29),
                (30, 26), (31, 27), (32, 28),
            ]
            for cx, cy in crack_pts:
                _set_pixel(surf, cx+ox, cy+oy, COLOR_BLACK)
            _draw_rect(surf, 23+ox, 24+oy, 2, 2, COLOR_NEON_ORANGE)
            _draw_rect(surf, 22+ox, 23+oy, 4, 4, (180, 90, 20))
            _draw_rect(surf, 23+ox, 24+oy, 2, 2, COLOR_NEON_ORANGE)
            p2_frames.append(surf)
        sprites[f"{anim}_p2_right"] = p2_frames
        sprites[f"{anim}_p2_left"] = [_mirror_h(f) for f in p2_frames]

    # PHASE 3: heavy damage
    for anim in ["idle", "walk"]:
        p3_frames = []
        for fr in sprites[f"{anim}_right"]:
            surf = fr.copy()
            for cy in range(18, 32):
                _set_pixel(surf, 14+ox + (cy % 5), cy+oy, COLOR_BLACK)
                _set_pixel(surf, 32+ox - (cy % 5), cy+oy, COLOR_BLACK)
            _draw_rect(surf, 1+ox, 16+oy, 5, 4, COLOR_BLACK)
            _draw_rect(surf, 42+ox, 16+oy, 5, 4, COLOR_BLACK)
            _set_pixel(surf, 3+ox, 17+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 4+ox, 18+oy, COLOR_GREEN_HACK)
            _set_pixel(surf, 2+ox, 16+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 43+ox, 17+oy, COLOR_NEON_BLUE)
            _set_pixel(surf, 44+ox, 18+oy, COLOR_NEON_ORANGE)
            _set_pixel(surf, 42+ox, 16+oy, COLOR_GREEN_HACK)
            _draw_rect(surf, 19+ox, 20+oy, 10, 10, (40, 5, 10))
            _draw_rect(surf, 20+ox, 21+oy, 8, 8, (60, 10, 15))
            _draw_rect(surf, 21+ox, 22+oy, 6, 6, (180, 30, 40))
            _draw_rect(surf, 23+ox, 24+oy, 2, 2, COLOR_RED_ALARM)
            _set_pixel(surf, 8+ox, 16+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 39+ox, 16+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 8+ox, 34+oy, COLOR_RED_ALARM)
            _set_pixel(surf, 39+ox, 34+oy, COLOR_RED_ALARM)
            p3_frames.append(surf)
        sprites[f"{anim}_p3_right"] = p3_frames
        sprites[f"{anim}_p3_left"] = [_mirror_h(f) for f in p3_frames]

    # HURT
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

    # DEATH (4 frames)
    death_frames = []
    for f in range(4):
        surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        if f < 2:
            _draw_warden_base(surf, 2, ox=ox, oy=oy)
            for i in range(f + 1):
                cx_e = 16 + i * 12 + ox
                cy_e = 24 + i * 8 + oy
                for dy in range(-5, 6):
                    for dx in range(-5, 6):
                        if dx * dx + dy * dy <= 25:
                            _set_pixel(surf, cx_e + dx, cy_e + dy, COLOR_NEON_ORANGE)
            _draw_outline_thick(surf)
        else:
            cx, cy = CW // 2, CH // 2
            radius = 12 + (f - 2) * 10
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
    _draw_rect(surf, 2, 0, 2, 3, COLOR_MID_GRAY)
    _draw_rect(surf, 0, 3, 8, 5, COLOR_DARK_GRAY)
    _set_pixel(surf, 1, 3, COLOR_MID_GRAY)
    _set_pixel(surf, 2, 3, COLOR_MID_GRAY)
    _draw_rect(surf, 8, 4, 4, 3, COLOR_MID_GRAY)
    _set_pixel(surf, 8, 4, (80, 75, 110))
    _draw_rect(surf, 10, 5, 2, 1, COLOR_RED_ALARM)
    _draw_outline(surf)
    return surf


def generate_terminal_sprite():
    """Hackable terminal 16x16 with scanlines and keyboard."""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    _draw_rect(surf, 2, 1, 12, 10, COLOR_DARK_GRAY)
    _set_pixel(surf, 3, 1, COLOR_MID_GRAY)
    _set_pixel(surf, 4, 1, COLOR_MID_GRAY)
    _draw_rect(surf, 3, 2, 10, 8, COLOR_BG_NIGHT)
    for row in range(4):
        y = 3 + row * 2
        bright = COLOR_GREEN_HACK
        dark = (0, 180, 60)
        _draw_rect(surf, 4, y, 6 + (row % 2) * 2, 1, bright if row % 2 == 0 else dark)
    _draw_rect(surf, 4, 8, 2, 1, COLOR_GREEN_HACK)
    _set_pixel(surf, 4, 8, (0, 255, 100))
    _set_pixel(surf, 13, 9, COLOR_GREEN_HACK)
    _draw_rect(surf, 5, 11, 6, 1, COLOR_MID_GRAY)
    _draw_rect(surf, 3, 12, 10, 3, COLOR_DARK_GRAY)
    _set_pixel(surf, 3, 12, COLOR_MID_GRAY)
    for kx in range(4, 13, 2):
        _set_pixel(surf, kx, 13, COLOR_MID_GRAY)
    for kx in range(5, 12, 2):
        _set_pixel(surf, kx, 14, COLOR_MID_GRAY)
    _draw_outline(surf)
    return surf


def generate_door_sprites():
    """Door/gate 16x32, open and closed states."""
    sprites = {}
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 16, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 1, 1, 14, 30, COLOR_MID_GRAY)
    for i in range(4):
        _draw_rect(surf, 1, 1 + i * 8, 14, 1, COLOR_DARK_GRAY)
    _set_pixel(surf, 2, 2, (80, 75, 110))
    _set_pixel(surf, 2, 10, (80, 75, 110))
    _draw_rect(surf, 7, 14, 2, 2, COLOR_RED_ALARM)
    _draw_outline(surf)
    sprites["closed"] = surf

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
    _draw_rect(surf, 2, 0, 2, 2, (255, 200, 200))
    return surf


def generate_emp_sprite():
    """EMP projectile 8x8, blue circle with glow."""
    surf = pygame.Surface((8, 8), pygame.SRCALPHA)
    cx, cy = 4, 4
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            dist = dx * dx + dy * dy
            if dist <= 4:
                _set_pixel(surf, cx + dx, cy + dy, (0, 255, 255))
            elif dist <= 9:
                _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_BLUE)
            elif dist <= 16:
                _set_pixel(surf, cx + dx, cy + dy, (0, 229, 255, 80))
    return surf


def generate_heart_sprite(full=True):
    """Heart for HUD, 11x11. Full = bright red with highlight, Empty = gray outline."""
    surf = pygame.Surface((11, 11), pygame.SRCALPHA)

    heart_pixels = [
        (1, 0), (2, 0), (3, 0), (4, 0), (6, 0), (7, 0), (8, 0), (9, 0),
        (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1),
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2),
        (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3),
        (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4),
        (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5),
        (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6),
        (3, 7), (4, 7), (5, 7), (6, 7), (7, 7),
        (4, 8), (5, 8), (6, 8),
        (5, 9),
    ]

    if full:
        color = COLOR_RED_ALARM
        for px, py in heart_pixels:
            _set_pixel(surf, px, py, color)
        shadow = (180, 30, 55)
        for px, py in heart_pixels:
            if py >= 5 or px >= 7:
                _set_pixel(surf, px, py, shadow)
        for px, py in heart_pixels:
            if 1 <= py <= 4 and 1 <= px <= 7:
                _set_pixel(surf, px, py, color)
        _set_pixel(surf, 1, 1, (255, 180, 190))
        _set_pixel(surf, 2, 1, (255, 140, 160))
        _set_pixel(surf, 1, 2, (255, 120, 140))
        _set_pixel(surf, 2, 2, (255, 140, 160))
    else:
        outline_color = (40, 35, 60)
        for px, py in heart_pixels:
            _set_pixel(surf, px, py, outline_color)
        interior = [
            (1, 1), (2, 1), (3, 1), (4, 1), (6, 1), (7, 1), (8, 1), (9, 1),
            (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2),
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3),
            (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4),
            (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5),
            (3, 6), (4, 6), (5, 6), (6, 6), (7, 6),
            (4, 7), (5, 7), (6, 7),
            (5, 8),
        ]
        dark_fill = (15, 13, 35)
        for px, py in interior:
            _set_pixel(surf, px, py, dark_fill)

    return surf


def generate_particle_sprites():
    """Various particle effect sprites."""
    particles = {}
    surf = pygame.Surface((3, 3), pygame.SRCALPHA)
    _set_pixel(surf, 1, 0, COLOR_YELLOW)
    _set_pixel(surf, 0, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 1, COLOR_WHITE_UI)
    _set_pixel(surf, 2, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 2, COLOR_YELLOW)
    particles["spark"] = surf

    surf = pygame.Surface((5, 5), pygame.SRCALPHA)
    _set_pixel(surf, 2, 0, COLOR_NEON_ORANGE)
    _set_pixel(surf, 0, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 4, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 4, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 2, COLOR_YELLOW)
    _set_pixel(surf, 1, 1, (255, 180, 50, 150))
    _set_pixel(surf, 3, 1, (255, 180, 50, 150))
    _set_pixel(surf, 1, 3, (255, 180, 50, 150))
    _set_pixel(surf, 3, 3, (255, 180, 50, 150))
    particles["hit"] = surf

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
