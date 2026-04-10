# data/levels/level_01.py — "Sotto la Linea"
# Mappa come array Python: 0=vuoto, 1=solido, 2=one-way platform
# Sezioni: tutorial -> terminale -> stealth -> arena thug -> platform verticale -> boss
from ctrl_alt_revenge.settings import TILE_SIZE

# Mappa larga ~200 tile (3200px), alta 30 tile (480px)
MAP_WIDTH_TILES = 200
MAP_HEIGHT_TILES = 30

def generate_level_01():
    """Genera il livello 1 completo. Restituisce un dizionario con tutti i dati."""

    # Inizializza mappa vuota
    collision = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]
    visual = [[0] * MAP_WIDTH_TILES for _ in range(MAP_HEIGHT_TILES)]

    # --- PAVIMENTO BASE (riga 26-29 = solido) ---
    for x in range(MAP_WIDTH_TILES):
        for y in range(26, MAP_HEIGHT_TILES):
            collision[y][x] = 1
            visual[y][x] = 1

    # --- SEZIONE 1: TUTORIAL MOVIMENTO (tile 0-30) ---
    # Muro iniziale a sinistra
    for y in range(0, 26):
        collision[y][0] = 1
        visual[y][0] = 1

    # Piccole piattaforme per tutorial salto
    for x in range(12, 16):
        collision[22][x] = 2  # one-way
        visual[22][x] = 3
    for x in range(18, 22):
        collision[19][x] = 2
        visual[19][x] = 3
    for x in range(24, 28):
        collision[22][x] = 2
        visual[22][x] = 3

    # --- SEZIONE 2: PRIMO TERMINALE + CANCELLO (tile 30-45) ---
    # Cancello (muro verticale con buco in alto)
    for y in range(10, 26):
        collision[y][42] = 1
        visual[y][42] = 4  # porta/cancello
        collision[y][43] = 1
        visual[y][43] = 4

    # Piattaforma vicino al terminale
    for x in range(33, 38):
        collision[20][x] = 2
        visual[20][x] = 3

    # --- SEZIONE 3: STEALTH CON TELECAMERE (tile 45-75) ---
    # Soffitto basso per sezione stealth
    for x in range(48, 72):
        collision[10][x] = 1
        visual[10][x] = 2

    # Coperture per nascondersi (2 tile alte, saltabili)
    for x in range(52, 54):
        for y in range(24, 26):
            collision[y][x] = 1
            visual[y][x] = 5  # copertura

    for x in range(60, 62):
        for y in range(24, 26):
            collision[y][x] = 1
            visual[y][x] = 5

    for x in range(68, 70):
        for y in range(24, 26):
            collision[y][x] = 1
            visual[y][x] = 5

    # --- SEZIONE 4: ARENA THUG (tile 75-100) ---
    # Muri parziali dell'arena (con apertura in basso per passare)
    for y in range(10, 22):
        collision[y][75] = 1
        visual[y][75] = 2
    for y in range(10, 22):
        collision[y][100] = 1
        visual[y][100] = 2

    # Piattaforme nell'arena
    for x in range(80, 84):
        collision[21][x] = 2
        visual[21][x] = 3
    for x in range(88, 92):
        collision[18][x] = 2
        visual[18][x] = 3
    for x in range(95, 99):
        collision[21][x] = 2
        visual[21][x] = 3

    # --- SEZIONE 5: PLATFORM VERTICALE CON WALL-JUMP (tile 100-130) ---
    # Corridoio verticale stretto (apertura in basso per entrare)
    for y in range(0, 23):
        collision[y][105] = 1
        visual[y][105] = 2
    for y in range(0, 23):
        collision[y][115] = 1
        visual[y][115] = 2

    # Piattaforme alternate per wall-jump
    for x in range(106, 110):
        collision[22][x] = 2
        visual[22][x] = 3
    for x in range(111, 115):
        collision[18][x] = 2
        visual[18][x] = 3
    for x in range(106, 110):
        collision[14][x] = 2
        visual[14][x] = 3
    for x in range(111, 115):
        collision[10][x] = 2
        visual[10][x] = 3
    for x in range(106, 110):
        collision[6][x] = 2
        visual[6][x] = 3

    # Uscita in alto
    for x in range(106, 115):
        collision[4][x] = 0
    # Ponte in alto che porta alla sezione boss
    for x in range(115, 140):
        collision[6][x] = 1
        visual[6][x] = 2
    # Scale per tornare giù
    for x in range(135, 140):
        for y in range(6, 26):
            if y % 4 == 0:
                collision[y][x] = 2
                visual[y][x] = 3

    # --- SEZIONE 6: ARENA BOSS (tile 140-180) ---
    # Pavimento boss arena
    for x in range(140, 180):
        for y in range(26, MAP_HEIGHT_TILES):
            collision[y][x] = 1
            visual[y][x] = 6  # pavimento boss

    # Muri arena boss (apertura a sinistra per entrare)
    for y in range(0, 22):
        collision[y][140] = 1
        visual[y][140] = 7  # muro boss
    for y in range(0, 26):
        collision[y][179] = 1
        visual[y][179] = 7

    # Soffitto arena boss
    for x in range(140, 180):
        collision[0][x] = 1
        visual[0][x] = 7

    # Piattaforme nell'arena boss
    for x in range(148, 153):
        collision[20][x] = 2
        visual[20][x] = 3
    for x in range(158, 163):
        collision[17][x] = 2
        visual[17][x] = 3
    for x in range(168, 173):
        collision[20][x] = 2
        visual[20][x] = 3

    # Soffitto generale (tile 0-140)
    for x in range(0, 140):
        collision[0][x] = 1

    # --- ENTITA' ---
    entities = {
        "player_spawn": (3 * TILE_SIZE, 24 * TILE_SIZE),

        "terminals": [
            {"x": 39 * TILE_SIZE, "y": 24 * TILE_SIZE, "type": "door",
             "gate_tiles": [(42, y) for y in range(10, 26)] + [(43, y) for y in range(10, 26)]},
        ],

        "cameras": [
            {"x": 50 * TILE_SIZE, "y": 10 * TILE_SIZE, "facing": 1},
            {"x": 58 * TILE_SIZE, "y": 10 * TILE_SIZE, "facing": -1},
            {"x": 66 * TILE_SIZE, "y": 10 * TILE_SIZE, "facing": 1},
        ],

        "thugs": [
            {"x": 80 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 60},
            {"x": 88 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 40},
            {"x": 95 * TILE_SIZE, "y": 24 * TILE_SIZE, "patrol": 50},
        ],

        "drones": [
            {"x": 55 * TILE_SIZE, "y": 14 * TILE_SIZE, "patrol": 80},
            {"x": 65 * TILE_SIZE, "y": 14 * TILE_SIZE, "patrol": 60},
        ],

        "boss_spawn": (160 * TILE_SIZE, 22 * TILE_SIZE),

        "dialogs": [
            {"x": 5 * TILE_SIZE, "y": 24 * TILE_SIZE, "dialog_id": "intro",
             "trigger_once": True},
            {"x": 142 * TILE_SIZE, "y": 24 * TILE_SIZE, "dialog_id": "boss_intro",
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
