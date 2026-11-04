# CTRL+ALT REVENGE!

**Picchia duro a scorrimento.** È un beat'em-up cyberpunk in pixel art 16-bit, in sviluppo con Godot 4.7.

2087. Le megacorporazioni si sono mangiate la città. GIG, ex ingegnere con un braccio cibernetico, ha perso tutto e scende in strada a riprenderselo.

## Stato

È in corso un rifacimento da zero sul branch `rewrite-godot`.

Il primo obiettivo è uno slice verticale giocabile del livello 1, "Sotto la Linea", con:
- GIG;
- due tipi di Thug;
- combattimento;
- un brano musicale.

Lo slice è giocabile dal titolo alla fine della demo: strada notturna sotto la ferrovia, un'ondata con il punk, bidone con la mela, cavo dell'alta tensione da saltare, arena con punk e bruto, "ZONA LIBERATA". Grafica, effetti sonori e interfaccia sono quelli definitivi dello slice; la musica per ora è segnaposto.

La specifica è in [`docs/specifica-slice.md`](docs/specifica-slice.md).

La versione precedente, in Python/Pygame con i port Game Boy Color e PICO-8, è archiviata nel branch [`legacy-pygame`](https://github.com/luigismith/ctrl-alt-revenge/tree/legacy-pygame).

## Come provarlo

Serve [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/), nella versione standard e non .NET. Dalla cartella del repository:

```
godot --headless --path game --import
godot --path game
```

Il primo comando importa gli asset (serve la prima volta e dopo ogni aggiornamento della grafica o dei suoni), il secondo apre il gioco in una finestra 1152×648, cioè tre volte la risoluzione interna 384×216.

Sul PC di sviluppo, con il laboratorio in `%USERPROFILE%\ctrlaltrevenge-lab\`, basta un doppio clic su `Gioca.bat` in quella cartella: importa il progetto e avvia il gioco.

Argomenti utili, da scrivere dopo `--`:

| Argomento | Effetto |
|---|---|
| `--autostart` | salta il titolo e parte dal livello |
| `--replay res://tests/replays/demo.json` | riproduce la dimostrazione di circa 69 s (GIG gioca da solo) |
| `--start-x 1150` | fa partire GIG da quel punto del livello (qui: prima del cavo) |
| `--debug-boxes` | mostra hitbox e hurtbox, come F1 |
| `--no-lights` | parte con le luci dinamiche spente, come F5 |

Per esempio `godot --path game -- --autostart`. Gli altri argomenti e i test sono descritti in [`game/tests/README.md`](game/tests/README.md).

La musica non è in questo repository (vedi sotto). Il gioco la cerca in `game/assets_private/music/`, in `music/` accanto all'eseguibile e, solo durante lo sviluppo (non nelle build esportate), in `%USERPROFILE%\ctrlaltrevenge-lab\music\`; senza musica funziona lo stesso, solo che è muto.

## Comandi

| Azione | Tastiera | Gamepad |
|---|---|---|
| Muoversi (anche in profondità) | frecce oppure W A S D | croce direzionale oppure levetta sinistra |
| Correre | due tocchi rapidi verso destra o sinistra | due tocchi rapidi verso destra o sinistra |
| Attacco | J oppure Z | X oppure Y (Quadrato o Triangolo) |
| Salto | K oppure X | A oppure B (Croce o Cerchio) |
| Pausa | Esc oppure Invio | Start (Options) |
| Confermare nei menu | Invio, Spazio, J oppure Z | A oppure Start |
| Tornare indietro nei menu | Esc oppure Backspace | B |

Le mosse:
- **Combo**: premendo attacco, jab, jab, gancio cyber e calcio finale si concatenano solo se il colpo precedente va a segno; a vuoto GIG ripete il primo jab.
- **Calcio volante**: attacco durante il salto.
- **Presa**: si cammina contro un nemico vicino, nella sua stessa corsia. Dalla presa, attacco dà una ginocchiata (al massimo due); il terzo attacco, oppure attacco più la direzione opposta, lo proietta. Il corpo proiettato atterra gli altri nemici.
- **Ostacolo**: il cavo nella pozzanghera si salta; toccarlo fa 10 di danno e atterra.

Avviando il gioco con Godot, come sopra, è una build di debug e funzionano anche F1 (hitbox e hurtbox), F2 (rallentatore), F3 (fermo immagine), F4 (avanza di un fotogramma durante il fermo immagine) e F5 (accende e spegne le luci dinamiche sui personaggi). Nelle build esportate per i giocatori questi tasti non fanno nulla.

## Struttura

| Cartella | Contenuto |
|---|---|
| `game/` | Progetto Godot: scene, script, dati, asset, test e replay |
| `tools/` | Pipeline per sprite e sfondi (dal 3D alla pixel art), effetti visivi, interfaccia e font, effetti sonori e musica, controlli sugli asset |
| `docs/` | Specifiche e riferimenti estetici |

## Licenze

- **Codice** (GDScript, Python, shader, configurazione): [MIT](LICENSE).
- **Asset originali** (grafica, animazioni, sfondi, effetti sonori, livelli, storia e personaggi): tutti i diritti riservati, compreso il divieto di usarli per addestrare sistemi di intelligenza artificiale. Vedi [`LICENSES/LicenseRef-CAR-Assets.txt`](LICENSES/LicenseRef-CAR-Assets.txt). La licenza MIT non si applica a questi file.
- **Script per Blender** in `tools/blender/`: GPL-3.0-or-later.
- **Materiale di terze parti**: [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

[`REUSE.toml`](REUSE.toml) dice quale licenza vale per ogni file.

**Musica.** La colonna sonora è generata con Suno e non viene pubblicata in questo repository: le build la includono, il codice sorgente no.

**Contributi.** Leggi [`CONTRIBUTING.md`](CONTRIBUTING.md).
