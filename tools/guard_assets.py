#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Tiene fuori dal repository PUBBLICO i media che non si possono ridistribuire.

  python -I tools/guard_assets.py --staged   # hook pre-commit (contenuto dell'indice)
  python -I tools/guard_assets.py --all      # controllo completo: file tracciati e file nuovi
                                             # non ignorati (quelli che un "git add" prenderebbe)

Blocca:
  * tutto ciò che sta in una cartella assets_private/ (quella vera è game/assets_private/: musica,
    voci e manifest con le battute)
  * la storia privata: docs/lore/ (repo privato) e le battute delle scene (game/data/battute/, che
    tools/site/export_web.sh copia solo nella build web), anche in altre cartelle "battute/"
  * la cache di importazione di Godot (.godot/), che contiene copie convertite dell'audio
  * l'audio riconosciuto dall'estensione (.wav .ogg .oga .opus .mp3 .flac .aif .aiff .aifc
    .m4a .wma) e l'audio importato da Godot (.oggvorbisstr .mp3str .sample)
  * l'audio riconosciuto dal contenuto (RIFF/WAVE, OggS, fLaC, FORM/AIFF, ID3, MPEG),
    qualunque sia il nome del file
  * i video con una traccia audio (MP4, MOV, WebM, MKV): la musica non si ridistribuisce nemmeno lì dentro
  * qualsiasi file oltre 20 MB
Eccezione: i percorsi che corrispondono ai pattern di tools/public_audio_allowlist.txt
(per esempio gli effetti sonori nostri o CC0; ognuno serve anche in REUSE.toml).
"""
from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "tools" / "public_audio_allowlist.txt"
AUDIO_EXT = {".wav", ".ogg", ".oga", ".opus", ".mp3", ".flac", ".aif", ".aiff", ".aifc",
             ".m4a", ".wma", ".oggvorbisstr", ".mp3str", ".sample"}
## I video si leggono per intero: la traccia audio sta in un contenitore, non nei primi byte.
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}
VIDEO_AUDIO = (b"soun", b"mp4a", b"A_OPUS", b"A_VORBIS", b"A_AAC")
MAX_BYTES = 20 * 1024 * 1024
## La storia privata: sta nel repo privato e, per le battute, solo nella build web (decisione 68).
PRIVATE_STORY = ("docs/lore/", "game/data/battute/")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


## Windows non accetta più di ~32 000 caratteri nella riga di comando: i nomi dei file in stage vanno a blocchi.
ARGS_MAX_CHARS = 12000


def chunks(names: list[str], limit: int = ARGS_MAX_CHARS) -> list[list[str]]:
    """I nomi divisi in blocchi la cui lunghezza totale (con gli spazi) resta sotto `limit`."""
    out: list[list[str]] = []
    cur: list[str] = []
    size = 0
    for n in names:
        if cur and size + len(n) + 1 > limit:
            out.append(cur)
            cur, size = [], 0
        cur.append(n)
        size += len(n) + 1
    if cur:
        out.append(cur)
    return out


def ls_files_staged(names: list[str]) -> bytes:
    """`git ls-files -s -z` dei nomi dati, un blocco alla volta."""
    return b"".join(git("--literal-pathspecs", "ls-files", "-s", "-z", "--", *blk) for blk in chunks(names))


def sniff(head: bytes) -> str | None:
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "WAV"
    if head[:4] == b"OggS":
        return "Ogg"
    if head[:4] == b"fLaC":
        return "FLAC"
    if head[:4] == b"FORM" and head[8:12] in (b"AIFF", b"AIFC"):
        return "AIFF"
    if head[:3] == b"ID3":
        return "MP3/ID3"
    if len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "MPEG audio"
    return None


def entries(staged: bool) -> list[tuple[str, str | None]]:
    """Coppie (percorso, id del blob) prese dall'indice; con --all anche i file non ancora
    tracciati e non ignorati, con id None (si leggono dal disco)."""
    if staged:
        names = git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR").split(b"\0")
        names = [n for n in names if n]
        if not names:
            return []
        raw = ls_files_staged([n.decode("utf-8", "surrogateescape") for n in names])
    else:
        raw = git("ls-files", "-s", "-z")
    out: list[tuple[str, str | None]] = []
    for rec in raw.split(b"\0"):
        if rec:
            meta, path = rec.split(b"\t", 1)
            out.append((path.decode("utf-8", "surrogateescape"), meta.split()[1].decode()))
    if not staged:
        for rec in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
            if rec:
                out.append((rec.decode("utf-8", "surrogateescape"), None))
    return out


def video_has_audio(blob: str | None, path: str) -> bool:
    """Un contenitore video (MP4, MOV, WebM, MKV) con una traccia audio."""
    if blob is None:
        data = (ROOT / path).read_bytes()
    else:
        data = git("cat-file", "blob", blob)
    return any(m in data for m in VIDEO_AUDIO)


def head_of(blob: str | None, path: str) -> tuple[int, bytes]:
    """Dimensione e primi 16 byte: dal blob dell'indice o, per i file nuovi, dal disco."""
    if blob is None:
        p = ROOT / path
        with open(p, "rb") as fh:
            return p.stat().st_size, fh.read(16)
    size = int(git("cat-file", "-s", blob))
    p = subprocess.Popen(["git", "cat-file", "blob", blob], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    head = p.stdout.read(16)
    p.stdout.close()
    p.kill()
    p.wait()
    return size, head


def main() -> int:
    staged = "--all" not in sys.argv
    allow = []
    if ALLOWLIST.exists():
        allow = [l.strip() for l in ALLOWLIST.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
    problems = []
    for path, blob in entries(staged):
        if any(fnmatch.fnmatchcase(path, pat) for pat in allow):
            continue
        reason = None
        if "/assets_private/" in "/" + path:
            reason = "asset privato (musica, voci e manifest con le battute: restano fuori dal repo)"
        elif path.startswith(PRIVATE_STORY) or (path.endswith(".json") and "/battute/" in "/" + path):
            reason = "storia privata (battute e lore stanno nel repo privato, non in quello pubblico)"
        elif path.startswith(".godot/") or "/.godot/" in path:
            reason = "cache di importazione di Godot"
        elif Path(path).suffix.lower() in AUDIO_EXT:
            reason = "estensione di file audio"
        elif Path(path).suffix.lower() in VIDEO_EXT and video_has_audio(blob, path):
            reason = "video con una traccia audio"
        else:
            size, head = head_of(blob, path)
            kind = sniff(head)
            if kind:
                reason = f"il contenuto sembra {kind}"
            elif size > MAX_BYTES:
                reason = f"file grande ({size // (1024 * 1024)} MB)"
        if reason:
            problems.append((path, reason))
    if problems:
        print("BLOCCATO: questi file non possono entrare nel repository pubblico:", file=sys.stderr)
        for path, reason in problems:
            print(f"  {path}: {reason}", file=sys.stderr)
        print("Rimedio: git restore --staged <file>; i media privati restano fuori dal repo "
              "(cartella ctrlaltrevenge-lab o archivio privato).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
