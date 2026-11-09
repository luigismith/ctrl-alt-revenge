# I droni del Recupero Crediti di SIDERA nei tratti platform: il Segugio (il mastino da recupero) e la Vedetta
# (il quadrirotore col faro), con la livrea «smalto e sangue di bue» scelta da Luigi l'8 novembre 2026.
#
# Il modello è 3D, con la pipeline dei prop (tools/env) e il render di tools/blender/env_gbuffer.py, a 60 px/m
# come i personaggi. Le pose vengono dalle fasi di game/src/platform/drones.gd. Escono lo sprite sheet, la normal
# map e il JSON nel formato dei personaggi (format 1), in game/assets/sprites/<id>/; le luci sono dipinte nei
# fotogrammi, gli aloni li aggiunge il gioco ai punti del JSON.
#
# Uso: python tools/sprites/droni.py [--norender]
#   --norender  rifà solo i colori e il foglio dal render già fatto (tools/sprites/out/droni/raw)
import json
import math
import os
import sys

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "env"))
import envlib as E  # noqa: E402
import paint as P  # noqa: E402
import materials as MT  # noqa: E402
from props import rot, cyl_mesh, box_mesh, place  # noqa: E402

OUTD = os.path.join(REPO, "tools", "sprites", "out", "droni")
RAW = os.path.join(OUTD, "raw")
DEST = os.path.join(REPO, "game", "assets", "sprites")
os.makedirs(RAW, exist_ok=True)
C = E.CLS

# ------------------------------------------------------------------ rampe e materiali
MT.RAMPS.update({
    "d_white": ["#1e2230", "#363d50", "#586179", "#828ca3", "#aeb7c8", "#d6dde8", "#f4f7fa"],
    "d_red": ["#2a0710", "#55101c", "#8e1a28", "#cc2a34", "#f25048", "#ff9a86"],
    "d_orange": ["#331206", "#64240c", "#a04014", "#d8621c", "#f88a34", "#ffbb78"],
    "d_dark": ["#0a0a10", "#14141c", "#1e1e2a", "#2a2a3a", "#3a3a4e"],
    "d_graph": ["#0c0c12", "#181a22", "#262934", "#363a48", "#4c5163", "#676d82"],
    "d_bone": ["#2c2826", "#56504b", "#8a837b", "#b8b0a5", "#d8d1c5", "#f1ece2"],
    "d_oxb": ["#180307", "#350911", "#57101d", "#7a1728", "#9a2434", "#b83c46"],
})
W_ = MT._m(120, "d_white", "d_white", bands=(0.08, 0.4, 0.75), spill=0.0, dither=False, tint=())
RED = MT._m(122, "d_red", "d_red", bands=(0.2, 0.6), spill=0.0, dither=False, tint=())
ORA = MT._m(123, "d_orange", "d_orange", bands=(0.08, 0.4, 0.75), spill=0.0, dither=False, tint=())
DARK = MT._m(125, "d_dark", "d_dark", bands=(0.3, 0.7), spill=0.0, dither=False, tint=())
STEEL = MT._m(126, "d_steel", "metal", bands=(0.1, 0.45, 0.8), spill=0.0, dither=False, tint=())
GRAPH = MT._m(127, "d_graph", "d_graph", bands=(0.08, 0.4, 0.75), spill=0.0, dither=False, tint=())
BONE = MT._m(129, "d_bone", "d_bone", bands=(0.08, 0.4, 0.75), spill=0.0, dither=False, tint=())
OXB = MT._m(130, "d_oxb", "d_oxb", bands=(0.2, 0.6), spill=0.0, dither=False, tint=())
COL = {W_: "#c8cfdc", RED: "#d8303a", ORA: "#e8702a", DARK: "#26262f", STEEL: "#5a6a80", GRAPH: "#363a48",
       BONE: "#d8d1c5", OXB: "#7a1728"}

OBJS = []      # oggetti del job
ROLE = {}      # oid -> (fotogramma, ruolo)
AX_X = rot(0, 90, 0)     # asse del cilindro lungo +X
AX_Y = rot(-90, 0, 0)    # lungo +Y


def add(fr, verts, faces, mat, R=None, t=(0, 0, 0), role="", cls="METAL", smooth=False):
    R = np.eye(3) if R is None else R
    OBJS.append(dict(type="mesh", verts=place(verts, R, t), faces=[list(f) for f in faces], cls=C[cls], mat=mat,
                     alb=E.f3(COL[mat]), smooth=smooth))
    ROLE[len(OBJS)] = (fr, role)


def box(fr, size, center, mat, R=None, role=""):
    v, f = box_mesh(*size)
    add(fr, [(x, y, z - size[2] / 2) for x, y, z in v], f, mat, R, center, role)


def cyl(fr, r0, r1, h, base, mat, R=None, n=14, role="", cls="METAL"):
    v, f = cyl_mesh(r0, r1, h, n=n)
    add(fr, v, f, mat, R, base, role, cls)


def ell(fr, rx, ry, rz, center, mat, R=None, n=16, rings=10, role=""):
    verts, faces = [], []
    for j in range(rings + 1):
        ph = math.pi * j / rings
        for k in range(n):
            a = 2 * math.pi * k / n
            verts.append((rx * math.sin(ph) * math.cos(a), ry * math.sin(ph) * math.sin(a), -rz * math.cos(ph)))
    for j in range(rings):
        for k in range(n):
            a, b = j * n + k, j * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    add(fr, verts, faces, mat, R, center, role, smooth=True)


def tube(fr, pts, r, mat, role="", n=6):
    """Tubo come catena di cilindri (zampe, bracci, antenne)."""
    for p, q in zip(pts[:-1], pts[1:]):
        p, q = np.array(p, float), np.array(q, float)
        d = q - p
        L = float(np.linalg.norm(d))
        z = np.array([0, 0, 1.0])
        ax = np.cross(z, d / L)
        s = float(np.linalg.norm(ax))
        if s < 1e-6:
            R = np.eye(3) if d[2] > 0 else rot(180, 0, 0)
        else:
            ax /= s
            ang = math.atan2(s, float(np.dot(z, d / L)))
            K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            R = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
        cyl(fr, r, r, L, p, mat, R, n=n, role=role, cls="PIPE")


class Gruppo:
    """Parti che si muovono insieme: ruotano di `ang` gradi attorno all'asse Y passante per `pivot` (con ang
    positivo una punta in +X va giù) e si spostano di `off`. sub() fa un gruppo figlio (la testa, la mascella)."""
    def __init__(self, fr, pivot, ang=0.0, off=(0, 0, 0), parent=None):
        self.fr, self.p, self.Rl, self.off, self.parent = fr, np.array(pivot, float), rot(0, ang, 0), np.array(off, float), parent
        self.R = (parent.R if parent else np.eye(3)) @ self.Rl

    def c(self, pt):
        loc = self.p + self.Rl @ (np.array(pt, float) - self.p) + self.off
        return self.parent.c(loc) if self.parent else tuple(loc)

    def sub(self, pivot, ang):
        return Gruppo(self.fr, pivot, ang, parent=self)

    def _R(self, R):
        return self.R @ (np.eye(3) if R is None else R)

    def box(self, size, ctr, mat, R=None, role=""):
        box(self.fr, size, self.c(ctr), mat, self._R(R), role)

    def cyl(self, r0, r1, h, base, mat, R=None, n=12, role=""):
        cyl(self.fr, r0, r1, h, self.c(base), mat, self._R(R), n=n, role=role)

    def ell(self, rx, ry, rz, ctr, mat, R=None, role=""):
        ell(self.fr, rx, ry, rz, self.c(ctr), mat, self._R(R), role=role)

    def tube(self, pts, r, mat, n=6):
        tube(self.fr, [self.c(p) for p in pts], r, mat, n=n)


def ik(H, T, a, b):
    """Due ossa nel piano XZ, ginocchio in avanti: dove sta il ginocchio e dove arriva davvero la punta."""
    dx, dz = T[0] - H[0], T[1] - H[1]
    d = min(max(math.hypot(dx, dz), abs(a - b) + 1e-3), a + b - 1e-3)
    th = math.atan2(dz, dx)
    al = math.acos((a * a + d * d - b * b) / (2 * a * d))
    K = (H[0] + a * math.cos(th + al), H[1] + a * math.sin(th + al))
    return K, (H[0] + d * math.cos(th), H[1] + d * math.sin(th))


# ------------------------------------------------------------------ SEGUGIO, livrea smalto e sangue di bue
FRONT = (0.1217, 0.1105)                 # ossa della zampa davanti (anca-ginocchio, ginocchio-piede)
HIND = (0.139, 0.128, (0.02, -0.07))     # dietro: anca-ginocchio, ginocchio-garretto, garretto->piede


def segugio(fr, o, testa=0.0, bocca=0.0, alza=0.0, becc=0.0, zampe=None, coda=None, rotto=False):
    """zampe: {'dv','dl','pv','pl'} -> (dx, dz) del piede rispetto alla posa ferma (d/p = davanti/dietro,
    v/l = lato vicino a chi guarda / lontano)."""
    zampe = zampe or {}
    ox, oy, oz = o
    g = Gruppo(fr, (ox + 0.05, oy, oz + 0.3), becc, (0, 0, alza))
    g.box((0.5, 0.28, 0.17), (ox - 0.04, oy, oz + 0.34), BONE)                       # schiena
    g.box((0.24, 0.32, 0.27), (ox + 0.2, oy, oz + 0.33), BONE, rot(0, 8, 0))         # petto largo
    g.box((0.5, 0.29, 0.055), (ox - 0.04, oy, oz + 0.3), DARK)                       # fascia scura
    g.box((0.3, 0.004, 0.04), (ox - 0.06, oy - 0.146, oz + 0.3), DARK, role="ticker")
    for dx in (0.15, 0.21):                                                          # strisce di livrea
        g.box((0.035, 0.006, 0.26), (ox + dx, oy - 0.163, oz + 0.33), OXB, rot(0, -14, 0))
    g.box((0.4, 0.006, 0.022), (ox - 0.06, oy - 0.142, oz + 0.38), OXB)
    g.box((0.4, 0.285, 0.012), (ox - 0.06, oy, oz + 0.427), OXB)
    g.box((0.16, 0.2, 0.07), (ox - 0.02, oy, oz + 0.45), DARK)                       # gobba col lampeggiante
    g.cyl(0.04, 0.035, 0.05, (ox - 0.02, oy, oz + 0.485), RED, role="luce")
    for s in (-1, 1):                                                                # ventola sull'anca
        g.cyl(0.06, 0.06, 0.02, (ox - 0.22, oy + s * 0.15, oz + 0.33), OXB, AX_Y)
        g.cyl(0.045, 0.045, 0.028, (ox - 0.22, oy + s * 0.154, oz + 0.33), DARK, AX_Y, role="vapore")
    for s, lato in ((-1, "v"), (1, "l")):
        y = oy + s * 0.11
        # davanti: anca, coscia, ginocchio in avanti, piede
        H = g.c((ox + 0.22, y, oz + 0.26))
        dx, dz = zampe.get("d" + lato, (0, 0))
        K, Pd = ik((H[0], H[2]), (ox + 0.23 + dx, oz + 0.03 + dz), *FRONT)
        tube(fr, [H, (K[0], y, K[1]), (Pd[0], y, Pd[1])], 0.032, GRAPH)
        box(fr, (0.07, 0.05, 0.03), (Pd[0] + 0.015, y, Pd[1] - 0.015), DARK)
        g.ell(0.07, 0.05, 0.09, (ox + 0.22, y, oz + 0.25), BONE)
        # dietro: anca, ginocchio in avanti, garretto all'indietro, piede
        H = g.c((ox - 0.24, y, oz + 0.3))
        dx, dz = zampe.get("p" + lato, (0, 0))
        pd = (ox - 0.25 + dx, oz + 0.03 + dz)
        K, Hk = ik((H[0], H[2]), (pd[0] - HIND[2][0], pd[1] - HIND[2][1]), HIND[0], HIND[1])
        Pp = (Hk[0] + HIND[2][0], Hk[1] + HIND[2][1])
        tube(fr, [H, (K[0], y, K[1]), (Hk[0], y, Hk[1]), (Pp[0], y, Pp[1])], 0.032, GRAPH)
        box(fr, (0.07, 0.05, 0.03), (Pp[0] + 0.015, y, Pp[1] - 0.015), DARK)
        g.ell(0.09, 0.05, 0.1, (ox - 0.24, y, oz + 0.29), BONE)
    cp = (ox + coda[0], oz + coda[1]) if coda else (ox - 0.38, oz + 0.47)            # coda-antenna (relativa)
    g.tube([(ox - 0.29, oy, oz + 0.38), (cp[0], oy, cp[1])], 0.012, STEEL, n=4)
    g.cyl(0.022, 0.022, 0.035, (cp[0] - 0.005, oy, cp[1]), RED, n=8)
    h = g.sub((ox + 0.27, oy, oz + 0.4), testa)
    h.box((0.06, 0.27, 0.07), (ox + 0.33, oy, oz + 0.43), DARK, role="collare")
    h.box((0.18, 0.22, 0.17), (ox + 0.43, oy, oz + 0.47), BONE)
    for s in (-1, 1):
        h.box((0.18, 0.04, 0.012), (ox + 0.43, oy + s * 0.05, oz + 0.556), OXB)
    h.box((0.13, 0.17, 0.075), (ox + 0.55, oy, oz + 0.452), DARK, role="muso")
    for k in range(2):
        h.box((0.005, 0.15, 0.012), (ox + 0.616, oy, oz + 0.435 + k * 0.03), STEEL)
    h.cyl(0.03, 0.03, 0.02, (ox + 0.6, oy, oz + 0.47), RED, AX_X, n=10, role="occhi")
    h.box((0.1, 0.13, 0.012), (ox + 0.54, oy, oz + 0.412), RED, role="bocca")
    j = h.sub((ox + 0.49, oy, oz + 0.415), bocca)
    j.box((0.12, 0.16, 0.035), (ox + 0.55, oy, oz + 0.397), DARK, role="muso")
    j.box((0.005, 0.13, 0.01), (ox + 0.611, oy, oz + 0.4), STEEL)
    for s in (-1, 1):
        if rotto and s == -1:
            continue                                                                 # un orecchio strappato
        h.box((0.1, 0.02, 0.06), (ox + 0.38, oy + s * 0.09, oz + 0.58), BONE, rot(0, -25, 0))
        h.box((0.03, 0.022, 0.06), (ox + 0.33, oy + s * 0.09, oz + 0.6), DARK, rot(0, -25, 0))
    if rotto:                                                                        # il moncone dell'orecchio
        h.box((0.03, 0.022, 0.025), (ox + 0.36, oy - 0.09, oz + 0.565), DARK, rot(0, 20, 0))


# Le pose, dalle fasi di drones.gd: (animazione, [kwargs per fotogramma], tick, luci, loop)
A_ = 0.05
SEG_POSE = [
    ("idle", [dict()], 30, "ronda", True),
    ("patrol", [dict(zampe=dict(dv=(A_, 0), pl=(A_, 0), dl=(-A_, 0), pv=(-A_, 0))),
                dict(alza=0.008, zampe=dict(dl=(0, 0.045), pv=(0, 0.045))),
                dict(zampe=dict(dv=(-A_, 0), pl=(-A_, 0), dl=(A_, 0), pv=(A_, 0))),
                dict(alza=0.008, zampe=dict(dv=(0, 0.045), pl=(0, 0.045)))], 8, "ronda", True),
    ("sniff", [dict(testa=55, becc=4, zampe=dict(dv=(0.03, 0), dl=(0.03, 0))),
               dict(testa=49, bocca=8, becc=4, zampe=dict(dv=(0.03, 0), dl=(0.03, 0)))], 10, "ronda", True),
    ("bark", [dict(testa=-24, bocca=30, becc=-3, zampe=dict(dv=(0.05, 0), dl=(0.04, 0), pv=(-0.03, 0), pl=(-0.03, 0))),
              dict(testa=-18, bocca=12, becc=-3, zampe=dict(dv=(0.05, 0), dl=(0.04, 0), pv=(-0.03, 0), pl=(-0.03, 0)))],
     6, "avviso", True),
    ("dash", [dict(testa=6, bocca=24, alza=0.03, zampe=dict(dv=(0.13, 0.05), dl=(0.1, 0.04), pv=(-0.13, 0.04), pl=(-0.1, 0.05)),
                   coda=(-0.42, 0.42)),
              dict(testa=2, bocca=14, alza=0.01, becc=-4, zampe=dict(dv=(-0.05, 0.03), dl=(-0.02, 0.02), pv=(0.12, 0.03), pl=(0.09, 0.02)),
                   coda=(-0.41, 0.44)),
              dict(testa=8, bocca=20, becc=4, zampe=dict(dv=(0.05, 0), dl=(0.08, 0.02), pv=(-0.04, 0.05), pl=(-0.07, 0.03)),
                   coda=(-0.42, 0.43))], 3, "avviso", True),
    ("pant", [dict(testa=18, bocca=26, alza=-0.012, zampe=dict(dv=(0.03, 0), dl=(0.02, 0), pv=(-0.03, 0), pl=(-0.02, 0)),
                   coda=(-0.4, 0.4)),
              dict(testa=22, bocca=10, zampe=dict(dv=(0.03, 0), dl=(0.02, 0), pv=(-0.03, 0), pl=(-0.02, 0)),
                   coda=(-0.4, 0.41))], 12, "ronda", True),
    ("broken", [dict(testa=38, bocca=18, alza=-0.16, becc=5, rotto=True, coda=(-0.43, 0.3),
                     zampe=dict(dv=(0.15, 0), dl=(0.11, 0), pv=(-0.13, 0), pl=(-0.09, 0)))], 30, "spento", False),
]


# ------------------------------------------------------------------ VEDETTA, la stessa livrea
def vedetta(fr, o, pale=0.0, livrea="smalto", rotto=False):
    ox, oy, oz = o
    sm = livrea == "smalto"
    corpo, fascia, anello = (BONE, OXB, BONE) if sm else (ORA, RED, ORA)
    g = Gruppo(fr, (ox, oy, oz + 0.3), 24 if rotto else 0, (0, 0, -0.17) if rotto else (0, 0, 0))
    g.box((0.36, 0.26, 0.13), (ox, oy, oz + 0.34), corpo)                          # scocca
    g.box((0.3, 0.2, 0.05), (ox - 0.01, oy, oz + 0.425), corpo)                    # dorso
    g.box((0.37, 0.265, 0.025), (ox, oy, oz + 0.3), fascia)                        # fascia
    if sm:
        for dx in (0.06, 0.11):                                                    # strisce come il Segugio
            g.box((0.03, 0.006, 0.13), (ox + dx, oy - 0.133, oz + 0.35), OXB, rot(0, -14, 0))
        g.box((0.3, 0.06, 0.008), (ox - 0.01, oy, oz + 0.452), OXB)
    for sx in (-1, 1):
        for sy in (-1, 1):
            if rotto and sx == 1 and sy == -1:
                g.tube([(ox + 0.12, oy - 0.09, oz + 0.38), (ox + 0.2, oy - 0.15, oz + 0.33)], 0.018, DARK)
                continue                                                           # braccio spezzato
            g.tube([(ox + sx * 0.12, oy + sy * 0.09, oz + 0.38), (ox + sx * 0.3, oy + sy * 0.24, oz + 0.42)],
                   0.018, DARK)
            c = (ox + sx * 0.3, oy + sy * 0.24, oz + 0.41)
            g.cyl(0.125, 0.125, 0.035, c, anello, n=18)                            # paraelica
            g.cyl(0.108, 0.108, 0.01, (c[0], c[1], c[2] + 0.012), DARK, n=18)      # fondo del condotto
            if not rotto:
                a = pale + (sx + 1) * 20 + (sy + 1) * 35
                g.box((0.2, 0.024, 0.006), (c[0], c[1], c[2] + 0.036), STEEL, rot(0, 0, a))   # pale
            g.cyl(0.02, 0.02, 0.03, (c[0], c[1], c[2] + 0.02), STEEL, n=8)          # mozzo
    g.cyl(0.04, 0.035, 0.06, (ox - 0.05, oy, oz + 0.45), RED, role="luce")          # lampeggiante
    g.cyl(0.065, 0.06, 0.07, (ox + 0.17, oy, oz + 0.27), DARK, AX_X, n=14)          # faro
    g.cyl(0.05, 0.05, 0.012, (ox + 0.24, oy, oz + 0.27), DARK, AX_X, n=14, role="faro")
    g.box((0.22, 0.17, 0.08), (ox - 0.02, oy, oz + 0.23), GRAPH if sm else DARK)    # stampante dei sigilli
    if not rotto:
        g.box((0.02, 0.13, 0.08), (ox + 0.04, oy, oz + 0.15), W_, rot(0, 15, 0), role="sigillo")
        g.box((0.03, 0.135, 0.02), (ox + 0.04, oy, oz + 0.15), RED, rot(0, 15, 0))


VED_POSE = [
    ("patrol", [dict(pale=0), dict(pale=45)], 2, "ronda", True),
    ("spot", [dict(pale=0), dict(pale=45)], 2, "avviso", True),
    ("broken", [dict(rotto=True)], 30, "spento", False),
]

# ------------------------------------------------------------------ la scena: un fotogramma per posa geometrica
FR = []   # (nome, sprite, animazione, indice, funzione, kwargs, cx)
for an, frs, _, _, _ in SEG_POSE:
    for i, kw in enumerate(frs):
        FR.append((f"segugio_{an}_{i}", "segugio", an, i, segugio, kw, 0.08))
for an, frs, _, _, _ in VED_POSE:
    if an == "spot":
        continue                                     # stessa geometria della ronda: cambiano solo le luci
    for i, kw in enumerate(frs):
        FR.append((f"vedetta_{an}_{i}", "vedetta", an, i, vedetta, kw, 0.0))
FR.append(("vedetta_vecchia", None, None, 0, vedetta, dict(livrea="arancio"), 0.0))

STEP = 1.7
for i, (nm, _, _, _, fn, kw, _) in enumerate(FR):
    fn(nm, (i * STEP, 0.0, 0.0), **kw)

x0, x1, y0, y1 = -60, int(len(FR) * STEP * E.KX) + 40, -60, 20
view = dict(yaw=E.YAW, pitch=E.PITCH, ppm=E.PPM, ss=E.SS, x0=x0, x1=x1, y0=y0, y1=y1, oy=0.0)
job = dict(tag="droni", out_dir=RAW, view=view, objects=OBJS, kit_dirs={}, p0=[-5.0, -5.0, -5.0], span=40.0)
if "--norender" not in sys.argv:
    E.run_blender(os.path.join(REPO, "tools", "blender", "env_gbuffer.py"), job, os.path.join(RAW, "droni_job.json"),
                  timeout=900, log=os.path.join(RAW, "droni.log"))
with open(os.path.join(RAW, "droni_paint.json"), "w") as fh:
    json.dump(dict(ops=[]), fh)

CFG = dict(amb=0.75, key=0.85, spill=0.0, spill_sigma=(2.0, 6.0), wet=0, dither=0.0, inner=True, depth_thr=0.03,
           outline=True)
cv = P.load("droni", RAW)
lit, _S = P.shade(cv, CFG)
q = P.quantize(cv, lit, CFG)
res, alpha = P.outlines(cv, q, CFG)
IMG = P.to_rgba(res, alpha)
assert IMG.shape[:2] == cv.A.shape, (IMG.shape, cv.A.shape)
OID = np.where(cv.A, cv.oid, 0)
MAT = np.where(cv.A, cv.mat, 0)
ZW = cv.pos[..., 2]
NRM = cv.n
AA = IMG[..., 3] > 0


def hx(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], np.uint8)


EDGE = hx("#7a1226")       # bordo esterno rosso scuro: la regola 5 (chi fa male) e il rosso di SIDERA
DUST, DUST_D = hx("#a24c32"), hx("#6e2c1e")
RUOLI = ("luce", "faro", "occhi", "ticker", "collare", "bocca", "muso", "vapore", "sigillo")


def ritaglia(nome):
    m = np.isin(OID, [k for k, v in ROLE.items() if v[0] == nome])
    near = np.zeros_like(m)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        near |= np.roll(np.roll(m, dy, 0), dx, 1)
    m = m | (AA & (OID == 0) & near)
    ys, xs = np.nonzero(m)
    y0_, y1_, x0_, x1_ = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sl = (slice(y0_, y1_), slice(x0_, x1_))
    mm = m[sl]
    t = np.zeros((y1_ - y0_, x1_ - x0_, 4), np.uint8)
    t[mm] = IMG[sl][mm]
    a = t[..., 3] > 0
    pad = np.pad(a, 1)
    bordo = a & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    t[bordo, :3] = EDGE
    ruoli = {}
    for r in RUOLI:
        ids = [k for k, v in ROLE.items() if v[0] == nome and v[1] == r]
        rm = np.isin(OID[sl], ids) & mm & ~bordo
        if rm.any():
            ruoli[r] = rm
    n = np.zeros(t.shape[:2] + (3,), np.float32)
    n[..., 2] = 1.0
    geo = cv.A[sl] & mm
    n[geo] = NRM[sl][geo]
    return dict(rgba=t, ruoli=ruoli, mat=np.where(mm, MAT[sl], 0), z=np.where(mm, ZW[sl], 9.0), n=n,
                bordo=bordo, box=(x0_, y0_, x1_, y1_))


def sporca(f, seed, forza):
    """La polvere rossa del minerale sul guscio: più in basso, a chiazze; sul grafite solo vicino a terra."""
    t, z, mat = f["rgba"], f["z"], f["mat"]
    h, w = z.shape
    rng = P.vnoise((h, w), 3, seed) * 0.65 + P.hash2(*np.mgrid[0:h, 0:w][::-1], seed) * 0.35
    q_ = forza * np.clip((0.52 - z) / 0.42, 0.12, 1.0)
    osso = (mat == BONE) & ~f["bordo"]
    gamba = (mat == GRAPH) & (z < 0.12) & ~f["bordo"]
    m1 = osso & (rng < q_ * 0.62)
    m2 = osso & (rng < q_ * 0.2)
    m3 = gamba & (rng < forza * 0.55)
    for m, col, k in ((m1, DUST, 0.42), (m2, DUST_D, 0.5), (m3, DUST, 0.35)):
        t[m, :3] = (t[m, :3] * (1 - k) + col * k).astype(np.uint8)


def dipingi(t, m, col):
    if m is not None:
        t[m, :3] = hx(col)


def luci(f, modo, tipo):
    t, r = f["rgba"].copy(), f["ruoli"]
    if tipo == "segugio":
        if modo == "spento":
            dipingi(t, r.get("occhi"), "#2a0710")
            dipingi(t, r.get("luce"), "#350911")
            cm = r.get("collare")
            if cm is not None:                       # lo schermo del collare, crepato
                ys, xs = np.nonzero(cm)
                for yy, xx in zip(ys, xs):
                    if (xx - xs.min()) == (yy - ys.min()) // 2:
                        t[yy, xx, :3] = hx("#8a837b")
            return t
        dipingi(t, r.get("occhi"), "#ff6a5a" if modo == "avviso" else "#cc2a34")
        dipingi(t, r.get("luce"), "#ff9a86" if modo == "avviso" else "#55101c")
        if modo == "avviso":
            cm = r.get("collare")
            if cm is not None:                       # «DEBITO RILEVATO»: il collare passa al rosso, a led
                ys, xs = np.nonzero(cm)
                for yy, xx in zip(ys, xs):
                    t[yy, xx, :3] = hx("#ff5a44") if (xx + yy) % 2 == 0 else hx("#5a0f1a")
            dipingi(t, r.get("bocca"), "#ff7a64")
            tm = r.get("ticker")
            if tm is not None:
                ys, xs = np.nonzero(tm)
                for yy, xx in zip(ys, xs):
                    if (xx + 2 * yy) % 3 != 0:
                        t[yy, xx, :3] = hx("#f25048")
        return t
    # Vedetta
    if modo == "spento":
        dipingi(t, r.get("luce"), "#350911")
        dipingi(t, r.get("faro"), "#1e1e2a")
        return t
    dipingi(t, r.get("faro"), "#fff4dc" if modo == "ronda" else "#ff6a5a")
    dipingi(t, r.get("luce"), "#cc2a34" if modo == "ronda" else "#ff9a86")
    return t


def centro(m):
    ys, xs = np.nonzero(m)
    return float(xs.mean()), float(ys.mean())


def normali(f):
    n = f["n"].copy()
    for m in f["ruoli"].values():                   # le luci piatte
        n[m] = (0, 0, 1)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    out = np.zeros(n.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip((n * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)
    out[..., 3] = f["rgba"][..., 3]
    return out


# ------------------------------------------------------------------ fotogrammi, atlante e JSON
CROP = {nm: ritaglia(nm) for nm, *_ in FR}
CX = {nm: cx for nm, _, _, _, _, _, cx in FR}
POSI = {nm: i for i, (nm, *_) in enumerate(FR)}
for k, nm in enumerate(CROP):
    sporca(CROP[nm], 11 + k, 1.0 if "broken" in nm else 0.8 if nm.startswith("segugio") else 0.5)

ANCORA_Y = {"segugio": CROP["segugio_idle_0"]["box"][3], "vedetta": CROP["vedetta_patrol_0"]["box"][3]}
RISULTATI = {}
for sid, pose in (("segugio", SEG_POSE), ("vedetta", VED_POSE)):
    fot = []
    for an, frs, ticks, modo, loop in pose:
        for i in range(len(frs)):
            nm = f"{sid}_{an if an != 'spot' else 'patrol'}_{i}"
            f = CROP[nm]
            bx = f["box"]
            ax = cv.sx(POSI[nm] * STEP + CX[nm], 0.0)
            ay = bx[3] if an == "broken" else ANCORA_Y[sid]
            anc = (int(round(ax - bx[0])), int(ay - bx[1]))
            pts = {}
            for r, key in (("occhi", "eye"), ("luce", "beacon"), ("bocca", "mouth"), ("vapore", "vent"),
                           ("faro", "lamp"), ("collare", "collar")):
                if r in f["ruoli"]:
                    px_, py_ = centro(f["ruoli"][r])
                    pts[key] = [int(round(px_ - anc[0])), int(round(py_ - anc[1]))]
            fot.append(dict(an=an, i=i, img=luci(f, modo, sid), nrm=normali(f), anchor=anc, ticks=ticks, points=pts,
                            loop=loop, modo=modo, src=nm))
    # atlante: righe per animazione, 1 px di spazio
    W = sum(fr["img"].shape[1] + 1 for fr in fot if fr["an"] == "patrol") + 1
    W = max(W, max(fr["img"].shape[1] for fr in fot) + 2, 256)
    x, y, hrow, rects = 1, 1, 0, []
    for fr in fot:
        h, w = fr["img"].shape[:2]
        if x + w + 1 > W:
            x, y, hrow = 1, y + hrow + 1, 0
        rects.append((x, y, w, h))
        x, hrow = x + w + 1, max(hrow, h)
    H = y + hrow + 1
    at, an_ = np.zeros((H, W, 4), np.uint8), np.zeros((H, W, 4), np.uint8)
    an_[..., :3] = (128, 128, 255)
    anims = {}
    for fr, (x, y, w, h) in zip(fot, rects):
        at[y:y + h, x:x + w] = fr["img"]
        an_[y:y + h, x:x + w] = fr["nrm"]
        a = anims.setdefault(fr["an"], dict(loop=fr["loop"], frames=[]))
        a["frames"].append(dict(rect=[x, y, w, h], anchor=list(fr["anchor"]), ticks=fr["ticks"], hurt=[], hit=[],
                                events=[], tags=[fr["modo"]], dx=0, points=fr["points"]))
    od = os.path.join(DEST, sid)
    os.makedirs(od, exist_ok=True)
    Image.fromarray(at, "RGBA").save(os.path.join(od, sid + ".png"))
    Image.fromarray(an_, "RGBA").save(os.path.join(od, sid + "_n.png"))
    lines = ["{", f'  "id": "{sid}",', '  "format": 1,', f'  "image": "{sid}.png",', f'  "normal_image": "{sid}_n.png",',
             '  "pixels_per_meter": 60,', '  "animations": {']
    names = list(anims)
    for k, n in enumerate(names):
        lines.append(f'    "{n}": {{')
        lines.append(f'      "loop": {"true" if anims[n]["loop"] else "false"},')
        lines.append('      "frames": [')
        frs = anims[n]["frames"]
        for j, fr in enumerate(frs):
            lines.append("        " + json.dumps(fr, ensure_ascii=False) + ("," if j < len(frs) - 1 else ""))
        lines.append("      ]")
        lines.append("    }" + ("," if k < len(names) - 1 else ""))
    lines += ["  }", "}", ""]
    open(os.path.join(od, sid + ".json"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    RISULTATI[sid] = fot
    print(sid, at.shape[1], "x", at.shape[0], {n: len(a["frames"]) for n, a in anims.items()})

# per il foglio: i fotogrammi con le luci e la Vedetta vecchia
np.savez_compressed(os.path.join(OUTD, "droni_foglio.npz"),
                    **{f"{sid}|{fr['an']}|{fr['i']}": fr["img"] for sid, fot in RISULTATI.items() for fr in fot},
                    **{f"anc|{sid}|{fr['an']}|{fr['i']}": np.array(fr["anchor"]) for sid, fot in RISULTATI.items() for fr in fot},
                    vecchia=luci(CROP["vedetta_vecchia"], "ronda", "vedetta"))
print("ok")
