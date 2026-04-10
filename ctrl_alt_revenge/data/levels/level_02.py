# data/levels/level_02.py — "La Rete" (The Network)
# Underground server farm — vertical, platforming-heavy
# Visual: 1=ground, 2=wall, 3=platform, 4=gate, 5=cover, 6=boss_floor, 7=boss_wall
from ctrl_alt_revenge.settings import TILE_SIZE

MAP_WIDTH_TILES = 150
MAP_HEIGHT_TILES = 35


def generate_level_02():
    """Genera il livello 2: La Rete — server farm sotterranea."""

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

    def clear_rect(x1, x2, y1, y2):
        for x in range(x1, x2):
            for y in range(y1, y2):
                if 0 <= x < MAP_WIDTH_TILES and 0 <= y < MAP_HEIGHT_TILES:
                    collision[y][x] = 0
                    visual[y][x] = 0

    # === BASE: pavimento e soffitto ===
    solid_rect(0, MAP_WIDTH_TILES, 31, MAP_HEIGHT_TILES, 1)  # pavimento
    solid_rect(0, MAP_WIDTH_TILES, 0, 1, 2)  # soffitto

    # === SEZIONE 1: SERVER ROOM ENTRY (tile 0-30) ===
    # Muro sinistro
    for y in range(0, 31):
        solid(0, y, 2)

    # Corridoio basso con server rack ai lati (coperture)
    solid_rect(0, 30, 8, 10, 2)  # soffitto basso

    # Server rack come coperture
    for rx in [5, 10, 15, 20, 25]:
        for y in range(28, 31):
            solid(rx, y, 5)
            solid(rx + 1, y, 5)

    # Piattaforme superiori — passaggio alternativo in alto
    oneway_row(3, 8, 18)
    oneway_row(10, 16, 14)
    oneway_row(18, 24, 18)
    oneway_row(22, 28, 12)

    # === SEZIONE 2: VERTICAL SHAFT — WALL JUMP (tile 30-50) ===
    # Pareti verticali del shaft
    for y in range(1, 31):
        solid(30, y, 2)
    for y in range(1, 31):
        solid(45, y, 2)

    # Apertura in basso per entrare
    collision[29][30] = 0; visual[29][30] = 0
    collision[30][30] = 0; visual[30][30] = 0
    collision[28][30] = 0; visual[28][30] = 0

    # Piattaforme a zig-zag dentro lo shaft
    oneway_row(31, 36, 28)
    oneway_row(39, 44, 24)
    oneway_row(31, 36, 20)
    oneway_row(39, 44, 16)
    oneway_row(31, 36, 12)
    oneway_row(39, 44, 8)
    oneway_row(31, 36, 4)

    # Uscita in alto a destra
    collision[3][45] = 0; visual[3][45] = 0
    collision[4][45] = 0; visual[4][45] = 0
    collision[5][45] = 0; visual[5][45] = 0

    # Ponte in alto che va a destra
    solid_rect(45, 70, 3, 4, 2)

    # === SEZIONE 3: HORIZONTAL DATA TUNNEL (tile 45-80) ===
    # Tunnel stretto orizzontale (altezza ridotta)
    solid_rect(45, 80, 7, 9, 2)  # soffitto del tunnel

    # Pavimento tunnel — sopraelevato rispetto al fondo
    solid_rect(45, 80, 15, 17, 1)

    # Aperture nel pavimento del tunnel (trappole / scorciatoie)
    clear_rect(55, 58, 15, 17)
    clear_rect(68, 71, 15, 17)

    # Piattaforme sotto il tunnel per chi cade
    oneway_row(52, 60, 22)
    oneway_row(64, 72, 22)
    oneway_row(56, 62, 27)
    oneway_row(66, 74, 27)

    # Scale per risalire
    oneway_row(76, 80, 20)
    oneway_row(73, 77, 25)

    # Gate controllato dal primo terminale (scorciatoia)
    for y in range(4, 15):
        solid(60, y, 4)

    # === SEZIONE 4: HACKING CHAMBER (tile 80-100) ===
    # Stanza chiusa con 3 terminali
    solid_rect(80, 100, 3, 5, 2)  # soffitto camera
    solid_rect(80, 100, 15, 17, 1)  # pavimento camera

    # Muri della camera
    for y in range(4, 15):
        solid(80, y, 2)
    # Muro destro con apertura
    for y in range(4, 12):
        solid(99, y, 2)

    # Piattaforme interne
    oneway_row(84, 89, 11)
    oneway_row(92, 97, 8)

    # Scale per scendere al livello inferiore
    oneway_row(97, 101, 20)
    oneway_row(94, 98, 24)
    oneway_row(97, 101, 28)

    # === SEZIONE 5: DOUBLE DRONE CORRIDOR (tile 100-125) ===
    # Corridoio lungo con droni che pattugliano
    # Pavimento a due livelli
    solid_rect(100, 125, 28, 30, 1)

    # Coperture
    for cx in [103, 109, 115, 121]:
        for y in range(26, 28):
            solid(cx, y, 5)

    # Piattaforme alte per i droni
    oneway_row(102, 108, 20)
    oneway_row(110, 116, 17)
    oneway_row(118, 124, 20)

    # Soffitto basso corridoio
    solid_rect(100, 125, 12, 14, 2)

    # === SEZIONE 6: MINI-BOSS AREA (tile 125-150) ===
    # Pavimento boss
    solid_rect(125, 149, 28, MAP_HEIGHT_TILES, 6)

    # Muro sinistro boss
    for y in range(1, 25):
        solid(125, y, 7)
    # Muro destro boss
    for y in range(1, 31):
        solid(149, y, 7)

    # Soffitto boss
    solid_rect(125, 150, 0, 2, 7)

    # Piattaforme boss arena
    oneway_row(130, 136, 24)
    oneway_row(138, 144, 20)
    oneway_row(130, 136, 16)

    # === ENTITA' ===
    entities = {
        "player_spawn": (3 * TILE_SIZE, 28 * TILE_SIZE),

        "terminals": [
            # Terminale 1: apre la scorciatoia (gate a tile 60)
            {"x": 50 * TILE_SIZE, "y": 14 * TILE_SIZE, "type": "door",
             "gate_tiles": [(60, y) for y in range(4, 15)]},
            # Terminale 2: disabilita droni (nel corridoio droni)
            {"x": 100 * TILE_SIZE, "y": 27 * TILE_SIZE, "type": "disable_drones",
             "gate_tiles": []},
        ],

        "cameras": [
            {"x": 8 * TILE_SIZE, "y": 8 * TILE_SIZE, "facing": 1},
            {"x": 20 * TILE_SIZE, "y": 8 * TILE_SIZE, "facing": -1},
            {"x": 110 * TILE_SIZE, "y": 12 * TILE_SIZE, "facing": 1},
        ],

        "thugs": [
            {"x": 12 * TILE_SIZE, "y": 29 * TILE_SIZE, "patrol": 40},
            {"x": 22 * TILE_SIZE, "y": 29 * TILE_SIZE, "patrol": 50},
            {"x": 85 * TILE_SIZE, "y": 14 * TILE_SIZE, "patrol": 30},
            {"x": 95 * TILE_SIZE, "y": 14 * TILE_SIZE, "patrol": 40},
        ],

        "drones": [
            {"x": 55 * TILE_SIZE, "y": 10 * TILE_SIZE, "patrol": 80},
            {"x": 70 * TILE_SIZE, "y": 10 * TILE_SIZE, "patrol": 60},
            {"x": 105 * TILE_SIZE, "y": 16 * TILE_SIZE, "patrol": 70},
            {"x": 120 * TILE_SIZE, "y": 16 * TILE_SIZE, "patrol": 60},
        ],

        "boss_spawn": (137 * TILE_SIZE, 25 * TILE_SIZE),

        "dialogs": [
            {"x": 5 * TILE_SIZE, "y": 28 * TILE_SIZE, "dialog_id": "intro",
             "trigger_once": True},
            {"x": 127 * TILE_SIZE, "y": 27 * TILE_SIZE, "dialog_id": "boss_intro",
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
