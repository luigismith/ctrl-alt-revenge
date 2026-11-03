# Specifica dello slice verticale

Versione 1 · 3 novembre 2026. È il contratto comune tra chi produce grafica, suoni e codice dello slice. Se qualcosa qui è sbagliato o impossibile, si corregge prima questo file e poi il resto.

## 1. Obiettivo e decisioni

Uno slice giocabile del livello 1, "Sotto la Linea": un tratto di strada notturna sotto la ferrovia sopraelevata e un'arena finale. Contiene GIG, due tipi di Thug (il punk e il bruto), combattimento con peso, interfaccia, effetti sonori e un brano in loop.

Decisioni di Luigi del 3 novembre 2026:

- **Approccio C, misto, a costo zero**: tutta la grafica nasce dalla pipeline 3D → pixel e dai pack CC0 ammessi, senza ritocchi umani.
- **GIG** ha l'aspetto della locandina (`docs/riferimenti-estetica/locandina-pixelart-chatgpt-2026-04-09.png`):
  - codino e barba grigi;
  - camicia da lavoro ocra con le maniche arrotolate, sopra un cappuccio grigio;
  - fasce da boxe blu, pantaloni oliva, stivali marroni.

  In più ha il braccio sinistro cibernetico (metallo scuro con anelli cyan luminosi) e un occhio cyan che brilla: quello rivolto alla telecamera.
- **Genere**: picchiaduro a scorrimento con profondità, nello stile di Streets of Rage, con elementi platform leggeri: salto sopra un ostacolo pericoloso.

Scelte tecniche già fissate:

- risoluzione 384×216;
- GIG specchiato quando guarda a sinistra;
- prima Windows;
- un solo giocatore;
- musica fuori dal repo.

## 2. Motore e progetto

- Godot 4.7.2 standard con GDScript tipizzato, senza plugin. Il progetto è in `game/`.
- Le impostazioni del progetto sono scritte esplicitamente in `game/project.godot`:
  - 384×216, stretch `viewport`, aspect `keep`, scale `integer`, finestra 1152×648;
  - filtro Nearest; snap delle trasformazioni 2D attivo, dei vertici spento;
  - renderer Mobile su Direct3D 12.
- Fisica a 60 tick al secondo, interpolazione spenta. Tutto il gameplay gira in `_physics_process`, un tick alla volta, in modo deterministico: niente `randf()` senza seme e niente tempi reali.
- L'hitstop congela i singoli attori. Non usare mai `get_tree().paused` (ferma anche la musica) né `Engine.time_scale`.
- Le azioni di input si creano da codice in `Controls` (autoload). Non assegnare azioni al tasto Shift (bug #122554 di Godot 4.7.2).
- Bug noti da evitare:
  - AnimationTree con macchine a stati annidate: non si usa;
  - limiti di Camera2D: la telecamera calcola i limiti da sé, con posizioni intere;
  - Vulkan sulla Radeon 780M: si resta su Direct3D 12.
- Lingua del gioco: italiano. Identificatori del codice in inglese, commenti in italiano.

## 3. Scala del mondo e pseudo-profondità

- **Densità**: 48 px per metro sul piano del pavimento, pari al blocco 4 della pipeline v6. GIG in guardia misura circa 88-92 px dai piedi alla cima del codino.
- **Coordinate di ogni entità**:
  - `x` orizzontale, in px del mondo;
  - `y` è la linea dei piedi sullo schermo, cioè la profondità;
  - `h` è l'altezza dal suolo (≥ 0, verso l'alto).

  Lo sprite si disegna in (x, y − h), l'ombra in (x, y).
- **Fascia calpestabile**: y da 150 a 208.
- **Ordine di disegno**: per `y` crescente.
- **Tolleranza di profondità per i colpi**: ±10 px per gli attacchi di GIG, ±8 px per quelli dei nemici.
- **Direzione**: tutti gli sprite sono disegnati rivolti a destra. Verso sinistra si specchiano, insieme a hitbox, hurtbox e offset.

## 4. Formato degli sprite

È il contratto tra grafica e codice. Ogni personaggio ha una cartella `game/assets/sprites/<id>/` con due file:

- `<id>.png`: atlante RGBA con i fotogrammi impacchettati, senza spazio sprecato oltre 1 px di margine.
- `<id>.json`, con questa struttura:

```json
{
  "id": "gig",
  "format": 1,
  "image": "gig.png",
  "pixels_per_meter": 48,
  "animations": {
    "jab1": {
      "loop": false,
      "frames": [
        {"rect": [0, 0, 70, 96], "anchor": [30, 93], "ticks": 3,
         "hurt": [[-11, -86, 22, 86]], "hit": [], "events": ["sfx:whoosh_light"], "tags": [], "dx": 0},
        {"rect": [70, 0, 88, 96], "anchor": [30, 93], "ticks": 2,
         "hurt": [[-11, -86, 22, 86]], "hit": [[14, -66, 30, 12]], "events": [], "tags": ["active"], "dx": 1}
      ]
    }
  }
}
```

**Campi di ogni fotogramma:**
- `rect`: [x, y, w, h] nell'atlante.
- `anchor`: il punto a terra fra i piedi, in pixel dentro `rect`.
- `ticks`: durata a 60 tick al secondo.
- `hurt` e `hit`: box [x, y, w, h] relativi all'ancora, con il personaggio rivolto a destra; y negativo vuol dire sopra il suolo. `hit` è vuoto quando il colpo non è attivo.
- `events`: stringhe che scattano quando il fotogramma inizia:
  - `sfx:<nome>`;
  - `fx:<nome>`;
  - `glint` (lampo che annuncia un attacco caricato);
  - `step` (passo).
- `tags`:
  - `active`: hitbox attiva;
  - `cancel`: finestra in cui, se il colpo è andato a segno, si concatena la mossa successiva;
  - `invuln`;
  - `armor`: non si interrompe con i colpi leggeri;
  - `hold`: fotogramma tenuto dal codice, per esempio a terra;
  - `air`.
- `dx`: spostamento in avanti in px quando il fotogramma inizia (root motion), opzionale.

**Mosse a coppie (presa, ginocchiate, proiezione).** I fotogrammi di GIG `grab_hold`, `knee` e `throw` hanno in più `"victim": [dx, dy, "<animazione>", <indice>]`. Significa: ancora della vittima = ancora di GIG + (dx, dy), con il personaggio rivolto a destra, e la vittima mostra quel fotogramma della sua animazione. Gli offset vengono da `author.py` e vanno ricalcolati per ogni corpo, punk e bruto.

**Animazioni richieste**, con nomi esatti:

| Personaggio | Animazioni |
|---|---|
| GIG (`gig`) | `idle` (guardia, loop), `walk`, `run`, `jump_rise`, `jump_fall`, `land`, `jab1`, `jab2`, `hook`, `kick` (finale), `air_kick`, `grab_hold`, `knee`, `throw`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down` (a terra, `hold`), `getup` |
| Punk (`thug_punk`) | `idle`, `walk`, `jab`, `haymaker`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down`, `getup`, `grabbed`, `kneed`, `thrown` |
| Bruto (`thug_bruiser`) | `idle`, `walk`, `punch`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down`, `getup`, `grabbed`, `kneed`, `thrown` |

La morte usa `knock_down` più un lampeggio gestito dal codice.

**Ritratti per l'interfaccia**: `game/assets/ui/portraits/<id>.png`, 32×32, dal render del volto.

## 5. Tempi e valori di combattimento

Tick a 60 Hz. Sono valori di partenza: si tarano con le prove di Luigi. Stanno in `game/data/attacks/*.tres` (risorse `AttackData`), non nel codice.

| Mossa | Avvio | Attivo | Recupero | Danno | Hitstop attaccante/vittima | Effetto |
|---|---|---|---|---|---|---|
| GIG `jab1` | 3 | 2 | 9 | 4 | 5/7 | stordimento 14 |
| GIG `jab2` | 3 | 2 | 9 | 4 | 5/7 | stordimento 14 |
| GIG `hook` (gancio cyber) | 6 | 3 | 12 | 7 | 7/9 | stordimento 18 |
| GIG `kick` (finale) | 10 | 3 | 20 | 12 | 9/12 | atterra; lancio 170 px/s in avanti e 220 px/s in alto, gravità 900 px/s² |
| GIG `air_kick` | 4 | 8 | 6 all'atterraggio | 8 | 6/8 | atterra |
| GIG `knee` (in presa) | 4 | 3 | 10 | 6 | 6/8 | — |
| GIG `throw` | 8 | — | 14 | 14, più 8 a chi viene colpito dal corpo | 11/11 | proiezione |
| Punk `jab` | 18 | 4 | 18 | 5 | 5/7 | stordimento 14 |
| Punk `haymaker` | 33 (lampo al tick 20) | 4 | 28 | 10 | 8/10 | atterra |
| Bruto `punch` | 26, con `armor` | 5 | 26 | 12 | 8/10 | atterra |

**Regole della combo:**
- Il tasto attacco concatena `jab1 → jab2 → hook → kick` solo se il colpo precedente è andato a segno; a vuoto ripete `jab1`.
- Buffer di input: 8 tick.
- Massimo 3 punti di giocoleria.
- Il KO finale di ogni ondata congela tutto per 26 tick, poi 0,4 s al 35% della velocità.

**Reazioni ai colpi:**
- lampo bianco sulla vittima per 2 tick;
- lo sprite trema, la hurtbox no;
- tremolio dello schermo solo per colpi pesanti, KO e proiezioni: massimo 5 px, solo traslazione, decadimento 1,5 al secondo.

**Valori dei personaggi:**
- **Vita**: GIG 120, punk 48, bruto 110. GIG ha 3 vite.
- **Invulnerabilità dopo il rialzo**: GIG 60 tick, nemici 20.
- **Movimento di GIG**:
  - camminata 1,5 px per tick in orizzontale e 1 px per tick in profondità;
  - corsa con doppio tocco della direzione entro 12 tick, a 3 px per tick;
  - salto con velocità iniziale 4,4 px per tick e gravità 0,26 px per tick².
- **Presa automatica**: scatta quando GIG cammina contro un nemico entro 18 px in orizzontale e 4 px in profondità, se il nemico non sta attaccando, non è in aria e non è a terra.
  - Dalla presa: attacco = ginocchiata (al massimo 2); il terzo attacco, oppure attacco più la direzione opposta, = proiezione.
  - Dopo 90 tick il nemico si libera.
- **Punteggio**:
  - per colpo: jab 10, gancio 20, calcio 50, ginocchiata 30, proiezione 100;
  - per KO: punk 500, bruto 1000.

**Intelligenza dei nemici:**
- Un `AttackDirector` (autoload) dà il permesso di attaccare a un solo nemico alla volta, con almeno 0,35 s fra due attacchi nemici qualsiasi e 1,2-2,0 s fra due attacchi dello stesso nemico.
- Chi aspetta resta a 60-90 px da GIG, fuori dalla sua corsia, e si sposta di lato.
- Il gancio caricato del punk si annuncia con il lampo (`glint`).
- Il bruto è lento e pesante: non si ferma per i jab durante l'avvio del pugno.

## 6. Livello "Sotto la Linea"

Mondo largo 1920 px, cioè 5 schermate. La telecamera segue GIG su posizioni intere, con zona morta di ±24 px e velocità massima di 4 px per tick; l'altezza della telecamera è fissa.

| x | Contenuto |
|---|---|
| 0-384 | Partenza; cartello "1 · SOTTO LA LINEA" |
| 576-960 | Ondata 1, con la telecamera bloccata: un punk |
| 1050 | Bidone dell'immondizia da rompere; dentro c'è una mela (+30 di vita) |
| 1230-1270 | Ostacolo da saltare: cavo dell'alta tensione strappato in una pozzanghera; scintille animate, 10 di danno e atterramento |
| 1536-1920 | Arena sotto i piloni della ferrovia, con la telecamera bloccata: un punk e un bruto, il bruto entra 3 s dopo |
| fine | "ZONA LIBERATA", poi la schermata di fine demo |

Fra un'ondata e l'altra compare la freccia "VAI ▶".

**Atmosfera:**
- notte, pioggia leggera, neon rossi, arancioni e un solo cyan;
- asfalto viola bagnato, palazzi blu-viola;
- la ferrovia sopraelevata in primo piano in alto.

**Sfondi** in `game/assets/env/sotto_la_linea/`: un PNG per piano più `layers.json`:

```json
{
  "format": 1,
  "level_width": 1920,
  "floor_band": [150, 208],
  "layers": [
    {"name": "sky", "image": "sky.png", "scroll": 0.0, "y": 0, "repeat_x": 0, "z": -100},
    {"name": "far", "image": "far.png", "scroll": 0.125, "y": 0, "repeat_x": 768, "z": -90, "emissive": "far_emis.png"},
    {"name": "floor", "image": "floor.png", "scroll": 1.0, "y": 140, "repeat_x": 768, "z": -10},
    {"name": "fg", "image": "fg.png", "scroll": 1.25, "y": 0, "repeat_x": 768, "z": 100}
  ]
}
```

- `scroll` è il fattore di parallasse, `y` lo scostamento verticale in px dello schermo.
- `repeat_x` è il periodo di ripetizione in px; 0 vuol dire che il piano non si ripete.
- `emissive` (opzionale) è una maschera disegnata in modalità additiva, per bagliori e sfarfallio dei neon.
- I piani a fattore 1,0 coprono tutti i 1920 px. Quelli più lenti coprono almeno `384 + 1536 × scroll` px, oppure si ripetono.

**Oggetti di scena**, in `game/assets/props/`: bidone (intero, colpito, rotto), mela, cavo con scintille (4-6 fotogrammi). Ognuno ha un JSON con lo stesso formato degli sprite.

## 7. Effetti visivi, interfaccia, suoni

**Effetti** in `game/assets/fx/`, ognuno con un PNG a strisce più `fx.json`:

```json
{"hit_spark_light": {"image": "hit_spark_light.png", "frame": [24, 24], "count": 4, "ticks": 2, "anchor": [12, 12]}}
```

Servono `hit_spark_light`, `hit_spark_heavy`, `dust_land`, `dust_skid`, `glint`, `cyber_spark` (per il gancio cyber) e `ombra` (ellisse).

**Interfaccia** in `game/assets/ui/`:
- il logo "CTRL+ALT REVENGE!" con riempimento crema e bordo rosso scuro, come la locandina;
- la scritta "PICCHIA DURO A SCORRIMENTO";
- le barre della vita, le cornici dei ritratti, la freccia "VAI ▶";
- un font pixel con le lettere accentate italiane: un font OFL o CC0 con il suo file di licenza, oppure un font bitmap fatto da noi.

**HUD** in stile Streets of Rage 2:
- in alto a sinistra: ritratto, nome, barra della vita e vite di GIG;
- sotto, la barra del nemico colpito per ultimo, con il suo nome ("PUNK", "BRUTO");
- in alto a destra, il punteggio a 6 cifre.

**Suoni** in `game/assets/sfx/<nome>.wav`: mono, 16 bit, 44,1 kHz, nostri (generati da script) o CC0 con licenza registrata. Nomi:
- colpi e movimenti: `whoosh_light`, `whoosh_heavy`, `hit_light`, `hit_medium`, `hit_heavy`, `hit_kick`, `knee`, `grab`, `throw`, `body_fall`, `body_thud`, `step_a`, `step_b`, `jump`, `land`, `glint`;
- scena: `zap` (cavo), `bin_hit`, `bin_break`, `pickup`, `ko`;
- interfaccia: `ui_move`, `ui_confirm`, `ui_pause`, `go_arrow`.

**Musica**: mai nel repo (vedi `LICENSES/` e README). L'autoload `Music` cerca i file in quest'ordine:
1. `res://assets_private/music/`;
2. la cartella `music/` accanto all'eseguibile;
3. `%USERPROFILE%/ctrlaltrevenge-lab/music/`.

Un file `music.json` in quella cartella descrive i brani: id, file, inizio e fine del loop in secondi, BPM, battiti per battuta, strati. Senza musica il gioco resta muto e non dà errori. Gli id dei brani sono `title`, `stage1` (con lo strato `stage1_arena` facoltativo) e `clear`.

## 8. Struttura del repo

```
game/                 progetto Godot
  project.godot
  scenes/             scene .tscn (minime: i nodi si costruiscono soprattutto da codice)
  src/core/           Game, Controls, flusso delle schermate
  src/combat/         Fighter, FrameAnim, CombatSystem, AttackDirector, AttackData
  src/actors/         GIG, Thug (IA)
  src/stage/          livello, telecamera, parallasse, ondate, oggetti di scena
  src/ui/             HUD, titolo, pausa, game over, fine demo
  src/audio/          Music, Sfx
  src/debug/          sovrapposizione hitbox, rallentatore, avanzamento a fotogramma, replay
  data/attacks/       AttackData .tres
  assets/             sprites/, env/, props/, fx/, ui/, sfx/, fonts/, third_party/
  tests/              run_tests.gd e replays/*.json
tools/
  blender/            script bpy della pipeline (GPL-3.0-or-later)
  sprites/            script Python della pipeline sprite (MIT)
  env/                script Python della pipeline sfondi (MIT)
  audio/              generazione degli effetti sonori e preparazione della musica
  guard_assets.py     blocca audio e file pesanti non ammessi
docs/                 questa specifica e i riferimenti estetici
```

**Strumenti e sorgenti fuori dal repo**, in `%USERPROFILE%\ctrlaltrevenge-lab\`, che in Python si legge con `os.environ["USERPROFILE"]`:
- `tools\godot-4.7.2\`: usare `Godot_v4.7.2-stable_win64_console.exe` per le esecuzioni da riga di comando;
- `tools\blender-4.5.15\blender.exe`;
- `sources\chars`: Quaternius UBC, UAL1, UAL2, Warped City;
- `sources\anim`: CMU, Mesh2Motion, Rokoko, e in `spike-out` i dump JSON di Mesh2Motion e le pose di `author.py`;
- `sources\env`: kit Quaternius e Kenney;
- `ricerca-2026-11-03\prove\`: gli script delle prove (`spike2-chars`, `spike-anim`, `spike-env`) da cui partire.

## 9. Licenze dei file

- `REUSE.toml` assegna la licenza a ogni percorso.
- **Ogni pack di terze parti** va in `game/assets/third_party/<pack>/` con questi file:
  - `SOURCE.md`: URL, nome e dimensione del file, sha256, licenza, credito, data;
  - una tabella in `REUSE.toml`;
  - una riga in `THIRD-PARTY-NOTICES.md`;
  - il testo della licenza in `LICENSES/`, per esempio `CC0-1.0.txt`.
- **Ammessi nel repo pubblico**: CC0 e CC-BY (con credito), font OFL (con OFL.txt).
- **Mai nel repo pubblico**:
  - musica Suno;
  - Mixamo, Reallusion, CraftPix, Oonquil, Shapeforms, Sonniss;
  - i file grezzi del pack Rokoko.
- **Script bpy**: vanno in `tools/blender/` con l'intestazione GPL. Il primo che si aggiunge porta con sé `LICENSES/GPL-3.0-or-later.txt`.
- **Codice nuovo**: MIT. Gli asset originali (sprite, sfondi, effetti, interfaccia, suoni, livelli) sono `LicenseRef-CAR-Assets`.

## 10. Verifica

- **Esecuzioni da riga di comando**:
  - si lanciano con `tools/run_godot.sh`, che usa l'eseguibile console, un timeout e `--log-file`;
  - una prova passa solo se il codice d'uscita è 0, se il log non contiene `SCRIPT ERROR`, `Parse Error` o `ERROR:` e se termina con la riga `DONE`.
- **Test**: `godot --headless --path game -s res://tests/run_tests.gd`.
- **Replay**: file JSON con gli input tick per tick, iniettati alla fine del tick precedente. Servono a verificare combo, danni, prese e ondate.
- **Controllo visivo**: Movie Maker con `--write-movie <percorso assoluto>/f.png --fixed-fps 60 --quit-after N`, in una finestra visibile.
  - Il fotogramma k mostra lo stato dopo il tick k+1.
  - Bisogna verificare che i fotogrammi consecutivi siano diversi.
  - Le tavole di fotogrammi si guardano ingrandite.
