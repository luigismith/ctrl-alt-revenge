# core/sprite_generator.py — Genera sprite pixel-art per protagonista e nemici
# Ogni sprite è disegnato pixel per pixel sulla palette cyberpunk
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

# Colori aggiuntivi per dettagli
COLOR_EYE = (200, 220, 255)
COLOR_CYBER_ARM = (80, 90, 110)
COLOR_CYBER_GLOW = COLOR_NEON_BLUE
COLOR_THUG_SHIRT = (60, 20, 20)
COLOR_THUG_SKIN = (190, 150, 110)
COLOR_THUG_BANDANA = COLOR_RED_ALARM
COLOR_DRONE_BODY = (70, 75, 90)
COLOR_DRONE_LIGHT = COLOR_RED_ALARM
COLOR_WARDEN_ARMOR = (40, 45, 60)
COLOR_WARDEN_VISOR = COLOR_RED_ALARM
COLOR_WARDEN_TRIM = COLOR_NEON_ORANGE


def _set_pixel(surf, x, y, color):
    """Imposta un pixel, controllando i bordi."""
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)


def _draw_rect(surf, x, y, w, h, color):
    """Rettangolo pieno."""
    for py in range(y, y + h):
        for px in range(x, x + w):
            _set_pixel(surf, px, py, color)


def _mirror_h(surf):
    """Specchia orizzontalmente."""
    return pygame.transform.flip(surf, True, False)


# ============================================================
# PROTAGONISTA — GIG
# 16x28 pixel, uomo maturo, barba grigia, giacca marrone,
# braccio cyber sinistro con glow blu
# ============================================================

def _draw_gig_base(surf, facing_right=True):
    """Disegna il frame base di GIG (in piedi, rivolto a destra)."""
    # Stivali (riga 24-27)
    _draw_rect(surf, 3, 24, 4, 4, COLOR_BOOTS_BROWN)   # piede sinistro
    _draw_rect(surf, 9, 24, 4, 4, COLOR_BOOTS_BROWN)    # piede destro
    # Suola
    _draw_rect(surf, 3, 27, 4, 1, COLOR_BLACK)
    _draw_rect(surf, 9, 27, 4, 1, COLOR_BLACK)

    # Pantaloni (riga 17-23)
    _draw_rect(surf, 4, 17, 3, 7, COLOR_PANTS_DARK)     # gamba sinistra
    _draw_rect(surf, 9, 17, 3, 7, COLOR_PANTS_DARK)     # gamba destra
    # Cintura
    _draw_rect(surf, 4, 16, 8, 1, COLOR_BLACK)
    _set_pixel(surf, 7, 16, COLOR_NEON_ORANGE)  # fibbia
    _set_pixel(surf, 8, 16, COLOR_NEON_ORANGE)

    # Torso / giacca (riga 8-16)
    _draw_rect(surf, 4, 8, 8, 8, COLOR_JACKET_BROWN)
    # Ombra giacca lato sinistro
    _draw_rect(surf, 4, 8, 2, 8, COLOR_JACKET_SHADOW)
    # Colletto
    _draw_rect(surf, 5, 7, 6, 1, COLOR_JACKET_BROWN)
    # T-shirt sotto
    _draw_rect(surf, 6, 8, 4, 3, COLOR_DARK_GRAY)

    # Braccio destro (umano)
    _draw_rect(surf, 12, 9, 2, 6, COLOR_JACKET_BROWN)
    _draw_rect(surf, 12, 15, 2, 2, COLOR_SKIN)  # mano
    # Pugno
    _draw_rect(surf, 12, 15, 2, 2, COLOR_SKIN)

    # Braccio sinistro (cyber)
    _draw_rect(surf, 2, 9, 2, 6, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 15, 2, 2, COLOR_CYBER_ARM)
    # Glow linee cyber sul braccio
    _set_pixel(surf, 2, 10, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 12, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 14, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 11, COLOR_CYBER_GLOW)
    _set_pixel(surf, 3, 13, COLOR_CYBER_GLOW)

    # Testa (riga 0-7)
    _draw_rect(surf, 5, 1, 6, 6, COLOR_SKIN)
    # Capelli / coda (grigio)
    _draw_rect(surf, 5, 0, 6, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 11, 1, COLOR_HAIR_GRAY)   # coda laterale
    _set_pixel(surf, 11, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 12, 2, COLOR_HAIR_GRAY)
    # Barba
    _draw_rect(surf, 5, 5, 5, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 6, 6, 3, 1, COLOR_HAIR_GRAY)
    # Occhi
    _set_pixel(surf, 7, 3, COLOR_EYE)
    _set_pixel(surf, 9, 3, COLOR_EYE)
    # Pupille
    _set_pixel(surf, 8, 3, COLOR_BLACK)
    _set_pixel(surf, 10, 3, COLOR_BLACK)
    # Sopracciglia
    _set_pixel(surf, 7, 2, COLOR_BLACK)
    _set_pixel(surf, 9, 2, COLOR_BLACK)
    # Impianto occhio sinistro (glow)
    _set_pixel(surf, 6, 3, COLOR_NEON_BLUE)


def generate_gig_sprites():
    """Genera tutti i frame animazione di GIG.
    Restituisce un dizionario {nome_animazione: [frame1, frame2, ...]}
    Ogni frame è disponibile in entrambe le direzioni.
    """
    sprites = {}

    # --- IDLE (2 frame, leggero breathing) ---
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
        _draw_gig_base(surf)
        if f == 1:
            # Leggero spostamento torso verso l'alto (breathing)
            # Ridisegna spalle un pixel più su
            _set_pixel(surf, 6, 7, COLOR_JACKET_BROWN)
            _set_pixel(surf, 9, 7, COLOR_JACKET_BROWN)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # --- RUN (4 frame) ---
    run_frames = []
    leg_offsets = [(0, 0, 0, 0), (1, -1, -1, 1), (0, 0, 0, 0), (-1, 1, 1, -1)]
    for f in range(4):
        surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
        lox1, loy1, lox2, loy2 = leg_offsets[f]

        # Stivali con offset per camminata
        _draw_rect(surf, 3 + lox1, 24 + loy1, 4, 3, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 9 + lox2, 24 + loy2, 4, 3, COLOR_BOOTS_BROWN)
        _draw_rect(surf, 3 + lox1, 26 + loy1, 4, 1, COLOR_BLACK)
        _draw_rect(surf, 9 + lox2, 26 + loy2, 4, 1, COLOR_BLACK)

        # Gambe
        _draw_rect(surf, 4 + lox1, 17, 3, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 9 + lox2, 17, 3, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 4, 16, 8, 1, COLOR_BLACK)
        _set_pixel(surf, 7, 16, COLOR_NEON_ORANGE)
        _set_pixel(surf, 8, 16, COLOR_NEON_ORANGE)

        # Torso (leggero bob)
        bob = -1 if f in (1, 3) else 0
        _draw_rect(surf, 4, 8 + bob, 8, 8, COLOR_JACKET_BROWN)
        _draw_rect(surf, 4, 8 + bob, 2, 8, COLOR_JACKET_SHADOW)
        _draw_rect(surf, 5, 7 + bob, 6, 1, COLOR_JACKET_BROWN)
        _draw_rect(surf, 6, 8 + bob, 4, 3, COLOR_DARK_GRAY)

        # Braccia oscillano
        arm_swing = 2 if f in (0, 2) else -1
        _draw_rect(surf, 12, 9 + bob, 2, 6, COLOR_JACKET_BROWN)
        _draw_rect(surf, 12, 15 + bob + arm_swing, 2, 2, COLOR_SKIN)
        _draw_rect(surf, 2, 9 + bob, 2, 6, COLOR_CYBER_ARM)
        _draw_rect(surf, 2, 15 + bob - arm_swing, 2, 2, COLOR_CYBER_ARM)
        _set_pixel(surf, 2, 10 + bob, COLOR_CYBER_GLOW)
        _set_pixel(surf, 2, 12 + bob, COLOR_CYBER_GLOW)

        # Testa
        _draw_rect(surf, 5, 1 + bob, 6, 6, COLOR_SKIN)
        _draw_rect(surf, 5, 0 + bob, 6, 2, COLOR_HAIR_GRAY)
        _draw_rect(surf, 5, 5 + bob, 5, 2, COLOR_HAIR_GRAY)
        _set_pixel(surf, 7, 3 + bob, COLOR_EYE)
        _set_pixel(surf, 9, 3 + bob, COLOR_EYE)
        _set_pixel(surf, 8, 3 + bob, COLOR_BLACK)
        _set_pixel(surf, 10, 3 + bob, COLOR_BLACK)
        _set_pixel(surf, 6, 3 + bob, COLOR_NEON_BLUE)

        run_frames.append(surf)
    sprites["run_right"] = run_frames
    sprites["run_left"] = [_mirror_h(f) for f in run_frames]

    # --- JUMP (1 frame, gambe raccolte) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Stivali più in alto (gambe raccolte)
    _draw_rect(surf, 3, 22, 4, 3, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 9, 22, 4, 3, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4, 18, 3, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 9, 18, 3, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 4, 17, 8, 1, COLOR_BLACK)
    # Torso
    _draw_rect(surf, 4, 8, 8, 9, COLOR_JACKET_BROWN)
    _draw_rect(surf, 4, 8, 2, 9, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 6, 8, 4, 3, COLOR_DARK_GRAY)
    # Braccia su
    _draw_rect(surf, 12, 7, 2, 6, COLOR_JACKET_BROWN)
    _draw_rect(surf, 12, 13, 2, 2, COLOR_SKIN)
    _draw_rect(surf, 2, 7, 2, 6, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 13, 2, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 2, 8, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 10, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 12, COLOR_CYBER_GLOW)
    # Testa
    _draw_rect(surf, 5, 1, 6, 6, COLOR_SKIN)
    _draw_rect(surf, 5, 0, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 5, 5, 5, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 7, 3, COLOR_EYE)
    _set_pixel(surf, 9, 3, COLOR_EYE)
    _set_pixel(surf, 6, 3, COLOR_NEON_BLUE)
    sprites["jump_right"] = [surf]
    sprites["jump_left"] = [_mirror_h(surf)]

    # --- FALL (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Gambe estese verso il basso
    _draw_rect(surf, 3, 24, 4, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 9, 24, 4, 4, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 3, 27, 4, 1, COLOR_BLACK)
    _draw_rect(surf, 9, 27, 4, 1, COLOR_BLACK)
    _draw_rect(surf, 4, 17, 3, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 9, 17, 3, 7, COLOR_PANTS_DARK)
    _draw_rect(surf, 4, 16, 8, 1, COLOR_BLACK)
    # Torso
    _draw_rect(surf, 4, 8, 8, 8, COLOR_JACKET_BROWN)
    _draw_rect(surf, 4, 8, 2, 8, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 6, 8, 4, 3, COLOR_DARK_GRAY)
    # Braccia allargate
    _draw_rect(surf, 13, 9, 2, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 13, 14, 2, 2, COLOR_SKIN)
    _draw_rect(surf, 1, 9, 2, 5, COLOR_CYBER_ARM)
    _draw_rect(surf, 1, 14, 2, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 1, 10, COLOR_CYBER_GLOW)
    _set_pixel(surf, 1, 12, COLOR_CYBER_GLOW)
    # Testa
    _draw_rect(surf, 5, 1, 6, 6, COLOR_SKIN)
    _draw_rect(surf, 5, 0, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 5, 5, 5, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 7, 3, COLOR_EYE)
    _set_pixel(surf, 9, 3, COLOR_EYE)
    _set_pixel(surf, 6, 3, COLOR_NEON_BLUE)
    sprites["fall_right"] = [surf]
    sprites["fall_left"] = [_mirror_h(surf)]

    # --- WALL SLIDE (1 frame, attaccato al muro) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Sovrapponi braccio destro attaccato al muro (più in alto)
    _draw_rect(surf, 13, 5, 2, 8, COLOR_JACKET_BROWN)
    _draw_rect(surf, 13, 5, 2, 2, COLOR_SKIN)
    sprites["wall_slide_right"] = [surf]
    sprites["wall_slide_left"] = [_mirror_h(surf)]

    # --- CROUCH (1 frame, abbassato) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Tutto spostato giù, compresso verticalmente
    _draw_rect(surf, 3, 25, 4, 3, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 9, 25, 4, 3, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 4, 21, 3, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 9, 21, 3, 4, COLOR_PANTS_DARK)
    _draw_rect(surf, 4, 20, 8, 1, COLOR_BLACK)
    _draw_rect(surf, 4, 14, 8, 6, COLOR_JACKET_BROWN)
    _draw_rect(surf, 4, 14, 2, 6, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 6, 14, 4, 3, COLOR_DARK_GRAY)
    _draw_rect(surf, 12, 15, 2, 4, COLOR_JACKET_BROWN)
    _draw_rect(surf, 12, 19, 2, 2, COLOR_SKIN)
    _draw_rect(surf, 2, 15, 2, 4, COLOR_CYBER_ARM)
    _draw_rect(surf, 2, 19, 2, 2, COLOR_CYBER_ARM)
    _set_pixel(surf, 2, 16, COLOR_CYBER_GLOW)
    _set_pixel(surf, 2, 18, COLOR_CYBER_GLOW)
    _draw_rect(surf, 5, 8, 6, 6, COLOR_SKIN)
    _draw_rect(surf, 5, 7, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 5, 12, 5, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 7, 10, COLOR_EYE)
    _set_pixel(surf, 9, 10, COLOR_EYE)
    _set_pixel(surf, 6, 10, COLOR_NEON_BLUE)
    sprites["crouch_right"] = [surf]
    sprites["crouch_left"] = [_mirror_h(surf)]

    # --- SLIDE (1 frame, scivolata a terra) ---
    surf = pygame.Surface((PLAYER_WIDTH + 4, PLAYER_HEIGHT), pygame.SRCALPHA)
    # Corpo quasi orizzontale, piedi avanti
    _draw_rect(surf, 0, 20, 6, 3, COLOR_BOOTS_BROWN)
    _draw_rect(surf, 0, 17, 5, 3, COLOR_PANTS_DARK)
    _draw_rect(surf, 4, 15, 10, 5, COLOR_JACKET_BROWN)
    _draw_rect(surf, 4, 15, 2, 5, COLOR_JACKET_SHADOW)
    _draw_rect(surf, 6, 15, 4, 3, COLOR_DARK_GRAY)
    _draw_rect(surf, 14, 14, 6, 6, COLOR_SKIN)
    _draw_rect(surf, 14, 13, 6, 2, COLOR_HAIR_GRAY)
    _draw_rect(surf, 14, 18, 5, 2, COLOR_HAIR_GRAY)
    _set_pixel(surf, 16, 16, COLOR_EYE)
    _set_pixel(surf, 18, 16, COLOR_EYE)
    _set_pixel(surf, 15, 16, COLOR_NEON_BLUE)
    sprites["slide_right"] = [surf]
    sprites["slide_left"] = [_mirror_h(surf)]

    # --- PUNCH (3 frame combo) ---
    for combo_idx in range(3):
        surf = pygame.Surface((PLAYER_WIDTH + 6, PLAYER_HEIGHT), pygame.SRCALPHA)
        _draw_gig_base(surf)
        # Pugno esteso in avanti - braccio si allunga progressivamente
        arm_extend = 3 + combo_idx * 2
        arm_y = 11 - combo_idx  # leggermente più alto per ogni colpo
        if combo_idx < 2:
            # Pugno con braccio destro
            _draw_rect(surf, 14, arm_y, arm_extend, 2, COLOR_JACKET_BROWN)
            _draw_rect(surf, 14 + arm_extend - 2, arm_y, 3, 3, COLOR_SKIN)
            # Flash d'impatto
            _set_pixel(surf, 14 + arm_extend + 1, arm_y, COLOR_NEON_ORANGE)
            _set_pixel(surf, 14 + arm_extend + 1, arm_y + 1, COLOR_YELLOW)
        else:
            # Calcio finale della combo - gamba estesa
            _draw_rect(surf, 13, 20, arm_extend + 2, 2, COLOR_PANTS_DARK)
            _draw_rect(surf, 13 + arm_extend, 19, 3, 3, COLOR_BOOTS_BROWN)
            _set_pixel(surf, 13 + arm_extend + 2, 20, COLOR_NEON_ORANGE)
            _set_pixel(surf, 13 + arm_extend + 3, 20, COLOR_YELLOW)
        sprites[f"punch{combo_idx}_right"] = [surf]
        sprites[f"punch{combo_idx}_left"] = [_mirror_h(surf)]

    # --- KICK (1 frame) ---
    surf = pygame.Surface((PLAYER_WIDTH + 6, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    _draw_rect(surf, 13, 18, 6, 2, COLOR_PANTS_DARK)
    _draw_rect(surf, 18, 17, 3, 3, COLOR_BOOTS_BROWN)
    _set_pixel(surf, 21, 18, COLOR_NEON_ORANGE)
    sprites["kick_right"] = [surf]
    sprites["kick_left"] = [_mirror_h(surf)]

    # --- PARRY (1 frame, guardia alta) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Braccia incrociate davanti
    _draw_rect(surf, 5, 7, 6, 3, COLOR_CYBER_ARM)
    _draw_rect(surf, 5, 7, 6, 1, COLOR_CYBER_GLOW)
    # Scudo energetico sottile
    for i in range(8):
        _set_pixel(surf, 4, 5 + i, COLOR_NEON_BLUE)
    sprites["parry_right"] = [surf]
    sprites["parry_left"] = [_mirror_h(surf)]

    # --- HURT (1 frame, knockback) ---
    surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Tilt all'indietro, flash rosso
    _draw_rect(surf, 4, 8, 8, 8, COLOR_RED_ALARM)  # flash rosso sul torso
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # --- HACK (1 frame, mano cyber estesa con ologramma) ---
    surf = pygame.Surface((PLAYER_WIDTH + 8, PLAYER_HEIGHT), pygame.SRCALPHA)
    _draw_gig_base(surf)
    # Braccio cyber esteso con proiezione olografica
    _draw_rect(surf, 0, 9, 2, 6, COLOR_CYBER_ARM)
    # Ologramma (quadratini verdi)
    for hy in range(4):
        for hx in range(4):
            if (hx + hy) % 2 == 0:
                _set_pixel(surf, hx + PLAYER_WIDTH, 8 + hy, COLOR_GREEN_HACK)
            else:
                _set_pixel(surf, hx + PLAYER_WIDTH, 8 + hy, (0, 180, 60, 150))
    sprites["hack_right"] = [surf]
    sprites["hack_left"] = [_mirror_h(surf)]

    return sprites


# ============================================================
# THUG — Scagnozzo umano
# 16x28, bandana rossa, maglietta scura, pugni
# ============================================================

def generate_thug_sprites():
    sprites = {}

    def _draw_thug_base(surf, alert=False):
        # Stivali
        _draw_rect(surf, 3, 24, 4, 4, COLOR_BLACK)
        _draw_rect(surf, 9, 24, 4, 4, COLOR_BLACK)
        # Pantaloni
        _draw_rect(surf, 4, 17, 3, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 9, 17, 3, 7, COLOR_PANTS_DARK)
        _draw_rect(surf, 4, 16, 8, 1, COLOR_BLACK)
        # Torso
        body_color = COLOR_RED_ALARM if alert else COLOR_THUG_SHIRT
        _draw_rect(surf, 4, 8, 8, 8, body_color)
        _draw_rect(surf, 6, 8, 4, 3, COLOR_DARK_GRAY)
        # Braccia
        _draw_rect(surf, 12, 9, 2, 6, body_color)
        _draw_rect(surf, 12, 15, 2, 2, COLOR_THUG_SKIN)
        _draw_rect(surf, 2, 9, 2, 6, body_color)
        _draw_rect(surf, 2, 15, 2, 2, COLOR_THUG_SKIN)
        # Testa
        _draw_rect(surf, 5, 1, 6, 6, COLOR_THUG_SKIN)
        # Bandana rossa
        _draw_rect(surf, 5, 0, 6, 2, COLOR_THUG_BANDANA)
        _set_pixel(surf, 11, 1, COLOR_THUG_BANDANA)
        _set_pixel(surf, 12, 2, COLOR_THUG_BANDANA)
        # Occhi — linea minacciosa
        _set_pixel(surf, 7, 3, COLOR_BLACK)
        _set_pixel(surf, 9, 3, COLOR_BLACK)
        # Bocca
        _set_pixel(surf, 7, 5, COLOR_BLACK)
        _set_pixel(surf, 8, 5, COLOR_BLACK)

    # IDLE
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
        _draw_thug_base(surf)
        if f == 1:
            _set_pixel(surf, 6, 7, COLOR_THUG_SHIRT)
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    leg_off = [(0, 0), (1, -1), (0, 0), (-1, 1)]
    for f in range(4):
        surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
        _draw_thug_base(surf)
        # Sovrascrive piedi con offset
        lo1, lo2 = leg_off[f]
        _draw_rect(surf, 3 + lo1, 24, 4, 4, COLOR_BLACK)
        _draw_rect(surf, 9 + lo2, 24, 4, 4, COLOR_BLACK)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # ATTACK
    surf = pygame.Surface((THUG_WIDTH + 6, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 14, 11, 5, 2, COLOR_THUG_SHIRT)
    _draw_rect(surf, 18, 10, 3, 3, COLOR_THUG_SKIN)
    _set_pixel(surf, 21, 11, COLOR_RED_ALARM)
    sprites["attack_right"] = [surf]
    sprites["attack_left"] = [_mirror_h(surf)]

    # ALERT (in allerta)
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf, alert=True)
    # Punto esclamativo sopra la testa
    _draw_rect(surf, 7, -3, 2, 3, COLOR_RED_ALARM)
    _set_pixel(surf, 7, 0, COLOR_RED_ALARM)
    sprites["alert_right"] = [surf]
    sprites["alert_left"] = [_mirror_h(surf)]

    # HURT
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 4, 8, 8, 8, (255, 100, 100, 180))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (2 frame)
    death_frames = []
    # Frame 1: barcollamento
    surf = pygame.Surface((THUG_WIDTH, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_thug_base(surf)
    _draw_rect(surf, 4, 8, 8, 8, (255, 100, 100, 100))
    death_frames.append(surf)
    # Frame 2: a terra (quasi orizzontale)
    surf = pygame.Surface((THUG_WIDTH + 8, THUG_HEIGHT), pygame.SRCALPHA)
    _draw_rect(surf, 0, 22, 20, 4, COLOR_THUG_SHIRT)
    _draw_rect(surf, 16, 21, 6, 5, COLOR_THUG_SKIN)
    _draw_rect(surf, 16, 20, 6, 2, COLOR_THUG_BANDANA)
    death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = [_mirror_h(f) for f in death_frames]

    return sprites


# ============================================================
# DRONE — Drone volante con laser
# 20x12, corpo metallico, luce rossa, eliche
# ============================================================

def generate_drone_sprites():
    sprites = {}

    def _draw_drone_base(surf, propeller_frame=0):
        w, h = DRONE_WIDTH, DRONE_HEIGHT
        # Corpo centrale
        _draw_rect(surf, 5, 4, 10, 6, COLOR_DRONE_BODY)
        _draw_rect(surf, 6, 3, 8, 1, COLOR_DRONE_BODY)
        _draw_rect(surf, 6, 10, 8, 1, COLOR_DRONE_BODY)
        # Pannello ventrale
        _draw_rect(surf, 7, 8, 6, 2, COLOR_MID_GRAY)
        # Occhio/sensore rosso
        _draw_rect(surf, 9, 5, 2, 2, COLOR_DRONE_LIGHT)
        _set_pixel(surf, 8, 5, (255, 100, 100))
        _set_pixel(surf, 11, 5, (255, 100, 100))
        # Eliche (cambiano frame)
        if propeller_frame == 0:
            _draw_rect(surf, 1, 2, 4, 1, COLOR_MID_GRAY)
            _draw_rect(surf, 15, 2, 4, 1, COLOR_MID_GRAY)
        else:
            _draw_rect(surf, 2, 2, 2, 1, COLOR_MID_GRAY)
            _draw_rect(surf, 16, 2, 2, 1, COLOR_MID_GRAY)
        # Supporto eliche
        _set_pixel(surf, 3, 3, COLOR_DARK_GRAY)
        _set_pixel(surf, 17, 3, COLOR_DARK_GRAY)
        # Antenne
        _set_pixel(surf, 4, 1, COLOR_NEON_BLUE)
        _set_pixel(surf, 15, 1, COLOR_NEON_BLUE)

    # FLY (2 frame per eliche)
    fly_frames = []
    for f in range(2):
        surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
        _draw_drone_base(surf, f)
        fly_frames.append(surf)
    sprites["fly_right"] = fly_frames
    sprites["fly_left"] = [_mirror_h(f) for f in fly_frames]

    # SHOOT (1 frame, con laser)
    surf = pygame.Surface((DRONE_WIDTH + 8, DRONE_HEIGHT + 4), pygame.SRCALPHA)
    _draw_drone_base(surf, 0)
    # Laser in basso
    for i in range(8):
        _set_pixel(surf, 10, DRONE_HEIGHT + i, COLOR_RED_ALARM)
        _set_pixel(surf, 9, DRONE_HEIGHT + i, (255, 46, 77, 100))
        _set_pixel(surf, 11, DRONE_HEIGHT + i, (255, 46, 77, 100))
    sprites["shoot_right"] = [surf]
    sprites["shoot_left"] = [_mirror_h(surf)]

    # HACKED (alleato, glow verde)
    surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
    _draw_drone_base(surf, 0)
    # Sovrascrivi occhio con verde
    _draw_rect(surf, 9, 5, 2, 2, COLOR_GREEN_HACK)
    _set_pixel(surf, 8, 5, (0, 200, 80))
    _set_pixel(surf, 11, 5, (0, 200, 80))
    sprites["hacked_right"] = [surf]
    sprites["hacked_left"] = [_mirror_h(surf)]

    # STUNNED (EMP)
    surf = pygame.Surface((DRONE_WIDTH, DRONE_HEIGHT), pygame.SRCALPHA)
    _draw_drone_base(surf, 0)
    # Scintille
    for i in range(3):
        _set_pixel(surf, 5 + i * 4, 1, COLOR_YELLOW)
        _set_pixel(surf, 6 + i * 4, 0, COLOR_YELLOW)
    sprites["stunned_right"] = [surf]
    sprites["stunned_left"] = [_mirror_h(surf)]

    # DEATH (esplosione)
    death_frames = []
    for f in range(3):
        surf = pygame.Surface((DRONE_WIDTH + 4, DRONE_HEIGHT + 4), pygame.SRCALPHA)
        # Esplosione crescente
        radius = 3 + f * 2
        cx, cy = DRONE_WIDTH // 2, DRONE_HEIGHT // 2
        colors = [COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_YELLOW]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    _set_pixel(surf, cx + dx + 2, cy + dy + 2, colors[f])
        # Frammenti
        if f > 0:
            for i in range(4):
                fx = cx + int(math.cos(i * 1.5 + f) * (radius + 2))
                fy = cy + int(math.sin(i * 1.5 + f) * (radius + 2))
                _set_pixel(surf, fx + 2, fy + 2, COLOR_DRONE_BODY)
        death_frames.append(surf)
    sprites["death_right"] = death_frames
    sprites["death_left"] = death_frames  # esplosione simmetrica

    return sprites


# ============================================================
# WARDEN — Boss livello 1
# 32x40, armatura pesante, visiera rossa, trim arancione
# ============================================================

def generate_warden_sprites():
    sprites = {}

    def _draw_warden_base(surf, phase=0):
        w, h = WARDEN_WIDTH, WARDEN_HEIGHT
        # Stivali pesanti
        _draw_rect(surf, 5, 34, 8, 6, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 19, 34, 8, 6, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 5, 39, 8, 1, COLOR_BLACK)
        _draw_rect(surf, 19, 39, 8, 1, COLOR_BLACK)
        # Trim luminoso sugli stivali
        _draw_rect(surf, 5, 34, 8, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 19, 34, 8, 1, COLOR_WARDEN_TRIM)

        # Gambali
        _draw_rect(surf, 7, 24, 6, 10, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 19, 24, 6, 10, COLOR_WARDEN_ARMOR)
        # Ginocchiere
        _draw_rect(surf, 7, 28, 6, 2, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 19, 28, 6, 2, COLOR_WARDEN_TRIM)

        # Cintura tech
        _draw_rect(surf, 6, 22, 20, 2, COLOR_DARK_GRAY)
        _draw_rect(surf, 14, 22, 4, 2, COLOR_NEON_ORANGE)

        # Torso corazzato
        _draw_rect(surf, 6, 10, 20, 12, COLOR_WARDEN_ARMOR)
        # Piastra pettorale
        _draw_rect(surf, 8, 11, 16, 8, (50, 55, 70))
        # Linee trim
        _draw_rect(surf, 8, 11, 16, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 8, 18, 16, 1, COLOR_WARDEN_TRIM)
        # Core luminoso (cambia colore per fase)
        core_colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_RED_ALARM]
        core_col = core_colors[min(phase, 2)]
        _draw_rect(surf, 14, 14, 4, 3, core_col)
        _draw_rect(surf, 15, 13, 2, 1, core_col)
        _draw_rect(surf, 15, 17, 2, 1, core_col)

        # Spalline massive
        _draw_rect(surf, 2, 8, 6, 4, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 24, 8, 6, 4, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 2, 8, 6, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 24, 8, 6, 1, COLOR_WARDEN_TRIM)

        # Braccia
        _draw_rect(surf, 2, 12, 4, 10, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 26, 12, 4, 10, COLOR_WARDEN_ARMOR)
        # Guanti
        _draw_rect(surf, 2, 22, 4, 3, COLOR_DARK_GRAY)
        _draw_rect(surf, 26, 22, 4, 3, COLOR_DARK_GRAY)
        # Glow sui guanti
        _set_pixel(surf, 3, 23, core_col)
        _set_pixel(surf, 27, 23, core_col)

        # Testa / elmo
        _draw_rect(surf, 9, 1, 14, 9, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 10, 0, 12, 1, COLOR_WARDEN_ARMOR)
        # Visiera
        _draw_rect(surf, 10, 4, 12, 3, COLOR_WARDEN_VISOR)
        # Barra luminosa centrale visiera
        _draw_rect(surf, 12, 5, 8, 1, (255, 150, 150))
        # Trim elmo
        _draw_rect(surf, 9, 1, 14, 1, COLOR_WARDEN_TRIM)
        # Antenna
        _set_pixel(surf, 15, 0, COLOR_RED_ALARM)
        _set_pixel(surf, 16, 0, COLOR_RED_ALARM)

    # IDLE (2 frame)
    idle_frames = []
    for f in range(2):
        surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        if f == 1:
            # Pulsazione core
            _draw_rect(surf, 14, 14, 4, 3, (0, 200, 255))
        idle_frames.append(surf)
    sprites["idle_right"] = idle_frames
    sprites["idle_left"] = [_mirror_h(f) for f in idle_frames]

    # WALK (4 frame)
    walk_frames = []
    for f in range(4):
        surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        # Piedi oscillano
        off = [0, 2, 0, -2][f]
        _draw_rect(surf, 5, 34, 8, 6, COLOR_BG_NIGHT)  # cancella
        _draw_rect(surf, 19, 34, 8, 6, COLOR_BG_NIGHT)
        _draw_rect(surf, 5 + off, 34, 8, 6, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 19 - off, 34, 8, 6, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, 5 + off, 34, 8, 1, COLOR_WARDEN_TRIM)
        _draw_rect(surf, 19 - off, 34, 8, 1, COLOR_WARDEN_TRIM)
        walk_frames.append(surf)
    sprites["walk_right"] = walk_frames
    sprites["walk_left"] = [_mirror_h(f) for f in walk_frames]

    # MELEE ATTACK (2 frame)
    for f in range(2):
        surf = pygame.Surface((WARDEN_WIDTH + 12, WARDEN_HEIGHT), pygame.SRCALPHA)
        _draw_warden_base(surf, 0)
        # Braccio destro esteso con pugno energetico
        arm_ext = 6 + f * 4
        _draw_rect(surf, WARDEN_WIDTH - 2, 14, arm_ext, 4, COLOR_WARDEN_ARMOR)
        _draw_rect(surf, WARDEN_WIDTH - 2 + arm_ext - 3, 13, 5, 5, COLOR_NEON_ORANGE)
        _draw_rect(surf, WARDEN_WIDTH - 2 + arm_ext - 2, 14, 3, 3, COLOR_YELLOW)
        sprites[f"melee{f}_right"] = [surf]
        sprites[f"melee{f}_left"] = [_mirror_h(surf)]

    # SHOCKWAVE (1 frame, battuta a terra)
    surf = pygame.Surface((WARDEN_WIDTH + 8, WARDEN_HEIGHT + 4), pygame.SRCALPHA)
    _draw_warden_base(surf, 1)
    # Onde shock dal pavimento
    for i in range(4):
        wave_w = (i + 1) * 6
        alpha = 255 - i * 50
        for wx in range(-wave_w, wave_w):
            _set_pixel(surf, WARDEN_WIDTH // 2 + wx + 4,
                       WARDEN_HEIGHT + i, (*COLOR_NEON_ORANGE[:3], max(0, alpha)))
    sprites["shockwave_right"] = [surf]
    sprites["shockwave_left"] = [_mirror_h(surf)]

    # SPAWN DRONES (1 frame, braccia alzate)
    surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    _draw_warden_base(surf, 1)
    # Braccia alzate
    _draw_rect(surf, 2, 4, 4, 8, COLOR_WARDEN_ARMOR)
    _draw_rect(surf, 26, 4, 4, 8, COLOR_WARDEN_ARMOR)
    # Segnale radio
    _set_pixel(surf, 1, 3, COLOR_RED_ALARM)
    _set_pixel(surf, 0, 2, COLOR_RED_ALARM)
    _set_pixel(surf, 30, 3, COLOR_RED_ALARM)
    _set_pixel(surf, 31, 2, COLOR_RED_ALARM)
    sprites["spawn_right"] = [surf]
    sprites["spawn_left"] = [_mirror_h(surf)]

    # PHASE 2 (armatura danneggiata, più veloce)
    for anim in ["idle", "walk"]:
        p2_frames = []
        for f in sprites[f"{anim}_right"]:
            surf = f.copy()
            # Crepe / danni visivi
            _set_pixel(surf, 10, 13, COLOR_BLACK)
            _set_pixel(surf, 11, 14, COLOR_BLACK)
            _set_pixel(surf, 12, 15, COLOR_BLACK)
            _set_pixel(surf, 20, 12, COLOR_BLACK)
            _set_pixel(surf, 21, 13, COLOR_BLACK)
            # Core arancione
            _draw_rect(surf, 14, 14, 4, 3, COLOR_NEON_ORANGE)
            p2_frames.append(surf)
        sprites[f"{anim}_p2_right"] = p2_frames
        sprites[f"{anim}_p2_left"] = [_mirror_h(f) for f in p2_frames]

    # PHASE 3 (armatura molto danneggiata, core rosso)
    for anim in ["idle", "walk"]:
        p3_frames = []
        for f in sprites[f"{anim}_right"]:
            surf = f.copy()
            # Più crepe
            for cy in range(12, 20):
                _set_pixel(surf, 10 + (cy % 3), cy, COLOR_BLACK)
                _set_pixel(surf, 20 - (cy % 3), cy, COLOR_BLACK)
            # Spalline danneggiate
            _draw_rect(surf, 2, 10, 3, 2, COLOR_BLACK)
            _draw_rect(surf, 27, 10, 3, 2, COLOR_BLACK)
            # Core rosso
            _draw_rect(surf, 14, 14, 4, 3, COLOR_RED_ALARM)
            p3_frames.append(surf)
        sprites[f"{anim}_p3_right"] = p3_frames
        sprites[f"{anim}_p3_left"] = [_mirror_h(f) for f in p3_frames]

    # HURT
    surf = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    _draw_warden_base(surf, 0)
    # Flash bianco
    overlay = pygame.Surface((WARDEN_WIDTH, WARDEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 100))
    surf.blit(overlay, (0, 0))
    sprites["hurt_right"] = [surf]
    sprites["hurt_left"] = [_mirror_h(surf)]

    # DEATH (3 frame, esplosione progressiva)
    death_frames = []
    for f in range(4):
        surf = pygame.Surface((WARDEN_WIDTH + 8, WARDEN_HEIGHT + 8), pygame.SRCALPHA)
        if f < 2:
            _draw_warden_base(surf, 2)
            # Esplosioni parziali
            for i in range(f + 1):
                cx = 12 + i * 8
                cy = 15 + i * 5
                for dy in range(-3, 4):
                    for dx in range(-3, 4):
                        if dx * dx + dy * dy <= 9:
                            _set_pixel(surf, cx + dx + 4, cy + dy + 4, COLOR_NEON_ORANGE)
        else:
            # Esplosione piena
            cx, cy = WARDEN_WIDTH // 2 + 4, WARDEN_HEIGHT // 2 + 4
            radius = 8 + (f - 2) * 6
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


# ============================================================
# OGGETTI VARI: telecamera, terminale, proiettile laser, particelle
# ============================================================

def generate_camera_sprite():
    """Telecamera di sorveglianza 12x8."""
    surf = pygame.Surface((12, 8), pygame.SRCALPHA)
    _draw_rect(surf, 2, 0, 2, 3, COLOR_MID_GRAY)    # supporto
    _draw_rect(surf, 0, 3, 8, 5, COLOR_DARK_GRAY)     # corpo
    _draw_rect(surf, 8, 4, 4, 3, COLOR_MID_GRAY)      # lente
    _draw_rect(surf, 10, 5, 2, 1, COLOR_RED_ALARM)     # LED
    return surf


def generate_terminal_sprite():
    """Terminale hackabile 16x16."""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    _draw_rect(surf, 2, 2, 12, 10, COLOR_DARK_GRAY)    # monitor
    _draw_rect(surf, 3, 3, 10, 8, COLOR_BG_NIGHT)       # schermo
    # Testo sullo schermo
    for i in range(3):
        _draw_rect(surf, 4, 4 + i * 2, 6 + (i % 2) * 2, 1, COLOR_GREEN_HACK)
    # Base
    _draw_rect(surf, 5, 12, 6, 1, COLOR_MID_GRAY)
    _draw_rect(surf, 4, 13, 8, 2, COLOR_DARK_GRAY)
    # Luce stato
    _set_pixel(surf, 13, 10, COLOR_GREEN_HACK)
    return surf


def generate_door_sprites():
    """Porta/cancello 16x32, aperta e chiusa."""
    sprites = {}
    # Chiusa
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 16, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 1, 1, 14, 30, COLOR_MID_GRAY)
    # Barre orizzontali
    for i in range(4):
        _draw_rect(surf, 1, 1 + i * 8, 14, 1, COLOR_DARK_GRAY)
    # Luce rossa = bloccata
    _draw_rect(surf, 7, 14, 2, 2, COLOR_RED_ALARM)
    sprites["closed"] = surf

    # Aperta
    surf = pygame.Surface((16, 32), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 4, 32, COLOR_DARK_GRAY)
    _draw_rect(surf, 12, 0, 4, 32, COLOR_DARK_GRAY)
    # Luce verde = aperta
    _draw_rect(surf, 1, 14, 2, 2, COLOR_GREEN_HACK)
    _draw_rect(surf, 13, 14, 2, 2, COLOR_GREEN_HACK)
    sprites["open"] = surf

    return sprites


def generate_laser_sprite():
    """Proiettile laser del drone, 6x2."""
    surf = pygame.Surface((6, 2), pygame.SRCALPHA)
    _draw_rect(surf, 0, 0, 6, 2, COLOR_RED_ALARM)
    _draw_rect(surf, 1, 0, 4, 2, (255, 150, 150))
    return surf


def generate_emp_sprite():
    """Proiettile EMP, 8x8 cerchio blu."""
    surf = pygame.Surface((8, 8), pygame.SRCALPHA)
    cx, cy = 4, 4
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if dx * dx + dy * dy <= 9:
                _set_pixel(surf, cx + dx, cy + dy, COLOR_NEON_BLUE)
            elif dx * dx + dy * dy <= 16:
                _set_pixel(surf, cx + dx, cy + dy, (0, 229, 255, 100))
    return surf


def generate_heart_sprite(full=True):
    """Cuore per l'HUD, 7x7."""
    surf = pygame.Surface((7, 7), pygame.SRCALPHA)
    color = COLOR_RED_ALARM if full else COLOR_DARK_GRAY
    # Forma cuore pixel
    pattern = [
        "._._._.",
        "__._..__",  # troppo largo, usiamo coordinate dirette
    ]
    heart_pixels = [
        (1, 0), (2, 0), (4, 0), (5, 0),
        (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1),
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (1, 3), (2, 3), (3, 3), (4, 3), (5, 3),
        (2, 4), (3, 4), (4, 4),
        (3, 5),
    ]
    for px, py in heart_pixels:
        _set_pixel(surf, px, py, color)
    return surf


def generate_particle_sprites():
    """Particelle varie per effetti."""
    particles = {}
    # Scintilla
    surf = pygame.Surface((3, 3), pygame.SRCALPHA)
    _set_pixel(surf, 1, 0, COLOR_YELLOW)
    _set_pixel(surf, 0, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 1, COLOR_WHITE_UI)
    _set_pixel(surf, 2, 1, COLOR_YELLOW)
    _set_pixel(surf, 1, 2, COLOR_YELLOW)
    particles["spark"] = surf

    # Hit effect
    surf = pygame.Surface((5, 5), pygame.SRCALPHA)
    _set_pixel(surf, 2, 0, COLOR_NEON_ORANGE)
    _set_pixel(surf, 0, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 4, 2, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 4, COLOR_NEON_ORANGE)
    _set_pixel(surf, 2, 2, COLOR_YELLOW)
    particles["hit"] = surf

    # Polvere
    surf = pygame.Surface((2, 2), pygame.SRCALPHA)
    surf.fill((200, 200, 200, 120))
    particles["dust"] = surf

    return particles


def generate_all_sprites():
    """Genera tutti gli sprite del gioco, restituisce un dizionario globale."""
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
