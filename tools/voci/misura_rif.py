#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Misura i riferimenti: cosa sente Whisper, tono mediano e sua stabilità, velocità (lettere al secondo).

Uso:  python -I tools/voci/misura_rif.py <cartella di whisper-base> <laboratorio>\\tts\\voci\\riferimenti
Per ogni .wav legge il testo dal .txt accanto."""
import glob, os, sys
import librosa, numpy as np, torch
from transformers import pipeline
wdir, folder = sys.argv[1], sys.argv[2]
asr = pipeline("automatic-speech-recognition", model=wdir, device=0 if torch.cuda.is_available() else -1)
for p in sorted(glob.glob(os.path.join(folder, "*.wav"))):
    y, sr = librosa.load(p, sr=16000)
    hyp = asr({"raw": y, "sampling_rate": 16000}, generate_kwargs={"language": "it", "task": "transcribe", "num_beams": 5})["text"].strip()
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=500, sr=16000)
    f0 = f0[~np.isnan(f0)]
    txt = open(p[:-4] + ".txt", encoding="utf-8").read()
    n = sum(c.isalpha() for c in txt)
    print("%s | %.1f s | F0 med %.0f Hz, p10-p90 %.0f-%.0f | %.1f lettere/s\n   %s" % (os.path.basename(p), y.size/16000, np.median(f0), np.percentile(f0,10), np.percentile(f0,90), n/(y.size/16000), hyp))
