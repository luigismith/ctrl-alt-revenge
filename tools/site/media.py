#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Media del sito e del README, presi dal gioco vero. Si rifanno tutti quando cambia la grafica.

Uso, dalla radice del repository, con il Python del laboratorio:

    python -I tools/site/media.py                  # tutto: copia, import, cattura, media
    python -I tools/site/media.py --no-capture     # rifà i media dalla cattura già pronta
    python -I tools/site/media.py --only sprite,logo,font,icone

Se cambia la grafica del gioco (sprite, sfondi, interfaccia, effetti: per esempio dopo la prova del cel
shading) serve il giro completo, senza --no-capture: il video, il poster, la GIF, le schermate e
l'anteprima social vengono dalla cattura, e una cattura vecchia mescolerebbe i due stili. Per questo la
cattura porta l'impronta della grafica e del replay (cattura.json): con --no-capture, se l'impronta non
torna, lo script si ferma (--forza per andare avanti lo stesso).

Passi (i nomi valgono per --only): copia, cattura, video, gif, schermate, social, sprite, ritratti,
ui, livello, logo, font, icone, manifest. Il manifesto (site/media/media.json) si riscrive sempre
alla fine.

Come lavora:
1. copia game/ in %USERPROFILE%/ctrlaltrevenge-lab/sito/godot, senza .godot/ né
   assets_private/, e la importa: le catture non toccano il repository;
2. registra il replay tests/replays/demo.json con Movie Maker (tools/run_godot.sh, --write-movie,
   --fixed-fps 60): un PNG 480x270 per tick in sito/media/cattura. La musica resta fuori:
   Godot non vede la cartella music del laboratorio e il WAV della registrazione si cancella;
3. controlla le zone vietate (VIETATI, qui sotto): per ogni fotogramma usato trova dove sta la
   telecamera confrontando la cattura con il piano della strada (backdrop.png), ricostruisce dove
   finisce ogni piano di layers.json e che cosa lo copre, e si ferma se in un ritaglio si vede
   anche un pixel di una zona vietata. Le zone "spegni" (luci cyan: il cyan, nel gioco, è solo di
   GIG) diventano il colore scuro del piano; le zone "copri" prendono il colore del fondo; le zone
   "togli" escono solo dai pezzi del livello per il sito (i cartelloni dei tetti). Regge se
   cambiano gli sprite o la loro luce; se cambia la strada le zone vanno ridisegnate: lo script se
   ne accorge dalle misure dei piani, ma non se la strada nuova ha le stesse misure (impronta in
   STRADA_IMPRONTA);
4. con Pillow e l'FFmpeg del laboratorio prepara, ingrandendo solo per multipli interi e con il
   vicino più prossimo (pixel netti):
   - site/media/eroe.webm, eroe.mp4, eroe-poster.png: loop di circa 6 s a 3x (1440x810, 60 fps),
     solo la rissa davanti al KEBAB. WebM VP9 profilo 1 in 4:4:4: il colore non si dimezza e i
     bordi dei pixel restano netti (Chrome ed Edge; chi non lo decodifica lo capisce dal tipo
     MIME e passa all'MP4); MP4 H.264 High in 4:2:0 per tutti gli altri (Safari). Senza audio;
   - site/media/eroe-2x.webm: lo stesso loop a 2x (960x540) per i telefoni (<source media>): sui
     telefoni il gioco sta a 2 pixel del dispositivo per pixel del gioco, quindi è a 1:1, pesa
     meno e costa meno decodificarlo;
   - docs/media/demo.gif: GIF del README a 2x (960x540), 20 fotogrammi al secondo, al massimo 3 MB;
   - site/media/schermate/*.png: ritagli a 1x (il sito li ingrandisce a multipli interi);
   - docs/media/schermate/*-2x.png: gli stessi ritagli a 2x, per il README (GitHub non li
     ingrandisce a pixel netti: il README li mostra a metà, netti su ogni schermo);
   - site/media/social.png: anteprima social 1280x640, gioco a 3x più il logo a 2x;
   - site/media/sprite/*.png e *.json: strisce di GIG, punk e bruto (guardia, camminata, una
     mossa) prese dagli atlanti di game/assets/sprites, con fotogrammi e durate; per GIG anche
     la striscia delle normali (gig-normali.png), per la prova della luce sul sito;
   - site/media/ui/: ritratti dell'HUD con la loro cornice (GIG anche con l'occhio spento, com'è
     prima del riavvio), barra della vita, VAI, ZONA LIBERATA, CONTINUA? e le cifre grandi;
   - site/media/livello/: i tetti (near.png) senza i cartelloni, un tratto di strada (backdrop e
     floor) senza le zone vietate e il graffito REVENGE, con le loro mappe emissive;
   - site/media/logo/logo-1x.png, logo-2x.png e logo-4x.png;
   - site/media/font/*.woff2: i font CAR Pixel (servono fontTools e brotli: se mancano nel
     Python in uso, lo script li prende con uv, nelle versioni fissate in WOFF2_CON; la prima
     volta serve la rete);
   - site/media/icone/: favicon dalla testa di GIG a 16, 32 e 180 px, più favicon.ico;
   - site/media/media.json: misure, pesi, testi alternativi in italiano e inglese, tipi MIME
     dei video, fotogrammi usati, zone controllate e dati della cattura.
5. nel laboratorio scrive sito/media/provino.png, un provino con tutto, da guardare a occhio.

I momenti scelti (fotogrammi del replay, costanti qui sotto) valgono finché il replay resta lo
stesso: se la cattura non finisce al tick atteso lo script si ferma (--forza per andare avanti
lo stesso, dopo aver ricontrollato i fotogrammi). Cambiare gli sprite non sposta i tick.

Licenze: questo script è MIT; i file prodotti sono asset del gioco (LicenseRef-CAR-Assets, vedi
REUSE.toml).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "game"
LAB = Path(os.environ.get("CAR_LAB") or Path(os.environ.get("USERPROFILE") or Path.home()) / "ctrlaltrevenge-lab")
WORK = LAB / "sito"
COPY = WORK / "godot"
MEDIA_WORK = WORK / "media"
FRAMES = MEDIA_WORK / "cattura"
FFMPEG = next((f for f in (LAB / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe", LAB / "tools" / "ffmpeg" / "bin" / "ffmpeg")
               if f.exists()), Path(shutil.which("ffmpeg") or LAB / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"))

SITE_MEDIA = ROOT / "site" / "media"
DOCS_MEDIA = ROOT / "docs" / "media"
MANIFEST = SITE_MEDIA / "media.json"

VIEW_W, VIEW_H = 480, 270
TICKS = 60
REPLAY = "res://tests/replays/demo.json"
ATTESO_TICK_FINE = 3841          # "Livello finito: ... tick 3841" del replay dimostrativo, seme 13

MAX_FILE = 4 * 1024 * 1024
MAX_TOTALE = 15 * 1024 * 1024
MAX_GIF = 3 * 1024 * 1024

# ------------------------------------------------------------------ momenti scelti
# Il fotogramma k mostra lo stato dopo il tick k del livello (game/tests/README.md).
# Intervalli [primo, ultimo escluso].

# Loop dell'eroe: solo la rissa davanti al KEBAB, con il graffito REVENGE e la saracinesca di ARIA VERA.
# La telecamera sta ferma dal 513 al 1186. Comincia e finisce dentro la stessa combo (656 -> 657), così
# il giro è continuo, e il primo fotogramma, il gancio cyber che solleva il punk, fa da poster.
EROE = [
    (657, 741),    # gancio cyber e calcio: il punk vola via e resta a terra
    (1010, 1187),  # secondo scambio e il punk va giù (dal 1187 compare VAI e la telecamera riparte verso la FARMACIA)
    (544, 657),    # il punk arriva: jab, jab... e si ricomincia dal gancio
]
EROE_SCALA = 3
EROE_SCALA_PICCOLO = 2           # eroe-2x.webm, per i telefoni
EROE_MEDIA_PICCOLO = "(max-width: 699px)"
EROE_CRF_H264 = 21               # 17 con la pioggia; la strada del Wind Day, a 17, pesava 4,4 MB
EROE_CRF_VP9 = 32

# GIF del README: gli stessi momenti, 20 al secondo, senza il secondo scambio. Lì lo scossone del colpo e
# una raffica del Wind Day cambiano la luce di tutta la strada a ogni fotogramma, e la GIF passava i 3 MB
# (4,6 MB); il loop resta continuo: gancio e calcio, il punk a terra, il punk che arriva, jab, jab.
GIF = [EROE[0], EROE[2]]
GIF_PASSO = 3                    # un fotogramma ogni 3 tick: 20 al secondo
GIF_SCALA = 2

# Schermate a 1x: (nome, fotogramma, ritaglio x0, y0, x1, y1 in pixel del gioco, alt it, alt en).
# I ritagli tengono fuori le zone vietate (lo verifica controlla_zone); nell'arena si taglia sotto
# il cartellone di Pasqua dei tetti.
SCHERMATE = [
    ("combo", 662, (200, 32, 480, 270),   # senza l'HUD: l'insegna KEBAB e il calcio sul punk
     "Nello slice: combo sul punk davanti all'insegna KEBAB, il gancio cyber e poi il calcio finale.",
     "In the slice: a combo on the punk under the KEBAB sign, the cyber hook and then the finishing kick."),
    ("cavo", 1658, (150, 50, 480, 270),
     "Nello slice: GIG salta il cavo elettrico che scintilla nella pozzanghera.",
     "In the slice: GIG leaps over a live power cable sparking in a puddle."),
    ("arena", 2750, (20, 75, 480, 270),
     "Nello slice, nell'arena: il calcio di GIG manda il punk addosso al bruto.",
     "In the slice, in the arena: GIG's kick sends the punk crashing into the brute."),
    ("presa", 3004, (20, 75, 480, 270),
     "Nello slice: GIG tiene il bruto per la presa e lo colpisce con una ginocchiata.",
     "In the slice: GIG holds the brute in a grab and drives a knee into him."),
]

# Anteprima social 1280x640: il fotogramma a 3x (1440x810) spostato a sinistra di 160 px (la rissa è a
# destra) e tagliato di 90 px sopra e 80 sotto; a sinistra sfuma a scacchi nella notte e il logo a 2x copre l'HUD.
SOCIAL_FOTOGRAMMA = 657
SOCIAL_SCALA = 3
SOCIAL_SPOSTA = (-160, -90)
SOCIAL_LOGO = (40, 28, 2)        # x, y, scala
SOCIAL_HUD = [(0, 0, 156, 42), (424, 0, 480, 16)]   # l'HUD nel fotogramma: ritratto e barre, punteggio

# Strisce degli sprite: (file, nome sul sito, atlante, [(animazione sul sito, animazione, AttackData)]).
SPRITE = [
    ("gig", "GIG", "gig/gig.json",
     [("guardia", "idle", None), ("camminata", "walk", None), ("gancio", "hook", "gig_hook")]),
    ("punk", "Punk", "thug_punk/thug_punk.json",
     [("guardia", "idle", None), ("camminata", "walk", None), ("gancio_caricato", "haymaker", "thug_punk_haymaker")]),
    ("bruto", "Bruto", "thug_bruiser/thug_bruiser.json",
     [("guardia", "idle", None), ("camminata", "walk", None), ("pugno", "punch", "thug_bruiser_punch")]),
]
# Per la prova della luce sul sito: anche la striscia delle normali di questi personaggi.
SPRITE_NORMALI = {"gig"}
# E la striscia "spenta", com'è GIG prima del riavvio, per i cartelloni della storia.
SPRITE_SPENTO = {"gig"}
METALLO = [(0x3a, 0x33, 0x52), (0x58, 0x50, 0x73), (0x8e, 0x86, 0xab), (0xc9, 0xc2, 0xde)]   # tools/fxui/palette.py

ALT_EROE = ("GIG colpisce il punk con il gancio del braccio cyber, nella polvere rossa del Wind Day, davanti "
            "all'insegna KEBAB.",
            "GIG lands a cyber-arm hook on the punk in the red dust of the Wind Day, under the KEBAB sign.")
DESCR_VIDEO = ("Il gioco in azione, davanti al kebab: jab, jab, gancio cyber e calcio sul punk, che alla fine "
               "va giù.",
               "Gameplay outside the kebab shop: jab, jab, cyber hook and kick on the punk, who finally goes "
               "down.")
ALT_SOCIAL = ("Il logo di CTRL+ALT REVENGE! sopra GIG che colpisce un punk con il gancio cyber, in una strada "
              "rossa di polvere.",
              "The CTRL+ALT REVENGE! logo over GIG landing a cyber hook on a punk in a street red with dust.")

# ------------------------------------------------------------------ zone vietate
# Quello che il sito non deve mostrare, in coordinate dei piani di game/assets/env/sotto_la_linea/layers.json:
# (piano, x0, y0, x1, y1, cosa, azione). Con "vieta" lo script si ferma se in un ritaglio usato se ne vede
# anche un pixel; con "spegni" i pixel cyan che si vedono prendono il colore scuro del piano lì accanto (luci
# spente); con "copri" i pixel della cosa che si vedono prendono il colore del fondo del riquadro; con
# "togli" la cosa esce solo dai pezzi del livello del sito (tetti e strada), e nelle catture resta.
# La strada del Wind Day (novembre 2026) non ha più niente da vietare: niente croce rossa (la croce della
# FARMACIA è verde, le croci delle targhe dei necrologi sono nere), niente insegne HOTEL e CINEMA, niente
# graffito GIG, luna, stelle o luci cyan. Restano i due cartelloni dei tetti, che nella striscia dei tetti
# del sito, ripetuta in orizzontale, si vedrebbero tornare; si tolgono fino al tetto, gambe comprese.
LIVELLO = GAME / "assets" / "env" / "sotto_la_linea"
VIETATI = [
    ("near", 462, 30, 518, 95, "il cartellone MANODOPERA 2.0 dei tetti (parte sopra il palazzo basso)", "togli"),
    ("near", 518, 30, 656, 89, "il cartellone MANODOPERA 2.0 dei tetti", "togli"),
    ("near", 1225, 26, 1399, 78, "il cartellone di Pasqua dei tetti", "togli"),
]
# Misure attese dei piani: se cambiano, la strada è stata rifatta e le zone vanno ricontrollate.
MISURE_PIANI = {"sky": (480, 270), "far": (720, 155), "mid": (960, 259), "near": (1440, 210),
                "backdrop": (2400, 187), "floor": (2400, 108), "fg": (2880, 33)}
# SHA-256 di backdrop.png e near.png quando le zone qui sopra sono state ridisegnate: la strada nuova del
# Wind Day aveva le stesse misure di quella vecchia, e il controllo delle misure da solo non bastava.
STRADA_IMPRONTA = "0a3dbd4fe5760692bc1e48f4c0c1b6fb05142ae709d8d762055d6e71a7cccbcd"
MARGINE = 3                      # px di sicurezza attorno ai ritagli: scossoni e arrotondamenti

# Tratto di strada del sito (backdrop e floor): dall'insegna MALEDICONO al muro prima della FARMACIA,
# 1175 px come la striscia del sito (site/css/sito.css, site/js/sito.js).
STRADA_X = (65, 1240)
REVENGE = (848, 146, 894, 170)   # il graffito REVENGE sul tavolato dei lavori, con un filo di margine (46x24)


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ strumenti

def git_bash() -> str:
    """Bash di Git per Windows (non quello di WSL): serve a lanciare tools/run_godot.sh."""
    if os.environ.get("CAR_BASH"):
        return os.environ["CAR_BASH"]
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parent.parent
        for cand in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
            if cand.exists():
                return str(cand)
    cand = Path("C:/Program Files/Git/bin/bash.exe")
    if cand.exists():
        return str(cand)
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    sys.exit("Bash di Git non trovato: indica il percorso con la variabile CAR_BASH")


def run_godot(seconds: int, *args: str) -> str:
    """tools/run_godot.sh sulla copia del progetto; restituisce l'output di Godot. La musica resta
    fuori: USERPROFILE punta a una cartella vuota, così Godot non trova la musica del laboratorio."""
    quiet_home = MEDIA_WORK / "senza_musica"
    quiet_home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CAR_LAB"] = str(LAB)
    env["USERPROFILE"] = str(quiet_home)
    env["GODOT_PROJECT"] = COPY.as_posix()
    cmd = [git_bash(), (ROOT / "tools" / "run_godot.sh").as_posix(), str(seconds), *args]
    res = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    if res.returncode != 0:
        sys.exit("Godot non è andato a buon fine (vedi sopra)")
    # run_godot.sh scrive "output: /c/.../tools/out/logs/godot-....out" (percorso POSIX).
    out_file = next((l.split(":", 1)[1].strip() for l in res.stdout.splitlines() if l.startswith("output:")), "")
    p = ROOT / "tools" / "out" / "logs" / Path(out_file).name if out_file else None
    return p.read_text(encoding="utf-8", errors="replace") if p and p.exists() else ""


def ffmpeg(args: list[str], frames: list[int] | None = None, fps: int = TICKS) -> None:
    """FFmpeg del laboratorio; con frames, i fotogrammi della cattura arrivano in RGB grezzo dallo stdin."""
    if not FFMPEG.exists():
        sys.exit(f"FFmpeg non trovato: {FFMPEG}")
    cmd = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y"]
    if frames is not None:
        cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VIEW_W}x{VIEW_H}", "-r", str(fps), "-i", "-"]
    p = subprocess.Popen(cmd + args, stdin=subprocess.PIPE if frames is not None else None)
    if frames is not None:
        for k in frames:
            p.stdin.write(np.asarray(frame(k)).tobytes())
        p.stdin.close()
    if p.wait() != 0:
        sys.exit("FFmpeg non è andato a buon fine: " + " ".join(cmd + args))


_frame_cache: dict[int, Image.Image] = {}


def raw_frame(k: int) -> np.ndarray:
    p = FRAMES / ("f%08d.png" % k)
    if not p.exists():
        sys.exit(f"Manca il fotogramma {k} della cattura ({p}): rifai la cattura")
    return np.asarray(Image.open(p).convert("RGB"))


def frame(k: int) -> Image.Image:
    """Il fotogramma k per il sito: quello della cattura, con le luci cyan della torre spente."""
    if k not in _frame_cache:
        a = raw_frame(k).copy()
        livello().copri(k, a)
        livello().spegni(k, a)
        _frame_cache[k] = Image.fromarray(a, "RGB")
    return _frame_cache[k]


# ------------------------------------------------------------------ geometria del livello

def _round_half_away(v: float) -> int:
    """Come roundi di GDScript: metà lontano dallo zero."""
    return int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)


def _is_cyan(rgb: np.ndarray) -> np.ndarray:
    """Cyan pieno e chiaro: l'occhio di GIG nel ritratto dell'HUD."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    return (g > 140) & (b > 160) & (r < g - 40) & (r < b - 40)


def _tinta_cyan(rgb: np.ndarray) -> np.ndarray:
    """Tinta cyan anche scura (le luci della torre nel PNG del piano)."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    return (g > r + 50) & (b > r + 50) & (g > 90)


def _acceso_cyan(rgb: np.ndarray) -> np.ndarray:
    """Come appare una luce cyan nella cattura, schiarita dalla mappa emissiva fin quasi al bianco."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    return (b > 150) & (g > 120) & (b - r > 20) & (g - r > 20)


class Livello:
    """I piani di "Sotto la Linea" come li mette backdrop.gd: x = -roundi(cam_x * scroll), y fissa, più
    lo scossone della telecamera, uguale per tutti i piani. Serve a sapere che cosa si vede in ogni
    fotogramma della cattura senza guardarlo."""

    RIGHE = np.arange(50, 160, 3)        # righe della strada (sopra il marciapiede) per trovare la telecamera

    def __init__(self) -> None:
        spec = json.loads((LIVELLO / "layers.json").read_text(encoding="utf-8"))
        self.piani: dict[str, dict] = {}
        for l in spec["layers"]:
            img = np.asarray(Image.open(LIVELLO / l["image"]).convert("RGBA"))
            self.piani[l["name"]] = dict(l, img=img)
        diversi = [f"{n}: {self.piani[n]['img'].shape[1]}x{self.piani[n]['img'].shape[0]} invece di {w}x{h}"
                   for n, (w, h) in MISURE_PIANI.items()
                   if n not in self.piani or self.piani[n]["img"].shape[:2] != (h, w)]
        if diversi or set(self.piani) != set(MISURE_PIANI):
            sys.exit("I piani di Sotto la Linea sono cambiati (" + "; ".join(diversi or ["piani diversi"]) +
                     "): ridisegna VIETATI, STRADA_X e REVENGE in tools/site/media.py e aggiorna MISURE_PIANI.")
        if impronta_strada() != STRADA_IMPRONTA:
            sys.exit("backdrop.png o near.png sono cambiati: ricontrolla VIETATI, STRADA_X e REVENGE in "
                     "tools/site/media.py, poi aggiorna STRADA_IMPRONTA (" + impronta_strada() + ").")
        bd = self.piani["backdrop"]["img"]
        self.bd_rgb = bd[..., :3].astype(np.int16)
        self.bd_a = bd[..., 3] > 250
        self.stime: dict[int, tuple[int, int, float]] = {}
        # Il piano lontano a luci spente: ogni pixel cyan prende il colore del vicino non cyan più prossimo.
        far = self.piani["far"]["img"]
        spenta = far[..., :3].copy()
        cyan = _tinta_cyan(far[..., :3]) & (far[..., 3] > 0)
        for y, x in zip(*np.nonzero(cyan)):
            for d in range(1, 6):
                cand = [(y, x - d), (y, x + d), (y - d, x), (y + d, x)]
                ok = [(cy, cx) for cy, cx in cand if 0 <= cy < far.shape[0] and 0 <= cx < far.shape[1]
                      and far[cy, cx, 3] > 0 and not cyan[cy, cx]]
                if ok:
                    spenta[y, x] = far[ok[0][0], ok[0][1], :3]
                    break
        self.far_cyan = cyan
        self.far_spenta = spenta
        # Le zone "copri": il colore del fondo (il più frequente nel riquadro) e i pixel della cosa da coprire.
        self.copri_dati: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for i, (nome, zx0, zy0, zx1, zy1, _, azione) in enumerate(VIETATI):
            if azione != "copri":
                continue
            img = self.piani[nome]["img"]
            riq = img[zy0:zy1, zx0:zx1, :3].reshape(-1, 3)
            colori, quanti = np.unique(riq, axis=0, return_counts=True)
            fondo = colori[int(np.argmax(quanti))]
            segno = np.zeros(img.shape[:2], bool)
            segno[zy0:zy1, zx0:zx1] = np.any(img[zy0:zy1, zx0:zx1, :3] != fondo, axis=-1)
            self.copri_dati[i] = (fondo, segno)

    # ---- dove sta la telecamera
    def _punteggio(self, f: np.ndarray, x: int, dy: int) -> float:
        src = self.RIGHE - dy
        b = self.bd_rgb[src, x:x + VIEW_W]
        m = self.bd_a[src, x:x + VIEW_W]
        ok = (np.abs(f[self.RIGHE].astype(np.int16) - b).sum(-1) < 24) & m
        return float(ok.sum()) / max(1, int(m.sum()))

    def stima(self, k: int) -> tuple[int, int, float]:
        """(x della strada sullo schermo, spostamento verticale, qualità del confronto) nel fotogramma k."""
        if k in self.stime:
            return self.stime[k]
        f = raw_frame(k)
        vicino = self.stime.get(k - 1)
        larghe = range(0, self.bd_rgb.shape[1] - VIEW_W + 1)
        xs = range(max(0, vicino[0] - 12), min(larghe.stop, vicino[0] + 13)) if vicino else larghe
        best = (-1.0, 0, 0)
        for dy in (0, -1, 1, -2, 2, -3, 3):
            for x in xs:
                s = self._punteggio(f, x, dy)
                if s > best[0]:
                    best = (s, x, dy)
            if best[0] >= 0.8:
                break
        if best[0] < 0.8 and vicino:
            # la telecamera ha fatto un salto più lungo del solito: si cerca su tutta la strada
            for x in larghe:
                s = self._punteggio(f, x, best[2])
                if s > best[0]:
                    best = (s, x, best[2])
        if best[0] < 0.6:
            sys.exit(f"Fotogramma {k}: non riconosco la strada dello slice (confronto {best[0]:.2f}). "
                     "La cattura o backdrop.png sono cambiati: ricontrolla VIETATI in tools/site/media.py.")
        self.stime[k] = (best[1], best[2], best[0])
        return self.stime[k]

    def posizione(self, nome: str, k: int) -> tuple[int, int]:
        """Dove finisce sullo schermo l'angolo in alto a sinistra del piano `nome` nel fotogramma k."""
        cam, dy, _ = self.stima(k)
        l = self.piani[nome]
        return -_round_half_away(cam * l["scroll"]), l["y"] + dy

    def coperto(self, nome: str, k: int, cache: dict | None = None) -> np.ndarray:
        """Maschera VIEW_H x VIEW_W dei pixel coperti dai piani davanti a `nome` (HUD e personaggi esclusi)."""
        if cache is not None and (nome, k) in cache:
            return cache[(nome, k)]
        z = self.piani[nome]["z"]
        out = np.zeros((VIEW_H, VIEW_W), bool)
        for altro, l in self.piani.items():
            if l["z"] <= z:
                continue
            ox, oy = self.posizione(altro, k)
            a = l["img"][..., 3] > 0
            h, w = a.shape
            y0, y1 = max(0, oy), min(VIEW_H, oy + h)
            x0, x1 = max(0, ox), min(VIEW_W, ox + w)
            if y0 < y1 and x0 < x1:
                out[y0:y1, x0:x1] |= a[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        if cache is not None:
            cache[(nome, k)] = out
        return out

    def visibili(self, zona: tuple, k: int, cache: dict | None = None) -> np.ndarray:
        """Maschera VIEW_H x VIEW_W dei pixel della zona che si vedono nel fotogramma k."""
        nome, zx0, zy0, zx1, zy1 = zona[:5]
        l = self.piani[nome]
        ox, oy = self.posizione(nome, k)
        a = np.zeros_like(l["img"][..., 3], dtype=bool)
        a[zy0:zy1, zx0:zx1] = l["img"][zy0:zy1, zx0:zx1, 3] > 0
        out = np.zeros((VIEW_H, VIEW_W), bool)
        h, w = a.shape
        y0, y1 = max(0, oy), min(VIEW_H, oy + h)
        x0, x1 = max(0, ox), min(VIEW_W, ox + w)
        if y0 < y1 and x0 < x1:
            out[y0:y1, x0:x1] = a[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        return out & ~self.coperto(nome, k, cache)

    def copri(self, k: int, a: np.ndarray) -> int:
        """Copre nel fotogramma (array RGB) le zone "copri" con il loro fondo; restituisce i pixel cambiati.
        Si toccano solo i pixel uguali a quelli del piano: pioggia, personaggi ed effetti davanti restano."""
        cambiati = 0
        for i, (fondo, segno) in self.copri_dati.items():
            zona = VIETATI[i]
            vis = self.visibili(zona, k)
            if not vis.any():
                continue
            ox, oy = self.posizione(zona[0], k)
            img = self.piani[zona[0]]["img"]
            ys, xs = np.nonzero(vis)
            fy, fx = ys - oy, xs - ox
            uguali = np.abs(a[ys, xs].astype(int) - img[fy, fx, :3].astype(int)).sum(-1) < 12
            sel = segno[fy, fx] & uguali
            a[ys[sel], xs[sel]] = fondo
            cambiati += int(sel.sum())
        return cambiati

    def spegni(self, k: int, a: np.ndarray) -> int:
        """Spegne nel fotogramma (array RGB) le luci delle zone "spegni"; restituisce i pixel cambiati."""
        cambiati = 0
        for zona in VIETATI:
            if zona[6] != "spegni" or zona[0] != "far":
                continue
            vis = self.visibili(zona, k)
            if not vis.any():
                continue
            ox, oy = self.posizione("far", k)
            # Lo scossone sposta i piani di qualche pixel rispetto al calcolo: si cerca lo spostamento che
            # fa combaciare meglio i pixel non cyan della torre, poi si spengono quelli cyan.
            ys, xs = np.nonzero(vis)
            best = (-1, 0, 0)
            for ddx in range(-MARGINE, MARGINE + 1):
                for ddy in range(-MARGINE, MARGINE + 1):
                    sx, sy = xs + ddx, ys + ddy
                    ok = (sx >= 0) & (sx < VIEW_W) & (sy >= 0) & (sy < VIEW_H)
                    fx, fy = xs[ok] - ox, ys[ok] - oy
                    fr = a[sy[ok], sx[ok]].astype(int)
                    ref = self.piani["far"]["img"][fy, fx, :3].astype(int)
                    n = int(((np.abs(fr - ref).sum(-1) < 12) & ~self.far_cyan[fy, fx]).sum())
                    if n > best[0]:
                        best = (n, ddx, ddy)
            _, ddx, ddy = best
            for y, x in zip(ys, xs):
                fy, fx = y - oy, x - ox
                sy, sx = y + ddy, x + ddx
                if not (0 <= sy < VIEW_H and 0 <= sx < VIEW_W) or not self.far_cyan[fy, fx]:
                    continue
                if _acceso_cyan(a[sy, sx][None, :])[0]:
                    a[sy, sx] = self.far_spenta[fy, fx]
                    cambiati += 1
        return cambiati


_livello: Livello | None = None


def impronta_strada() -> str:
    import hashlib
    h = hashlib.sha256()
    for nome in ("backdrop.png", "near.png"):
        h.update((LIVELLO / nome).read_bytes())
    return h.hexdigest()


def livello() -> Livello:
    global _livello
    if _livello is None:
        _livello = Livello()
    return _livello


def controlla_zone(uso: str, frames: list[int], box: tuple[int, int, int, int]) -> list[str]:
    """Errori per le zone "vieta" che si vedono nel ritaglio `box` (x0, y0, x1, y1) dei fotogrammi."""
    errori = []
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(0, x0 - MARGINE), max(0, y0 - MARGINE), min(VIEW_W, x1 + MARGINE), min(VIEW_H, y1 + MARGINE)
    lv = livello()
    dove: dict[int, list[int]] = {}
    for k in frames:                      # nell'ordine dei segmenti: la stima segue la telecamera
        cache: dict = {}
        for i, zona in enumerate(VIETATI):
            if zona[6] == "vieta" and lv.visibili(zona, k, cache)[y0:y1, x0:x1].any():
                dove.setdefault(i, []).append(k)
    for i, ks in dove.items():
        errori.append(f"{uso}: si vede {VIETATI[i][5]} ({len(ks)} fotogrammi, il primo è il {ks[0]})")
    return errori


def step_controllo() -> dict:
    """Controlla tutti i ritagli che finiscono nel sito e nel README; si ferma alla prima zona vietata."""
    lv = livello()
    usi = [("video dell'eroe", frames_of(EROE), (0, 0, VIEW_W, VIEW_H)),
           ("GIF del README", frames_of(GIF, GIF_PASSO), (0, 0, VIEW_W, VIEW_H))]
    usi += [(f"schermata {n}", [k], box) for n, k, box, _, _ in SCHERMATE]
    sx, sy = SOCIAL_SPOSTA
    s = SOCIAL_SCALA
    usi.append(("anteprima social", [SOCIAL_FOTOGRAMMA],
                (max(0, -sx // s), max(0, -sy // s), min(VIEW_W, (1280 - sx + s - 1) // s), min(VIEW_H, (640 - sy + s - 1) // s))))
    errori = []
    for uso, frames, box in usi:
        errori += controlla_zone(uso, frames, box)
    # Il tratto di strada e il graffito REVENGE sono ritagli fissi di backdrop e floor.
    for nome, (a0, a1) in (("strada", STRADA_X), ("REVENGE", (REVENGE[0], REVENGE[2]))):
        for zona in VIETATI:
            if zona[0] in ("backdrop", "floor") and zona[6] == "vieta" and a0 < zona[3] and a1 > zona[1]:
                if nome == "strada" or (REVENGE[1] < zona[4] and REVENGE[3] > zona[2]):
                    errori.append(f"{nome}: il ritaglio {a0}-{a1} prende {zona[5]}")
    if errori:
        sys.exit("Zone vietate nei media:\n  " + "\n  ".join(errori) +
                 "\nCambia i momenti o i ritagli in tools/site/media.py (EROE, GIF, SCHERMATE, SOCIAL, STRADA_X).")
    spenti, coperti = {}, {}
    for k in sorted({k for _, frames, _ in usi for k in frames}):
        a = raw_frame(k).copy()
        c = lv.copri(k, a)
        n = lv.spegni(k, a)
        if n:
            spenti[k] = n
        if c:
            coperti[k] = c
    qualita = min((lv.stime[k][2] for k in lv.stime), default=1.0)   # senza zone "vieta" non si stima niente
    log(f"controllo: {len(lv.stime)} fotogrammi, nessuna zona vietata in vista (confronto minimo {qualita:.2f}); "
        f"luci della torre spente in {len(spenti)} fotogrammi; luna coperta in {len(coperti)} fotogrammi "
        f"(al massimo {max(coperti.values(), default=0)} pixel)")
    return {"zone": [{"piano": z[0], "riquadro": list(z[1:5]), "cosa": z[5], "azione": z[6]} for z in VIETATI],
            "fotogrammi_controllati": len(lv.stime), "luci_spente_in": len(spenti),
            "luna_coperta_in": len(coperti), "luna_pixel_coperti_max": max(coperti.values(), default=0),
            "confronto_minimo": round(qualita, 3)}


def up(im: Image.Image, s: int) -> Image.Image:
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)


def frames_of(segments: list[tuple[int, int]], step: int = 1) -> list[int]:
    return [k for a, b in segments for k in range(a, b, step)]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def site_rel(p: Path) -> str:
    return p.relative_to(SITE_MEDIA).as_posix()


# ------------------------------------------------------------------ 1. copia e cattura

def rmtree(path: Path) -> None:
    """shutil.rmtree che su Windows riprova: antivirus e indicizzatore tengono aperti per un attimo i
    file appena scritti, e i file in sola lettura non si cancellano al primo colpo."""
    def retry(func, p, exc):
        for _ in range(20):
            try:
                os.chmod(p, stat.S_IWRITE)
                func(p)
                return
            except FileNotFoundError:
                return
            except OSError:
                time.sleep(0.5)
        raise exc
    shutil.rmtree(path, onexc=retry)


def step_copia() -> None:
    """Copia game/ in sito/godot, senza la cache .godot/ e senza assets_private/ (musica)."""
    if COPY.exists():
        rmtree(COPY)
    shutil.copytree(GAME, COPY, ignore=shutil.ignore_patterns(".godot", "assets_private"))
    log(f"copia del progetto: {COPY}")
    run_godot(600, "--headless", "--import")


def step_cattura(forza: bool) -> dict:
    """Registra il replay dimostrativo con Movie Maker: un PNG 480x270 per tick."""
    if FRAMES.exists():
        rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    text = run_godot(600, "--write-movie", (FRAMES / "f.png").as_posix(), "--fixed-fps", str(TICKS),
                     "--quit-after", "6000", "--", "--replay", REPLAY, "--quit-at-end")
    wav = FRAMES / "f.wav"
    if wav.exists():
        wav.unlink()
    if "Music:" in text:
        sys.exit("La cattura ha caricato della musica: non deve succedere")
    # Niente date qui né nel manifesto: rifatti senza cambiamenti, i file restano identici byte per byte.
    info: dict = {"replay": "game/tests/replays/demo.json"}
    m = re.search(r"Godot Engine v(\S+)", text)
    if m:
        info["godot"] = m.group(1)
    m = re.search(r"Livello finito: punteggio (\d+), tick (\d+), hash ([0-9a-f]+)", text)
    if not m:
        sys.exit("La cattura non dice dove finisce il livello: controlla il log di Godot")
    info.update(punteggio=int(m.group(1)), tick_fine=int(m.group(2)), hash=m.group(3))
    info["fotogrammi"] = len(list(FRAMES.glob("f*.png")))
    info["impronta_grafica"] = impronta_grafica()
    (FRAMES / "cattura.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"cattura: {info['fotogrammi']} fotogrammi, fine al tick {info['tick_fine']}, in {FRAMES}")
    check_cattura(info, forza)
    return info


GRAFICA = ["assets/sprites", "assets/env", "assets/ui", "assets/fx", "assets/fonts"]


def impronta_grafica() -> str:
    """SHA-256 della grafica che finisce nelle catture (sprite, sfondi, interfaccia, effetti, font) e del
    replay: se cambia, la cattura va rifatta. I .import si saltano: Godot li riscrive a ogni importazione."""
    import hashlib
    h = hashlib.sha256()
    files = [f for d in GRAFICA for f in (GAME / d).rglob("*") if f.is_file() and f.suffix != ".import"]
    files.append(GAME / REPLAY.replace("res://", ""))
    for f in sorted(files, key=lambda x: x.relative_to(GAME).as_posix()):
        h.update(f.relative_to(GAME).as_posix().encode("utf-8") + b"\0")
        h.update(f.read_bytes())
    return h.hexdigest()


def check_cattura(info: dict, forza: bool) -> None:
    if info.get("tick_fine") != ATTESO_TICK_FINE:
        msg = (f"Il replay finisce al tick {info.get('tick_fine')} e non al {ATTESO_TICK_FINE}: il gameplay o il "
               "replay sono cambiati e i fotogrammi scelti in tools/site/media.py vanno ricontrollati.")
        if not forza:
            sys.exit(msg + " Rilancia con --forza per andare avanti lo stesso.")
        log("ATTENZIONE: " + msg)


def load_cattura(forza: bool) -> dict:
    p = FRAMES / "cattura.json"
    if not p.exists():
        sys.exit(f"Manca la cattura ({p}): lancia lo script senza --no-capture")
    info = json.loads(p.read_text(encoding="utf-8"))
    info.pop("data", None)
    check_cattura(info, forza)
    ora = impronta_grafica()
    if "impronta_grafica" not in info:
        log("ATTENZIONE: la cattura non ha l'impronta della grafica (è di una versione vecchia di questo script): "
            "se sprite, sfondi o interfaccia sono cambiati, rifai la cattura senza --no-capture.")
    elif info["impronta_grafica"] != ora:
        msg = ("La grafica del gioco o il replay sono cambiati dopo la cattura: il video, la GIF, le schermate e "
               "l'anteprima social verrebbero dalla grafica vecchia. Rilancia senza --no-capture.")
        if not forza:
            sys.exit(msg + " (--forza per andare avanti lo stesso)")
        log("ATTENZIONE: " + msg)
    return info


# ------------------------------------------------------------------ 2. video dell'eroe

def avc_codecs(mp4: Path) -> str:
    """Stringa codecs dell'H.264 letta dal box avcC (profilo, vincoli, livello)."""
    data = mp4.read_bytes()
    i = data.find(b"avcC")
    if i < 0:
        return "avc1"
    prof, compat, level = data[i + 5], data[i + 6], data[i + 7]
    return "avc1.%02X%02X%02X" % (prof, compat, level)


def vp9_level(w: int, h: int, fps: int) -> str:
    """Livello VP9 minimo per dimensione e frequenza (tabella dei livelli di WebM/VP9)."""
    table = [("10", 829440, 36864), ("11", 2764800, 73728), ("20", 4608000, 122880), ("21", 9216000, 245760),
             ("30", 20736000, 552960), ("31", 36864000, 983040), ("40", 83558400, 2228224),
             ("41", 160432128, 2228224), ("50", 311951360, 8912896), ("51", 588251136, 8912896)]
    for name, rate, size in table:
        if w * h <= size and w * h * fps <= rate:
            return name
    return "62"


def step_video(out: dict) -> None:
    frames = frames_of(EROE)
    w, h = VIEW_W * EROE_SCALA, VIEW_H * EROE_SCALA
    tags = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            # File identici a ogni giro (niente UID casuali né date nel contenitore): nessuna modifica spuria in git.
            "-fflags", "+bitexact", "-flags:v", "+bitexact", "-map_metadata", "-1"]
    # Prima l'ingrandimento in RGB (vicino più prossimo), poi la conversione in YUV: così il 4:2:0 dell'MP4
    # dimezza la crominanza dell'immagine già ingrandita e non mescola i colori di pixel vicini del gioco.
    up_rgb = f"scale={w}:{h}:flags=neighbor,format=gbrp,scale=out_color_matrix=bt709:out_range=tv:flags=area+accurate_rnd"
    # Colori dichiarati per intero (BT.709 anche per primarie e trasferimento), come nel tipo MIME.
    bt709 = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"
    mp4 = SITE_MEDIA / "eroe.mp4"
    webm = SITE_MEDIA / "eroe.webm"
    SITE_MEDIA.mkdir(parents=True, exist_ok=True)
    log(f"video: {len(frames)} fotogrammi ({len(frames) / TICKS:.2f} s), H.264...")
    ffmpeg(["-vf", up_rgb + ",format=yuv420p," + bt709, "-c:v", "libx264", "-preset", "veryslow", "-crf", str(EROE_CRF_H264),
            "-x264-params", "no-deblock=1:aq-mode=3:psy-rd=1.0,0.25", "-g", "120", "-profile:v", "high",
            "-level:v", "4.2", "-pix_fmt", "yuv420p", *tags, "-movflags", "+faststart", "-an", str(mp4)], frames)
    log("video: VP9 4:4:4, due passate...")
    passlog = MEDIA_WORK / "vp9"
    vp9 = ["-vf", up_rgb + ",format=yuv444p," + bt709, "-c:v", "libvpx-vp9", "-profile:v", "1", "-pix_fmt", "yuv444p",
           "-crf", str(EROE_CRF_VP9), "-b:v", "0", "-g", "240", "-row-mt", "1", "-tile-columns", "1",
           "-auto-alt-ref", "1", "-lag-in-frames", "25", *tags, "-an", "-passlogfile", str(passlog)]
    ffmpeg(vp9 + ["-pass", "1", "-deadline", "good", "-cpu-used", "4", "-f", "null", os.devnull], frames)
    ffmpeg(vp9 + ["-pass", "2", "-deadline", "good", "-cpu-used", "1", str(webm)], frames)
    for p in MEDIA_WORK.glob("vp9*.log"):
        p.unlink()
    # Lo stesso loop a 2x per i telefoni: lì il gioco sta a 2 pixel del dispositivo per pixel del gioco.
    wp, hp = VIEW_W * EROE_SCALA_PICCOLO, VIEW_H * EROE_SCALA_PICCOLO
    up_piccolo = (f"scale={wp}:{hp}:flags=neighbor,format=gbrp,"
                  "scale=out_color_matrix=bt709:out_range=tv:flags=area+accurate_rnd")
    webm_piccolo = SITE_MEDIA / f"eroe-{EROE_SCALA_PICCOLO}x.webm"
    log("video: VP9 4:4:4 a 2x per i telefoni, due passate...")
    vp9p = ["-vf", up_piccolo + ",format=yuv444p," + bt709] + vp9[2:]
    ffmpeg(vp9p + ["-pass", "1", "-deadline", "good", "-cpu-used", "4", "-f", "null", os.devnull], frames)
    ffmpeg(vp9p + ["-pass", "2", "-deadline", "good", "-cpu-used", "1", str(webm_piccolo)], frames)
    for p in MEDIA_WORK.glob("vp9*.log"):
        p.unlink()
    poster = SITE_MEDIA / "eroe-poster.png"
    save_png(up(frame(EROE[0][0]), EROE_SCALA), poster)
    out["eroe"] = {
        "video": [
            {"file": site_rel(webm_piccolo), "media": EROE_MEDIA_PICCOLO,
             "type": f'video/webm; codecs="vp09.01.{vp9_level(wp, hp, TICKS)}.08.03.01.01.01.00"',
             "nota": "Lo stesso loop a 2x, per i telefoni: va per primo, con l'attributo media."},
            {"file": site_rel(webm), "type": f'video/webm; codecs="vp09.01.{vp9_level(w, h, TICKS)}.08.03.01.01.01.00"',
             "nota": "VP9 profilo 1 in 4:4:4: il colore non si dimezza e i bordi dei pixel restano netti. Va messo "
                     "per primo, con questo tipo: chi non sa decodificarlo passa da solo all'MP4."},
            {"file": site_rel(mp4), "type": f'video/mp4; codecs="{avc_codecs(mp4)}"',
             "nota": "H.264 High, 4:2:0: per tutti gli altri (Safari)."},
        ],
        "poster": site_rel(poster),
        "larghezza": w, "altezza": h, "fps": TICKS,
        "fotogrammi": len(frames), "durata_s": round(len(frames) / TICKS, 3),
        "audio": False,
        "segmenti": EROE,
        "alt_poster": {"it": ALT_EROE[0], "en": ALT_EROE[1]},
        "descrizione": {"it": DESCR_VIDEO[0], "en": DESCR_VIDEO[1]},
        "nota": "Loop continuo: l'ultimo fotogramma precede il primo. Il poster è il primo fotogramma.",
    }


# ------------------------------------------------------------------ 3. GIF del README

def step_gif(out: dict) -> None:
    frames = frames_of(GIF, GIF_PASSO)
    fps = TICKS // GIF_PASSO
    w, h = VIEW_W * GIF_SCALA, VIEW_H * GIF_SCALA
    gif = DOCS_MEDIA / "demo.gif"
    DOCS_MEDIA.mkdir(parents=True, exist_ok=True)
    # Una tavolozza sola per tutta la GIF, senza retinatura (pixel netti); i fotogrammi salvano solo il
    # rettangolo che cambia e i pixel uguali al precedente restano trasparenti.
    graph = (f"scale={w}:{h}:flags=neighbor,split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
             f"[b][p]paletteuse=dither=none:diff_mode=rectangle")
    ffmpeg(["-filter_complex", graph, "-loop", "0", str(gif)], frames, fps)
    size = gif.stat().st_size
    log(f"gif: {len(frames)} fotogrammi a {fps} al secondo, {size / 1e6:.2f} MB")
    if size > MAX_GIF:
        sys.exit(f"La GIF pesa {size} byte, più di 3 MB: accorcia GIF in tools/site/media.py")
    out["gif"] = {
        "file": rel(gif), "larghezza": w, "altezza": h, "fps": fps, "fotogrammi": len(frames),
        "durata_s": round(len(frames) / fps, 2), "segmenti": GIF,
        "alt": {"it": DESCR_VIDEO[0], "en": DESCR_VIDEO[1]},
    }


# ------------------------------------------------------------------ 4. schermate e anteprima social

def step_schermate(out: dict) -> None:
    """Ritagli a 1x: il sito li ingrandisce a multipli interi con image-rendering: pixelated."""
    items = []
    for name, k, box, alt_it, alt_en in SCHERMATE:
        p = SITE_MEDIA / "schermate" / f"{name}.png"
        im = frame(k).crop(box)
        save_png(im, p)
        save_png(up(im, 2), DOCS_MEDIA / "schermate" / f"{name}-2x.png")
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "scala": 1,
                      "fotogramma": k, "ritaglio": list(box), "alt": {"it": alt_it, "en": alt_en}})
    out["schermate"] = items
    log(f"schermate: {len(items)} a 1x")


def logo_image(scale: int) -> Image.Image:
    return up(Image.open(GAME / "assets" / "ui" / "title_logo.png").convert("RGBA"), scale)


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) / 16 + 1 / 32


def step_social(out: dict) -> None:
    """1280x640: notte a sinistra, il fotogramma a 3x che entra a scacchi (retino di Bayer, come nei
    giochi di una volta), il logo a 2x sopra l'HUD."""
    s = SOCIAL_SCALA
    sx, sy = SOCIAL_SPOSTA
    notte = np.array([23, 9, 19], np.uint8)   # --notte del sito, il prugna
    card = Image.new("RGBA", (1280, 640), (*notte.tolist(), 255))
    # L'HUD (ritratto, barre, vite e punteggio) sparisce nella notte, a scacchi: sopra c'è il logo.
    f = np.asarray(frame(SOCIAL_FOTOGRAMMA)).copy()
    yy, xx = np.mgrid[0:VIEW_H, 0:VIEW_W]
    dist = np.full((VIEW_H, VIEW_W), 1e9)
    for x0, y0, x1, y1 in SOCIAL_HUD:
        dx = np.maximum(np.maximum(x0 - xx, xx - (x1 - 1)), 0)
        dy = np.maximum(np.maximum(y0 - yy, yy - (y1 - 1)), 0)
        dist = np.minimum(dist, np.hypot(dx, dy))
    soglia = np.tile(BAYER4, (-(-VIEW_H // 4), -(-VIEW_W // 4)))[:VIEW_H, :VIEW_W]
    f[np.clip(1 - dist / 14, 0, 1) > soglia] = notte
    big = up(Image.fromarray(f, "RGB"), s).convert("RGBA")
    # sfumatura a scacchi sui primi 40 pixel del gioco che si vedono a sinistra, calcolata a 1x e poi ingrandita
    w = 40
    x0 = max(0, -(sx // s))                     # prima colonna del gioco che entra nell'anteprima
    a = np.ones((VIEW_H, VIEW_W), float)
    a[:, :x0] = 0
    a[:, x0:x0 + w] = (np.arange(w) + 0.5) / w
    soglia = np.tile(BAYER4, (-(-VIEW_H // 4), -(-VIEW_W // 4)))[:VIEW_H, :VIEW_W]
    alpha = Image.fromarray(np.where(a > soglia, 255, 0).astype(np.uint8), "L").resize(big.size, Image.NEAREST)
    big.putalpha(alpha)
    card.alpha_composite(big, (sx, sy))
    lx, ly, ls = SOCIAL_LOGO
    card.alpha_composite(logo_image(ls), (lx, ly))
    p = SITE_MEDIA / "social.png"
    save_png(card.convert("RGB"), p)
    out["social"] = {"file": site_rel(p), "larghezza": card.width, "altezza": card.height,
                     "fotogramma": SOCIAL_FOTOGRAMMA, "alt": {"it": ALT_SOCIAL[0], "en": ALT_SOCIAL[1]}}
    log("anteprima social: 1280x640")


# ------------------------------------------------------------------ 4b. interfaccia e livello

UI = GAME / "assets" / "ui"


def rgba(p: Path) -> Image.Image:
    return Image.open(p).convert("RGBA")


def step_ritratti(out: dict) -> None:
    """Ritratti dell'HUD con fondo e cornice, come nel gioco (ritratto a +1,+1 nella cornice da 34).
    Per GIG anche l'occhio spento: prima del riavvio il cyan non c'è ancora."""
    items = []
    fondo = rgba(UI / "portrait_back.png")
    for nome, ritratto, cornice in [("gig", "gig", "portrait_frame"), ("punk", "thug_punk", "portrait_frame_enemy"),
                                    ("bruto", "thug_bruiser", "portrait_frame_enemy")]:
        im = fondo.copy()
        im.alpha_composite(rgba(UI / "portraits" / f"{ritratto}.png"), (1, 1))
        im.alpha_composite(rgba(UI / f"{cornice}.png"))
        p = SITE_MEDIA / "ui" / f"ritratto-{nome}.png"
        save_png(im, p)
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height})
        if nome == "gig":
            a = np.asarray(im).copy()
            cyan = _is_cyan(a[..., :3]) & (a[..., 3] > 0)
            a[cyan] = (0x58, 0x50, 0x73, 255)      # METAL_LO di tools/fxui/palette.py
            p = SITE_MEDIA / "ui" / "ritratto-gig-spento.png"
            save_png(Image.fromarray(a, "RGBA"), p)
            items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height,
                          "nota": f"occhio spento: {int(cyan.sum())} pixel cyan diventano metallo scuro"})
    out["ritratti"] = items
    log(f"ritratti: {len(items)}")


def step_ui(out: dict) -> None:
    """Pezzi dell'interfaccia del gioco, così come sono: barra della vita, VAI, ZONA LIBERATA,
    CONTINUA? e le cifre grandi."""
    items = []
    for src, dst in [("bar_frame.png", "barra-cornice.png"), ("bar_fill.png", "barra-piena.png"),
                     ("bar_back.png", "barra-vuota.png"), ("bar_frame_enemy.png", "barra-cornice-nemico.png"),
                     ("bar_fill_enemy.png", "barra-piena-nemico.png"), ("bar_back_enemy.png", "barra-vuota-nemico.png"),
                     ("go_arrow.png", "vai.png"), ("msg_zone_clear.png", "zona-liberata.png"),
                     ("msg_continue.png", "continua.png"), ("big_digits.png", "cifre.png"),
                     ("stage_card_1.png", "cartello-livello-1.png")]:
        im = rgba(UI / src)
        p = SITE_MEDIA / "ui" / dst
        save_png(im, p)
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "fonte": rel(UI / src)})
    out["ui"] = items
    log(f"interfaccia: {len(items)} pezzi")


def senza_zone(nome: str, im: Image.Image) -> Image.Image:
    """Il piano `nome` con le zone vietate trasparenti."""
    a = np.asarray(im).copy()
    for z in VIETATI:
        if z[0] == nome and z[6] in ("vieta", "togli"):
            a[z[2]:z[4], z[1]:z[3], 3] = 0
    return Image.fromarray(a, "RGBA")


def step_livello(out: dict) -> None:
    """Pezzi veri del livello per il sito: i tetti (near) senza i cartelloni e un tratto di strada
    (backdrop sopra, floor alla sua y di layers.json) senza le zone vietate, ognuno con la sua mappa emissiva."""
    lv = livello()                              # controlla le misure dei piani
    pav_y = lv.piani["floor"]["y"]
    items = []
    for src, dst in [("near.png", "tetti.png"), ("near_emis.png", "tetti-luce.png")]:
        im = senza_zone("near", rgba(LIVELLO / src))
        p = SITE_MEDIA / "livello" / dst
        save_png(im, p)
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "fonte": rel(LIVELLO / src)})
    x0, x1 = STRADA_X
    for base, pav, dst in [("backdrop.png", "floor.png", "strada.png"),
                           ("backdrop_emis.png", "floor_emis.png", "strada-luce.png")]:
        tela = Image.new("RGBA", (MISURE_PIANI["backdrop"][0], VIEW_H), (0, 0, 0, 0))
        tela.alpha_composite(senza_zone("backdrop", rgba(LIVELLO / base)), (0, 0))
        tela.alpha_composite(senza_zone("floor", rgba(LIVELLO / pav)), (0, pav_y))
        im = tela.crop((x0, 0, x1, VIEW_H))
        p = SITE_MEDIA / "livello" / dst
        save_png(im, p)
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "x_nel_livello": [x0, x1]})
    im = rgba(LIVELLO / "backdrop.png").crop(REVENGE)
    p = SITE_MEDIA / "livello" / "revenge.png"
    save_png(im, p)
    items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "riquadro_nel_livello": list(REVENGE)})
    out["livello"] = items
    log(f"livello: tetti, strada ({x1 - x0} px) e REVENGE")


# ------------------------------------------------------------------ 5. strisce degli sprite

def spenta_striscia(sheet: Image.Image) -> Image.Image:
    """La striscia con i colori di tinta cyan (180-215 gradi, anche quasi bianchi) sulla rampa METALLO,
    in ordine di luminosità: il braccio e l'occhio spenti, con le stesse ombre."""
    import colorsys
    a = np.asarray(sheet).copy()
    vis = a[..., 3] > 0
    colori = np.unique(a[vis][:, :3], axis=0)
    cyan = []
    for c in colori:
        h, s, v = colorsys.rgb_to_hsv(*(c / 255.0))
        if 0.5 <= h <= 0.6 and s > 0.15 and v > 0.25:
            cyan.append((0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2], tuple(int(x) for x in c)))
    cyan.sort()
    for i, (_, c) in enumerate(cyan):
        k = round(i * (len(METALLO) - 1) / max(1, len(cyan) - 1)) if len(cyan) > 1 else 2
        m = np.all(a[..., :3] == c, axis=-1) & vis
        a[m, :3] = METALLO[k]
    return Image.fromarray(a, "RGBA")


def attack_data(name: str) -> dict:
    """startup, active, recovery e air di data/attacks/<name>.tres."""
    vals = {"air": False}
    for line in (GAME / "data" / "attacks" / f"{name}.tres").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(startup|active|recovery|air) = (\S+)$", line.strip())
        if m:
            vals[m.group(1)] = m.group(2) == "true" if m.group(1) == "air" else int(m.group(2))
    return vals


def _distribute(seg: list[dict], total: int) -> list[dict]:
    """Come AnimClip._distribute (src/combat/anim_clip.gd): `total` tick sui fotogrammi del segmento."""
    if total <= 0 or not seg:
        return []
    n = len(seg)
    if total < n:
        keep = {int(math.floor(float(k) * n / total)) for k in range(total)}
        return [dict(seg[i], ticks=1) for i in range(n) if i in keep]
    out = [dict(f) for f in seg]
    weights = sum(max(f["ticks"], 1) for f in seg)
    spare = total - n
    given = 0
    remainders = []
    for i, f in enumerate(seg):
        share = float(spare) * max(f["ticks"], 1) / weights
        whole = int(math.floor(share))
        out[i]["ticks"] = 1 + whole
        given += whole
        remainders.append((share - whole, -i))
    remainders.sort(reverse=True)
    k = 0
    while given < spare:
        out[-remainders[k][1]]["ticks"] += 1
        given += 1
        k += 1
    return out


def _split_index(frames: list[dict], startup: int, recovery: int) -> int:
    n = len(frames)
    boundary = float(sum(f["ticks"] for f in frames)) * startup / max(1.0, float(startup + recovery))
    split, t = n, 0
    for i in range(n):
        if float(t) >= boundary - 0.001:
            split = i
            break
        t += frames[i]["ticks"]
    if startup > 0:
        split = max(split, 1)
    if recovery > 0:
        split = min(split, n - 1)
    return max(0, min(split, n))


def retimed(frames: list[dict], startup: int, active: int, recovery: int) -> list[dict]:
    """Come AnimClip.retimed: in gioco le mosse durano i tick dell'AttackData, non quelli del JSON."""
    src = [dict(f) for f in frames]
    act = [i for i, f in enumerate(src) if "active" in f.get("tags", [])]
    if not act and active <= 0:
        split = _split_index(src, startup, max(recovery, 0))
        res = _distribute(src[:split], startup)
        return res + (src[split:] if recovery < 0 else _distribute(src[split:], recovery))
    if not act:
        act = [len(src) >> 1]
    a, b = act[0], act[-1]
    seg_s, seg_a, seg_r = src[:a], src[a:b + 1], src[b + 1:]
    if not seg_s and startup > 0:
        seg_s = [dict(seg_a[0])]
    if not seg_r and recovery > 0:
        seg_r = [dict(seg_a[-1])]
    res = _distribute(seg_s, startup) + _distribute(seg_a, active)
    return res + (seg_r if recovery < 0 else _distribute(seg_r, recovery))


def step_sprite(out: dict) -> None:
    items = []
    for key, label, atlas_rel, anims in SPRITE:
        atlas_json = GAME / "assets" / "sprites" / atlas_rel
        data = json.loads(atlas_json.read_text(encoding="utf-8"))
        atlas = Image.open(atlas_json.parent / data["image"]).convert("RGBA")
        rows = []
        for site_name, anim, atk in anims:
            src = data["animations"][anim]
            frs = src["frames"]
            if atk:
                ad = attack_data(atk)
                frs = retimed(frs, ad["startup"], ad["active"], -1 if ad["air"] else ad["recovery"])
            rows.append((site_name, anim, bool(src.get("loop", False)), frs))
        # Cella unica per personaggio, con i piedi (l'ancora) sempre nello stesso punto.
        left = max(f["anchor"][0] for _, _, _, frs in rows for f in frs)
        right = max(f["rect"][2] - f["anchor"][0] for _, _, _, frs in rows for f in frs)
        top = max(f["anchor"][1] for _, _, _, frs in rows for f in frs)
        bottom = max(f["rect"][3] - f["anchor"][1] for _, _, _, frs in rows for f in frs)
        cw, ch = left + right, top + bottom
        cols = max(len(frs) for _, _, _, frs in rows)
        sheet = Image.new("RGBA", (cw * cols, ch * len(rows)), (0, 0, 0, 0))
        normal = None
        if key in SPRITE_NORMALI and data.get("normal_image"):
            natlas = Image.open(atlas_json.parent / data["normal_image"]).convert("RGBA")
            normal = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
        animations = {}
        for r, (site_name, anim, loop, frs) in enumerate(rows):
            entries = []
            for c, f in enumerate(frs):
                x, y, w, h = f["rect"]
                ax, ay = f["anchor"]
                sheet.alpha_composite(atlas.crop((x, y, x + w, y + h)), (c * cw + left - ax, r * ch + top - ay))
                if normal is not None:
                    normal.alpha_composite(natlas.crop((x, y, x + w, y + h)), (c * cw + left - ax, r * ch + top - ay))
                entries.append({"x": c * cw, "y": r * ch, "tick": f["ticks"], "ms": round(f["ticks"] * 1000 / TICKS, 2)})
            total = sum(e["tick"] for e in entries)
            animations[site_name] = {"riga": r, "ciclo": loop, "animazione_nel_gioco": anim, "fotogrammi": entries,
                                     "tick_totali": total, "durata_ms": round(total * 1000 / TICKS, 2)}
        png = SITE_MEDIA / "sprite" / f"{key}.png"
        save_png(sheet, png)
        meta = {
            "formato": 1,
            "nota": "Generato da tools/site/media.py dagli atlanti del gioco: non modificare a mano.",
            "personaggio": label,
            "immagine": png.name,
            "dimensioni": [sheet.width, sheet.height],
            "cella": [cw, ch],
            "piedi": [left, top],
            "guarda": "destra",
            "scala": 1,
            "tick_al_secondo": TICKS,
            "fonte": rel(atlas_json),
            "animazioni": animations,
        }
        item = {"file": site_rel(png), "json": site_rel(js := SITE_MEDIA / "sprite" / f"{key}.json"),
                "personaggio": label, "cella": [cw, ch], "animazioni": list(animations)}
        if key in SPRITE_SPENTO:
            # Prima del riavvio il braccio e l'occhio sono spenti (il cyan nasce con il riavvio): i colori cyan
            # della striscia diventano la rampa del metallo dell'HUD, dal più scuro al più chiaro.
            spento = spenta_striscia(sheet)
            spng = SITE_MEDIA / "sprite" / f"{key}-spento.png"
            save_png(spento, spng)
            meta["varianti"] = {"spento": spng.name}
            item["spento"] = site_rel(spng)
        if normal is not None:
            npng = SITE_MEDIA / "sprite" / f"{key}-normali.png"
            save_png(normal, npng)
            meta["normali"] = npng.name
            meta["normali_nota"] = ("Normal map dell'atlante, stessa disposizione della striscia: R = x verso destra, "
                                    "G = y verso l'alto, B = verso chi guarda (128, 128, 255 = di fronte).")
            item["normali"] = site_rel(npng)
        js.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        items.append(item)
        log(f"sprite {key}: cella {cw}x{ch}, {', '.join(animations)}")
    out["sprite"] = items


# ------------------------------------------------------------------ 6. logo, font e icone

def step_logo(out: dict) -> None:
    items = []
    for s in (1, 2, 4):
        im = logo_image(s)
        p = SITE_MEDIA / "logo" / f"logo-{s}x.png"
        save_png(im, p)
        items.append({"file": site_rel(p), "larghezza": im.width, "altezza": im.height, "scala": s,
                      "alt": {"it": "CTRL+ALT REVENGE!", "en": "CTRL+ALT REVENGE!"}})
    out["logo"] = items
    log("logo: 1x, 2x e 4x")


# Versioni fissate: con un fontTools nuovo i WOFF2 potrebbero cambiare di qualche byte (differenze finte in git).
WOFF2_CON = ["fonttools==4.67.0", "brotli==1.2.0"]
WOFF2_CODE = ("import sys\nfrom fontTools.ttLib import TTFont\n"
              "for a, b in zip(sys.argv[1::2], sys.argv[2::2]):\n"
              "    f = TTFont(a, recalcTimestamp=False)\n    f.flavor = 'woff2'\n    f.save(b)\n")


def step_font(out: dict) -> None:
    pairs = [(GAME / "assets" / "fonts" / "car_pixel_bold.ttf", SITE_MEDIA / "font" / "car-pixel-bold.woff2", 700),
             (GAME / "assets" / "fonts" / "car_pixel_regular.ttf", SITE_MEDIA / "font" / "car-pixel-regular.woff2", 400)]
    (SITE_MEDIA / "font").mkdir(parents=True, exist_ok=True)
    args = [str(x) for a, b, _ in pairs for x in (a, b)]
    try:
        import brotli  # noqa: F401
        import fontTools  # noqa: F401
        cmd = [sys.executable, "-I", "-c", WOFF2_CODE, *args]
    except ImportError:
        uv = shutil.which("uv")
        if not uv:
            log("ATTENZIONE: per i WOFF2 servono fontTools e brotli (oppure uv): font saltati")
            return
        con = [x for pacchetto in WOFF2_CON for x in ("--with", pacchetto)]
        cmd = [uv, "run", "--no-project", "--quiet", *con, "python", "-I", "-c", WOFF2_CODE, *args]
    subprocess.run(cmd, check=True)
    out["font"] = [{"file": site_rel(b), "famiglia": "CAR Pixel", "peso": wt, "fonte": rel(a)} for a, b, wt in pairs]
    out["font_nota"] = ("Un pixel del font è un pixel del gioco a 12 px: per lettere nette usare solo multipli "
                        "di 12 px (24, 36, 48...). Glifi: ASCII, accentate italiane, « » “ ” ‘ ’ … – — ▶ ◀ ▲ ▼ ♥ × · ° ©.")
    log("font: WOFF2")


def ico_bytes(images: list[Image.Image]) -> bytes:
    """favicon.ico con immagini PNG dentro (una per misura), senza ricampionare."""
    blobs = []
    for im in images:
        b = io.BytesIO()
        im.save(b, "PNG", optimize=True)
        blobs.append(b.getvalue())
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for im, blob in zip(images, blobs):
        entries += struct.pack("<BBBBHHII", im.width % 256, im.height % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    return head + entries + b"".join(blobs)


def step_icone(out: dict) -> None:
    ui = GAME / "assets" / "ui"
    portrait = Image.open(ui / "portraits" / "gig.png").convert("RGBA")
    back = Image.open(ui / "portrait_back.png").convert("RGBA")
    # 32 px: il ritratto dell'HUD sul suo fondo "schermo".
    i32 = back.crop((1, 1, 33, 33))
    i32.alpha_composite(portrait)
    # 16 px: un pixel ogni due, con la fase che tiene l'occhio cyan, gli occhiali e la barba.
    a32 = np.asarray(i32)
    i16 = Image.fromarray(np.ascontiguousarray(a32[1::2, 1::2]))
    # 180 px (apple-touch-icon): fondo pieno, ritratto a 5x con un margine; niente angoli trasparenti.
    base = Image.new("RGBA", (36, 36), (18, 15, 36, 255))
    base.alpha_composite(back, (1, 1))
    base.alpha_composite(portrait, (2, 2))
    i180 = up(base, 5)
    items = []
    for im, name in ((i16, "favicon-16.png"), (i32, "favicon-32.png"), (i180, "apple-touch-icon.png")):
        p = SITE_MEDIA / "icone" / name
        save_png(im.convert("RGB") if name.startswith("apple") else im, p)
        items.append({"file": site_rel(p), "misura": im.width})
    ico = SITE_MEDIA / "icone" / "favicon.ico"
    ico.write_bytes(ico_bytes([i16, i32]))
    items.append({"file": site_rel(ico), "misura": "16 e 32"})
    out["icone"] = items
    log("icone: 16, 32, 180 e favicon.ico")


# ------------------------------------------------------------------ 7. manifesto e provino

def produced_files(out: dict) -> list[Path]:
    files: list[Path] = []
    for v in out.get("eroe", {}).get("video", []):
        files.append(SITE_MEDIA / v["file"])
    if "eroe" in out:
        files.append(SITE_MEDIA / out["eroe"]["poster"])
    for key in ("schermate", "ritratti", "ui", "livello", "logo", "font", "icone"):
        files += [SITE_MEDIA / it["file"] for it in out.get(key, [])]
    for it in out.get("sprite", []):
        files += [SITE_MEDIA / it["file"], SITE_MEDIA / it["json"]]
        for extra in ("normali", "spento"):
            if it.get(extra):
                files.append(SITE_MEDIA / it[extra])
    if "social" in out:
        files.append(SITE_MEDIA / out["social"]["file"])
    if "gif" in out:
        files.append(ROOT / out["gif"]["file"])
    return files


SEZIONI = ["controllo", "eroe", "gif", "schermate", "social", "sprite", "ritratti", "ui", "livello", "logo", "font",
           "font_nota", "icone"]


def step_manifest(out: dict, info: dict) -> None:
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    # Le parti non rifatte in questo giro restano quelle del manifesto precedente; l'ordine delle sezioni
    # è fisso, così lo stesso contenuto dà sempre lo stesso file.
    out = {k: out[k] if k in out else old[k] for k in SEZIONI if k in out or k in old}
    info = {k: v for k, v in (info or old.get("cattura", {})).items() if k != "data"}
    files = produced_files(out)
    # Elimina i file scritti in passato da questo script e non più prodotti (nomi cambiati).
    keep = {f.resolve() for f in files}
    for item in old.get("file", []):
        p = (ROOT / item["file"]).resolve()
        if p not in keep and p.exists() and (SITE_MEDIA.resolve() in p.parents or DOCS_MEDIA.resolve() in p.parents):
            p.unlink()
            log(f"tolto il vecchio {item['file']}")
    listing, total = [], 0
    for f in files:
        size = f.stat().st_size
        total += size
        listing.append({"file": rel(f), "byte": size})
        if size > MAX_FILE:
            sys.exit(f"{rel(f)} pesa {size} byte: il limite è 4 MB")
    manifest = {
        "formato": 1,
        "nota": "Generato da tools/site/media.py: non modificare a mano. I percorsi delle voci sono relativi a "
                "site/media/, quelli dell'elenco 'file' e della GIF alla radice del repository.",
        "cattura": info,
        **out,
        "file": listing,
        "totale_byte": total,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total += MANIFEST.stat().st_size
    log(f"manifesto: {len(files) + 1} file, {total / 1e6:.2f} MB in tutto")
    if total > MAX_TOTALE:
        sys.exit(f"I media pesano {total} byte: il limite è 15 MB")


def step_provino(out: dict) -> None:
    """Provino nel laboratorio (non nel repo): poster, schermate, social, sprite, logo e icone."""
    tiles: list[tuple[str, Image.Image]] = []
    if "eroe" in out:
        tiles.append(("eroe-poster", Image.open(SITE_MEDIA / out["eroe"]["poster"]).convert("RGB")))
    for it in out.get("schermate", []):
        tiles.append((it["file"], Image.open(SITE_MEDIA / it["file"]).convert("RGB")))
    if "social" in out:
        tiles.append(("social", Image.open(SITE_MEDIA / out["social"]["file"]).convert("RGB")))
    rows = tiles
    W = max([im.width for _, im in rows] + [0])
    extra = []
    for it in out.get("sprite", []):
        extra.append(up(Image.open(SITE_MEDIA / it["file"]).convert("RGBA"), 2))
        for k in ("spento", "normali"):
            if it.get(k):
                extra.append(up(Image.open(SITE_MEDIA / it[k]).convert("RGBA"), 2))
    for key in ("livello", "ritratti", "ui"):
        for it in out.get(key, []):
            im = Image.open(SITE_MEDIA / it["file"]).convert("RGBA")
            extra.append(im if im.width > 600 else up(im, 2))
    for it in out.get("logo", [])[1:2]:
        extra.append(Image.open(SITE_MEDIA / it["file"]).convert("RGBA"))
    for it in out.get("icone", []):
        if it["file"].endswith(".png"):
            extra.append(Image.open(SITE_MEDIA / it["file"]).convert("RGBA"))
    H = sum(im.height + 24 for _, im in rows) + sum(im.height + 16 for im in extra) + 16
    sheet = Image.new("RGBA", (max([W] + [im.width for im in extra]) + 32, H), (18, 15, 36, 255))
    d = ImageDraw.Draw(sheet)
    y = 8
    for name, im in rows:
        d.text((16, y), name, fill=(255, 226, 122, 255))
        sheet.paste(im, (16, y + 14))
        y += im.height + 24
    for im in extra:
        sheet.alpha_composite(im, (16, y))
        y += im.height + 16
    p = MEDIA_WORK / "provino.png"
    sheet.convert("RGB").save(p, optimize=True)
    log(f"provino: {p}")


# ------------------------------------------------------------------ main

STEPS = ["copia", "cattura", "video", "gif", "schermate", "social", "sprite", "ritratti", "ui", "livello", "logo",
         "font", "icone", "manifest"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-capture", action="store_true", help="usa la cattura già fatta")
    ap.add_argument("--only", default="", help="passi da fare, separati da virgole")
    ap.add_argument("--forza", action="store_true", help="va avanti anche se il replay non finisce al tick atteso")
    a = ap.parse_args()
    steps = [s.strip() for s in a.only.split(",") if s.strip()] or list(STEPS)
    for s in steps:
        if s not in STEPS:
            sys.exit(f"passo sconosciuto: {s} (passi: {', '.join(STEPS)})")
    if a.no_capture:
        steps = [s for s in steps if s not in ("copia", "cattura")]
    if "copia" in steps:
        step_copia()
    need_frames = any(s in steps for s in ("video", "gif", "schermate", "social"))
    if "cattura" in steps:
        info = step_cattura(a.forza)
    elif need_frames:
        info = load_cattura(a.forza)
    else:
        p = FRAMES / "cattura.json"
        info = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        info.pop("data", None)
    out: dict = {}
    if need_frames or "livello" in steps:
        # Prima di tutto le zone vietate: se un ritaglio ne mostra una, non si scrive niente.
        out["controllo"] = step_controllo()
    if "video" in steps:
        step_video(out)
    if "gif" in steps:
        step_gif(out)
    if "schermate" in steps:
        step_schermate(out)
    if "social" in steps:
        step_social(out)
    if "sprite" in steps:
        step_sprite(out)
    if "ritratti" in steps:
        step_ritratti(out)
    if "ui" in steps:
        step_ui(out)
    if "livello" in steps:
        step_livello(out)
    if "logo" in steps:
        step_logo(out)
    if "font" in steps:
        step_font(out)
    if "icone" in steps:
        step_icone(out)
    step_manifest(out, info or {})
    step_provino(json.loads(MANIFEST.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
