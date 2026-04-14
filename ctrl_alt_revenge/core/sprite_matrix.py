# core/sprite_matrix.py — Matrix-based pixel art system
# Define sprites as ASCII art where each character = one pixel color
import pygame


def matrix_to_surface(matrix, color_map, width=None, height=None):
    """Convert an ASCII matrix to a pygame Surface.

    Args:
        matrix: list of strings, each string is one row of pixels
        color_map: dict mapping single characters to (r,g,b) tuples or None for transparent
        width/height: optional canvas dimensions (defaults to matrix size)
    """
    if not matrix:
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    matrix_h = len(matrix)
    matrix_w = max(len(row) for row in matrix)

    w = width if width is not None else matrix_w
    h = height if height is not None else matrix_h

    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # Center the matrix on the canvas
    offset_x = (w - matrix_w) // 2
    offset_y = h - matrix_h  # align to bottom

    for y, row in enumerate(matrix):
        for x, ch in enumerate(row):
            if ch in color_map:
                color = color_map[ch]
                if color is not None:
                    if len(color) == 3:
                        color = (*color, 255)
                    surf.set_at((x + offset_x, y + offset_y), color)

    return surf


def mirror_h(surf):
    """Mirror surface horizontally."""
    return pygame.transform.flip(surf, True, False)


# ============================================================
# COLOR PALETTES
# ============================================================

# GIG palette — grizzled cyberpunk protagonist
GIG_COLORS = {
    '.': None,                   # transparent
    '#': (5, 3, 15),             # outline (near-black)
    'H': (185, 180, 175),        # hair highlight
    'h': (160, 155, 150),        # hair base
    'g': (120, 115, 110),        # hair shadow
    'S': (230, 190, 150),        # skin highlight
    's': (210, 170, 130),        # skin base
    'k': (180, 140, 100),        # skin shadow
    'd': (140, 105, 70),         # skin deep shadow
    'E': (0, 229, 255),          # cyber glow bright
    'e': (0, 150, 180),          # cyber glow dim
    'W': (245, 241, 216),        # white (eye)
    'J': (200, 140, 65),         # jacket highlight
    'j': (180, 120, 50),         # jacket base
    'x': (140, 90, 35),          # jacket shadow
    'X': (100, 65, 25),          # jacket deep shadow
    'G': (60, 20, 20),           # shirt dark
    'A': (100, 112, 135),        # cyber arm highlight
    'a': (80, 90, 110),          # cyber arm base
    'c': (55, 62, 80),           # cyber arm shadow
    'P': (70, 75, 85),           # pants highlight
    'p': (50, 55, 60),           # pants base
    'q': (30, 35, 40),           # pants shadow
    'B': (140, 95, 50),          # boots highlight
    'b': (120, 80, 40),          # boots base
    'D': (80, 55, 25),           # boots shadow
    'O': (255, 122, 26),         # orange accent (belt buckle, glow)
    'Y': (255, 220, 50),         # yellow (impact, spark)
    'R': (255, 46, 77),          # red (hit, impact)
}


# ============================================================
# GIG SPRITES — 32 wide x 44 tall content (fits in 44x48 canvas)
# Character faces RIGHT in these definitions (cyber arm on left side)
# ============================================================

# IDLE frame 0 — standing pose, confident stance
GIG_IDLE_0 = [
    "........##########......",
    ".......#HHHHHhhgg#......",  # hair top
    "......#HHhhhhhhhgg##....",  # hair with ponytail start
    "......#HHhhhhhhhhg#g#...",  # ponytail trails right
    "......#HsssssssssSg##...",  # hair border/top of face
    "......#sSSSSSSSSSSs#....",  # forehead highlight
    "......#sSEEsssssSSs#....",  # cyber eye (EE) + human eye
    "......#sSEEsssWWSSs#....",  # cyber eye + eye white
    "......#sSsksssWdSSs#....",  # nose shadow
    "......#skssksssssSs#....",  # cheeks
    "......#sggghhhhhggs#....",  # mustache
    "......#sghhhhhhhggs#....",  # beard
    "......#sgghhhhhgg#s#....",  # beard
    ".......#sghhhhhg#ss#....",  # chin
    ".......#sghhhhs##.......",  # neck
    "......#JJJJJJJJJJJJ#....",  # collar line
    ".....#JjjjjjjjjjjjjJ#...",  # jacket top
    "....#aAAAc#jjGGjjjjjj#..",  # shoulders + cyber arm start
    "....#aEEec#jjGGGjjjjj#..",  # cyber arm glow segment 1
    "....#aAAAc#jjGGGjjjjj#..",  # arm
    "....#aEEec#jjGGjjjjjxx#.",  # cyber arm glow 2 + human arm
    "....#aAAAc#jjjjjjjjjsss#",  # arm + human arm (skin)
    "....#aEEec#jjjjjjjjjkkS#",  # cyber arm glow 3
    "....#aAAAc#jjjjjjxxjkss#",  # pocket start
    "....#aEEec#jjxxxxxxjxxx#",  # cyber arm glow 4
    "....#aAAAc#jxxxxxxxjjjj#",  # pocket
    ".....#aac##jjjjjjjjjjj#.",  # arm ends
    "......##g#jjjjjjjjjjj#..",  # hand at hip
    "........##OOOOOOOOO##...",  # belt with buckle
    "........#pppppppp#.#....",  # waist
    "........#pPppppppP#.....",  # hips
    "........#pPppppppP#.....",
    "........#pPpp#.#pP#.....",  # leg separation
    "........#pPp##.#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pqp#..#qp#.....",
    "........#ppp#..#pp#.....",
    ".......#BbbbB##BbbbB#...",  # boots top
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",  # boot detail
    ".......#DDDDD##DDDDD#...",  # sole
    "........######..######..",  # ground line
]


# IDLE frame 1 — slight breathing (shoulders up 1px)
GIG_IDLE_1 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",  # collar raised (breathing in)
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",  # shoulders UP 1px
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjj#..",
    "....#aAAAc#jjGGjjjjjxx#.",
    "....#aEEec#jjjjjjjjjsss#",
    "....#aAAAc#jjjjjjjjjkkS#",
    "....#aEEec#jjjjjjxxjkss#",
    "....#aAAAc#jjxxxxxxjxxx#",
    "....#aEEec#jxxxxxxxjjjj#",
    ".....#aac##jjjjjjjjjjj#.",
    "......##g#jjjjjjjjjjj#..",
    "........##OOOOOOOOO##...",
    "........#pppppppp#.#....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPpp#.#pP#.....",
    "........#pPp##.#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pqp#..#qp#.....",
    "........#ppp#..#pp#.....",
    ".......#BbbbB##BbbbB#...",
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",
    ".......#DDDDD##DDDDD#...",
    "........######..######..",
]


# RUN frame 0 — left leg forward, right arm forward
GIG_RUN_0 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjxxx#",  # human arm swings forward
    "....#aAAAc#jjGGGjjjjxss#",
    "....#aEEec#jjGGGjjjjxkS#",
    "....#aAAAc#jjGGjjjjjjxk#",
    "....#aEEec#jjjjjjjjjjjj#",
    "....#aAAAc#jjjjjjjjjjjj#",
    "....#aEEec#jjjjjjxxjjjj#",
    "....#aAAAc#jjxxxxxxjjjj#",
    "....#aEEec#jxxxxxxxjjjj#",
    ".....#aac##jjjjjjjjjjj#.",
    "......##g#jjjjjjjjjjj#..",
    "........##OOOOOOOOO##...",
    "........#pppppppp#.#....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPpp#..ppP#....",  # left leg forward
    "........#pPp#..pppP#....",
    "........#pPp#.pPppP#....",
    "........#pPp#.pPppP#....",
    "........#pq##.pPppP#....",
    "........#pp#..pPppP#....",
    ".......#pp#...pPppP#....",
    ".......#pp#...pqppP#....",
    "......#pp#....pppP#.....",
    "......#Bb#...#BbbbB#....",  # left boot forward
    "......#Bb#...#BbbbB#....",
    "......#Bb#...#BDDbB#....",
    ".....#DDD#...#DDDDD#....",
    "......####....######....",
]


# RUN frame 1 — passing position (both legs together, slight bob up)
GIG_RUN_1 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjj#..",
    "....#aAAAc#jjGGjjjjjxx#.",
    "....#aEEec#jjjjjjjjjsss#",
    "....#aAAAc#jjjjjjjjjkkS#",
    "....#aEEec#jjjjjjxxjkss#",
    "....#aAAAc#jjxxxxxxjxxx#",
    "....#aEEec#jxxxxxxxjjjj#",
    ".....#aac##jjjjjjjjjjj#.",
    "......##g#jjjjjjjjjjj#..",
    "........##OOOOOOOOO##...",
    "........#pppppppp#.#....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pqp#..#qp#.....",
    "........#ppp#..#pp#.....",
    "........#ppp#..#pp#.....",
    ".......#BbbbB##BbbbB#...",
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",
    ".......#DDDDD##DDDDD#...",
    "........######..######..",
]


# RUN frame 2 — right leg forward, left arm forward (mirror of 0)
GIG_RUN_2 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "..#aAAAc#jjjjjjjjjj#....",  # cyber arm swings forward
    "#aEEec#jjGGjjjjjjjjj#...",
    "#aAAAc#jjGGGjjjjjjjj#...",
    "#aEEec#jjGGGjjjjjjjj#...",
    ".#Eec#jjGGjjjjjjjjjxxx#.",
    "..##c#jjjjjjjjjjjjjjss#.",
    "....#jjjjjjjjjjjjjjjjj#.",
    "....#jjjjjjjjjxxjjjjjjk#",
    "....#jjjxxxxxxxjjjjjxxx#",
    "....#jjxxxxxxxxjjjjjjjj#",
    ".....#jjjjjjjjjjjjjjjj#.",
    "......#jjjjjjjjjjjjjj#..",
    "......##OOOOOOOOO##.....",
    "......#pppppppp#.#......",
    "......#pPppppppP#.......",
    "......#pPppppppP#.......",
    "......#pPpp#..ppP#......",  # right leg forward
    "......#pPp#..pppP#......",
    "......#pPp#.pPppP#......",
    "......#pPp#.pPppP#......",
    "......#pq##.pPppP#......",
    "......#pp#..pPppP#......",
    ".....#pp#...pPppP#......",
    ".....#pp#...pqppP#......",
    "....#pp#....pppP#.......",
    "....#Bb#...#BbbbB#......",
    "....#Bb#...#BbbbB#......",
    "....#Bb#...#BDDbB#......",
    "...#DDD#...#DDDDD#......",
    "....####....######......",
]


# RUN frame 3 — passing position (same as frame 1)
GIG_RUN_3 = GIG_RUN_1  # reuse


# JUMP — legs tucked, body leaning
GIG_JUMP_0 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjjxxx",  # arm up
    "....#aAAAc#jjGGjjjjjxss#",
    "....#aEEec#jjjjjjjjjxkS#",
    "....#aAAAc#jjjjjjjjjjxs#",
    "....#aEEec#jjjjjjxxjjjjx",
    "....#aAAAc#jjxxxxxxjjjjx",
    "....#aEEec#jxxxxxxxjjjj#",
    ".....#aac##jjjjjjjjjjj#.",
    "......##g#jjjjjjjjjjj#..",
    "........##OOOOOOOOO##...",
    ".......#ppppppppppp#....",
    "......#pPppppppppppP#...",
    "......#pPpp##...##pP#...",  # legs tucked up
    "......#pPp#......#Pp#...",
    ".....#pPp#........#Pp#..",
    "....#pPp#..........#Pp#.",
    "...#pPp#............#P#.",
    "..#pPp#..............#P#",
    "..#Pb#................#b",
    "..#BbbB#............#BbB",
    "..#BDDB#............#BDB",
    "..#DDDD#............#DDD",
    "...####................#",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]


# FALL — arms spread, legs down
GIG_FALL_0 = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "..#aAAAc##jjjjjjjjjj##xx",  # arms spread wide
    "#aEEec#Jjjjjjjjjjjjjjxss",
    "#aAAAc#jjGGjjjjjjjjjkxkS",
    "#aEEec#jjGGGjjjjjjjjxxxs",
    "#aAAAc#jjGGGjjjjjjjjxxxx",
    "#aEEec#jjGGjjjjjjjjjjjjx",
    ".##cc#jjjjjjjjjjjjjjjjjx",
    "..###jjjjjjjjjjxxjjjjjjx",
    ".....#jjxxxxxxxxjjjjjj#.",
    "....#jjxxxxxxxxxxjjjjj#.",
    ".....#jjjjjjjjjjjjjjj#..",
    ".....##OOOOOOOOOO##.....",
    ".....#pppppppppp#.......",
    "....#pPppppppppP#.......",
    "....#pPppppppppP#.......",
    "....#pPpp#..ppP#........",  # legs splayed
    "....#pPp#..pppP#........",
    "....#pPp#..pPppP#.......",
    "....#pPp#..pPppP#.......",
    "...#pPp#...pPppP#.......",
    "...#pPp#...pPppP#.......",
    "..#pPp#....pPppP#.......",
    "..#pp#.....pPppP#.......",
    ".#pp#......pPppP#.......",
    "#Bb#......#BbbbB#.......",
    "#Bb#......#BbbbB#.......",
    "#DDD#.....#BDDbB#.......",
    ".###......#DDDDD#.......",
    "...........######.......",
    "........................",
    "........................",
]


# PUNCH frame 0 — wind-up, body twisted, arm pulled back
GIG_PUNCH_WINDUP = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjj#..",
    "....#aAAAc#jjGGjjjjjj#..",
    "....#aEEec#jjjjjjjjjj#..",  # right arm NOT drawn (pulled back)
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjjjjjxxjj#..",
    "....#aAAAc#jjxxxxxxjj#..",
    "....#aEEec#jxxxxxxxjj#..",
    ".....#aac##jjjjjjjjj#...",
    "......##g#jjjjjjjjjj#...",
    "........##OOOOOOOOO#....",
    "........#pppppppp#......",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPpp#.#pP#.....",
    "........#pPp##.#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pqp#..#qp#.....",
    "........#ppp#..#pp#.....",
    ".......#BbbbB##BbbbB#...",
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",
    ".......#DDDDD##DDDDD#...",
    "........######..######..",
]


# PUNCH frame 1 — STRIKE, right arm fully extended forward
GIG_PUNCH_STRIKE = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjjjjjjjjjjjxxx#YO",  # right arm extended with FIST + impact
    "....#aAAAc#jjGGjjjjjjjjjjjjjjjxssssYO",
    "....#aEEec#jjjjjjjjjjjjjjjjjjjxkkSYO.",
    "....#aAAAc#jjjjjjjjjj#jjjjjjjjxxxx#..",
    "....#aEEec#jjjjjjxxjj#..............",
    "....#aAAAc#jjxxxxxxjj#..............",
    "....#aEEec#jxxxxxxxjj#..............",
    ".....#aac##jjjjjjjjj#...............",
    "......##g#jjjjjjjjjj#...............",
    "........##OOOOOOOOO#................",
    "........#pppppppp#..................",
    "........#pPppppppP#.................",
    "........#pPppppppP#.................",
    "........#pPpp#.#pP#.................",
    "........#pPp##.#Pp#.................",
    "........#pPp#..#Pp#.................",
    "........#pPp#..#Pp#.................",
    "........#pPp#..#Pp#.................",
    "........#pPp#..#Pp#.................",
    "........#pPp#..#Pp#.................",
    "........#pqp#..#qp#.................",
    "........#ppp#..#pp#.................",
    ".......#BbbbB##BbbbB#...............",
    ".......#BbbbB##BbbbB#...............",
    ".......#BbDDB##BDDbB#...............",
    ".......#DDDDD##DDDDD#...............",
    "........######..######..............",
]


# PUNCH frame 2 — recovery (arm halfway back)
GIG_PUNCH_RECOVERY = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjjjjjjxxss#..",  # arm halfway
    "....#aAAAc#jjGGjjjjjjjjjxsssk#..",
    "....#aEEec#jjjjjjjjjjjjjxkkk#...",
    "....#aAAAc#jjjjjjjjjj##jxxxx#...",
    "....#aEEec#jjjjjjxxjj#..........",
    "....#aAAAc#jjxxxxxxjj#..........",
    "....#aEEec#jxxxxxxxjj#..........",
    ".....#aac##jjjjjjjjj#...........",
    "......##g#jjjjjjjjjj#...........",
    "........##OOOOOOOOO#............",
    "........#pppppppp#..............",
    "........#pPppppppP#.............",
    "........#pPppppppP#.............",
    "........#pPpp#.#pP#.............",
    "........#pPp##.#Pp#.............",
    "........#pPp#..#Pp#.............",
    "........#pPp#..#Pp#.............",
    "........#pPp#..#Pp#.............",
    "........#pPp#..#Pp#.............",
    "........#pPp#..#Pp#.............",
    "........#pqp#..#qp#.............",
    "........#ppp#..#pp#.............",
    ".......#BbbbB##BbbbB#...........",
    ".......#BbbbB##BbbbB#...........",
    ".......#BbDDB##BDDbB#...........",
    ".......#DDDDD##DDDDD#...........",
    "........######..######..........",
]


# KICK — high kick with leg extended
GIG_KICK = [
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#skssksssssSs#....",
    "......#sggghhhhhggs#....",
    "......#sghhhhhhhggs#....",
    "......#sgghhhhhgg#s#....",
    ".......#sghhhhhg#ss#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjjjjjjjjj#..",
    "....#aEEec#jjGGjjjjjj#..",
    "....#aAAAc#jjGGGjjjjj#..",
    "....#aEEec#jjGGGjjjjj#..",
    "....#aAAAc#jjGGjjjjjxx#.",
    "....#aEEec#jjjjjjjjjsss#",
    "....#aAAAc#jjjjjjjjjkkS#",
    "....#aEEec#jjjjjjxxjkss#",
    "....#aAAAc#jjxxxxxxjxxx#",
    "....#aEEec#jxxxxxxxjjjj#",
    ".....#aac##jjjjjjjjjjj#.",
    "......##g#jjjjjjjjjjj#..",
    "........##OOOOOOOOO##...",
    "........#pppppppp#.#....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPpppppppppppppppppppppppY",  # leg extended HIGH
    "........#pPppPPppppppppppppppppppppO",
    "........#pqpPPPpppppppppppppppBbbbbO",
    "........#pppPPPppppppppppppppBbbbbbY",  # boot at end
    "........#pPp#pppppppppppppppBDDbbbD#",
    "........#pPp##ppppppppppppppDDDDDDD#",
    "........#pPp#..........................",
    "........#pPp#..........................",
    "........#pqp#..........................",
    "........#ppp#..........................",
    ".......#BbbbB#.........................",
    ".......#BbbbB#.........................",
    ".......#BbDDB#.........................",
    ".......#DDDDD#.........................",
    "........######.........................",
]


# HURT — knocked back, arms up
GIG_HURT = [
    "........##########......",
    ".......#hhhhhgggg#......",
    "......#hhghhhhhhgg##....",
    "......#hhghhhhhhhg#g#...",
    "......#HkkkkkkkkkSg##...",
    "......#ksssssssssss#....",
    "......#kskRsssssssks#...",  # red flash on face (hit)
    "......#ksRRsssWWkks#....",
    "......#kskkkssWdkks#....",
    "......#kkkkkkkkkkks#....",
    "......#kgggggggggks#....",
    "......#kgggggggggks#....",
    "......#kgggggggg#s#.....",
    ".......#kggggggg#ss#....",
    "......#xxxxxxxxxxxx#....",
    ".....#xxxxxxxxxxxxxx#...",
    "....#aAAAc#xxGGxxxxxx#..",
    "....#aEEec#RxGGRxxxxx#..",  # red flash on torso
    "....#aAAAc#xxGGGxxxxx#..",
    "....#aEEec#xxGGGxxxxx#..",
    "....#aAAAc#xxGGxxxxxxx#.",
    "....#aEEec#xxxxxxxxxsss#",
    "....#aAAAc#xxxxxxxxxkkk#",
    "....#aEEec#xxxxxxxxxkks#",
    "....#aAAAc#xxXXXXXXxxxx#",
    "....#aEEec#xXXXXXXXxxxx#",
    ".....#aac##xxxxxxxxxxx#.",
    "......##g#xxxxxxxxxxx#..",
    "........##OOOOOOOOO##...",
    "........#pppppppp#.#....",
    "........#pPppppppP#.....",
    "........#pPppppppP#.....",
    "........#pPpp#.#pP#.....",
    "........#pPp##.#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pPp#..#Pp#.....",
    "........#pqp#..#qp#.....",
    "........#ppp#..#pp#.....",
    ".......#BbbbB##BbbbB#...",
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",
    ".......#DDDDD##DDDDD#...",
    "........######..######..",
]


# CROUCH — body compressed
GIG_CROUCH = [
    "........................",
    "........................",
    "........................",
    "........##########......",
    ".......#HHHHHhhgg#......",
    "......#HHhhhhhhhgg##....",
    "......#HHhhhhhhhhg#g#...",
    "......#HsssssssssSg##...",
    "......#sSSSSSSSSSSs#....",
    "......#sSEEsssssSSs#....",
    "......#sSEEsssWWSSs#....",
    "......#sSsksssWdSSs#....",
    "......#sggghhhhhggs#....",
    "......#sgghhhhhgghs#....",
    "......#JJJJJJJJJJJJ#....",
    ".....#JjjjjjjjjjjjjJ#...",
    "....#aAAAc#jjGGjjjjjj#..",
    "....#aEEec#jjGGGjjjjj#..",
    "....#aAAAc#jjGGjjjjjj#..",
    "....#aEEec#jxxxxxxxjj#..",
    "....#aAAAc#xxxxxxxxxx#..",
    ".....#aac#xxxxxxxxxxx#..",
    "........#xOOOOOOOOOOx#..",
    "........#pppppppppppp#..",
    "........#pPppppppPppP#..",
    "........#pPpp##Ppp#pP#..",
    "........#pPp#.#Pp#.pP#..",
    "........#pPp#.#Pp#.pP#..",
    "........#pqp#.#qp#.qp#..",
    "........#ppp#.#pp#.pp#..",
    ".......#BbbbB##BbbbB#...",
    ".......#BbbbB##BbbbB#...",
    ".......#BbDDB##BDDbB#...",
    ".......#DDDDD##DDDDD#...",
    "........######..######..",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]


def build_gig_sprites(canvas_w, canvas_h):
    """Build all GIG sprite frames as pygame Surfaces.
    The matrices are drawn facing RIGHT. The _right suffix sprites are those
    (facing right), and _left are mirrored.
    Note: entity.py uses _left when facing==1, so we label things consistent
    with the rest of the engine's convention.
    """
    frames = {}

    def make(matrix):
        return matrix_to_surface(matrix, GIG_COLORS, canvas_w, canvas_h)

    # Base sprites face RIGHT (cyber arm on left side of character = left side of sprite)
    # The engine convention is: _left suffix when facing right (swapped via entity.py)
    # So base matrices (facing right) go to _left key.
    base_idle = [make(GIG_IDLE_0), make(GIG_IDLE_1)]
    base_run = [make(GIG_RUN_0), make(GIG_RUN_1), make(GIG_RUN_2), make(GIG_RUN_3)]
    base_jump = [make(GIG_JUMP_0)]
    base_fall = [make(GIG_FALL_0)]
    base_hurt = [make(GIG_HURT)]
    base_crouch = [make(GIG_CROUCH)]

    # Punch combo — three frames each, but all combos use same animation
    base_punch = [make(GIG_PUNCH_WINDUP), make(GIG_PUNCH_STRIKE), make(GIG_PUNCH_RECOVERY)]
    base_kick = [make(GIG_PUNCH_WINDUP), make(GIG_KICK), make(GIG_PUNCH_RECOVERY)]

    # Assign: base = facing right, but engine convention uses _left for facing==1
    # So: base goes to _left, mirrored goes to _right
    frames["idle_left"] = base_idle
    frames["idle_right"] = [mirror_h(f) for f in base_idle]
    frames["run_left"] = base_run
    frames["run_right"] = [mirror_h(f) for f in base_run]
    frames["jump_left"] = base_jump
    frames["jump_right"] = [mirror_h(f) for f in base_jump]
    frames["fall_left"] = base_fall
    frames["fall_right"] = [mirror_h(f) for f in base_fall]
    frames["hurt_left"] = base_hurt
    frames["hurt_right"] = [mirror_h(f) for f in base_hurt]
    frames["crouch_left"] = base_crouch
    frames["crouch_right"] = [mirror_h(f) for f in base_crouch]
    frames["land_left"] = base_crouch[:]
    frames["land_right"] = [mirror_h(f) for f in base_crouch]
    frames["slide_left"] = base_crouch[:]
    frames["slide_right"] = [mirror_h(f) for f in base_crouch]
    frames["wall_slide_left"] = base_idle[:1]
    frames["wall_slide_right"] = [mirror_h(base_idle[0])]
    frames["parry_left"] = base_idle[:1]
    frames["parry_right"] = [mirror_h(base_idle[0])]
    frames["hack_left"] = base_idle[:1]
    frames["hack_right"] = [mirror_h(base_idle[0])]

    for i in range(3):
        frames[f"punch{i}_left"] = base_punch
        frames[f"punch{i}_right"] = [mirror_h(f) for f in base_punch]

    frames["kick_left"] = base_kick
    frames["kick_right"] = [mirror_h(f) for f in base_kick]

    return frames
