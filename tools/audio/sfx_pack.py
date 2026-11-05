#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Monta gli effetti sonori del gioco da suoni già pronti, con licenza libera (scelta di Luigi del
5 novembre 2026: i suoni sintetizzati da tools/audio/sfx_gen.py non andavano).

Le fonti sono pacchetti CC0 (Kenney, Freesound, OpenGameArt) e un pacchetto CC-BY 4.0 (i pugni di
DavidW, per i colpi pesanti e il KO): l'elenco con autori, pagine e licenze è in FONTI_SFX, i
crediti stanno in CREDITS.md. I file sorgente non stanno nel repo ma nel laboratorio, in
sources/sfx/<pacchetto>/ (arrivano da un PC all'altro con la cartella condivisa).

Ogni suono del gioco è una ricetta: uno o più strati (file, ritardo, guadagno, taglio, intonazione,
filtri), mescolati e poi rifiniti come quelli di sfx_gen: picco a -1 dBFS, senza componente continua,
code tagliate, dissolvenze. Ai colpi si aggiunge una saturazione morbida, che dà lo schiocco compresso
dei picchiaduro a scorrimento di console. Il guadagno di missaggio di ogni suono va in mix.json, con
gli stessi livelli di loudness di sfx_gen.

  python -I tools/audio/sfx_pack.py                 # monta in tools/audio/out/sfx_pack/ e controlla
  python -I tools/audio/sfx_pack.py --install       # e copia in game/assets/sfx/

I file .wav.import già presenti nel gioco non si toccano (tengono il loro uid); per i suoni nuovi
si scrive quello standard (PCM 16 bit, niente loop).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402
import sfx_gen as G  # noqa: E402

SR = G.SR
ROOT = Path(__file__).resolve().parents[2]
LAB = Path(os.environ.get("CAR_LAB", Path.home() / "ctrlaltrevenge-lab"))
SRC = LAB / "sources" / "sfx"
FFMPEG = LAB / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
OUT_DEFAULT = ROOT / "tools" / "audio" / "out" / "sfx_pack"
GAME_SFX = G.GAME_SFX

# Abbreviazioni delle cartelle delle fonti.
KI = "kenney-impact-sounds/Audio/"
KF = "kenney-interface-sounds/Audio/"
KR = "kenney-rpg-audio/Audio/"
KS = "kenney-sci-fi-sounds/Audio/"
FS = "freesound-cc0/"
RD = "oga-rubberduck-100-cc0-sfx-2/"
TW = "oga-thwack/PCM/"
DW = "oga-davidw-punch-sfx/"

# Le fonti, per i crediti (CREDITS.md) e per chi deve riscaricarle.
FONTI_SFX = {
    "kenney-impact-sounds": ("Kenney", "Impact Sounds", "https://kenney.nl/assets/impact-sounds", "CC0-1.0"),
    "kenney-interface-sounds": ("Kenney", "Interface Sounds", "https://kenney.nl/assets/interface-sounds", "CC0-1.0"),
    "kenney-rpg-audio": ("Kenney", "RPG Audio", "https://kenney.nl/assets/rpg-audio", "CC0-1.0"),
    "kenney-sci-fi-sounds": ("Kenney", "Sci-Fi Sounds", "https://kenney.nl/assets/sci-fi-sounds", "CC0-1.0"),
    "freesound-cc0": ("vari autori", "suoni singoli di Freesound", "https://freesound.org/s/<ID>/", "CC0-1.0"),
    "oga-rubberduck-100-cc0-sfx-2": ("rubberduck", "100 CC0 SFX #2", "https://opengameart.org/content/100-cc0-sfx-2", "CC0-1.0"),
    "oga-thwack": ("AntumDeluge", "Thwack Sounds", "https://opengameart.org/content/thwack-sounds", "CC0-1.0"),
    "oga-davidw-punch-sfx": ("DavidW", "Punch SFX", "https://opengameart.org/content/punch-sfx", "CC-BY-4.0"),
}

# Nomi: quelli di sfx_gen più i due nuovi della stanza di prova.
NAMES = G.NAMES + ["block", "hack"]
MIX_TARGET = dict(G.MIX_TARGET, block=-11.5, hack=-15.0)
# Suoni a cui si dà lo schiocco: saturazione morbida (drive) dopo il missaggio degli strati.
DRIVE = {"hit_light": 2.2, "hit_medium": 2.6, "hit_heavy": 4.5, "hit_kick": 4.0, "knee": 4.0, "ko": 3.5,
         "body_thud": 3.0, "body_fall": 2.0, "block": 4.0, "bin_hit": 2.5}
# Durata massima di ogni suono (s), prima delle code tagliate da finish().
MAX_DUR = {"ko": 1.4, "bin_break": 1.2, "glint": 0.9, "zap": 0.7, "hack": 0.7, "body_fall": 0.8,
           "step_a": 0.16, "step_b": 0.16, "whoosh_light": 0.35, "whoosh_heavy": 0.5, "throw": 0.5,
           "jump": 0.3, "land": 0.35, "pickup": 0.6, "grab": 0.4}


def L(path: str, at: float = 0.0, db: float = 0.0, start: float | None = None, dur: float | None = None,
      pitch: float = 1.0, hp: float = 0.0, lp: float = 0.0) -> dict:
    """Uno strato: file, ritardo (s), guadagno (dB), inizio nel file (None = dal primo attacco),
    durata massima, intonazione (rapporto: <1 più grave e più lungo), passa-alto e passa-basso (Hz)."""
    return dict(path=path, at=at, db=db, start=start, dur=dur, pitch=pitch, hp=hp, lp=lp)


RECIPES = {
    # colpi: il foley di Kenney per il corpo, DavidW sotto per il peso dei colpi pesanti
    "hit_light": [L(KI + "impactPunch_medium_000.ogg", hp=90)],
    "hit_medium": [L(KI + "impactPunch_medium_003.ogg", hp=70), L(DW + "punch_2_0.wav", db=-9, lp=3000)],
    "hit_heavy": [L(DW + "punch_6_0.wav"), L(KI + "impactPunch_heavy_000.ogg", db=-4)],
    "hit_kick": [L(KI + "impactPunch_heavy_002.ogg"), L(DW + "punch_9_0.wav", db=-6, lp=2500)],
    "knee": [L(KI + "impactSoft_heavy_002.ogg"), L(KI + "impactPunch_heavy_003.ogg", db=-3, at=0.004)],
    "ko": [L(DW + "punch_1_0.wav"), L(KI + "impactSoft_heavy_000.ogg", db=-4, at=0.03, pitch=0.85)],
    # aria e stoffa
    "whoosh_light": [L(FS + "389590_Swing-Woosh.ogg", hp=250)],
    "whoosh_heavy": [L(FS + "475135_FX-Swoosh-Low-Pitch.ogg", hp=120)],
    "throw": [L(FS + "507466_Clean-fast-Swoosh-aiff.ogg", pitch=0.85, hp=120), L(KR + "clothBelt.ogg", db=-6)],
    "grab": [L(KR + "cloth1.ogg"), L(FS + "667271_Cloth-Grab.ogg", db=-6)],
    "jump": [L(KR + "cloth4.ogg", hp=200)],
    # corpi a terra e passi sull'asfalto bagnato
    "body_fall": [L(FS + "504626_BODY-FALL-V-HVY-DIRT.ogg")],
    "body_thud": [L(KI + "impactSoft_heavy_000.ogg")],
    "land": [L(FS + "540272_land-a-jump-wav.ogg")],
    "step_a": [L(RD + "sfx100v2_footstep_wet_01.ogg", hp=120)],
    "step_b": [L(RD + "sfx100v2_footstep_wet_02.ogg", hp=120)],
    # oggetti e cyber
    "glint": [L(FS + "545238_Item-Sparkle.ogg", hp=1500)],
    "zap": [L(FS + "512471_Electric-zap-wav.ogg")],
    "hack": [L(KS + "forceField_002.ogg"), L(KF + "glitch_002.ogg", db=-6, at=0.02)],
    "bin_hit": [L(KS + "impactMetal_000.ogg")],
    "bin_break": [L(FS + "498434_Trash-can-falling.ogg")],
    "pickup": [L(FS + "816237_Crunch.ogg")],
    # la parata: un colpo secco sull'avambraccio
    "block": [L(TW + "thwack-02.wav"), L(KI + "impactGeneric_light_000.ogg", db=-6)],
    # interfaccia
    "ui_move": [L(KF + "select_002.ogg")],
    "ui_confirm": [L(KF + "confirmation_001.ogg")],
    "ui_pause": [L(KF + "switch_002.ogg")],
    "go_arrow": [L(KF + "question_001.ogg")],
}


def decode(path: Path) -> np.ndarray:
    """Qualunque formato -> mono float64 a 44,1 kHz, con ffmpeg."""
    ff = str(FFMPEG) if FFMPEG.exists() else "ffmpeg"
    r = subprocess.run([ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg non legge {path}:\n{r.stderr.decode(errors='replace')[-800:]}")
    return np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)


def onset(x: np.ndarray, rel_db: float = -36.0) -> int:
    """Primo campione sopra rel_db dal picco, meno 2 ms: si toglie il silenzio iniziale."""
    p = np.max(np.abs(x))
    idx = np.nonzero(np.abs(x) > p * 10 ** (rel_db / 20))[0]
    return max(0, int(idx[0]) - G.n_of(0.002)) if len(idx) else 0


def repitch(x: np.ndarray, ratio: float) -> np.ndarray:
    """Cambia l'intonazione come un campionatore: ratio < 1 suona più grave e dura di più."""
    if ratio == 1.0:
        return x
    n = int(round(len(x) / ratio))
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x)


def layer(spec: dict) -> np.ndarray:
    x = decode(SRC / spec["path"])
    s = onset(x) if spec["start"] is None else G.n_of(spec["start"])
    x = x[s:]
    if spec["dur"]:
        x = x[:G.n_of(spec["dur"])]
    x = repitch(x, spec["pitch"])
    if spec["hp"]:
        x = G.hp(x, spec["hp"], order=2)
    if spec["lp"]:
        x = G.lp(x, spec["lp"], order=2)
    # ogni strato entra col picco a 0 dB più il suo guadagno: i rapporti nella ricetta sono chiari
    p = np.max(np.abs(x))
    return x / p * al.from_db(spec["db"]) if p > 0 else x


def build(name: str) -> np.ndarray:
    parts = [(G.n_of(sp["at"]), layer(sp)) for sp in RECIPES[name]]
    n = max(o + len(x) for o, x in parts)
    y = np.zeros(n)
    for o, x in parts:
        y[o:o + len(x)] += x
    if name in MAX_DUR:
        m = G.n_of(MAX_DUR[name])
        if len(y) > m:
            y = y[:m]
            fo = G.n_of(0.03)
            y[-fo:] *= np.linspace(1.0, 0.0, fo)
    d = DRIVE.get(name)
    if d:
        # sotto i 55 Hz c'è solo rimbombo che si mangia il margine: via, prima di saturare
        y = G.hp(y, 55.0, order=2)
        y = y / np.max(np.abs(y))
        y = np.tanh(d * y) / np.tanh(d)
    fade_in = 2.0 if name in ("whoosh_light", "whoosh_heavy", "throw", "jump", "glint", "hack") else 0.5
    return G.finish(name, y, fade_in_ms=fade_in, fade_out_ms=25.0 if name in ("ko", "bin_break") else 10.0)


def check(name: str, x: np.ndarray) -> list[str]:
    errs = []
    if abs(al.sample_peak_db(x) - G.PEAK_DBFS) > 0.05:
        errs.append("picco fuori posto")
    if abs(x.mean()) > 1e-4:
        errs.append(f"componente continua {x.mean():.2e}")
    if abs(x[0]) > 1e-3 or abs(x[-1]) > 1e-3:
        errs.append("estremi non nulli")
    if not np.all(np.isfinite(x)):
        errs.append("valori non finiti")
    if not 0.03 <= len(x) / SR <= 1.6:
        errs.append(f"durata {len(x) / SR:.2f} s")
    return errs


def install(out: Path) -> None:
    """Copia WAV e mix.json; l'import solo per i suoni che nel gioco non ci sono ancora."""
    GAME_SFX.mkdir(parents=True, exist_ok=True)
    moves = []
    for p in sorted(out.iterdir()):
        if p.suffix == ".wav" or p.name == "mix.json" or (p.name.endswith(".wav.import") and not (GAME_SFX / p.name).exists()):
            t = GAME_SFX / (p.name + ".tmp_install")
            t.write_bytes(p.read_bytes())
            moves.append((t, GAME_SFX / p.name))
    for t, final in moves:
        os.replace(t, final)
    print(f"installati {len(moves)} file in {GAME_SFX}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    if not SRC.is_dir():
        print(f"mancano le fonti in {SRC}: vedi FONTI_SFX in questo file", file=sys.stderr)
        return 1
    a.out.mkdir(parents=True, exist_ok=True)
    problems, mix = [], {}
    print(f"{'suono':13s} {'ms':>5s} {'F100':>6s} {'centr':>6s} {'mix':>5s}")
    for name in NAMES:
        x = build(name)
        errs = check(name, x)
        if errs:
            problems.append(f"{name}: " + "; ".join(errs))
        fl = G.fast_loudness(x)
        mix[name] = min(0.0, round((MIX_TARGET[name] - fl) * 2) / 2)
        print(f"{name:13s} {len(x) / SR * 1000:5.0f} {fl:6.1f} {al.spectral_centroid(x, SR):6.0f} {mix[name]:5.1f}")
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(G.IMPORT_TEMPLATE, encoding="utf-8", newline="\n")
    doc = {"format": 1, "comment": "Guadagno di missaggio in dB per ogni effetto (generato da tools/audio/sfx_pack.py).",
           "gain_db": mix}
    (a.out / "mix.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"OK: {len(NAMES)} suoni in {a.out}")
    if a.install:
        install(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
