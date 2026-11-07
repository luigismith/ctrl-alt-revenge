#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""La g iniziale di GIG: dolce (/dʒ/, affricata, con fruscio sopra i 2,5 kHz per 40-90 ms) o dura (/g/, scoppio breve)?
Misura, nella finestra fra l'inizio della parola e l'inizio della vocale, la durata del fruscio ad alta frequenza.

Uso:  python -I tools/voci/misura_g.py <cartella di whisper-base> "<prese>\\*.wav"
L'ultima parola di ogni presa è quella misurata."""
import glob, os, sys
import librosa, numpy as np, torch
from transformers import pipeline
wdir, pattern = sys.argv[1], sys.argv[2]
asr = pipeline("automatic-speech-recognition", model=wdir, device=0 if torch.cuda.is_available() else -1)
for p in sorted(glob.glob(pattern)):
    y, sr = librosa.load(p, sr=16000)
    r = asr({"raw": y, "sampling_rate": 16000}, return_timestamps="word", generate_kwargs={"language": "it", "task": "transcribe"})
    ch = r["chunks"][-1]
    t0 = max(0.0, ch["timestamp"][0] - 0.05)
    seg = y[int(t0 * sr): int((t0 + 0.30) * sr)]
    S = np.abs(librosa.stft(seg, n_fft=256, hop_length=40)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=256)
    hi = S[f > 2500].sum(0); lo = S[(f > 100) & (f < 1000)].sum(0)
    ratio = hi / (lo + 1e-9)
    tot = S.sum(0); act = tot > tot.max() * 0.01
    fric = ((ratio > 1.0) & act).sum() * 40 / sr * 1000
    print("%-38s %-10s fruscio %3.0f ms" % (os.path.basename(p), ch["text"].strip(), fric))
