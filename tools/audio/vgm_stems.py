#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Rende gli "stem" di un brano VGM (Mega Drive) tenendo solo le voci scelte.

Le voci sono: fm0..fm5 (canali FM dell'YM2612), dac (campioni PCM sul canale 6),
psg0..psg2 (onde quadre del PSG) e noise (rumore del PSG).
Il file VGM viene copiato e modificato byte per byte senza cambiare la lunghezza dei comandi:
- voce FM spenta: ogni key-on di quel canale (registro 0x28) diventa un key-off;
- DAC spento: ogni scrittura del registro 0x2B (abilitazione del DAC) diventa 0x00;
- voce PSG spenta: ogni scrittura di volume di quel canale diventa 15 (muto).
Poi ffmpeg (con libgme) rende il VGM in WAV. Tutti gli stem escono dallo stesso emulatore
con gli stessi tempi, quindi sono allineati al campione e la loro somma ridà il brano intero.

Per avere più giri del brano (e le code vere delle note al punto di ripresa) il VGM si
"srotola" (--unroll N): il flusso dei comandi viene ripetuto N volte in un VGM lineare, senza
punto di loop, così il render non dipende dalla gestione del loop di libgme.
Nota misurata: libgme suona i VGM circa lo 0,05% più lenti del nominale (a 150 BPM nominali il
render va a 149,93; il ritardo rispetto al WAV dell'autore cresce di 22 campioni al secondo).
Non è un difetto del loop: prepare_music.py cerca il loop sul render stesso e ricava il BPM
dalla sua lunghezza.

Attenzione: libgme chiude la traccia dopo circa 6 s di silenzio, quindi una voce sola che tace
a lungo uscirebbe troncata. Per questo lo strato si ricava per sottrazione: si rendono il brano
intero e la "base" (tutte le voci tranne quelle dello strato), e strato = intero - base.
Il missaggio dell'emulatore è lineare, quindi base + strato = intero a meno di 1 LSB.

  python -I tools/audio/vgm_stems.py brano.vgm --split dac,noise --unroll 2 -o cartella/ --seconds 212
  python -I tools/audio/vgm_stems.py brano.vgm --report --seconds 120 -o cartella/   # peso di ogni voce
  python -I tools/audio/vgm_stems.py brano.vgm --keep fm0,fm1,dac -o basso_batteria.wav --seconds 120
"""
from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

VOICES = ["fm0", "fm1", "fm2", "fm3", "fm4", "fm5", "dac", "psg0", "psg1", "psg2", "noise"]
LAB = Path(os.environ.get("CAR_LAB", Path(os.environ.get("USERPROFILE", str(Path.home()))) / "ctrlaltrevenge-lab"))
EXE = ".exe" if os.name == "nt" else ""  # sul Mac gli eseguibili non hanno estensione
FFMPEG = LAB / "tools" / "ffmpeg" / "bin" / ("ffmpeg" + EXE)

_LEN = {0x4F: 2, 0x50: 2, 0x61: 3, 0x62: 1, 0x63: 1, 0x66: 1, 0x68: 12,
        0x90: 5, 0x91: 5, 0x92: 6, 0x93: 11, 0x94: 2, 0x95: 5, 0xE0: 5}


def _cmd_len(b: bytes, i: int) -> int:
    c = b[i]
    if c in _LEN:
        return _LEN[c]
    if c == 0x67:
        return 7 + (struct.unpack_from("<I", b, i + 3)[0] & 0x7FFFFFFF)
    if 0x30 <= c <= 0x3F:
        return 2
    if 0x40 <= c <= 0x4E or 0x51 <= c <= 0x5F or 0xA0 <= c <= 0xBF:
        return 3
    if 0x70 <= c <= 0x8F:
        return 1
    if 0xC0 <= c <= 0xDF:
        return 4
    if 0xE1 <= c <= 0xFF:
        return 5
    return 1


_SETUP_ONLY = {0x67, 0x90, 0x91, 0x92}  # blocchi PCM e impostazione degli stream: una volta sola


def unroll(vgm: bytes, times: int) -> bytes:
    """VGM lineare con il brano (o la sua parte in loop) ripetuto 'times' volte, senza loop."""
    b = bytes(vgm)
    ver = struct.unpack_from("<I", b, 0x08)[0]
    rel = struct.unpack_from("<I", b, 0x34)[0] if ver >= 0x150 else 0
    start = 0x34 + rel if rel else 0x40
    total = struct.unpack_from("<I", b, 0x18)[0]
    loop_samples = struct.unpack_from("<I", b, 0x20)[0]
    loop_pos = 0x1C + struct.unpack_from("<I", b, 0x1C)[0] if loop_samples else start
    period = loop_samples or total
    first = bytearray()
    again = bytearray()
    i = start
    while i < len(b):
        c = b[i]
        if c == 0x66:
            break
        n = _cmd_len(b, i)
        first += b[i:i + n]
        if i >= loop_pos and c not in _SETUP_ONLY:
            again += b[i:i + n]
        i += n
    data = first + again * (times - 1) + bytes([0x66])
    head = bytearray(b[:start])
    struct.pack_into("<I", head, 0x04, len(head) + len(data) - 4)  # fine del file
    struct.pack_into("<I", head, 0x14, 0)                          # niente tag GD3
    struct.pack_into("<I", head, 0x18, total + period * (times - 1))
    struct.pack_into("<I", head, 0x1C, 0)                          # niente loop
    struct.pack_into("<I", head, 0x20, 0)
    return bytes(head + data)


def patch(vgm: bytes, keep: set[str], unroll_times: int = 1) -> bytes:
    """Copia del VGM in cui suonano solo le voci in 'keep', eventualmente srotolata."""
    if vgm[:4] != b"Vgm ":
        raise ValueError("non è un file VGM")
    if unroll_times > 1:
        vgm = unroll(vgm, unroll_times)
    b = bytearray(vgm)
    ver = struct.unpack_from("<I", b, 0x08)[0]
    rel = struct.unpack_from("<I", b, 0x34)[0] if ver >= 0x150 else 0
    i = 0x34 + rel if rel else 0x40
    latch = 0
    while i < len(b):
        c = b[i]
        if c == 0x66:
            break
        if c == 0x52 and b[i + 1] == 0x28:
            ch = b[i + 2] & 0x07
            idx = ch if ch < 3 else ch - 1
            if 0 <= idx <= 5 and f"fm{idx}" not in keep:
                b[i + 2] &= 0x0F
        elif c == 0x52 and b[i + 1] == 0x2B and "dac" not in keep:
            b[i + 2] = 0x00
        elif c == 0x50:
            v = b[i + 1]
            if v & 0x80:
                latch = (v >> 5) & 0x03
                if v & 0x10:
                    name = "noise" if latch == 3 else f"psg{latch}"
                    if name not in keep:
                        b[i + 1] = v | 0x0F
        i += _cmd_len(b, i)
    return bytes(b)


def render(vgm_path: Path, keep: set[str], out_wav: Path, seconds: float, sr: int = 44100,
           unroll_times: int = 1) -> None:
    data = patch(vgm_path.read_bytes(), keep, unroll_times)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "stem.vgm"
        tmp.write_bytes(data)
        cmd = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-f", "libgme",
               "-sample_rate", str(sr), "-i", str(tmp), "-t", f"{seconds:.6f}",
               "-c:a", "pcm_s16le", str(out_wav)]
        subprocess.run(cmd, check=True, timeout=600)


def _read16(path: Path):
    import numpy as np
    from scipy.io import wavfile
    sr, x = wavfile.read(str(path))
    return sr, x.astype(np.int32)


def _render_checked(vgm: Path, keep: set[str], out: Path, seconds: float,
                    unroll_times: int = 1) -> "np.ndarray":
    render(vgm, keep, out, seconds, unroll_times=unroll_times)
    sr, x = _read16(out)
    want = int(round(seconds * sr))
    if len(x) < want:
        raise RuntimeError(f"{out.name}: {len(x) / sr:.2f} s invece di {seconds:.2f} s "
                           "(libgme ha chiuso la traccia per silenzio: scegli altre voci)")
    return x[:want]


def split(vgm: Path, layer: set[str], outdir: Path, seconds: float, unroll_times: int = 1) -> dict:
    """Scrive <nome>__full.wav, __base.wav (senza lo strato) e __layer.wav (= full - base)."""
    import numpy as np
    from scipy.io import wavfile
    outdir.mkdir(parents=True, exist_ok=True)
    full = _render_checked(vgm, set(VOICES), outdir / f"{vgm.stem}__full.wav", seconds, unroll_times)
    base = _render_checked(vgm, set(VOICES) - layer, outdir / f"{vgm.stem}__base.wav", seconds, unroll_times)
    lay = full - base
    clip = int(np.sum(np.abs(lay) > 32767))
    wavfile.write(str(outdir / f"{vgm.stem}__layer.wav"), 44100, np.clip(lay, -32768, 32767).astype(np.int16))
    wavfile.write(str(outdir / f"{vgm.stem}__full.wav"), 44100, full.astype(np.int16))
    wavfile.write(str(outdir / f"{vgm.stem}__base.wav"), 44100, base.astype(np.int16))
    return {"samples": len(full), "layer_clipped_samples": clip,
            "layer_peak": int(np.abs(lay).max()), "base_peak": int(np.abs(base).max())}


def report(vgm: Path, outdir: Path, seconds: float) -> None:
    """Peso di ogni voce: differenza fra il brano intero e il brano senza quella voce."""
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import audiolib as al
    outdir.mkdir(parents=True, exist_ok=True)
    full = _render_checked(vgm, set(VOICES), outdir / "_full.wav", seconds) / 32768.0
    print(f"brano intero: {al.integrated_loudness(full, 44100):.2f} LUFS")
    for v in VOICES:
        try:
            rest = _render_checked(vgm, set(VOICES) - {v}, outdir / "_rest.wav", seconds) / 32768.0
        except RuntimeError as e:
            print(f"{v:6s} {e}")
            continue
        part = full - rest
        loud = al.integrated_loudness(part, 44100)
        rms = float(np.sqrt(np.mean(part ** 2)))
        cen = al.spectral_centroid(part[: 44100 * 30], 44100) if rms > 0 else 0.0
        print(f"{v:6s} {loud:7.2f} LUFS  rms {al.db(rms):6.1f} dB  baricentro {cen:6.0f} Hz")
    for p in ("_full.wav", "_rest.wav"):
        (outdir / p).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vgm", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True, help="WAV di uscita, o cartella con --split/--report")
    ap.add_argument("--keep", default=",".join(VOICES), help="voci da tenere, separate da virgole")
    ap.add_argument("--split", help="voci dello strato: scrive full, base e layer in --out")
    ap.add_argument("--report", action="store_true", help="misura il peso di ogni voce")
    ap.add_argument("--seconds", type=float, required=True, help="durata da rendere")
    ap.add_argument("--unroll", type=int, default=1, help="ripete il brano (o la sua parte in loop) N volte")
    a = ap.parse_args()
    if not FFMPEG.exists():
        print(f"ffmpeg non trovato: {FFMPEG}", file=sys.stderr)
        return 2
    if a.report:
        report(a.vgm, a.out, a.seconds)
        return 0
    if a.split:
        layer = {v.strip() for v in a.split.split(",") if v.strip()}
        if layer - set(VOICES):
            print(f"voci sconosciute: {sorted(layer - set(VOICES))}", file=sys.stderr)
            return 2
        print(split(a.vgm, layer, a.out, a.seconds, a.unroll))
        return 0
    keep = {v.strip() for v in a.keep.split(",") if v.strip()}
    bad = keep - set(VOICES)
    if bad:
        print(f"voci sconosciute: {sorted(bad)}", file=sys.stderr)
        return 2
    render(a.vgm, keep, a.out, a.seconds, unroll_times=a.unroll)
    return 0


if __name__ == "__main__":
    sys.exit(main())
