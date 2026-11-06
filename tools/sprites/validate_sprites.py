# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Controlla gli sprite dei personaggi contro docs/specifica-slice.md (§4 formato, §5 tempi).

Uso:  python -I tools/sprites/validate_sprites.py [cartella]   (predefinita: game/assets/sprites)
La cartella contiene una sottocartella per personaggio (gig, gig_spento, i nemici) con <id>.png e
<id>.json.
Se accanto c'è <id>.debug.json (scritto da build_chars.py) controlla anche la deriva dell'ancora.
Esce con codice 1 se trova errori; stampa anche gli avvisi.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))

REQUIRED = {
    "gig": ["idle", "walk", "run", "jump_rise", "jump_fall", "land", "jab1", "jab2", "hook", "kick", "air_kick",
            "grab_hold", "knee", "throw", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup"],
    # GIG prima del riavvio, col braccio morto: le mosse del prologo
    "gig_spento": ["idle", "walk", "run", "jump_rise", "jump_fall", "jump_arc", "land", "jab2", "mazza", "hurt_high",
                   "hurt_low", "knock_air", "knock_down", "getup", "crouch", "crouch_walk", "slide", "ledge_hang",
                   "ledge_climb"],
    "thug_punk": ["idle", "walk", "jab", "haymaker", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
                  "grabbed", "kneed", "thrown"],
    "thug_bruiser": ["idle", "walk", "punch", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
                     "grabbed", "kneed", "thrown"],
    # gli Esattori del prologo (decisione 63 della storia): stesse mosse dei nemici dello slice, più le loro
    "rider": ["idle", "walk", "jab", "haymaker", "pignora", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
              "grabbed", "kneed", "thrown"],
    "esattore": ["idle", "walk", "punch", "block", "charge_wind", "charge_run", "dizzy", "hurt_high", "hurt_low",
                 "knock_air", "knock_down", "getup", "grabbed", "kneed", "thrown"],
    "messo": ["idle", "walk", "read", "laser", "call", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
              "grabbed", "kneed", "thrown"],
}
# cicli: i tre dello slice più quelli delle mosse platform di prova (accovacciato, appeso alla sporgenza)
LOOPS = {"idle", "walk", "run", "crouch", "crouch_walk", "ledge_hang", "wall_slide", "wall_run", "hack", "charge_run", "dizzy",
         "pignora", "read", "call"}
# (avvio, attivo, recupero) in tick a 60 Hz, §5; None = non controllato
TIMING = {("gig", "jab1"): (3, 2, 9), ("gig", "jab2"): (3, 2, 9), ("gig", "hook"): (6, 3, 12),
          ("gig", "kick"): (10, 3, 20), ("gig", "air_kick"): (4, 8, None), ("gig", "knee"): (4, 3, 10),
          ("gig", "throw"): (8, 0, 14), ("gig_spento", "jab2"): (3, 2, 9), ("gig_spento", "mazza"): (14, 6, 15),
          ("thug_punk", "jab"): (18, 4, 18), ("thug_punk", "haymaker"): (33, 4, 28),
          ("thug_bruiser", "punch"): (26, 5, 26), ("rider", "jab"): (18, 4, 18), ("rider", "haymaker"): (33, 4, 28),
          ("esattore", "punch"): (26, 5, 26)}
PAIRS = ("grab_hold", "knee", "throw")
# varianti senza ritratto proprio: nell'interfaccia usano quello del personaggio base
NO_PORTRAIT = {"gig_spento"}
# animazioni sul posto in cui i piedi non devono muoversi affatto rispetto all'ancora
FEET_FIXED = {"idle", "hurt_high", "hurt_low", "grabbed", "grab_hold"}
ENEMIES = ("thug_punk", "thug_bruiser", "rider", "esattore", "messo")
TAGS = {"active", "cancel", "invuln", "armor", "hold", "air"}
SFX = {"whoosh_light", "whoosh_heavy", "hit_light", "hit_medium", "hit_heavy", "hit_kick", "knee", "grab", "throw",
       "body_fall", "body_thud", "step_a", "step_b", "jump", "land", "glint", "zap", "bin_hit", "bin_break", "pickup",
       "ko", "ui_move", "ui_confirm", "ui_pause", "go_arrow"}
FX = {"hit_spark_light", "hit_spark_heavy", "dust_land", "dust_skid", "glint", "cyber_spark", "ombra"}
# fx:<nome>@<punto>: l'effetto nasce nel punto del fotogramma (campo points), es. fx:cyber_spark@fist_l
EV_RE = re.compile(r"^(sfx:[a-z_]+|fx:[a-z_]+(@[a-z_]+)?|glint|step)$")
# punti del fotogramma (§4), relativi all'ancora: pugni, punte dei piedi, centro della testa, presa delle mani
POINTS = {"fist_l", "fist_r", "foot_l", "foot_r", "head", "grip"}
OUTLINE = (0x14, 0x0e, 0x1e)
# 30 colori (pipeline v7): rampe ridotte dentro ogni materiale, più contorni e dettagli
MAX_COLORS = 30


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, *a):
        self.errors.append(" ".join(str(x) for x in a))

    def warn(self, *a):
        self.warnings.append(" ".join(str(x) for x in a))



# I limiti di plausibilità sono pensati a 48 px/m: crescono con la scala di tools/sprites/camera.json.
S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera.json"), encoding="utf-8"))["pixels_per_meter"] / 48.0

def is_box(b):
    return isinstance(b, list) and len(b) == 4 and all(isinstance(v, int) for v in b) and b[2] > 0 and b[3] > 0


def check_char(cid, d, R, others):
    jp = os.path.join(d, cid + ".json")
    if not os.path.exists(jp):
        R.err(cid, ": manca", jp)
        return None
    data = json.load(open(jp, encoding="utf-8"))
    if data.get("id") != cid:
        R.err(cid, ": id sbagliato", data.get("id"))
    if data.get("format") != 1:
        R.err(cid, ": format deve valere 1")
    ppm = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera.json"), encoding="utf-8"))["pixels_per_meter"]
    if data.get("pixels_per_meter") != ppm:
        R.err(cid, ": pixels_per_meter deve valere", ppm, "(tools/sprites/camera.json)")
    ip = os.path.join(d, data.get("image", ""))
    if not os.path.exists(ip):
        R.err(cid, ": manca l'immagine", ip)
        return data
    im = Image.open(ip)
    if im.mode != "RGBA":
        R.err(cid, ": l'atlante deve essere RGBA, è", im.mode)
    W, H = im.size
    arr = np.asarray(im.convert("RGBA"))
    opaque = arr[arr[..., 3] > 0][:, :3]
    if len(opaque) and ((arr[..., 3] > 0) & (arr[..., 3] < 255)).any():
        R.err(cid, ": l'atlante ha pixel semitrasparenti")
    # atlante delle normali (luci dinamiche): stessa misura, opaco dove lo è l'atlante dei colori
    nimg = data.get("normal_image")
    if nimg is not None:
        npth = os.path.join(d, str(nimg))
        if not os.path.exists(npth):
            R.err(cid, ": manca l'atlante delle normali", npth)
        else:
            nim = Image.open(npth)
            if nim.size != im.size or nim.mode != "RGBA":
                R.err(cid, ": l'atlante delle normali deve essere RGBA", im.size, "è", nim.mode, nim.size)
            else:
                na = np.asarray(nim)
                if ((arr[..., 3] > 0) & (na[..., 3] == 0)).any():
                    R.err(cid, ": l'atlante delle normali è trasparente dove lo sprite non lo è")
                zz = na[..., 2][arr[..., 3] > 0]
                if len(zz) and zz.min() < 120:
                    R.warn(cid, ": normali rivolte all'indietro (blu < 120) in", int((zz < 120).sum()), "pixel")
    ncol = len({tuple(c) for c in opaque.tolist()})
    if ncol > MAX_COLORS:
        R.err(cid, f": {ncol} colori, il massimo è {MAX_COLORS}")
    if len(opaque) and not (opaque == np.array(OUTLINE)).all(-1).any():
        R.err(cid, ": manca il colore del contorno comune #140e1e")
    anims = data.get("animations", {})
    for name in REQUIRED[cid]:
        if name not in anims:
            R.err(cid, ": manca l'animazione", name)
    for name in anims:
        if name not in REQUIRED[cid]:
            R.warn(cid, ": animazione in più", name)
    used = np.zeros((H, W), np.int32)
    rects = {}
    dbg = {}
    dp = os.path.join(d, cid + ".debug.json")
    if os.path.exists(dp):
        dbg = json.load(open(dp, encoding="utf-8"))
    for name, an in anims.items():
        fr = an.get("frames", [])
        if not fr:
            R.err(cid, name, ": nessun fotogramma")
            continue
        if an.get("loop") is not (name in LOOPS):
            R.err(cid, name, ": loop deve essere", name in LOOPS)
        ticks = []
        for i, f in enumerate(fr):
            where = f"{cid} {name}[{i}]"
            for key in ("rect", "anchor", "ticks", "hurt", "hit", "events", "tags"):
                if key not in f:
                    R.err(where, ": manca", key)
            rect = f.get("rect", [0, 0, 0, 0])
            if not (isinstance(rect, list) and len(rect) == 4 and all(isinstance(v, int) for v in rect)):
                R.err(where, ": rect non valido", rect)
                continue
            x, y, w, h = rect
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
                R.err(where, ": rect fuori dall'atlante", rect, (W, H))
            else:
                key = tuple(rect)
                if key not in rects:
                    rects[key] = where
                    used[y:y + h, x:x + w] += 1
                if not (arr[y:y + h, x:x + w, 3] > 0).any():
                    R.err(where, ": rect vuoto")
            a = f.get("anchor", [0, 0])
            if not (isinstance(a, list) and len(a) == 2 and all(isinstance(v, int) for v in a)):
                R.err(where, ": anchor non valido", a)
            elif not (-80 * S <= a[0] <= w + 80 * S and -40 * S <= a[1] <= h + 80 * S):
                R.err(where, ": anchor implausibile", a, "rect", rect)
            t = f.get("ticks")
            if not isinstance(t, int) or t < 1:
                R.err(where, ": ticks non valido", t)
                t = 0
            ticks.append(t)
            for b in f.get("hurt", []):
                if not is_box(b):
                    R.err(where, ": hurtbox non valida", b)
                elif not (-90 * S <= b[0] <= 90 * S and -150 * S <= b[1] <= 20 * S and b[2] <= 160 * S and b[3] <= 160 * S):
                    R.err(where, ": hurtbox implausibile", b)
            if not f.get("hurt"):
                R.warn(where, ": nessuna hurtbox")
            for b in f.get("hit", []):
                if not is_box(b):
                    R.err(where, ": hitbox non valida", b)
                elif not (-30 * S <= b[0] <= 110 * S and -150 * S <= b[1] <= 10 * S and b[2] <= 90 * S and b[3] <= 90 * S):
                    R.err(where, ": hitbox implausibile", b)
            tags = set(f.get("tags", []))
            if not tags <= TAGS:
                R.err(where, ": tag sconosciuti", tags - TAGS)
            if ("active" in tags) != bool(f.get("hit")):
                R.err(where, ": 'active' e hit non vuoto devono andare insieme")
            pts = f.get("points", {})
            if not isinstance(pts, dict):
                R.err(where, ": points deve essere un oggetto")
                pts = {}
            for pn, pv in pts.items():
                if pn not in POINTS:
                    R.warn(where, ": punto sconosciuto", pn)
                if not (isinstance(pv, list) and len(pv) == 2 and all(isinstance(v, int) for v in pv)):
                    R.err(where, ": punto non valido", pn, pv)
                elif not (-120 * S <= pv[0] <= 120 * S and -170 * S <= pv[1] <= 60 * S):
                    R.err(where, ": punto implausibile", pn, pv)
            for e in f.get("events", []):
                if not EV_RE.match(e):
                    R.err(where, ": evento non valido", e)
                elif e.startswith("sfx:") and e[4:] not in SFX:
                    R.err(where, ": suono non previsto dalla specifica", e)
                elif e.startswith("fx:") and e[3:].split("@")[0] not in FX:
                    R.err(where, ": effetto non previsto dalla specifica", e)
                elif e.startswith("fx:") and "@" in e and e.split("@")[1] not in pts:
                    R.err(where, ": il punto dell'effetto non c'è nel fotogramma", e)
            if "dx" in f and not isinstance(f["dx"], int):
                R.err(where, ": dx deve essere intero")
            if "dy" in f and not isinstance(f["dy"], int):
                R.err(where, ": dy deve essere intero")
            if cid == "gig" and name in PAIRS:
                v = f.get("victim")
                if not isinstance(v, dict):
                    R.err(where, ": manca victim")
                else:
                    if not isinstance(v.get("behind"), bool):
                        R.err(where, ": victim.behind deve essere true/false")
                    for en in ENEMIES:
                        e = v.get(en)
                        if not (isinstance(e, list) and len(e) == 4 and isinstance(e[0], int) and isinstance(e[1], int)
                                and isinstance(e[2], str) and isinstance(e[3], int)):
                            R.err(where, ": voce victim non valida per", en, e)
                            continue
                        if abs(e[0]) > 80 or abs(e[1]) > 12:
                            R.err(where, ": offset vittima implausibile", en, e)
                        if e[2] not in ("grabbed", "kneed", "thrown"):
                            R.err(where, ": animazione vittima non prevista", e[2])
                        od = others.get(en)
                        if od is not None:
                            van = od.get("animations", {}).get(e[2])
                            if van is None:
                                R.err(where, ":", en, "non ha l'animazione", e[2])
                            elif not 0 <= e[3] < len(van["frames"]):
                                R.err(where, ": fotogramma vittima fuori intervallo", en, e)
            # deriva dell'ancora (sidecar di debug): origine del ritaglio + ancora = costante
        if name in dbg.get("inplace", []) and name not in ("walk", "run"):
            # animazioni sul posto: un piede che resta a terra fra due fotogrammi non deve muoversi rispetto
            # all'ancora (caviglia entro 7 px dalla linea dei piedi = a terra; tolleranza di arrotondamento 1 px)
            feet = dbg.get("feet", {}).get(name, [])
            worst = 0.0
            for a, b in zip(feet, feet[1:]):
                for s in "lr":
                    if -a[s][1] < 7 and -b[s][1] < 7:
                        worst = max(worst, abs(a[s][0] - b[s][0]), abs(a[s][1] - b[s][1]))
            if worst > 1.0:
                if name in FEET_FIXED:
                    R.err(cid, name, f": un piede a terra scivola di {worst:.1f} px rispetto all'ancora")
                else:
                    R.warn(cid, name, f": lavoro di piedi (passo o perno) fino a {worst:.1f} px rispetto all'ancora")
            pts = {(o[0] + f["anchor"][0], o[1] + f["anchor"][1]) for o, f in zip(dbg["origins"][name], fr)}
            if len(pts) != 1:
                R.warn(cid, name, ": l'ancora si sposta nel fotogramma insieme alla radice del rig "
                                  "(i piedi a terra restano fermi rispetto all'ancora)", sorted(pts))
        # tempi del §5
        tm = TIMING.get((cid, name))
        if tm:
            act = [i for i, f in enumerate(fr) if "active" in f.get("tags", [])]
            su_t, ac_t, re_t = tm
            if ac_t:
                if not act:
                    R.err(cid, name, ": nessun fotogramma attivo")
                    continue
                if act != list(range(act[0], act[-1] + 1)):
                    R.err(cid, name, ": fotogrammi attivi non contigui")
                su = sum(ticks[:act[0]])
                ac = sum(ticks[act[0]:act[-1] + 1])
                rc = sum(ticks[act[-1] + 1:])
            else:
                # proiezione: niente hitbox; il rilascio è il fotogramma che inizia al tick dell'avvio (8)
                starts = [sum(ticks[:i]) for i in range(len(ticks))]
                if su_t not in starts:
                    R.err(cid, name, f": nessun fotogramma inizia al tick {su_t} (rilascio della proiezione)")
                    continue
                rel = starts.index(su_t)
                su, ac, rc = sum(ticks[:rel]), 0, sum(ticks[rel:])
            got = (su, ac, rc if re_t is not None else None)
            exp = (su_t, ac_t, re_t)
            if got != exp:
                R.err(cid, name, ": tempi", got, "attesi", exp)
            if name in ("jab1", "jab2", "hook"):
                if "cancel" not in fr[-1].get("tags", []):
                    R.err(cid, name, ": l'ultimo fotogramma del recupero deve avere 'cancel'")
            if name == "haymaker":
                start = 0
                ok = False
                for t, f in zip(ticks, fr):
                    if start == 20 and "glint" in f.get("events", []):
                        ok = True
                    start += t
                if not ok:
                    R.err(cid, name, ": serve l'evento glint su un fotogramma che inizia al tick 20")
            if name == "punch":
                for f in fr[:act[0]]:
                    if "armor" not in f.get("tags", []):
                        R.err(cid, name, ": tutti i fotogrammi d'avvio devono avere 'armor'")
                        break
        if name in ("knock_down",) and "hold" not in fr[-1].get("tags", []):
            R.err(cid, name, ": l'ultimo fotogramma deve avere 'hold'")
    if (used > 1).any():
        R.err(cid, ": rect sovrapposti nell'atlante")
    return data


def check_portraits(R, ids):
    pdir = os.path.join(REPO, "game", "assets", "ui", "portraits")
    for cid in ids:
        if cid in NO_PORTRAIT:
            continue
        p = os.path.join(pdir, cid + ".png")
        if not os.path.exists(p):
            R.warn("ritratto mancante", p)
            continue
        im = Image.open(p)
        if im.size != (32, 32) or im.mode != "RGBA":
            R.err("ritratto", cid, ": deve essere 32x32 RGBA, è", im.size, im.mode)


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = pos[0] if pos else os.path.join(REPO, "game", "assets", "sprites")
    R = Report()
    data = {}
    for cid in REQUIRED:
        d = os.path.join(root, cid)
        if os.path.isdir(d):
            data[cid] = json.load(open(os.path.join(d, cid + ".json"), encoding="utf-8")) \
                if os.path.exists(os.path.join(d, cid + ".json")) else None
    for cid in REQUIRED:
        d = os.path.join(root, cid)
        if not os.path.isdir(d):
            R.warn("manca la cartella", d)
            continue
        others = {k: v for k, v in data.items() if k != cid and v}
        check_char(cid, d, R, others)
    if "--portraits" in sys.argv:
        check_portraits(R, [c for c in REQUIRED if os.path.isdir(os.path.join(root, c))])
    for w in R.warnings:
        print("AVVISO:", w)
    for e in R.errors:
        print("ERRORE:", e)
    print(f"validazione: {len(R.errors)} errori, {len(R.warnings)} avvisi ({root})")
    sys.exit(1 if R.errors else 0)


if __name__ == "__main__":
    main()
