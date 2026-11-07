#!/usr/bin/env bash
# Esporta la demo web del gioco (preset "Web" di game/export_presets.cfg: release, senza thread,
# così gira anche su GitHub Pages, che non manda le intestazioni COOP/COEP) e la prepara per il sito.
# Lo stesso script gira in locale (Git Bash su Windows) e su GitHub (.github/workflows/sito.yml).
#
# Uso:  tools/site/export_web.sh [cartella di uscita]
#   senza argomenti esporta in <laboratorio>/sito/web
#
# Variabili, tutte facoltative:
#   GODOT    eseguibile di Godot 4.7.2 con i modelli d'esportazione installati (predefinito: quello
#            console del laboratorio, in modalità autonoma: i modelli stanno nella sua editor_data/;
#            sul Mac quello di Godot.app, con editor_data/ accanto all'app)
#   WORK     cartella per la copia del progetto (predefinita: <laboratorio>/sito/godot-web; è
#            diversa da sito/godot, che usa tools/site/media.py, così i due script non si
#            cancellano la copia a vicenda)
#   CAR_LAB  cartella del laboratorio (predefinita: %USERPROFILE%\ctrlaltrevenge-lab)
#   CAR_MUSIC_DIR  cartella con music.json e gli OGG della demo (per esempio gli allegati della release
#            "musica-demo"): se c'è, la musica entra nella build in res://assets_private/music/;
#            se manca, la demo esce senza musica, come prima
#   CAR_BATTUTE_DIR  cartella con le battute private delle scene (predefinita: docs/lore/battute, la
#            cartella privata della storia, che git ignora). La demo ha solo quelle del prologo
#            (decisione 68): DEMO_BATTUTE. Se il file manca, le scene mostrano un segnaposto
#   CAR_BATTUTE_OBBLIGATORIE=1  senza le battute del prologo l'esportazione si ferma
#   CAR_VOCI_DIR  cartella con le voci delle battute (decisione 92), una sottocartella per file di
#            battute: <capitolo>/manifest.json e <capitolo>/<scena>/<id>.ogg, come le scrive voci.py nel
#            laboratorio (predefinita: <laboratorio>/tts/voci). Entrano in res://assets_private/voci/,
#            solo per DEMO_BATTUTE; i file di lavoro (quelli che iniziano con "_") restano fuori
#
# Passi:
#   1. copia game/ in WORK senza .godot/, così l'importazione riparte da zero come su GitHub, e senza
#      assets_private/, perché la musica non deve mai entrare nella build web; aggiunge
#      THIRD-PARTY-NOTICES.md, che i crediti leggono da res:// e che il filtro del preset include;
#      copia le battute del prologo in data/battute/, dove le cerca SceneLines (solo nella copia: nel
#      repo pubblico non ci sono); se ci sono, mette musica e voci in assets_private/ e toglie
#      assets_private/* dal filtro di esclusione del preset (solo nella copia);
#   2. nella copia il preset usa la pagina tools/site/web_shell.html. Nel repo resta la pagina di
#      Godot, così l'esportazione dall'editor funziona anche senza questo script;
#   3. importa gli asset ed esporta in release;
#   4. mette accanto a index.html il logo e il font della pagina di caricamento, presi dagli asset
#      del gioco (se cambiano, basta rilanciare lo script);
#   5. controlla i log (solo quelli dei tentativi riusciti) e che nella build ci siano solo la musica,
#      le battute e le voci date,
#      stampa il peso dei file e scrive nella pagina della demo quanti MB si scaricano.
#
# Per provarla in locale:
#   "$USERPROFILE/ctrlaltrevenge-lab/venv/Scripts/python.exe" -I -m http.server 8650 \
#       --bind 127.0.0.1 --directory "<cartella di uscita>"
# e aprire http://127.0.0.1:8650/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if command -v cygpath >/dev/null 2>&1; then
  # Git Bash su Windows: Godot vuole percorsi Windows (con le barre in avanti va bene)
  native() { cygpath -m "$1"; }
  LAB="$(cygpath -u "${CAR_LAB:-${USERPROFILE}\\ctrlaltrevenge-lab}")"
  GODOT="${GODOT:-$LAB/tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe}"
else
  native() { printf '%s' "$1"; }
  LAB="${CAR_LAB:-$HOME/ctrlaltrevenge-lab}"
  # sul Mac quello del laboratorio, se c'è (su GitHub, in Linux, il godot del PATH)
  MAC_GODOT="$LAB/tools/godot-4.7.2/Godot.app/Contents/MacOS/Godot"
  if [ -z "${GODOT:-}" ] && [ -x "$MAC_GODOT" ]; then
    GODOT="$MAC_GODOT"
  fi
  GODOT="${GODOT:-godot}"
fi
WORK="${WORK:-$LAB/sito/godot-web}"
OUT="${1:-$LAB/sito/web}"

if ! command -v "$GODOT" >/dev/null 2>&1; then
  echo "Godot non trovato: $GODOT (imposta la variabile GODOT)" >&2
  exit 3
fi

# Prima di svuotare una cartella controlla che sia davvero roba di questo script: la copia del
# progetto ha il file MARK, l'uscita di un'esportazione ha index.wasm (una cartella del sito no).
MARK=".copia-di-export_web"
check_dir() {
  local dir="$1" mark="$2"
  if [ -z "$dir" ] || [ "$dir" = "/" ]; then
    echo "Cartella non valida: '$dir'" >&2
    exit 2
  fi
  if [ -d "$dir" ] && [ -n "$(ls -A "$dir")" ] && [ ! -e "$dir/$mark" ]; then
    echo "$dir non è vuota e non contiene $mark: non la svuoto." >&2
    exit 2
  fi
}
check_dir "$WORK" "$MARK"
check_dir "$OUT" index.wasm

# --- 1. copia del progetto --------------------------------------------------------------------
echo "Copia del progetto in $WORK"
rm -rf "$WORK"
mkdir -p "$WORK"
(cd "$ROOT/game" && tar --exclude=./.godot --exclude=./assets_private --exclude=./data/battute -cf - .) | (cd "$WORK" && tar -xf -)
cp "$ROOT/THIRD-PARTY-NOTICES.md" "$WORK/"
# i file che iniziano con il punto Godot non li vede: il segno resta fuori dal gioco
touch "$WORK/$MARK"
# La musica della demo, solo se è stata data: va in assets_private/music, dove la cerca Music, e il
# preset della copia smette di escludere assets_private (nel repo il preset resta com'è).
MUSIC=0
if [ -n "${CAR_MUSIC_DIR:-}" ] && [ -f "$CAR_MUSIC_DIR/music.json" ]; then
  mkdir -p "$WORK/assets_private/music"
  cp "$CAR_MUSIC_DIR/music.json" "$WORK/assets_private/music/"
  cp "$CAR_MUSIC_DIR"/*.ogg "$WORK/assets_private/music/"
  sed -i 's|^exclude_filter="tests/\*, assets_private/\*"$|exclude_filter="tests/*"|' "$WORK/export_presets.cfg"
  MUSIC=1
  echo "Musica della demo da $CAR_MUSIC_DIR:"
  ls -l "$WORK/assets_private/music"
fi

# Le battute private delle scene: solo i file di DEMO_BATTUTE (il prologo), dalla cartella privata.
DEMO_BATTUTE="prologo"
BATTUTE_DIR="${CAR_BATTUTE_DIR:-$ROOT/docs/lore/battute}"
BATTUTE=0
for b in $DEMO_BATTUTE; do
  if [ -f "$BATTUTE_DIR/$b.json" ]; then
    mkdir -p "$WORK/data/battute"
    cp "$BATTUTE_DIR/$b.json" "$WORK/data/battute/"
    BATTUTE=1
  elif [ "${CAR_BATTUTE_OBBLIGATORIE:-0}" = 1 ]; then
    echo "Mancano le battute $BATTUTE_DIR/$b.json (CAR_BATTUTE_OBBLIGATORIE=1)." >&2
    exit 1
  else
    echo "  Attenzione: mancano le battute $BATTUTE_DIR/$b.json, le scene avranno il segnaposto." >&2
  fi
done
if [ "$BATTUTE" = 1 ]; then
  echo "Battute della demo da $BATTUTE_DIR:"
  ls -l "$WORK/data/battute"
fi

# Le voci delle battute, se ci sono: solo il manifest e gli OGG, in assets_private/voci/<capitolo>/.
VOCI_DIR="${CAR_VOCI_DIR:-$LAB/tts/voci}"
VOCI=0
for b in $DEMO_BATTUTE; do
  if [ -f "$VOCI_DIR/$b/manifest.json" ]; then
    mkdir -p "$WORK/assets_private/voci/$b"
    (cd "$VOCI_DIR/$b" && find . -name '_*' -prune -o -type f \( -name manifest.json -o -name '*.ogg' \) -print | tar -cf - -T -) \
      | (cd "$WORK/assets_private/voci/$b" && tar -xf -)
    VOCI=1
  fi
done
if [ "$VOCI" = 1 ]; then
  sed -i 's|^exclude_filter="tests/\*, assets_private/\*"$|exclude_filter="tests/*"|' "$WORK/export_presets.cfg"
  echo "Voci della demo da $VOCI_DIR: $(find "$WORK/assets_private/voci" -name '*.ogg' | wc -l) file"
fi

# --- 2. pagina della demo -------------------------------------------------------------------
cp "$ROOT/tools/site/web_shell.html" "$WORK/web_shell.html"
sed -i 's|^html/custom_html_shell=.*$|html/custom_html_shell="res://web_shell.html"|' "$WORK/export_presets.cfg"
if ! grep -q '^html/custom_html_shell="res://web_shell.html"$' "$WORK/export_presets.cfg"; then
  echo "Nel preset manca html/custom_html_shell: c'è ancora il preset Web in game/export_presets.cfg?" >&2
  exit 1
fi

# --- 3. importazione ed esportazione ----------------------------------------------------------
LOG="${WORK%/}-export.log"
LOGDIR="${WORK%/}-log"
: >"$LOG"
rm -rf "$LOGDIR"
mkdir -p "$LOGDIR"
OK_LOGS=()
# Godot 4.7.2 a volte va in segmentation fault all'inizio della prima importazione (in locale circa
# 3 volte su 10, sempre sul primo file da reimportare): si ripulisce e si riprova da capo. Ogni
# tentativo ha il suo log (in $LOGDIR); gli errori si cercano solo in quelli dei tentativi riusciti,
# così le righe di un tentativo finito male non bocciano quello dopo. $LOG li raccoglie tutti.
# Uso: run_godot <descrizione> <tentativi> <funzione di pulizia> <argomenti per Godot...>
run_godot() {
  local what="$1" max="$2" cleanup="$3" n=1 log
  shift 3
  while :; do
    log="$LOGDIR/$what-$n.log"
    if timeout --kill-after=10 600 "$GODOT" --headless --path "$(native "$WORK")" "$@" >"$log" 2>&1; then
      cat "$log" >>"$LOG"
      OK_LOGS+=("$log")
      return 0
    fi
    cat "$log" >>"$LOG"
    if [ "$n" -ge "$max" ]; then
      echo "$what: Godot non è riuscito dopo $n tentativi. Ultime righe di $log:" >&2
      tail -30 "$log" >&2
      exit 1
    fi
    echo "  $what interrotta (tentativo $n di $max): riprovo da capo" >&2
    "$cleanup"
    n=$((n + 1))
  done
}
clean_import() { rm -rf "$WORK/.godot"; }
clean_export() { rm -rf "$OUT"; mkdir -p "$OUT"; }

echo "Importazione degli asset"
run_godot "Importazione" 5 clean_import --import
echo "Esportazione web (release, senza thread) in $OUT"
clean_export
run_godot "Esportazione" 3 clean_export --export-release "Web" "$(native "$OUT")/index.html"

# Errori nei log dei tentativi riusciti (i colori ANSI si tolgono prima di cercare)
ERRS="$(sed 's/\x1b\[[0-9;]*m//g' "${OK_LOGS[@]}" | grep -E "SCRIPT ERROR|Parse Error|^ERROR:" || true)"
if [ -n "$ERRS" ]; then
  echo "Errori nel log di Godot (${OK_LOGS[*]}):" >&2
  printf '%s\n' "$ERRS" | head -40 >&2
  exit 1
fi
for f in index.html index.js index.wasm index.pck index.audio.worklet.js; do
  if [ ! -s "$OUT/$f" ]; then
    echo "Manca $OUT/$f: l'esportazione non è completa." >&2
    exit 1
  fi
done
if ! grep -q 'car_pixel_bold.ttf' "$OUT/index.html"; then
  echo "index.html non usa la pagina tools/site/web_shell.html." >&2
  exit 1
fi

# --- 4. logo e font della pagina di caricamento ----------------------------------------------
cp "$ROOT/game/assets/ui/title_logo.png" "$OUT/logo.png"
cp "$ROOT/game/assets/fonts/car_pixel_bold.ttf" "$OUT/car_pixel_bold.ttf"
# l'immagine d'avvio di Godot serve solo alla sua pagina predefinita
rm -f "$OUT/index.png"

# --- 5. musica solo se data, e peso dei file -------------------------------------------------
# Nel pacchetto i percorsi sono in chiaro: la musica importata sarebbe .oggvorbisstr o .mp3str.
if [ "$MUSIC" = 1 ]; then
  if ! LC_ALL=C grep -a -q 'assets_private/music/music.json' "$OUT/index.pck"; then
    echo "La musica della demo era data, ma nella build non c'è." >&2
    exit 1
  fi
elif [ "$VOCI" = 0 ] && LC_ALL=C grep -a -q -E 'assets_private|\.oggvorbisstr|\.mp3str' "$OUT/index.pck"; then
  echo "Nella build c'è della musica (assets_private, OGG o MP3) che nessuno ha dato: non si pubblica." >&2
  exit 1
elif LC_ALL=C grep -a -q 'assets_private/music' "$OUT/index.pck"; then
  echo "Nella build c'è della musica che nessuno ha dato: non si pubblica." >&2
  exit 1
fi

# Le voci: solo se date, e solo per i capitoli della demo.
if [ "$VOCI" = 1 ]; then
  for b in $DEMO_BATTUTE; do
    if [ -f "$VOCI_DIR/$b/manifest.json" ] && ! LC_ALL=C grep -a -q "assets_private/voci/$b/manifest.json" "$OUT/index.pck"; then
      echo "Le voci di $b erano date, ma nella build non ci sono." >&2
      exit 1
    fi
  done
  OTHER="$(LC_ALL=C grep -a -o -E 'assets_private/voci/[A-Za-z0-9_-]+/' "$OUT/index.pck" | sort -u || true)"
  for o in $OTHER; do
    c="${o#assets_private/voci/}"; c="${c%/}"
    case " $DEMO_BATTUTE " in *" $c "*) ;; *) echo "Nella build ci sono voci che la demo non deve avere: $c" >&2; exit 1 ;; esac
  done
elif LC_ALL=C grep -a -q 'assets_private/voci' "$OUT/index.pck"; then
  echo "Nella build ci sono voci che nessuno ha dato: non si pubblica." >&2
  exit 1
fi

# Le battute: nella build solo quelle date (il prologo), nessun altro capitolo.
if [ "$BATTUTE" = 1 ] && ! LC_ALL=C grep -a -q 'data/battute/prologo.json' "$OUT/index.pck"; then
  echo "Le battute del prologo erano date, ma nella build non ci sono." >&2
  exit 1
fi
OTHER="$(LC_ALL=C grep -a -o -E 'data/battute/[A-Za-z0-9_-]+\.json' "$OUT/index.pck" | sort -u | grep -v -x 'data/battute/prologo.json' || true)"
if [ -n "$OTHER" ]; then
  echo "Nella build ci sono battute che la demo non deve avere: $OTHER" >&2
  exit 1
fi

# Il pacchetto si apre come lo legge la build: i nemici devono avere i loro attacchi (vedi
# tools/site/controlla_pck.gd: in 4.7.2 la conversione dei .tres in binario li svuotava).
CHECK_LOG="$LOGDIR/controlla_pck.log"
if ! (cd "$OUT" && timeout 120 "$GODOT" --headless --main-pack "$(native "$OUT/index.pck")" \
    -s "$(native "$ROOT/tools/site/controlla_pck.gd")") >"$CHECK_LOG" 2>&1 \
    || ! grep -q 'CONTROLLO_PCK_OK' "$CHECK_LOG"; then
  echo "Il controllo del pacchetto non è passato:" >&2
  grep -E 'Pacchetto|ERROR' "$CHECK_LOG" | head -20 >&2
  exit 1
fi
grep 'Pacchetto controllato' "$CHECK_LOG"

echo "Peso della build (gzip -9 è una stima di quanto si scarica: GitHub Pages comprime il .wasm):"
total=0
total_gz=0
for f in "$OUT"/*; do
  size=$(wc -c <"$f")
  gz=$(gzip -9 -c "$f" | wc -c)
  total=$((total + size))
  total_gz=$((total_gz + gz))
  printf '  %-34s %10d byte   gzip %10d\n' "$(basename "$f")" "$size" "$gz"
done
awk -v t="$total" -v g="$total_gz" 'BEGIN { printf "  TOTALE %.1f MB, con gzip %.1f MB\n", t / 1e6, g / 1e6 }'
# La pagina della demo dice quanto si scarica: il peso con gzip, arrotondato al MB.
MB="$(awk -v g="$total_gz" 'BEGIN { printf "%.0f", g / 1e6 }')"
sed -i "s/__CAR_DEMO_MB__/$MB/g" "$OUT/index.html"
if grep -q '__CAR_DEMO_MB__' "$OUT/index.html"; then
  echo "index.html: il peso della demo non è stato scritto." >&2
  exit 1
fi
echo "  nella pagina della demo: circa $MB MB"
echo "OK"
