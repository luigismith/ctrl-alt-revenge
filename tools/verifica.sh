#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
# Il controllo unico del repository: lo stesso in locale (Git Bash su Windows, Mac) e nella CI
# (.github/workflows/test.yml, su Linux). Fa, in quest'ordine:
#   1. import   l'importazione di Godot 4.7.2 (headless) del progetto game/;
#   2. test     la suite dei test, con i replay e i loro hash (game/tests/run_tests.gd);
#   3. guardia  tools/guard_assets.py --all: niente musica, storia privata o file enormi nel repo;
#   4. sito     tools/site/build.py in tools/out/verifica/sito: parole vietate, collegamenti, CSP;
#   5. pck      tools/site/controlla_pck.gd sulla build web, solo se c'è (index.pck).
# Ogni passo gira anche se uno prima è fallito, tranne i test, che senza l'importazione non partono.
#
# Stampa un riassunto corto (un rigo per passo, più i test falliti) e scrive tutto il resto nel
# log, così chi lo lancia legge poco. Il codice d'uscita è 0 solo se tutto passa.
#
# Uso:  tools/verifica.sh [--web <cartella della build web>]
# Variabili, tutte facoltative:
#   GODOT       eseguibile di Godot 4.7.2 (predefinito: quello del laboratorio, vedi tools/run_godot.sh)
#   CAR_LAB     cartella del laboratorio (predefinita: ~/ctrlaltrevenge-lab)
#   CAR_WEB_DIR la build web da controllare (predefinita: <laboratorio>/sito/web, quella di
#               tools/site/export_web.sh); vale anche --web
# Log:  tools/out/verifica/verifica-<data>.log, e la copia dell'ultimo in tools/out/verifica/ultimo.log
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v cygpath >/dev/null 2>&1; then
  LAB="$(cygpath -u "${CAR_LAB:-${USERPROFILE}\\ctrlaltrevenge-lab}")"
  native() { cygpath -w "$1"; }
else
  LAB="${CAR_LAB:-$HOME/ctrlaltrevenge-lab}"
  native() { printf '%s' "$1"; }
fi
WEB="${CAR_WEB_DIR:-$LAB/sito/web}"
while [ $# -gt 0 ]; do
  case "$1" in
    --web) WEB="${2:?--web vuole una cartella}"; shift 2 ;;
    -h|--help) sed -n '4,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opzione sconosciuta: $1 (vedi --help)" >&2; exit 2 ;;
  esac
done

# Python 3.10 o più nuovo, come l'hook di pre-commit: python (Windows), python3 (Mac, Linux)
PY=""
for c in python python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    PY="$c"; break
  fi
done

DIR="$ROOT/tools/out/verifica"
mkdir -p "$DIR"
LOG="$DIR/verifica-$(date +%Y%m%d-%H%M%S).log"
: >"$LOG"
INIZIO=$SECONDS
RIGHE=()
DETTAGLI=()
FALLITI=0
PASSATI=0

# passo <nome> <comando...>: lo lancia, ne mette l'uscita nel log e annota l'esito
ESITO_OUT=""
passo() {
  local nome="$1"; shift
  local t0=$SECONDS out="$DIR/.passo.out"
  { echo; echo "=================== $nome: $*"; } >>"$LOG"
  "$@" >"$out" 2>&1
  local code=$?
  cat "$out" >>"$LOG"
  ESITO_OUT="$(cat "$out")"
  rm -f "$out"
  echo "=================== $nome: codice $code, $((SECONDS - t0)) s" >>"$LOG"
  return $code
}
segna() {   # segna <ok|FAIL|--> <testo>
  RIGHE+=("$(printf '  %-4s %s' "$1" "$2")")
  case "$1" in ok) PASSATI=$((PASSATI + 1)) ;; FAIL) FALLITI=$((FALLITI + 1)) ;; esac
}

# 1-2. Godot: importazione e test
if passo import bash tools/run_godot.sh 900 --headless --import; then
  segna ok "import di Godot ($((SECONDS - INIZIO)) s)"
  t=$SECONDS
  REQUIRE_DONE=1 passo test bash tools/run_godot.sh 900 --headless -s res://tests/run_tests.gd
  code=$?
  OUT_FILE="$(printf '%s\n' "$ESITO_OUT" | sed -n 's/^output: //p' | tail -1)"
  if [ -n "$OUT_FILE" ] && [ -f "$OUT_FILE" ]; then
    n_ok=$(grep -c '^ok   - ' "$OUT_FILE")
    n_ko=$(grep -c '^FAIL - ' "$OUT_FILE")
    cat "$OUT_FILE" >>"$LOG"
    while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(grep '^FAIL - ' "$OUT_FILE" | head -15 | cut -c1-200)
  else
    n_ok=0; n_ko=0
  fi
  if [ $code -eq 0 ]; then
    segna ok "test: $n_ok passati, replay compresi ($((SECONDS - t)) s)"
  else
    segna FAIL "test: $n_ok passati, $n_ko falliti ($((SECONDS - t)) s)"
    if [ "$n_ko" -eq 0 ]; then
      while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(printf '%s\n' "$ESITO_OUT" | grep -E 'ERROR|Errori|codice|DONE|non trovato' | head -8 | cut -c1-200)
    fi
  fi
else
  segna FAIL "import di Godot: vedi il log"
  while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(printf '%s\n' "$ESITO_OUT" | grep -E 'ERROR|Errori|codice|non trovato' | head -8 | cut -c1-200)
  segna FAIL "test: non partiti, manca l'importazione"
fi

# 3. la guardia degli asset
if [ -z "$PY" ]; then
  segna FAIL "guardia e sito: manca Python 3.10 o più nuovo"
else
  if passo guardia "$PY" -I tools/guard_assets.py --all; then
    segna ok "guardia degli asset"
  else
    segna FAIL "guardia degli asset"
    while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(printf '%s\n' "$ESITO_OUT" | grep -v '^\s*$' | head -10 | cut -c1-200)
  fi

  # 4. il sito, in una cartella di lavoro (la stessa a ogni giro: build.py la svuota e la rifà)
  if passo sito "$PY" -I tools/site/build.py --out "$(native "$DIR/sito")"; then
    segna ok "build del sito"
  else
    segna FAIL "build del sito"
    while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(printf '%s\n' "$ESITO_OUT" | grep -v '^\s*$' | tail -10 | cut -c1-200)
  fi
fi

# 5. il pacchetto della demo web, se c'è
if [ -f "$WEB/index.pck" ]; then
  G="$(bash -c 'source <(sed -n "/^case \"\$(uname -s)\" in/,/^esac/p" tools/run_godot.sh); printf %s "$GODOT"')"
  pck_check() {
    (cd "$WEB" && timeout 120 "$G" --headless --main-pack "$(native "$WEB/index.pck")" \
      -s "$(native "$ROOT/tools/site/controlla_pck.gd")")
  }
  passo pck pck_check
  if printf '%s\n' "$ESITO_OUT" | grep -q 'CONTROLLO_PCK_OK'; then
    segna ok "pacchetto della demo web ($(du -k "$WEB/index.pck" | cut -f1) KB)"
  else
    segna FAIL "pacchetto della demo web"
    while IFS= read -r r; do DETTAGLI+=("       $r"); done < <(printf '%s\n' "$ESITO_OUT" | grep -E 'Pacchetto|ERROR' | head -8 | cut -c1-200)
  fi
else
  segna -- "pacchetto della demo web: nessuna build in $WEB"
fi

cp "$LOG" "$DIR/ultimo.log"
DURATA=$((SECONDS - INIZIO))
if [ $FALLITI -eq 0 ]; then
  echo "VERIFICA OK: $PASSATI passi passati, 0 falliti ($((DURATA / 60)) min $((DURATA % 60)) s)"
else
  echo "VERIFICA FALLITA: $FALLITI passi falliti, $PASSATI passati ($((DURATA / 60)) min $((DURATA % 60)) s)"
fi
printf '%s\n' "${RIGHE[@]}"
if [ ${#DETTAGLI[@]} -gt 0 ]; then
  echo "  dettagli:"
  printf '%s\n' "${DETTAGLI[@]}"
fi
echo "log: ${LOG#"$ROOT/"}"
[ $FALLITI -eq 0 ]
