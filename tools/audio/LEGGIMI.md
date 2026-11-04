# Audio: effetti sonori, musica, verifiche

Gli script usano il Python del laboratorio, sempre con `-I`:

```
PY=~/ctrlaltrevenge-lab/venv/Scripts/python.exe
```

Gli strumenti esterni stanno in `~/ctrlaltrevenge-lab/tools/`:
- `ffmpeg/bin/ffmpeg.exe`: build essentials di gyan.dev;
- `pymusiclooper/bin/pymusiclooper.exe`: installato con `uv tool install pymusiclooper==3.6.0`.

La musica non entra mai nel repo: sta in `~/ctrlaltrevenge-lab/music/`.

## Effetti sonori

```
$PY -I tools/audio/sfx_gen.py --sheet      # genera in tools/audio/out/sfx/, controlla, disegna le tavole
$PY -I tools/audio/sfx_gen.py --install    # poi copia in game/assets/sfx/
```

Cosa produce:
- 25 WAV mono, 16 bit, 44,1 kHz, con picco a -1 dBFS, senza componente continua e con dissolvenze di pochi ms;
- i `.wav.import`, per importarli in PCM e senza loop;
- `mix.json`, con il guadagno di ogni suono. Lo legge l'autoload `Sfx`.

Ogni suono ha un seme fisso: rigenerare dà gli stessi file, bit per bit.

Le tavole `out/sfx/tavola_sfx.png` e `tavola_sfx_zoom.png` mostrano forme d'onda e spettrogrammi. Lo script si ferma se un suono ha picco, componente continua, estremi, coda o durata fuori norma, o se due suoni sono troppo simili.

## Brani di Suno

Si scaricano in `~/ctrlaltrevenge-lab/suno/` (vedi `PROMPT.md` lì), poi:

```
$PY -I tools/audio/prepare_music.py stage1 --main ~/ctrlaltrevenge-lab/suno/sotto_la_linea.wav \
    --bpm-hint 124 --title "Sotto la Linea" --source "https://suno.com/song/..." --license "Suno Pro"
$PY -I tools/audio/prepare_music.py stage1 --main mix.wav --layer arena=stem_batteria.wav \
    --subtract-layers --bpm-hint 124 ...       # la base è il mix meno lo stem, l'arena lo rimette
$PY -I tools/audio/prepare_music.py clear --main sotto_la_linea.wav --jingle 151.2 154.6
```

Passi dello script:
1. PyMusicLooper propone i punti di loop.
2. La fine si rifinisce per correlazione, perché PyMusicLooper può sbagliare di centinaia di campioni.
3. Il BPM si ricava dalla lunghezza del loop.
4. Un guadagno lineare porta il loop a -16 LUFS, con true peak ≤ -1 dBTP.
5. Il file si taglia alla fine del loop e si codifica in OGG q6 con ffmpeg.
6. Il file decodificato si ricontrolla e `music.json` si aggiorna.

Se il giunto non convince, si può imporre il loop con `--loop INIZIO FINE` (in secondi).

La musica segnaposto CC0 di oggi si ricrea con `make_placeholder_music.py`. Usa `vgm_stems.py`, che rende i VGM con libgme e ne ricava gli strati, e `vgm_info.py`, che legge loop e note dei VGM.

## Verifiche in Godot

Dopo l'integrazione le prove girano anche direttamente sul progetto del gioco (vedi `game/tests/README.md`):

```
REQUIRE_DONE=1 tools/run_godot.sh 120 --headless -s "$(cygpath -w "$PWD/tools/audio/godot_tests/test_audio.gd")"
```

Per provare script audio nuovi senza toccare `game/` resta il progetto di prova:

```
$PY -I tools/audio/make_test_project.py --src game/src/audio --sfx game/assets/sfx
tools/audio/out/test_project/tools/run_godot.sh 180 --headless --import
REQUIRE_DONE=1 tools/audio/out/test_project/tools/run_godot.sh 240 --headless -s res://tests/test_audio.gd
tools/audio/out/test_project/tools/run_godot.sh 240 --write-movie "C:/percorso/assoluto/f.png" --fixed-fps 60 --quit-after 1500
$PY -I tools/audio/analyze_capture.py C:/percorso/assoluto/f.wav <output .out della registrazione> --png tavola.png
```

- **`test_audio.gd`** (50 prove) controlla:
  - la ricerca della musica nelle tre cartelle;
  - la lettura di `music.json` e il caso "nessuna musica";
  - i brani in OGG e in WAV, con i loro loop;
  - i bus, la cache, i guadagni e il pan di `Sfx`.
- **`analyze_capture.py`** confronta la registrazione di Movie Maker con gli OGG, interpolati come fa Godot, e controlla:
  - le dissolvenze, il duck e le rampe dello strato;
  - il salto esatto al giunto del loop e l'assenza di click;
  - il jingle seguito dal silenzio, e il pan degli effetti.
