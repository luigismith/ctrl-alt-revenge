#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Genera da script tutti gli effetti sonori dello slice (specifica, paragrafo 7).

Dal 5 novembre 2026 il gioco usa i suoni già pronti montati da tools/audio/sfx_pack.py, che prende
da qui nomi, livelli e finitura: --install sovrascriverebbe quei suoni con questi sintetizzati.

Carattere da console 16 bit (Mega Drive): suoni corti, secchi e con peso.
- colpi: transiente netto + corpo grave con discesa di altezza e saturazione + coda di rumore
  filtrato, poi una passata "PCM" (sample-and-hold a bassa frequenza e quantizzazione a pochi bit)
  che imita i campioni del DAC dell'YM2612;
- whoosh: rumore attraverso un filtro passa-banda a stato variabile che si muove;
- glint: campanelli FM acuti; zap: ronzio FM, scariche casuali e sfrigolio;
- interfaccia: toni brevi a onda quadra (PSG) o FM.

Ogni suono ha un seme fisso: lo stesso comando produce sempre gli stessi file, bit per bit.
Uscita: WAV mono, 16 bit, 44,1 kHz, picco a -1 dBFS, senza componente continua, con dissolvenze
di pochi ms all'inizio e alla fine. Il file mix.json accanto ai WAV contiene il guadagno di
missaggio di ogni suono (letto dall'autoload Sfx) perché i file hanno tutti lo stesso picco.

  python -I tools/audio/sfx_gen.py                      # genera in tools/audio/out/sfx/ e verifica
  python -I tools/audio/sfx_gen.py --sheet              # in più la tavola di forme d'onda e spettrogrammi
  python -I tools/audio/sfx_gen.py --install            # copia i file validati in game/assets/sfx/
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402

SR = 44100
PEAK_DBFS = -1.0
ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / "tools" / "audio" / "out" / "sfx"
GAME_SFX = ROOT / "game" / "assets" / "sfx"

# Nomi richiesti dalla specifica (paragrafo 7), nell'ordine della tavola.
NAMES = [
    "whoosh_light", "whoosh_heavy", "hit_light", "hit_medium", "hit_heavy", "hit_kick", "knee",
    "grab", "throw", "body_fall", "body_thud", "step_a", "step_b", "jump", "land", "glint",
    "zap", "bin_hit", "bin_break", "pickup", "ko",
    "ui_move", "ui_confirm", "ui_pause", "go_arrow",
]

# Loudness "veloce" (finestra di 100 ms, pesatura K) a cui portare ogni categoria nel gioco.
# I guadagni risultanti vanno in mix.json; non si alza mai un suono sopra il livello del file.
MIX_TARGET = {
    "hit_light": -11.0, "hit_medium": -10.5, "hit_heavy": -10.0, "hit_kick": -10.0, "knee": -10.5,
    "body_fall": -11.0, "body_thud": -11.5, "ko": -9.5, "bin_hit": -12.0, "bin_break": -11.0,
    "whoosh_light": -18.0, "whoosh_heavy": -17.0, "throw": -15.0, "grab": -16.0, "jump": -19.0,
    "land": -17.0, "step_a": -31.0, "step_b": -31.0, "glint": -14.0, "zap": -13.0,
    "pickup": -15.0, "ui_move": -19.0, "ui_confirm": -17.0, "ui_pause": -17.0, "go_arrow": -16.0,
}

# Import in Godot: PCM 16 bit (non il QOA predefinito), niente loop, niente ritocchi.
# Godot completa da sé uid, percorso e dipendenze alla prima importazione.
IMPORT_TEMPLATE = """[remap]

importer="wav"
type="AudioStreamWAV"

[params]

force/8_bit=false
force/mono=false
force/max_rate=false
force/max_rate_hz=44100
edit/trim=false
edit/normalize=false
edit/loop_mode=1
edit/loop_begin=0
edit/loop_end=-1
compress/mode=0
"""

# Durate ammesse (s): controllo di sanità sui suoni generati.
DUR_RANGE = {
    "step_a": (0.05, 0.15), "step_b": (0.05, 0.15), "ui_move": (0.03, 0.15),
    "ko": (0.8, 1.6), "bin_break": (0.5, 1.2), "glint": (0.35, 1.1), "zap": (0.3, 0.8),
    "bin_hit": (0.2, 0.8), "pickup": (0.2, 0.8), "body_fall": (0.3, 0.9),
}


# ======================================================================= mattoni di sintesi

def n_of(dur: float) -> int:
    return int(round(dur * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def env_exp(n: int, tau: float, delay: float = 0.0) -> np.ndarray:
    """Decadimento esponenziale con costante di tempo tau (s), da 1 al tempo 'delay'."""
    t = tvec(n) - delay
    e = np.exp(-np.maximum(t, 0.0) / tau)
    e[t < 0] = 0.0
    return e


def env_ar(n: int, attack: float, tau: float, delay: float = 0.0) -> np.ndarray:
    """Attacco a mezzo coseno di durata 'attack', poi decadimento esponenziale."""
    t = tvec(n) - delay
    a = np.clip(t / max(attack, 1e-6), 0.0, 1.0)
    rise = 0.5 - 0.5 * np.cos(np.pi * a)
    dec = np.exp(-np.maximum(t - attack, 0.0) / tau)
    e = rise * dec
    e[t < 0] = 0.0
    return e


def env_bell(n: int, rise: float, fall: float, delay: float = 0.0, power: float = 1.0) -> np.ndarray:
    """Inviluppo a campana: sale in 'rise' secondi e scende a zero in 'fall' secondi."""
    t = tvec(n) - delay
    e = np.zeros(n)
    up = (t >= 0) & (t < rise)
    e[up] = np.sin(0.5 * np.pi * t[up] / rise) ** 2
    dn = (t >= rise) & (t < rise + fall)
    e[dn] = np.cos(0.5 * np.pi * (t[dn] - rise) / fall) ** 2
    return e ** power


def glide(n: int, f0: float, f1: float, tau: float) -> np.ndarray:
    """Frequenza che scende (o sale) esponenzialmente da f0 verso f1 con costante tau."""
    return f1 + (f0 - f1) * np.exp(-tvec(n) / tau)


def osc_sine(freq: np.ndarray | float, n: int, phase0: float = 0.0) -> np.ndarray:
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    ph = 2.0 * np.pi * np.cumsum(f) / SR + phase0
    return np.sin(ph)


def osc_fm(fc: np.ndarray | float, ratio: float, index: np.ndarray | float, n: int,
           fb: float = 0.0) -> np.ndarray:
    """FM a due operatori: portante fc, modulante fc*ratio, indice variabile nel tempo.
    'fb' aggiunge una piccola retroazione sulla modulante, come l'operatore 1 dell'YM2612."""
    f = np.broadcast_to(np.asarray(fc, dtype=np.float64), (n,))
    idx = np.broadcast_to(np.asarray(index, dtype=np.float64), (n,))
    pc = 2.0 * np.pi * np.cumsum(f) / SR
    pm = 2.0 * np.pi * np.cumsum(f * ratio) / SR
    if fb > 0.0:
        mod = np.empty(n)
        prev = 0.0
        for i in range(n):  # retroazione: la modulante si modula da sola
            prev = np.sin(pm[i] + fb * prev)
            mod[i] = prev
    else:
        mod = np.sin(pm)
    return np.sin(pc + idx * mod)


def osc_pulse(freq: float, n: int, duty: float = 0.5, fmax: float = 16000.0) -> np.ndarray:
    """Onda rettangolare a banda limitata (serie di Fourier troncata): il tono del PSG."""
    t = tvec(n)
    y = np.zeros(n)
    k = 1
    while k * freq < fmax:
        a = (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty)
        # attenuazione dolce delle armoniche alte per evitare il fenomeno di Gibbs
        g = np.cos(0.5 * np.pi * (k * freq) / fmax) ** 2
        y += a * g * np.cos(2.0 * np.pi * k * freq * t)
        k += 1
    return y - y.mean()


def noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def bp(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, fc, btype="lowpass", fs=SR, output="sos"), x)


def hp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, fc, btype="highpass", fs=SR, output="sos"), x)


def svf_bandpass(x: np.ndarray, fc: np.ndarray, q: float | np.ndarray) -> np.ndarray:
    """Filtro a stato variabile TPT (Zavalishin) con frequenza che cambia a ogni campione:
    resta stabile anche quando la frequenza si muove in fretta (serve ai whoosh)."""
    n = len(x)
    fc = np.clip(np.broadcast_to(np.asarray(fc, dtype=np.float64), (n,)), 20.0, 0.45 * SR)
    qq = np.broadcast_to(np.asarray(q, dtype=np.float64), (n,))
    g = np.tan(np.pi * fc / SR)
    k = 1.0 / qq
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    out = np.empty(n)
    ic1 = ic2 = 0.0
    for i in range(n):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        out[i] = v1
    return out


def sat(x: np.ndarray, drive: float) -> np.ndarray:
    """Saturazione morbida: aggiunge armoniche al corpo grave (si sente anche sugli altoparlanti
    piccoli) e comprime il picco."""
    return np.tanh(drive * x) / np.tanh(drive)


def pcm_crunch(x: np.ndarray, rate: float, bits: int, post_lp: float = 13000.0) -> np.ndarray:
    """Imitazione di un campione PCM del Mega Drive: tenuta a 'rate' Hz (sample-and-hold, con le
    sue immagini acute "granulose"), quantizzazione a 'bits' bit, poi un passa-basso morbido."""
    peak = np.max(np.abs(x)) or 1.0
    y = x / peak
    n = len(y)
    idx = np.floor(np.arange(n) * rate / SR)
    src = np.minimum(np.round(idx * SR / rate).astype(np.int64), n - 1)
    y = y[src]
    levels = 2 ** (bits - 1) - 1
    y = np.round(y * levels) / levels
    return lp(y, post_lp, order=2) * peak


def impulse_tail(x: np.ndarray, tail_s: float, tau: float, lp_hz: float, rng: np.random.Generator,
                 wet: float) -> np.ndarray:
    """Riverbero corto: convoluzione con rumore che decade (risposta all'impulso sintetica)."""
    m = n_of(tail_s)
    ir = rng.standard_normal(m) * env_exp(m, tau)
    ir = lp(ir, lp_hz)
    ir[0] = 0.0
    ir /= np.sqrt(np.sum(ir * ir)) or 1.0
    wetsig = signal.fftconvolve(x, ir)  # lunga len(x) + m - 1
    wetsig = np.concatenate([wetsig, np.zeros(len(x) + m - len(wetsig))])
    dry = np.concatenate([x, np.zeros(m)])
    return dry + wet * wetsig


def place(dst: np.ndarray, src: np.ndarray, at_s: float, gain: float = 1.0) -> None:
    i = n_of(at_s)
    j = min(len(dst), i + len(src))
    if j > i:
        dst[i:j] += gain * src[: j - i]


def norm(x: np.ndarray) -> np.ndarray:
    p = np.max(np.abs(x))
    return x / p if p > 0 else x


# ======================================================================= strati ricorrenti

def layer_transient(n: int, rng: np.random.Generator, hp_hz: float, tau: float, amp: float) -> np.ndarray:
    """Transiente netto: un lampo di rumore acuto di pochi millisecondi."""
    return amp * norm(hp(noise(n, rng), hp_hz, order=2)) * env_exp(n, tau)


def layer_snap(n: int, f0: float, f1: float, tau_f: float, tau_a: float, amp: float) -> np.ndarray:
    """Schiocco intonato: sinusoide che precipita di altezza in pochi ms."""
    return amp * osc_sine(glide(n, f0, f1, tau_f), n) * env_exp(n, tau_a)


def layer_body(n: int, f0: float, f1: float, tau_f: float, tau_a: float, drive: float, amp: float,
               attack: float = 0.0008) -> np.ndarray:
    """Corpo grave del colpo: sinusoide con discesa di altezza, saturata per dare peso.
    La saturazione comprimerebbe anche il decadimento (coda lunga e rimbombante): per questo
    dopo la saturazione si moltiplica ancora per l'inviluppo elevato a 0,6."""
    e = env_ar(n, attack, tau_a)
    b = osc_sine(glide(n, f0, f1, tau_f), n, phase0=0.0) * e
    return amp * sat(b, drive) * e ** 0.6


def layer_noise_band(n: int, rng: np.random.Generator, lo: float, hi: float, attack: float,
                     tau: float, amp: float, delay: float = 0.0, order: int = 2) -> np.ndarray:
    return amp * norm(bp(noise(n, rng), lo, hi, order)) * env_ar(n, attack, tau, delay)


def layer_noise_low(n: int, rng: np.random.Generator, fc: float, attack: float, tau: float,
                    amp: float, delay: float = 0.0) -> np.ndarray:
    return amp * norm(lp(noise(n, rng), fc, order=2)) * env_ar(n, attack, tau, delay)


def crackles(n: int, rng: np.random.Generator, rate_hz: float, decay_s: float, hp_hz: float,
             burst_ms: tuple[float, float] = (0.4, 2.0)) -> np.ndarray:
    """Treno di scariche casuali (processo di Poisson) con densità che cala nel tempo."""
    y = np.zeros(n)
    t = 0.0
    dur = n / SR
    while True:
        t += rng.exponential(1.0 / rate_hz) * np.exp(t / decay_s) ** 0.5
        if t >= dur:
            break
        blen = n_of(rng.uniform(*burst_ms) / 1000.0) + 2
        b = rng.standard_normal(blen) * np.exp(-np.arange(blen) / (blen / 3.0))
        a = rng.uniform(0.3, 1.0) * np.exp(-t / decay_s)
        place(y, a * b, t)
    return hp(y, hp_hz, order=2)


def modal(n: int, freqs: list[float], decays: list[float], amps: list[float],
          rng: np.random.Generator, detune: float = 0.004, delay: float = 0.0) -> np.ndarray:
    """Risonanze di un oggetto metallico: somma di sinusoidi smorzate, ognuna sdoppiata e
    leggermente stonata per avere i battimenti del metallo vero."""
    y = np.zeros(n)
    t = tvec(n) - delay
    on = t >= 0
    for f, d, a in zip(freqs, decays, amps):
        for s in (-1.0, 1.0):
            ff = f * (1.0 + s * detune * rng.uniform(0.5, 1.5))
            ph = rng.uniform(0, 2 * np.pi)
            y[on] += 0.5 * a * np.sin(2 * np.pi * ff * t[on] + ph) * np.exp(-t[on] / d)
    # attacco di 0,3 ms per non partire da un gradino
    y *= np.clip(t / 0.0003, 0.0, 1.0)
    return y


# ======================================================================= i suoni

def s_whoosh(n_dur: float, f_lo: float, f_hi: float, f_end: float, rise: float, fall: float,
             q: float, rng: np.random.Generator, sub: tuple[float, float] | None = None,
             air: float = 0.25) -> np.ndarray:
    n = n_of(n_dur)
    t = tvec(n)
    # traiettoria della frequenza centrale: sale fino al picco dell'inviluppo, poi ridiscende
    pk = rise / n_dur
    u = t / n_dur
    fc = np.where(u < pk, f_lo * (f_hi / f_lo) ** (np.sin(0.5 * np.pi * u / pk)),
                  f_hi * (f_end / f_hi) ** (np.clip((u - pk) / (1 - pk), 0, 1) ** 0.8))
    env = env_bell(n, rise, fall)
    w = svf_bandpass(noise(n, rng), fc, q)
    # strato d'aria più acuto e più stretto, leggermente in ritardo: il "sibilo"
    w2 = svf_bandpass(noise(n, rng), np.minimum(fc * 2.3, 9000.0), q * 1.8)
    y = norm(w) * env + air * norm(w2) * env_bell(n, rise * 1.1, fall * 0.85)
    if sub is not None:
        # spinta grave per i movimenti pesanti
        y += sub[1] * osc_sine(glide(n, sub[0] * 1.6, sub[0], rise), n) * env_bell(n, rise, fall * 0.8)
    return y


def gen_whoosh_light(rng):
    return s_whoosh(0.15, 900.0, 3800.0, 1600.0, 0.038, 0.105, 1.4, rng, air=0.3)


def gen_whoosh_heavy(rng):
    y = s_whoosh(0.30, 300.0, 1700.0, 500.0, 0.085, 0.205, 1.1, rng, sub=(95.0, 0.35), air=0.22)
    return sat(norm(y), 1.4)


def gen_hit_light(rng):
    # Più grave dopo la prova di Luigi (5 novembre 2026: "il suono dei pugni è troppo alto di tono").
    n = n_of(0.16)
    y = (layer_transient(n, rng, 1600.0, 0.0012, 0.7)
         + layer_snap(n, 1500.0, 380.0, 0.004, 0.005, 0.5)
         + layer_body(n, 210.0, 120.0, 0.015, 0.024, 2.5, 0.7)
         # lo "smack": rumore in banda media, è la parte che si sente su qualsiasi altoparlante
         + layer_noise_band(n, rng, 600.0, 2200.0, 0.0006, 0.028, 0.9)
         + layer_noise_low(n, rng, 1000.0, 0.002, 0.040, 0.25))
    return pcm_crunch(sat(y, 1.4), 16000.0, 8)


def gen_hit_medium(rng):
    n = n_of(0.21)
    y = (layer_transient(n, rng, 1300.0, 0.0016, 0.75)
         + layer_snap(n, 1300.0, 300.0, 0.005, 0.007, 0.45)
         + layer_body(n, 175.0, 95.0, 0.022, 0.040, 3.0, 0.85)
         + layer_noise_band(n, rng, 500.0, 1800.0, 0.0008, 0.040, 0.95)
         + layer_noise_low(n, rng, 800.0, 0.003, 0.060, 0.3))
    return pcm_crunch(sat(y, 1.5), 16000.0, 8)


def gen_hit_heavy(rng):
    n = n_of(0.40)
    y = (layer_transient(n, rng, 1400.0, 0.0024, 1.0)
         + layer_snap(n, 2800.0, 300.0, 0.006, 0.010, 0.6)
         + layer_body(n, 200.0, 85.0, 0.035, 0.070, 4.0, 0.9)
         + layer_noise_band(n, rng, 450.0, 2000.0, 0.0010, 0.060, 1.0)
         + layer_noise_low(n, rng, 800.0, 0.004, 0.110, 0.3))
    # scricchiolio a bassa risoluzione sopra il corpo: la "grana" dei colpi pesanti
    grit = pcm_crunch(layer_noise_band(n, rng, 300.0, 1400.0, 0.001, 0.050, 0.5), 8000.0, 5, 6000.0)
    return pcm_crunch(sat(y + grit, 1.6), 15000.0, 8)


def gen_hit_kick(rng):
    n = n_of(0.34)
    y = (layer_transient(n, rng, 1800.0, 0.0020, 0.9)
         + layer_body(n, 210.0, 100.0, 0.030, 0.055, 3.5, 0.8)
         # schiaffo di cuoio: banda media larga e forte, è ciò che distingue il calcio dal pugno
         + layer_noise_band(n, rng, 1000.0, 4500.0, 0.0006, 0.045, 1.0, order=2)
         + layer_noise_band(n, rng, 2500.0, 7000.0, 0.0004, 0.012, 0.4)
         + layer_noise_low(n, rng, 900.0, 0.003, 0.085, 0.25))
    return pcm_crunch(sat(y, 1.5), 17000.0, 8)


def gen_knee(rng):
    n = n_of(0.30)
    y = (layer_transient(n, rng, 1200.0, 0.0018, 0.5)
         + layer_body(n, 170.0, 90.0, 0.025, 0.055, 3.5, 0.9)
         # colpo sordo nella pancia: tanta banda medio-bassa, poco acuto
         + layer_noise_band(n, rng, 350.0, 1500.0, 0.0012, 0.050, 1.15)
         # "uff" dell'aria che esce: rumore a formante intorno a 700 Hz
         + layer_noise_band(n, rng, 520.0, 950.0, 0.006, 0.045, 0.4, delay=0.012, order=3))
    return pcm_crunch(lp(sat(y, 1.6), 5000.0), 14000.0, 8, post_lp=9000.0)


def gen_grab(rng):
    n = n_of(0.17)
    y = (layer_noise_band(n, rng, 2000.0, 7500.0, 0.0015, 0.016, 0.8)
         + layer_noise_band(n, rng, 1600.0, 6000.0, 0.0015, 0.022, 0.55, delay=0.034)
         + layer_noise_band(n, rng, 2500.0, 9000.0, 0.003, 0.018, 0.35, delay=0.07)
         + layer_body(n, 160.0, 120.0, 0.02, 0.022, 1.5, 0.3, attack=0.002))
    return pcm_crunch(y, 20000.0, 10)


def gen_throw(rng):
    y = s_whoosh(0.46, 240.0, 1450.0, 380.0, 0.16, 0.30, 1.0, rng, sub=(70.0, 0.45), air=0.2)
    # secondo strato più lento e scuro: la massa del corpo che gira
    n = len(y)
    y2 = svf_bandpass(noise(n, rng), glide(n, 900.0, 260.0, 0.18), 0.8) * env_bell(n, 0.2, 0.26)
    return sat(norm(y) + 0.6 * norm(y2), 1.3)


def gen_body_fall(rng):
    n = n_of(0.80)
    y = (layer_transient(n, rng, 900.0, 0.003, 0.6)
         + layer_body(n, 135.0, 62.0, 0.04, 0.10, 3.6, 0.9, attack=0.0015)
         + layer_noise_low(n, rng, 1000.0, 0.002, 0.080, 0.6)
         + layer_noise_band(n, rng, 300.0, 1500.0, 0.0015, 0.070, 0.8))
    # rimbalzo più piccolo
    b2 = (layer_body(n, 150.0, 75.0, 0.03, 0.06, 2.8, 0.45, attack=0.0015)
          + layer_noise_band(n, rng, 300.0, 1400.0, 0.0015, 0.045, 0.35))
    place(y, b2, 0.135)
    # asfalto bagnato: schizzi e ghiaia, scariche acute che si diradano
    splash = crackles(n, rng, 420.0, 0.09, 2500.0) * 0.4
    splash += layer_noise_band(n, rng, 2500.0, 8000.0, 0.002, 0.06, 0.2)
    return pcm_crunch(sat(y, 1.5) + splash, 16000.0, 8)


def gen_body_thud(rng):
    n = n_of(0.55)
    y = (layer_transient(n, rng, 700.0, 0.003, 0.4)
         + layer_body(n, 125.0, 62.0, 0.035, 0.080, 4.0, 0.9, attack=0.0012)
         + layer_noise_low(n, rng, 700.0, 0.002, 0.060, 0.6)
         + layer_noise_band(n, rng, 250.0, 1100.0, 0.002, 0.050, 0.85))
    return pcm_crunch(lp(sat(y, 1.6), 4000.0), 14000.0, 8, post_lp=7000.0)


def gen_step(rng, f0: float, band: tuple[float, float]):
    n = n_of(0.095)
    y = (layer_body(n, f0, f0 * 0.68, 0.012, 0.013, 1.6, 0.55, attack=0.0015)
         + layer_noise_band(n, rng, band[0], band[1], 0.0015, 0.015, 0.4)
         # schizzo dell'acqua sull'asfalto
         + 0.25 * crackles(n, rng, 900.0, 0.03, 4000.0, (0.2, 0.8))
         + layer_noise_band(n, rng, 4000.0, 10000.0, 0.002, 0.022, 0.12))
    return pcm_crunch(y, 20000.0, 10)


def gen_step_a(rng):
    return gen_step(rng, 165.0, (1500.0, 5000.0))


def gen_step_b(rng):
    return gen_step(rng, 148.0, (1300.0, 4400.0))


def gen_jump(rng):
    n = n_of(0.21)
    t = tvec(n)
    fc = 500.0 * (2700.0 / 500.0) ** np.clip(t / 0.12, 0, 1) ** 0.7
    air = svf_bandpass(noise(n, rng), fc, 1.6) * env_bell(n, 0.045, 0.15)
    push = layer_noise_band(n, rng, 1800.0, 5200.0, 0.001, 0.010, 0.5)
    tap = layer_body(n, 150.0, 120.0, 0.01, 0.012, 1.4, 0.35)
    return norm(air) * 0.9 + push + tap


def gen_land(rng):
    n = n_of(0.19)
    y = (layer_transient(n, rng, 1500.0, 0.0015, 0.5)
         + layer_body(n, 150.0, 85.0, 0.02, 0.030, 2.2, 0.6)
         + layer_noise_band(n, rng, 700.0, 3200.0, 0.0008, 0.040, 0.85)
         + layer_noise_band(n, rng, 300.0, 900.0, 0.0010, 0.030, 0.4)
         + 0.35 * crackles(n, rng, 700.0, 0.04, 4000.0, (0.2, 0.9))
         + layer_noise_band(n, rng, 4000.0, 9000.0, 0.002, 0.03, 0.2))
    return pcm_crunch(y, 18000.0, 9)


def gen_glint(rng):
    n = n_of(1.05)
    b1 = osc_fm(2637.0, 3.5, 2.4 * env_exp(n, 0.06), n) * env_ar(n, 0.0015, 0.17)
    b2 = osc_fm(3951.0, 1.41, 1.6 * env_exp(n, 0.08), n) * env_ar(n, 0.0015, 0.21)
    b2 = np.concatenate([np.zeros(n_of(0.055)), b2])[:n]
    shimmer = norm(hp(noise(n, rng), 7000.0, 3)) * (0.6 + 0.4 * np.sin(2 * np.pi * 38.0 * tvec(n)))
    shimmer *= env_ar(n, 0.004, 0.11) * 0.16
    y = 0.75 * b1 + 0.6 * b2 + shimmer
    return pcm_crunch(y, 26000.0, 10, post_lp=15000.0)


def gen_zap(rng):
    n = n_of(0.70)
    t = tvec(n)
    # ronzio elettrico: FM aspra con una modulante a 50 Hz di rete, che trema
    jitter = 1.0 + 0.04 * lp(rng.standard_normal(n), 30.0) * 8.0
    buzz = osc_fm(1150.0 * jitter, 0.0983, 7.0 * env_exp(n, 0.25) + 2.0, n)
    buzz *= (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 50.0 * t + rng.uniform(0, 6.28))))
    buzz = bp(buzz, 250.0, 4500.0) * env_ar(n, 0.002, 0.16)
    # scariche secche e sfrigolio dell'arco, a scatti casuali
    crk = crackles(n, rng, 260.0, 0.22, 1800.0, (0.3, 2.5))
    gate = np.repeat(rng.uniform(0, 1, n // 300 + 1) > 0.45, 300)[:n].astype(float)
    gate = lp(gate, 400.0)
    sizzle = norm(bp(noise(n, rng), 3000.0, 9000.0)) * gate * env_ar(n, 0.001, 0.2) * 0.35
    thump = layer_body(n, 160.0, 80.0, 0.02, 0.03, 2.0, 0.5)
    y = 0.6 * norm(buzz) + 0.7 * norm(crk) + sizzle + thump
    return pcm_crunch(y, 11025.0, 7, post_lp=10000.0)


BIN_FREQS = [347.0, 778.0, 1243.0, 1817.0, 2463.0, 3311.0]


def bin_strike(n: int, rng: np.random.Generator, scale: float, amp: float, decay_mul: float,
               delay: float = 0.0) -> np.ndarray:
    fr = [f * scale for f in BIN_FREQS]
    dc = [d * decay_mul for d in (0.26, 0.19, 0.13, 0.095, 0.07, 0.05)]
    am = [1.0, 0.75, 0.55, 0.42, 0.3, 0.2]
    return amp * modal(n, fr, dc, am, rng, delay=delay)


def gen_bin_hit(rng):
    n = n_of(0.75)
    # un bidone di lamiera è smorzato: suona "clank", non come una campana
    y = (bin_strike(n, rng, 1.0, 0.9, 0.55)
         + layer_transient(n, rng, 2000.0, 0.0015, 0.7)
         + layer_body(n, 190.0, 125.0, 0.02, 0.032, 2.0, 0.6)
         + layer_noise_band(n, rng, 2000.0, 6000.0, 0.0005, 0.04, 0.3))
    return pcm_crunch(sat(y, 1.3), 18000.0, 9)


def gen_bin_break(rng):
    n = n_of(1.15)
    y = (bin_strike(n, rng, 0.94, 1.0, 0.9)
         + layer_transient(n, rng, 1500.0, 0.003, 0.9)
         + layer_body(n, 160.0, 70.0, 0.03, 0.07, 2.8, 0.9))
    # lamiera che si accartoccia: piccoli urti casuali che si diradano
    tt = 0.03
    k = 0
    while tt < 0.55:
        place(y, bin_strike(n_of(0.2), rng, rng.uniform(1.05, 1.9), 0.45 * np.exp(-tt / 0.25), 0.35), tt)
        place(y, layer_noise_band(n_of(0.05), rng, 1500.0, 7000.0, 0.0005, 0.008, 0.35 * np.exp(-tt / 0.3)), tt)
        tt += rng.uniform(0.025, 0.07)
        k += 1
    # coperchio che gira e si ferma: colpetti sempre più fitti
    tt, gap = 0.36, 0.085
    while gap > 0.012 and tt < 0.8:
        place(y, bin_strike(n_of(0.08), rng, 2.4, 0.22 * (gap / 0.085) ** 0.5, 0.25), tt)
        tt += gap
        gap *= 0.8
    y += 0.3 * crackles(n, rng, 160.0, 0.25, 2500.0)
    return pcm_crunch(sat(y, 1.4), 16000.0, 9)


def gen_pickup(rng):
    notes = [1318.5, 1661.2, 1975.5, 2637.0]  # Mi6 Sol#6 Si6 Mi7: arpeggio maggiore che sale
    step = 0.042
    n = n_of(step * 3 + 0.62)
    y = np.zeros(n)
    for i, f in enumerate(notes):
        last = i == len(notes) - 1
        m = n_of(0.62 if last else step + 0.02)
        vib = 1.0 + (0.006 * np.sin(2 * np.pi * 7.0 * tvec(m)) if last else 0.0)
        tone = osc_fm(f * vib, 1.0, 1.4 * env_exp(m, 0.05) + 0.4, m)
        tone *= env_ar(m, 0.002, 0.10 if last else 0.035)
        if not last:  # la nota lascia il posto alla successiva senza gradino
            tone *= np.clip((m - np.arange(m)) / n_of(0.004), 0.0, 1.0)
        place(y, tone, i * step, 0.8 if last else 0.7)
    return pcm_crunch(y, 22050.0, 10, post_lp=11000.0)


def gen_ko(rng):
    n = n_of(0.75)
    hit = (layer_transient(n, rng, 1200.0, 0.0035, 1.0)
           + layer_snap(n, 3000.0, 200.0, 0.006, 0.012, 0.5)
           + layer_body(n, 150.0, 40.0, 0.06, 0.16, 4.0, 1.3)
           + layer_noise_band(n, rng, 350.0, 1700.0, 0.001, 0.08, 1.0)
           + layer_noise_low(n, rng, 700.0, 0.004, 0.16, 0.4))
    # boato grave che scende, come un'esplosione lontana
    boom = osc_sine(glide(n, 85.0, 33.0, 0.25), n) * env_ar(n, 0.01, 0.28)
    sweep = svf_bandpass(noise(n, rng), glide(n, 2200.0, 180.0, 0.2), 0.9) * env_ar(n, 0.01, 0.22)
    y = pcm_crunch(sat(hit + 0.8 * sat(boom, 2.0), 1.6), 15000.0, 8) + 0.5 * norm(sweep)
    # coda d'ambiente: la strada sotto la ferrovia rimbomba
    return impulse_tail(y, 0.55, 0.16, 2500.0, rng, wet=0.45)


def gen_ui_move(rng):
    n = n_of(0.13)
    return osc_pulse(1046.5, n, 0.5) * env_ar(n, 0.0015, 0.018)


def gen_ui_confirm(rng):
    n = n_of(0.45)
    y = np.zeros(n)
    m1 = n_of(0.065)
    t1 = osc_fm(784.0, 1.0, 1.2, m1) * env_ar(m1, 0.002, 0.04)
    t1 *= np.clip((m1 - np.arange(m1)) / n_of(0.004), 0.0, 1.0)
    place(y, t1, 0.0, 0.8)
    m2 = n_of(0.39)
    place(y, osc_fm(1568.0, 1.0, 1.4 * env_exp(m2, 0.06) + 0.3, m2) * env_ar(m2, 0.002, 0.06), 0.055, 0.9)
    return y


def gen_ui_pause(rng):
    n = n_of(0.55)
    y = np.zeros(n)
    for at, f, tau, dur in ((0.0, 1318.5, 0.04, 0.07), (0.065, 987.8, 0.04, 0.07), (0.13, 1318.5, 0.07, 0.42)):
        m = n_of(dur)
        tone = osc_pulse(f, m, 0.25) * env_ar(m, 0.0015, tau)
        if dur < 0.1:
            tone *= np.clip((m - np.arange(m)) / n_of(0.004), 0.0, 1.0)
        place(y, tone, at, 0.8)
    return y


def gen_go_arrow(rng):
    n = n_of(0.45)
    y = np.zeros(n)
    for at, hold in ((0.0, 0.085), (0.13, 0.30)):
        m = n_of(hold)
        tone = 0.65 * osc_pulse(1760.0, m, 0.5) + 0.35 * osc_fm(1760.0, 2.0, 1.0, m)
        # il primo bip si chiude in 4 ms, il secondo si spegne da solo
        cut = np.clip((m - np.arange(m)) / n_of(0.004), 0.0, 1.0)
        place(y, tone * env_ar(m, 0.002, 0.045) * cut, at)
    return lp(y, 9000.0)


GENERATORS = {name: globals()["gen_" + name] for name in NAMES}


# ======================================================================= finitura e controlli

def finish(name: str, x: np.ndarray, fade_in_ms: float = 1.0, fade_out_ms: float = 8.0) -> np.ndarray:
    """Passa-alto a 30 Hz, via la media, dissolvenze a coseno, picco a -1 dBFS, taglio del silenzio
    in coda (sotto -66 dB dal picco), così il file non porta code inutili."""
    y = hp(np.asarray(x, dtype=np.float64), 30.0, order=2)
    y = y - y.mean()
    p = np.max(np.abs(y))
    if p <= 0:
        raise ValueError(f"{name}: silenzio")
    y /= p
    # coda: taglia dopo l'ultimo campione sopra -66 dB, più 10 ms per la dissolvenza
    above = np.nonzero(np.abs(y) > 10 ** (-66 / 20))[0]
    end = min(len(y), above[-1] + n_of(0.010)) if len(above) else len(y)
    y = y[:end]
    fi = max(2, n_of(fade_in_ms / 1000.0))
    fo = max(2, n_of(fade_out_ms / 1000.0))
    y[:fi] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(fi) / fi)
    y[-fo:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, fo + 1) / fo)
    y = y - y.mean() * np.hanning(len(y)) / np.hanning(len(y)).mean()  # media nulla senza gradini
    y *= al.from_db(PEAK_DBFS) / np.max(np.abs(y))
    return y


def small_speaker_loudness(x: np.ndarray) -> float:
    """Loudness veloce dopo un passa-alto a 200 Hz: quanto si sente su un portatile."""
    return fast_loudness(hp(x, 200.0, order=4))


def fast_loudness(x: np.ndarray) -> float:
    """Loudness pesata K su finestre di 100 ms (massimo): misura la forza percepita dei suoni brevi."""
    z = al._block_powers(x, SR, 0.1, 0.005)
    return float(-0.691 + 10.0 * np.log10(max(z.max(), 1e-20)))


def features(x: np.ndarray) -> np.ndarray:
    """Impronta per confrontare i suoni: spettro medio in 24 bande logaritmiche + inviluppo."""
    spec = np.abs(np.fft.rfft(x, n=16384)) ** 2
    f = np.fft.rfftfreq(16384, 1 / SR)
    edges = np.geomspace(40, 16000, 25)
    bands = np.array([spec[(f >= a) & (f < b)].sum() for a, b in zip(edges[:-1], edges[1:])])
    bands = 10 * np.log10(bands / bands.sum() + 1e-9)
    _, env = al.rms_envelope(x, SR, 0.01)
    env = np.pad(env, (0, max(0, 60 - len(env))))[:60]
    env = 20 * np.log10(env / env.max() + 1e-4)
    return np.concatenate([bands / 3.0, env / 6.0])


def check(name: str, x: np.ndarray) -> list[str]:
    errs = []
    peak = al.sample_peak_db(x)
    if abs(peak - PEAK_DBFS) > 0.05:
        errs.append(f"picco {peak:.2f} dBFS")
    if abs(x.mean()) > 1e-4:
        errs.append(f"componente continua {x.mean():.2e}")
    if abs(x[0]) > 1e-3 or abs(x[-1]) > 1e-3:
        errs.append(f"estremi non nulli ({x[0]:.4f}, {x[-1]:.4f})")
    jump = np.max(np.abs(np.diff(x[: n_of(0.0005)]))) if len(x) > 30 else 0
    if jump > 0.35:
        errs.append(f"gradino iniziale {jump:.2f}")
    lo, hi = DUR_RANGE.get(name, (0.05, 0.7))
    d = len(x) / SR
    if not lo <= d <= hi:
        errs.append(f"durata {d:.3f} s fuori da [{lo}, {hi}]")
    if not np.all(np.isfinite(x)):
        errs.append("valori non finiti")
    # livello nei 10 ms subito prima della dissolvenza finale: se è alto, il suono è stato
    # troncato invece di spegnersi da solo
    tail = x[-n_of(0.020):-n_of(0.010)]
    tail_db = float(al.db(np.sqrt(np.mean(tail * tail)) / np.max(np.abs(x))))
    if tail_db > -36.0:
        errs.append(f"coda troncata ({tail_db:.0f} dB dal picco)")
    return errs


def render_all() -> dict[str, np.ndarray]:
    out = {}
    for i, name in enumerate(NAMES):
        rng = np.random.default_rng(20261103 + 7919 * i)  # seme fisso per ogni suono
        raw = GENERATORS[name](rng)
        fade_in = 1.0 if name not in ("whoosh_light", "whoosh_heavy", "throw", "jump", "glint") else 2.0
        out[name] = finish(name, raw, fade_in_ms=fade_in, fade_out_ms=10.0 if name != "ko" else 25.0)
    return out


def write_sheet(sounds: dict[str, np.ndarray], stats: dict, path: Path, zoom_path: Path) -> None:
    """Tavola: per ogni suono forma d'onda (sopra) e spettrogramma 0-16 kHz in scala logaritmica."""
    from PIL import Image, ImageDraw, ImageFont
    cols, cw, chh = 5, 300, 250
    wh, sh = 70, 140
    rows = (len(sounds) + cols - 1) // cols
    img = Image.new("RGB", (cols * cw, rows * chh), (14, 12, 26))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=12)
    except TypeError:
        font = ImageFont.load_default()
    stops = np.array([[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66],
                      [245, 125, 21], [250, 193, 39], [252, 255, 164]], dtype=float)
    lut = np.array([np.interp(np.linspace(0, 1, 256), np.linspace(0, 1, len(stops)), stops[:, c])
                    for c in range(3)]).T.astype(np.uint8)
    tmax = max(len(v) for v in sounds.values()) / SR
    for k, (name, x) in enumerate(sounds.items()):
        ox, oy = (k % cols) * cw, (k // cols) * chh
        s = stats[name]
        d.text((ox + 6, oy + 4), f"{name}  {s['dur_s']*1000:.0f} ms", fill=(255, 240, 200), font=font)
        d.text((ox + 6, oy + 18), f"pk {s['peak_dbfs']:.1f}  rms {s['rms_dbfs']:.1f}  F {s['fast_lufs']:.1f}  c {s['centroid_hz']:.0f}Hz",
               fill=(170, 200, 255), font=font)
        # scala del tempo comune a tutti i suoni (così le durate si confrontano a occhio)
        w = cw - 12
        x0, y0 = ox + 6, oy + 34
        d.rectangle([x0, y0, x0 + w, y0 + wh], outline=(60, 60, 90))
        npx = max(1, int(w * (len(x) / SR) / tmax))
        seg = np.array_split(x, npx)
        for i, sg in enumerate(seg):
            a, b = sg.min(), sg.max()
            d.line([x0 + i, y0 + wh / 2 - b * wh / 2, x0 + i, y0 + wh / 2 - a * wh / 2], fill=(120, 230, 255))
        f, t, S = al.spectrogram_db(x, SR, 512, 64)
        S = np.clip((S - S.max() + 80) / 80, 0, 1)
        fy = np.geomspace(60, 16000, sh)[::-1]
        rows_idx = np.searchsorted(f, fy).clip(0, len(f) - 1)
        S2 = S[rows_idx, :]
        tx = int(w * (len(x) / SR) / tmax)
        tx = max(1, tx)
        col_idx = np.linspace(0, S2.shape[1] - 1, tx).astype(int)
        S3 = (S2[:, col_idx] * 255).astype(np.uint8)
        im = Image.fromarray(lut[S3])
        y1 = y0 + wh + 6
        img.paste(im, (x0, y1))
        d.rectangle([x0, y1, x0 + w, y1 + sh], outline=(60, 60, 90))
        for hz, lab in ((100, "100"), (1000, "1k"), (10000, "10k")):
            yy = y1 + int(np.interp(np.log(hz), np.log(fy[::-1]), np.arange(sh)[::-1]))
            d.text((x0 + w - 24, yy - 6), lab, fill=(200, 200, 200), font=font)
    img.save(path)
    # zoom: i primi 25 ms e gli ultimi 25 ms di ogni suono, per vedere attacchi e chiusure
    zc, zw, zh = 5, 300, 120
    zimg = Image.new("RGB", (zc * zw, rows * zh), (14, 12, 26))
    zd = ImageDraw.Draw(zimg)
    m = n_of(0.025)
    for k, (name, x) in enumerate(sounds.items()):
        ox, oy = (k % zc) * zw, (k // zc) * zh
        zd.text((ox + 6, oy + 2), f"{name}: inizio | fine (25 ms)", fill=(255, 240, 200), font=font)
        for j, part in enumerate((x[:m], x[-m:])):
            bx, by, bw, bh = ox + 6 + j * 146, oy + 18, 140, zh - 26
            zd.rectangle([bx, by, bx + bw, by + bh], outline=(60, 60, 90))
            zd.line([bx, by + bh / 2, bx + bw, by + bh / 2], fill=(50, 50, 70))
            pts = [(bx + i * bw / (len(part) - 1), by + bh / 2 - v * bh / 2) for i, v in enumerate(part)]
            zd.line(pts, fill=(120, 230, 255))
    zimg.save(zoom_path)


def install(src: Path, dst: Path) -> None:
    """Copia in game/assets/sfx con nome temporaneo e poi rinomina: chi importa non vede mai
    un file a metà."""
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.iterdir()
                   if p.suffix == ".wav" or p.name.endswith(".wav.import") or p.name == "mix.json")
    tmp = []
    for p in files:
        t = dst / (p.name + ".tmp_install")
        shutil.copyfile(p, t)
        tmp.append((t, dst / p.name))
    for t, final in tmp:
        os.replace(t, final)
    print(f"installati {len(tmp)} file in {dst}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--sheet", action="store_true", help="scrive la tavola e lo zoom in --out")
    ap.add_argument("--install", action="store_true", help="copia in game/assets/sfx dopo i controlli")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sounds = render_all()
    stats, problems, mix = {}, [], {}
    for name, x in sounds.items():
        errs = check(name, x)
        if errs:
            problems.append(f"{name}: " + "; ".join(errs))
        fl = fast_loudness(x)
        gain = min(0.0, round((MIX_TARGET[name] - fl) * 2) / 2)
        mix[name] = gain
        stats[name] = {
            "dur_s": round(len(x) / SR, 4), "peak_dbfs": round(al.sample_peak_db(x), 2),
            "true_peak_dbtp": round(al.true_peak_db(x), 2),
            "rms_dbfs": round(float(al.db(np.sqrt(np.mean(x * x)))), 2), "fast_lufs": round(fl, 2),
            "momentary_lufs": round(al.momentary_max(x, SR), 2),
            "small_speaker_lufs": round(small_speaker_loudness(x), 2),
            "centroid_hz": round(al.spectral_centroid(x, SR)), "dc": float(x.mean()),
            "mix_db": gain,
        }
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(IMPORT_TEMPLATE, encoding="utf-8", newline="\n")
    # i suoni devono essere diversi fra loro: distanza fra le impronte, vicino più prossimo
    feats = {k: features(v) for k, v in sounds.items()}
    names = list(feats)
    dist = np.array([[np.sqrt(np.mean((feats[p] - feats[q]) ** 2)) for q in names] for p in names])
    np.fill_diagonal(dist, np.inf)
    print(f"{'suono':13s} {'ms':>5s} {'picco':>6s} {'TP':>6s} {'RMS':>6s} {'F100':>6s} {'>200':>6s} {'M400':>6s} {'centr':>6s} {'mix':>5s}  vicino più simile")
    for i, name in enumerate(names):
        s = stats[name]
        j = int(np.argmin(dist[i]))
        stats[name]["nearest"] = names[j]
        stats[name]["nearest_dist"] = round(float(dist[i, j]), 3)
        print(f"{name:13s} {s['dur_s']*1000:5.0f} {s['peak_dbfs']:6.2f} {s['true_peak_dbtp']:6.2f} {s['rms_dbfs']:6.1f} "
              f"{s['fast_lufs']:6.1f} {s['small_speaker_lufs']:6.1f} {s['momentary_lufs']:6.1f} {s['centroid_hz']:6.0f} {s['mix_db']:5.1f}  {names[j]} ({dist[i, j]:.2f})")
    pairs = sorted(((dist[i, j], names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))))
    print("coppie più simili:", ", ".join(f"{p}~{q} {d:.2f}" for d, p, q in pairs[:6]))
    for d_, p, q in pairs:
        if d_ < 0.6 and {p, q} != {"step_a", "step_b"}:
            problems.append(f"{p} e {q} troppo simili ({d_:.2f})")
    mix_doc = {"format": 1, "comment": "Guadagno di missaggio in dB per ogni effetto (generato da tools/audio/sfx_gen.py).",
               "gain_db": mix}
    (a.out / "mix.json").write_text(json.dumps(mix_doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (a.out / "report.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if a.sheet:
        write_sheet(sounds, stats, a.out / "tavola_sfx.png", a.out / "tavola_sfx_zoom.png")
        print("tavole:", a.out / "tavola_sfx.png", a.out / "tavola_sfx_zoom.png")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"OK: {len(sounds)} suoni in {a.out}")
    if a.install:
        install(a.out, GAME_SFX)
    return 0


if __name__ == "__main__":
    sys.exit(main())
