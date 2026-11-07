# Interfaccia

Tutto è generato da `tools/fxui/make_ui.py`, alla risoluzione del gioco (480×270) e senza ingrandimenti. `ui.json` elenca ogni elemento: file, dimensioni, margini 9-slice, fotogrammi e note. In più contiene i font da usare, i colori dei testi e la disposizione dell'HUD del mockup (`hud_layout`).

La cartella `portraits/` non nasce da qui: i ritratti 32×32 li fa la pipeline dei personaggi.

## Primi piani delle scene (`closeups/`)

I primi piani 96×96 dei filmati nel motore: GIG prima del riavvio (`gig_spento_sx`), il messo (`messo_dx`) e il rider (`rider_dx`). Neanche questi nascono da `make_ui.py`:

- **Il volto** in stile murales è generato con **ChatGPT di OpenAI**, ridipingendo il nostro render 3D del personaggio (decisione 68 della storia). Il JSON accanto lo dice nel campo `fonte`.
- **La riduzione in pixel art** la fa `tools/sprites/closeup_ai.py`: allinea il volto al render, ne fa la tavolozza e la aggancia ai colori del personaggio. Le impostazioni stanno nella voce `ai` del primo piano, in `tools/sprites/chars/<personaggio>.json`.
- **Palpebre chiuse (`_blink`) e bocca aperta (`_talk`)** le disegna lo stesso script sui pixel della base: niente di animato viene dall'AI.
- **Gli originali e i prompt** non sono nel repository.

Ogni JSON dà i riquadri di occhi (`eyes`) e bocca (`mouth`) e i loro colori (`lid`, `mouth_dark`).

## Elementi

| Chiave in `ui.json` | File | Misure | Note |
|---|---|---|---|
| `logo` | `title_logo.png` | 248×89 | "CTRL+ALT REVENGE!" come sulla locandina: crema, bordo rosso scuro, estrusione, ombra |
| `subtitle` | `title_subtitle.png` | 223×13 | "PICCHIA DURO A SCORRIMENTO" arancio, sotto il logo |
| `stage_card_1` | `stage_card_1.png` | 293×27 | "1 · SOTTO LA LINEA" |
| `msg_zone_clear` | `msg_zone_clear.png` | 276×31 | "ZONA LIBERATA" |
| `msg_pause` | `msg_pause.png` | 115×31 | "PAUSA" |
| `msg_continue` | `msg_continue.png` | 197×31 | "CONTINUA?" |
| `msg_game_over` | `msg_game_over.png` | 202×31 | "GAME OVER" (facoltativo) |
| `msg_demo_end` | `msg_demo_end.png` | 307×31 | "FINE DELLA DEMO" |
| `big_digits` | `big_digits.png` | 10 fotogrammi da 23×31 | cifre 0-9 in oro nello stile delle scritte `msg_*`; il fotogramma k è la cifra k (conto alla rovescia di CONTINUA?, a 1x) |
| `go_arrow` | `go_arrow.png` | 3 fotogrammi da 56×24 | "VAI ▶": 0 acceso, 1 triangolo avanti di 3 px, 2 spento; 8 tick ciascuno, in ciclo |
| `portrait_frame` | `portrait_frame.png` | 34×34 | cornice di GIG, il ritratto va in (1, 1) |
| `portrait_frame_enemy` | `portrait_frame_enemy.png` | 34×34 | cornice rossa per i nemici (facoltativa) |
| `portrait_back` | `portrait_back.png` | 34×34 | fondo "schermo" da mettere dietro al ritratto |
| `bar_back`, `bar_ghost`, `bar_fill` | `bar_*.png` | 104×6 | barra di GIG: fondo vuoto, scia del danno, vita (giallo-ocra) |
| `bar_frame` | `bar_frame.png` | 108×10 | cornice della barra di GIG, 9-slice 2 px |
| `bar_back_enemy`, `bar_ghost_enemy`, `bar_fill_enemy` | `bar_*_enemy.png` | 104×4 | barra del nemico: fondo, scia, vita (rossa) |
| `bar_frame_enemy` | `bar_frame_enemy.png` | 108×8 | cornice della barra del nemico |

## Come si compongono

- **Ritratto**, in quest'ordine:
  1. `portrait_back` in (x, y);
  2. il ritratto 32×32 in (x + 1, y + 1);
  3. `portrait_frame` in (x, y).
- **Barra della vita** con l'area colorata in (x, y), larga w e alta h:
  1. `bar_back`, regione (0, 0, w, h);
  2. `bar_ghost`, regione (0, 0, larghezza della scia, h);
  3. `bar_fill`, regione (0, 0, larghezza della vita, h);
  4. `bar_frame` in (x − 2, y − 2).

  Le strisce sono uniformi in orizzontale: si ritaglia la parte sinistra, oppure si stira in larghezza. Le cornici sono 9-slice con margini di 2 px, se servono altre lunghezze.
- **Testi variabili** (nome, vite, punteggio, nome del nemico, menu): font `CAR Pixel Bold` a 12 px, con ombra di 1 px color `shadow`. I colori sono in `ui.json` → `colors`.
- **Scritte grandi e logo**: si disegnano a 1x, centrati, su coordinate intere. Bordo e ombra sono già nell'immagine.

## Verifica

- `tools/fxui/out/check/hud_mockup_1x.png` e `_3x.png`: HUD in scena, con fondale e personaggi di prova.
- `tools/fxui/out/check/hud_plain_*.png`: HUD su fondo scuro.
- `tools/fxui/out/check/title_mockup_*.png`: titolo di prova.
- `tools/fxui/out/check/messages_1x.png`: tutte le scritte sopra il gioco.
- `python -I tools/fxui/godot_check.py hud`: ricostruisce l'HUD in Godot 4.7.2 con questi file e `hud_layout`, e lo confronta col mockup. Risultato: 0 pixel diversi.

Licenza: asset originali, `LicenseRef-CAR-Assets`.
