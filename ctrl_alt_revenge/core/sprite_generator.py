# core/sprite_generator.py -- Pixel-art sprite generator using ASCII matrix system
# Each sprite frame is defined as a list of strings where each character = one pixel
# This makes sprites trivially inspectable and editable
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

# Canvas sizes
GIG_CANVAS_W, GIG_CANVAS_H = 44, 48
THUG_CANVAS_W, THUG_CANVAS_H = 42, 48
DRONE_CANVAS_W, DRONE_CANVAS_H = 40, 24
WARDEN_CANVAS_W, WARDEN_CANVAS_H = 64, 72

# Outline color
OUTLINE = (5, 3, 15)

# ===================================================================
# Matrix-to-surface conversion
# ===================================================================

def _matrix_to_surface(matrix, color_map, width, height, ox=0, oy=0):
    """Convert ASCII art matrix to a pygame Surface.
    Each character in the matrix maps to a color via color_map.
    '.' is always transparent. The matrix is placed at offset (ox, oy)."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y, row in enumerate(matrix):
        for x, ch in enumerate(row):
            if ch == '.':
                continue
            color = color_map.get(ch)
            if color is not None:
                px, py = x + ox, y + oy
                if 0 <= px < width and 0 <= py < height:
                    if len(color) == 4:
                        surf.set_at((px, py), color)
                    else:
                        surf.set_at((px, py), (*color, 255))
    return surf


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


# ===================================================================
# GIG Color Map
# ===================================================================

GIG_COLORS = {
    '.': None,
    '#': OUTLINE,
    'H': (160, 155, 150),     # hair gray
    'h': (120, 115, 110),     # hair dark
    'L': (185, 180, 175),     # hair light
    'S': (210, 170, 130),     # skin base
    's': (180, 140, 100),     # skin shadow
    'F': (230, 190, 150),     # skin highlight
    'f': (150, 110, 75),      # skin deep
    'J': (180, 120, 50),      # jacket base
    'j': (140, 90, 35),       # jacket shadow
    'K': (200, 140, 65),      # jacket highlight
    'k': (100, 65, 25),       # jacket deep
    'C': (0, 229, 255),       # cyber glow
    'c': (0, 150, 180),       # cyber dim
    'g': (0, 120, 150, 120),  # cyber halo
    'G': (0, 80, 100, 80),    # cyber bleed
    'A': (80, 90, 110),       # cyber arm
    'a': (100, 112, 135),     # cyber arm highlight
    'z': (55, 62, 80),        # cyber arm shadow
    'D': (50, 55, 60),        # dark gray (shirt)
    'P': (50, 55, 60),        # pants
    'p': (65, 70, 78),        # pants highlight
    'q': (35, 38, 45),        # pants shadow
    'B': (120, 80, 40),       # boots
    'b': (145, 100, 55),      # boots highlight
    'V': (50, 35, 18),        # boots sole
    'O': (255, 122, 26),      # orange accent
    'Y': (255, 220, 50),      # yellow
    'W': (200, 220, 255),     # eye white
    'E': (0, 0, 0),           # eye dark / black
    'X': (0, 255, 255),       # bright cyan
    'T': (255, 200, 100, 100),  # trail
    'R': (255, 46, 77),       # red
    'N': (0, 150, 200, 80),   # eye halo
    'n': (0, 100, 130, 40),   # eye halo dim
    'M': (0, 120, 160, 60),   # eye halo soft
}

# ===================================================================
# GIG Frames -- 44x48 canvas, 32px wide art, ox=6
# ===================================================================

# Standing idle frame 0: base pose
GIG_IDLE_0 = [
    "........LHLHLHLHhh..........",  # row 0: hair top
    "........HHHHHHHHHh..........",  # row 1: hair
    ".......LHHHHHHHHhHh.........",  # row 2: hair + ponytail start
    "........FFFFSSSSsH.Hh........",  # row 3: forehead
    "........NCCNSSSSS.H..h.......",  # row 4: eyebrows + cyber eye halo
    "........gCCgSSSWWS...........",  # row 5: eyes row top
    "........MCCMSSSEESh..........",  # row 6: eyes row bottom
    "........nnnSSfSSSSh..........",  # row 7: nose
    "........HHHHHHHHHHh..........",  # row 8: beard start
    "........hHLHLHLHLHh..........",  # row 9: beard middle
    "........hHLHHHLHHHh..........",  # row 10: beard
    ".........hHLHLHLHh...........",  # row 11: chin
    "..........jKKKKKKJJ..........",  # row 12: collar
    ".........JJKKKKKKJJJ.........",  # row 13: collar/shoulder
    "......jjjjJJDDDDJJJJKK.......",  # row 14: torso top + arms start
    "......AaCcjJDDDDJJJJKJ.......",  # row 15: cyber arm glow + torso
    "......AaCcjJJJJJJJJJJJ.......",  # row 16: torso
    "......AGCcjJJJJJJJJJJJ.......",  # row 17: torso
    "......AaCcjJJDDJjjJJJJ.......",  # row 18: torso + pocket
    "......AGCcjJJJJJjkJJJJ.......",  # row 19: torso
    "......AaCcjJJJJJjkJJJJ.......",  # row 20: torso
    "......AGCcjJJJJJjjJJJJ.......",  # row 21: torso
    "......zACcjJJJJJJJJJss.......",  # row 22: torso lower
    "......zAAAjJJJJJJJJJss.......",  # row 23: torso lower
    "......AaAAAAJJJJJJJJSSs......",  # row 24: hands level
    "......AaAAAAJJJJJJJJSSs......",  # row 25: hands
    "......AaAAAAJJJJJJJJsSs......",  # row 26: hands
    "..............jjjjjj..........",  # row 27: belt line
    ".............EOOOEEE..........",  # row 28: belt + buckle
    "..........pPPP....pPPP.......",  # row 29: legs start
    "..........PPPP....PPPP.......",  # row 30: legs
    "..........PPPP....PPPP.......",  # row 31: legs
    "..........PPPP....PPPP.......",  # row 32: legs
    "..........PPPP....PPPP.......",  # row 33: legs
    "..........pPPP....PPpP.......",  # row 34: legs
    "..........PPPP....PPPP.......",  # row 35: legs
    "..........PPPP....PPPP.......",  # row 36: legs
    "..........qPPP....PPqP.......",  # row 37: legs bottom
    "..........qPPP....PPqP.......",  # row 38: legs bottom
    ".........bBbBB....bBbBB......",  # row 39: boots top
    ".........BEBBB....BBBEB......",  # row 40: boots lacing
    ".........BBEBB....BBBEB......",  # row 41: boots lacing
    ".........BEBB.....BBBEB......",  # row 42: boots
    ".........BBBBB....BBBBB......",  # row 43: boots
    ".........BBBBB....BBBBB......",  # row 44: boots
    ".........BBBBB....BBBBB......",  # row 45: boots
    ".........VVVVV....VVVVV......",  # row 46: sole
    ".........VVVVV....VVVVV......",  # row 47: sole
]

# Idle frame 1: slight breathing (1px bob on torso/head)
GIG_IDLE_1 = [
    "..............................",  # row 0: empty (bob down)
    "........LHLHLHLHhh..........",  # row 1
    "........HHHHHHHHHh..........",  # row 2
    ".......LHHHHHHHHhHhh........",  # row 3
    "........FFFFSSSSsH..h.......",  # row 4
    "........NCCNSSSSS...........",  # row 5
    "........gCCgSSSWWS..........",  # row 6
    "........MCCMSSSEESh.........",  # row 7
    "........nnnSSfSSSSh.........",  # row 8
    "........HHHHHHHHHHh.........",  # row 9
    "........hHLHLHLHLHh.........",  # row 10
    "........hHLHHHLHHHh.........",  # row 11
    ".........hHLHLHLHh...........",  # row 12
    "..........jKKKKKKJJ..........",  # row 13
    ".........JJKKKKKKJJJ.........",  # row 14
    "......jjjjJJDDDDJJJJKK.......",  # row 15
    "......AaCcjJDDDDJJJJKJ.......",  # row 16
    "......AaCcjJJJJJJJJJJJ.......",  # row 17
    "......AGCcjJJJJJJJJJJJ.......",  # row 18
    "......AaCcjJJDDJjjJJJJ.......",  # row 19
    "......AGCcjJJJJJjkJJJJ.......",  # row 20
    "......AaCcjJJJJJjkJJJJ.......",  # row 21
    "......AGCcjJJJJJjjJJJJ.......",  # row 22
    "......zACcjJJJJJJJJJss.......",  # row 23
    "......zAAAjJJJJJJJJJss.......",  # row 24
    "......AaAAAAJJJJJJJJSSs......",  # row 25
    "......AaAAAAJJJJJJJJSSs......",  # row 26
    "......AaAAAAJJJJJJJJsSs......",  # row 27
    ".............EOOOEEE..........",  # row 28
    "..........pPPP....pPPP.......",  # row 29
    "..........PPPP....PPPP.......",  # row 30
    "..........PPPP....PPPP.......",  # row 31
    "..........PPPP....PPPP.......",  # row 32
    "..........PPPP....PPPP.......",  # row 33
    "..........pPPP....PPpP.......",  # row 34
    "..........PPPP....PPPP.......",  # row 35
    "..........PPPP....PPPP.......",  # row 36
    "..........qPPP....PPqP.......",  # row 37
    "..........qPPP....PPqP.......",  # row 38
    ".........bBbBB....bBbBB......",  # row 39
    ".........BEBBB....BBBEB......",  # row 40
    ".........BBEBB....BBBEB......",  # row 41
    ".........BEBB.....BBBEB......",  # row 42
    ".........BBBBB....BBBBB......",  # row 43
    ".........BBBBB....BBBBB......",  # row 44
    ".........BBBBB....BBBBB......",  # row 45
    ".........VVVVV....VVVVV......",  # row 46
    ".........VVVVV....VVVVV......",  # row 47
]

# Run frame 0: left leg forward, right arm forward
GIG_RUN_0 = [
    "........LHLHLHLHhh..........",  # row 0
    "........HHHHHHHHHh..........",  # row 1
    ".......LHHHHHHHHhHhh........",  # row 2
    "........FFFFSSSSsH...........",  # row 3
    "........hhhESSSSS...........",  # row 4
    "........gCCgSSSWWS..........",  # row 5
    "........MCCMSSSEESh.........",  # row 6
    "........nnnSSfSSSSh.........",  # row 7
    "........HHHHHHHHHHh.........",  # row 8
    "........hHLHLHLHLHh.........",  # row 9
    "........hHLHHHLHHHh.........",  # row 10
    ".........hHLHLHLHh...........",  # row 11
    "..........jKKKKKKJJ..........",  # row 12
    ".........JJKKKKKKJJJ.........",  # row 13
    "......AajjJJDDDDJJJJKKJJ.....",  # row 14: arms pumped
    "......AACcjJDDDDJJJJJJSS.....",  # row 15
    "......AACcjJJJJJJJJJJSSS.....",  # row 16
    "......AGCcjJJJJJJJJJJJ.......",  # row 17
    "......AACcjJJDDJjjJJJJ.......",  # row 18
    "......AGCcjJJJJJjkJJJJ.......",  # row 19
    "......AACcjJJJJJjkJJJJ.......",  # row 20
    "......AAJJjJJJJJjjJJJJ.......",  # row 21: cyber arm fist lower
    "......zzzzjJJJJJJJJJ.........",  # row 22
    "......AAAzjJJJJJJJJJ.........",  # row 23
    "......AaAAAAJJJJJJJJJ........",  # row 24
    "......AaAAAAJJJJJJJJJ........",  # row 25
    "......AaAAAAJJJJJJJJJ........",  # row 26
    "..............jjjjjj..........",  # row 27
    ".............EOOOEEE..........",  # row 28
    "..........pPPP......pPPP.....",  # row 29: left leg forward
    "..........PPPP......PPPP.....",  # row 30
    "..........PPPP......PPPP.....",  # row 31
    "..........PPPP......PPPP.....",  # row 32
    "..........PPPP......PPPP.....",  # row 33
    "..........PPPP......PPPP.....",  # row 34
    "..........PPPP......PPPP.....",  # row 35
    "..........PPPP......PPPP.....",  # row 36
    "..........PPPP......PPPP.....",  # row 37
    "..........PPPP......PPPP.....",  # row 38
    ".........bBbBB......bBbBB....",  # row 39
    ".........BBBBB......BBBBB....",  # row 40
    ".........BBBBB......BBBBB....",  # row 41
    ".........BBBBB......BBBBB....",  # row 42
    ".........BBBBB......BBBBB....",  # row 43
    ".........BBBBB......BBBBB....",  # row 44
    ".........BBBBB......BBBBB....",  # row 45
    ".........VVVVV......VVVVV....",  # row 46
    ".........VVVVV......VVVVV....",  # row 47
]

# Run frame 1: passing position (legs together, bob up)
GIG_RUN_1 = [
    "........LHLHLHLHhh..........",
    "........HHHHHHHHHh..........",
    ".......LHHHHHHHHhHhh........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "......AajjJJDDDDJJJJKK.......",
    "......AACcjJDDDDJJJJKJ.......",
    "......AACcjJJJJJJJJJJJ.......",
    "......AGCcjJJJJJJJJJJJ.......",
    "......AACcjJJDDJjjJJJJ.......",
    "......AGCcjJJJJJjkJJJJ.......",
    "......AACcjJJJJJjkJJJJ.......",
    "......zzzzjJJJJJjjJJJJ.......",
    "......AAAzjJJJJJJJJJss.......",
    "......AAjjjJJJJJJJJJss.......",
    "......AaAAAAJJJJJJJJSSs......",
    "......AaAAAAJJJJJJJJSSs......",
    "......AaAAAAJJJJJJJJsSs......",
    "..............jjjjjj..........",
    ".............EOOOEEE..........",
    "..........pPPPpPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPP.PPP...........",
    "..........PPPP.PPP...........",
    "..........PPPP.PPP...........",
    "..........PPPP.PPP...........",
    ".........bBbBBbBbBB..........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........VVVVV.VVVVV.........",
    ".........VVVVV.VVVVV.........",
]

# Run frame 2: right leg forward, left arm forward
GIG_RUN_2 = [
    "........LHLHLHLHhh..........",
    "........HHHHHHHHHh..........",
    ".......LHHHHHHHHhHhh........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "..AAaajjjjJJDDDDJJJJKK.......",  # cyber arm forward
    "..AACCccjjJJDDDDJJJJKJ.......",
    "..AACCccjjJJJJJJJJJJJ.......",
    "......AGCcjJJJJJJJJJJJ.......",
    "......AACcjJJDDJjjJJJJ.......",
    "......AGCcjJJJJJjkJJJJ.......",
    "......AACcjJJJJJjkJJJJ.......",
    "..........jJJJJJjjJJJJ.......",
    "..........jJJJJJJJJJJJ.......",
    "..........jJJJJJJJJJss.......",
    ".............JJJJJJJJss.......",
    ".............JJJJJJJJSSs......",
    ".............JJJJJJJJsSs......",
    "..............jjjjjj..........",
    ".............EOOOEEE..........",
    ".....pPPP......pPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    ".....PPPP......PPPP..........",
    "....bBbBB......bBbBB.........",
    "....BBBBB......BBBBB.........",
    "....BBBBB......BBBBB.........",
    "....BBBBB......BBBBB.........",
    "....BBBBB......BBBBB.........",
    "....BBBBB......BBBBB.........",
    "....BBBBB......BBBBB.........",
    "....VVVVV......VVVVV.........",
    "....VVVVV......VVVVV.........",
]

# Run frame 3: passing position (opposite phase)
GIG_RUN_3 = GIG_RUN_1  # Same as frame 1, symmetric passing

# Punch frame 1 (right arm fully extended with fist)
GIG_PUNCH0_1 = [
    "........LHLHLHLHhh..........",
    "........HHHHHHHHHh..........",
    ".......LHHHHHHHHhHhh........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "......jjjjJJDDDDJJJJKK.......",
    "......AaCcjJDDDDJJJJKJ.......",
    "......AaCcjJJJJJJJJJJJ.......",
    "......AGCcjJJJJJJJJJJJ.......",
    "......AaCcjJJDDJKKKKKKKKFSOY.",  # arm extended at row 18
    "......AGCcjJJJJJjkJJJJ.......",
    "......AaCcjJJJJJjkJJJJ.......",
    "......AGCcjJJJJJjjJJJJ.......",
    "......zACcjJJJJJJJJJ.........",
    "......zAAAjJJJJJJJJJ.........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "..............jjjjjj..........",
    ".............EOOOEEE..........",
    "..........pPPP....pPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........pPPP....PPpP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........qPPP....PPqP.......",
    "..........qPPP....PPqP.......",
    ".........bBbBB....bBbBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........VVVVV....VVVVV......",
    ".........VVVVV....VVVVV......",
]

# Kick frame 1 (right leg extended)
GIG_KICK_1 = [
    "........LHLHLHLHhh..........",
    "........HHHHHHHHHh..........",
    ".......LHHHHHHHHhHhh........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "......jjjjJJDDDDJJJJKK.......",
    "......AaCcjJDDDDJJJJKJ.......",
    "......AaCcjJJJJJJJJJJJ.......",
    "......AGCcjJJJJJJJJJJJ.......",
    "......AaCcjJJDDJjjJJJJ.......",
    "......AGCcjJJJJJjkJJJJ.......",
    "......AaCcjJJJJJjkJJJJ.......",
    "......AGCcjJJJJJjjJJJJ.......",
    "......zACcjJJJJJJJJJss.......",
    "......zAAAjJJJJJJJJJss.......",
    "......AaAAAAJJJJJJJJSSs......",
    "......AaAAAAJJJJJJJJSSs......",
    "......AaAAAAJJJJJJJJsSs......",
    "..............jjjjjj..........",
    ".............EOOOEEE..........",
    "..........pPPP................",
    "..........PPPP................",
    "..........PPPP.PPPPPPPPPPPbBOY",  # kick line
    "..........PPPP.PPPPPPPPPPBBb..",
    "..........PPPP................",
    "..........pPPP................",
    "..........PPPP................",
    "..........PPPP................",
    "..........qPPP................",
    "..........qPPP................",
    ".........bBbBB................",
    ".........BBBBB................",
    ".........BBBBB................",
    ".........BBBBB................",
    ".........BBBBB................",
    ".........BBBBB................",
    ".........BBBBB................",
    ".........VVVVV................",
    ".........VVVVV................",
]

# Jump frame 0 (legs tucked up)
GIG_JUMP_0 = [
    "........LHLHLHLHhH..........",
    "........HHHHHHHHHhL.........",
    ".......LHHHHHHHHhh..........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "......jjjjJJDDDDJJJJKK.......",
    "......AaCcjJDDDDJJJJKKJJ.....",  # arms slightly raised
    "......AaCcjJJJJJJJJJJSSS.....",
    "......AGCcjJJJJJJJJJJSSS.....",
    "......AACcjJJDDJjjJJJJ.......",
    "......AGCcjJJJJJjkJJJJ.......",
    "......AACcjJJJJJjkJJJJ.......",
    "......AGCcjJJJJJjjJJJJ.......",
    "......zACcjJJJJJJJJJ.........",
    "......zAAAjJJJJJJJJJ.........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "..............jjjjjj..........",
    ".............EOOOEEE..........",
    "..............EOOE............",
    "..........pPPPpPPP...........",  # legs tucked
    "..........PPPPPPPP...........",
    "..........PPPPPPPP...........",
    "..........PPPP.PPP...........",
    "..........PPPP.PPP...........",
    "..........PPPP.PPP...........",
    ".........bBbBBbBbBB..........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........BBBBB.BBBBB.........",
    ".........VVVVV.VVVVV.........",
    ".........VVVVV.VVVVV.........",
    "..............................",
    "..............................",
    "..............................",
    "..............................",
]

# Fall frame 0 (arms spread, legs down, ponytail up)
GIG_FALL_0 = [
    "........LHLHLHLHhHL.........",  # ponytail flows up
    "........HHHHHHHHHhH.........",
    ".......LHHHHHHHHhh..........",
    "........FFFFSSSSsH...........",
    "........hhhESSSSS...........",
    "........gCCgSSSWWS..........",
    "........MCCMSSSEESh.........",
    "........nnnSSfSSSSh.........",
    "........HHHHHHHHHHh.........",
    "........hHLHLHLHLHh.........",
    "........hHLHHHLHHHh.........",
    ".........hHLHLHLHh...........",
    "..........jKKKKKKJJ..........",
    ".........JJKKKKKKJJJ.........",
    "....AAjjjjJJDDDDJJJJKKJJ.....",  # arms wide
    "....AACcjjJJDDDDJJJJJJSS.....",
    "....AACcjjJJJJJJJJJJJJSSS....",
    "......AGCcjJJJJJJJJJJJ.......",
    "......AACcjJJDDJjjJJJJ.......",
    "......AGCcjJJJJJjkJJJJ.......",
    "......AACcjJJJJJjkJJJJ.......",
    "......AGCcjJJJJJjjJJJJ.......",
    "......zACcjJJJJJJJJJ.........",
    "......zAAAjJJJJJJJJJ.........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "......AaAAAAJJJJJJJJJ........",
    "..........jjjjjjjjjjj........",
    ".............EOOOEEE..........",
    "..........pPPP....pPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........pPPP....PPpP.......",
    "..........PPPP....PPPP.......",
    "..........PPPP....PPPP.......",
    "..........qPPP....PPqP.......",
    "..........qPPP....PPqP.......",
    ".........bBbBB....bBbBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........BBBBB....BBBBB......",
    ".........VVVVV....VVVVV......",
    ".........VVVVV....VVVVV......",
]


def _build_gig_frame(matrix):
    """Build a GIG surface from a matrix."""
    return _matrix_to_surface(matrix, GIG_COLORS, GIG_CANVAS_W, GIG_CANVAS_H)


# ===================================================================
# THUG Color Map
# ===================================================================

THUG_COLORS = {
    '.': None,
    '#': OUTLINE,
    'R': (230, 50, 70),       # bandana
    'r': (180, 30, 55),       # bandana shadow
    'f': (255, 80, 100),      # bandana fold
    'S': (190, 150, 110),     # skin
    'F': (210, 170, 130),     # skin highlight
    's': (155, 120, 85),      # skin shadow
    'T': (60, 20, 20),        # shirt dark
    't': (40, 12, 12),        # shirt shadow
    'h': (80, 30, 30),        # shirt highlight
    'D': (50, 55, 60),        # dark gray
    'X': (100, 50, 50),       # skull marking
    'E': (0, 0, 0),           # eyes/black
    'P': (50, 55, 60),        # pants
    'p': (65, 70, 78),        # pants highlight
    'q': (35, 38, 45),        # pants shadow
    'B': (0, 0, 0),           # boots (black)
    'b': (30, 30, 30),        # boots highlight
    'V': (15, 12, 10),        # boots sole
    'G': (200, 180, 80),      # brass
    'g': (230, 210, 120),     # brass highlight
    'O': (255, 122, 26),      # orange
    'Y': (255, 220, 50),      # yellow
}

THUG_IDLE_0 = [
    "..........RRRRRRRRRRRr......",  # row 0: bandana
    "..........rfRRfRRfRRRr......",  # row 1: bandana folds
    "..........RRRRRRRRRRRRh.....",  # row 2: bandana bottom + knot
    "..........FFFSSSSSSSs..r....",  # row 3: head top
    "..........EEEsSSSSSsSs..r...",  # row 4: eyebrows
    "..........sEESSSSSEEs...r...",  # row 5: eyebrows / eyes
    "..........SSESSSSSEESs......",  # row 6: eyes
    "..........SSSSSSSSSSSs......",  # row 7: face
    "..........SSSSSSSSSSss......",  # row 8: face
    "..........sEEEEsssSSs.......",  # row 9: scowl
    "..........SSSSSSSSSSss......",  # row 10: chin
    "..........sSSSSSSSSss.......",  # row 11: jaw
    ".......tttDDDDDDDDDDTTTTh...",  # row 12: shoulders
    ".......tttDDDDDDDDDDTTTTh...",  # row 13: shoulders
    ".......ttTTTTDDDDTTTTTTTh...",  # row 14: upper torso + arms
    "...SSsstTTTTDDDDTTTTTSSFh...",  # row 15: arms + skin
    "...SSFstTTTTTTTTTTTTTSSFh...",  # row 16
    "...SSFstTTTTTTTTTTTTTSSSh...",  # row 17
    "...SSsstTTTTTTTTTTTTTSSS....",  # row 18
    "...SSFstTTTXTTTTXTTTTSSF....",  # row 19: skull X
    "...SssstTTTTXTTXTTTTTSSF....",  # row 20
    "...SSsstTTTTTXXTTTTTTSSS....",  # row 21
    "...SSFstTTTTXTTXTTTTTSSF....",  # row 22
    "...SSsstTTTXTTTTXTTTTSSS....",  # row 23
    "...GgGGtTTTTTTTTTTTTTGgGG...",  # row 24: fists + brass
    "...SSSSttTTTTTTTTTTTTSSS....",  # row 25
    "...SSSSttTTTTTTTTTTTTSSS....",  # row 26
    "..........TTTTTTTTTTTt.......",  # row 27
    ".......EEEEEEEEEEEEEEEE.....",  # row 28: belt
    "........pPPPPP....PPPPPP....",  # row 29: legs
    "........PPPPPP....PPPPPP....",  # row 30
    "........PPPPPP....PPPPPP....",  # row 31
    "........PPPPPP....PPPPPP....",  # row 32
    "........PPPPPP....PPPPPP....",  # row 33
    "........PPPPPP....PPPPPP....",  # row 34
    "........PPPPPP....PPPPPP....",  # row 35
    "........PPPPPP....PPPPPP....",  # row 36
    "........qPPPPP....PPPPPq....",  # row 37
    "........qPPPPP....PPPPPq....",  # row 38
    "......bBBBBBBB....BBBBBBB...",  # row 39: boots
    "......bBBBBBBB....bBBBBBB...",  # row 40
    "......BBBBBBB.....BBBBBBB...",  # row 41
    "......BBBBBBB.....BBBBBBB...",  # row 42
    "......BBBBBBB.....BBBBBBB...",  # row 43
    "......BBBBBBB.....BBBBBBB...",  # row 44
    "......BBBBBBB.....BBBBBBB...",  # row 45
    "......VVVVVVVV....VVVVVVV...",  # row 46: sole
    "......VVVVVVVV....VVVVVVV...",  # row 47
]

THUG_ATTACK_1 = [
    "..........RRRRRRRRRRRr......",
    "..........rfRRfRRfRRRr......",
    "..........RRRRRRRRRRRRh.....",
    "..........FFFSSSSSSSs..r....",
    "..........EEEsSSSSSsSs..r...",
    "..........sEESSSSSEEs...r...",
    "..........SSESSSSSEESs......",
    "..........SSSSSSSSSSSs......",
    "..........SSSSSSSSSSss......",
    "..........sEEEEsssSSs.......",
    "..........SSSSSSSSSSss......",
    "..........sSSSSSSSSss.......",
    ".......tttDDDDDDDDDDTTTTh...",
    ".......tttDDDDDDDDDDTTTTh...",
    ".......ttTTTTDDDDTTTTTTTh...",
    "...SSsstTTTTDDDDTTTTTTTTh...",
    "...SSFstTTTTTTTTTTTTTTTTh...",
    "...SSFstTTTTTTTTTTSSSSSSSFOY",  # strike row - arm extended
    "...SSsstTTTTTTTTTTGgGGSSFOY.",  # brass knuckles + impact
    "...SSFstTTTXTTTTXTTTTT......",
    "...SssstTTTTXTTXTTTTT.......",
    "...SSsstTTTTTXXTTTTTT.......",
    "...SSFstTTTTXTTXTTTTT.......",
    "...SSsstTTTXTTTTXTTTT.......",
    "...GgGGtTTTTTTTTTTTTT.......",
    "...SSSSttTTTTTTTTTTTTT......",
    "...SSSSttTTTTTTTTTTTTT......",
    "..........TTTTTTTTTTTt.......",
    ".......EEEEEEEEEEEEEEEE.....",
    "........pPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........PPPPPP....PPPPPP....",
    "........qPPPPP....PPPPPq....",
    "........qPPPPP....PPPPPq....",
    "......bBBBBBBB....BBBBBBB...",
    "......bBBBBBBB....bBBBBBB...",
    "......BBBBBBB.....BBBBBBB...",
    "......BBBBBBB.....BBBBBBB...",
    "......BBBBBBB.....BBBBBBB...",
    "......BBBBBBB.....BBBBBBB...",
    "......BBBBBBB.....BBBBBBB...",
    "......VVVVVVVV....VVVVVVV...",
    "......VVVVVVVV....VVVVVVV...",
]


# ===================================================================
# DRONE Color Map
# ===================================================================

DRONE_COLORS = {
    '.': None,
    'B': (70, 75, 90),        # body
    'H': (95, 100, 118),      # body highlight
    'S': (45, 50, 65),        # body shadow
    'R': (230, 50, 70),       # red sensor
    'r': (180, 30, 55),       # red dim
    'P': (150, 160, 180, 120), # propeller blur
    'p': (120, 130, 150, 80), # propeller blur dim
    'L': (200, 210, 230),     # panel lines
    'A': (100, 105, 120),     # antenna
    'G': (0, 200, 80),        # green (hacked)
    'Y': (255, 220, 50),      # yellow (stunned)
    'E': (0, 0, 0),           # black
    'O': (255, 122, 26),      # orange running light
}


# ===================================================================
# WARDEN Color Map
# ===================================================================

WARDEN_COLORS = {
    '.': None,
    '#': OUTLINE,
    'A': (40, 45, 60),        # armor base
    'a': (60, 68, 88),        # armor highlight
    'Z': (25, 28, 40),        # armor shadow
    'R': (230, 50, 70),       # visor red
    'r': (180, 30, 55),       # visor dark
    'O': (255, 122, 26),      # orange trim
    'Y': (255, 220, 50),      # yellow
    'E': (0, 0, 0),           # black
    'C': (0, 229, 255),       # cyan
    'G': (0, 200, 80),        # green
    'S': (55, 62, 80),        # dark detail
    'P': (20, 20, 20),        # dark boots
    'D': (50, 55, 60),        # dark gray
}


WARDEN_IDLE_0 = [
    "................................................................",  # 0
    "................................................................",  # 1
    "................................................................",  # 2
    "................................................................",  # 3
    "....................aaAAAAAAAAAAAAaa.............................",  # 4
    "...................aAAAAAAAAAAAAAAAAa............................",  # 5
    "..................AAAAAAAAAAAAAAAAAaAa...........................",  # 6
    "..................AAArrrrrrrrrrRRAAA.............................",  # 7
    "..................AAArrRRRRRRRrRRAAA.............................",  # 8
    "..................AAArrRRRRRRRrRRAAA.............................",  # 9
    "..................AAArrrrrrrrrrRRAAA.............................",  # 10
    "..................AAAAAAAAAAAAAAAAAAA............................",  # 11
    "...................AAOOOAAAAAOOOAAA.............................",  # 12
    "....................AAAAAAAAAAAAA...............................",  # 13
    ".....................AAOOOOOAA..................................",  # 14
    ".............ZZZZZZZZAAAAAAAAAAAZZZZZZZZa.......................",  # 15
    "............ZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa.....................",  # 16
    "...........ZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa....................",  # 17
    "...........ZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa....................",  # 18
    "..........AaAAAAOOAAAAAAAAAAAAAOOAAAAAAAAAAAAa..................",  # 19
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.a..................",  # 20
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.a..................",  # 21
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.a..................",  # 22
    "..........AAAAAAAAAAAAAACCAAAAAAAAAAAAAAAAAAAAa..................",  # 23
    "..........AAAAAAAAAAAAAACCAAAAAAAAAAAAAAAAAAAAa..................",  # 24
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.a..................",  # 25
    "..........ZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZ...................",  # 26
    "..........ZAAAAAAAAOOOAAAAAOOOAAAAAAAAAAAAZ.....................",  # 27
    "...........ZAAAAAAAAAAAAAAAAAAAAAAAAAAAAZ.......................",  # 28
    "...........ZAAAAAAAAAAAAAAAAAAAAAAAAAAZ.........................",  # 29
    "............ZAAAAAAAAOAAAAAOAAAAAAAAZ..........................",  # 30
    "............ZZAAAAAAAAAAAAAAAAAAAZZZ...........................",  # 31
    ".............ZZAAAAAAAAAAAAAAAAAZZ.............................",  # 32
    "..............ZZZZAAAAAAAAAAZZZZ...............................",  # 33
    "...............ZZZAAAAAAAAZZZ..................................",  # 34
    "................ZZAAAAAAAAZZ...................................",  # 35
    "................ZAAAAAAAAZ.....................................",  # 36
    "................ZAAAAAAAAZ.....................................",  # 37
    "................ZAAAAAAAAZ.....................................",  # 38
    "...........OAAAAAAAAAAAAAAAAAAO................................",  # 39
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 40
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 41
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 42
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 43
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 44
    "...........AAAAAAAAA....AAAAAAAAA..............................",  # 45
    "..........OAAAAAAAAO...OAAAAAAAAO.............................",  # 46
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 47
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 48
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 49
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 50
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 51
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 52
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 53
    "..........AAAAAAAAA.....AAAAAAAAA.............................",  # 54
    ".........OAAAAAAAAAAO..OAAAAAAAAAAO...........................",  # 55
    ".........AAAAAAAAAA.....AAAAAAAAAA............................",  # 56
    ".........AAAAAAAAAA.....AAAAAAAAAA............................",  # 57
    ".........AAAAAAAAAA.....AAAAAAAAAA............................",  # 58
    ".........AAAAAAAAAA.....AAAAAAAAAA............................",  # 59
    ".........AAAAAAAAAA.....AAAAAAAAAA............................",  # 60
    ".........PPPPPPPPPP.....PPPPPPPPPP............................",  # 61
    ".........PPPPPPPPPP.....PPPPPPPPPP............................",  # 62
    ".........EEEEEEEEEE.....EEEEEEEEEE...........................",  # 63
    "................................................................",  # 64
    "................................................................",  # 65
    "................................................................",  # 66
    "................................................................",  # 67
    "................................................................",  # 68
    "................................................................",  # 69
    "................................................................",  # 70
    "................................................................",  # 71
]


# ===================================================================
# generate_gig_sprites -- main character
# ===================================================================

def generate_gig_sprites():
    """Generate all animation frames for GIG using the high-quality matrix system."""
    from ctrl_alt_revenge.core.sprite_matrix import build_gig_sprites
    sprites = build_gig_sprites(GIG_CANVAS_W, GIG_CANVAS_H)
    # Apply outlines to all frames
    for key, frames in sprites.items():
        for f in frames:
            _draw_outline(f)
    return sprites


def _generate_gig_sprites_legacy():
    """Legacy matrix-based generator — kept for reference."""
    sprites = {}
    CW, CH = GIG_CANVAS_W, GIG_CANVAS_H
    ox = (CW - PLAYER_WIDTH) // 2  # 6
    oy = CH - PLAYER_HEIGHT         # 0

    # --- IDLE (4 frames) ---
    idle_frames = []
    # Frame 0: base standing
    surf = _build_gig_frame(GIG_IDLE_0)
    _draw_outline(surf)
    idle_frames.append(surf)
    # Frame 1: breathing bob
    surf = _build_gig_frame(GIG_IDLE_1)
    _draw_outline(surf)
    idle_frames.append(surf)
    # Frame 2: glow phase (bright cyber glow)
    surf = _build_gig_frame(GIG_IDLE_0)
    # Enhance glow on frame 2
    for gy in [15, 17, 19]:
        _set_pixel(surf, 9, gy, (0, 255, 255))
        _set_pixel(surf, 10, gy, (0, 255, 255))
    _draw_outline(surf)
    idle_frames.append(surf)
    # Frame 3: ponytail sway (slight variation)
    surf = _build_gig_frame(GIG_IDLE_0)
    _draw_outline(surf)
    idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frames) ---
    run_frames = []
    for f, matrix in enumerate([GIG_RUN_0, GIG_RUN_1, GIG_RUN_2, GIG_RUN_3]):
        surf = _build_gig_frame(matrix)
        _draw_outline(surf)
        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (2 frames) ---
    jump_frames = []
    for jf in range(2):
        surf = _build_gig_frame(GIG_JUMP_0)
        if jf == 1:
            # Slight arm variation
            _set_pixel(surf, 26, 16, GIG_COLORS['K'])
        _draw_outline(surf)
        jump_frames.append(surf)
    sprites["jump_right"] = jump_frames
    sprites["jump_left"] = [_mirror_h(f) for f in jump_frames]

    # --- FALL (2 frames) ---
    fall_frames = []
    for ff in range(2):
        surf = _build_gig_frame(GIG_FALL_0)
        if ff == 1:
            # Coat tail flutter
            _set_pixel(surf, 12, 27, GIG_COLORS['j'])
            _set_pixel(surf, 28, 27, GIG_COLORS['j'])
        _draw_outline(surf)
        fall_frames.append(surf)
    sprites["fall_right"] = fall_frames
    sprites["fall_left"] = [_mirror_h(f) for f in fall_frames]

    # --- LAND (2 frames): squash + recover ---
    land_frames = []
    # Squash frame: compressed
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    # Wide stance boots
    _draw_rect(surf, 4+ox, 41, 6, 5, GIG_COLORS['B'])
    _set_pixel(surf, 5+ox, 41, GIG_COLORS['b'])
    _draw_rect(surf, 4+ox, 46, 6, 2, GIG_COLORS['V'])
    _draw_rect(surf, 20+ox, 41, 6, 5, GIG_COLORS['B'])
    _set_pixel(surf, 21+ox, 41, GIG_COLORS['b'])
    _draw_rect(surf, 20+ox, 46, 6, 2, GIG_COLORS['V'])
    _draw_rect(surf, 7+ox, 35, 4, 6, GIG_COLORS['P'])
    _draw_rect(surf, 19+ox, 35, 4, 6, GIG_COLORS['P'])
    _draw_rect(surf, 5+ox, 34, 20, 1, GIG_COLORS['E'])
    _draw_rect(surf, 7+ox, 20, 18, 14, GIG_COLORS['J'])
    _draw_rect(surf, 7+ox, 20, 3, 14, GIG_COLORS['j'])
    _draw_rect(surf, 22+ox, 20, 3, 4, GIG_COLORS['K'])
    _draw_rect(surf, 12+ox, 20, 6, 4, GIG_COLORS['D'])
    _draw_rect(surf, 24+ox, 22, 4, 8, GIG_COLORS['J'])
    _draw_rect(surf, 24+ox, 30, 4, 3, GIG_COLORS['S'])
    _draw_rect(surf, 1+ox, 22, 6, 8, GIG_COLORS['A'])
    _draw_rect(surf, 1+ox, 30, 6, 3, GIG_COLORS['A'])
    _set_pixel(surf, 3+ox, 23, GIG_COLORS['C'])
    _set_pixel(surf, 4+ox, 23, GIG_COLORS['C'])
    _set_pixel(surf, 3+ox, 25, GIG_COLORS['c'])
    _set_pixel(surf, 4+ox, 25, GIG_COLORS['c'])
    # Squashed head (shifted down 8px)
    _draw_rect(surf, 8+ox, 10, 12, 3, GIG_COLORS['H'])
    _draw_rect(surf, 8+ox, 13, 12, 6, GIG_COLORS['S'])
    _set_pixel(surf, 9+ox, 15, GIG_COLORS['C'])
    _set_pixel(surf, 10+ox, 15, GIG_COLORS['C'])
    _set_pixel(surf, 16+ox, 15, GIG_COLORS['W'])
    _set_pixel(surf, 17+ox, 15, GIG_COLORS['W'])
    _draw_rect(surf, 9+ox, 17, 8, 2, GIG_COLORS['H'])
    _draw_outline(surf)
    land_frames.append(surf)
    # Recover: slightly bent knees
    surf = _build_gig_frame(GIG_IDLE_0)
    _draw_outline(surf)
    land_frames.append(surf)
    sprites["land_right"] = land_frames
    sprites["land_left"] = [_mirror_h(f) for f in land_frames]

    # --- WALL SLIDE (1 frame) ---
    surf = _build_gig_frame(GIG_IDLE_0)
    # Overwrite right arm to reach up
    _draw_rect(surf, 25+ox, 6, 4, 14, GIG_COLORS['J'])
    _set_pixel(surf, 25+ox, 6, GIG_COLORS['K'])
    _draw_rect(surf, 25+ox, 6, 4, 3, GIG_COLORS['S'])
    _draw_outline(surf)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_rect(surf, 7+ox, 41, 5, 5, GIG_COLORS['B'])
    _set_pixel(surf, 8+ox, 41, GIG_COLORS['b'])
    _draw_rect(surf, 7+ox, 46, 5, 2, GIG_COLORS['V'])
    _draw_rect(surf, 18+ox, 41, 5, 5, GIG_COLORS['B'])
    _set_pixel(surf, 19+ox, 41, GIG_COLORS['b'])
    _draw_rect(surf, 18+ox, 46, 5, 2, GIG_COLORS['V'])
    _draw_rect(surf, 8+ox, 35, 4, 6, GIG_COLORS['P'])
    _draw_rect(surf, 18+ox, 35, 4, 6, GIG_COLORS['P'])
    _draw_rect(surf, 7+ox, 34, 18, 1, GIG_COLORS['E'])
    _draw_rect(surf, 7+ox, 22, 18, 12, GIG_COLORS['J'])
    _draw_rect(surf, 7+ox, 22, 3, 12, GIG_COLORS['j'])
    _draw_rect(surf, 22+ox, 22, 3, 3, GIG_COLORS['K'])
    _draw_rect(surf, 12+ox, 22, 6, 4, GIG_COLORS['D'])
    _draw_rect(surf, 24+ox, 24, 4, 8, GIG_COLORS['J'])
    _draw_rect(surf, 24+ox, 32, 4, 3, GIG_COLORS['S'])
    _draw_rect(surf, 1+ox, 24, 6, 8, GIG_COLORS['A'])
    _draw_rect(surf, 1+ox, 32, 6, 3, GIG_COLORS['A'])
    _set_pixel(surf, 3+ox, 25, GIG_COLORS['C'])
    _set_pixel(surf, 4+ox, 25, GIG_COLORS['C'])
    _set_pixel(surf, 3+ox, 27, GIG_COLORS['c'])
    _set_pixel(surf, 4+ox, 27, GIG_COLORS['c'])
    _draw_rect(surf, 8+ox, 12, 12, 3, GIG_COLORS['H'])
    _draw_rect(surf, 8+ox, 15, 12, 6, GIG_COLORS['S'])
    _set_pixel(surf, 9+ox, 17, GIG_COLORS['C'])
    _set_pixel(surf, 10+ox, 17, GIG_COLORS['C'])
    _set_pixel(surf, 16+ox, 17, GIG_COLORS['W'])
    _set_pixel(surf, 17+ox, 17, GIG_COLORS['W'])
    _draw_rect(surf, 9+ox, 19, 8, 2, GIG_COLORS['H'])
    _draw_outline(surf)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame) ---
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_rect(surf, 0+ox, 33, 6, 5, GIG_COLORS['B'])
    _set_pixel(surf, 1+ox, 33, GIG_COLORS['b'])
    _draw_rect(surf, 0+ox, 38, 6, 2, GIG_COLORS['V'])
    _draw_rect(surf, 0+ox, 29, 6, 4, GIG_COLORS['P'])
    _draw_rect(surf, 6+ox, 26, 20, 7, GIG_COLORS['J'])
    _draw_rect(surf, 6+ox, 26, 3, 7, GIG_COLORS['j'])
    _draw_rect(surf, 24+ox, 26, 2, 3, GIG_COLORS['K'])
    _draw_rect(surf, 10+ox, 26, 6, 4, GIG_COLORS['D'])
    _draw_rect(surf, 25+ox, 20, 10, 3, GIG_COLORS['H'])
    _draw_rect(surf, 25+ox, 23, 10, 8, GIG_COLORS['S'])
    _set_pixel(surf, 26+ox, 23, GIG_COLORS['F'])
    _draw_rect(surf, 25+ox, 29, 8, 3, GIG_COLORS['H'])
    _set_pixel(surf, 27+ox, 25, GIG_COLORS['C'])
    _set_pixel(surf, 28+ox, 25, GIG_COLORS['C'])
    _set_pixel(surf, 31+ox, 25, GIG_COLORS['W'])
    _set_pixel(surf, 32+ox, 25, GIG_COLORS['W'])
    _draw_outline(surf)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 combo moves, 3 frames each) ---
    for combo_idx in range(3):
        punch_frames = []
        arm_extend = 7 + combo_idx * 4
        arm_y = 18 - combo_idx * 2

        # Frame 0: wind-up
        surf = _build_gig_frame(GIG_IDLE_0)
        if combo_idx < 2:
            # Clear right arm area and draw pulled back
            _draw_rect(surf, ox, arm_y, 6, 4, GIG_COLORS['J'])
            _draw_rect(surf, ox-3, arm_y, 4, 4, GIG_COLORS['S'])
            _set_pixel(surf, ox-3, arm_y+1, GIG_COLORS['s'])
        else:
            # Kick wind-up: clear right leg, draw pulled back
            _draw_rect(surf, 5+ox, 30, 12, 4, GIG_COLORS['P'])
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 1: strike
        surf = _build_gig_frame(GIG_PUNCH0_1 if combo_idx == 0 else GIG_IDLE_0)
        if combo_idx == 1:
            # Second punch - higher arm
            _draw_rect(surf, 26+ox, arm_y, arm_extend, 4, GIG_COLORS['J'])
            _set_pixel(surf, 26+ox, arm_y, GIG_COLORS['K'])
            _draw_rect(surf, 26+ox+arm_extend-3, arm_y, 4, 4, GIG_COLORS['S'])
            _set_pixel(surf, 26+ox+arm_extend, arm_y, GIG_COLORS['F'])
            _set_pixel(surf, 26+ox+arm_extend+1, arm_y, GIG_COLORS['O'])
            _set_pixel(surf, 26+ox+arm_extend+1, arm_y+1, GIG_COLORS['Y'])
        elif combo_idx == 2:
            # Kick strike
            _draw_rect(surf, 24+ox, 33, arm_extend+4, 4, GIG_COLORS['P'])
            _draw_rect(surf, 24+ox+arm_extend+2, 32, 4, 5, GIG_COLORS['B'])
            _set_pixel(surf, 24+ox+arm_extend+5, 33, GIG_COLORS['O'])
            _set_pixel(surf, 24+ox+arm_extend+6, 34, GIG_COLORS['Y'])
        _draw_outline(surf)
        punch_frames.append(surf)

        # Frame 2: recovery
        surf = _build_gig_frame(GIG_IDLE_0)
        if combo_idx < 2:
            half_ext = arm_extend // 2
            _draw_rect(surf, 26+ox, arm_y, half_ext, 4, GIG_COLORS['J'])
            _draw_rect(surf, 26+ox+half_ext-2, arm_y, 4, 4, GIG_COLORS['S'])
        else:
            _draw_rect(surf, 24+ox, 33, 5, 4, GIG_COLORS['P'])
            _draw_rect(surf, 28+ox, 32, 4, 5, GIG_COLORS['B'])
        _draw_outline(surf)
        punch_frames.append(surf)

        sprites[f"punch{combo_idx}_right"] = punch_frames
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(f) for f in punch_frames]

    # --- KICK (3 frames) ---
    kick_frames = []
    # Wind-up
    surf = _build_gig_frame(GIG_IDLE_0)
    _draw_rect(surf, 5+ox, 30, 12, 4, GIG_COLORS['P'])
    _draw_outline(surf)
    kick_frames.append(surf)
    # Strike
    surf = _build_gig_frame(GIG_KICK_1)
    _draw_outline(surf)
    kick_frames.append(surf)
    # Recovery
    surf = _build_gig_frame(GIG_IDLE_0)
    _draw_rect(surf, 24+ox, 31, 5, 4, GIG_COLORS['P'])
    _draw_rect(surf, 28+ox, 30, 4, 5, GIG_COLORS['B'])
    _draw_outline(surf)
    kick_frames.append(surf)
    sprites["kick_right"] = kick_frames
    sprites["kick_left"] = [_mirror_h(f) for f in kick_frames]

    # --- PARRY (1 frame) ---
    surf = _build_gig_frame(GIG_IDLE_0)
    # Cyber arm raised in guard
    _draw_rect(surf, 8+ox, 10, 14, 4, GIG_COLORS['A'])
    _set_pixel(surf, 8+ox, 10, GIG_COLORS['a'])
    _draw_rect(surf, 8+ox, 10, 14, 1, GIG_COLORS['C'])
    for i in range(14):
        _set_pixel(surf, 7+ox, 8+i, GIG_COLORS['C'])
        _set_pixel(surf, 6+ox, 9+i, (0, 200, 255, 80))
    _draw_outline(surf)
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame) ---
    surf = _build_gig_frame(GIG_IDLE_0)
    for py in range(12, 28):
        for px in range(7+ox, 24+ox):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                nr = min(255, r + 80)
                surf.set_at((px, py), (nr, max(0, g-30), max(0, b-30), a))
    _draw_outline(surf)
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame) ---
    surf = _build_gig_frame(GIG_IDLE_0)
    # Draw hack interface
    for hy in range(6):
        for hx in range(6):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 12+hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx+PLAYER_WIDTH+ox, 12+hy, (0, 180, 60, 150))
    _draw_outline(surf)
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ===================================================================
# generate_thug_sprites -- Street enforcer
# ===================================================================

def _build_thug_frame(matrix):
    """Build a THUG surface from a matrix."""
    return _matrix_to_surface(matrix, THUG_COLORS, THUG_CANVAS_W, THUG_CANVAS_H)


def generate_thug_sprites():
    """Generate THUG sprites using the high-quality matrix system."""
    from ctrl_alt_revenge.core.thug_matrix import build_thug_sprites
    sprites = build_thug_sprites(THUG_CANVAS_W, THUG_CANVAS_H)
    for key, frames in sprites.items():
        for f in frames:
            _draw_outline(f)
    return sprites


def _generate_thug_sprites_legacy():
    sprites = {}
    CW, CH = THUG_CANVAS_W, THUG_CANVAS_H
    ox = (CW - THUG_WIDTH) // 2  # 6
    oy = CH - THUG_HEIGHT         # 0

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = _build_thug_frame(THUG_IDLE_0)
        if f == 1:
            _set_pixel(surf, 10+ox, 11, THUG_COLORS['T'])
            _set_pixel(surf, 17+ox, 11, THUG_COLORS['T'])
        _draw_outline(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames) -- use idle base with leg offsets
    walk_frames = []
    leg_off = [(0, 0), (3, -3), (0, 0), (-3, 3)]
    for f in range(4):
        surf = _build_thug_frame(THUG_IDLE_0)
        # Clear leg area and redraw with offsets
        lo1, lo2 = leg_off[f]
        if lo1 != 0 or lo2 != 0:
            # Clear original legs
            for cy in range(29, 48):
                for cx in range(0, CW):
                    if surf.get_at((cx, cy)).a > 0:
                        surf.set_at((cx, cy), (0, 0, 0, 0))
            # Redraw left leg
            _draw_rect(surf, 5+ox+lo1, 29, 6, 10, GIG_COLORS['P'])
            _set_pixel(surf, 5+ox+lo1, 29, GIG_COLORS['p'])
            _set_pixel(surf, 6+ox+lo1, 29, GIG_COLORS['p'])
            _draw_rect(surf, 2+ox+lo1, 39, 8, 7, (0, 0, 0))
            _set_pixel(surf, 3+ox+lo1, 39, (30, 30, 30))
            _draw_rect(surf, 2+ox+lo1, 46, 8, 2, (15, 12, 10))
            # Redraw right leg
            _draw_rect(surf, 17+ox+lo2, 29, 6, 10, GIG_COLORS['P'])
            _set_pixel(surf, 22+ox+lo2, 29, GIG_COLORS['p'])
            _draw_rect(surf, 18+ox+lo2, 39, 8, 7, (0, 0, 0))
            _set_pixel(surf, 19+ox+lo2, 39, (30, 30, 30))
            _draw_rect(surf, 18+ox+lo2, 46, 8, 2, (15, 12, 10))
        _draw_outline(surf)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK (3 frames)
    attack_frames = []
    # Wind-up
    surf = _build_thug_frame(THUG_IDLE_0)
    # Overwrite right arm pulled back
    _draw_rect(surf, ox-3, 18, 5, 4, THUG_COLORS['S'])
    _set_pixel(surf, ox-3, 18, THUG_COLORS['s'])
    _draw_rect(surf, ox-4, 17, 4, 5, THUG_COLORS['S'])
    _set_pixel(surf, ox-4, 17, THUG_COLORS['G'])
    _set_pixel(surf, ox-2, 17, THUG_COLORS['G'])
    _set_pixel(surf, ox-3, 17, THUG_COLORS['g'])
    _draw_outline(surf)
    attack_frames.append(surf)
    # Strike
    surf = _build_thug_frame(THUG_ATTACK_1)
    _draw_outline(surf)
    attack_frames.append(surf)
    # Recovery
    surf = _build_thug_frame(THUG_IDLE_0)
    _draw_rect(surf, 27+ox, 18, 4, 4, THUG_COLORS['S'])
    _draw_rect(surf, 30+ox, 17, 4, 5, THUG_COLORS['S'])
    _set_pixel(surf, 30+ox, 17, THUG_COLORS['G'])
    _set_pixel(surf, 33+ox, 17, THUG_COLORS['G'])
    _draw_outline(surf)
    attack_frames.append(surf)
    sprites["attack_right"] = attack_frames
    sprites["attack_left"] = [_mirror_h(f) for f in attack_frames]

    # ALERT
    surf = _build_thug_frame(THUG_IDLE_0)
    # Red-shift the shirt color
    for py in range(12, 28):
        for px in range(0, CW):
            r, g, b, a = surf.get_at((px, py))
            if a > 0 and r < 100 and g < 50:
                surf.set_at((px, py), (min(255, r + 170), g, b, a))
    _draw_rect(surf, 13+ox, 0, 2, 1, COLOR_RED_ALARM)
    _draw_outline(surf)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = _build_thug_frame(THUG_IDLE_0)
    for py in range(12, 28):
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
    surf = _build_thug_frame(THUG_IDLE_0)
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
    _draw_rect(surf, 0+ox, 37, 28, 7, THUG_COLORS['T'])
    _draw_rect(surf, 0+ox, 37, 4, 7, THUG_COLORS['t'])
    _draw_rect(surf, 22+ox, 35, 10, 9, THUG_COLORS['S'])
    _set_pixel(surf, 23+ox, 35, THUG_COLORS['F'])
    _draw_rect(surf, 22+ox, 33, 10, 3, THUG_COLORS['R'])
    _set_pixel(surf, 22+ox, 33, THUG_COLORS['r'])
    _draw_outline(surf)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ===================================================================
# generate_drone_sprites -- Surveillance drone
# ===================================================================

def _draw_drone_base(surf, propeller_frame=0, eye_bright=True, ox=4, oy=2):
    """Draw drone base. 32x20 on 40x24 canvas."""
    W, H = DRONE_WIDTH, DRONE_HEIGHT

    # Propeller blur (top)
    prop_color = (150, 160, 180, 120)
    prop_dim = (120, 130, 150, 80)
    if propeller_frame == 0:
        _draw_rect(surf, 2+ox, 0+oy, 10, 2, prop_color)
        _draw_rect(surf, 20+ox, 0+oy, 10, 2, prop_dim)
    else:
        _draw_rect(surf, 2+ox, 0+oy, 10, 2, prop_dim)
        _draw_rect(surf, 20+ox, 0+oy, 10, 2, prop_color)

    # Propeller mounts (2x3 pillars)
    _draw_rect(surf, 6+ox, 2+oy, 2, 3, (95, 100, 118))
    _draw_rect(surf, 24+ox, 2+oy, 2, 3, (95, 100, 118))

    # Main body: aerodynamic shape
    _draw_rect(surf, 4+ox, 5+oy, 24, 3, (95, 100, 118))  # highlight top
    _draw_rect(surf, 2+ox, 7+oy, 28, 6, (70, 75, 90))     # body
    _draw_rect(surf, 4+ox, 13+oy, 24, 3, (45, 50, 65))    # shadow bottom
    _draw_rect(surf, 6+ox, 16+oy, 20, 2, (45, 50, 65))    # chin

    # Panel lines
    _set_pixel(surf, 10+ox, 8+oy, (200, 210, 230))
    _set_pixel(surf, 10+ox, 11+oy, (200, 210, 230))
    _set_pixel(surf, 22+ox, 8+oy, (200, 210, 230))
    _set_pixel(surf, 22+ox, 11+oy, (200, 210, 230))

    # Sensor eye (3x3 center)
    eye_color = COLOR_RED_ALARM if eye_bright else (180, 30, 55)
    _draw_rect(surf, 14+ox, 8+oy, 3, 3, eye_color)
    # Dim ring around sensor
    _set_pixel(surf, 13+ox, 8+oy, (180, 30, 55))
    _set_pixel(surf, 17+ox, 8+oy, (180, 30, 55))
    _set_pixel(surf, 13+ox, 10+oy, (180, 30, 55))
    _set_pixel(surf, 17+ox, 10+oy, (180, 30, 55))

    # Antenna
    _set_pixel(surf, 16+ox, 4+oy, (100, 105, 120))
    _set_pixel(surf, 16+ox, 3+oy, (100, 105, 120))

    # Running lights
    _set_pixel(surf, 3+ox, 9+oy, COLOR_NEON_ORANGE)
    _set_pixel(surf, 28+ox, 9+oy, COLOR_NEON_ORANGE)


def generate_drone_sprites():
    """Generate DRONE sprites using the high-quality matrix system."""
    from ctrl_alt_revenge.core.drone_matrix import build_drone_sprites
    sprites = build_drone_sprites(DRONE_CANVAS_W, DRONE_CANVAS_H)
    for key, frames in sprites.items():
        for f in frames:
            _draw_outline(f)
    return sprites


def _generate_drone_sprites_legacy():
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

    # DEATH (2 frames)
    death_frames = []
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    _draw_drone_base(surf, 0, eye_bright=False, ox=ox, oy=oy)
    for py in range(CH):
        for px in range(CW):
            r, g, b, a = surf.get_at((px, py))
            if a > 0:
                surf.set_at((px, py), (min(255, r+60), max(0, g-20), max(0, b-20), a))
    _draw_outline(surf)
    death_frames.append(surf)
    # Explosion
    surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
    cx, cy = CW // 2, CH // 2
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            if dx*dx + dy*dy <= 36:
                if dx*dx + dy*dy <= 9:
                    _set_pixel(surf, cx+dx, cy+dy, COLOR_YELLOW)
                elif dx*dx + dy*dy <= 20:
                    _set_pixel(surf, cx+dx, cy+dy, COLOR_NEON_ORANGE)
                else:
                    _set_pixel(surf, cx+dx, cy+dy, COLOR_RED_ALARM)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ===================================================================
# generate_warden_sprites -- Boss
# ===================================================================

def _build_warden_frame(matrix):
    """Build a WARDEN surface from a matrix."""
    return _matrix_to_surface(matrix, WARDEN_COLORS, WARDEN_CANVAS_W, WARDEN_CANVAS_H)


def generate_warden_sprites():
    """Generate WARDEN BOSS sprites using the high-quality matrix system."""
    from ctrl_alt_revenge.core.warden_matrix import build_warden_sprites
    sprites = build_warden_sprites(WARDEN_CANVAS_W, WARDEN_CANVAS_H)
    for key, frames in sprites.items():
        for f in frames:
            _draw_outline(f)
    return sprites


def _generate_warden_sprites_legacy():
    sprites = {}
    CW, CH = WARDEN_CANVAS_W, WARDEN_CANVAS_H
    ox = (CW - WARDEN_WIDTH) // 2  # 8
    oy = (CH - WARDEN_HEIGHT) // 2  # 4

    # IDLE (2 frames)
    idle_frames = []
    for f in range(2):
        surf = _build_warden_frame(WARDEN_IDLE_0)
        if f == 1:
            _set_pixel(surf, 23+ox, 24+oy, (0, 255, 255))
            _set_pixel(surf, 24+ox, 24+oy, (0, 255, 255))
        _draw_outline_thick(surf)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frames) -- use idle base with leg offsets
    walk_frames = []
    for f in range(4):
        surf = _build_warden_frame(WARDEN_IDLE_0)
        off = [0, 3, 0, -3][f]
        if off != 0:
            # Clear legs and redraw with offset
            for cy in range(39, 64):
                for cx in range(0, CW):
                    if surf.get_at((cx, cy)).a > 0:
                        surf.set_at((cx, cy), (0, 0, 0, 0))
            # Left leg
            _draw_rect(surf, 8+ox+off, 39+oy, 12, 16, (40, 45, 60))
            _set_pixel(surf, 9+ox+off, 39+oy, (60, 68, 88))
            _draw_rect(surf, 8+ox+off, 46+oy, 12, 2, COLOR_NEON_ORANGE)
            _draw_rect(surf, 6+ox+off, 55+oy, 14, 9, (40, 45, 60))
            _set_pixel(surf, 7+ox+off, 55+oy, (60, 68, 88))
            _draw_rect(surf, 6+ox+off, 55+oy, 14, 1, COLOR_NEON_ORANGE)
            _draw_rect(surf, 6+ox+off, 63+oy, 14, 1, COLOR_BLACK)
            _draw_rect(surf, 6+ox+off, 61+oy, 14, 2, (20, 20, 20))
            # Right leg
            _draw_rect(surf, 28+ox-off, 39+oy, 12, 16, (40, 45, 60))
            _set_pixel(surf, 29+ox-off, 39+oy, (60, 68, 88))
            _draw_rect(surf, 28+ox-off, 46+oy, 12, 2, COLOR_NEON_ORANGE)
            _draw_rect(surf, 28+ox-off, 55+oy, 14, 9, (40, 45, 60))
            _set_pixel(surf, 29+ox-off, 55+oy, (60, 68, 88))
            _draw_rect(surf, 28+ox-off, 55+oy, 14, 1, COLOR_NEON_ORANGE)
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
            surf = _build_warden_frame(WARDEN_IDLE_0)
            # Extend right arm for melee strike
            arm_ext = 10 + f * 6 + m_idx * 3
            arm_start_x = WARDEN_WIDTH - 2 + ox
            _draw_rect(surf, arm_start_x, 23+oy, arm_ext, 5, (40, 45, 60))
            _set_pixel(surf, arm_start_x, 23+oy, (60, 68, 88))
            _draw_rect(surf, arm_start_x+arm_ext-4, 22+oy, 8, 8, COLOR_NEON_ORANGE)
            _draw_rect(surf, arm_start_x+arm_ext-3, 23+oy, 6, 6, COLOR_YELLOW)
            _draw_outline_thick(surf)
            melee_frames.append(surf)
        sprites[f"melee{m_idx}_right"] = melee_frames
        sprites[f"melee{m_idx}_left"] = [_mirror_h(f) for f in melee_frames]

    # SHOCKWAVE (1 frame)
    surf = _build_warden_frame(WARDEN_IDLE_0)
    for i in range(6):
        wave_w = (i + 1) * 8
        alpha = 255 - i * 40
        for wx in range(-wave_w, wave_w):
            px = CW // 2 + wx
            py_w = WARDEN_HEIGHT + oy + i
            if 0 <= px < CW and 0 <= py_w < CH:
                _set_pixel(surf, px, py_w, (*COLOR_NEON_ORANGE[:3], max(0, alpha)))
    _draw_outline_thick(surf)
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame)
    surf = _build_warden_frame(WARDEN_IDLE_0)
    # Both arms raised
    _draw_rect(surf, 2+ox, 7+oy, 6, 13, (40, 45, 60))
    _set_pixel(surf, 3+ox, 7+oy, (60, 68, 88))
    _draw_rect(surf, 40+ox, 7+oy, 6, 13, (40, 45, 60))
    _set_pixel(surf, 41+ox, 7+oy, (60, 68, 88))
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
    surf = _build_warden_frame(WARDEN_IDLE_0)
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
            surf = _build_warden_frame(WARDEN_IDLE_0)
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
# OBJECTS -- kept as direct draw (small sprites)
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
    """Heart for HUD, 11x11."""
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
