# tools/env: oggetti di scena 3D, cielo e piani lontani

Dal 7 novembre 2026 gli sfondi di «Sotto la Linea» nascono da basi fatte con ChatGPT e ridotte in pixel art. Questa cartella fa ancora il cielo, i piani lontani, gli oggetti di scena 3D e il carattere pixel delle insegne. Tutto è deterministico: due esecuzioni danno file identici byte per byte.

Chi fa cosa:

| File del gioco | Chi lo fa |
|---|---|
| `env/sotto_la_linea/sky.png`, `far.png`, `far_emis.png`, `mid.png`, `mid_emis.png` | `taranto.py --mid` |
| `backdrop`, `near`, `fg` (con le loro `_emis`) | `tools/ambienti/componi_slice.py` |
| `floor.png` (la patina del minerale) | `tools/ambienti/patina_floor.py` |
| `props/cable.png`, `cable.json` (il cavo scoperto e il rivolo) | `tools/ambienti/cavo_rivolo.py` |
| `props/bin.png`, `bin.json`, `apple.png`, `apple.json` | `build_all.py` (cioè `props.py`) |

`layers.json` e `floor_emis.png` non li genera più nessuno script: si correggono a mano.

```
python -I tools/env/build_all.py             # il bidone e la mela, in tools/env/out/props/
python -I tools/env/build_all.py --install   # ... e li copia in game/assets/props
python -I tools/env/taranto.py --mid --uscita DIR   # cielo, far e mid; poi si copiano a mano in game/assets
python -I tools/env/compose.py all game/assets/env/sotto_la_linea DIR   # inquadrature di controllo (DIR deve esistere)
```

Serve il laboratorio in `%USERPROFILE%/ctrlaltrevenge-lab`:
- Blender 4.5 portable, per il bidone e la mela;
- il Python del `venv`, sempre con l'opzione `-I`;
- per `taranto.py`, le basi nella cartella privata condivisa (`ambienti-ai/sotto-la-linea`).

## I file

- **`props.py`** fa gli oggetti di scena nel formato sprite della specifica §4. La geometria è in metri, il render passa per `tools/blender/env_gbuffer.py` (GPL), che scrive un G-buffer senza anti-aliasing; la luce è sfumata.
  - `bin`: `idle`, `hit` (3 fotogrammi, `sfx:bin_hit`), `break` (4 fotogrammi, `sfx:bin_break`, l'ultimo `hold`). Ancora a terra al centro, `hurt` [-15, -48, 30, 48]. Nel livello sta in (x 1313, y 200).
  - `apple`: 2 fotogrammi, il secondo con il luccichio. `hurt` [-10, -18, 20, 18] è l'area di raccolta.
- **`paint.py`** fa da "shader differito" in Python per `props.py`: motivi per materiale, luce chiave, palette con le rampe di `materials.py` (colore più vicino in OKLab), contorni di 1 px (`#140e1e` come i personaggi).
- **`envlib.py`**: la vista dei personaggi (`tools/sprites/camera.json`: yaw 30, pitch 12, 60 px/m), le classi dei materiali, il lancio di Blender e le conversioni di colore.
- **`pixfont.py`**: il carattere pixel delle insegne, disegnato da noi. Lo usa `tools/ambienti/componi_slice.py`.
- **`taranto.py`**: il cielo di polvere rossa del Wind Day, il piano lontano con l'area a caldo e la torre di SIDERA, e il piano dei palazzi. Le spiegazioni sono in testa al file.
- **`compose.py`**: compone le inquadrature come il gioco (piano in `floor(−scroll·cam + 0.5)`, emissivi in modo additivo) da una cartella con `layers.json`. Fa i mockup con gli sprite del gioco, la GIF di scorrimento, la tavola dei piani e i controlli.
- **`install.py`**: copia il bidone e la mela in `game/assets/props`, prima con il nome `.tmp` e poi rinominando.

## Scala

Dal 5 novembre 2026 lo schermo è 480×270 e la vista ha 60 px/m; prima erano 384×216 e 48 px/m. Le misure in pixel di progetto di `props.py` sono ancora a 48 px/m e passano per `envlib.px()`, cioè `floor(p × 1,25 + 0,5)`, la stessa regola dei dati del livello. I rettangoli degli oggetti si convertono sui bordi, simmetrici rispetto all'ancora (per esempio −12…12 diventa −15…15).

## Note per il codice

- **Piani** (`layers.json`): sette piani, tutti senza ripetizione (`repeat_x` 0).
  - Le larghezze sono quelle minime, 480 + 1920 × scroll: `sky` 480, `far` 720, `mid` 960, `near` 1440, `backdrop` e `floor` 2400, `fg` 2880.
  - Le righe di partenza: `sky` 0, `far` 33, `mid` 18, `near` 0, `backdrop` 0, `floor` 162, `fg` 0.
  - `floor` parte da y 162 perché contiene anche la base delle cose basse davanti alle facciate. `floor` e `backdrop` non si sovrappongono.
- **Maschere `*_emis.png`**: vanno disegnate in modo additivo, con lo stesso `z` e la stessa posizione del loro piano. A piena intensità danno l'alone dei neon; per lo sfarfallio basta modularne l'intensità.
- **Le pozze del pavimento**: `game/src/fx/wind_day.gd` le ricava da `floor.png` (pixel opachi con g ≥ r + 4 e b > g + 6). Chi ritocca il pavimento deve lasciare identica questa maschera: `patina_floor.py` lo controlla.

## La storia

Fino al 7 novembre 2026 questa cartella faceva tutto il livello: una scena 3D in metri (`layout.py`, `render_scenes.py`), dipinta in cel shading (`street.py`, `near_fg.py`), con il cielo e i palazzi ricolorati da Warped City di Luis Zuno (CC0, `warped.py`) e una pozzanghera elettrificata dipinta sul pavimento (`props.build_cable`). Sono stati tolti quando gli sfondi nuovi sono entrati nel gioco; restano nella storia di git. Le fonti verificate allora sono in `FONTI.md`.
