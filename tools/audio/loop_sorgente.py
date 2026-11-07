#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Prepara una sorgente con il giunto del loop già pulito, da passare a prepare_music.py.

Serve per i brani radi che non si ripetono mai uguali (le scene parlate fatte con Suno):
lì PyMusicLooper non trova un giunto pulito. Lo script:

1. prende il loop INIZIO -> FINE (in campioni, a battute intere);
2. fa sfumare l'ultima parte prima di FINE, a potenza costante, nella musica che precede
   INIZIO, così al ritorno del loop il segnale continua senza salti;
3. se si indica --taglia, toglie l'inizio fino a quel campione, con 20 ms di dissolvenza in entrata
   (per le scene sorelle che partono a metà del brano);
4. scrive un WAV float a 32 bit che finisce a FINE e stampa i valori da dare a prepare_music.py:
   --loop INIZIO FINE --no-refine.

Esempio (il messo, 6 novembre 2026):
  python -I tools/audio/loop_sorgente.py suno/pignoramento.wav suno/lavorati/porta.wav \\
      4305600 5441290 --dissolvenza 2.956 --taglia 4281600
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402
from scipy.io import wavfile  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sorgente", type=Path, help="WAV scaricato da Suno")
    ap.add_argument("uscita", type=Path, help="WAV lavorato (nel laboratorio, mai nel repo)")
    ap.add_argument("inizio", type=int, help="inizio del loop, in campioni")
    ap.add_argument("fine", type=int, help="fine del loop, in campioni")
    ap.add_argument("--dissolvenza", type=float, default=0.0, help="secondi di dissolvenza prima della fine (0: nessuna)")
    ap.add_argument("--taglia", type=int, default=0, help="campione da cui comincia il file (0: dall'inizio)")
    a = ap.parse_args()

    x, sr = al.read_wav(a.sorgente)
    x = al.as_2d(x)
    s, e, t0 = a.inizio, a.fine, a.taglia
    n = int(round(a.dissolvenza * sr))
    if not (0 <= t0 <= s < e <= len(x)) or s - n < 0:
        ap.error(f"valori fuori dal brano ({len(x)} campioni) o dissolvenza più lunga dell'inizio")
    y = x[:e].copy()
    if n > 0:
        t = (np.arange(n) + 0.5) / n
        y[e - n:e] = (x[e - n:e] * np.cos(np.pi * t / 2)[:, None]
                      + x[s - n:s] * np.sin(np.pi * t / 2)[:, None])
    if t0 > 0:
        y = y[t0:].copy()
        f = int(0.02 * sr)
        y[:f] *= np.linspace(0.0, 1.0, f)[:, None]
    a.uscita.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(a.uscita), sr, y.astype(np.float32))
    s2, e2 = s - t0, e - t0
    print(f"{a.uscita.name}: --loop {s2 / sr:.6f} {e2 / sr:.6f} --no-refine "
          f"(campioni {s2} -> {e2}, picco {al.db(float(np.abs(y).max())):.2f} dBFS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
