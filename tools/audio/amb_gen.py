"""Ambienti in loop e passi per superficie di CTRL+ALT REVENGE, sintetizzati dal codice (nessun campione di terzi).

Usa i mattoni di sfx_gen.py. Ogni ambiente è un loop di 24 s, stereo, con il giunto pulito per costruzione:
- i rumori (vento, pioggia) si generano più lunghi e si raccordano con una dissolvenza a potenza costante;
- gli eventi con coda (gocce, riverbero) si fanno "a cerchio": la coda che esce dalla fine rientra all'inizio;
- i toni (ronzii) hanno frequenze multiple di 1/24 Hz, quindi in 24 s fanno cicli interi.
Ogni loop si porta al livello (LUFS integrati) scelto per lui. Sono strati: il gioco li somma
(per esempio cimitero + pioggia delle prime gocce).

  python -I tools/audio/amb_gen.py --out <cartella>     # scrive loop, passi, mix.json e report.json

La cartella di prova sta nel laboratorio (%USERPROFILE%\\ctrlaltrevenge-lab\\sfx\\_prova_2026-11-11\\):
niente va in game/assets/sfx finché la regia non approva le prove.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402
import sfx_gen as sg  # noqa: E402

SR = sg.SR
DUR = 24.0
N = int(round(DUR * SR))
OV = int(round(2.0 * SR))          # sovrapposizione per il raccordo dei rumori

LOOP_IMPORT = """[remap]

importer="wav"
type="AudioStreamWAV"

[params]

force/8_bit=false
force/mono=false
force/max_rate=false
force/max_rate_hz=44100
edit/trim=false
edit/normalize=false
edit/loop_mode=2
edit/loop_begin=0
edit/loop_end=-1
compress/mode=0
"""


# ----------------------------------------------------------------------------- mattoni

def loopify(x: np.ndarray) -> np.ndarray:
    """x lungo N+OV: i primi OV campioni si fondono (potenza costante) con la coda, che li continua."""
    y = x[:N].copy()
    th = np.linspace(0.0, np.pi / 2, OV)
    y[:OV] = np.sin(th) * x[:OV] + np.cos(th) * x[N:N + OV]
    return y


def fold(x: np.ndarray) -> np.ndarray:
    """La coda oltre N rientra all'inizio (per gli eventi con risonanza e riverbero)."""
    y = x[:N].copy()
    t = x[N:]
    y[:len(t)] += t[:N]
    return y


def put(dst: np.ndarray, src: np.ndarray, at: int, gain: float = 1.0) -> None:
    """Somma src in dst a partire da 'at', con ritorno a capo."""
    at %= len(dst)
    j = min(len(dst), at + len(src))
    dst[at:j] += gain * src[: j - at]
    rest = len(src) - (j - at)
    if rest > 0:
        dst[:rest] += gain * src[j - at:]


def env_lp_noise(n: int, rng: np.random.Generator, fc: float, order: int = 2) -> np.ndarray:
    """Rumore passa-basso portato a media 0 e deviazione 1: per le raffiche e i modulatori lenti."""
    z = signal.sosfilt(signal.butter(order, fc, btype="lowpass", fs=SR, output="sos"), rng.standard_normal(n))
    z = z[int(SR * 0.5):] if len(z) > SR else z
    z = np.concatenate([z, z[::-1]])[:n] if len(z) < n else z[:n]
    return (z - z.mean()) / (z.std() + 1e-12)


def gust(n: int, rng: np.random.Generator, fc: float = 0.25, depth: float = 0.65, power: float = 1.4) -> np.ndarray:
    """Raffica: 1 - depth ... 1, lenta e irregolare."""
    g = env_lp_noise(n + 2 * SR, rng, fc)[:n]
    g = (g - g.min()) / (g.max() - g.min())
    return (1.0 - depth) + depth * g ** power


def sines(freqs_amps: list[tuple[float, float]], n: int, ph: np.ndarray | None = None) -> np.ndarray:
    """Toni con frequenze multiple di 1/DUR: fanno cicli interi nel loop."""
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, (f, a) in enumerate(freqs_amps):
        f = round(f * DUR) / DUR
        y += a * np.sin(2 * np.pi * f * t + (0.0 if ph is None else ph[i]))
    return y


def stereo(make, seed: int) -> np.ndarray:
    """Due canali con rumori diversi (stessa 'regia', semi diversi): ampiezza e profondità."""
    return np.stack([make(np.random.default_rng(seed)), make(np.random.default_rng(seed + 1000003))], axis=1)


def drop_click(rng: np.random.Generator, lo: float, hi: float, ms: float, ping: float = 0.0) -> np.ndarray:
    n = max(8, int(ms / 1000.0 * SR))
    b = sg.bp(rng.standard_normal(n), lo, hi, 2) * np.exp(-np.arange(n) / (n / 3.2))
    b /= np.max(np.abs(b)) + 1e-12
    if ping > 0:
        f = rng.uniform(1700.0, 4200.0)
        m = min(n, int(0.012 * SR))
        t = np.arange(m) / SR
        b = b.copy()
        b[:m] += ping * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.004)
    return b


def poisson_times(rng: np.random.Generator, rate: float, dur: float = DUR) -> np.ndarray:
    k = rng.poisson(rate * dur)
    return np.sort(rng.uniform(0.0, dur, k))


def circ_reverb(x: np.ndarray, rng: np.random.Generator, tail_s: float, tau: float, lp_hz: float, wet: float) -> np.ndarray:
    m = int(tail_s * SR)
    ir = rng.standard_normal(m) * np.exp(-np.arange(m) / (tau * SR))
    ir = sg.lp(ir, lp_hz)
    ir[0] = 0.0
    ir /= np.sqrt(np.sum(ir * ir)) or 1.0
    return x + wet * fold(np.concatenate([signal.fftconvolve(x, ir), np.zeros(0)])[: N + m])


# ----------------------------------------------------------------------------- gli ambienti

def amb_cimitero(rng: np.random.Generator) -> np.ndarray:
    """Pomeriggio asciutto fra i cipressi di San Brunone: vento leggero e il fruscio dei rami, il
    rombo basso e continuo del nastro della Linea (cronologia, «Sempre»), un ronzio lontano di cupole
    e di droni. Niente campane, niente cicale, niente traffico a scoppio."""
    n = N + OV
    g = gust(n, rng, 0.22, 0.7, 1.5)
    g2 = gust(n, rng, 0.35, 0.8, 2.0)
    wind = sg.bp(rng.standard_normal(n), 220.0, 950.0, 2) * (0.25 + 0.75 * g) * 0.9
    wind += sg.bp(rng.standard_normal(n), 900.0, 2200.0, 2) * g * 0.25
    # i rami: sibilo corto e irregolare nelle raffiche
    leaf = sg.bp(rng.standard_normal(n), 2600.0, 6500.0, 2) * (g2 ** 2) * np.clip(env_lp_noise(n, rng, 14.0) + 0.6, 0, None) * 0.22
    # la Linea, lontanissima: banda bassa quasi ferma
    linea = sg.lp(rng.standard_normal(n), 85.0, 2) * (1.0 + 0.12 * env_lp_noise(n, rng, 0.2)) * 1.3
    base = wind + leaf + linea
    y = loopify(base)
    # ronzio di cupole: due toni lenti che battono (periodici nel loop) + un drone che passa lontano
    y += sines([(96.0, 0.03), (97.5, 0.025), (192.0, 0.008)], N)
    t = np.arange(N) / SR
    pas = np.clip(np.sin(np.pi * np.clip((t - 7.0) / 9.0, 0.0, 1.0)), 0, None) ** 2
    rotor = 0.5 + 0.5 * np.sin(2 * np.pi * 38.0 * t + 2.2 * np.sin(2 * np.pi * 0.7 * t))
    drone = sg.bp(rng.standard_normal(N), 160.0, 780.0, 2) * (0.4 + 0.6 * rotor) * pas * 0.28
    return y + drone


def amb_uccelli(rng: np.random.Generator) -> np.ndarray:
    """Strato a parte (si può togliere): pochi passeri lontani e due gabbiani del Mar Piccolo. Da giudicare a orecchio."""
    y = np.zeros(N)
    nphr = 5
    starts = np.sort(rng.uniform(1.0, DUR - 3.0, nphr))
    for s in starts:
        k = int(rng.integers(2, 5))
        f0 = rng.uniform(2700.0, 4300.0)
        t0 = s
        for _ in range(k):
            d = rng.uniform(0.045, 0.09)
            m = int(d * SR)
            tt = np.arange(m) / SR
            sweep = f0 * (1.0 + rng.uniform(-0.22, 0.22) * (tt / d) + 0.12 * np.sin(np.pi * tt / d))
            ph = 2 * np.pi * np.cumsum(sweep) / SR
            c = np.sin(ph) + 0.25 * np.sin(2 * ph + 0.7)
            c *= np.sin(np.pi * tt / d) ** 1.5
            put(y, c, int(t0 * SR), rng.uniform(0.5, 1.0))
            t0 += d + rng.uniform(0.05, 0.13)
            f0 *= rng.uniform(0.9, 1.1)
    for s in (5.5, 15.0):
        d = 0.9
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 820.0 - 260.0 * (tt / d) + 70.0 * np.sin(2 * np.pi * 7.0 * tt)
        ph = 2 * np.pi * np.cumsum(f) / SR
        saw = sum(np.sin(h * ph) / h for h in range(1, 12))
        saw = sg.bp(saw, 700.0, 3200.0, 2) * (np.sin(np.pi * tt / d) ** 1.2) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.2 * tt))
        put(y, saw, int(s * SR), 0.5)
    y = sg.lp(y, 7500.0)
    return circ_reverb(y, rng, 1.2, 0.35, 5000.0, 0.8)


def amb_pioggia_prime(rng: np.random.Generator) -> np.ndarray:
    """A5: le prime gocce, rade e pesanti, sulla terra e sulle foglie. Sono uno strato da aggiungere al cimitero."""
    y = np.zeros(N)
    for t in poisson_times(rng, 6.5):
        big = rng.random() < 0.25
        c = drop_click(rng, rng.uniform(900, 1800) if big else rng.uniform(1800, 3500), rng.uniform(5000, 8500),
                       rng.uniform(5, 14) if big else rng.uniform(2.5, 7), ping=0.12)
        put(y, c, int(t * SR), rng.lognormal(-0.7, 0.55) * (1.0 if big else 0.55))
    hiss = sg.bp(rng.standard_normal(N), 3000.0, 9000.0, 2) * (0.5 + 0.5 * np.clip(env_lp_noise(N, rng, 0.3) * 0.5 + 0.5, 0, 1)) * 0.07
    return y * 0.55 + hiss


def amb_pioggia_piena(rng: np.random.Generator) -> np.ndarray:
    """A6 e B: pioggia fitta all'aperto, sull'asfalto e sulle lamiere: sibilo, gocce, rombo lontano."""
    n = N + OV
    sib = sg.bp(rng.standard_normal(n), 600.0, 9500.0, 2) + 0.7 * sg.bp(rng.standard_normal(n), 180.0, 600.0, 2)
    sib *= 0.6 * (1.0 + 0.10 * env_lp_noise(n, rng, 0.4))
    imp = np.zeros(n)
    idx = rng.integers(0, n, int(950 * n / SR))
    imp[idx] = rng.lognormal(-0.4, 0.8, len(idx))
    drops = sg.bp(imp, 1600.0, 7500.0, 2) * 6.0
    imp2 = np.zeros(n)
    idx2 = rng.integers(0, n, int(28 * n / SR))
    imp2[idx2] = rng.lognormal(0.0, 0.5, len(idx2))
    big = sg.bp(imp2, 350.0, 1500.0, 2) * 14.0       # gocce grosse e rivoli dai tetti
    roar = sg.lp(rng.standard_normal(n), 240.0, 2) * 1.6 * (1.0 + 0.14 * env_lp_noise(n, rng, 0.25))
    return loopify(sib + drops + big + roar)


def amb_cantine(rng: np.random.Generator) -> np.ndarray:
    """B2, sotto la strada: gocce nel tufo con molto riverbero scuro, il rimbombo della stanza e, sopra,
    la pioggia ovattata dal terreno."""
    drips = np.zeros(N)
    t = 0.6
    while t < DUR - 0.5:
        f = rng.uniform(750.0, 1750.0)
        m = int(0.09 * SR)
        tt = np.arange(m) / SR
        ph = 2 * np.pi * np.cumsum(f * (1.0 + 0.7 * (1 - np.exp(-tt / 0.012)))) / SR
        d = np.sin(ph) * np.exp(-tt / rng.uniform(0.018, 0.035))
        d[:40] += 0.6 * sg.hp(rng.standard_normal(40), 2500.0, 2)
        put(drips, d, int(t * SR), rng.uniform(0.35, 1.0))
        t += rng.uniform(1.1, 3.6)
    drips = circ_reverb(drips, rng, 2.4, 0.5, 2200.0, 1.0)
    n = N + OV
    rumble = loopify(sg.lp(rng.standard_normal(n), 130.0, 2) * 1.6 * (1.0 + 0.2 * env_lp_noise(n, rng, 0.2)))
    rumble += sines([(55.0, 0.05), (82.5, 0.03)], N)
    rain = loopify(sg.lp(sg.bp(rng.standard_normal(n), 250.0, 2200.0, 2), 1500.0) * 0.5 * (1.0 + 0.2 * env_lp_noise(n, rng, 0.3)))
    return drips * 0.9 + rumble + rain * 0.45


def amb_garage(rng: np.random.Generator) -> np.ndarray:
    """B4: la pioggia sul lucernario (gocce tintinnanti sul vetro, rombo ovattato) e il ronzio della
    lampada del banco a 100 Hz (rete a 50 Hz) con le sue armoniche."""
    y = np.zeros(N)
    modes = [(1450.0, 0.014), (2380.0, 0.010), (3350.0, 0.007)]
    for t in poisson_times(rng, 24.0):
        a = rng.lognormal(-0.5, 0.6)
        c = drop_click(rng, 2200.0, 8500.0, rng.uniform(1.5, 4.0), ping=0.0)
        m = int(0.07 * SR)
        tt = np.arange(m) / SR
        ring = sum(rng.uniform(0.2, 0.6) * np.sin(2 * np.pi * f * rng.uniform(0.97, 1.03) * tt) * np.exp(-tt / d) for f, d in modes)
        c2 = np.zeros(m)
        c2[:len(c)] = c[:m] * 0.5
        put(y, c2 + 0.5 * ring, int(t * SR), a)
    y = circ_reverb(y, rng, 0.35, 0.09, 6000.0, 0.8)
    n = N + OV
    roar = loopify(sg.lp(sg.bp(rng.standard_normal(n), 200.0, 2200.0, 2), 1800.0) * 0.55 * (1.0 + 0.12 * env_lp_noise(n, rng, 0.3)))
    lamp = sines([(100.0, 0.05), (200.0, 0.022), (300.0, 0.016), (400.0, 0.007)], N)
    lamp *= 1.0 + 0.04 * np.sin(2 * np.pi * round(0.33 * DUR) / DUR * np.arange(N) / SR)
    return y * 0.9 + roar * 0.5 + lamp


# nome: (funzione, LUFS integrati bersaglio, seme, perché)
AMBIENTI = {
    "amb_cimitero": (amb_cimitero, -28.0, 11, "da solo nei tratti senza musica (A1-A4): deve sentirsi, ma sotto le voci"),
    "amb_uccelli": (amb_uccelli, -38.0, 12, "strato raro e lontano sopra il cimitero: eventi brevi, il valore integrato è basso"),
    "amb_pioggia_prime": (amb_pioggia_prime, -32.0, 13, "gocce rade (A5), si somma al cimitero"),
    "amb_pioggia_piena": (amb_pioggia_piena, -28.0, 14, "A6 e B: è l'ambiente principale e copre la musica a -16: 12 dB sotto"),
    "amb_cantine": (amb_cantine, -30.0, 15, "interno: silenzio abitato"),
    "amb_garage": (amb_garage, -30.0, 16, "interno: la quiete prima del riavvio"),
}


# ----------------------------------------------------------------------------- i passi

def step_pietra(rng: np.random.Generator, f0: float, band: tuple[float, float]) -> np.ndarray:
    """Stivali su pietra asciutta (viali e lapidi di San Brunone): tacco secco, un po' di sabbia."""
    n = sg.n_of(0.09)
    y = (sg.layer_body(n, f0, f0 * 0.7, 0.010, 0.016, 1.3, 0.5, attack=0.0012)
         + sg.layer_transient(n, rng, 2500.0, 0.0035, 0.55)
         + sg.layer_noise_band(n, rng, band[0], band[1], 0.0012, 0.014, 0.3)
         + 0.12 * sg.crackles(n, rng, 2500.0, 0.04, 5000.0, (0.3, 1.2)))
    return sg.pcm_crunch(y, 22050.0, 11)


def step_bagnato(rng: np.random.Generator, f0: float, band: tuple[float, float]) -> np.ndarray:
    """Stivali su asfalto bagnato (la fuga): il passo di prima con più spruzzo e uno sciacquio."""
    n = sg.n_of(0.12)
    y = (sg.layer_body(n, f0, f0 * 0.66, 0.012, 0.012, 1.4, 0.4, attack=0.0015)
         + sg.layer_noise_band(n, rng, band[0], band[1], 0.002, 0.02, 0.4)
         + 0.4 * sg.crackles(n, rng, 1700.0, 0.05, 3500.0, (0.3, 1.6))
         + sg.layer_noise_band(n, rng, 2500.0, 9000.0, 0.004, 0.035, 0.28, delay=0.006))
    return sg.pcm_crunch(y, 20000.0, 10)


def step_interno(rng: np.random.Generator, f0: float, band: tuple[float, float]) -> np.ndarray:
    """Cemento di garage e cantine: passo secco con una coda di stanza."""
    n = sg.n_of(0.09)
    y = (sg.layer_body(n, f0, f0 * 0.7, 0.010, 0.014, 1.3, 0.5, attack=0.0012)
         + sg.layer_transient(n, rng, 2000.0, 0.004, 0.4)
         + sg.layer_noise_band(n, rng, band[0], band[1], 0.0012, 0.012, 0.25))
    y = sg.pcm_crunch(y, 22050.0, 11)
    return sg.impulse_tail(y, 0.3, 0.07, 2500.0, rng, 0.45)


PASSI = {
    "step_pietra_a": (step_pietra, 172.0, (1800.0, 5500.0)),
    "step_pietra_b": (step_pietra, 150.0, (1500.0, 5000.0)),
    "step_bagnato_a": (step_bagnato, 165.0, (1500.0, 5000.0)),
    "step_bagnato_b": (step_bagnato, 148.0, (1300.0, 4400.0)),
    "step_interno_a": (step_interno, 160.0, (1300.0, 4200.0)),
    "step_interno_b": (step_interno, 140.0, (1100.0, 3800.0)),
}
STEP_TARGET = -25.0      # loudness veloce (100 ms, pesata K) nel gioco; oggi -31 (i colpi sono a -10/-11)


# ----------------------------------------------------------------------------- controlli e uscita

def seam_report(x: np.ndarray) -> dict:
    """Salto al giunto del loop (ultimo -> primo campione) rispetto alla differenza tipica fra campioni vicini."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    d = np.abs(np.diff(np.concatenate([m[-2000:], m[:2000]])))
    near = np.concatenate([d[:1950], d[2050:]])
    out = {"click_vs_rms": round(float(d[1997:2003].max() / (np.sqrt(np.mean(near ** 2)) + 1e-12)), 2)}
    k = int(0.5 * SR)
    out["step_500ms_db"] = round(float(10 * np.log10(np.mean(m[-k:] ** 2) / np.mean(m[:k] ** 2))), 2)
    # quanto cambia la potenza fra finestre vicine dentro il loop: il salto al giunto deve essere dello stesso ordine
    w = np.array([np.mean(m[i:i + k] ** 2) for i in range(0, len(m) - 2 * k, k)])
    adj = np.abs(10 * np.log10(w[1:] / w[:-1]))
    out["salto_tipico_500ms_db"] = round(float(np.percentile(adj, 90)), 2)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rep, problems = {}, []
    for name, (fn, target, seed, why) in AMBIENTI.items():
        x = stereo(fn, seed)
        x = x - x.mean(axis=0)
        if name == "amb_uccelli":
            gain_db = target - sg.fast_loudness(x.mean(axis=1))      # eventi brevi: si misura il picco di 100 ms
        else:
            gain_db = target - al.integrated_loudness(x, SR)
        x = x * 10 ** (gain_db / 20)
        tp = al.true_peak_db(x)
        if tp > -2.0:
            problems.append(f"{name}: picco vero {tp:.1f} dBTP")
        if not np.all(np.isfinite(x)):
            problems.append(f"{name}: valori non finiti")
        s = seam_report(x)
        if s["click_vs_rms"] > 4.0 or abs(s["step_500ms_db"]) > max(1.5, 1.5 * s["salto_tipico_500ms_db"]):
            problems.append(f"{name}: giunto {s}")
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(LOOP_IMPORT, encoding="utf-8", newline="\n")
        rep[name] = {"dur_s": round(len(x) / SR, 3), "lufs": round(al.integrated_loudness(x, SR), 2),
                     "fast_lufs": round(sg.fast_loudness(x.mean(axis=1)), 2), "true_peak_dbtp": round(tp, 2),
                     "centroide_hz": round(al.spectral_centroid(x.mean(axis=1), SR)), "giunto": s, "perche_il_livello": why}
        print(f"{name:20s} {len(x)/SR:5.1f}s  {rep[name]['lufs']:6.1f} LUFS  TP {tp:6.1f}  centr {rep[name]['centroide_hz']:5d}  giunto {s}")
    mix = {}
    for i, (name, (fn, f0, band)) in enumerate(PASSI.items()):
        rng = np.random.default_rng(20261111 + 104729 * i)
        raw = fn(rng, f0, band)
        x = sg.finish(name, raw, fade_in_ms=1.0, fade_out_ms=10.0)
        errs = sg.check(name, x)
        if errs:
            problems.append(f"{name}: " + "; ".join(errs))
        fl = sg.fast_loudness(x)
        mix[name] = round(min(0.0, STEP_TARGET - fl) * 2) / 2
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(sg.IMPORT_TEMPLATE, encoding="utf-8", newline="\n")
        rep[name] = {"dur_s": round(len(x) / SR, 4), "picco_dbfs": round(al.sample_peak_db(x), 2), "fast_lufs": round(fl, 2),
                     "altoparlante_piccolo_lufs": round(sg.small_speaker_loudness(x), 2), "centroide_hz": round(al.spectral_centroid(x, SR)),
                     "mix_db": mix[name], "livello_nel_gioco_fast_lufs": round(fl + mix[name], 2)}
        print(f"{name:20s} {len(x)/SR*1000:5.0f}ms  fast {fl:6.1f}  piccolo {rep[name]['altoparlante_piccolo_lufs']:6.1f}  mix {mix[name]:5.1f}  nel gioco {rep[name]['livello_nel_gioco_fast_lufs']:6.1f}")
    (a.out / "mix_prova.json").write_text(json.dumps({"format": 1, "comment": "Guadagni dei passi nuovi (bersaglio fast %.0f LUFS)" % STEP_TARGET, "gain_db": mix}, indent=1) + "\n", encoding="utf-8", newline="\n")
    (a.out / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
