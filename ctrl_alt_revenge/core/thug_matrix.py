# core/thug_matrix.py — High-quality THUG sprite matrices
import pygame
from ctrl_alt_revenge.core.sprite_matrix import matrix_to_surface, mirror_h


# THUG palette — bulky street thug with red bandana
THUG_COLORS = {
    '.': None,
    '#': (5, 3, 15),             # outline
    'R': (255, 90, 100),         # bandana highlight
    'r': (210, 50, 70),          # bandana base
    'q': (150, 30, 45),          # bandana shadow
    'S': (210, 170, 130),        # skin highlight
    's': (190, 150, 110),        # skin base
    'k': (150, 115, 85),         # skin shadow
    'G': (90, 35, 35),           # shirt highlight
    'g': (60, 20, 20),           # shirt base
    'd': (40, 10, 10),           # shirt shadow
    'P': (70, 75, 85),           # pants highlight
    'p': (50, 55, 60),           # pants base
    'q2': (30, 35, 40),          # pants shadow (unused char)
    'B': (45, 45, 50),           # boot highlight
    'b': (25, 25, 30),           # boot base
    'D': (10, 10, 12),           # boot sole
    'Y': (255, 220, 80),         # brass knuckle shine
    'W': (245, 241, 216),        # eye white
    'E': (200, 50, 50),          # angry eye
}


# THUG IDLE — bulky menacing pose
THUG_IDLE_0 = [
    "......#####################.",
    ".....#RRRRrrrqqqqqqqqRRR#...",  # bandana top with fold
    "....#RRrrrrrqqqqqqrrrrrr#q#.",  # bandana knot trailing right
    "....#rrrrqqqqqqqrrrqqqq#q##.",  # bandana tail
    "....#SSSssssksssssSSs#q#....",  # forehead
    "....#SssEEssssEEssSSs#......",  # angry eyes
    "....#SssEWssssEWssSSs#......",  # eye white
    "....#sssksssssssssss#.......",  # cheek
    "....#skssskkssskssSs#.......",  # mouth area
    "....#skkkkkkkkkkkkss#.......",  # chin
    ".....#sskkkkkkkkkss#........",  # jaw
    "......##sssssssss##.........",  # neck
    "....#GGGGGGGGGGGGGGGG#......",  # shirt collar
    "...#GgggggggggggggggggG#....",  # shoulder line (wide)
    "..#sGggdgggggggggggggggs#...",  # torso + wide shoulders
    ".#ssGggggggggggggggggggss#..",
    ".#ssGgggggggggdgggggggggss#.",
    ".#ssGgggggggggggggggggggss#.",
    ".#skGggggggggggggggggggkss#.",
    ".#sskGggggggggggggggggksss#.",  # torso sides
    "..#sskGgggdgggggggggggkss#..",
    "..#ssskGgggggggggggggksss#..",
    "...#sssk#ggdddddddggg#ksss#.",  # arms meet body
    "....#ssY#ggdggggggddg#Yss#..",  # fist with brass knuckle
    "....#YYY#ggggggggggdg#YYY#..",  # knuckles
    "....#Ys#gggggggggggdg#sY#...",
    ".....##ggGGGgggGGGgg##......",  # belt
    "......#pppppppppppp#........",  # hips
    "......#pPppppppppPp#........",
    "......#pPp#....#pPp#........",  # legs split
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#pPp#....#pPp#........",
    "......#ppp#....#ppp#........",
    "......#ppp#....#ppp#........",
    ".....#BbbbB#..#BbbbB#.......",  # boots (wider than gig's)
    ".....#BbbbB#..#BbbbB#.......",
    ".....#BbbbB#..#BbbbB#.......",
    ".....#DDDDD#..#DDDDD#.......",  # sole
    "......######..######........",
]


# THUG WALK — same pose, legs staggered
THUG_WALK = [
    "......#####################.",
    ".....#RRRRrrrqqqqqqqqRRR#...",
    "....#RRrrrrrqqqqqqrrrrrr#q#.",
    "....#rrrrqqqqqqqrrrqqqq#q##.",
    "....#SSSssssksssssSSs#q#....",
    "....#SssEEssssEEssSSs#......",
    "....#SssEWssssEWssSSs#......",
    "....#sssksssssssssss#.......",
    "....#skssskkssskssSs#.......",
    "....#skkkkkkkkkkkkss#.......",
    ".....#sskkkkkkkkkss#........",
    "......##sssssssss##.........",
    "....#GGGGGGGGGGGGGGGG#......",
    "...#GgggggggggggggggggG#....",
    "..#sGggdgggggggggggggggs#...",
    ".#ssGggggggggggggggggggss#..",
    ".#ssGgggggggggdgggggggggss#.",
    ".#ssGgggggggggggggggggggss#.",
    ".#skGggggggggggggggggggkss#.",
    ".#sskGggggggggggggggggksss#.",
    "..#sskGgggdgggggggggggkss#..",
    "..#ssskGgggggggggggggksss#..",
    "...#sssk#ggdddddddggg#ksss#.",
    "....#ssY#ggdggggggddg#Yss#..",
    "....#YYY#ggggggggggdg#YYY#..",
    "....#Ys#gggggggggggdg#sY#...",
    ".....##ggGGGgggGGGgg##......",
    "......#pppppppppppp#........",
    "......#pPppppppppPp#........",
    ".....#pPpp#....#pPp#........",  # left leg forward
    ".....#pPp#.....#pPp#........",
    ".....#pPp#.....#pPp#........",
    ".....#pPp#.....#pPp#........",
    ".....#pPp#.....#pPp#........",
    ".....#pPp#.....#pPp#........",
    ".....#pPp#.....#pPp#........",
    "....#pPp#......#ppp#........",
    "....#ppp#......#ppp#........",
    "....#ppp#......#ppp#........",
    "...#BbbbB#....#BbbbB#.......",
    "...#BbbbB#....#BbbbB#.......",
    "...#BbbbB#....#BbbbB#.......",
    "...#DDDDD#....#DDDDD#.......",
    "....#####......######.......",
]


# THUG ATTACK — punching, arm extended
THUG_ATTACK = [
    "......#####################.",
    ".....#RRRRrrrqqqqqqqqRRR#...",
    "....#RRrrrrrqqqqqqrrrrrr#q#.",
    "....#rrrrqqqqqqqrrrqqqq#q##.",
    "....#SSSssssksssssSSs#q#....",
    "....#SssEEssssEEssSSs#......",
    "....#SssEWssssEWssSSs#......",
    "....#sssksssssssssss#.......",
    "....#skssskkssskssSs#.......",
    "....#skkkkkkkkkkkkss#.......",
    ".....#sskkkkkkkkkss#........",
    "......##sssssssss##.........",
    "....#GGGGGGGGGGGGGGGG#......",
    "...#GgggggggggggggggggG#....",
    "..#sGggdgggggggggggggggs#...",
    ".#ssGggggggggggggggggggss#..",
    ".#ssGgggggggggdgggggggggssssskY",  # arm EXTENDED RIGHT
    ".#ssGggggggggggggggggggssskYY#.",
    ".#skGgggggggggggggggggggskYY##.",  # fist with knuckles
    ".#sskGggggggggggggggggksssk#...",
    "..#sskGgggdgggggggggggkss#.....",
    "..#ssskGgggggggggggggksss#.....",
    "...#sssk#ggdddddddggggkss#.....",  # left arm still at body
    "....#ssY#ggdggggggdgggsss#.....",
    "....#YYY#gggggggggggggss#......",
    "....#Ys#ggggggggggggggg#.......",
    ".....##ggGGGgggGGGgg##.........",
    "......#pppppppppppp#...........",
    "......#pPppppppppPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#pPp#....#pPp#...........",
    "......#ppp#....#ppp#...........",
    "......#ppp#....#ppp#...........",
    ".....#BbbbB#..#BbbbB#..........",
    ".....#BbbbB#..#BbbbB#..........",
    ".....#BbbbB#..#BbbbB#..........",
    ".....#DDDDD#..#DDDDD#..........",
    "......######..######...........",
]


def build_thug_sprites(canvas_w, canvas_h):
    frames = {}
    def make(m):
        return matrix_to_surface(m, THUG_COLORS, canvas_w, canvas_h)

    base_idle = [make(THUG_IDLE_0), make(THUG_IDLE_0)]
    base_walk = [make(THUG_WALK), make(THUG_IDLE_0), make(THUG_WALK), make(THUG_IDLE_0)]
    base_attack = [make(THUG_IDLE_0), make(THUG_ATTACK), make(THUG_IDLE_0)]
    base_hurt = [make(THUG_IDLE_0)]
    base_death = [make(THUG_IDLE_0), make(THUG_IDLE_0)]

    frames["idle_left"] = base_idle
    frames["idle_right"] = [mirror_h(f) for f in base_idle]
    frames["walk_left"] = base_walk
    frames["walk_right"] = [mirror_h(f) for f in base_walk]
    frames["attack_left"] = base_attack
    frames["attack_right"] = [mirror_h(f) for f in base_attack]
    frames["hurt_left"] = base_hurt
    frames["hurt_right"] = [mirror_h(f) for f in base_hurt]
    frames["alert_left"] = base_idle[:1]
    frames["alert_right"] = [mirror_h(base_idle[0])]
    frames["death_left"] = base_death
    frames["death_right"] = [mirror_h(f) for f in base_death]
    return frames
