# settings.py — Costanti, palette, input map
# CTRL+ALT REVENGE! — Picchia Duro a Scorrimento

TITLE = "CTRL+ALT REVENGE!"
VERSION = "0.1.0"

# Risoluzione interna pixel-perfect
INTERNAL_WIDTH = 320
INTERNAL_HEIGHT = 240
SCALE = 3
SCREEN_WIDTH = INTERNAL_WIDTH * SCALE   # 960
SCREEN_HEIGHT = INTERNAL_HEIGHT * SCALE  # 720

FPS = 60
GRAVITY = 0.5
MAX_FALL_SPEED = 10.0

# Tile
TILE_SIZE = 16

# Palette cyberpunk (esattamente come da spec)
COLOR_BG_NIGHT     = (13, 11, 43)      # #0d0b2b
COLOR_NEON_BLUE    = (0, 229, 255)      # #00e5ff
COLOR_NEON_PURPLE  = (160, 32, 240)     # #a020f0
COLOR_NEON_ORANGE  = (255, 122, 26)     # #ff7a1a
COLOR_RED_ALARM    = (255, 46, 77)      # #ff2e4d
COLOR_WHITE_UI     = (245, 241, 216)    # #f5f1d8
COLOR_DARK_GRAY    = (30, 28, 50)
COLOR_MID_GRAY     = (60, 55, 90)
COLOR_SKIN         = (210, 170, 130)
COLOR_SKIN_SHADOW  = (180, 140, 100)
COLOR_HAIR_GRAY    = (160, 155, 150)
COLOR_JACKET_BROWN = (180, 120, 50)
COLOR_JACKET_SHADOW = (140, 90, 35)
COLOR_PANTS_DARK   = (50, 55, 60)
COLOR_BOOTS_BROWN  = (120, 80, 40)
COLOR_BLACK        = (0, 0, 0)
COLOR_GREEN_HACK   = (0, 255, 100)
COLOR_YELLOW       = (255, 220, 50)

# Player
PLAYER_SPEED = 3.0
PLAYER_JUMP_FORCE = -8.0
PLAYER_JUMP_CUT = -2.0     # velocità minima se rilasci il tasto
PLAYER_WALL_SLIDE_SPEED = 1.2
PLAYER_WALL_JUMP_FORCE_X = 4.0
PLAYER_WALL_JUMP_FORCE_Y = -7.0
COYOTE_TIME = 6           # frame
JUMP_BUFFER = 6            # frame
PLAYER_HP = 4
PLAYER_IFRAMES = 30        # frame di invincibilità dopo danno
KNOCKBACK_FORCE_X = 3.0
KNOCKBACK_FORCE_Y = -3.0

# Combat
PUNCH_DAMAGE = 1
KICK_DAMAGE = 2
COMBO_WINDOW = 25          # frame per continuare la combo
PARRY_WINDOW = 10          # frame di finestra parry

# Gun
GUN_DAMAGE = 2
GUN_COOLDOWN = 20  # frames between shots
GUN_AMMO_MAX = 12
BULLET_SPEED = 6.0
MEDIKIT_HEAL = 2

# Perks / Upgrades
PERK_DROP_THUG = 5      # CHIP guadagnati uccidendo un thug
PERK_DROP_DRONE = 8     # CHIP da drone
PERK_DROP_BOSS = 50     # CHIP da boss
PERK_PICKUP_VALUE = 10  # CHIP da pickup specifici

# Hacking
HACK_SLOWMO_FACTOR = 0.25
HACK_TIME_LIMIT = 5.0      # secondi
HACK_GRID_SIZE = 4

# Implants
EMP_COOLDOWN = 360         # frame (6 secondi)
BULLET_TIME_DURATION = 180 # frame (3 secondi)

# Nemici
THUG_HP = 3
THUG_SPEED = 1.2
THUG_SIGHT_RANGE = 120
THUG_SIGHT_CONE = 60       # gradi metà-cono

DRONE_HP = 2
DRONE_SPEED = 1.8
DRONE_SIGHT_RANGE = 150
DRONE_SHOOT_COOLDOWN = 90  # frame

WARDEN_HP = 20
WARDEN_PHASE_THRESHOLDS = [14, 7]  # HP per passaggio fase

# Heat system
HEAT_DECAY_RATE = 0.002    # per frame
HEAT_ALARM_THRESHOLD = 0.5
HEAT_MAX = 1.0

# Input map (rebindable)
import pygame
INPUT_MAP = {
    "left":    [pygame.K_LEFT, pygame.K_a],
    "right":   [pygame.K_RIGHT, pygame.K_d],
    "up":      [pygame.K_UP, pygame.K_w],
    "down":    [pygame.K_DOWN, pygame.K_s],
    "jump":    [pygame.K_SPACE, pygame.K_z],
    "punch":   [pygame.K_j, pygame.K_x],
    "kick":    [pygame.K_k, pygame.K_c],
    "hack":    [pygame.K_e, pygame.K_y],
    "parry":   [pygame.K_l, pygame.K_v],
    "implant1": [pygame.K_1],
    "implant2": [pygame.K_2],
    "implant3": [pygame.K_3],
    "implant4": [pygame.K_4],
    "pause":   [pygame.K_ESCAPE, pygame.K_p],
    "confirm": [pygame.K_RETURN, pygame.K_SPACE],
    "crouch":  [pygame.K_DOWN, pygame.K_s],
    "slide":   [pygame.K_DOWN, pygame.K_s],  # giù + salto = slide
}

# Gamepad mapping (Xbox layout)
GAMEPAD_MAP = {
    "jump": 0,      # A
    "punch": 2,     # X
    "kick": 3,      # Y
    "hack": 1,      # B
    "parry": 4,     # LB
    "pause": 7,     # Start
    "confirm": 0,   # A
}

# Stringhe di gioco (tono cupo/ironico)
STRINGS = {
    "title": "CTRL+ALT REVENGE!",
    "subtitle": "Picchia Duro a Scorrimento",
    "start": "PREMI START — o qualsiasi tasto, tanto che importa",
    "game_over": "Game Over — Reboot in corso...",
    "hack_success": "Sistema bucato in 0.3 secondi. Patetico.",
    "hack_fail": "Hack fallito. Sei diventato rumoroso.",
    "heat_low": "Heat: BASSA — per ora nessuno ti cerca davvero.",
    "heat_mid": "Heat: MEDIA — qualcuno ha notato qualcosa.",
    "heat_high": "Heat: ALTA — stanno arrivando tutti.",
    "pause_text": "PAUSA — Il mondo aspetta... forse.",
    "boss_intro": "WARDEN v2.0 — Protocollo di contenimento attivato.",
    "level_complete": "Livello completato. Non festeggiare, è solo l'inizio.",
}

# Direzioni
DIR_LEFT = -1
DIR_RIGHT = 1

# Layer del livello
LAYER_BG = 0
LAYER_TILES = 1
LAYER_ENTITIES = 2
LAYER_FG = 3
LAYER_UI = 4

# Dimensioni sprite (Golden Axe / Cadillacs & Dinosaurs scale)
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 48
THUG_WIDTH = 30
THUG_HEIGHT = 48
DRONE_WIDTH = 32
DRONE_HEIGHT = 20
WARDEN_WIDTH = 48
WARDEN_HEIGHT = 64

# Difficulty presets
DIFFICULTIES = {
    "FACILE": {
        "player_hp": 6,
        "enemy_damage_mult": 0.5,
        "enemy_speed_mult": 0.8,
        "hack_time_limit": 8.0,
        "parry_window": 12,
    },
    "NORMALE": {
        "player_hp": 4,
        "enemy_damage_mult": 1.0,
        "enemy_speed_mult": 1.0,
        "hack_time_limit": 5.0,
        "parry_window": 8,
    },
    "DIFFICILE": {
        "player_hp": 3,
        "enemy_damage_mult": 1.5,
        "enemy_speed_mult": 1.3,
        "hack_time_limit": 3.5,
        "parry_window": 6,
    },
}
CURRENT_DIFFICULTY = "NORMALE"
