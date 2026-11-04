#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Legge file VGM (musica Mega Drive) senza emularli: intestazione, tag GD3, punti di loop
esatti ed eventi del chip (key-on dell'YM2612, campioni PCM del DAC, note del PSG).

Serve a scegliere e a preparare i brani segnaposto CC0 (Safety Stoat Studios, "Free VGMs"):
dai key-on si stimano tempo (BPM) e densità di note, dal DAC l'uso della batteria campionata.
Il punto di loop scritto nell'intestazione è esatto al campione (44,1 kHz) e si può confrontare
con quello trovato da PyMusicLooper sul WAV renderizzato.

  python -I tools/audio/vgm_info.py file.vgm [altri.vgm ...] [--json uscita.json]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

VGM_RATE = 44100


def _u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0] if off + 4 <= len(b) else 0


def _gd3(b: bytes, off: int) -> dict:
    """Tag GD3: stringhe UTF-16 terminate da zero (titolo, gioco, sistema, autore, ...)."""
    if off <= 0 or b[off:off + 4] != b"Gd3 ":
        return {}
    size = _u32(b, off + 8)
    raw = b[off + 12: off + 12 + size].decode("utf-16-le", errors="replace")
    parts = raw.split("\x00")
    keys = ["title_en", "title_jp", "game_en", "game_jp", "system_en", "system_jp",
            "author_en", "author_jp", "date", "ripper", "notes"]
    return {k: v for k, v in zip(keys, parts) if v}


def parse(path: Path) -> dict:
    b = path.read_bytes()
    if b[:4] != b"Vgm ":
        raise ValueError(f"{path}: non è un file VGM")
    version = _u32(b, 0x08)
    total = _u32(b, 0x18)
    loop_off = _u32(b, 0x1C)
    loop_samples = _u32(b, 0x20)
    data_off = 0x40
    if version >= 0x150 and _u32(b, 0x34):
        data_off = 0x34 + _u32(b, 0x34)
    gd3_rel = _u32(b, 0x14)
    info = {
        "file": path.name,
        "version": f"{version >> 8:x}.{version & 0xFF:02x}",
        "total_samples": total,
        "total_s": total / VGM_RATE,
        "loop_samples": loop_samples,
        "loop_s": loop_samples / VGM_RATE,
        "loop_start_sample": total - loop_samples if loop_samples else None,
        "sn76489_clock": _u32(b, 0x0C),
        "ym2612_clock": _u32(b, 0x2C) if version >= 0x110 else 0,
        "gd3": _gd3(b, 0x14 + gd3_rel) if gd3_rel else {},
    }
    # Scansione dei comandi: teniamo il tempo in campioni e annotiamo gli eventi.
    t = 0
    i = data_off
    fm_on: list[tuple[int, int]] = []      # (campione, canale 0-5) per ogni key-on
    dac_seeks: list[int] = []              # 0xE0: inizio di un campione PCM (batteria)
    psg_notes: list[tuple[int, int]] = []  # (campione, canale) quando il volume passa da muto a udibile
    psg_vol = [15, 15, 15, 15]
    psg_latch = 0
    dac_bytes = 0
    n = len(b)
    while i < n:
        c = b[i]
        if c == 0x66:
            break
        if c in (0x52, 0x53):
            reg, val = b[i + 1], b[i + 2]
            if c == 0x52 and reg == 0x28 and (val & 0xF0):
                ch = val & 0x07
                ch = ch if ch < 3 else ch - 1
                fm_on.append((t, ch))
            i += 3
        elif c == 0x50:
            v = b[i + 1]
            if v & 0x80:
                psg_latch = (v >> 5) & 0x03
                if v & 0x10:
                    vol = v & 0x0F
                    if psg_vol[psg_latch] >= 14 and vol < 12:
                        psg_notes.append((t, psg_latch))
                    psg_vol[psg_latch] = vol
            i += 2
        elif c == 0x61:
            t += struct.unpack_from("<H", b, i + 1)[0]
            i += 3
        elif c == 0x62:
            t += 735
            i += 1
        elif c == 0x63:
            t += 882
            i += 1
        elif 0x70 <= c <= 0x7F:
            t += (c & 0x0F) + 1
            i += 1
        elif 0x80 <= c <= 0x8F:
            t += c & 0x0F
            dac_bytes += 1
            i += 1
        elif c == 0x67:
            size = _u32(b, i + 3) & 0x7FFFFFFF
            i += 7 + size
        elif c == 0xE0:
            dac_seeks.append(t)
            i += 5
        elif c == 0x4F:
            i += 2
        elif 0x51 <= c <= 0x5F:
            i += 3
        elif 0x30 <= c <= 0x3F:
            i += 2
        elif 0x40 <= c <= 0x4E:
            i += 3
        elif 0xA0 <= c <= 0xBF:
            i += 3
        elif 0xC0 <= c <= 0xDF:
            i += 4
        elif 0xE1 <= c <= 0xFF:
            i += 5
        elif c == 0x68:
            i += 12
        elif 0x90 <= c <= 0x95:
            i += {0x90: 5, 0x91: 5, 0x92: 6, 0x93: 11, 0x94: 2, 0x95: 5}[c]
        else:
            i += 1
    info["scan_end_sample"] = t
    info["fm_keyons"] = len(fm_on)
    info["dac_hits"] = len(dac_seeks)
    info["dac_bytes"] = dac_bytes
    info["psg_notes"] = len(psg_notes)
    info["fm_channels_used"] = sorted({ch for _, ch in fm_on})
    # Densità di eventi nella parte che si ripete (o in tutto il brano se non c'è loop).
    s0 = info["loop_start_sample"] or 0
    span = max(1, total - s0)
    onsets = [tt for tt, _ in fm_on] + dac_seeks + [tt for tt, _ in psg_notes]
    loop_onsets = [tt for tt in onsets if tt >= s0]
    info["events_per_s_loop"] = len(loop_onsets) * VGM_RATE / span
    info["dac_hits_per_s_loop"] = sum(1 for tt in dac_seeks if tt >= s0) * VGM_RATE / span
    info["bpm_est"], info["bpm_strength"] = estimate_bpm(loop_onsets, s0, total)
    return info


def estimate_bpm(onsets: list[int], s0: int, s1: int) -> tuple[float | None, float]:
    """Stima del tempo dall'autocorrelazione del treno di attacchi (griglia di 5 ms)."""
    if len(onsets) < 16 or s1 <= s0:
        return None, 0.0
    hop = VGM_RATE // 200
    nbin = (s1 - s0) // hop + 1
    x = np.zeros(nbin)
    for tt in onsets:
        x[(tt - s0) // hop] += 1.0
    x -= x.mean()
    ac = np.correlate(x, x, mode="full")[nbin - 1:]
    ac /= ac[0] if ac[0] else 1.0
    # periodi del battito fra 60 e 200 BPM: 0,3-1,0 s
    lo, hi = int(0.3 * 200), int(1.0 * 200)
    lags = np.arange(lo, hi + 1)
    # rinforza il battito sommando anche i multipli (2 e 4 battiti)
    score = np.array([ac[l] + 0.5 * ac[min(2 * l, len(ac) - 1)] + 0.25 * ac[min(4 * l, len(ac) - 1)] for l in lags])
    k = int(np.argmax(score))
    lag = lags[k]
    # interpolazione parabolica per un BPM più fine
    if 0 < k < len(score) - 1:
        a, bb, c = score[k - 1], score[k], score[k + 1]
        den = a - 2 * bb + c
        if den != 0:
            lag = lag + 0.5 * (a - c) / den
    bpm = 60.0 * 200 / lag
    return round(float(bpm), 2), round(float(score[k]), 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", type=Path, help="salva i risultati in un file JSON")
    a = ap.parse_args()
    rows = []
    for f in a.files:
        try:
            rows.append(parse(f))
        except Exception as e:  # un file rotto non deve fermare gli altri
            print(f"{f}: {e}", file=sys.stderr)
    hdr = f"{'file':42s} {'tot s':>7s} {'loop s':>7s} {'start':>7s} {'ev/s':>6s} {'dac/s':>6s} {'bpm?':>7s} {'forza':>6s}  titolo / autore"
    print(hdr)
    for r in rows:
        g = r["gd3"]
        ls = r["loop_start_sample"]
        print(f"{r['file']:42s} {r['total_s']:7.2f} {r['loop_s']:7.2f} "
              f"{(ls / VGM_RATE if ls is not None else float('nan')):7.2f} {r['events_per_s_loop']:6.1f} "
              f"{r['dac_hits_per_s_loop']:6.2f} {str(r['bpm_est']):>7s} {r['bpm_strength']:6.3f}  "
              f"{g.get('title_en', '')} / {g.get('game_en', '')} / {g.get('author_en', '')}")
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
