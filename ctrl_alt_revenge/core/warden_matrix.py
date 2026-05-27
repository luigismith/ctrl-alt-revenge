# core/warden_matrix.py — High-quality WARDEN BOSS sprite matrices
import pygame
from ctrl_alt_revenge.core.sprite_matrix import matrix_to_surface, mirror_h


WARDEN_COLORS = {
    '.': None,
    '#': (5, 3, 15),             # outline (2px for boss)
    'A': (80, 88, 110),          # armor highlight
    'a': (50, 55, 75),            # armor base
    'd': (35, 40, 55),           # armor shadow
    'D': (20, 25, 35),           # armor deep shadow
    'R': (255, 80, 100),         # visor red bright
    'r': (200, 40, 60),           # visor red base
    'V': (255, 200, 200),        # visor center bright
    'O': (255, 122, 26),         # orange trim
    'o': (200, 90, 20),           # orange trim shadow
    'Y': (255, 220, 80),          # yellow accent
    'E': (0, 229, 255),           # cyan core bright
    'e': (0, 150, 180),           # cyan core dim
    'c': (0, 100, 130),           # cyan core deep
    'W': (245, 241, 216),         # white
}


# WARDEN IDLE — massive armored boss, imposing pose
WARDEN_IDLE_0 = [
    "...................##############...................",
    "................###aaaaaaaaaaaaaa###................",  # helmet top
    "..............##aAAAAAAAAAAAAAAAAAAa##..............",  # helmet
    ".............#aAAAAAAOOOOOOOOAAAAAAAAa#.............",  # orange trim band
    "............#aAAAAAOOoooooooOOAAAAAAAAa#............",
    "...........#aAAAAAOoooooooooooAAAAAAAAAa#...........",
    "..........#aAAAAAAAOOOOOOOOOAAAAAAAAAAAAa#..........",
    "..........#aAAAAAdddddddddddddddddAAAAAAa#..........",  # visor area starts
    ".........#aAAAAAdRRRRrRRRRRRRrRRRRdAAAAAAa#.........",  # visor row 1
    ".........#aAAAAAdRRRRVVVVVVVVRRRRRdAAAAAAa#.........",  # visor bright center
    ".........#aAAAAAdRRRRrRRRRRRRrRRRRdAAAAAAa#.........",  # visor row 3
    "..........#aAAAAAddddddddddddddddAAAAAAAA#..........",
    "..........#aAAAAAAAAAAaaaaaAAAAAAAAAAAAa#...........",
    "...........#aAAAAAAaaaaaaaaaaAAAAAAAAa#.............",  # neck
    "............##aaaAAAaaaaaaaaAAAAAaaa##..............",  # neck/shoulder line
    "............#OOOOOOOO##########OOOOOOOO#............",  # shoulder trim
    "..........#OAAOOOOOOAAAAAAAAAAAOOOOOAAO#............",
    "........##OAAAAOOOAAAAAAAAAAAAAOOOAAAAOO##..........",  # massive shoulder pads
    ".......#OAAAAAAO#aaAAAAAAAAAAAAa#OAAAAAAO#..........",
    "......#OAAAAAAAO#aAAAAAAAAAAAAAa#OAAAAAAAO#.........",
    ".....#OAAAAAAAAO#AAAAAAAAAAAAAAA#OAAAAAAAAO#........",
    ".....#OAAAAAAAAO#AAAAdddddddddAA#OAAAAAAAAO#........",  # chest plate starts
    ".....#OAAAAAAAAO#AAAdEEEEEEEEEEdAOAAAAAAAAA#........",
    "......#aaaaaaaaO#AAdEEEEEEcEEEEdAOAAAAAAAa#.........",  # core glow row 1
    "......#aAAAAAAaO#AAdEEEEcccEEEEdAOAAAAAAAa#.........",  # core
    "......#aAAAAAAaO#AAdEEEEEEEEEEEdAOAAAAAAAa#.........",  # core
    "......#aAAAAAAaO#AAdEEEEEEcEEEEdAOAAAAAAAa#.........",  # core
    "......#aAAAAAAaO#AAdEEEEEEEEEEdAOAAAAAAAAa#.........",  # core
    "......#aAAAAAAaO#AAAAdddddddddAAOAAAAAAAAa#.........",  # core ring bottom
    "......#aAAAAAAaO#AAAAAAAAAAAAAAAOAAAAAAAAa#.........",
    "......#aAAAAAAa##AAAAOOOOOOOOOAA##aAAAAAAa#.........",  # waist trim
    "......#aaaaaaaa##aaaAAOOOOOOOAaa##aaaaaaaa#.........",
    "......#OOOOOOO##aaaaAAAAAAAAAaaaa##OOOOOOO#.........",  # belt
    "......#YYYYYY####aaaaAAAAAAAAaaa####YYYYYY#.........",  # gauntlet/belt accents
    ".......######....#aaaaaaaaaaaaaa#....######.........",  # arms hidden behind body
    "................#aaaaaaaaaaaaaaa#...................",  # waist
    "...............#aAAAAAAAaaaAAAAAAa#.................",  # hip
    "..............#aAAAAAAAa#aAAAAAAAAa#................",  # leg split
    "..............#aAAAAAAa#.#AAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",  # thighs (thicker)
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aOOOOOOa#.#aOOOOOOa#.................",  # knee guards (orange trim)
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#adAAAAAa#.#aAAAAAda#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aOOOOOOa#.#aOOOOOOa#.................",  # boot trim
    ".............#aAAAAAAAa#.#aAAAAAAAa#................",  # boots wider
    "............#aAAAAAAAAa#.#aAAAAAAAAa#...............",
    "............#DDDDDDDDDD#.#DDDDDDDDDD#...............",  # boot soles
    ".............############..############..............",  # ground
]


# WARDEN MELEE — punching forward with glowing fist
WARDEN_MELEE = [
    "...................##############...................",
    "................###aaaaaaaaaaaaaa###................",
    "..............##aAAAAAAAAAAAAAAAAAAa##..............",
    ".............#aAAAAAAOOOOOOOOAAAAAAAAa#.............",
    "............#aAAAAAOOoooooooOOAAAAAAAAa#............",
    "...........#aAAAAAOoooooooooooAAAAAAAAAa#...........",
    "..........#aAAAAAAAOOOOOOOOOAAAAAAAAAAAAa#..........",
    "..........#aAAAAAdddddddddddddddddAAAAAAa#..........",
    ".........#aAAAAAdRRRRrRRRRRRRrRRRRdAAAAAAa#.........",
    ".........#aAAAAAdRRRRVVVVVVVVRRRRRdAAAAAAa#.........",
    ".........#aAAAAAdRRRRrRRRRRRRrRRRRdAAAAAAa#.........",
    "..........#aAAAAAddddddddddddddddAAAAAAAA#..........",
    "..........#aAAAAAAAAAAaaaaaAAAAAAAAAAAAa#...........",
    "...........#aAAAAAAaaaaaaaaaaAAAAAAAAa#.............",
    "............##aaaAAAaaaaaaaaAAAAAaaa##..............",
    "............#OOOOOOOO##########OOOOOOOO#OOOOOOOOOOOO",  # arm extended right!
    "..........#OAAOOOOOOAAAAAAAAAAAOOOOOAAOOOOOOOOOOOOOO",
    "........##OAAAAOOOAAAAAAAAAAAAAOOOAAAAAAAAAAAAAAAAOO",  # full arm out
    ".......#OAAAAAAO#aaAAAAAAAAAAAAa#OAAAAAAAAAAAAAAYYYY",  # fist with glow
    "......#OAAAAAAAO#aAAAAAAAAAAAAAa#OAAAAAAAAAAYYYYOOOO",
    ".....#OAAAAAAAAO#AAAAAAAAAAAAAAA#OAAAAAAAAAYYY##OOOO",
    ".....#OAAAAAAAAO#AAAAdddddddddAA#OAAAAAAAA#####.....",
    ".....#OAAAAAAAAO#AAAdEEEEEEEEEEdAOAAAAAAAA#.........",
    "......#aaaaaaaaO#AAdEEEEEEcEEEEdAOAAAAAAAa#.........",
    "......#aAAAAAAaO#AAdEEEEcccEEEEdAOAAAAAAAa#.........",
    "......#aAAAAAAaO#AAdEEEEEEEEEEEdAOAAAAAAAa#.........",
    "......#aAAAAAAaO#AAdEEEEEEcEEEEdAOAAAAAAAa#.........",
    "......#aAAAAAAaO#AAdEEEEEEEEEEdAOAAAAAAAAa#.........",
    "......#aAAAAAAaO#AAAAdddddddddAAOAAAAAAAAa#.........",
    "......#aAAAAAAaO#AAAAAAAAAAAAAAAOAAAAAAAAa#.........",
    "......#aAAAAAAa##AAAAOOOOOOOOOAA##aAAAAAAa#.........",
    "......#aaaaaaaa##aaaAAOOOOOOOAaa##aaaaaaaa#.........",
    "......#OOOOOOO##aaaaAAAAAAAAAaaaa##OOOOOOO#.........",
    "......#YYYYYY####aaaaAAAAAAAAaaa####YYYYYY#.........",
    ".......######....#aaaaaaaaaaaaaa#....######.........",
    "................#aaaaaaaaaaaaaaa#...................",
    "...............#aAAAAAAAaaaAAAAAAa#.................",
    "..............#aAAAAAAAa#aAAAAAAAAa#................",
    "..............#aAAAAAAa#.#AAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aOOOOOOa#.#aOOOOOOa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#adAAAAAa#.#aAAAAAda#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aAAAAAAa#.#aAAAAAAa#.................",
    "..............#aOOOOOOa#.#aOOOOOOa#.................",
    ".............#aAAAAAAAa#.#aAAAAAAAa#................",
    "............#aAAAAAAAAa#.#aAAAAAAAAa#...............",
    "............#DDDDDDDDDD#.#DDDDDDDDDD#...............",
    ".............############..############..............",
]


def build_warden_sprites(canvas_w, canvas_h):
    frames = {}
    def make(m):
        return matrix_to_surface(m, WARDEN_COLORS, canvas_w, canvas_h)

    base_idle = [make(WARDEN_IDLE_0), make(WARDEN_IDLE_0)]
    base_walk = [make(WARDEN_IDLE_0), make(WARDEN_IDLE_0)]
    base_melee = [make(WARDEN_MELEE), make(WARDEN_MELEE)]
    base_shockwave = [make(WARDEN_IDLE_0)]
    base_spawn = [make(WARDEN_IDLE_0)]
    base_hurt = [make(WARDEN_IDLE_0)]
    base_death = [make(WARDEN_IDLE_0), make(WARDEN_IDLE_0), make(WARDEN_IDLE_0), make(WARDEN_IDLE_0)]

    # Pulse the core color for animation frames
    # (Simple variation: brighten frame 1 of idle)

    keys = {
        "idle": base_idle,
        "walk": base_walk,
        "melee0": base_melee,
        "melee1": base_melee,
        "shockwave": base_shockwave,
        "spawn": base_spawn,
        "hurt": base_hurt,
        "death": base_death,
        # Phase variants — same sprites for now (can tint later)
        "idle_p2": base_idle,
        "walk_p2": base_walk,
        "idle_p3": base_idle,
        "walk_p3": base_walk,
    }

    for k, base in keys.items():
        frames[f"{k}_left"] = base
        frames[f"{k}_right"] = [mirror_h(f) for f in base]

    return frames
