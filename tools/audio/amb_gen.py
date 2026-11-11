"""Ambienti in loop e passi per superficie di CTRL+ALT REVENGE, sintetizzati dal codice (nessun campione di terzi).

Usa i mattoni di sfx_gen.py. Ogni ambiente è un loop di 24 s, stereo, con il giunto pulito per costruzione:
- i rumori (vento, pioggia) si generano più lunghi e si raccordano con una dissolvenza a potenza costante;
- gli eventi con coda (gocce, riverbero) si fanno "a cerchio": la coda che esce dalla fine rientra all'inizio;
- i toni (ronzii) hanno frequenze multiple di 1/24 Hz, quindi in 24 s fanno cicli interi.
Ogni loop si porta al livello (LUFS integrati) scelto per lui. Sono strati: il gioco li somma
(per esempio cimitero + pioggia delle prime gocce).

  python -I tools/audio/amb_gen.py --out <cartella>     # scrive loop, passi, mix.json e report.json
  python -I tools/audio/amb_gen.py --out <cartella> --install
      # genera la serie da installare (v2 dove c'è, niente uccelli) e la copia nel gioco:
      # ambienti in OGG q4 in game/assets/sfx/amb/, passi in WAV in game/assets/sfx/,
      # e in mix.json solo le righe dei passi (le altre restano identiche)

La cartella di prova sta nel laboratorio (%USERPROFILE%\\ctrlaltrevenge-lab\\sfx\\_prova_2026-11-11\\).
Installati l'11 novembre 2026, su scelta di Luigi.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
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

# ----------------------------------------------------------------------------- installazione

GAME_SFX = sg.GAME_SFX
GAME_AMB = GAME_SFX / "amb"
LAB = Path(os.environ.get("CAR_LAB", Path(os.environ.get("USERPROFILE", str(Path.home()))) / "ctrlaltrevenge-lab"))
NON_INSTALLARE = {"amb_uccelli"}     # voto 4: non è un uccello credibile
OGG_QUALITY = "4"

# Godot riempie da solo uid, path e deps al primo import.
OGG_IMPORT = """[remap]

importer="oggvorbisstr"
type="AudioStreamOggVorbis"

[params]

loop=true
loop_offset=0
bpm=0
beat_count=0
bar_beats=4
"""


def ffmpeg() -> str:
    exe = LAB / "tools" / "ffmpeg" / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    found = str(exe) if exe.exists() else shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg non trovato: serve per gli OGG (laboratorio o PATH)")
    return found


def ogg_encode(wav: Path, dst: Path) -> None:
    tmp = dst.with_name(dst.name + ".tmp_install")
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-map_metadata", "-1",
           "-c:a", "libvorbis", "-q:a", OGG_QUALITY, "-fflags", "+bitexact", "-f", "ogg", str(tmp)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg ha fallito:\n" + r.stderr[-2000:])
    os.replace(tmp, dst)


def ogg_decode(path: Path, channels: int = 2) -> np.ndarray:
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", str(channels), "-ar", str(SR), "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg non decodifica " + str(path))
    return np.frombuffer(r.stdout, dtype="<f4").reshape(-1, channels).astype(np.float64)


def install_files(pairs: list[tuple[Path, Path]]) -> None:
    """Copia con nome temporaneo e poi rinomina: chi importa non vede mai un file a metà.
    Un .import già presente nel gioco non si tocca: Godot ci ha scritto uid e percorso (come in sfx_pack)."""
    tmp = []
    for src, dst in pairs:
        if dst.name.endswith(".import") and dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        t = dst.with_name(dst.name + ".tmp_install")
        shutil.copyfile(src, t)
        tmp.append((t, dst))
    for t, dst in tmp:
        os.replace(t, dst)


def merge_mix(rows: dict[str, float]) -> list[str]:
    """Aggiunge (o aggiorna) in game/assets/sfx/mix.json solo queste righe. Le righe di sfx_pack
    restano identiche, e un nome che è già di sfx_pack ferma tutto. Restituisce le righe nuove."""
    path = GAME_SFX / "mix.json"
    text = path.read_text(encoding="utf-8")
    doc = json.loads(text)
    if json.dumps(doc, indent=1, ensure_ascii=False) + "\n" != text:
        raise RuntimeError("mix.json non è nel formato atteso: riscriverlo cambierebbe altre righe")
    gains = doc["gain_db"]
    import sfx_pack  # i nomi dei suoni montati da sfx_pack (sfx_gen + block, hack)
    clash = sorted(set(rows) & set(sfx_pack.NAMES))
    if clash:
        raise RuntimeError(f"nomi già usati dai suoni di sfx_pack: {clash}")
    new = [k for k in rows if k not in gains]
    gains.update({k: float(v) for k, v in rows.items()})
    tmp = path.with_name(path.name + ".tmp_install")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return new


def ambienti_da_installare() -> dict:
    """Gli ambienti che vanno nel gioco: v2 dove c'è, gli altri della fase 1, senza uccelli."""
    out = {}
    for name, (fn, target, seed, why) in AMBIENTI.items():
        if name in NON_INSTALLARE:
            continue
        if name in AMBIENTI_V2:
            fn2, target2, seed2, why2 = AMBIENTI_V2[name]
            out[name] = (lambda s, f=fn2: f(s), target2, seed2, why2)
        else:
            out[name] = (lambda s, f=fn: stereo(f, s), target, seed, why)
    return out


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


# ----------------------------------------------------------------------------- gli ambienti v2 (11 novembre, fase 2)
# Fanno lo stereo da sé: i fondi diffusi hanno rumori diversi nei due canali, gli eventi puntuali sono
# gli stessi a sinistra e a destra, messi in un punto con il pan (una goccia non ha due altezze).

def pan2(x: np.ndarray, p: float) -> np.ndarray:
    """Mono -> stereo a potenza costante, p da -1 (sinistra) a 1 (destra)."""
    return np.stack([x * np.sqrt(0.5 * (1 - p)), x * np.sqrt(0.5 * (1 + p))], axis=1)


def bed(make, seed: int) -> np.ndarray:
    return np.stack([make(np.random.default_rng(seed)), make(np.random.default_rng(seed + 1000003))], axis=1)


def bubble_drop(rng: np.random.Generator, f0: float, tau: float, splash: float) -> np.ndarray:
    """Goccia d'acqua vera: un colpetto di rumore e la bolla che risuona salendo di altezza
    (risonanza di Minnaert), smorzata in pochi millisecondi: «plic», non una campanella."""
    m = int(0.04 * SR)
    tt = np.arange(m) / SR
    f = f0 * (1.0 + 0.55 * (1.0 - np.exp(-tt / 0.006)))
    b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / tau) * np.clip(tt / 0.0004, 0, 1)
    k = int(0.006 * SR)
    b[:k] += splash * sg.hp(rng.standard_normal(k), 3000.0, 2) * np.exp(-np.arange(k) / (k / 4))
    return b


def amb_cantine_v2(seed: int) -> np.ndarray:
    """B2, le cantine sotto la strada, rifatte. Le gocce sono bolle brevi (6-15 ms), non più campanelle;
    una perdita batte regolare nello stesso punto; il riverbero è più scuro e più diffuso. Dalla grata
    arriva la ventola di un purificatore ARIA+ della strada (2087), che respira lenta; nei tubi, ogni
    tanto, un gorgoglio. Sopra, la pioggia e la città ovattate dal terreno."""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    # la perdita regolare: 14 gocce nei 24 s (una ogni 1,71 s), un po' a sinistra
    leak = np.zeros(N)
    for i in range(14):
        tt = i * DUR / 14 + rng.normal(0.0, 0.03)
        put(leak, bubble_drop(rng, 1650.0 * rng.uniform(0.97, 1.03), rng.uniform(0.006, 0.009), 0.35), int(tt * SR), rng.uniform(0.8, 1.0))
    out += pan2(leak, -0.45)
    # gocce sparse dalla volta, in punti diversi
    for tt in poisson_times(rng, 0.45):
        d = bubble_drop(rng, rng.uniform(900.0, 2600.0), rng.uniform(0.004, 0.012), rng.uniform(0.2, 0.6))
        x = np.zeros(N)
        put(x, d, int(tt * SR), rng.uniform(0.3, 0.8))
        out += pan2(x, rng.uniform(-0.8, 0.8))
    # riverbero della cantina: scuro, diffuso, poco bagnato rispetto alla v1
    out = np.stack([circ_reverb(out[:, c], np.random.default_rng(seed + 7 + c), 1.6, 0.32, 1400.0, 0.55) for c in range(2)], axis=1)
    # il gorgoglio nei tubi, due volte
    for t0, p in ((6.3, 0.5), (17.8, 0.3)):
        g = np.zeros(int(0.9 * SR))
        tt = 0.0
        while tt < 0.75:
            b = bubble_drop(rng, rng.uniform(180.0, 420.0), rng.uniform(0.01, 0.02), 0.0)
            s = int(tt * SR)
            g[s:s + len(b)] += b[: len(g) - s] * rng.uniform(0.4, 1.0) * np.sin(np.pi * tt / 0.75)
            tt += rng.uniform(0.03, 0.08)
        g = resonate_bp(g, 320.0, 3.0)
        x = np.zeros(N)
        put(x, g, int(t0 * SR), 0.5)
        out += pan2(sg.lp(x, 1200.0), p)
    # la ventola ARIA+ dietro la grata: pale a 152 Hz che respirano (±4% in 12 s), soffio filtrato dalla grata
    breath = np.sin(2 * np.pi * 2 * t / DUR)
    f = (round(152.0 * DUR) / DUR) * (1.0 + 0.04 * breath)
    ph = 2 * np.pi * np.cumsum(f) / SR
    fan_tone = 0.02 * np.sin(ph) + 0.012 * np.sin(2 * ph + 0.4) + 0.006 * np.sin(3 * ph + 1.1)
    def fan_noise(r):
        n = N + OV
        z = sg.bp(r.standard_normal(n), 300.0, 2400.0, 2)
        z = z + 0.5 * sg.bp(r.standard_normal(n), 1180.0, 1320.0, 2)      # il fischio della grata
        return loopify(z)
    fan = bed(fan_noise, seed + 11) * (0.09 * (1.0 + 0.25 * breath))[:, None]
    out += fan * np.array([0.75, 1.15]) + pan2(fan_tone, 0.35)
    # la terra sopra: rombo della città e pioggia ovattata
    def above(r):
        n = N + OV
        rum = sg.lp(r.standard_normal(n), 120.0, 2) * 1.5 * (1.0 + 0.2 * env_lp_noise(n, r, 0.2))
        rain = sg.lp(sg.bp(r.standard_normal(n), 250.0, 2000.0, 2), 1200.0) * 0.2 * (1.0 + 0.2 * env_lp_noise(n, r, 0.3))
        return loopify(rum + rain)
    out += bed(above, seed + 13)
    out += pan2(sines([(55.0, 0.04), (82.5, 0.02)], N), 0.0)
    return out


def resonate_bp(x: np.ndarray, f: float, q: float) -> np.ndarray:
    b, a = signal.iirpeak(f, q, fs=SR)
    return signal.lfilter(b, a, x)


def rustle(n: int, rng: np.random.Generator, density: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Fruscio di foglie: tanti granelli di rumore di 2-6 ms, più fitti dove 'density' è alta."""
    y = np.zeros(n)
    rate = 900.0 * density / max(density.mean(), 1e-9)
    cum = np.cumsum(rate) / SR
    k = int(cum[-1])
    pos = np.searchsorted(cum, np.sort(rng.uniform(0, cum[-1], k)))
    for p in pos:
        m = int(rng.uniform(0.002, 0.006) * SR)
        g = rng.standard_normal(m) * np.hanning(m) * rng.lognormal(-0.5, 0.6)
        put(y, g, int(p), 1.0)
    return sg.bp(y, lo, hi, 2)


def drone_pass(t: np.ndarray, t0: float, dur: float, f_bpf: float, dist: float) -> tuple[np.ndarray, np.ndarray]:
    """Un drone che passa da sinistra a destra: tono delle pale con armoniche, doppler (±3%) e
    attenuazione con la distanza; restituisce il segnale mono e il pan nel tempo."""
    u = np.clip((t - t0) / dur, 0.0, 1.0)
    x = (u - 0.5) * 2.0
    r = np.sqrt(x ** 2 + dist ** 2)
    vr = np.gradient(r) * SR / dur            # velocità radiale (in unità di passaggio al secondo)
    f = f_bpf * (1.0 - 0.03 * vr / (np.abs(vr).max() + 1e-9))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = sum(a * np.sin((h + 1) * ph + 0.3 * h) for h, a in enumerate([1.0, 0.6, 0.4, 0.25, 0.15, 0.08]))
    amp = (dist / r) ** 1.5 * np.sin(np.pi * u) ** 0.7
    return tone * amp, np.clip(x, -0.9, 0.9)


def amb_cimitero_v2(seed: int) -> np.ndarray:
    """A1-A4, San Brunone di pomeriggio, rifatto. Vento a più bande con raffiche indipendenti; il
    fruscio dei cipressi fatto a granelli (più vero del rumore filtrato); due droni di consegna che
    passano lontani, con il doppler; il ronzio delle cupole che va e viene; dalla strada il fruscio
    delle gomme delle auto elettriche e il loro avviso acustico (il «canto» che le elettriche fanno per i
    pedoni: dice il 2087 senza parole). Il nastro della Linea, sotto, come nella v1. Niente uccelli."""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / SR
    def wind(r):
        n = N + OV
        g1, g2, g3 = gust(n, r, 0.18, 0.7, 1.5), gust(n, r, 0.3, 0.75, 1.8), gust(n, r, 0.45, 0.85, 2.2)
        w = sg.bp(r.standard_normal(n), 180.0, 700.0, 2) * (0.3 + 0.7 * g1) * 0.8
        w += sg.bp(r.standard_normal(n), 600.0, 1600.0, 2) * g2 * 0.28
        w += rustle(n, r, 0.05 + g3 ** 2.5, 2400.0, 7500.0) * 0.12
        w += rustle(n, r, 0.1 + g2 ** 2, 1200.0, 3500.0) * 0.08
        linea = sg.lp(r.standard_normal(n), 85.0, 2) * (1.0 + 0.12 * env_lp_noise(n, r, 0.2)) * 1.3
        tyres = sg.bp(r.standard_normal(n), 400.0, 2500.0, 2) * (0.25 + 0.75 * gust(n, r, 0.08, 0.9, 3.0)) * 0.12
        return loopify(w + linea + tyres)
    out = bed(wind, seed + 1)
    # le cupole: due toni che battono, l'ampiezza che respira in 8 s
    hum = sines([(96.0, 0.03), (97.5, 0.025), (192.0, 0.01), (288.0, 0.004)], N) * (1.0 + 0.35 * np.sin(2 * np.pi * 3 * t / DUR))
    out += pan2(hum, 0.2)
    # due droni lontani, con il doppler
    for t0, dur, fb, dist, g in ((2.5, 9.0, 183.0, 0.9, 0.12), (13.0, 9.5, 211.0, 1.3, 0.1)):
        x, p = drone_pass(t, t0, dur, fb, dist)
        x = sg.lp(x, 2200.0) + sg.bp(rng.standard_normal(N), 300.0, 1800.0, 2) * np.abs(x) * 0.6
        out += np.stack([x * np.sqrt(0.5 * (1 - p)), x * np.sqrt(0.5 * (1 + p))], axis=1) * g
    # l'avviso acustico delle elettriche, lontano dietro il muro: due note morbide che salgono con la velocità
    for t0, p in ((7.0, -0.6), (19.0, 0.5)):
        m = int(3.5 * SR)
        tt = np.arange(m) / SR
        f = 520.0 * (1.0 + 0.12 * np.sin(np.pi * tt / 3.5))
        ph = 2 * np.pi * np.cumsum(f) / SR
        avas = (np.sin(ph) + 0.5 * np.sin(1.5 * ph) + 0.2 * np.sin(2 * ph)) * np.sin(np.pi * tt / 3.5) ** 2
        x = np.zeros(N)
        put(x, sg.lp(avas, 1500.0), int(t0 * SR), 0.015)
        out += pan2(x, p)
    return out


def amb_garage_v2(seed: int) -> np.ndarray:
    """B4, il garage di Addolorata alle 16, rifatto. Il ronzio della lampada del banco è quello di un
    reattore a 100 Hz: ricco di armoniche, con il ronzio sporco sopra e un leggero sfarfallio. La pioggia
    sul lucernario cambia: gocce di misure diverse, il vetro che risuona appena, una raffica ogni tanto e il
    rivolo nella grondaia. Dal lucernario cade una goccia in un secchio di metallo, regolare."""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    # la pioggia sul vetro: densità che sale e scende (due raffiche nel loop, periodiche)
    dens = 1.0 + 0.6 * np.sin(2 * np.pi * 2 * t / DUR + 0.8) ** 2
    rate = 22.0 * dens
    cum = np.cumsum(rate) / SR
    times = np.searchsorted(cum, np.sort(rng.uniform(0, cum[-1], int(cum[-1]))))
    glass = [(1450.0, 0.010), (2380.0, 0.008), (3350.0, 0.006), (5100.0, 0.004)]
    for p in times:
        big = rng.random() < 0.18
        c = drop_click(rng, 1600.0 if big else 2400.0, 8500.0, rng.uniform(2.5, 6.0) if big else rng.uniform(1.0, 3.0))
        m = int(0.05 * SR)
        tt = np.arange(m) / SR
        ring = sum(rng.uniform(0.0, 0.35) * np.sin(2 * np.pi * f * rng.uniform(0.96, 1.04) * tt) * np.exp(-tt / d) for f, d in glass)
        d = np.zeros(m)
        d[:len(c)] += c[:m] * (0.7 if big else 0.45)
        d += 0.25 * ring
        x = np.zeros(N)
        put(x, d, int(p), rng.lognormal(-0.4, 0.5) * (1.6 if big else 1.0))
        out += pan2(x, rng.uniform(-0.6, 0.6))
    out = np.stack([circ_reverb(out[:, c], np.random.default_rng(seed + 3 + c), 0.4, 0.1, 5000.0, 0.6) for c in range(2)], axis=1)
    # la goccia nel secchio: 11 nei 24 s, a destra, «plonk» con un filo di metallo
    bucket = np.zeros(N)
    for i in range(11):
        tt = i * DUR / 11 + 0.4 + rng.normal(0.0, 0.025)
        b = bubble_drop(rng, 820.0 * rng.uniform(0.97, 1.03), 0.012, 0.25)
        q = int(0.12 * SR)
        tq = np.arange(q) / SR
        ring = sum(a * np.sin(2 * np.pi * f * tq) * np.exp(-tq / dd) for f, a, dd in ((415.0, 0.25, 0.05), (1130.0, 0.15, 0.03), (2140.0, 0.08, 0.02)))
        ring[:len(b)] += b
        put(bucket, ring, int(tt * SR), rng.uniform(0.85, 1.0))
    out += pan2(sg.impulse_tail(bucket, 0.3, 0.07, 3000.0, rng, 0.35)[:N], 0.55)
    # il rivolo nella grondaia e il rombo della pioggia sul tetto
    def roof(r):
        n = N + OV
        roar = sg.lp(sg.bp(r.standard_normal(n), 200.0, 2200.0, 2), 1800.0) * 0.3 * (1.0 + 0.15 * env_lp_noise(n, r, 0.3))
        trickle = sg.bp(r.standard_normal(n), 900.0, 2600.0, 2) * np.clip(env_lp_noise(n, r, 9.0), 0, None) * 0.06
        return loopify(roar + trickle)
    out += bed(roof, seed + 5) * (dens / dens.mean())[:, None] ** 0.5
    # il reattore della lampada: 100 Hz con armoniche fino a 2 kHz, saturato; il ronzio sporco
    # (rumore modulato a 100 Hz) e lo sfarfallio (cali brevi, 3 nel loop)
    ph = 2 * np.pi * 100.0 * t
    lamp = sum(np.sin(h * ph + 0.37 * h * h) / h ** 1.1 for h in range(1, 21))
    lamp = np.tanh(1.6 * lamp) * 0.045
    buzz = sg.lp(sg.hp(rng.standard_normal(N), 1500.0, 2), 6000.0, 2) * (0.5 + 0.5 * np.cos(ph)) ** 6 * 0.02
    flick = np.ones(N)
    for t0 in (4.2, 11.7, 19.3):
        flick -= 0.35 * np.exp(-((t - t0) / 0.08) ** 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 9.0 * (t - t0)))
    out += pan2((lamp + buzz) * flick, -0.25)
    return out


# v2: (funzione che fa lo stereo, LUFS integrati bersaglio, seme, perché)
AMBIENTI_V2 = {
    "amb_cimitero": (amb_cimitero_v2, -28.0, 21, "da solo nei tratti senza musica (A1-A4): 12 dB sotto la musica (-16), sotto le voci"),
    "amb_cantine": (amb_cantine_v2, -30.0, 25, "interno: silenzio abitato, 14 dB sotto la musica"),
    "amb_garage": (amb_garage_v2, -30.0, 26, "interno: la quiete prima del riavvio, 14 dB sotto la musica"),
}

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
# Guadagni fissi, che vincono sulla formula. 11 novembre 2026: il limitatore del Master lavorava di
# continuo (true peak -0,3 dBFS nel video degli effetti del prologo); i passi scendono di 4 dB.
MIX_FISSO = {"step_pietra_a": -12.0, "step_pietra_b": -12.5, "step_bagnato_a": -11.0,
             "step_bagnato_b": -11.0, "step_interno_a": -15.0, "step_interno_b": -12.5}


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
    ap.add_argument("--v2", action="store_true", help="solo gli ambienti rifatti l'11 novembre (cimitero, cantine, garage)")
    ap.add_argument("--install", action="store_true", help="genera la serie da installare e la copia in game/assets/sfx")
    a = ap.parse_args()
    if a.install and a.v2:
        ap.error("--install genera già la serie giusta (v2 dove c'è): niente --v2")
    a.out.mkdir(parents=True, exist_ok=True)
    rep, problems = {}, []
    if a.install:
        table = ambienti_da_installare()
    elif a.v2:
        table = {k: (lambda s, f=fn: f(s), t, sd, w) for k, (fn, t, sd, w) in AMBIENTI_V2.items()}
    else:
        table = {k: (lambda s, f=fn: stereo(f, s), t, sd, w) for k, (fn, t, sd, w) in AMBIENTI.items()}
    for name, (make, target, seed, why) in table.items():
        x = make(seed)
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
    for i, (name, (fn, f0, band)) in enumerate([] if a.v2 else PASSI.items()):
        rng = np.random.default_rng(20261111 + 104729 * i)
        raw = fn(rng, f0, band)
        x = sg.finish(name, raw, fade_in_ms=1.0, fade_out_ms=10.0)
        errs = sg.check(name, x)
        if errs:
            problems.append(f"{name}: " + "; ".join(errs))
        fl = sg.fast_loudness(x)
        mix[name] = MIX_FISSO.get(name, round(min(0.0, STEP_TARGET - fl) * 2) / 2)
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(sg.IMPORT_TEMPLATE, encoding="utf-8", newline="\n")
        rep[name] = {"dur_s": round(len(x) / SR, 4), "picco_dbfs": round(al.sample_peak_db(x), 2), "fast_lufs": round(fl, 2),
                     "altoparlante_piccolo_lufs": round(sg.small_speaker_loudness(x), 2), "centroide_hz": round(al.spectral_centroid(x, SR)),
                     "mix_db": mix[name], "livello_nel_gioco_fast_lufs": round(fl + mix[name], 2)}
        print(f"{name:20s} {len(x)/SR*1000:5.0f}ms  fast {fl:6.1f}  piccolo {rep[name]['altoparlante_piccolo_lufs']:6.1f}  mix {mix[name]:5.1f}  nel gioco {rep[name]['livello_nel_gioco_fast_lufs']:6.1f}")
    if not a.v2:
        (a.out / "mix_prova.json").write_text(json.dumps({"format": 1, "comment": "Guadagni dei passi nuovi (bersaglio fast %.0f LUFS)" % STEP_TARGET, "gain_db": mix}, indent=1) + "\n", encoding="utf-8", newline="\n")
    (a.out / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("OK")
    if a.install:
        return install(a.out, list(table), mix, rep)
    return 0


def install(out: Path, ambienti: list[str], mix: dict[str, float], rep: dict) -> int:
    """Ambienti in OGG q4 (giunto rimisurato sull'OGG decodificato) e passi in WAV, poi le righe di mix.json."""
    problems, pairs = [], []
    ogg_dir = out / "ogg"
    ogg_dir.mkdir(exist_ok=True)
    for name in ambienti:
        ogg = ogg_dir / f"{name}.ogg"
        ogg_encode(out / f"{name}.wav", ogg)
        (ogg_dir / f"{name}.ogg.import").write_text(OGG_IMPORT, encoding="utf-8", newline="\n")
        y = ogg_decode(ogg)
        s = seam_report(y)
        rep[name]["ogg"] = {"kb": round(ogg.stat().st_size / 1024), "campioni": len(y), "campioni_wav": N,
                            "lufs": round(al.integrated_loudness(y, SR), 2), "true_peak_dbtp": round(al.true_peak_db(y), 2),
                            "giunto": s}
        print(f"{name + '.ogg':24s} {rep[name]['ogg']['kb']:5d} kB  campioni {len(y)} (wav {N})  TP {rep[name]['ogg']['true_peak_dbtp']:6.1f}  "
              f"giunto {s}  (wav {rep[name]['giunto']})")
        if len(y) != N:
            problems.append(f"{name}.ogg: {len(y)} campioni invece di {N}: il loop non torna")
        if s["click_vs_rms"] > 4.0:
            problems.append(f"{name}.ogg: clic al giunto {s['click_vs_rms']}")
        pairs += [(ogg, GAME_AMB / ogg.name), (ogg_dir / f"{name}.ogg.import", GAME_AMB / f"{name}.ogg.import")]
    for name in mix:
        pairs += [(out / f"{name}.wav", GAME_SFX / f"{name}.wav"), (out / f"{name}.wav.import", GAME_SFX / f"{name}.wav.import")]
    (out / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if problems:
        print("PROBLEMI (niente installato):\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    install_files(pairs)
    new = merge_mix(mix)
    print(f"installati {len(pairs)} file; righe nuove in mix.json: {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
