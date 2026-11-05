# Pipeline degli sfondi di "Sotto la Linea"

Genera i piani di parallasse in `game/assets/env/sotto_la_linea/` e gli oggetti di scena in `game/assets/props/`. Il processo è deterministico: due esecuzioni danno file identici byte per byte.

```
python -I tools/env/build_all.py             # tutto, con le verifiche in tools/env/out/verify/
python -I tools/env/build_all.py --install   # ... e copia i file finiti in game/assets
```

Serve il laboratorio in `%USERPROFILE%/ctrlaltrevenge-lab`:
- Blender 4.5 portable;
- i kit CC0 in `sources/env`;
- Warped City in `sources/chars/oga-warped-city`;
- il Python del `venv`, sempre con l'opzione `-I`.

Un giro completo dura circa 55 secondi.

## Scala

Dal 5 novembre 2026 lo schermo è 480×270 e la vista ha 60 px/m, come gli sprite dei personaggi; prima erano 384×216 e 48 px/m. Tutto è più grande del 25%:
- le misure in metri non cambiano;
- le posizioni di progetto del layout restano scritte in px a 48 px/m e `envlib.design_X()` le porta in metri, quindi sullo schermo cadono in `xs × 1,25`;
- le misure in pixel di progetto passano per `envlib.px()`, cioè `floor(p × 1,25 + 0,5)`, la stessa regola dei dati del livello nel codice del gioco: OY 150 → 188, fascia (150, 208) → (188, 260), larghezza del livello 1920 → 2400;
- le linee di 1 px e i caratteri pixel (`pixfont.py`) restano della loro misura: le insegne crescono in metri, le lettere no;
- i piani di Warped City non si ricampionano: si allungano componendo i pezzi (vedi `warped.py`).

## Come funziona

1. **`layout.py`** descrive le scene in metri: geometria (scatole, cilindri, tubi, mesh, pochi modelli dei kit) e operazioni di pittura 2D. Usa la stessa vista dei personaggi (`tools/sprites/camera.json`):
   - yaw 30, pitch 12, 60 px/m;
   - X lungo la strada, Y profondità, Z in alto;
   - sullo schermo `x = 51,96 X + 30 Y` e `y = 188 − 14,40 Y − 58,69 Z`.

   Le scene sono tre:
   - `street`: fondale e pavimento, 2400 × 270 px;
   - `near`: secondo isolato, 17,5 px/m, pitch 0, 1440 × 210 px;
   - `fg`: travata del viadotto vista dal basso, pitch −12, 2880 × 80 px (tagliato a 33 righe).
2. **`render_scenes.py`** lancia `tools/blender/env_gbuffer.py` (GPL). Lo script scrive un G-buffer senza anti-aliasing, a 4x:
   - colore base;
   - normale nello spazio telecamera;
   - classe;
   - indice dell'oggetto e materiale;
   - emissivo;
   - posizione nel mondo a 16 bit.
3. **`paint.py`** fa da "shader differito" in Python, in quest'ordine:
   1. inclinazione 1:8 (la strada diventa orizzontale) e riduzione a 1x per voto di maggioranza;
   2. motivi per materiale: intonaco, mattoni, serrande, lastre, asfalto;
   3. operazioni di pittura: insegne al neon col carattere pixel di `pixfont.py`, manifesti, graffiti, targhe, interni delle vetrine, reti con test di profondità, pozzanghere, crepe, rifiuti, coni di luce delle lampade a muro;
   4. luce: luce chiave a bande nella direzione dei personaggi, ambiente notturno, luce dei neon e riflessi sull'asfalto bagnato;
   5. palette: rampe di `materials.py`, colore più vicino in OKLab, retinatura 4x4;
   6. contorni di 1 px (`#140e1e` come i personaggi) e maschere emissive.

   Dal 4 novembre 2026 i piani `street`, `near` e `fg` sono in cel shading a 3 toni (chiave `cel` nelle loro configurazioni, valori in `paint.CEL_3TONI`), dalla prova del laboratorio `prove-cel-shading`:
   - la luce chiave ha tre toni con le stesse soglie per tutti i materiali;
   - la luce dei neon e i riflessi sul bagnato vanno a zone con il bordo netto;
   - gli aloni delle maschere emissive sono anelli netti, e dentro la cornice delle insegne l'alone è pieno;
   - sotto le lampade a muro c'è un cono di luce a due bande: il colore sale di uno o due toni dentro la sua rampa;
   - nella fascia calpestabile i riflessi sono più scuri (`wet_lane`), per non confondersi con gli stivali dei personaggi;
   - la retinatura è spenta.

   Gli oggetti di scena (`props.py`) restano con la luce sfumata.
4. **`street.py`** e **`near_fg.py`** producono i piani. `warped.py` ricolora Warped City (CC0) nei piani `sky`, `far` e `mid` e aggiunge la torre cyan, l'unico cyan del livello. La pixel art di Warped City resta della sua misura (niente ricampionamento):
   - `sky`: i pezzi a | b | a | a, tagliati a 480; sotto si ripete l'ultima riga, che è di un colore solo, fino a 270;
   - `far`: cinque copie di `buildings-bg`, una sì e una no specchiate (720 px); in fondo si ripete la riga piena fino a y 188;
   - `mid`: sette palazzi a 16 px l'uno dall'altro (960 px), con il varco fra x 90 e 328 per la torre cyan; ogni colonna ripete la sua ultima riga fino sotto il bordo dello schermo.
5. **`props.py`** produce gli oggetti di scena nel formato sprite della specifica §4:
   - `bin`: render 3D, `idle`, `hit`, `break` (l'ultimo fotogramma è `hold`);
   - `apple`;
   - `cable`: dipinto sopra il pavimento, 6 fotogrammi di scintille.
6. **`assemble.py`** scrive `layers.json`. **`compose.py`** compone le inquadrature come il gioco: piano in `floor(−scroll·cam + 0.5)`, emissivi in modo additivo. Da lì escono i mockup, la GIF di scorrimento, la tavola dei piani e i controlli.
   I mockup usano gli sprite del gioco (`game/assets/sprites`, già a 60 px/m) e gli oggetti di scena appena fatti.
7. **`install.py`** copia in `game/assets`: prima con nome `.tmp`, poi rinomina.

## Note per il codice

- **Piani** (`layers.json`): sette piani, tutti senza ripetizione (`repeat_x` 0).
  - Le larghezze sono quelle minime: 480 + 1920 × scroll, cioè `sky` 480, `far` 720, `mid` 960, `near` 1440, `backdrop` e `floor` 2400, `fg` 2880.
  - Le righe di partenza: `sky` 0, `far` 33, `mid` 18, `near` 0, `backdrop` 0, `floor` 162, `fg` 0.
  - `floor` parte da y 162 perché contiene anche la base delle cose basse davanti alle facciate. `floor` e `backdrop` non si sovrappongono.
- **Maschere `*_emis.png`**: vanno disegnate in modo additivo, con lo stesso `z` e la stessa posizione del loro piano. A piena intensità danno l'alone dei neon; per lo sfarfallio basta modularne l'intensità.
- **Riprova in Godot 4.7.2** (fatta con lo schermo 384×216, da rifare a 480×270): un progetto temporaneo in `tools/env/out/godot_test` con le stesse impostazioni di `game/project.godot`, Movie Maker, telecamera a 4 px per tick, piani in `floor(−scroll·cam + 0.5)`. I fotogrammi coincidono pixel per pixel con `compose.py` (0 pixel diversi su 3 × 40 fotogrammi: partenza, ostacolo, arena).
  - Un arrotondamento diverso, per esempio `roundi(cam·scroll)`, cambia solo il fotogramma in cui un piano lento fa il suo passo di 1 px: nessun tremolio.
- **Rettangoli degli oggetti**: convertiti da 48 a 60 px/m sui bordi, simmetrici rispetto all'ancora (per esempio −12…12 diventa −15…15).
- **Bidone** (`bin`): ancora a terra al centro, `hurt` [-15, -48, 30, 48]. Nel livello sta in (x 1313, y 200).
  - `hit`: 3 fotogrammi, `sfx:bin_hit`.
  - `break`: 4 fotogrammi, `sfx:bin_break`, l'ultimo `hold`.
- **Mela** (`apple`): `hurt` [-10, -18, 20, 18] è l'area di raccolta.
- **Primo piano** (`fg`): la travata con lampade al sodio piatte attaccate sotto e cavi poco tesi. `near_fg.py` lo taglia a 33 righe (`FG_MAX_Y`): le insegne del fondale stanno fra y 34 e 56 e si devono leggere con la telecamera ferma in partenza (x 0) e nell'ondata 1 (x 720).
- **Cavo** (`cable`): va disegnato con l'ancora in (x 1563, y 188), sotto gli attori, perché sta sul suolo.
  - Una sola pozza irregolare, fra x 1528 e 1603 e fra y 183 e 265, che in ogni riga della fascia copre la zona del danno (x 1538-1588; `props.py` lo controlla). Si raccorda col cavo che scende dal palo del fondale.
  - Acqua blu scura con riflessi azzurri, cavo scuro con il bordo chiaro. Nei fotogrammi 0 e 3 il lampo: archi bianco-azzurri di 20-30 px e la luce sull'acqua e sull'asfalto, già dipinta nell'immagine (più larga della pozza, per l'alone).
  - `hit` [-28, -8, 56, 8] è a livello del suolo: il codice lo applica a tutta la profondità della fascia quando l'attore non è in aria.
  - `sfx:zap` all'inizio del ciclo.
