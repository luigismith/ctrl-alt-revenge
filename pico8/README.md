# CTRL+ALT REVENGE! — PICO-8 ISO EDITION

Port fake-3D isometrico per **PICO-8**, la fantasy console di Lexaloffle.

![PICO-8](https://img.shields.io/badge/PICO--8-fantasy_console-purple)
![Lua](https://img.shields.io/badge/Lua-script-blue)
![16_colors](https://img.shields.io/badge/Palette-16_colors-orange)
![128x128](https://img.shields.io/badge/Resolution-128x128-yellow)

## Cosa cambia rispetto alla versione Pygame

| Aspetto | Pygame (originale) | PICO-8 (questa) |
|---------|----|----|
| **Visuale** | Side-scroller 2D | **Isometrico top-down (8 direzioni)** |
| **Risoluzione** | 320x240 → 960x720 | 128x128 (fantasy console nativa) |
| **Colori** | Palette cyberpunk custom | 16 colori PICO-8 fissi |
| **Gravita'** | Sì (X/Y con salti) | **No — movimento sul piano X/Y** |
| **Dimensione** | 14 MB exe | 32 KB .p8 cart |
| **Engine** | Pygame-CE + Python | PICO-8 Lua |

## Gameplay

Arena isometrica con tile a diamante. **GIG** si muove in 8 direzioni sul piano:
schiva, picchia, spara. Nessun salto — solo controllo top-down stile **Final Fight ISO**
o **Cadillacs & Dinosaurs** ribaltato in pianta.

### Controlli

| Tasto PICO-8 | Tastiera predefinita | Azione |
|---|---|---|
| ⬅️ ➡️ ⬆️ ⬇️ | Frecce | Movimento (8 direzioni, diagonali normalizzate) |
| 🅾️ | **Z** | Pugno (colpisce nella direzione di facing) |
| ❎ | **X** | Spara (hitscan, 6 colpi) |

### Nemici

- **Thug**: pattuglia random, insegue il player a 6 caselle, attacca a contatto. HP 2
- **Drone**: piu' veloce, fluttua piu' alto. HP 1

### Sistema

- 4 HP iniziali (cuori top-left)
- 6 colpi di pistola (top-left sotto cuori)
- CHIP guadagnati uccidendo nemici (top-right)
- Vinci eliminando tutti i nemici dell'arena
- Camera con lerp follow

## Tecnica isometrica

```lua
-- World (wx, wy) -> Screen (sx, sy) con proiezione 2:1
function w2s(wx, wy)
  return (wx - wy) * 8,   -- sx
         (wx + wy) * 4    -- sy
end
```

- **Tile**: rombi 16x8 pixel disegnati con line-scan
- **Sprite**: billboard (sempre frontale alla camera), 16x16 pixel
- **Ombra**: ellisse 7x1 sotto i piedi
- **Depth sorting**: tutti i drawables ordinati per `wx + wy` prima del disegno
- **Drone hover**: offset Y aggiuntivo + oscillazione sinusoidale

## Come giocare

### Opzione 1 — PICO-8 originale (Lexaloffle)

1. Scarica PICO-8 da [www.lexaloffle.com/pico-8](https://www.lexaloffle.com/pico-8.php)
2. Apri il file `ctrl_alt_revenge.p8` da dentro PICO-8 con `LOAD CTRL_ALT_REVENGE`
3. `RUN`

### Opzione 2 — Player web open-source

Usa [PICO-8 EDU](https://www.pico-8-edu.com/) o
[picotron-web](https://github.com/picolove/picolove) per caricare il `.p8`.

### Opzione 3 — Esporta HTML/binari

Dentro PICO-8:
```
LOAD ctrl_alt_revenge.p8
EXPORT ctrl_alt_revenge.html
EXPORT ctrl_alt_revenge.exe
```

## Struttura del cart

```
ctrl_alt_revenge.p8
├── __lua__       Script game logic (~400 righe)
│   ├── w2s()              Iso projection
│   ├── make_player()      Player state factory
│   ├── make_thug/drone()  Enemy factories
│   ├── update_player()    Movement + combat input
│   ├── update_enemy(e)    Patrol/chase/attack AI
│   ├── try_attack()       Melee hitbox check
│   ├── try_shoot()        Hitscan gun
│   ├── draw_floor()       Iso diamond tiles
│   ├── draw_billboard()   Sprite + shadow blit
│   ├── draw_player()      Animation state machine
│   ├── draw_enemy(e)      Sprite + iframes flash
│   ├── draw_title/win/gameover()
│   └── _init/update/draw  PICO-8 entry points
├── __gfx__       Sprite sheet (GIG idle/walk/punch, thug, drone)
├── __sfx__       4 SFX (punch, shoot, kill, hurt)
└── __music__     Loop musica gameplay
```

## Limiti PICO-8 e scelte di design

| Limite | Valore | Conseguenza |
|---|---|---|
| Risoluzione | 128x128 | Sprite 16x16 invece di 32x48 del Pygame |
| Token Lua | 8192 | Ridotto da ~5000 righe Python a ~400 righe Lua |
| Sprite slots | 256 (16x16=64) | 1 personaggio = 2 frame (idle+walk), no run completo |
| Colori | 16 fissi | Palette PICO-8 nativa (no neon custom) |
| Memoria | 32KB cart | Singolo livello/arena, no progressione tra zone |

## Estensioni possibili

- [ ] Boss Warden come grande sprite 32x32
- [ ] 3 arene consecutive (uso `__map__` per layout differenti)
- [ ] Pickup CHIP visibili sul terreno
- [ ] Hacking minigame
- [ ] Modalita' 2 giocatori (PICO-8 supporta multiplayer locale)
- [ ] Musica multi-pattern (intro/level/boss)

---

Il cart sta in **32 KB** per design — un beat'em-up isometrico completo dentro le
limitazioni della piu' famosa fantasy console del mondo.
