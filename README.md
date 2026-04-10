# CTRL+ALT REVENGE! — Picchia Duro a Scorrimento

Platform a scorrimento laterale 16-bit con elementi metroidvania, hacking in tempo reale, parkour urbano e stealth leggero.

## Installazione

```bash
pip install pygame-ce
```

> Richiede Python 3.11+

## Avvio

```bash
python main.py
```

## Controlli

| Azione | Tastiera | Gamepad |
|---|---|---|
| Movimento | Frecce / WASD | Stick sinistro |
| Salto | SPAZIO / Z | A |
| Pugno | J / X | X |
| Calcio | K / C | Y |
| Parry | L / V | LB |
| Hack | E / Y | B |
| Accovacciati | GIU' | Stick giu' |
| Slide | GIU' + SALTO (durante corsa) | - |
| Innesti 1-4 | 1, 2, 3, 4 | - |
| Pausa | ESC / P | Start |

I controlli sono rebindabili in `ctrl_alt_revenge/settings.py` (`INPUT_MAP`).

## Protagonista — GIG

Uomo maturo con barba grigia, giacca marrone e braccio cyber sinistro con glow blu.

- **Movimento:** corsa, salto variabile (jump cut), doppio salto
- **Parkour:** wall-slide, wall-jump, slide sotto ostacoli bassi
- **Coyote time:** 6 frame, **Jump buffer:** 6 frame
- **Combat:** pugno + calcio (combo a 3 colpi), parry con finestra di 8 frame
- **Stealth:** accovacciato dimezza il cono di rilevamento nemici
- **HP:** 4 cuori, knockback + i-frames di 30 frame

## Innesti Modulari

| # | Nome | Slot | Effetto |
|---|---|---|---|
| 1 | Visione Termica | Occhi | Evidenzia nemici (toggle) |
| 2 | Proiettile EMP | Braccia | Stordisce nemici cibernetici (cooldown 6s) |
| 3 | Bullet Time | Core | 3 secondi di slow-mo, ricarica a uccisione |
| 4 | Doppio Salto | Gambe | Abilita il double jump |

## Hacking

Avvicinati a un terminale/drone e premi E. Si apre una griglia 4x4: traccia un percorso da START a END evitando i nodi rossi, in 5 secondi. Il gioco rallenta al 25% ma non si ferma.

## Nemici

- **Thug:** umano con bandana rossa, pattuglia e attacca corpo a corpo
- **Drone:** vola in sinusoide, spara laser telegrafato, hackabile (diventa alleato 8s)
- **Warden (Boss):** 3 fasi — melee, shockwave dal pavimento, spawn droni

## Livello 1 — "Sotto la Linea"

Tutorial movimento → terminale hackabile (apre cancello) → sezione stealth con telecamere → mini-arena con 3 thug → sezione platform verticale con wall-jump → arena boss Warden.

## Struttura del progetto

```
ctrl_alt_revenge/
├── main.py                     # entry point, game loop, FSM stati
├── settings.py                 # costanti, palette, input map
├── core/
│   ├── state_machine.py        # FSM per stati di gioco
│   ├── camera.py               # camera con lerp e clamp
│   ├── input.py                # astrazione tastiera + gamepad
│   ├── assets.py               # asset loader con cache
│   └── sprite_generator.py     # genera sprite pixel-art a runtime
├── entities/
│   ├── entity.py               # classe base
│   ├── player.py               # GIG: movimento, parkour, combat
│   ├── enemy.py                # base nemico con AI
│   ├── components.py           # mixin: Health, Hitbox, Hurtbox, AI, Hackable
│   └── enemies/
│       ├── thug.py             # scagnozzo umano
│       ├── drone.py            # drone volante hackabile
│       └── boss_warden.py      # boss livello 1 (3 fasi)
├── systems/
│   ├── physics.py              # AABB, gravita', collisioni tilemap
│   ├── combat.py               # collisioni hitbox/hurtbox
│   ├── hacking.py              # mini-gioco griglia 4x4
│   ├── implants.py             # innesti modulari
│   └── dialog.py               # dialoghi a scelta multipla
├── ui/
│   ├── hud.py                  # HUD: cuori, heat, slot innesti
│   ├── menu.py                 # menu principale, pausa, game over
│   └── dialog_box.py           # box dialogo con ritratto e typewriter
├── data/
│   ├── levels/level_01.py      # livello 1 generato programmaticamente
│   ├── dialogs/level_01_dialogs.py
│   └── implants.json
└── assets/ (vuoto — tutto generato a runtime)
```

## Sprite generati

Tutti gli sprite sono generati programmaticamente pixel per pixel in `sprite_generator.py`:

- **GIG:** 28 animazioni (idle, run, jump, fall, wall_slide, crouch, slide, punch x3, kick, parry, hurt, hack) in entrambe le direzioni
- **Thug:** 12 animazioni (idle, walk, attack, alert, hurt, death)
- **Drone:** 10 animazioni (fly, shoot, hacked, stunned, death con esplosione)
- **Warden:** 24 animazioni (idle, walk, melee, shockwave, spawn, hurt, death + varianti fase 2/3)
- **Oggetti:** terminale, telecamera, porte, laser, EMP, cuori, particelle

## Palette

| Colore | Hex | Uso |
|---|---|---|
| Sfondo notte | `#0d0b2b` | Background |
| Neon blu | `#00e5ff` | Cyber, UI attiva |
| Neon viola | `#a020f0` | Accenti |
| Neon arancione | `#ff7a1a` | Selezione, trim |
| Rosso allarme | `#ff2e4d` | Danno, alert |
| Bianco UI | `#f5f1d8` | Testi |

## Roadmap

- [ ] Tilemap esterna con Tiled (.tmx) + pytmx/pyscroll
- [ ] Audio: colonna sonora synthwave + effetti sonori
- [ ] Telecamere di sorveglianza funzionanti con cono visivo
- [ ] Sistema di checkpoint
- [ ] Livelli 2-5 con nuovi nemici e boss
- [ ] Cutscene pixel-art tra i livelli
- [ ] Negozio innesti tra i livelli
- [ ] Leaderboard locale
- [ ] Supporto gamepad completo (menu + hack)
- [ ] Sprite sheet esterne per sostituire i placeholder
- [ ] Effetti particellari avanzati (polvere, scintille, pioggia)
- [ ] Parallasse multi-layer con neon animati
