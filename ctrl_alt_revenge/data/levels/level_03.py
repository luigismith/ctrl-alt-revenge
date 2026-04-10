# data/levels/level_03.py — "Il Tetto del Mondo" (Rooftop)
# Skyscraper rooftops at night — gap jumping, narrow walkways, drone-heavy
# Visual: 1=ground, 2=wall, 3=platform, 4=gate, 5=cover, 6=boss_floor, 7=boss_wall
from ctrl_alt_revenge.settings import TILE_SIZE

MAP_WIDTH_TILES = 180
MAP_HEIGHT_TILES = 40


def generate_level_03():
    """Genera il livello 3: Il Tetto del Mondo — tetti dei grattacieli di notte."""

    collision = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]
    visual = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]

    def solid(x, y, vis=1):
        if 0 <= x < MAP_WIDTH_TILES and 0 <= y < MAP_HEIGHT_TILES:
            collision[y][x] = 1
            visual[y][x] = vis

    def oneway(x, y, vis=3):
        if 0 <= x < MAP_WIDTH_TILES and 0 <= y < MAP_HEIGHT_TILES:
            collision[y][x] = 2
            visual[y][x] = vis

    def solid_rect(x1, x2, y1, y2, vis=1):
        for x in range(x1, x2):
            for y in range(y1, y2):
                solid(x, y, vis)

    def oneway_row(x1, x2, y, vis=3):
        for x in range(x1, x2):
            oneway(x, y, vis)

    # NO global floor — rooftops are isolated buildings over the void
    # Falling off = death (void below y=38)

    # Death floor at the very bottom (solid so player dies on contact)
    solid_rect(0, MAP_WIDTH_TILES, 38, MAP_HEIGHT_TILES, 1)

    # === BUILDING 1: START (tile 0-25) ===
    # Rooftop surface
    solid_rect(0, 25, 30, 34, 1)
    # Left wall
    for y in range(10, 34):
        solid(0, y, 2)
    # Right edge wall (low parapet)
    for y in range(28, 30):
        solid(24, y, 2)

    # Stairwell structure on roof
    solid_rect(2, 8, 24, 26, 2)
    oneway_row(2, 8, 22)

    # Antenna mast
    solid(12, 26, 2)
    solid(12, 27, 2)
    solid(12, 28, 2)
    solid(12, 29, 2)

    # === GAP 1 (tile 25-30) — 5 tile gap, easy jump ===
    # Small floating platform in the gap
    oneway_row(27, 29, 30)

    # === BUILDING 2 (tile 30-55) ===
    solid_rect(30, 55, 32, 36, 1)
    # Lower rooftop — this building is slightly lower

    # Air conditioning units as cover
    for cx in [33, 40, 47]:
        solid(cx, 30, 5)
        solid(cx, 31, 5)
        solid(cx + 1, 30, 5)
        solid(cx + 1, 31, 5)

    # Elevated walkway across the roof
    oneway_row(35, 45, 26)

    # Water tower structure
    solid_rect(50, 54, 26, 28, 2)
    solid_rect(49, 55, 28, 30, 2)

    # === GAP 2 (tile 55-62) — 7 tile gap, needs double jump ===
    # Two tiny stepping platforms
    oneway_row(57, 59, 31)
    oneway_row(60, 62, 29)

    # === BUILDING 3 (tile 62-90) — tallest building, multi-level ===
    solid_rect(62, 90, 28, 32, 1)

    # Lower level (inside building — accessed through holes)
    solid_rect(62, 90, 34, 36, 1)

    # Access holes between levels
    # (clear parts of the y=28-32 floor)
    for x in range(70, 73):
        for y in range(28, 32):
            collision[y][x] = 0
            visual[y][x] = 0
    for x in range(82, 85):
        for y in range(28, 32):
            collision[y][x] = 0
            visual[y][x] = 0

    # Walls on this building
    for y in range(20, 36):
        solid(62, y, 2)
    for y in range(20, 36):
        solid(89, y, 2)

    # Roof structures — multi-height platforms
    oneway_row(65, 70, 24)
    oneway_row(74, 80, 20)
    oneway_row(83, 88, 24)

    # Scaffold on the outside (left)
    oneway_row(58, 62, 24)

    # Terminal here — disables searchlights
    # Gate blocking a shortcut
    for y in range(28, 34):
        solid(76, y, 4)

    # === GAP 3 (tile 90-96) — 6 tile gap with wind platforms ===
    # One-way platforms simulating wind gusts at angles
    oneway_row(91, 93, 27)
    oneway_row(93, 95, 25)
    oneway_row(94, 96, 28)

    # === BUILDING 4: CRANE/SCAFFOLD (tile 96-130) ===
    # Narrow building base
    solid_rect(96, 130, 32, 36, 1)

    # Crane arm extending upward and to the right
    # Vertical crane mast
    for y in range(8, 32):
        solid(100, y, 2)
        solid(101, y, 2)

    # Crane arm (horizontal beam at top)
    solid_rect(100, 120, 8, 10, 2)

    # Scaffold platforms at various heights
    oneway_row(103, 108, 28)
    oneway_row(110, 116, 24)
    oneway_row(103, 108, 20)
    oneway_row(112, 118, 16)
    oneway_row(103, 108, 12)

    # Hanging platform from crane
    oneway_row(114, 120, 12)

    # Right side — platforms going down to next building
    oneway_row(122, 128, 16)
    oneway_row(125, 130, 22)
    oneway_row(122, 128, 28)

    # === GAP 4 (tile 130-136) — 6 tile gap ===
    oneway_row(132, 134, 30)

    # === BUILDING 5: HELIPAD (tile 136-160) ===
    # Helipad arena — wider, flat
    solid_rect(136, 160, 30, 34, 1)

    # Helipad markings (cover tiles for visual flavor)
    for y in range(28, 30):
        solid(145, y, 5)
        solid(146, y, 5)
        solid(153, y, 5)
        solid(154, y, 5)

    # Low walls on edges
    for y in range(28, 30):
        solid(136, y, 2)
        solid(159, y, 2)

    # Elevated observation platform
    oneway_row(140, 148, 24)
    oneway_row(152, 158, 24)

    # === GAP 5 (tile 160-165) — 5 tile gap to boss ===
    oneway_row(162, 164, 29)

    # === BUILDING 6: BOSS ARENA (tile 165-180) — narrow platform ===
    # Narrow boss platform — 15 tiles wide, falling off = death
    solid_rect(165, 179, 30, 34, 6)

    # Walls on both sides (boss containment)
    for y in range(10, 34):
        solid(165, y, 7)
    for y in range(10, 34):
        solid(179, y, 7)

    # Ceiling
    solid_rect(165, 180, 10, 11, 7)

    # Single platform inside boss arena
    oneway_row(169, 175, 24)

    # === ENTITA' ===
    entities = {
        "player_spawn": (4 * TILE_SIZE, 28 * TILE_SIZE),

        "terminals": [
            # Disabilita i riflettori / apre gate scorciatoia
            {"x": 66 * TILE_SIZE, "y": 27 * TILE_SIZE, "type": "door",
             "gate_tiles": [(76, y) for y in range(28, 34)]},
        ],

        "cameras": [
            {"x": 35 * TILE_SIZE, "y": 26 * TILE_SIZE, "facing": 1},
            {"x": 48 * TILE_SIZE, "y": 26 * TILE_SIZE, "facing": -1},
            {"x": 140 * TILE_SIZE, "y": 24 * TILE_SIZE, "facing": 1},
        ],

        "thugs": [
            {"x": 38 * TILE_SIZE, "y": 30 * TILE_SIZE, "patrol": 50},
            {"x": 145 * TILE_SIZE, "y": 28 * TILE_SIZE, "patrol": 60},
        ],

        "drones": [
            # Drone-heavy level — 6 droni
            {"x": 42 * TILE_SIZE, "y": 26 * TILE_SIZE, "patrol": 80},
            {"x": 75 * TILE_SIZE, "y": 18 * TILE_SIZE, "patrol": 70},
            {"x": 93 * TILE_SIZE, "y": 22 * TILE_SIZE, "patrol": 50},
            {"x": 112 * TILE_SIZE, "y": 14 * TILE_SIZE, "patrol": 60},
            {"x": 142 * TILE_SIZE, "y": 20 * TILE_SIZE, "patrol": 80},
            {"x": 155 * TILE_SIZE, "y": 20 * TILE_SIZE, "patrol": 60},
        ],

        "boss_spawn": (172 * TILE_SIZE, 26 * TILE_SIZE),

        "dialogs": [
            {"x": 6 * TILE_SIZE, "y": 28 * TILE_SIZE, "dialog_id": "intro",
             "trigger_once": True},
            {"x": 167 * TILE_SIZE, "y": 28 * TILE_SIZE, "dialog_id": "boss_intro",
             "trigger_once": True},
        ],
    }

    return {
        "collision": collision,
        "visual": visual,
        "width": MAP_WIDTH_TILES,
        "height": MAP_HEIGHT_TILES,
        "width_px": MAP_WIDTH_TILES * TILE_SIZE,
        "height_px": MAP_HEIGHT_TILES * TILE_SIZE,
        "entities": entities,
    }
