# core/drone_matrix.py — High-quality DRONE sprite matrices
import pygame
from ctrl_alt_revenge.core.sprite_matrix import matrix_to_surface, mirror_h


DRONE_COLORS = {
    '.': None,
    '#': (5, 3, 15),             # outline
    'M': (110, 120, 140),        # metal highlight
    'm': (80, 90, 110),          # metal base
    'd': (55, 62, 80),           # metal shadow
    'D': (35, 40, 55),           # metal deep shadow
    'R': (255, 80, 80),          # red eye bright
    'r': (200, 40, 50),          # red eye base
    'E': (0, 229, 255),          # cyan accent
    'e': (0, 150, 180),          # cyan dim
    'O': (255, 122, 26),         # thruster glow
    'Y': (255, 220, 80),         # thruster core
    'P': (200, 200, 220),        # propeller blur
    'p': (100, 100, 120),        # propeller dim
    'W': (245, 241, 216),        # white highlight
}


# DRONE FLY frame 0 — sleek aerodynamic body, propellers visible
DRONE_FLY_0 = [
    "..#######.........#######..",  # propeller blur top
    ".#PPPPPPP##......#PPPPPPP#.",
    "..#pppppp##......##pppppp#.",
    "....##mmM#........#mMmm##..",  # rotor mounts
    "......#MMmmmmMMMmmmmMM#....",  # top body
    ".....#MmmmddDDdddmmmMMm#...",  # body top with shading
    "....#MmmdEEEErrEEEEddmmm#..",  # cyan + red eye row
    "....#MmddEEERRRREEEdddmm#..",  # red eye middle
    "....#MmddEEEErrEEEEddmmm#..",  # cyan continues
    ".....#MmmmdddDDddddmmMM#...",  # body bottom
    "......#mmmmDDDDDDmmmmM#....",  # bottom edge
    "........##dOOOOYYOOd##.....",  # thruster glow
    ".........#OOYYYYYOO#.......",  # thruster core
    "..........#OOYYOO#.........",  # thruster fade
    "...........#O##O#..........",
]


# DRONE FLY frame 1 — propeller in different position
DRONE_FLY_1 = [
    "....###.............###....",
    "...#pP##P#.........#P##Pp#.",
    "..#PpppPPP##......##PPpppP#",  # propeller alternate
    ".....#mmM#........#mMmm#...",
    "......#MMmmmmMMMmmmmMM#....",
    ".....#MmmmddDDdddmmmMMm#...",
    "....#MmmdEEEErrEEEEddmmm#..",
    "....#MmddEEERRRREEEdddmm#..",
    "....#MmddEEEErrEEEEddmmm#..",
    ".....#MmmmdddDDddddmmMM#...",
    "......#mmmmDDDDDDmmmmM#....",
    "........##dOOOOYYOOd##.....",
    ".........#OOYYYYYOO#.......",
    "..........#OOYYOO#.........",
    "...........#OYYO#..........",
]


# SHOOTING — laser firing down
DRONE_SHOOT = [
    "..#######.........#######..",
    ".#PPPPPPP##......#PPPPPPP#.",
    "..#pppppp##......##pppppp#.",
    "....##mmM#........#mMmm##..",
    "......#MMmmmmMMMmmmmMM#....",
    ".....#MmmmddDDdddmmmMMm#...",
    "....#MmmdEEEERRRREEEddmmm#.",  # red eye glowing
    "....#MmddRRRRRRRRRRRRdmm#..",
    "....#MmddEEEERRRREEEddmmm#.",
    ".....#MmmmdddDDddddmmMM#...",
    "......#mmmmDDDDDDmmmmM#....",
    "........##dRRRRRRRRd##.....",  # laser charging
    ".........#RRRRRRRRRR#......",
    "...........#R#R#R#.........",  # laser beam fires down
    "...........#R#R#R#.........",
]


def build_drone_sprites(canvas_w, canvas_h):
    frames = {}
    def make(m):
        return matrix_to_surface(m, DRONE_COLORS, canvas_w, canvas_h)

    base_fly = [make(DRONE_FLY_0), make(DRONE_FLY_1)]
    base_shoot = [make(DRONE_SHOOT)]
    base_hacked = [make(DRONE_FLY_0)]
    base_stunned = [make(DRONE_FLY_0)]
    base_death = [make(DRONE_FLY_0), make(DRONE_FLY_1), make(DRONE_FLY_0)]

    # Tint hacked green
    for f in base_hacked:
        # Replace red pixels with green
        for y in range(f.get_height()):
            for x in range(f.get_width()):
                c = f.get_at((x, y))
                if c.r > 150 and c.g < 100 and c.b < 100:
                    f.set_at((x, y), (0, 255, 100, c.a))

    # Stun = yellow tint
    for f in base_stunned:
        for y in range(f.get_height()):
            for x in range(f.get_width()):
                c = f.get_at((x, y))
                if c.r > 150 and c.g < 100 and c.b < 100:
                    f.set_at((x, y), (255, 220, 50, c.a))

    frames["fly_left"] = base_fly
    frames["fly_right"] = [mirror_h(f) for f in base_fly]
    frames["shoot_left"] = base_shoot
    frames["shoot_right"] = [mirror_h(f) for f in base_shoot]
    frames["hacked_left"] = base_hacked
    frames["hacked_right"] = [mirror_h(f) for f in base_hacked]
    frames["stunned_left"] = base_stunned
    frames["stunned_right"] = [mirror_h(f) for f in base_stunned]
    frames["death_left"] = base_death
    frames["death_right"] = [mirror_h(f) for f in base_death]
    return frames
