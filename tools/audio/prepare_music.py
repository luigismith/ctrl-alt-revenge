#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Prepara un brano per il gioco: punti di loop, volume, OGG e voce in music.json.

Pensato per i WAV scaricati da Suno (e i loro stem), funziona con qualsiasi WAV.
La musica non entra mai nel repo: tutto finisce nella cartella music/ del laboratorio
(%USERPROFILE%/ctrlaltrevenge-lab/music/), dove l'autoload Music la cerca.

Passi per un brano in loop:
  1. PyMusicLooper ("export-points --alt-export-top") propone i candidati (inizio, fine) del loop.
  2. La fine di ogni candidato si rifinisce per correlazione (+-1024 campioni): PyMusicLooper
     lavora su blocchi di 512 campioni e può sbagliare di qualche centinaio di campioni.
     Vince il candidato con il giunto più somigliante.
  3. BPM dalla lunghezza del loop: battiti = numero intero di battute più vicino al tempo
     indicato (--bpm-hint) o stimato; bpm = 60 * battiti / durata del loop.
  4. Via la componente continua e passa-alto a 20 Hz in modo "periodico": il pezzo che si
     ripete viene filtrato come se fosse già al secondo giro, così il giunto resta continuo.
  5. Loudness integrata (BS.1770-4) misurata sul loop, con tutti gli strati accesi: un solo
     guadagno lineare porta a -16 LUFS, abbassato se serve perché il true peak resti <= -1 dBTP.
     Niente compressione né loudnorm dinamico: cambierebbero il suono fra fine e inizio del loop.
  6. Taglio alla fine del loop (gli OGG di Godot hanno solo il punto di ripresa, loop_offset),
     codifica OGG Vorbis q6 con ffmpeg (mai l'export OGG di PyMusicLooper: su Windows si blocca),
     poi decodifica di controllo: lunghezza esatta, true peak, loudness, continuità del giunto.
  7. Aggiorna music.json (scrittura atomica). Gli strati (es. "arena") ricevono lo stesso
     taglio, lo stesso filtro e lo stesso guadagno della base, così restano in fase.

Per un jingle (--jingle INIZIO FINE, in secondi) niente loop: si taglia, si sfuma e si normalizza.

Esempi:
  python -I tools/audio/prepare_music.py stage1 --main suno/sotto_la_linea.wav --bpm-hint 124 \\
      --source "https://suno.com/song/..." --title "Sotto la Linea"
  python -I tools/audio/prepare_music.py stage1 --main suno/mix.wav --layer arena=suno/drums.wav \\
      --subtract-layers --bpm-hint 124          # base = mix - batteria, l'arena la rimette
  python -I tools/audio/prepare_music.py clear --main suno/sotto_la_linea.wav --jingle 151.2 154.6
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiolib as al  # noqa: E402

LAB = Path(os.environ.get("CAR_LAB", Path(os.environ.get("USERPROFILE", str(Path.home()))) / "ctrlaltrevenge-lab"))
FFMPEG = LAB / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
PML = LAB / "tools" / "pymusiclooper" / "bin" / "pymusiclooper.exe"
MUSIC_DIR = LAB / "music"
TOOL_VERSION = 1


# ----------------------------------------------------------------------------- utilità

def log(msg: str) -> None:
    print(msg, flush=True)


def write_f32(path: Path, x: np.ndarray, sr: int) -> None:
    wavfile.write(str(path), sr, np.asarray(x, dtype=np.float32))


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=env)


def mono(x: np.ndarray) -> np.ndarray:
    return al.as_2d(x).mean(axis=1)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp_prepare")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------- loop

def pymusiclooper_candidates(wav: Path, top: int, min_loop: float | None, max_loop: float | None,
                             approx: tuple[float, float] | None) -> list[tuple[int, int, float]]:
    cmd = [str(PML), "export-points", "--path", str(wav), "--alt-export-top", str(top)]
    if min_loop:
        cmd += ["--min-loop-duration", f"{min_loop:.3f}"]
    if max_loop:
        cmd += ["--max-loop-duration", f"{max_loop:.3f}"]
    if approx:
        cmd += ["--approx-loop-position", f"{approx[0]:.3f}", f"{approx[1]:.3f}"]
    log("PyMusicLooper: " + " ".join(cmd[1:]))
    r = run(cmd, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"PyMusicLooper ha fallito ({r.returncode}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    cands = []
    for line in r.stdout.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$", line)
        if m:
            cands.append((int(m.group(1)), int(m.group(2)), float(m.group(5))))
    if not cands:
        raise RuntimeError("PyMusicLooper non ha proposto punti di loop:\n" + r.stdout[-2000:])
    return cands


def _ncc_curve(ref: np.ndarray, seg: np.ndarray) -> np.ndarray:
    """Correlazione normalizzata di 'ref' con ogni finestra di 'seg' (stessa lunghezza)."""
    c = signal.correlate(seg, ref, mode="valid")
    csum = np.concatenate([[0.0], np.cumsum(seg * seg)])
    energy = csum[len(ref):] - csum[: len(csum) - len(ref)]
    return c / np.sqrt(np.maximum(energy * np.dot(ref, ref), 1e-30))


def ncc_sides(m: np.ndarray, s: int, e: int, w: int) -> tuple[float | None, float | None]:
    """Somiglianza del giunto e -> s vista dai due lati:
    - prima: m[s-w:s] contro m[e-w:e] (ciò che precede l'inizio somiglia alla fine del loop);
    - dopo:  m[s:s+w] contro m[e:e+w] (ciò che segue la fine nella sorgente è l'inizio del loop).
    Basta che uno dei due lati combaci: con un'introduzione diversa dalla fine del loop il lato
    "prima" non torna anche quando il giunto è perfetto. None se il lato non c'è nella sorgente."""
    out = []
    for a, b in (((s - w, s), (e - w, e)), ((s, s + w), (e, e + w))):
        if a[0] < 0 or b[0] < 0 or a[1] > len(m) or b[1] > len(m):
            out.append(None)
            continue
        x, y = m[a[0]:a[1]], m[b[0]:b[1]]
        den = np.sqrt(np.dot(x, x) * np.dot(y, y))
        out.append(float(np.dot(x, y) / den) if den > 0 else 0.0)
    return out[0], out[1]


def ncc_best(m: np.ndarray, s: int, e: int, w: int) -> float:
    vals = [v for v in ncc_sides(m, s, e, w) if v is not None]
    return max(vals) if vals else 0.0


def refine_end(m: np.ndarray, s: int, e: int, radius: int = 1024, w: int = 3308) -> tuple[int, float]:
    """Sposta la fine del loop di +-radius campioni dove il giunto somiglia di più alla sorgente,
    guardando separatamente il lato prima e il lato dopo (finestre di 75 ms a 44,1 kHz) e
    tenendo il migliore dei due."""
    best = np.full(2 * radius + 1, -np.inf)
    if s - w >= 0 and e - radius - w >= 0:  # lato prima
        best = np.maximum(best, _ncc_curve(m[s - w:s], m[e - radius - w:e + radius]))
    if s + w <= len(m) and e + radius + w <= len(m):  # lato dopo
        best = np.maximum(best, _ncc_curve(m[s:s + w], m[e - radius:e + radius + w]))
    if not np.isfinite(best).any():
        return e, ncc_best(m, s, e, w)
    k = int(np.argmax(best))
    return e - radius + k, float(best[k])


def seam_metrics(x: np.ndarray, s: int, e: int, sr: int, before: np.ndarray | None = None) -> dict:
    """Continuità del giunto e -> s, cioè del segnale che si sente al ritorno del loop:
    - jump_ratio: salto fra l'ultimo campione e il primo dopo la ripresa, diviso per il
      99,9° percentile dei salti fra campioni vicini (sotto 1,5: nessun gradino);
    - ncc_before / ncc_after: somiglianza del giunto dai due lati (vedi ncc_sides);
    - codec_db: se 'before' è il segnale prima della codifica, energia sopra 4 kHz della
      differenza (decodificato - originale) nei 3 ms del giunto, rispetto alla musica;
      codec_typ_db è la stessa misura in 40 punti a caso del loop (il rumore normale del codec)
      e codec_excess_db la differenza: un click aggiunto dalla codifica alla fine del file si
      vedrebbe come un eccesso netto. Non si guarda l'energia acuta assoluta, perché spesso sul
      giunto c'è un attacco musicale vero."""
    x2 = al.as_2d(x)
    n = int(0.05 * sr)
    v = np.concatenate([x2[e - n: e], x2[s: s + n]], axis=0)
    d = np.abs(np.diff(v, axis=0)).max(axis=1)
    jump = float(d[n - 1])
    ref = float(np.percentile(np.delete(d, n - 1), 99.9)) or 1e-9
    nb, na = ncc_sides(mono(x2), s, e, int(0.075 * sr))
    out = {"jump_ratio": round(jump / ref, 3),
           "ncc_before": None if nb is None else round(nb, 5),
           "ncc_after": None if na is None else round(na, 5)}
    if before is not None:
        b2 = al.as_2d(before)
        vb = np.concatenate([b2[e - n: e], b2[s: s + n]], axis=0)
        hp = signal.sosfilt(signal.butter(4, 4000, btype="highpass", fs=sr, output="sos"), v - vb, axis=0)
        win = int(0.003 * sr)
        at = float((hp[n - win // 2: n + win // 2] ** 2).sum())
        music = float((v ** 2).sum()) * win / len(v) or 1e-20
        level = float(10 * np.log10(max(at, 1e-30) / music))
        sos = signal.butter(4, 4000, btype="highpass", fs=sr, output="sos")
        typ = []
        for c in np.linspace(s + 2 * n, e - 2 * n, 40).astype(int):
            dx = x2[c - n: c + n] - b2[c - n: c + n]
            hx = signal.sosfilt(sos, dx, axis=0)
            mx = float((x2[c - n: c + n] ** 2).sum()) * win / (2 * n) or 1e-20
            typ.append(10 * np.log10(max(float((hx[n - win // 2: n + win // 2] ** 2).sum()), 1e-30) / mx))
        typ_db = float(np.median(typ))
        out.update({"codec_db": round(level, 1), "codec_typ_db": round(typ_db, 1),
                    "codec_excess_db": round(level - typ_db, 1)})
    return out


def estimate_bpm(x: np.ndarray, sr: int, lo: float = 70.0, hi: float = 190.0) -> float:
    """Stima grezza del tempo: autocorrelazione del flusso spettrale (onset)."""
    m = mono(x)[: sr * 60]
    f, t, s = signal.stft(m, fs=sr, nperseg=2048, noverlap=2048 - 512)
    mag = np.log1p(np.abs(s))
    flux = np.maximum(np.diff(mag, axis=1), 0).sum(axis=0)
    flux -= flux.mean()
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    fps = sr / 512.0
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo) + 1)
    k = lags[int(np.argmax(ac[lags]))]
    return 60.0 * fps / k


# ----------------------------------------------------------------------------- filtro e volume

def periodic_highpass(x: np.ndarray, sr: int, s: int, e: int, fc: float) -> np.ndarray:
    """Toglie la media del loop e filtra con un passa-alto causale. Il tratto [s, e) viene preso
    dal secondo giro (stato del filtro = fine del loop), quindi e -> s è continuo come nella
    sorgente. Dieci millisecondi prima di s si passa con una dissolvenza incrociata dal primo
    giro al secondo: succede una volta sola, all'ingresso nel loop."""
    x2 = al.as_2d(x).astype(np.float64)
    x2 = x2 - x2[s:e].mean(axis=0)
    if fc <= 0:
        return x2[:e]
    sos = signal.butter(2, fc, btype="highpass", fs=sr, output="sos")
    ext = np.concatenate([x2[:e], x2[s:e]], axis=0)
    y = signal.sosfilt(sos, ext, axis=0)
    L = e - s
    out = y[:e].copy()
    out[s:e] = y[e: e + L]
    n = min(int(0.010 * sr), s)
    if n > 0:
        w = (0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n))[:, None]
        out[s - n: s] = (1 - w) * y[s - n: s] + w * y[e - n: e]
    return out


def plain_highpass(x: np.ndarray, sr: int, fc: float) -> np.ndarray:
    x2 = al.as_2d(x).astype(np.float64)
    x2 = x2 - x2.mean(axis=0)
    if fc <= 0:
        return x2
    return signal.sosfilt(signal.butter(2, fc, btype="highpass", fs=sr, output="sos"), x2, axis=0)


def choose_gain(ref: np.ndarray, sr: int, target: float, max_tp: float, margin: float) -> tuple[float, float, float]:
    lufs = al.integrated_loudness(ref, sr)
    gain = target - lufs
    tp = al.true_peak_db(ref)
    if tp + gain > max_tp - margin:
        gain = max_tp - margin - tp
    return gain, lufs, tp


# ----------------------------------------------------------------------------- codifica

def encode_ogg(x: np.ndarray, sr: int, dst: Path, meta_src: Path | None, tags: dict, work: Path) -> None:
    tmp_wav = work / (dst.stem + "_enc.wav")
    write_f32(tmp_wav, x, sr)
    tmp_ogg = dst.with_name(dst.name + ".tmp_prepare")
    cmd = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp_wav)]
    if meta_src is not None:
        # conserva i metadati del file originale (provenienza Suno, se presenti)
        cmd += ["-i", str(meta_src), "-map", "0:a", "-map_metadata", "1"]
    for k, v in tags.items():
        cmd += ["-metadata", f"{k}={v}"]
    cmd += ["-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(tmp_ogg)]
    r = run(cmd, timeout=900)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg ha fallito:\n" + r.stderr[-2000:])
    os.replace(tmp_ogg, dst)
    tmp_wav.unlink(missing_ok=True)


def decode(path: Path, work: Path) -> tuple[np.ndarray, int]:
    out = work / (path.stem + "_dec.wav")
    r = run([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
             "-c:a", "pcm_f32le", str(out)], timeout=900)
    if r.returncode != 0:
        raise RuntimeError("decodifica fallita:\n" + r.stderr[-2000:])
    x, sr = al.read_wav(out)
    out.unlink(missing_ok=True)
    return x, sr


# ----------------------------------------------------------------------------- music.json

def load_manifest(path: Path) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("tracks"), list):
            return data
    return {"format": 1, "comment": "Brani per l'autoload Music (tools/audio/prepare_music.py). "
            "Tempi in secondi; i campioni sono esatti alla frequenza sample_rate.", "tracks": []}


def save_manifest(path: Path, data: dict) -> None:
    order = {"title": 0, "stage1": 1, "clear": 2}
    data["tracks"].sort(key=lambda t: (order.get(t.get("id"), 9), t.get("id", "")))
    atomic_write_bytes(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


# ----------------------------------------------------------------------------- principale

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", help="id del brano: title, stage1, clear, ...")
    ap.add_argument("--main", type=Path, required=True, help="WAV principale (il mix, o la base)")
    ap.add_argument("--layer", action="append", default=[], metavar="ID=WAV",
                    help="strato sincronizzato (ripetibile), es. arena=stem_batteria.wav")
    ap.add_argument("--subtract-layers", action="store_true",
                    help="gli strati sono stem del mix: la base diventa mix - strati")
    ap.add_argument("--loop-search", type=Path, help="WAV su cui cercare il loop (predefinito: base + strati)")
    ap.add_argument("--loop", nargs=2, type=float, metavar=("INIZIO", "FINE"), help="loop forzato, in secondi")
    ap.add_argument("--no-refine", action="store_true", help="con --loop: non rifinire la fine")
    ap.add_argument("--min-loop", type=float, help="durata minima del loop (s)")
    ap.add_argument("--max-loop", type=float, help="durata massima del loop (s)")
    ap.add_argument("--approx-loop", nargs=2, type=float, metavar=("INIZIO", "FINE"))
    ap.add_argument("--jingle", nargs=2, type=float, metavar=("INIZIO", "FINE"), help="taglio senza loop (s)")
    ap.add_argument("--fade-in", type=float, default=0.005, help="jingle: dissolvenza iniziale (s)")
    ap.add_argument("--fade-out", type=float, default=0.30, help="jingle: dissolvenza finale (s)")
    ap.add_argument("--bpm-hint", type=float, help="tempo approssimativo (altrimenti stimato)")
    ap.add_argument("--bar-beats", type=int, default=4)
    ap.add_argument("--target-lufs", type=float, default=-16.0)
    ap.add_argument("--max-tp", type=float, default=-1.0)
    ap.add_argument("--hp", type=float, default=20.0, help="passa-alto in Hz (0 = solo via la media)")
    ap.add_argument("--music-dir", type=Path, default=MUSIC_DIR)
    ap.add_argument("--file", help="nome del file OGG (predefinito: <id>.ogg)")
    ap.add_argument("--gain-db", type=float, default=0.0, help="guadagno extra da applicare nel gioco")
    ap.add_argument("--placeholder", action="store_true", help="brano segnaposto da sostituire")
    ap.add_argument("--source", default="", help="URL o nota di provenienza")
    ap.add_argument("--title", default="", help="nome leggibile del brano")
    ap.add_argument("--license", default="", help="licenza (es. CC0-1.0, Suno Pro)")
    ap.add_argument("--note", default="", help="nota libera in music.json")
    a = ap.parse_args()

    for tool in (FFMPEG,) + ((PML,) if not (a.loop or a.jingle) else ()):
        if not tool.exists():
            log(f"manca {tool}")
            return 2
    a.music_dir.mkdir(parents=True, exist_ok=True)
    work = a.music_dir / "_work" / a.id
    work.mkdir(parents=True, exist_ok=True)

    base, sr = al.read_wav(a.main)
    base = al.as_2d(base)
    layers: list[tuple[str, np.ndarray, Path]] = []
    for spec in a.layer:
        lid, _, p = spec.partition("=")
        y, sr2 = al.read_wav(Path(p))
        if sr2 != sr:
            raise SystemExit(f"lo strato {lid} è a {sr2} Hz, la base a {sr} Hz")
        y = al.as_2d(y)
        if y.shape[1] != base.shape[1]:
            y = np.repeat(y.mean(axis=1, keepdims=True), base.shape[1], axis=1)
        if len(y) < len(base):
            y = np.concatenate([y, np.zeros((len(base) - len(y), y.shape[1]))])
        layers.append((lid, y[: len(base)], Path(p)))
    if a.subtract_layers:
        for _, y, _ in layers:
            base = base - y
    ref = base + sum((y for _, y, _ in layers), np.zeros_like(base))
    log(f"{a.id}: {a.main.name}, {len(base) / sr:.3f} s a {sr} Hz, strati: {[l[0] for l in layers] or 'nessuno'}")

    entry: dict = {"id": a.id, "file": a.file or f"{a.id}.ogg", "title": a.title, "placeholder": bool(a.placeholder),
                   "source": a.source, "license": a.license, "gain_db": a.gain_db, "sample_rate": sr,
                   "prepared": dt.date.today().isoformat(), "prepared_by": f"tools/audio/prepare_music.py v{TOOL_VERSION}"}
    if a.note:
        entry["note"] = a.note

    if a.jingle:
        # ------------------------------------------------------------------ jingle
        i0, i1 = int(round(a.jingle[0] * sr)), int(round(a.jingle[1] * sr))
        streams = {"main": plain_highpass(base, sr, a.hp)[i0:i1]}
        for lid, y, _ in layers:
            streams[lid] = plain_highpass(y, sr, a.hp)[i0:i1]
        nfi, nfo = int(a.fade_in * sr), int(a.fade_out * sr)
        for k in streams:
            z = streams[k]
            z[:nfi] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(nfi) / nfi))[:, None]
            z[len(z) - nfo:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(1, nfo + 1) / nfo))[:, None]
        ref_seg = sum(streams.values())
        gain, lufs, tp = choose_gain(ref_seg, sr, a.target_lufs, a.max_tp, 0.3)
        S, E = 0, i1 - i0
        entry.update({"loop": False, "loop_start": 0.0, "loop_end": round(E / sr, 6),
                      "loop_start_sample": 0, "loop_end_sample": E, "bpm": 0.0, "bar_beats": a.bar_beats,
                      "beats": 0, "cut_from_s": [a.jingle[0], a.jingle[1]]})
        seam = None
    else:
        # ------------------------------------------------------------------ loop
        if a.loop:
            S, E = int(round(a.loop[0] * sr)), int(round(a.loop[1] * sr))
            ncc = ncc_best(mono(ref), S, E, int(0.075 * sr))
            if not a.no_refine:
                E, ncc = refine_end(mono(ref), S, E)
            cands = [(S, E, 1.0)]
            log(f"loop indicato: {S} -> {E} (ncc {ncc:.4f})")
        else:
            search = a.loop_search
            if search is None:
                search = work / "loop_search.wav"
                write_f32(search, ref, sr)
            cands = pymusiclooper_candidates(search, 10, a.min_loop, a.max_loop,
                                             tuple(a.approx_loop) if a.approx_loop else None)
            m = mono(ref)
            best = None
            for s0, e0, score in cands:
                e1, ncc = refine_end(m, s0, e0)
                log(f"  candidato {s0:>9d} -> {e0:>9d} (punteggio {score:.4f}) rifinito {e1:>9d} "
                    f"({e1 - e0:+d}) ncc {ncc:.5f}")
                if best is None or ncc > best[3]:
                    best = (s0, e1, score, ncc)
            S, E = best[0], best[1]
            log(f"scelto: {S} -> {E}, loop {(E - S) / sr:.4f} s, ncc {best[3]:.5f}")
        L = E - S
        hint = a.bpm_hint or estimate_bpm(ref, sr)
        bars = max(1, int(round(L / sr * hint / 60.0 / a.bar_beats)))
        beats = bars * a.bar_beats
        bpm = 60.0 * beats / (L / sr)
        log(f"tempo: indicazione {hint:.2f} -> {bars} battute da {a.bar_beats} = {beats} battiti, bpm {bpm:.4f}")
        streams = {"main": periodic_highpass(base, sr, S, E, a.hp)}
        for lid, y, _ in layers:
            streams[lid] = periodic_highpass(y, sr, S, E, a.hp)
        ref_loop = sum(streams.values())[S:E]
        gain, lufs, tp = choose_gain(ref_loop, sr, a.target_lufs, a.max_tp, 0.3)
        seam = seam_metrics(ref, S, E, sr)
        log(f"giunto nella sorgente: {seam}")
        entry.update({"loop": True, "loop_start": round(S / sr, 6), "loop_end": round(E / sr, 6),
                      "loop_start_sample": S, "loop_end_sample": E, "bpm": round(bpm, 4),
                      "bar_beats": a.bar_beats, "beats": beats})
    log(f"loudness misurata {lufs:.2f} LUFS, true peak {tp:.2f} dBTP -> guadagno {gain:+.2f} dB")

    # ---------------------------------------------------------------------- codifica e verifica
    files = {"main": entry["file"]}
    for lid, _, _ in layers:
        files[lid] = f"{Path(entry['file']).stem}_{lid}.ogg"
    sources = {"main": a.main, **{lid: p for lid, _, p in layers}}
    for attempt in range(3):
        g = al.from_db(gain)
        decoded = {}
        for k, z in streams.items():
            tags = {"CAR_ID": a.id, "CAR_STREAM": k}
            if entry["loop"]:
                tags.update({"LOOPSTART": str(S), "LOOPLENGTH": str(E - S)})
            encode_ogg(z * g, sr, a.music_dir / files[k], sources[k], tags, work)
            decoded[k], dsr = decode(a.music_dir / files[k], work)
            if dsr != sr or len(decoded[k]) != E:
                raise RuntimeError(f"{files[k]}: decodificati {len(decoded[k])} campioni a {dsr} Hz, attesi {E} a {sr}")
        total = sum(al.as_2d(v) for v in decoded.values())
        tp_out = al.true_peak_db(total)
        tp_streams = max(al.true_peak_db(v) for v in decoded.values())
        worst = max(tp_out, tp_streams)
        if worst <= a.max_tp:
            break
        log(f"true peak dopo la codifica {worst:.2f} dBTP > {a.max_tp}: abbasso di {worst - a.max_tp + 0.1:.2f} dB")
        gain -= worst - a.max_tp + 0.1
    else:
        raise RuntimeError("impossibile rispettare il true peak")
    lufs_out = al.integrated_loudness(total[S:E] if entry["loop"] else total, sr)
    entry.update({"applied_gain_db": round(gain, 2), "loudness_lufs": round(lufs_out, 2),
                  "true_peak_dbtp": round(worst, 2)})
    if entry["loop"]:
        pre = sum(al.as_2d(z) for z in streams.values()) * al.from_db(gain)
        seam_out = seam_metrics(total, S, E, sr, before=pre)
        entry["seam"] = {"source": seam, "decoded": seam_out}
        log(f"giunto nell'OGG decodificato: {seam_out}")
        src_ncc = max(v for v in (seam["ncc_before"], seam["ncc_after"], -1.0) if v is not None)
        codec_click = seam_out["codec_excess_db"] > 10.0 and seam_out["codec_db"] > -40.0
        if src_ncc < 0.9 or seam_out["jump_ratio"] > 1.5 or codec_click:
            log("ATTENZIONE: il giunto del loop non è pulito, controlla a orecchio o indica --loop")
    entry["layers"] = [{"id": lid, "file": files[lid], "gain_db": 0.0} for lid, _, _ in layers]
    log(f"OGG: {', '.join(files.values())}; loudness {lufs_out:.2f} LUFS, true peak {worst:.2f} dBTP, "
        f"{E / sr:.3f} s")

    manifest_path = a.music_dir / "music.json"
    data = load_manifest(manifest_path)
    data["tracks"] = [t for t in data["tracks"] if t.get("id") != a.id] + [entry]
    save_manifest(manifest_path, data)
    log(f"aggiornato {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
