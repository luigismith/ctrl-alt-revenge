#!/usr/bin/env bash
# Esegue Godot 4.7.2 (su Windows l'eseguibile console, sul Mac quello dentro Godot.app, su Linux
# quello per x86_64; oppure quello della variabile GODOT) sul progetto game/ con timeout e file di log, poi controlla il log. Il progetto si cambia con la
# variabile GODOT_PROJECT (cartella con project.godot, assoluta o relativa alla radice del
# repository; predefinita: game/), mai con un secondo --path. Fallisce se:
#   - il codice d'uscita non è 0 (124 = timeout);
#   - il log contiene SCRIPT ERROR, Parse Error o righe che iniziano con ERROR:
#     (salvo quelle che corrispondono alla regex in GODOT_ERR_ALLOW);
#   - con REQUIRE_DONE=1, l'ultima riga non vuota dell'output non è "DONE".
#
# Uso:  tools/run_godot.sh <secondi> [argomenti per Godot...]
# Esempi:
#   tools/run_godot.sh 120 --headless --import
#   REQUIRE_DONE=1 tools/run_godot.sh 120 --headless -s res://tests/run_tests.gd
#   tools/run_godot.sh 90 --write-movie "C:/percorso/assoluto/f.png" --fixed-fps 60 --quit-after 300
#   GODOT_PROJECT=tools/fxui/out/godot_check tools/run_godot.sh 60 --headless --import
set -u

# L'eseguibile si può dare con la variabile GODOT (un percorso o un nome nel PATH): la usa la CI.
case "$(uname -s)" in
  Darwin)
    # Mac: il laboratorio in ~/ctrlaltrevenge-lab, con Godot.app; i percorsi restano quelli di Unix
    LAB="${CAR_LAB:-$HOME/ctrlaltrevenge-lab}"
    GODOT="${GODOT:-$LAB/tools/godot-4.7.2/Godot.app/Contents/MacOS/Godot}"
    unix_path() { printf '%s' "$1"; }
    native_path() { printf '%s' "$1"; }
    ;;
  MINGW*|MSYS*|CYGWIN*)
    # Git Bash su Windows: Godot vuole i percorsi di Windows
    LAB="$(cygpath -u "${CAR_LAB:-${USERPROFILE}\\ctrlaltrevenge-lab}")"
    GODOT="${GODOT:-$LAB/tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe}"
    unix_path() { cygpath -u "$1"; }
    native_path() { cygpath -w "$1"; }
    ;;
  *)
    # Linux (la CI di GitHub, o WSL): l'eseguibile del laboratorio, se manca la variabile GODOT
    LAB="${CAR_LAB:-$HOME/ctrlaltrevenge-lab}"
    GODOT="${GODOT:-$LAB/tools/godot-4.7.2/Godot_v4.7.2-stable_linux.x86_64}"
    unix_path() { printf '%s' "$1"; }
    native_path() { printf '%s' "$1"; }
    ;;
esac
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GODOT_PROJECT:-$ROOT/game}"
case "$PROJECT" in
  /*|[A-Za-z]:*) ;;
  *) PROJECT="$ROOT/$PROJECT" ;;
esac
PROJECT="$(unix_path "$PROJECT")"

if ! command -v "$GODOT" >/dev/null 2>&1; then
  echo "Godot non trovato: $GODOT" >&2
  exit 3
fi
if [ ! -f "$PROJECT/project.godot" ]; then
  echo "Progetto Godot non trovato: $PROJECT" >&2
  exit 3
fi

SECS="${1:?indica il timeout in secondi}"
shift

LOGDIR="$ROOT/tools/out/logs"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
LOG="$LOGDIR/godot-$STAMP.log"
OUT="$LOGDIR/godot-$STAMP.out"

# Il timeout di GNU c'è in Git Bash, non sul Mac: lì lo fa questa funzione, con lo stesso codice
# d'uscita (124). Il cane da guardia scrive su /dev/null, così non tiene aperta l'uscita di chi
# ha lanciato lo script.
if command -v timeout >/dev/null 2>&1; then
  run_limited() { timeout --kill-after=10 "$@"; }
else
  run_limited() {
    local secs="$1" flag="$LOGDIR/.timeout-$STAMP"
    shift
    "$@" &
    local pid=$!
    ( sleep "$secs"; if kill -TERM "$pid" 2>/dev/null; then : >"$flag"; sleep 10; kill -KILL "$pid" 2>/dev/null; fi ) \
      >/dev/null 2>&1 &
    local watch=$!
    wait "$pid"
    local code=$?
    pkill -P "$watch" >/dev/null 2>&1
    kill "$watch" >/dev/null 2>&1
    wait "$watch" 2>/dev/null
    if [ -e "$flag" ]; then
      rm -f "$flag"
      return 124
    fi
    return "$code"
  }
fi

run_limited "$SECS" "$GODOT" --path "$(native_path "$PROJECT")" \
  --log-file "$(native_path "$LOG")" "$@" >"$OUT" 2>&1
CODE=$?

FAIL=0
if [ "$CODE" -ne 0 ]; then
  echo "Godot è uscito con codice $CODE (124 = timeout)" >&2
  FAIL=1
fi

ERRS="$(cat "$LOG" "$OUT" 2>/dev/null | grep -E "SCRIPT ERROR|Parse Error|^ERROR:" || true)"
if [ -n "${GODOT_ERR_ALLOW:-}" ] && [ -n "$ERRS" ]; then
  ERRS="$(printf '%s\n' "$ERRS" | grep -Ev "$GODOT_ERR_ALLOW" || true)"
fi
if [ -n "$ERRS" ]; then
  echo "Errori nel log di Godot:" >&2
  printf '%s\n' "$ERRS" | head -40 >&2
  FAIL=1
fi

if [ "${REQUIRE_DONE:-0}" = "1" ]; then
  LAST="$(grep -v '^[[:space:]]*$' "$OUT" | tail -1 | tr -d '\r')"
  if [ "$LAST" != "DONE" ]; then
    echo "Manca la riga finale DONE (ultima riga: '$LAST')" >&2
    FAIL=1
  fi
fi

echo "log: $LOG"
echo "output: $OUT"
if [ "$FAIL" -ne 0 ]; then
  echo "--- ultime righe dell'output ---" >&2
  tail -30 "$OUT" >&2
  exit 1
fi
echo "OK"
exit 0
