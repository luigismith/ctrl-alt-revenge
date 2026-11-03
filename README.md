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

La specifica è in [`docs/specifica-slice.md`](docs/specifica-slice.md).

La versione precedente, in Python/Pygame con i port Game Boy Color e PICO-8, è archiviata nel branch [`legacy-pygame`](https://github.com/luigismith/ctrl-alt-revenge/tree/legacy-pygame).

## Come provarlo

Serve [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/), nella versione standard e non .NET. Dalla cartella del repository:

```
godot --headless --path game --import
godot --path game
```

La musica non è in questo repository (vedi sotto). Senza musica il gioco funziona lo stesso, solo che è muto.

## Struttura

| Cartella | Contenuto |
|---|---|
| `game/` | Progetto Godot: scene, script, dati, asset |
| `tools/` | Pipeline per sprite e sfondi (dal 3D alla pixel art), effetti sonori, controlli sugli asset |
| `docs/` | Specifiche e riferimenti estetici |

## Licenze

- **Codice** (GDScript, Python, shader, configurazione): [MIT](LICENSE).
- **Asset originali** (grafica, animazioni, sfondi, effetti sonori, livelli, storia e personaggi): tutti i diritti riservati, compreso il divieto di usarli per addestrare sistemi di intelligenza artificiale. Vedi [`LICENSES/LicenseRef-CAR-Assets.txt`](LICENSES/LicenseRef-CAR-Assets.txt). La licenza MIT non si applica a questi file.
- **Script per Blender** in `tools/blender/`: GPL-3.0-or-later.
- **Materiale di terze parti**: [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

[`REUSE.toml`](REUSE.toml) dice quale licenza vale per ogni file.

**Musica.** La colonna sonora è generata con Suno e non viene pubblicata in questo repository: le build la includono, il codice sorgente no.

**Contributi.** Leggi [`CONTRIBUTING.md`](CONTRIBUTING.md).
