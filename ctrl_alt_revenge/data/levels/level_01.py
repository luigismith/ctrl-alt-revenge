# data/levels/level_01.py — "Sotto la Linea"
# Mappa come array Python: 0=vuoto, 1=solido, 2=one-way platform
# Visual: 1=ground, 2=wall, 3=platform, 4=gate, 5=cover, 6=boss_floor, 7=boss_wall
# Sezioni: tutorial (0-25) -> stealth (25-50) -> combat arena (50-75) -> vertical (75-100) -> boss (100-130)
from ctrl_alt_revenge.settings import TILE_SIZE

MAP_WIDTH_TILES = 130
MAP_HEIGHT_TILES = 30


def generate_level_01():
    """Genera il livello 1 completo — versione compatta con migliore pacing."""

    collision = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]
    visual = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]

    # Helper per piazzare blocchi
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

    # === PAVIMENTO BASE (riga 26-29) ===
    solid_rect(0, MAP_WIDTH_TILES, 26, MAP_HEIGHT_TILES, 1)

    # === SOFFITTO GENERALE (riga 0) ===
    solid_rect(0, MAP_WIDTH_TILES, 0, 1, 2)

    # === SEZIONE 1: TUTORIAL (tile 0-25) ===
    # Muro sinistro
    for y in range(0, 26):
        solid(0, y, 2)

    # Piattaforma bassa per imparare il salto
    oneway_row(8, 12, 23)
    # Piattaforma media per doppio salto
    oneway_row(14, 18, 20)
    # Walkway sopraelevata — crea un secondo livello
    solid_rect(6, 22, 16, 17, 2)
    # Scale a sinistra per salire sulla walkway
    oneway_row(4, 7, 19)
    oneway_row(3, 6, 22)

    # === GATE + TERMINALE (tile 22-27) ===
    # Cancello verticale
    for y in range(8, 26):
        solid(25, y, 4)
        solid(26, y, 4)
    # Terminale platform
    oneway_row(20, 24, 23)

    # === SEZIONE 2: STEALTH (tile 27-50) ===
    # Soffitto basso per atmosfera opprimente
    solid_rect(27, 50, 6, 8, 2)

    # Passaggio sotterraneo (scavato nel pavimento) — alternativa stealth
    solid_rect(30, 48, 24, 25, 1)  # ripristina pavimento sopra il tunnel
    for x in range(32, 46):
        collision[24][x] = 0  # scava tunnel
        visual[24][x] = 0
    # Entrata tunnel a sinistra
    collision[25][31] = 0
    visual[25][31] = 0
    collision[24][31] = 0
    visual[24][31] = 0
    # Uscita tunnel a destra
    collision[25][46] = 0
    visual[25][46] = 0
    collision[24][46] = 0
    visual[24][46] = 0

    # Coperture in superficie
    for cx in [30, 36, 42]:
        for y in range(24, 26):
            solid(cx, y, 5)
            solid(cx + 1, y, 5)

    # Piattaforme elevate per drone patrol
    oneway_row(33, 37, 14)
    oneway_row(40, 44, 11)

    # === SEZIONE 3: COMBAT ARENA (tile 50-75) ===
    # Muri parziali dell'arena
    for y in range(8, 22):
        solid(50, y, 2)
    for y in range(8, 22):
        solid(75, y, 2)

    # Multi-livello nell'arena
    # Piano inferiore — pavimento standard a y=25
    # Piano medio — walkway
    oneway_row(54, 60, 21)
    oneway_row(65, 72, 21)
    # Piano alto — piattaforme per vantaggio tattico
    oneway_row(57, 62, 17)
    oneway_row(67, 71, 14)
    # Pilastro centrale spezzato (one-way platform at top, passable at ground)
    oneway(62, 20, 3)
    oneway(63, 20, 3)
    oneway_row(61, 65, 18)

    # === SEZIONE 4: VERTICAL PLATFORMING (tile 75-100) ===
    # Shaft verticale stretto con wall-jump (opening at bottom for ground passage)
    for y in range(1, 22):
        solid(78, y, 2)
    for y in range(1, 22):
        solid(88, y, 2)

    # Piattaforme alternate dentro lo shaft
    oneway_row(79, 83, 23)
    oneway_row(84, 88, 19)
    oneway_row(79, 83, 15)
    oneway_row(84, 88, 11)
    oneway_row(79, 83, 7)

    # Uscita in alto — ponte verso boss
    solid_rect(83, 100, 5, 6, 2)

    # Scale/piattaforme discendenti dal ponte
    oneway_row(93, 97, 9)
    oneway_row(90, 94, 14)
    oneway_row(95, 99, 19)
    oneway_row(92, 96, 23)

    # === SEZIONE 5: BOSS ARENA (tile 100-130) ===
    # Pavimento boss
    solid_rect(100, 129, 26, MAP_HEIGHT_TILES, 6)

    # Muro sinistro boss (con apertura in basso per entrare)
    for y in range(1, 22):
        solid(100, y, 7)
    # Muro destro boss (chiuso)
    for y in range(1, 26):
        solid(129, y, 7)

    # Soffitto arena boss
    solid_rect(100, 130, 0, 1, 7)

    # Piattaforme nell'arena boss
    oneway_row(106, 111, 21)
    oneway_row(114, 120, 17)
    oneway_row(122, 127, 21)

    # === ENTITA' ===
    entities = {
        "player_spawn": (3 * TILE_SIZE, 24 * TILE_SIZE),

        "terminals": [
            {"x": 22 * TILE_SIZE, "y": 22 * TILE_SIZE, "type": "door",
             "gate_tiles": [(25, y) for y in range(8, 26)] + [(26, y) for y in range(8, 26)]},
        ],

        "cameras": [
            {"x": 32 * TILE_SIZE, "y": 6 * TILE_SIZE, "facing": 1},
            {"x": 40 * TILE_SIZE, "y": 6 * TILE_SIZE, "facing": -1},
            {"x": 46 * TILE_SIZE, "y": 6 * TILE_SIZE, "facing": 1},
        ],

        "thugs": [
            # 2 guardie al cancello
            {"x": 28 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 30},
            {"x": 24 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 20},
            # 3 nell'arena combat
            {"x": 55 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 50},
            {"x": 63 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 40},
            {"x": 70 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 60},
        ],

        "drones": [
            # 1 nella sezione stealth
            {"x": 38 * TILE_SIZE, "y": 10 * TILE_SIZE, "patrol": 100},
            # 2 nella sezione verticale
            {"x": 83 * TILE_SIZE, "y": 12 * TILE_SIZE, "patrol": 60},
            {"x": 83 * TILE_SIZE, "y": 20 * TILE_SIZE, "patrol": 40},
        ],

        "boss_spawn": (115 * TILE_SIZE, 22 * TILE_SIZE),

        "dialogs": [
            {"x": 5 * TILE_SIZE, "y": 24 * TILE_SIZE, "dialog_id": "intro",
             "trigger_once": True},
            {"x": 102 * TILE_SIZE, "y": 24 * TILE_SIZE, "dialog_id": "boss_intro",
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
