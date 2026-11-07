# Voci: le battute parlate, con Qwen3-TTS in locale

Le voci si fanno sul PC, senza servizi in rete: **progetta e clona**.
1. VoiceDesign 1.7B crea da una descrizione la voce di riferimento di ogni personaggio.
2. Base 0.6B la clona su ogni battuta, con più semi fissi.
3. Whisper base ascolta ogni presa e sceglie quella con meno lettere sbagliate.

Qui c'è solo il codice. Restano fuori dal repo:
- le battute (`docs/lore/battute/<capitolo>.json`) e la regia delle voci (`docs/lore/voci/voci.json`): sono private, nel repo della storia;
- modelli, audio e pagina di scelta riempita: stanno nel laboratorio, in `%USERPROFILE%\ctrlaltrevenge-lab\tts` (o in `%CAR_LAB%\tts`, se la variabile c'è).

## Preparare il PC

Servono Python 3.13 e [uv](https://docs.astral.sh/uv/), più ffmpeg: quello del laboratorio (`tools\ffmpeg\bin`, lo mette `tools/setup/prepara_laboratorio.ps1`) o uno nel PATH. Con una scheda NVIDIA va tutto molto più svelto; sulla CPU funziona, ma lento.

In PowerShell:

```
$T = "$env:USERPROFILE\ctrlaltrevenge-lab\tts"
$env:UV_CACHE_DIR = "$T\_cache-uv"; $env:HF_HOME = "$T\_cache-hf"
uv venv --python 3.13 "$T\venv-qwen3"
$PY = "$T\venv-qwen3\Scripts\python.exe"
uv pip install --python $PY torch==2.15.0 torchaudio==2.11.1 --index-url https://download.pytorch.org/whl/cu132
uv pip install --python $PY qwen-tts==0.1.1 transformers==4.57.3 accelerate==1.12.0 soundfile==0.14.0 librosa==1.0.0 numpy==2.5.4
```

Senza scheda NVIDIA, al posto di `cu132` si usa `cpu`.

I modelli, una volta sola (circa 7 GB):

```
uv pip install --python $PY huggingface_hub
& "$T\venv-qwen3\Scripts\hf.exe" download Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign --local-dir "$T\modelli\qwen3-tts-1.7b-voicedesign"
& "$T\venv-qwen3\Scripts\hf.exe" download Qwen/Qwen3-TTS-12Hz-0.6B-Base --local-dir "$T\modelli\qwen3-tts-0.6b-base"
& "$T\venv-qwen3\Scripts\hf.exe" download openai/whisper-base --local-dir "$T\modelli\whisper-base"
```

I nomi delle cartelle sono quelli del blocco `modelli` di `voci.json`. Dopo il download gli script non vanno più in rete.

## Rifare le voci da zero

Dalla cartella del repo, con `$PY` come sopra. Le fasi vanno in ordine; ognuna riprende da dove trova i file, quindi per rifare tutto si svuota prima `$T\voci\<capitolo>` (e `riferimenti`, se cambia una voce).

```
& $PY -I -X utf8 tools/voci/voci.py riferimenti    # le voci di riferimento, in $T\voci\riferimenti
& $PY -I -X utf8 tools/voci/voci.py prese          # una presa per seme e per battuta
& $PY -I -X utf8 tools/voci/voci.py scegli         # Whisper ascolta e sceglie
& $PY -I -X utf8 tools/voci/voci.py finali         # trattamento, filtro TV, tempi delle parole, .ogg e manifest.json
& $PY -I -X utf8 tools/voci/voci.py demo           # la scena montata, in .wav e .mp4 con i sottotitoli
& $PY -I tools/voci/zip_voci.py                    # $T\voci\voci-prologo.zip
```

Il capitolo di default è `prologo`; per un altro si aggiunge `--capitolo <nome>`. Altre opzioni:
- `--voce <voce>=<proposta>`, per provare un'altra proposta di voce;
- `--solo <voce>`, per lavorare su una voce sola;
- `--tv <livello>|senza`, per un altro livello del filtro TV;
- `voci.py tv`, che rifà solo gli `.ogg` dai `.wav` senza filtro, quando cambia il filtro.

Le scelte fatte a orecchio stanno in `scelte_a_mano` di `voci.json` e vincono su Whisper.

Dove finisce tutto, in `$T\voci\`:
- `<capitolo>\manifest.json` e `<capitolo>\<scena>\<id>.ogg`: le voci per il gioco (48 kHz, mono, Vorbis);
- `<capitolo>\_finali\`: gli stessi file in `.wav`, senza il filtro TV;
- `demo\`: le scene montate;
- `voci-<capitolo>.zip`: manifest e `.ogg`, da caricare a mano fra gli allegati della release.

Niente di questo va nel repo: il manifest e l'audio contengono le battute.

## Scegliere a orecchio

```
& $PY -I -X utf8 tools/voci/scelta.py       # le prese migliori di ogni voce, in $T\voci\scelta
& $PY -I -X utf8 tools/voci/scelta_tv.py    # le battute finali a ogni livello del filtro TV
tools\voci\apri_scelta.cmd                   # avvia il server e apre http://127.0.0.1:8765/
```

Il server ascolta solo su `127.0.0.1`. La pagina viene da `tools/voci/scelta/index.html`, i dati e l'audio dal laboratorio. **Salva le scelte** scrive `$T\voci\scelta\scelte_luigi.json`.

`misura_g.py` e `misura_rif.py` sono due controlli piccoli: la g dolce di un nome e tono e velocità dei riferimenti.

## Licenze

- Il codice di questa cartella è MIT, come gli altri strumenti.
- [Qwen3-TTS](https://github.com/Qwen/Qwen3-TTS) (i modelli `Qwen3-TTS-12Hz-1.7B-VoiceDesign` e `Qwen3-TTS-12Hz-0.6B-Base` e il pacchetto `qwen-tts`): Apache-2.0, del team Qwen di Alibaba. Permette l'uso commerciale; per vendere il gioco basta citarlo nei crediti e tenere l'avviso della licenza.
- [Whisper base](https://huggingface.co/openai/whisper-base): MIT, © OpenAI. Serve solo a controllare le prese, non finisce nel gioco.
- Le voci non vengono da persone vere: sono progettate da una descrizione scritta. L'audio prodotto segue le licenze degli asset del gioco.
