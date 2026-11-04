# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Funzioni audio comuni agli strumenti di tools/audio (solo NumPy e SciPy).

- lettura e scrittura WAV (PCM 16 bit in scrittura; in lettura anche 24/32 bit e float);
- loudness secondo ITU-R BS.1770-4 / EBU R128: integrata (con gating), momentanea (400 ms),
  a breve termine (3 s);
- true peak con sovracampionamento 4x (approssimazione di BS.1770-4, allegato 2);
- piccoli aiuti: dB, inviluppi RMS, spettrogrammi.

I segnali sono array float64 con forma (campioni,) per il mono o (campioni, canali).
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


# ---------------------------------------------------------------- WAV

def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Legge un WAV e restituisce (dati float64 in [-1, 1], frequenza di campionamento)."""
    sr, x = wavfile.read(str(path))
    if x.dtype == np.int16:
        y = x.astype(np.float64) / 32768.0
    elif x.dtype == np.int32:
        y = x.astype(np.float64) / 2147483648.0
    elif x.dtype == np.uint8:
        y = (x.astype(np.float64) - 128.0) / 128.0
    else:
        y = x.astype(np.float64)
    return y, int(sr)


def write_wav16(path: str | Path, x: np.ndarray, sr: int) -> None:
    """Scrive PCM 16 bit (mono o stereo) senza dither, con arrotondamento e saturazione."""
    q = np.clip(np.round(np.asarray(x) * 32767.0), -32768, 32767).astype("<i2")
    ch = 1 if q.ndim == 1 else q.shape[1]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(q.tobytes())


def as_2d(x: np.ndarray) -> np.ndarray:
    return x[:, None] if x.ndim == 1 else x


# ---------------------------------------------------------------- dB

def db(v: float | np.ndarray, floor: float = 1e-12) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(v), floor))


def from_db(d: float | np.ndarray) -> float | np.ndarray:
    return 10.0 ** (np.asarray(d) / 20.0)


# ---------------------------------------------------------------- BS.1770-4

def k_weighting_sos(sr: int) -> np.ndarray:
    """I due filtri della pesatura K (mensola acuta + passa-alto RLB) per qualsiasi frequenza,
    con le formule di libebur128 (danno i coefficienti della norma a 48 kHz)."""
    f0 = 1681.974450955533
    g = 3.999843853973347
    q = 0.7071752369554196
    k = np.tan(np.pi * f0 / sr)
    vh = 10.0 ** (g / 20.0)
    vb = vh ** 0.4996667741545416
    a0 = 1.0 + k / q + k * k
    shelf = [(vh + vb * k / q + k * k) / a0, 2.0 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0,
             1.0, 2.0 * (k * k - 1.0) / a0, (1.0 - k / q + k * k) / a0]
    f0 = 38.13547087602444
    q = 0.5003270373238773
    k = np.tan(np.pi * f0 / sr)
    den = 1.0 + k / q + k * k
    hp = [1.0, -2.0, 1.0, 1.0, 2.0 * (k * k - 1.0) / den, (1.0 - k / q + k * k) / den]
    return np.array([shelf, hp])


def _block_powers(x: np.ndarray, sr: int, win_s: float, hop_s: float) -> np.ndarray:
    """Potenza media pesata K (somma sui canali, peso 1 per L/R) per blocchi sovrapposti."""
    y = signal.sosfilt(k_weighting_sos(sr), as_2d(x), axis=0)
    p = np.sum(y * y, axis=1)
    win = int(round(win_s * sr))
    hop = int(round(hop_s * sr))
    if len(p) < win:
        return np.array([p.mean()]) if len(p) else np.array([0.0])
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, len(p) - win + 1, hop)
    return (c[starts + win] - c[starts]) / win


def integrated_loudness(x: np.ndarray, sr: int) -> float:
    """Loudness integrata in LUFS (blocchi di 400 ms al 75 %, gate assoluto -70, relativo -10)."""
    z = _block_powers(x, sr, 0.4, 0.1)
    lk = -0.691 + 10.0 * np.log10(np.maximum(z, 1e-20))
    z1 = z[lk > -70.0]
    if len(z1) == 0:
        return -np.inf
    rel = -0.691 + 10.0 * np.log10(z1.mean()) - 10.0
    z2 = z[(lk > -70.0) & (lk > rel)]
    if len(z2) == 0:
        return -np.inf
    return float(-0.691 + 10.0 * np.log10(z2.mean()))


def momentary_max(x: np.ndarray, sr: int) -> float:
    """Massimo della loudness momentanea (finestra di 400 ms, passo 10 ms)."""
    z = _block_powers(x, sr, 0.4, 0.01)
    return float(-0.691 + 10.0 * np.log10(max(z.max(), 1e-20)))


def short_term_max(x: np.ndarray, sr: int) -> float:
    z = _block_powers(x, sr, 3.0, 0.1)
    return float(-0.691 + 10.0 * np.log10(max(z.max(), 1e-20)))


def true_peak_db(x: np.ndarray, oversample: int = 4) -> float:
    """True peak in dBTP: massimo assoluto dopo un sovracampionamento polifase 4x."""
    y = signal.resample_poly(as_2d(x), oversample, 1, axis=0)
    return float(db(np.max(np.abs(y))))


def sample_peak_db(x: np.ndarray) -> float:
    return float(db(np.max(np.abs(x))))


# ---------------------------------------------------------------- analisi

def rms_envelope(x: np.ndarray, sr: int, win_s: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    """Inviluppo RMS a finestre contigue: (tempi di inizio in s, RMS lineare)."""
    m = as_2d(x).mean(axis=1)
    win = max(1, int(round(win_s * sr)))
    n = len(m) // win
    r = np.sqrt((m[: n * win].reshape(n, win) ** 2).mean(axis=1))
    return np.arange(n) * win / sr, r


def spectral_centroid(x: np.ndarray, sr: int) -> float:
    m = as_2d(x).mean(axis=1)
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / sr)
    return float((f * spec).sum() / max(spec.sum(), 1e-20))


def spectrogram_db(x: np.ndarray, sr: int, nfft: int = 512, hop: int = 64) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    m = as_2d(x).mean(axis=1)
    f, t, s = signal.stft(m, fs=sr, nperseg=nfft, noverlap=nfft - hop, boundary="zeros", padded=True)
    return f, t, 20.0 * np.log10(np.abs(s) + 1e-9)
