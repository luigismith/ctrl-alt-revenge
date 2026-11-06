#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Analizza il WAV registrato da Movie Maker con la scena di prova dell'audio
(tools/audio/godot_tests/audio_test.gd) e controlla che Music e Sfx facciano quello che devono.

Metodo: gli OGG del laboratorio si decodificano e si ricampionano a 48 kHz (la frequenza di
Movie Maker); per ogni finestra della registrazione si cerca per correlazione la posizione nel
brano, poi si stima per minimi quadrati quanto pesano la base e lo strato arena in ogni
finestra di 20 ms (guadagni nel tempo). Così si vedono le dissolvenze, il duck, lo strato e il
punto esatto in cui il loop riparte.

Controlli:
  - la musica parte con la dissolvenza di 0,5 s e arriva al guadagno atteso (bus Music -6 dB);
  - al giunto del loop la posizione torna indietro esattamente di (fine - inizio) campioni, il
    segnale resta continuo (residuo del modello, indici di salto e di energia acuta) e lo strato
    acceso riparte insieme alla base;
  - lo strato arena entra ed esce con rampe regolari di 0,8 s; il duck vale -10 dB;
  - il jingle suona per intero una volta sola e poi c'è silenzio;
  - gli effetti a sinistra, a destra e al centro hanno il pan atteso.

  python -I tools/audio/analyze_capture.py <f.wav> <output di Godot (.out)> [--png tavola.png] [--json r.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402

LAB = Path(os.environ.get("CAR_LAB", Path(os.environ.get("USERPROFILE", str(Path.home()))) / "ctrlaltrevenge-lab"))
EXE = ".exe" if os.name == "nt" else ""  # sul Mac gli eseguibili non hanno estensione
FFMPEG = LAB / "tools" / "ffmpeg" / "bin" / ("ffmpeg" + EXE)
ROOT = Path(__file__).resolve().parents[2]
SR = 48000
FPS = 60


def decode(path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    """Decodifica con ffmpeg: (originale, ricampionato a 48 kHz con filtro polifase, frequenza)."""
    out = Path(os.environ.get("TEMP", ".")) / (path.stem + "_analisi.wav")
    subprocess.run([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                    "-c:a", "pcm_f32le", str(out)], check=True, timeout=600)
    x, sr = al.read_wav(out)
    out.unlink(missing_ok=True)
    x = al.as_2d(x)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    g = np.gcd(SR, sr)
    return x, signal.resample_poly(x, SR // g, sr // g, axis=0), sr


def catmull(x: np.ndarray, s: np.ndarray) -> np.ndarray:
    """Interpolazione cubica di Hermite (Catmull-Rom) alle posizioni frazionarie s, con le stesse
    formule di AudioStreamPlaybackResampled di Godot: serve a confrontare la registrazione con
    ciò che Godot produce davvero (il cubico attenua un po' gli acuti)."""
    i = np.floor(s).astype(np.int64)
    i = np.clip(i, 1, len(x) - 3)
    mu = (s - i)[:, None]
    y0, y1, y2, y3 = x[i - 1], x[i], x[i + 1], x[i + 2]
    mu2 = mu * mu
    h11 = mu2 * (mu - 1)
    z = mu2 - h11
    h01 = z - h11
    h10 = mu - z
    return y1 + (y2 - y1) * h01 + ((y2 - y0) * h10 + (y3 - y1) * h11) * 0.5


def best_lag(cap: np.ndarray, ref: np.ndarray, t: int, guess: int, radius: int, win: int) -> tuple[int, float]:
    """Posizione nel riferimento (vicino a 'guess') che somiglia di più a cap[t:t+win]."""
    a = cap[t:t + win].mean(axis=1)
    lo = max(0, guess - radius)
    hi = min(len(ref) - win, guess + radius)
    if hi <= lo or not np.any(a):
        return guess, 0.0
    seg = ref[lo:hi + win].mean(axis=1)
    c = signal.correlate(seg, a, mode="valid")
    cs = np.concatenate([[0.0], np.cumsum(seg * seg)])
    e = cs[win:] - cs[:-win]
    ncc = c / np.sqrt(np.maximum(e * np.dot(a, a), 1e-30))
    ncc[e < 1e-3 * max(e.max(), 1e-30)] = 0.0  # tratti quasi muti del riferimento: non contano
    k = int(np.argmax(ncc))
    return lo + k, float(ncc[k])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", type=Path)
    ap.add_argument("log", type=Path)
    ap.add_argument("--music-dir", type=Path, default=LAB / "music")
    ap.add_argument("--sfx-dir", type=Path, default=ROOT / "tools" / "audio" / "out" / "sfx")
    ap.add_argument("--png", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()

    sr, raw = wavfile.read(str(a.capture))
    assert sr == SR, f"registrazione a {sr} Hz"
    cap = raw.astype(np.float64) / (2147483648.0 if raw.dtype == np.int32 else 32768.0)
    text = a.log.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"AUDIO_TEST music_dir=.* loop_start_sample=(\d+) loop_end_sample=(\d+) sample_rate=(\d+) "
                  r"seek_mid=([\d.]+) seek_end=([\d.]+)", text)
    S, E, src_sr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    seek_mid, seek_end = float(m.group(4)), float(m.group(5))
    events = [(int(t) / FPS, name) for t, name in re.findall(r"AUDIO_TEST tick=(\d+) (\w+)", text)]
    when = {}
    for t, name in events:
        when.setdefault(name, []).append(t)
    manifest = json.loads((a.music_dir / "music.json").read_text(encoding="utf-8"))
    tracks = {t["id"]: t for t in manifest["tracks"]}
    mix = json.loads((a.sfx_dir / "mix.json").read_text(encoding="utf-8"))["gain_db"]
    r = SR / src_sr
    S48, E48 = S * r, E * r
    # Godot avanza nel file di floor(44100/48000 * 65536) / 65536 campioni per campione d'uscita:
    # leggermente meno del rapporto esatto, quindi la posizione "scivola" di circa 0,16 campioni
    # al secondo. Le posizioni si esprimono come (t * K + scostamento), con K questa pendenza.
    K = (np.floor(src_sr / SR * 65536) / 65536) / (src_sr / SR)
    music_gain = float(al.from_db(-6.0))  # bus Music
    results: dict = {"capture_s": len(cap) / SR}
    problems: list[str] = []
    print(f"registrazione: {len(cap) / SR:.3f} s, picco {al.sample_peak_db(cap):.2f} dBFS")

    B44, B, _ = decode(a.music_dir / tracks["stage1"]["file"])
    A44, A, _ = decode(a.music_dir / tracks["stage1"]["layers"][0]["file"])
    J44, J, j_sr = decode(a.music_dir / tracks["clear"]["file"])

    t_play = when["play_stage1"][0]
    t_mid, t_end = when["seek_mid"][0], when["seek_end"][0]
    t_on1, t_on2 = when["layer_on"]
    t_off = when["layer_off"][0]
    t_don, t_doff = when["duck_on"][0], when["duck_off"][0]
    t_j = when["jingle"][0]

    # ---------------------------------------------------------------- posizione nel brano
    win = 4800
    s_mid, s_end, s_j = int(t_mid * SR), int(t_end * SR), int(t_j * SR)
    seam_guess = s_end + (E48 - seek_end * SR) / K
    pos = []
    for t in range(int(0.55 * SR), s_j, win):
        if abs(t - s_mid) < 2 * win or abs(t - s_end) < 2 * win:
            continue
        if t < s_mid:
            guess = t
        elif t < s_end:
            guess = int(seek_mid * SR + (t - s_mid))
        else:
            guess = int(seek_end * SR + (t - s_end))
        cands = [best_lag(cap, B, t, guess, 6000, win)]
        if t > s_end:  # dopo il giunto il brano riparte dall'inizio del loop
            cands.append(best_lag(cap, B, t, int(S48 + (t - seam_guess)), 6000, win))
        p, q = max(cands, key=lambda c: c[1])
        pos.append((t, p, q))
    pos = np.array(pos)
    off = pos[:, 1] - pos[:, 0] * K
    good = pos[:, 2] > 0.8
    seg_pre = np.median(off[good & (pos[:, 0] < s_mid)])
    seg_mid = np.median(off[good & (pos[:, 0] > s_mid) & (pos[:, 0] < s_end)])
    tail = good & (pos[:, 0] > s_end)
    off_pre = np.median(off[tail & (off > (E48 - seam_guess) - 1000)])   # tra il seek e il giunto
    off_post = np.median(off[tail & (off < (E48 - seam_guess) - 1000)])  # dopo il giunto
    jump = off_pre - off_post
    want = E48 - S48
    t_seam = (E48 - off_pre) / K
    results.update({"loop_jump_samples48": float(jump), "loop_jump_expected48": float(want),
                    "seam_time_s": float(t_seam / SR)})
    print(f"posizioni: {int(good.sum())} finestre su {len(pos)} riconosciute (somiglianza > 0,8)")
    print(f"giunto del loop a {t_seam / SR:.4f} s: la posizione torna indietro di {jump:.1f} campioni a 48 kHz "
          f"(atteso {want:.1f}, differenza {jump - want:+.1f})")
    if abs(jump - want) > 2.0:
        problems.append(f"salto del loop sbagliato di {jump - want:+.1f} campioni")

    # rifinitura sotto il campione: mezzo campione a 48 kHz sfasa di 36 gradi un suono a 10 kHz
    # (il charleston dello strato), quindi ogni tratto si allinea cercando lo scostamento
    # frazionario che rende minimo il residuo del modello base + strato
    def refine(off0: float, t_from: float, t_to: float) -> float:
        starts = np.linspace(t_from, t_to - 0.03, 12)
        best = (np.inf, 0.0)
        for delta in np.linspace(-0.8, 0.8, 33):
            tot = 0.0
            for ts_ in starts:
                tt = np.arange(int(ts_ * SR), int(ts_ * SR) + 960)
                sp = (tt * K + off0 + delta) / r
                X = np.stack([catmull(B44, sp).ravel(), catmull(A44, sp).ravel()], axis=1)
                y = cap[tt[0]:tt[-1] + 1].ravel()
                c, *_ = np.linalg.lstsq(X, y, rcond=None)
                tot += float(np.sum((y - X @ c) ** 2))
            if tot < best[0]:
                best = (tot, delta)
        return off0 + best[1]

    seg_pre = refine(seg_pre, t_play + 0.6, t_mid - 0.05)
    seg_mid = refine(seg_mid, t_mid + 0.1, t_end - 0.05)
    off_pre = refine(off_pre, t_end + 0.1, t_seam / SR - 0.05)
    off_post = refine(off_post, t_seam / SR + 0.05, t_j - 0.05)
    jump = off_pre - off_post
    t_seam = (E48 - off_pre) / K
    results.update({"loop_jump_samples48": float(jump), "seam_time_s": float(t_seam / SR)})
    print(f"allineamento sotto il campione: salto del loop {jump:.2f} (atteso {want:.2f}, differenza "
          f"{jump - want:+.2f} campioni a 48 kHz = {(jump - want) / r:+.2f} campioni del file)")
    if abs(jump - want) > 1.0:
        problems.append(f"salto del loop sbagliato di {jump - want:+.2f} campioni")

    def ref_pos(tt: np.ndarray) -> np.ndarray:
        tk = tt * K
        p = np.where(tt < s_mid, tk + seg_pre, tk + seg_mid)
        p = np.where(tt >= s_end, tk + off_pre, p)
        return np.where(tt >= t_seam, tk + off_post, p)

    # ---------------------------------------------------------------- dove parte il jingle
    Jp = np.concatenate([np.zeros((SR, 2)), J, np.zeros((SR, 2))])
    probe = s_j + int(0.5 * SR)
    pj, qj = best_lag(cap, Jp, probe, int(1.5 * SR), SR, 9600)
    j_start = probe - (pj - SR)
    jbest = (np.inf, 0.0)
    for delta in np.linspace(-0.8, 0.8, 33):
        tot = 0.0
        for ts_ in np.linspace(0.3, len(J) / SR - 0.3, 10):
            tt = np.arange(j_start + int(ts_ * SR), j_start + int(ts_ * SR) + 960)
            ref = catmull(J44, (tt - j_start - delta) * (j_sr / SR))
            y = cap[tt[0]:tt[-1] + 1]
            gg = float(np.dot(ref.ravel(), y.ravel()) / max(np.dot(ref.ravel(), ref.ravel()), 1e-20))
            tot += float(np.sum((y - gg * ref) ** 2))
        if tot < jbest[0]:
            jbest = (tot, delta)
    j_frac = j_start + jbest[1]

    # ---------------------------------------------------------------- guadagni nel tempo
    # modello di ogni finestra di 20 ms: registrazione = gb * base + ga * strato + gj * jingle,
    # con i riferimenti interpolati come fa Godot (Catmull-Rom sui campioni a 44,1 kHz)
    gw = 960
    rows = []
    for t0 in range(0, min(len(cap), j_start + len(J)) - gw, gw):
        tt = np.arange(t0, t0 + gw)
        y = cap[t0:t0 + gw].ravel()
        cols, names = [], []
        if t0 < s_j + int(0.6 * SR):
            p = ref_pos(tt)
            if np.any(p < 0) or np.any(p >= len(B) - 4):
                continue
            sp = p / r
            cols += [catmull(B44, sp).ravel(), catmull(A44, sp).ravel()]
            names += ["b", "a"]
        if t0 + gw > j_start:
            sj = (tt - j_frac) * (j_sr / SR)
            jw = np.where((sj >= 1)[:, None] & (sj < len(J44) - 3)[:, None], catmull(J44, np.clip(sj, 1, len(J44) - 4)), 0.0)
            cols.append(jw.ravel())
            names.append("j")
        if not cols:
            continue
        X = np.stack(cols, axis=1)
        en = np.einsum("ij,ij->j", X, X)
        keep = en >= 1e-3 * max(en.max(), 1e-20)  # riferimento muto in questa finestra: non stimabile
        coef = np.full(len(names), np.nan)
        if keep.any():
            c, *_ = np.linalg.lstsq(X[:, keep], y, rcond=None)
            coef[keep] = c
            res = y - X[:, keep] @ c
        else:
            res = y
        g = dict(zip(names, coef))
        rows.append((t0 / SR, g.get("b", np.nan), g.get("a", np.nan), g.get("j", np.nan),
                     float(np.sqrt(np.mean(res ** 2))), float(np.sqrt(np.mean(y ** 2)))))
    G = np.array(rows)
    tg, gb, ga, gj = G[:, 0], G[:, 1] / music_gain, G[:, 2] / music_gain, G[:, 3] / music_gain
    res_rel = G[:, 4] / np.maximum(G[:, 5], 1e-9)

    def span(t0: float, t1: float) -> np.ndarray:
        return (tg >= t0) & (tg < t1)

    def med(col: np.ndarray, t0: float, t1: float) -> float:
        v = col[span(t0, t1)]
        v = v[np.isfinite(v)]
        return float(np.median(v)) if len(v) else float("nan")

    steady = med(gb, t_play + 0.6, t_mid - 0.05)
    print(f"base a regime: {steady:.4f} del pieno (bus Music -6 dB = {music_gain:.4f})")
    results["base_gain_rel"] = steady
    if abs(steady - 1) > 0.05:
        problems.append(f"guadagno della base {steady:.3f}")
    fade_in = gb[span(t_play, t_play + 0.5)]
    print("dissolvenza iniziale (20 ms):", " ".join(f"{v:.2f}" for v in fade_in))
    if np.any(np.diff(fade_in) < -0.03) or fade_in[-1] < 0.85 or fade_in[0] > 0.15:
        problems.append("dissolvenza iniziale irregolare")

    def ramp(t0: float, rising: bool, label: str) -> np.ndarray:
        v = ga[span(t0 - 0.04, t0 + 0.9)]
        fin = v[np.isfinite(v)]
        print(f"rampa di {label} ({len(fin)}/{len(v)} finestre stimabili):", " ".join(f"{x:.2f}" for x in v))
        if len(fin) < 0.7 * len(v):
            problems.append(f"rampa di {label}: strato poco stimabile")
            return v
        tv = tg[span(t0 - 0.04, t0 + 0.9)]
        inside = np.isfinite(v) & (tv > t0 + 0.06) & (tv < t0 + 0.74)
        slope, icpt = np.polyfit(tv[inside], v[inside], 1)
        dev = v[inside] - (slope * tv[inside] + icpt)
        want_slope = (1.0 if rising else -1.0) / 0.8
        t_half = (0.5 - icpt) / slope - t0
        print(f"   retta: pendenza {slope:+.3f}/s (attesa {want_slope:+.3f}), metà a {t_half:.3f} s dal comando, "
              f"scarto quadratico {np.sqrt(np.mean(dev ** 2)):.3f}")
        if abs(slope / want_slope - 1) > 0.15 or not 0.3 < t_half < 0.5 or np.sqrt(np.mean(dev ** 2)) > 0.08:
            problems.append(f"rampa di {label} non lineare in 0,8 s")
        if rising and (fin[0] > 0.1 or fin[-1] < 0.9):
            problems.append(f"rampa di {label}: non va da 0 a 1")
        if not rising and (fin[0] < 0.85 or fin[-1] > 0.1):
            problems.append(f"rampa di {label}: non va da 1 a 0")
        return v

    up = ramp(t_on1, True, "accensione")
    dn = ramp(t_off, False, "spegnimento")
    lay_on = med(ga, t_on1 + 1.0, t_off - 0.05)
    lay_off = med(ga, t_off + 1.0, t_don - 0.05)
    print(f"strato arena acceso: {lay_on:.3f} del pieno; spento: {lay_off:.3f}")
    results.update({"layer_on": lay_on, "layer_off": lay_off})
    if abs(lay_on - 1) > 0.06 or abs(lay_off) > 0.03:
        problems.append("livelli dello strato non attesi")
    ducked = med(gb, t_don + 0.4, t_doff - 0.05)
    back = med(gb, t_doff + 0.4, t_on2 - 0.05)
    print(f"duck: {al.db(ducked):.2f} dB (atteso -10); dopo: {al.db(back):+.2f} dB")
    results.update({"duck_db": float(al.db(ducked)), "after_duck_db": float(al.db(back))})
    if abs(al.db(ducked) + 10) > 0.6 or abs(al.db(back)) > 0.4:
        problems.append("duck non a -10 dB")
    # strato acceso attraverso il giunto: deve ripartire insieme alla base
    before = med(ga, t_end + 0.3, t_seam / SR - 0.05)
    after = med(ga, t_seam / SR + 0.05, t_j - 0.05)
    n_after = int(np.isfinite(ga[span(t_seam / SR + 0.05, t_j - 0.05)]).sum())
    print(f"strato acceso prima del giunto {before:.3f}, dopo {after:.3f} ({n_after} finestre stimabili)")
    results.update({"layer_before_seam": before, "layer_after_seam": after})
    if abs(before - 1) > 0.06 or abs(after - 1) > 0.06 or n_after < 20:
        problems.append("lo strato non riparte in sincrono con la base")
    # residuo del modello: un click o un loop sbagliato si vedrebbero come un picco
    near = np.abs(tg - t_seam / SR) < 0.05
    far = (tg > t_play + 0.6) & (tg < t_j) & (np.abs(tg - t_seam / SR) > 0.2) \
        & (np.abs(tg - t_mid) > 0.2) & (np.abs(tg - t_end) > 0.2)
    print(f"residuo relativo del modello: mediano {np.median(res_rel[far]):.3f}, 99° percentile "
          f"{np.percentile(res_rel[far], 99):.3f}; al giunto {np.max(res_rel[near]):.3f}")
    results.update({"residual_median": float(np.median(res_rel[far])), "residual_at_seam": float(np.max(res_rel[near]))})
    if np.max(res_rel[near]) > max(2.0 * np.median(res_rel[far]), np.percentile(res_rel[far], 99)):
        problems.append("al giunto il segnale si scosta dal modello più che altrove")
    ts = int(round(t_seam))
    n = int(0.05 * SR)
    seg = cap[ts - n: ts + n]
    d = np.abs(np.diff(seg, axis=0)).max(axis=1)
    jump_ratio = float(d[n - 1] / (np.percentile(np.delete(d, n - 1), 99.9) or 1e-9))
    hp = signal.sosfilt(signal.butter(4, 4000, btype="highpass", fs=SR, output="sos"), seg, axis=0)
    pw = np.convolve((hp ** 2).sum(axis=1), np.ones(144), mode="same")
    hf_ratio = float(pw[n] / (np.median(pw[144:-144]) or 1e-12))
    print(f"giunto nella registrazione: salto {jump_ratio:.2f} (sotto 1,5: nessun gradino), "
          f"energia acuta {hf_ratio:.2f} (sotto 4: nessun click)")
    results.update({"seam_jump_ratio": jump_ratio, "seam_hf_ratio": hf_ratio})
    if jump_ratio > 1.5 or hf_ratio > 4.0:
        problems.append("click al giunto")
    out_fade = gb[span(t_j - 0.04, t_j + 0.42)]
    print("dissolvenza verso il jingle (20 ms):", " ".join(f"{v:.2f}" for v in out_fade))
    if out_fade[-1] > 0.02 or np.any(np.diff(out_fade) > 0.05):
        problems.append("dissolvenza verso il jingle irregolare")

    # ---------------------------------------------------------------- jingle e silenzio
    q = qj
    k = span(j_start / SR + 0.4, j_start / SR + len(J) / SR - 0.05)
    jg = float(np.nanmedian(gj[k])) * music_gain
    jres = float(np.median(res_rel[k]))
    print(f"jingle: parte a {j_start / SR:.4f} s (comando a {t_j:.4f} s, {(j_start / SR - t_j) * 1000:.1f} ms dopo), "
          f"guadagno {jg / music_gain:.3f} del pieno, residuo {jres:.3f}, somiglianza {q:.4f}")
    q_end = int(when["sfx_left"][0] * SR) - int(0.02 * SR)
    quiet = cap[j_start + len(J) + int(0.05 * SR): q_end]
    quiet_db = float(al.db(np.sqrt(np.mean(quiet ** 2)) + 1e-12))
    print(f"dopo il jingle: {len(quiet) / SR:.2f} s a {quiet_db:.1f} dBFS RMS (picco {al.sample_peak_db(quiet):.1f} dBFS)")
    results.update({"jingle_start_s": j_start / SR, "jingle_gain_rel": jg / music_gain, "jingle_residual": jres,
                    "silence_db": quiet_db})
    if abs(jg / music_gain - 1) > 0.05 or jres > 0.15 or q < 0.95:
        problems.append("jingle non riconosciuto per intero")
    if quiet_db > -70:
        problems.append("dopo il jingle non c'è silenzio")

    # ---------------------------------------------------------------- effetti e pan
    hit, hsr = al.read_wav(a.sfx_dir / "hit_heavy.wav")
    g = np.gcd(SR, hsr)
    H = signal.resample_poly(hit, SR // g, hsr // g)
    base_g = float(al.from_db(mix["hit_heavy"]))
    pans = {}
    for key, pan in (("sfx_left", -0.25), ("sfx_right", 0.25), ("sfx_center", 0.0)):
        t0 = int(when[key][0] * SR)
        seg = cap[t0: t0 + int(0.6 * SR)]
        c = signal.correlate(seg.mean(axis=1), H, mode="valid")
        k = int(np.argmax(np.abs(c)))
        w = cap[t0 + k: t0 + k + len(H)]
        gl = float(np.dot(w[:, 0], H) / np.dot(H, H))
        gr = float(np.dot(w[:, 1], H) / np.dot(H, H))
        # AudioEffectPanner su un suono mono: sinistra (1 - pan), destra (1 + pan)
        el, er = base_g * (1.0 - pan), base_g * (1.0 + pan)
        pans[key] = {"delay_ms": k / SR * 1000, "left": gl, "right": gr, "want_left": el, "want_right": er}
        print(f"{key}: {k / SR * 1000:.1f} ms dopo il comando; sinistra {gl:.3f} (attesa {el:.3f}), "
              f"destra {gr:.3f} (attesa {er:.3f}), differenza {al.db(gl / gr):+.1f} dB")
        if abs(gl - el) > 0.03 or abs(gr - er) > 0.03:
            problems.append(f"pan di {key} non atteso")
    results["sfx"] = pans
    tail = cap[int(when["sfx_missing"][0] * SR):]
    results["after_missing_peak_db"] = al.sample_peak_db(tail[int(0.6 * SR):]) if len(tail) > int(0.7 * SR) else None

    if a.png:
        draw(a.png, cap, tg, gb, ga, gj, events, t_seam, B44, off_pre, off_post, G[:, 1], r)
        print("tavola:", a.png)
    if a.json:
        a.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems))
        return 1
    print("OK: musica, loop, strato, duck, jingle ed effetti come previsto")
    return 0


def draw(path, cap, tg, gb, ga, gj, events, t_seam, B44, off_pre, off_post, gb_abs, r) -> None:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1500, 960
    img = Image.new("RGB", (W, H), (14, 12, 26))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    dur = len(cap) / SR
    X = lambda t: 70 + (W - 90) * t / dur  # noqa: E731
    # 1) inviluppo RMS (dB) dei due canali con gli eventi della scena
    y0, h1 = 34, 230
    d.text((10, 8), "registrazione Movie Maker: RMS a 10 ms in dBFS (sinistra azzurro, destra arancio) ed eventi",
           fill=(255, 240, 200), font=font)
    for db_ in (0, -20, -40, -60):
        yy = y0 + h1 - (db_ + 70) / 70 * h1
        d.line([70, yy, W - 20, yy], fill=(45, 45, 65))
        d.text((10, yy - 7), f"{db_} dB", fill=(160, 160, 180), font=font)
    for ch, col in ((0, (120, 230, 255)), (1, (255, 150, 120))):
        t, env = al.rms_envelope(cap[:, ch], SR, 0.01)
        v = np.clip((al.db(env + 1e-9) + 70) / 70, 0, 1)
        d.line([(X(tt), y0 + h1 - vv * h1) for tt, vv in zip(t, v)], fill=col)
    for i, (t, name) in enumerate(events):
        d.line([X(t), y0, X(t), y0 + h1], fill=(90, 90, 120))
        d.text((X(t) + 2, y0 + 2 + 13 * (i % 4)), name, fill=(210, 210, 230), font=font)
    d.line([X(t_seam / SR), y0, X(t_seam / SR), y0 + h1], fill=(255, 80, 80))
    d.text((X(t_seam / SR) + 2, y0 + h1 - 15), "giunto del loop", fill=(255, 120, 120), font=font)
    # 2) guadagni stimati (1 = pieno)
    y1, h2 = 300, 230
    d.text((10, y1 - 24), "guadagni stimati ogni 20 ms: base (azzurro), strato arena (arancio), jingle (verde); 1 = pieno, 0,32 = -10 dB",
           fill=(255, 240, 200), font=font)
    for v in (0.0, 0.316, 1.0):
        yy = y1 + h2 - v * h2 / 1.15
        d.line([70, yy, W - 20, yy], fill=(45, 45, 65))
        d.text((10, yy - 7), f"{v:.2f}", fill=(160, 160, 180), font=font)
    for col, data in (((120, 230, 255), gb), ((255, 170, 60), ga), ((120, 255, 140), gj)):
        pts = [(X(t), y1 + h2 - v * h2 / 1.15) for t, v in zip(tg, data) if np.isfinite(v)]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            if p1[0] - p0[0] < 3:
                d.line([p0, p1], fill=col, width=2)
    for t, name in events:
        d.line([X(t), y1, X(t), y1 + h2], fill=(60, 60, 85))
    # 3) zoom sul giunto
    y2, h3 = 600, 160
    n = int(0.010 * SR)
    ts = int(round(t_seam))
    seg = cap[ts - n: ts + n, 0]
    tt = np.arange(ts - n, ts + n)
    p = np.where(tt < t_seam, tt + off_pre, tt + off_post)
    k = (tg > t_seam / SR - 0.5) & (tg < t_seam / SR - 0.05)
    model = catmull(B44, p / r)[:, 0] * float(np.nanmedian(gb_abs[k]))
    d.text((10, y2 - 24), "giunto del loop, 10 ms prima e dopo (canale sinistro): registrazione (azzurro) e base attesa "
           "(bianco): ci si somma lo strato arena acceso", fill=(255, 240, 200), font=font)
    sc = h3 / 2 / max(np.max(np.abs(seg)), 1e-6)
    px = lambda i: 70 + (W - 90) * i / (2 * n)  # noqa: E731
    d.line([(px(i), y2 + h3 / 2 - v * sc) for i, v in enumerate(model)], fill=(230, 230, 230))
    d.line([(px(i), y2 + h3 / 2 - v * sc) for i, v in enumerate(seg)], fill=(120, 230, 255))
    d.line([px(n), y2, px(n), y2 + h3], fill=(255, 80, 80))
    # 4) effetti col pan
    y3, h4 = 820, 120
    tl = [t for t, nme in events if nme == "sfx_left"][0]
    tm = [t for t, nme in events if nme == "sfx_missing"][0]
    seg = cap[int((tl - 0.05) * SR): int((tm + 0.4) * SR)]
    d.text((10, y3 - 24), "effetti: hit_heavy a sinistra, a destra e al centro, poi un suono mancante (sinistra azzurro, destra arancio)",
           fill=(255, 240, 200), font=font)
    m = max(1, len(seg) // (W - 90))
    for ch, col in ((0, (120, 230, 255)), (1, (255, 150, 120))):
        mx = np.abs(seg[: (len(seg) // m) * m, ch]).reshape(-1, m).max(axis=1)
        d.line([(70 + i, y3 + h4 - v * h4) for i, v in enumerate(mx)], fill=col)
    img.save(path)


if __name__ == "__main__":
    sys.exit(main())
