"""I suoni degli eventi del prologo di CTRL+ALT REVENGE, sintetizzati dal codice (nessun campione di terzi).

Sono i 10 eventi del §6 di `.claude/sessioni/effetti-nel-gioco.md`, che oggi suonano con un segnaposto:
il tuono lontano, i colpi alla porta, il riavvio e i registri, i tre tasti, la Vedetta, i passi dei rider,
il laser e il sigillo del messo, la serranda e il cancello, la tosse, il braccio a vuoto e il taglio
dell'hacking. Siamo nel 2087: i suoni dicono l'anno con i servomotori, gli elettromagneti, i bip di
SIDERA e i droni, con la resa di oggi (niente chiptune).

Usa i mattoni di sfx_gen.py e amb_gen.py. Semi fissi: rigenerare dà gli stessi file.
- Gli eventi sono mono, alla stessa intensità percepita fra loro (REF_FAST, loudness veloce di 100 ms,
  pesata K) con il picco vero sotto TP_MAX; il livello nel gioco lo dà il guadagno proposto (MIX).
- I due loop (Vedetta, rider fuori campo) hanno il giunto pulito per costruzione e il livello integrato.

  python -I tools/audio/eventi_gen.py --out <cartella>    # WAV, .import, mix_prova.json, report.json, tavole

La cartella di prova sta nel laboratorio (%USERPROFILE%\\ctrlaltrevenge-lab\\sfx\\_prova_2026-11-11\\eventi\\):
Installati l'11 novembre 2026, su scelta di Luigi:

  python -I tools/audio/eventi_gen.py --out <cartella> --install
      # genera, controlla e copia in game/assets/sfx/ i WAV con il loro .import;
      # in mix.json aggiunge solo le righe degli eventi (i loop hanno il livello nel file)
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
import amb_gen as ag  # noqa: E402

SR = sg.SR
REF_FAST = -14.0       # tutti i file degli eventi a questa loudness veloce: stessa intensità percepita
TP_MAX = -1.0          # picco vero massimo (dBTP)
# Guadagni fissi, che vincono sulla formula. 11 novembre 2026: il limitatore del Master lavorava di
# continuo (true peak -0,3 dBFS nel video degli effetti del prologo); scendono i suoni che erano sopra 0.
MIX_FISSO = {"porta_colpo_a": -2.5, "porta_colpo_b": -2.5, "sigillo_a": -2.5,
             "porta_colpo_c": -2.0, "porta_sfondata": -2.0, "laser_segno": -2.0}


# ----------------------------------------------------------------------------- mattoni

def n_of(d: float) -> int:
    return sg.n_of(d)


def tv(n: int) -> np.ndarray:
    return np.arange(n) / SR


def at(x: np.ndarray, d: float, n: int) -> np.ndarray:
    """x ritardato di d secondi, dentro un buffer lungo n. Gli ultimi 8 ms del pezzo sfumano: un
    risuonatore troncato (dal suo buffer o da quello di arrivo) non deve fare clic."""
    y = np.zeros(n)
    i = n_of(d)
    if i < n:
        m = min(len(x), n - i)
        seg = np.array(x[:m], dtype=float)
        f = min(m, n_of(0.008))
        if f > 1:
            seg[-f:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, f + 1) / f)
        y[i:i + m] = seg
    return y


def nz(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def harm(f: np.ndarray, n: int, amps: list[float], phase: float = 0.0) -> np.ndarray:
    """Tono con armoniche (ampiezze date) su una frequenza che può variare nel tempo."""
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(np.asarray(f, dtype=float), (n,))) / SR + phase
    return sum(a * np.sin((h + 1) * ph) for h, a in enumerate(amps))


def resonate(x: np.ndarray, f: float, q: float) -> np.ndarray:
    b, a = signal.iirpeak(f, q, fs=SR)
    return signal.lfilter(b, a, x)


def room(x: np.ndarray, rng: np.random.Generator, tail: float, tau: float, lp_hz: float, wet: float) -> np.ndarray:
    return sg.impulse_tail(x, tail, tau, lp_hz, rng, wet)


def beep(n: int, f: float, dur: float, delay: float, amp: float, h3: float = 0.0) -> np.ndarray:
    """Bip pulito (SIDERA): sinusoide con attacco e rilascio morbidi di 3 ms."""
    m = n_of(dur)
    t = tv(m)
    e = np.minimum(1.0, np.minimum(t / 0.003, (dur - t) / 0.003)).clip(0, 1)
    b = (np.sin(2 * np.pi * f * t) + h3 * np.sin(2 * np.pi * 3 * f * t)) * e * amp
    return at(b, delay, n)


# ----------------------------------------------------------------------------- 1. il tuono lontano

def tuono(rng: np.random.Generator, vicino: float) -> np.ndarray:
    """Tuono lontano (B, il terzo tasto): niente schiocco, un rotolare basso che va e viene.
    `vicino` 0..1 aggiunge un po' di crepitio e un attacco più netto."""
    dur = 6.5
    n = n_of(dur)
    base = sg.lp(nz(n, rng), 160.0 + 260.0 * vicino, 2) + 0.9 * sg.lp(nz(n, rng), 55.0, 2)
    env = np.zeros(n)
    t0 = rng.uniform(0.12, 0.25)
    for k in range(int(rng.integers(4, 7))):
        a = rng.uniform(0.5, 1.0) * np.exp(-k * 0.35)
        att = rng.uniform(0.12, 0.3) * (1.0 - 0.6 * vicino) if k == 0 else rng.uniform(0.15, 0.4)
        env += a * sg.env_ar(n, att, rng.uniform(0.5, 1.2), t0)
        t0 += rng.uniform(0.35, 1.1)
    flutter = np.clip(1.0 + 0.55 * ag.env_lp_noise(n, rng, 9.0), 0.15, None)
    y = base * env * flutter
    if vicino > 0:
        cr = sg.bp(sg.crackles(n, rng, 260.0, 0.5, 300.0, (1.0, 6.0)), 500.0, 2600.0, 2)
        y += vicino * 0.5 * cr * sg.env_ar(n, 0.02, 0.5, 0.15) / (np.max(np.abs(cr)) + 1e-9) * np.max(np.abs(y))
    y = sg.lp(y, 700.0 + 1600.0 * vicino, 2)
    return room(y, rng, 1.8, 0.7, 500.0, 0.5)[: n_of(dur + 1.0)]


# ----------------------------------------------------------------------------- 2. i colpi alla porta

PORTA_MODI = [87.0, 131.0, 178.0, 236.0, 301.0, 388.0, 470.0, 612.0, 790.0, 1030.0]


def porta_colpo(rng: np.random.Generator, forza: float) -> np.ndarray:
    """Un colpo sulla porta basculante di lamiera del garage, sentito da dentro. Prima del colpo un
    servomotore che carica (il braccio MANODOPERA dell'Esattore): è il 2087. Dopo, la porta trema nel telaio."""
    n = n_of(1.0)
    d = 0.06
    servo = harm(sg.glide(n_of(0.07), 700.0, 1350.0, 0.03), n_of(0.07), [1.0, 0.35, 0.2]) * sg.env_bell(n_of(0.07), 0.045, 0.025)
    y = at(servo * 0.05 * forza, 0.0, n)
    s = rng.uniform(0.94, 1.06)
    thump = sg.layer_body(n, 92.0 * s, 52.0 * s, 0.02, 0.09 + 0.03 * forza, 1.6, 1.0)
    decs = [0.42, 0.38, 0.3, 0.26, 0.2, 0.17, 0.13, 0.1, 0.08, 0.06]
    amps = [1.0, 0.8, 0.7, 0.55, 0.5, 0.4, 0.3, 0.22, 0.15, 0.1]
    panel = sg.modal(n, [f * s * rng.uniform(0.97, 1.03) for f in PORTA_MODI], decs, amps, rng, detune=0.012)
    boom = sg.layer_noise_band(n, rng, 140.0, 900.0, 0.001, 0.08, 0.5)
    tr = sg.layer_transient(n, rng, 1500.0, 0.004, 0.45)
    rattle = sg.bp(sg.crackles(n, rng, 160.0 + 90 * forza, 0.18, 600.0, (1.0, 4.0)), 700.0, 4200.0, 2)
    rattle = rattle / (np.max(np.abs(rattle)) + 1e-9) * 0.25 * forza
    hit = thump + 0.7 * panel + 1.6 * boom + tr + at(rattle, 0.012, n)
    y += at(sg.sat(hit * (0.6 + 0.5 * forza), 1.3), d, n)
    return room(y, rng, 0.5, 0.12, 2500.0, 0.35)


def porta_sfondata(rng: np.random.Generator) -> np.ndarray:
    """La porta cede: l'ultimo colpo, la lamiera che si piega, la serratura che salta e la porta a terra."""
    n = n_of(2.4)
    y = porta_colpo(rng, 1.3)[:n]
    y = np.concatenate([y, np.zeros(max(0, n - len(y)))])
    # la lamiera che si piega: parziali che scendono, con attrito
    m = n_of(0.45)
    groan = sum(a * sg.osc_sine(sg.glide(m, f, f * 0.82, 0.18), m) for f, a in [(148.0, 1.0), (233.0, 0.6), (371.0, 0.45), (590.0, 0.3), (905.0, 0.18)])
    groan = groan * sg.env_bell(m, 0.06, 0.35) * (0.7 + 0.3 * np.clip(ag.env_lp_noise(m, rng, 40.0), -1, 1))
    groan += 0.4 * sg.bp(nz(m, rng), 400.0, 2500.0, 2) * sg.env_bell(m, 0.05, 0.3)
    y += at(groan * 0.35, 0.1, n)
    # la serratura che salta
    k = n_of(0.12)
    snap = sg.layer_transient(k, rng, 3000.0, 0.003, 1.0) + sg.modal(k, [2140.0, 3420.0, 5050.0], [0.05, 0.035, 0.02], [1.0, 0.6, 0.4], rng)
    y += at(snap * 0.6, 0.2, n)
    # la porta a terra, e due rimbalzi
    for tt, g in [(0.78, 1.0), (0.93, 0.35), (1.02, 0.18)]:
        q = n_of(1.2)
        slam = sg.layer_body(q, 75.0, 42.0, 0.03, 0.12, 2.0, 1.0) + 0.4 * sg.modal(q, [f * 0.9 for f in PORTA_MODI], [0.5, 0.4, 0.32, 0.26, 0.2, 0.16, 0.12, 0.1, 0.08, 0.06], [1, .8, .7, .55, .5, .4, .3, .22, .15, .1], rng, detune=0.015)
        slam += sg.layer_noise_band(q, rng, 200.0, 3000.0, 0.001, 0.06, 0.6) + sg.layer_transient(q, rng, 1200.0, 0.006, 0.5)
        y += at(sg.sat(slam * g, 1.4), tt, n)
    deb = sg.bp(sg.crackles(n_of(1.0), rng, 90.0, 0.4, 1500.0, (0.5, 3.0)), 1500.0, 7000.0, 2)
    y += at(deb / (np.max(np.abs(deb)) + 1e-9) * 0.15, 0.85, n)
    return room(y, rng, 0.8, 0.18, 2200.0, 0.4)


# ----------------------------------------------------------------------------- 3. il riavvio e i registri

def riavvio_ronzio(rng: np.random.Generator) -> np.ndarray:
    """«Un ronzio basso che sale» (Tere e l'occhio cyan): il braccio che si ricarica dopo vent'anni.
    La fondamentale sale da 38 a 110 Hz, le armoniche si accendono, sopra fischia il condensatore."""
    dur = 2.6
    n = n_of(dur)
    t = tv(n)
    u = t / dur
    f = 38.0 * (110.0 / 38.0) ** (u ** 1.6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    bright = 0.25 + 0.6 * u
    hum = sum((bright ** h) / (h + 1) * np.sin((h + 1) * ph) for h in range(12))
    hum = sg.sat(hum, 1.5)
    whine = sg.osc_sine(2800.0 * (3.2 ** u), n) * (0.008 + 0.05 * u ** 2)
    cr = sg.crackles(n, rng, 40.0, 1e9, 2500.0, (0.3, 1.2)) * (u ** 2) * 0.35
    lvl = 10 ** ((-14.0 + 14.0 * u) / 20)
    e = np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return (hum * lvl + whine + cr * lvl) * e


def riavvio_scarica(rng: np.random.Generator) -> np.ndarray:
    """L'evento 'reboot': il relè che scatta, la scarica bianca e gli anelli del braccio che si
    accendono uno dopo l'altro (campanelle FM, non chiptune), poi il braccio che resta acceso."""
    n = n_of(2.0)
    k = n_of(0.08)
    clack = sg.layer_transient(k, rng, 2000.0, 0.003, 0.8) + sg.modal(k, [1900.0, 3100.0], [0.02, 0.012], [0.6, 0.4], rng)
    y = at(clack, 0.0, n)
    m = n_of(0.35)
    zap = sg.osc_fm(sg.glide(m, 2600.0, 260.0, 0.06), 1.41, sg.glide(m, 7.0, 1.0, 0.08), m) * sg.env_ar(m, 0.002, 0.09)
    zap += 0.7 * sg.hp(nz(m, rng), 1500.0, 2) * sg.env_ar(m, 0.001, 0.05)
    y += at(zap * 0.7, 0.03, n)
    y += at(sg.layer_body(n_of(0.6), 72.0, 40.0, 0.04, 0.22, 1.8, 0.8), 0.03, n)
    for i, f in enumerate([659.3, 784.0, 987.8, 1174.7, 1318.5]):
        q = n_of(0.6)
        b = sg.osc_fm(f, 2.0, 1.2 * sg.env_exp(q, 0.08), q) + 0.6 * sg.osc_fm(f * 1.004, 2.0, sg.env_exp(q, 0.1), q)
        y += at(b * sg.env_ar(q, 0.003, 0.22) * 0.22, 0.26 + 0.1 * i, n)
    q = n_of(1.6)
    tq = tv(q)
    thr = harm(110.0, q, [1.0, 0.5, 0.3, 0.15]) * sg.env_bell(q, 0.35, 1.25) * (1.0 + 0.1 * np.sin(2 * np.pi * 6.0 * tq))
    y += at(thr * 0.12, 0.3, n)
    return room(y, rng, 0.9, 0.25, 5000.0, 0.3)


def registro_clic(rng: np.random.Generator) -> np.ndarray:
    """Il braccio nella culla del registro: il fermo che scatta e il magnete che tira giù."""
    n = n_of(0.2)
    k = sg.layer_transient(n, rng, 2000.0, 0.002, 0.7) + sg.modal(n, [2800.0, 4100.0], [0.015, 0.01], [0.5, 0.3], rng)
    th = sg.layer_body(n, 125.0, 80.0, 0.012, 0.03, 1.5, 0.8) + sg.layer_noise_band(n, rng, 500.0, 1800.0, 0.001, 0.015, 0.25)
    return room(k + at(th, 0.022, n), rng, 0.2, 0.04, 4000.0, 0.2)


def registro_ronzio(rng: np.random.Generator) -> np.ndarray:
    """La copia: un ronzio che sale (dal tick 6 al lampo del tick 34: 0,47 s) e il chiacchiericcio dei dati."""
    dur = 0.6
    n = n_of(dur)
    t = tv(n)
    u = np.clip(t / 0.5, 0, 1)
    f = 70.0 * (3.0 ** u)
    hum = harm(f, n, [1.0, 0.6, 0.45, 0.3, 0.2, 0.12]) * (0.3 + 0.7 * u)
    chat = np.zeros(n)
    tt = 0.03
    while tt < 0.5:
        q = n_of(0.008)
        chat += at(np.sin(2 * np.pi * rng.uniform(2200, 5200) * tv(q)) * np.hanning(q), tt, n) * rng.uniform(0.3, 1.0)
        tt += rng.exponential(0.04 * (1.0 - 0.7 * tt / 0.5))
    e = np.clip(t / 0.03, 0, 1) * np.clip((dur - t) / 0.1, 0, 1)
    return (sg.sat(hum, 1.4) + 0.18 * chat) * e


def registro_lampo(rng: np.random.Generator) -> np.ndarray:
    """«Il bip di SIDERA che diventa cyan»: un bip sterile (sinusoide pura) che si scalda, si allarga
    in un coro e sale di una quarta, con un luccichio sopra."""
    dur = 0.6
    n = n_of(dur)
    t = tv(n)
    y = beep(n, 1568.0, 0.1, 0.0, 0.6)
    m = n_of(0.5)
    tm = tv(m)
    f = 1568.0 * (1.0 + (4 / 3 - 1) * (1 - np.exp(-tm / 0.05)))
    warm = sum(sg.osc_fm(f * d, 1.0, 0.8 * sg.env_exp(m, 0.2), m) for d in (0.996, 1.0, 1.005)) / 3
    warm *= sg.env_ar(m, 0.01, 0.16)
    y += at(warm * 0.7, 0.08, n)
    sh = sg.hp(nz(n, rng), 6000.0, 2) * sg.env_ar(n, 0.02, 0.12, 0.09) * 0.12
    return room(y + sh, rng, 0.5, 0.12, 7000.0, 0.25)


# ----------------------------------------------------------------------------- 4. i tre tasti e lo spinotto

def tasto(rng: np.random.Generator, tono: float, naso: bool = False) -> np.ndarray:
    """Un tasto della vecchia tastiera meccanica di Vito, sul banco del garage: lo scatto (con la molla
    che canta un po', è vecchia), il fondo corsa sulla plastica ingiallita, il banco sotto.
    Col naso: corsa più lenta, un attimo di strisciata, il fondo più morbido, ma il clic resta netto."""
    n = n_of(0.16)
    t0 = 0.018 if naso else 0.006
    y = np.zeros(n)
    if naso:
        y += sg.layer_noise_band(n, rng, 1500.0, 5000.0, 0.008, 0.006, 0.06)
    y += at(sg.layer_transient(n_of(0.02), rng, 3000.0, 0.0015, 0.6) + sg.modal(n_of(0.02), [3800.0 * tono, 5200.0 * tono], [0.012, 0.008], [0.5, 0.3], rng), t0, n)
    b0 = t0 + (0.014 if naso else 0.008)
    thock = sg.modal(n_of(0.1), [420.0 * tono, 980.0 * tono, 1650.0 * tono], [0.03, 0.02, 0.012], [1.0, 0.6, 0.35], rng, detune=0.01)
    thock += sg.layer_body(n_of(0.1), 180.0 * tono, 140.0 * tono, 0.01, 0.015, 1.3, 0.5)
    y += at(thock * (0.45 if naso else 0.8), b0, n)
    y += at(sg.modal(n_of(0.1), [4600.0 * tono], [0.04], [1.0], rng), b0, n) * 0.08
    y += at(sg.layer_body(n_of(0.1), 110.0, 90.0, 0.02, 0.04, 1.2, 0.15), b0, n)
    return room(y, rng, 0.25, 0.05, 4000.0, 0.22)


def spinotto(rng: np.random.Generator) -> np.ndarray:
    """L'evento 'keyboard': lo sportello della porta di servizio sul braccio morto e lo spinotto che entra."""
    n = n_of(0.32)
    y = sg.layer_noise_band(n, rng, 1000.0, 6000.0, 0.03, 0.02, 0.12)
    k = n_of(0.15)
    latch = sg.layer_transient(k, rng, 2500.0, 0.002, 0.7) + sg.modal(k, [2200.0, 3500.0, 5300.0], [0.02, 0.014, 0.008], [0.5, 0.35, 0.2], rng)
    latch += sg.layer_body(k, 160.0, 110.0, 0.01, 0.025, 1.4, 0.6)
    y += at(latch, 0.09, n)
    cr = sg.crackles(n_of(0.12), rng, 200.0, 0.04, 4000.0, (0.2, 0.8))
    y += at(cr / (np.max(np.abs(cr)) + 1e-9) * 0.12, 0.1, n)
    return room(y, rng, 0.25, 0.05, 4000.0, 0.2)


# ----------------------------------------------------------------------------- 5. la Vedetta

VEDETTA_LOOP = 4.0


def loop_noise(n_loop: int, ov: int, make) -> np.ndarray:
    """Rumore lungo n_loop+ov raccordato su sé stesso (dissolvenza a potenza costante)."""
    x = make(n_loop + ov)
    y = x[:n_loop].copy()
    th = np.linspace(0.0, np.pi / 2, ov)
    y[:ov] = np.sin(th) * x[:ov] + np.cos(th) * x[n_loop:n_loop + ov]
    return y


def per(f: float, dur: float) -> float:
    """La frequenza più vicina che fa cicli interi in dur secondi."""
    return round(f * dur) / dur


def vedetta_loop(rng: np.random.Generator) -> np.ndarray:
    """Il ronzio della Vedetta in volo (loop di 4 s, mono, da posizionare): quattro eliche con il
    passaggio delle pale vicino a 150 Hz che battono fra loro, il soffio delle pale modulato, il fischio
    dei motori elettrici. Tutti i toni fanno cicli interi nei 4 s."""
    L = VEDETTA_LOOP
    n = n_of(L)
    t = tv(n)
    y = np.zeros(n)
    bpf = [per(f, L) for f in (148.0, 151.5, 155.25, 159.0)]
    mod = np.zeros(n)
    for i, f in enumerate(bpf):
        ph = rng.uniform(0, 2 * np.pi)
        y += sum(a * np.sin(2 * np.pi * (h + 1) * f * t + ph * (h + 1)) for h, a in enumerate([1.0, 0.55, 0.35, 0.22, 0.12, 0.07]))
        mod += (0.5 + 0.5 * np.cos(2 * np.pi * f * t + ph)) ** 3
    mod /= len(bpf)
    wash = loop_noise(n, n_of(0.5), lambda m: sg.bp(nz(m, rng), 250.0, 2600.0, 2))
    wash = wash / np.std(wash) * (0.35 + 0.65 * mod)
    whine = sum(a * np.sin(2 * np.pi * per(f, L) * t) for f, a in [(2400.0, 1.0), (2412.0, 0.8), (4810.0, 0.25)])
    return 0.25 * y + 0.5 * wash + 0.05 * whine


def vedetta_faro(rng: np.random.Generator) -> np.ndarray:
    """L'evento 'faro_rosso': il faro gira sul giunto (servo) e, quando prende GIG, si fa rosso con un
    doppio tono che sale. Freddo e aziendale, ma non è la sirena."""
    n = n_of(0.75)
    m = n_of(0.3)
    servo = harm(sg.glide(m, 600.0, 1100.0, 0.1), m, [1.0, 0.4, 0.25]) * sg.env_bell(m, 0.05, 0.22) * 0.25
    sweep = sg.svf_bandpass(nz(m, rng), np.geomspace(2000.0, 6500.0, m), 5.0) * sg.env_bell(m, 0.08, 0.2)
    gate = (np.sin(2 * np.pi * 32.0 * tv(m)) > 0.2).astype(float)
    sweep *= sg.lp(gate, 400.0, 2) * 0.25
    y = at(servo + sweep, 0.0, n)
    y += beep(n, 988.0, 0.09, 0.28, 0.5, h3=0.12) + beep(n, 1480.0, 0.16, 0.4, 0.5, h3=0.12)
    return room(y, rng, 0.4, 0.1, 5000.0, 0.25)


# ----------------------------------------------------------------------------- 6. i rider sotto la pioggia

RIDER_LOOP = 12.0


def rider_passo(rng: np.random.Generator, f0: float, peso: float = 1.0) -> np.ndarray:
    """Un passo di rider sull'asfalto bagnato: stivale più pesante di quello di GIG e l'attrezzatura che
    tintinna (il corpetto, le fibbie)."""
    x = ag.step_bagnato(rng, f0, (1300.0, 4600.0))
    n = len(x) + n_of(0.04)
    y = np.concatenate([x, np.zeros(n - len(x))]) * peso
    jing = sg.bp(sg.crackles(n, rng, 600.0, 0.03, 3000.0, (0.2, 0.6)), 3000.0, 7500.0, 2)
    y += at(jing / (np.max(np.abs(jing)) + 1e-9) * 0.08, 0.01, n)
    return y


def rider_passi_loop(rng: np.random.Generator) -> np.ndarray:
    """I passi dei rider fuori campo, per tutta la fuga (loop di 12 s, stereo): tre rider che corrono,
    ognuno col suo passo, che si avvicinano e si allontanano (periodi interi nel loop), con l'eco delle
    facciate e la distanza (passa-basso)."""
    L = RIDER_LOOP
    n = n_of(L)
    out = np.zeros((n, 2))
    t = tv(n)
    for r in range(3):
        rate = rng.uniform(2.6, 3.1)
        pan = rng.uniform(-0.7, 0.7)
        k = int(rng.integers(1, 3))
        phi = rng.uniform(0, 2 * np.pi)
        swell = 0.5 + 0.5 * np.cos(2 * np.pi * k * t / L + phi)
        mono = np.zeros(n)
        tt = rng.uniform(0, 0.3)
        f0 = rng.uniform(118.0, 140.0)
        while tt < L:
            p = sg.lp(rider_passo(rng, f0 * rng.uniform(0.95, 1.05), rng.uniform(0.7, 1.0)), 2600.0, 2)
            ag.put(mono, p, n_of(tt), 0.25 + 0.75 * swell[n_of(tt) % n])
            tt += (1.0 / rate) * rng.uniform(0.93, 1.07)
        # eco delle facciate (circolare: resta nel loop)
        ech = np.roll(mono, n_of(rng.uniform(0.09, 0.14))) * 0.28
        out[:, 0] += mono * np.sqrt(0.5 * (1 - pan)) + ech * np.sqrt(0.5 * (1 + pan))
        out[:, 1] += mono * np.sqrt(0.5 * (1 + pan)) + ech * np.sqrt(0.5 * (1 - pan))
    return out


# ----------------------------------------------------------------------------- 7. il laser e il sigillo

def laser_mira(rng: np.random.Generator) -> np.ndarray:
    """La penna laser del messo che mira: un fischio sottile che sale, con un tremolio, e un ronzio sotto."""
    dur = 0.7
    n = n_of(dur)
    t = tv(n)
    f = 2200.0 * (5200.0 / 2200.0) ** np.clip(t / 0.5, 0, 1) * (1.0 + 0.015 * np.sin(2 * np.pi * 30.0 * t))
    y = sg.osc_sine(f, n) * 0.5 + 0.15 * harm(120.0, n, [1.0, 0.4, 0.2])
    y += 0.06 * sg.bp(nz(n, rng), 5000.0, 9000.0, 2)
    e = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return y * e


def laser_segno(rng: np.random.Generator) -> np.ndarray:
    """Il laser prende il braccio: lo sfrigolio del segno e il bip dello scanner che registra il bene pignorato."""
    n = n_of(0.45)
    cr = sg.crackles(n, rng, 900.0, 0.12, 2500.0, (0.2, 1.0))
    y = cr / (np.max(np.abs(cr)) + 1e-9) * 0.5 + sg.layer_noise_band(n, rng, 3000.0, 8000.0, 0.002, 0.06, 0.4)
    y += beep(n, 2730.0, 0.08, 0.06, 0.45, h3=0.15)
    y += sg.layer_body(n, 160.0, 120.0, 0.01, 0.03, 1.2, 0.25)
    return y


def sigillo(rng: np.random.Generator, tono: float) -> np.ndarray:
    """Il sigillo «PIGNORATO» che si chiude sul braccio: la morsa magnetica, il ronzio dell'elettromagnete
    e il doppio tono di SIDERA che conferma (scende)."""
    n = n_of(0.65)
    y = sg.layer_transient(n, rng, 1800.0, 0.003, 0.6)
    y += sg.layer_body(n, 140.0 * tono, 70.0 * tono, 0.02, 0.05, 2.0, 1.0)
    y += 0.8 * sg.modal(n, [520.0 * tono, 1340.0 * tono, 2210.0 * tono], [0.12, 0.08, 0.05], [1.0, 0.6, 0.35], rng)
    q = n_of(0.3)
    buzz = sg.sat(harm(100.0, q, [1.0, 0.7, 0.5, 0.35, 0.25]), 2.0) * sg.env_ar(q, 0.01, 0.12) * 0.25
    y += at(buzz, 0.02, n)
    y += beep(n, 1318.5 * tono, 0.07, 0.2, 0.3) + beep(n, 987.8 * tono, 0.12, 0.29, 0.3)
    return room(y, rng, 0.35, 0.08, 3500.0, 0.25)


# ----------------------------------------------------------------------------- 8. la serranda e il cancello

def serranda(rng: np.random.Generator) -> np.ndarray:
    """La serranda della cantina che scende (motorizzata, è il 2087): il motore che tira, le stecche che
    sbattono una dopo l'altra sempre più in fretta, il colpo a terra."""
    n = n_of(2.0)
    t = tv(n)
    mot = harm(180.0 * (1 + 0.06 * np.clip(t / 1.3, 0, 1)), n, [1.0, 0.5, 0.3, 0.2, 0.1]) * sg.env_bell(n, 0.08, 1.25) * 0.12
    y = mot
    tt, gap = 0.06, 0.07
    while tt < 1.28:
        k = n_of(0.12)
        c = sg.layer_transient(k, rng, 1500.0, 0.002, 0.5)
        c += sg.modal(k, list(rng.uniform(700.0, 2600.0, 3)), [0.06, 0.05, 0.04], [0.6, 0.4, 0.3], rng, detune=0.01)
        y += at(c * rng.uniform(0.35, 0.65), tt, n)
        tt += gap * rng.uniform(0.85, 1.15)
        gap = max(0.04, gap * 0.97)
    y += sg.bp(nz(n, rng), 800.0, 4000.0, 2) * sg.env_bell(n, 0.1, 1.15) * 0.08
    q = n_of(0.7)
    slam = sg.layer_body(q, 90.0, 50.0, 0.02, 0.08, 2.0, 1.0) + sg.layer_transient(q, rng, 1200.0, 0.004, 0.5)
    slam += 0.45 * sg.modal(q, [180.0, 410.0, 730.0, 1150.0], [0.3, 0.2, 0.15, 0.1], [1.0, 0.7, 0.5, 0.3], rng, detune=0.012)
    y += at(slam, 1.3, n)
    return room(y, rng, 0.5, 0.12, 3000.0, 0.3)


def cancello(rng: np.random.Generator, tono: float) -> np.ndarray:
    """Il cancello che si richiude dopo l'hacking (gate_close): l'attuatore che spinge, il ferro che sbatte
    e risuona, la serratura elettromagnetica che si chiude."""
    n = n_of(1.3)
    m = n_of(0.3)
    act = harm(sg.glide(m, 240.0, 320.0, 0.1), m, [1.0, 0.5, 0.3]) * sg.env_bell(m, 0.05, 0.25) * 0.15
    y = at(act, 0.0, n)
    q = n_of(1.0)
    clang = sg.modal(q, [f * tono for f in (212.0, 471.0, 763.0, 1190.0, 1655.0, 2310.0)], [0.6, 0.45, 0.35, 0.25, 0.18, 0.12], [1.0, 0.8, 0.6, 0.45, 0.3, 0.2], rng, detune=0.008)
    clang = 0.6 * clang + sg.layer_transient(q, rng, 1500.0, 0.004, 0.6) + sg.layer_body(q, 110.0, 70.0, 0.02, 0.06, 1.6, 0.6)
    y += at(clang, 0.27, n)
    k = n_of(0.3)
    lock = sg.layer_body(k, 150.0, 100.0, 0.01, 0.03, 1.5, 0.4) + sg.sat(harm(100.0, k, [1.0, 0.6, 0.4]), 1.8) * sg.env_ar(k, 0.005, 0.05) * 0.15
    y += at(lock, 0.42, n)
    y += beep(n, 880.0, 0.1, 0.5, 0.15)
    return room(y, rng, 0.6, 0.15, 3500.0, 0.3)


# ----------------------------------------------------------------------------- 9. la tosse

def tosse_colpo(rng: np.random.Generator, f0: float, dur: float, forza: float) -> np.ndarray:
    """Un colpo di tosse di GIG (50 anni, nella polvere): tre fasi, come nella tosse vera.
    1. lo scoppio: la glottide si apre di colpo, rumore largo per 20-30 ms;
    2. il soffio: rumore turbolento con le formanti di una vocale aperta e scura, che cala;
    3. la voce: la glottide si richiude vibrando, raschiata (impulsi irregolari, jitter e shimmer).
    Sotto, il colpo del petto. Sintesi a formanti."""
    n = n_of(dur)
    t = tv(n)
    f = f0 * (1.0 + 0.04 * ag.env_lp_noise(n, rng, 30.0)) * (1.0 - 0.18 * t / dur)
    ph = np.cumsum(f) / SR
    pulses = np.diff(np.floor(ph), prepend=0.0) * np.clip(1.0 + 0.35 * rng.standard_normal(n), 0.2, None)
    voiced = sg.lp(pulses, 2200.0, 2)
    voiced /= np.max(np.abs(voiced)) + 1e-9
    burst = sg.hp(nz(n, rng), 150.0, 2) * sg.env_ar(n, 0.0015, 0.018)
    turb = nz(n, rng) * sg.env_ar(n, 0.006, 0.075, 0.008)
    rasp = voiced * sg.env_bell(n, 0.04, dur * 0.55, dur * 0.3) * (1.0 + 0.5 * np.clip(ag.env_lp_noise(n, rng, 60.0), -1, 1))
    src = 0.6 * turb + 0.7 * rasp
    y = 1.2 * sg.bp(burst, 250.0, 5000.0, 1)
    for fr, q, g in [(680.0, 3.5, 1.0), (1150.0, 5.0, 0.7), (2500.0, 7.0, 0.35), (3400.0, 8.0, 0.15)]:
        y += g * resonate(src, fr * rng.uniform(0.95, 1.05), q)
    y += sg.layer_body(n, 120.0, 85.0, 0.015, 0.035, 1.4, 0.45)
    return y * forza


def respiro(rng: np.random.Generator) -> np.ndarray:
    """Il respiro corto e rauco prima di tossire."""
    n = n_of(0.16)
    x = sg.bp(nz(n, rng), 900.0, 4000.0, 2) * sg.env_bell(n, 0.12, 0.04)
    return 0.12 * (x + 0.6 * resonate(x, 1800.0, 6.0))


def tosse(rng: np.random.Generator, colpi: list[tuple[float, float]]) -> np.ndarray:
    pre = 0.16 if len(colpi) > 1 else 0.0
    n = n_of(pre + colpi[-1][0] + 0.5)
    y = at(respiro(rng), 0.0, n) if pre else np.zeros(n)
    for tt, g in colpi:
        y += at(tosse_colpo(rng, rng.uniform(100.0, 120.0), rng.uniform(0.2, 0.28), g), pre + tt, n)
    return room(y, rng, 0.35, 0.08, 4000.0, 0.15)


# ----------------------------------------------------------------------------- 10. il braccio a vuoto e il taglio

def braccio_a_vuoto(rng: np.random.Generator, tono: float) -> np.ndarray:
    """Il braccio morto prova a muoversi: il solenoide scatta, il servo gira due volte e si spegne, i
    contatti friggono. Niente luce: è un clic che non porta a niente."""
    n = n_of(0.32)
    y = sg.layer_transient(n, rng, 2500.0, 0.002, 0.6) + sg.modal(n, [2900.0 * tono, 4400.0 * tono], [0.02, 0.012], [0.4, 0.25], rng)
    y += sg.layer_body(n, 220.0 * tono, 150.0 * tono, 0.008, 0.015, 1.3, 0.4)
    m = n_of(0.2)
    srv = harm(sg.glide(m, 340.0 * tono, 105.0 * tono, 0.07), m, [1.0, 0.5, 0.35, 0.2]) * sg.env_bell(m, 0.012, 0.17) * 0.25
    y += at(srv * (1.0 + 0.4 * np.sin(2 * np.pi * 28.0 * tv(m))), 0.02, n)
    cr = sg.crackles(n_of(0.15), rng, 300.0, 0.05, 4000.0, (0.2, 0.8))
    y += at(cr / (np.max(np.abs(cr)) + 1e-9) * 0.15, 0.03, n)
    return y


def hack_cut(rng: np.random.Generator) -> np.ndarray:
    """L'hacking interrotto: il flusso di dati si inceppa (tre grani che si ripetono, sempre più sgranati),
    poi la linea cade con un tono che precipita e un clic di statica."""
    n = n_of(0.45)
    g = n_of(0.028)
    grain = sg.osc_fm(1800.0, 3.0, 2.0, g) * np.hanning(g)
    y = np.zeros(n)
    for i, rate in enumerate([22050.0, 11025.0, 6000.0]):
        y += at(sg.pcm_crunch(grain, rate, 8 - 2 * i, 9000.0) * (0.8 - 0.15 * i), 0.03 * i, n)
    m = n_of(0.22)
    drop = harm(sg.glide(m, 900.0, 70.0, 0.06), m, [1.0, 0.4, 0.25, 0.15]) * sg.env_ar(m, 0.003, 0.08) * 0.6
    y += at(drop, 0.09, n)
    y += at(sg.hp(nz(n_of(0.05), rng), 2000.0, 2) * sg.env_exp(n_of(0.05), 0.012) * 0.4, 0.09, n)
    y += at(sg.layer_transient(n_of(0.02), rng, 3000.0, 0.0015, 0.3), 0.3, n)
    return y


# ----------------------------------------------------------------------------- il catalogo

# file: (evento del §6, funzione, seme, uscita nel gioco in loudness veloce proposta, punto del codice, segnaposto di oggi)
EVENTI = {
    "tuono_lontano_a": (1, lambda r: tuono(r, 0.0), 101, -20.0, "sceneggiatura «Il terzo tasto» §3 (dopo CANC) e la pioggia di B; nessun evento oggi", "—"),
    "tuono_lontano_b": (1, lambda r: tuono(r, 0.35), 102, -19.0, "come sopra, un po' più vicino", "—"),
    "porta_colpo_a": (2, lambda r: porta_colpo(r, 0.7), 201, -13.0, "prologue.gd:1478 door_bang (PROLOGUE_SFX :1702)", "body_thud -3"),
    "porta_colpo_b": (2, lambda r: porta_colpo(r, 0.9), 202, -12.0, "idem: a turno, o per door_t sempre più piccolo", "body_thud -3"),
    "porta_colpo_c": (2, lambda r: porta_colpo(r, 1.1), 203, -11.0, "idem: gli ultimi colpi", "body_thud -3"),
    "porta_sfondata": (2, porta_sfondata, 204, -10.0, "prologue.gd:1480 door_break", "bin_break 0"),
    "riavvio_ronzio": (3, riavvio_ronzio, 301, -15.0, "scena «Tere e l'occhio cyan» §1 (suono nel copione: scene_player.gd:375)", "—"),
    "riavvio_scarica": (3, riavvio_scarica, 302, -11.0, "prologue.gd:1531/1540 reboot (PROLOGUE_SFX)", "zap 0"),
    "registro_clic": (3, registro_clic, 303, -17.0, "registri.gd:155 → test_room.gd EVENT_SFX registro_clic", "grab -4"),
    "registro_ronzio": (3, registro_ronzio, 304, -18.0, "registri.gd:133 registro_ronzio", "hack -6"),
    "registro_lampo": (3, registro_lampo, 305, -15.0, "registri.gd:135 registro_lampo", "zap -4"),
    "tasto_ctrl": (4, lambda r: tasto(r, 1.0), 401, -16.0, "prologue.gd:1436 reboot_key, reboot_step 2 (CTRL)", "ui_move 0"),
    "tasto_alt": (4, lambda r: tasto(r, 0.93), 402, -16.0, "prologue.gd:1436 reboot_key, reboot_step 3 (ALT)", "ui_move 0"),
    "tasto_canc": (4, lambda r: tasto(r, 1.06, naso=True), 403, -15.0, "prologue.gd:1436 reboot_key, reboot_step 4 (CANC col naso)", "ui_move 0"),
    "spinotto": (4, spinotto, 404, -17.0, "prologue.gd:1431 keyboard", "ui_confirm -2"),
    "vedetta_faro": (5, vedetta_faro, 502, -17.0, "test_room.gd:851 DRONE_SFX faro_rosso", "ui_move -6"),
    "rider_passo_a": (6, lambda r: rider_passo(r, 128.0), 601, -24.0, "rider.gd (i passi dei rider in campo, se servono)", "—"),
    "rider_passo_b": (6, lambda r: rider_passo(r, 120.0), 602, -24.0, "idem", "—"),
    "rider_passo_c": (6, lambda r: rider_passo(r, 135.0, 0.85), 603, -24.5, "idem", "—"),
    "laser_mira": (7, laser_mira, 701, -17.0, "messo.gd:180 (oggi glint -6)", "glint -6"),
    "laser_segno": (7, laser_segno, 702, -13.0, "messo.gd:210 (oggi zap -4)", "zap -4"),
    "sigillo_a": (7, lambda r: sigillo(r, 1.0), 703, -13.0, "platform_player.gd:1149 sigillo → EVENT_SFX", "block 0"),
    "sigillo_b": (7, lambda r: sigillo(r, 0.94), 704, -13.0, "idem, a turno", "block 0"),
    "serranda": (8, serranda, 801, -14.0, "la serranda della cantina (B2): nessun evento oggi", "—"),
    "cancello_a": (8, lambda r: cancello(r, 1.0), 802, -14.0, "test_room.gd:1904 gate_close", "bin_hit -8"),
    "cancello_b": (8, lambda r: cancello(r, 0.9), 803, -14.0, "idem, a turno", "bin_hit -8"),
    "tosse_a": (9, lambda r: tosse(r, [(0.0, 1.0), (0.3, 0.8)]), 901, -17.0, "hazards.gd:225 tosse → EVENT_SFX", "body_thud -12"),
    "tosse_b": (9, lambda r: tosse(r, [(0.0, 1.0), (0.24, 0.75), (0.45, 0.55)]), 902, -17.0, "idem", "body_thud -12"),
    "tosse_c": (9, lambda r: tosse(r, [(0.0, 0.9)]), 903, -17.5, "idem", "body_thud -12"),
    "braccio_a_vuoto_a": (10, lambda r: braccio_a_vuoto(r, 1.0), 1001, -19.0, "platform_player.gd:500 → EVENT_SFX braccio_a_vuoto", "ui_move -6"),
    "braccio_a_vuoto_b": (10, lambda r: braccio_a_vuoto(r, 0.9), 1002, -19.0, "idem, a turno", "ui_move -6"),
    "hack_cut": (10, hack_cut, 1003, -17.0, "test_room.gd:1917 hack_cut", "ui_move -4"),
}

# loop: (evento, funzione, seme, LUFS integrati del file, perché, punto del codice)
LOOP = {
    "vedetta_loop": (5, vedetta_loop, 501, -22.0, "sorgente posizionale: il gioco la attenua con la distanza; da vicino sta sotto i colpi e sopra la pioggia (-28)", "drones.gd, un AudioStreamPlayer2D per Vedetta (nuovo)"),
    "rider_passi_loop": (6, rider_passi_loop, 600, -32.0, "strato d'ambiente della fuga: 4 dB sotto la pioggia piena (-28), si sente nei vuoti", "Ambience, strato in A6-B3 (nuovo)"),
}

NOMI_EVENTO = {1: "Il tuono lontano", 2: "I colpi alla porta", 3: "Il riavvio e i registri", 4: "I tre tasti (CTRL, ALT, CANC)",
               5: "La Vedetta", 6: "I passi dei rider sotto la pioggia", 7: "Il laser e il sigillo del messo",
               8: "La serranda e il cancello", 9: "La tosse", 10: "Il braccio a vuoto e il taglio dell'hacking"}


# ----------------------------------------------------------------------------- finitura, misure, tavole

def finish_event(name: str, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Finitura di sfx_gen (passa-alto a 30 Hz, code, dissolvenze), poi alla loudness comune REF_FAST,
    abbassata se il picco vero supera TP_MAX. Restituisce il file e quanto è stato abbassato."""
    y = sg.finish(name, x, fade_in_ms=1.0, fade_out_ms=15.0)
    y *= 10 ** ((REF_FAST - sg.fast_loudness(y)) / 20)
    tp = al.true_peak_db(y)
    cut = 0.0
    if tp > TP_MAX - 0.05:
        cut = TP_MAX - 0.1 - tp
        y *= 10 ** (cut / 20)
    return y, cut


def finish_loop(x: np.ndarray, target: float) -> np.ndarray:
    y = x - x.mean(axis=0)
    return y * 10 ** ((target - al.integrated_loudness(y, SR)) / 20)


def problems_of(name: str, x: np.ndarray, loop: bool) -> list[str]:
    errs = []
    m = x.mean(axis=1) if x.ndim == 2 else x
    if not np.all(np.isfinite(x)):
        errs.append("valori non finiti")
    tp = al.true_peak_db(x)
    if tp > TP_MAX:
        errs.append(f"picco vero {tp:.2f} dBTP")
    if abs(m.mean()) > 1e-4:
        errs.append(f"componente continua {m.mean():.1e}")
    if not loop and (abs(m[0]) > 1e-3 or abs(m[-1]) > 1e-3):
        errs.append("estremi non nulli")
    return errs


def tavola(files: dict[str, np.ndarray], path: Path, cols: int = 4) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(files)
    rows = (len(names) + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(4.2 * cols, 2.3 * rows))
    for a, nm in zip(np.ravel(axs), names):
        x = files[nm]
        m = x.mean(axis=1) if x.ndim == 2 else x
        f, t, S = signal.spectrogram(m, SR, nperseg=1024, noverlap=896)
        Z = 10 * np.log10(S + 1e-14)
        a.pcolormesh(t, f, Z, vmin=Z.max() - 75, vmax=Z.max(), shading="auto")
        a.set_yscale("symlog", linthresh=300)
        a.set_ylim(30, 16000)
        a.set_title(nm, fontsize=8)
        a.tick_params(labelsize=6)
    for a in np.ravel(axs)[len(names):]:
        a.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=75)
    plt.close(fig)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--solo", nargs="*", default=None, help="genera solo questi file")
    ap.add_argument("--no-tavole", action="store_true")
    ap.add_argument("--install", action="store_true", help="dopo i controlli copia i file generati in game/assets/sfx")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rep_path = a.out / "report.json"
    rep = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.exists() and a.solo else {}
    problems, mix, done = [], {}, {}
    for name, (ev, fn, seed, out_fast, where, placeholder) in EVENTI.items():
        if a.solo is not None and name not in a.solo:
            continue
        x, cut = finish_event(name, fn(np.random.default_rng(seed)))
        problems += [f"{name}: {e}" for e in problems_of(name, x, False)]
        fl = sg.fast_loudness(x)
        tp = al.true_peak_db(x)
        # guadagno per arrivare al livello voluto, ma col picco vero nel gioco sotto TP_MAX
        mix[name] = MIX_FISSO.get(name, float(np.floor(min(out_fast - fl, TP_MAX - tp) * 2) / 2))
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(sg.IMPORT_TEMPLATE, encoding="utf-8", newline="\n")
        rep[name] = {"evento": ev, "dur_s": round(len(x) / SR, 3), "fast_lufs": round(fl, 2),
                     "lufs_integrati": round(al.integrated_loudness(x, SR), 2) if len(x) > 0.4 * SR else None,
                     "true_peak_dbtp": round(al.true_peak_db(x), 2), "abbassato_per_il_picco_db": round(cut, 2),
                     "altoparlante_piccolo_fast": round(sg.small_speaker_loudness(x), 2),
                     "centroide_hz": round(al.spectral_centroid(x, SR)), "mix_db": mix[name],
                     "nel_gioco_fast_lufs": round(fl + mix[name], 2), "nel_gioco_true_peak_dbtp": round(tp + mix[name], 2),
                     "livello_voluto_fast_lufs": out_fast, "codice": where, "segnaposto_oggi": placeholder}
        done[name] = x
        print(f"{name:20s} {len(x)/SR:5.2f}s  fast {fl:6.1f}  TP {rep[name]['true_peak_dbtp']:6.1f}  cut {cut:5.1f}  mix {mix[name]:5.1f}  piccolo {rep[name]['altoparlante_piccolo_fast']:6.1f}")
    for name, (ev, fn, seed, target, why, where) in LOOP.items():
        if a.solo is not None and name not in a.solo:
            continue
        x = finish_loop(fn(np.random.default_rng(seed)), target)
        problems += [f"{name}: {e}" for e in problems_of(name, x, True)]
        s = ag.seam_report(x)
        if s["click_vs_rms"] > 4.0 or abs(s["step_500ms_db"]) > max(1.5, 1.5 * s["salto_tipico_500ms_db"]):
            problems.append(f"{name}: giunto {s}")
        al.write_wav16(a.out / f"{name}.wav", x, SR)
        (a.out / f"{name}.wav.import").write_text(ag.LOOP_IMPORT, encoding="utf-8", newline="\n")
        m = x.mean(axis=1) if x.ndim == 2 else x
        rep[name] = {"evento": ev, "dur_s": round(len(x) / SR, 3), "lufs_integrati": round(al.integrated_loudness(x, SR), 2),
                     "fast_lufs": round(sg.fast_loudness(m), 2), "true_peak_dbtp": round(al.true_peak_db(x), 2),
                     "centroide_hz": round(al.spectral_centroid(m, SR)), "giunto": s, "perche_il_livello": why, "codice": where}
        done[name] = x
        print(f"{name:20s} {len(x)/SR:5.1f}s  {rep[name]['lufs_integrati']:6.1f} LUFS  TP {rep[name]['true_peak_dbtp']:6.1f}  giunto {s}")
    mp = a.out / "mix_prova.json"
    old = json.loads(mp.read_text(encoding="utf-8"))["gain_db"] if mp.exists() and a.solo else {}
    old.update(mix)
    mp.write_text(json.dumps({"format": 1, "comment": "Guadagni proposti degli eventi nuovi (file a fast %.0f LUFS)" % REF_FAST, "gain_db": old}, indent=1) + "\n", encoding="utf-8", newline="\n")
    rep_path.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if not a.no_tavole and done:
        names = list(done)
        for i in range(0, len(names), 12):
            tavola({k: done[k] for k in names[i:i + 12]}, a.out / f"tavola_{i // 12 + 1}.png")
    if problems:
        print("PROBLEMI:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("OK")
    if a.install:
        import sfx_pack  # i nomi dei suoni montati da sfx_pack
        clash = sorted(set(done) & set(sfx_pack.NAMES))
        if clash:
            print(f"PROBLEMI: nomi già usati dai suoni di sfx_pack: {clash}", file=sys.stderr)
            return 1
        pairs = [(a.out / f"{n}{ext}", ag.GAME_SFX / f"{n}{ext}") for n in done for ext in (".wav", ".wav.import")]
        ag.install_files(pairs)
        new = ag.merge_mix(mix)
        print(f"installati {len(pairs)} file in {ag.GAME_SFX}; righe nuove in mix.json: {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
