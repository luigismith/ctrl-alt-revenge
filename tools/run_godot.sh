#!/usr/bin/env bash
# Esegue Godot 4.7.2 (eseguibile console) sul progetto game/ con timeout e file di log,
# poi controlla il log. Il progetto si cambia con la variabile GODOT_PROJECT (cartella con
# project.godot, assoluta o relativa alla radice del repository; predefinita: game/), mai con
# un secondo --path. Fallisce se:
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

LAB_WIN="${CAR_LAB:-${USERPROFILE}\\ctrlaltrevenge-lab}"
LAB="$(cygpath -u "$LAB_WIN")"
GODOT="$LAB/tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GODOT_PROJECT:-$ROOT/game}"
case "$PROJECT" in
  /*|[A-Za-z]:*) ;;
  *) PROJECT="$ROOT/$PROJECT" ;;
esac
PROJECT="$(cygpath -u "$PROJECT")"

if [ ! -x "$GODOT" ]; then
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

timeout --kill-after=10 "$SECS" "$GODOT" --path "$(cygpath -w "$PROJECT")" \
  --log-file "$(cygpath -w "$LOG")" "$@" >"$OUT" 2>&1
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
