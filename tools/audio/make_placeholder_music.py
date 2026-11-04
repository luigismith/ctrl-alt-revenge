#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Ricrea la musica segnaposto (CC0) nella cartella music/ del laboratorio, finché non arrivano
i brani di Suno. Niente di tutto questo entra nel repo.

Fonte: Safety Stoat Studios, "Free VGMs" (musica vera per Mega Drive), licenza CC0 1.0:
  https://github.com/jerellsworth/free_vgms (commit 2e376d0), https://safetystoatstudios.itch.io/free-vgms
I file vanno scaricati in %USERPROFILE%/ctrlaltrevenge-lab/downloads/free_vgms/ (con --download
lo fa lo script, dal commit fissato); lo script controlla lo sha256 di ogni file prima di usarlo.

Brani:
  stage1  MD_tracks/i_wondered_what_i_could_do_with_it (Si minore, 150 BPM nominali, basso FM a
          ottavi, batteria PCM): reso con libgme dal VGM "srotolato" due volte, così il giunto ha le
          code vere delle note. Strato "arena" = canale FM 2 (percussioni FM, il charleston);
          la base è tutto il resto. Nell'arena lo strato si accende e il ritmo si infittisce.
  title   sharp_in_head/title (Sol minore, rado e più lento): il WAV dell'autore.
  clear   la cadenza finale in Sol maggiore di MD_tracks/my_fathers_eyes (116,95-119,45 s),
          l'unico brano del pacchetto con un finale composto, sfumata negli ultimi 0,6 s.

  python -I tools/audio/make_placeholder_music.py [--download]
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vgm_stems  # noqa: E402

LAB = vgm_stems.LAB
SRC = LAB / "downloads" / "free_vgms"
MUSIC = LAB / "music"
COMMIT = "2e376d0abfa5709f6c0e648095672cd6c1654f93"
RAW = f"https://raw.githubusercontent.com/jerellsworth/free_vgms/{COMMIT}/"
FILES = {
    "LICENSE": "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499",
    "MD_tracks/i_wondered_what_i_could_do_with_it.vgm": "d87e80cb376ae55eea765dff8e45caf83221b33463b3797c203b34e02a90e0a3",
    "MD_tracks/my_fathers_eyes.wav": "b5d96aa372a67a5eaf2dac74a77dc5406f01116131022a965453b7a4a27d2cc1",
    "sharp_in_head/title.wav": "fec35d9f99a3242fb7318ee704dc3d4b002f513c7e6832086773e8a47cbebd6b",
}
CREDIT = "Safety Stoat Studios (Zachary Rubenstein), Free VGMs, CC0 1.0"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(*args: str) -> None:
    cmd = [sys.executable, "-I", str(HERE / "prepare_music.py"), *args]
    print(">", " ".join(args[:1]), flush=True)
    subprocess.run(cmd, check=True, timeout=3600)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true", help="scarica i file mancanti dal commit fissato")
    a = ap.parse_args()
    for rel, want in FILES.items():
        p = SRC / rel
        if not p.exists() and a.download:
            p.parent.mkdir(parents=True, exist_ok=True)
            print("scarico", rel, flush=True)
            urllib.request.urlretrieve(RAW + rel, p)
        if not p.exists():
            print(f"manca {p}: rilancia con --download", file=sys.stderr)
            return 2
        got = sha256(p)
        if got != want:
            print(f"{rel}: sha256 {got} diverso da quello atteso {want}", file=sys.stderr)
            return 2
    print("sorgenti verificate (sha256)")

    vgm = SRC / "MD_tracks" / "i_wondered_what_i_could_do_with_it.vgm"
    work = MUSIC / "_work" / "stage1_src"
    seconds = 2 * 4656960 / 44100.0  # due giri interi del VGM
    print(vgm_stems.split(vgm, {"fm1"}, work, seconds, unroll_times=2), flush=True)
    stem = work / vgm.stem
    prepare("stage1", "--main", f"{stem}__base.wav", "--layer", f"arena={stem}__layer.wav",
            "--min-loop", "100", "--max-loop", "110", "--bpm-hint", "150", "--placeholder",
            "--license", "CC0-1.0", "--title", "I Wondered What I Could Do With It (segnaposto)",
            "--source", f"{CREDIT}: MD_tracks/i_wondered_what_i_could_do_with_it.vgm "
                        f"(https://github.com/jerellsworth/free_vgms, commit {COMMIT[:7]}); reso con libgme "
                        "(ffmpeg 9.0.2) dal VGM srotolato due volte; strato arena = canale FM 2 (percussioni FM), "
                        "base = tutto il resto",
            "--note", "libgme suona circa lo 0,05% più lento del nominale: il BPM è quello misurato sul loop")
    prepare("title", "--main", str(SRC / "sharp_in_head" / "title.wav"), "--bpm-hint", "150",
            "--min-loop", "60", "--placeholder", "--license", "CC0-1.0",
            "--title", "Title, da Sharp in Head (segnaposto)",
            "--source", f"{CREDIT}: sharp_in_head/title.wav (https://github.com/jerellsworth/free_vgms, "
                        f"commit {COMMIT[:7]}); WAV dell'autore")
    prepare("clear", "--main", str(SRC / "MD_tracks" / "my_fathers_eyes.wav"), "--jingle", "116.95", "119.45",
            "--fade-in", "0.005", "--fade-out", "0.6", "--placeholder", "--license", "CC0-1.0",
            "--title", "Finale di My Father's Eyes (segnaposto)",
            "--source", f"{CREDIT}: MD_tracks/my_fathers_eyes.wav (https://github.com/jerellsworth/free_vgms, "
                        f"commit {COMMIT[:7]}); cadenza finale in Sol maggiore, 116,95-119,45 s")

    lines = [
        "# Fonti della musica in questa cartella",
        "",
        "Musica segnaposto, da sostituire con i brani di Suno (vedi ../suno/PROMPT.md).",
        "Ricreata da `tools/audio/make_placeholder_music.py` del repo; i dettagli di ogni brano sono in `music.json`.",
        "",
        f"- Fonte: {CREDIT}.",
        f"  - Repository: https://github.com/jerellsworth/free_vgms, commit `{COMMIT}`.",
        "  - Pagina: https://safetystoatstudios.itch.io/free-vgms (\"This is a pack of CC0-licensed music",
        "    compatible with the Sega Mega Drive [...] You can use them for whatever you want!\").",
        "  - Licenza: CC0 1.0 Universal (file LICENSE del repository, verificato il 3 novembre 2026).",
        "  - Credito facoltativo: \"Music: Safety Stoat Studios (CC0)\".",
        "- File usati (sha256):",
    ]
    lines += [f"  - `{rel}`: `{h}`" for rel, h in FILES.items()]
    lines += ["", "Strumenti: ffmpeg 9.0.2 essentials (gyan.dev, GPL-3.0) e PyMusicLooper 3.6.0 (MIT), "
              "usati solo per preparare i file."]
    (MUSIC / "FONTI.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("scritto", MUSIC / "FONTI.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
