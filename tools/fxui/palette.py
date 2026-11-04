# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Tavolozza di effetti e interfaccia.

I colori del logo vengono dalla locandina (docs/riferimenti-estetica/
locandina-pixelart-chatgpt-2026-04-09.png), misurati come mediana dei pixel:
crema #f7e8bd, rosso del bordo #7a170f e #5e0f06, arancio del sottotitolo #c7772b
(qui schiarito per la leggibilità a 1x), giallo di "AGOSTO 2026" #e2a510.
"""
from pix import hexc

# --- inchiostri scuri (contorni, ombre) ---------------------------------------
INK = hexc("#0b0816")          # quasi nero viola: contorni dell'interfaccia
INK2 = hexc("#1a1230")         # viola notte
BG = hexc("#120f24")           # colore di sfondo del progetto (project.godot)

# --- logo e scritte grandi (dalla locandina) -----------------------------------
CREAM_HI = hexc("#fff7dc")
CREAM = hexc("#f7e8bd")
CREAM_LO = hexc("#e6cd96")
CREAM_LO2 = hexc("#cfae74")
RED = hexc("#9c2214")          # bordo, tono chiaro
RED_DARK = hexc("#7a170f")     # bordo della locandina
RED_DEEP = hexc("#4f0c07")     # estrusione e ombra del bordo
ORANGE_HI = hexc("#f6b25a")
ORANGE = hexc("#e48a2e")
ORANGE_LO = hexc("#b05d1c")
GOLD_HI = hexc("#ffe27a")
GOLD = hexc("#e2a510")
GOLD_LO = hexc("#a8700a")

# --- barre della vita ------------------------------------------------------------
BAR_GIG = [hexc("#fff3a6"), hexc("#f8d24a"), hexc("#eab12a"), hexc("#d18f16"), hexc("#9c600c")]
BAR_ENEMY = [hexc("#ffb08a"), hexc("#f2563a"), hexc("#d83a26"), hexc("#b22618"), hexc("#7a140c")]
BAR_GHOST = [hexc("#ffffff"), hexc("#fff4dc"), hexc("#f7e8bd"), hexc("#e6cd96"), hexc("#bfa37a")]
BAR_EMPTY = [hexc("#241a38"), hexc("#2e2346"), hexc("#2e2346"), hexc("#2a1f40"), hexc("#1f1730")]
METAL_HI = hexc("#c9c2de")
METAL = hexc("#8e86ab")
METAL_LO = hexc("#585073")
METAL_DK = hexc("#3a3352")

# --- effetti ----------------------------------------------------------------------
WHITE = hexc("#ffffff")
SPARK_PALE = hexc("#fff8c8")
SPARK_YEL = hexc("#ffd84a")
SPARK_ORA = hexc("#ff9a2a")
SPARK_RED = hexc("#e2471c")
SPARK_DRK = hexc("#9a2410")

CYAN_WHITE = hexc("#eafeff")
CYAN_HI = hexc("#9df6ff")
CYAN = hexc("#3fd8f0")
CYAN_MID = hexc("#1f9fd0")
CYAN_DEEP = hexc("#1b5a9a")

DUST_HI = hexc("#d6cce4")
DUST = hexc("#a99cbf")
DUST_MID = hexc("#80739a")
DUST_LO = hexc("#5c5176")

RAIN_HI = hexc("#d2defa")
RAIN = hexc("#9fb2e2")
RAIN_LO = hexc("#6f82b8")

SHADOW = hexc("#0b0816")
