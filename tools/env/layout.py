# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - "Sotto la Linea": descrizione deterministica delle scene 3D degli sfondi.

Scrive i file di lavoro JSON per tools/blender/env_gbuffer.py (geometria) e le operazioni di pittura
2D (insegne, manifesti, graffiti, reti, pozzanghere...) lette da tools/env/paint.py. Nessun numero
casuale senza seme: ogni scelta usa random.Random con un seme fisso.

Scene:
  street : strada di periferia (x 0-1536) e arena sotto i piloni (1536-1920), piani backdrop + floor
  near   : palazzi del secondo isolato (parallasse 0,5), densità ridotta
  fg     : impalcato della ferrovia visto dal basso (parallasse 1,25)
Coordinate: vedi envlib.py (X lungo la strada, Y profondità, Z in alto, metri).
"""
from __future__ import annotations

import math
import random

import envlib as E
from materials import (M_ASPHALT, M_AWNING_BLUE, M_AWNING_RED, M_BRICK, M_CABINET, M_CABLE, M_CONCRETE,
                       M_CONCRETE_PILLAR, M_DARK, M_DIRT, M_GLASS, M_GLASS_DOOR, M_HOARDING, M_KERB, M_LAMP,
                       M_METAL, M_NEON, M_PAPER, M_PLANT, M_PLASTER_BLUE, M_PLASTER_GREY, M_PLASTER_MAUVE,
                       M_POLE, M_RUBBER, M_RUST, M_SHUTTER, M_SIDEWALK, M_SIGNBOX, M_STEEL, M_STONE, M_TILE,
                       M_TRASH, M_WINDOW_LIT, M_WOOD, M_SLAB)

C = E.CLS
YF = 0.6            # piano delle facciate (davanti)
ZROAD = -0.12       # quota della carreggiata (il marciapiede è a 0)
YKERB = -2.0        # bordo del marciapiede
KERB_W = 0.25
COL = dict(
    plaster_blue="#2f3a5c", plaster_mauve="#3f2c52", plaster_grey="#363246", brick="#4a2234",
    stone="#463b4c", metal="#323a4e", shutter="#3a4458", glass="#151d36", wood="#3b2228",
    asphalt="#1f172f", sidewalk="#2c2339", kerb="#353142", dirt="#2e2029", signbox="#1c2030",
    awning_red="#6a182e", awning_blue="#1c2d4c", trash="#1a1724", plant="#24392b", rubber="#1b1820",
    rust="#5c3023", paper="#857d90", pillar="#3a3648", steel="#2a3144", dark="#100e18", pole="#3c384a",
    cabinet="#56606a",
)
NEON = dict(red="#ff4a4a", orange="#ff8a32", warm="#ffb060", cyan="#33e4ff", white="#ffe8d8", sodium="#ffa448",
            pink="#ff5a7a")


def c3(h):
    return E.f3(h)


class Scene:
    def __init__(self, name):
        self.name = name
        self.objects = []
        self.paint = []

    def add(self, **o):
        o.setdefault("alb", c3("#808080"))
        self.objects.append(o)
        return len(self.objects)

    def box(self, x0, y0, z0, x1, y1, z1, cls, mat, col, emi=None, **kw):
        return self.add(type="box", size=[x1 - x0, y1 - y0, z1 - z0], at=[x0, y0, z0], cls=C[cls], mat=mat,
                        alb=c3(col), emi=c3(emi) if emi else None, **kw)

    def cyl(self, c, r, h, cls, mat, col, n=12, axis="z", r2=None, emi=None, **kw):
        return self.add(type="cyl", c=list(c), r=r, h=h, n=n, axis=axis, r2=r2, cls=C[cls], mat=mat, alb=c3(col),
                        emi=c3(emi) if emi else None, **kw)

    def tube(self, pts, r, cls, mat, col, n=6, emi=None):
        return self.add(type="tube", pts=[list(p) for p in pts], r=r, n=n, cls=C[cls], mat=mat, alb=c3(col),
                        emi=c3(emi) if emi else None)

    def mesh(self, verts, faces, cls, mat, col, emi=None, smooth=False):
        return self.add(type="mesh", verts=[list(v) for v in verts], faces=faces, cls=C[cls], mat=mat,
                        alb=c3(col), emi=c3(emi) if emi else None, smooth=smooth)

    def kit(self, key, at, cls, mat, col, s=1.0, rz=0.0, matmap=None, emi=None):
        return self.add(type="kit", key=key, at=list(at), s=s, rz=rz, cls=C[cls], mat=mat, alb=c3(col),
                        emi=c3(emi) if emi else None, matmap=matmap or {})

    def op(self, kind, **kw):
        self.paint.append(dict(kind=kind, **kw))


def X(xs, Y=YF):
    return E.x_to_X(xs, Y)


# ------------------------------------------------------------------ mappe dei materiali dei kit
def cp_matmap(accent="#5c3023"):
    return {
        "Black": dict(cls=C["CABLE"], mat=M_CABLE, alb=c3("#14121c")),
        "Grey": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#3a4256")),
        "LightGrey": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#4c566c")),
        "DarkGrey": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#262c3c")),
        "MetalLight": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#4c566c")),
        "Orange": dict(cls=C["METAL"], mat=M_RUST, alb=c3(accent)),
        "Texture_Signs": dict(cls=C["SIGN"], mat=M_SIGNBOX, alb=c3("#1c2030")),
        "Light": dict(cls=C["LAMP"], mat=M_LAMP, alb=c3(NEON["sodium"]), emi=c3(NEON["sodium"])),
        "Screen": dict(cls=C["GLASS"], mat=M_GLASS, alb=c3("#151d36")),
    }


def dt_matmap():
    return {
        "MI_Ornaments": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#2a3042")),
        "MI_Trim_MetalConcrete": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#3a4256")),
        "MI_Trim": dict(cls=C["WOOD"], mat=M_WOOD, alb=c3("#3b2228")),
        "MI_Trim_Dark": dict(cls=C["METAL"], mat=M_METAL, alb=c3("#262c3c")),
        "MI_Glass": dict(cls=C["GLASS"], mat=M_GLASS, alb=c3("#151d36")),
        "MI_FakeInterior": dict(cls=C["GLASS"], mat=M_GLASS, alb=c3("#151d36")),
        "MI_InteriorWall": dict(cls=C["DARK"], mat=M_DARK, alb=c3("#100e18")),
        "MI_Dirt": dict(cls=C["DARK"], mat=M_DIRT, alb=c3("#2e2029")),
    }


# ------------------------------------------------------------------ pezzi di facciata
LINTEL = 2.05
SIGN_Z0, SIGN_Z1 = 2.1, 2.58


def building(S, xs0, xs1, col_key, mat, top=14.0, depth=9.0, plinth=True, cornice=None):
    """Corpo dell'edificio (fronte arretrato di 0,2 m) e zoccolo. Ritorna (X0, X1)."""
    X0, X1 = X(xs0), X(xs1)
    S.box(X0, YF + 0.2, 0.0, X1, YF + depth, top, "WALL" if mat != M_BRICK else "BRICK", mat, COL[col_key])
    return X0, X1


def facade_band(S, X0, X1, col_key, mat, z0=LINTEL, z1=14.0):
    """Fascia di facciata sopra le aperture (a filo YF)."""
    return S.box(X0, YF, z0, X1, YF + 0.2, z1, "WALL" if mat != M_BRICK else "BRICK", mat, COL[col_key])


def pier(S, X0, X1, col_key, mat, z1=LINTEL, cls=None):
    return S.box(X0, YF, 0.0, X1, YF + 0.2, z1, cls or ("WALL" if mat != M_BRICK else "BRICK"), mat, COL[col_key])


def plinth(S, X0, X1, col="#2a2433", z1=0.38):
    return S.box(X0, YF - 0.04, 0.0, X1, YF + 0.05, z1, "CONCRETE", M_STONE, col)


def sign_box(S, X0, X1, z0=SIGN_Z0, z1=SIGN_Z1, col=None, lit=None):
    """Insegna a cassonetto sopra la vetrina. lit = colore emissivo del pannello (insegna luminosa)."""
    if lit:
        return S.box(X0, YF - 0.14, z0, X1, YF + 0.02, z1, "BILLBOARD", M_SIGNBOX, lit, emi=lit)
    return S.box(X0, YF - 0.14, z0, X1, YF + 0.02, z1, "SIGN", M_SIGNBOX, col or COL["signbox"])


def shutter(S, X0, X1, z0=0.0, z1=LINTEL, col=None):
    oid = S.box(X0, YF + 0.16, z0, X1, YF + 0.2, z1, "SHUTTER", M_SHUTTER, col or COL["shutter"])
    S.box(X0 - 0.04, YF + 0.12, z1 - 0.1, X1 + 0.04, YF + 0.2, z1, "METAL", M_METAL, "#262c3c")   # guida in alto
    return oid


def shop_window(S, X0, X1, z0=0.4, z1=1.92, lit="#ffb060", frame="#262c3c", mullions=1):
    """Vetrina: zoccolo, cornice metallica, vetro (acceso o spento), montanti."""
    S.box(X0, YF + 0.12, 0.0, X1, YF + 0.2, z0, "METAL", M_METAL, frame)
    S.box(X0, YF + 0.1, z0 - 0.06, X1, YF + 0.2, z0, "METAL", M_METAL, "#3a4256")
    S.box(X0, YF + 0.1, z1, X1, YF + 0.2, LINTEL, "METAL", M_METAL, frame)
    if lit:
        g = S.box(X0, YF + 0.16, z0, X1, YF + 0.2, z1, "WINDOW_LIT", M_WINDOW_LIT, lit, emi=lit)
    else:
        g = S.box(X0, YF + 0.16, z0, X1, YF + 0.2, z1, "GLASS", M_GLASS, COL["glass"])
    w = X1 - X0
    for i in range(1, mullions + 1):
        xm = X0 + w * i / (mullions + 1)
        S.box(xm - 0.03, YF + 0.12, z0, xm + 0.03, YF + 0.2, z1, "METAL", M_METAL, frame)
    for xe in (X0, X1 - 0.05):
        S.box(xe, YF + 0.1, z0, xe + 0.05, YF + 0.2, z1, "METAL", M_METAL, frame)
    return g


def door(S, X0, X1, z1=1.98, kind="glass", lit="#ffb060", col=None):
    """Porta: vetro acceso, vetro scuro o legno."""
    S.box(X0 - 0.06, YF + 0.1, 0.0, X0, YF + 0.2, z1 + 0.06, "METAL", M_METAL, "#262c3c")
    S.box(X1, YF + 0.1, 0.0, X1 + 0.06, YF + 0.2, z1 + 0.06, "METAL", M_METAL, "#262c3c")
    S.box(X0 - 0.06, YF + 0.1, z1, X1 + 0.06, YF + 0.2, z1 + 0.06, "METAL", M_METAL, "#262c3c")
    if kind == "glass" and lit:
        g = S.box(X0, YF + 0.17, 0.05, X1, YF + 0.2, z1, "WINDOW_LIT", M_WINDOW_LIT, lit, emi=lit)
        S.box(X0, YF + 0.15, 1.0, X1, YF + 0.17, 1.06, "METAL", M_METAL, "#55647c")   # maniglione
        return g
    if kind == "glass":
        return S.box(X0, YF + 0.17, 0.05, X1, YF + 0.2, z1, "GLASS", M_GLASS_DOOR, COL["glass"])
    g = S.box(X0, YF + 0.15, 0.0, X1, YF + 0.2, z1, "WOOD", M_WOOD, col or COL["wood"])
    return g


def awning(S, X0, X1, z_top=2.3, out=0.8, drop=0.32, col_key="awning_red", mat=M_AWNING_RED):
    """Tenda da sole: falda inclinata + mantovana."""
    y_out = YF - out
    verts = [(X0, YF + 0.02, z_top), (X1, YF + 0.02, z_top), (X1, y_out, z_top - drop), (X0, y_out, z_top - drop),
             (X0, YF + 0.02, z_top + 0.04), (X1, YF + 0.02, z_top + 0.04), (X1, y_out, z_top - drop + 0.04),
             (X0, y_out, z_top - drop + 0.04)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    a = S.mesh(verts, faces, "AWNING", mat, COL[col_key])
    v = S.box(X0, y_out - 0.02, z_top - drop - 0.24, X1, y_out, z_top - drop + 0.04, "AWNING", mat, COL[col_key])
    for xe in (X0 + 0.05, X1 - 0.07):
        S.tube([(xe, YF, z_top - 0.5), (xe, y_out + 0.05, z_top - drop - 0.02)], 0.018, "METAL", M_METAL, "#55647c")
    return a, v


def blade_sign(S, Xc, z0, z1, depth=0.72, thick=0.14, col=None):
    """Insegna a bandiera perpendicolare alla facciata; ritorna l'oid (faccia +X visibile)."""
    y0 = YF - depth - 0.08
    oid = S.box(Xc, y0, z0, Xc + thick, YF - 0.08, z1, "SIGN", M_SIGNBOX, col or COL["signbox"])
    for zb in (z0 + 0.15, z1 - 0.2):
        S.box(Xc + 0.03, YF - 0.1, zb, Xc + thick - 0.03, YF + 0.02, zb + 0.06, "METAL", M_METAL, "#262c3c")
    return oid, y0


def wall_lamp(S, Xc, z, col=NEON["warm"]):
    S.box(Xc - 0.09, YF - 0.12, z, Xc + 0.09, YF + 0.02, z + 0.05, "METAL", M_METAL, "#262c3c")
    return S.box(Xc - 0.07, YF - 0.11, z - 0.12, Xc + 0.07, YF - 0.01, z, "LAMP", M_LAMP, col, emi=col)


def downpipe(S, Xc, z1=8.0, col="#3a4256", y=None):
    y = YF - 0.07 if y is None else y
    S.cyl((Xc, y, 0.0), 0.05, z1, "PIPE", M_METAL, col, n=8)
    for zz in (0.9, 2.6, 4.4):
        S.box(Xc - 0.07, y - 0.06, zz, Xc + 0.07, y + 0.07, zz + 0.05, "METAL", M_METAL, "#262c3c")


def ac_unit(S, Xl, z, small=False):
    """Condizionatore a muro (Quaternius Downtown City MegaKit, CC0)."""
    s = 0.9 if small else 1.15
    return S.kit("dt:Prop_ACUnit", (Xl, YF - 0.36 * s - 0.02, z), "METAL", M_METAL, "#4c566c", s=s,
                 matmap=dt_matmap())


def trash_bags(S, Xl, rng, n=3):
    for i in range(n):
        x = Xl + i * 0.36 + rng.uniform(-0.05, 0.05)
        r = rng.uniform(0.2, 0.27)
        S.cyl((x, YF - 0.25 - rng.uniform(0, 0.1), 0.0), r, r * 1.5, "TRASH", M_TRASH, COL["trash"], n=9,
              r2=r * 0.55)


# ------------------------------------------------------------------ STRADA (backdrop + floor)
def build_street():
    S = Scene("street")
    rng = random.Random(20261103)
    XL, XR = -14.0, 56.0            # la geometria esce dalla finestra: niente bordi vuoti
    # ---------------- suolo
    # marciapiede (asfalto più chiaro) dalla facciata al cordolo; strada più bassa
    S.box(XL, YKERB, -0.3, X(1560, 0) + 0.2, YF + 0.3, 0.0, "SIDEWALK", M_SIDEWALK, COL["sidewalk"])
    S.box(XL, YKERB - KERB_W, -0.3, X(1560, 0) + 0.2, YKERB, 0.0, "KERB", M_KERB, COL["kerb"])
    S.box(XL, -9.0, -0.4, XR, YKERB - KERB_W, ZROAD, "ASPHALT", M_ASPHALT, COL["asphalt"])
    # arena: piazzale in cemento sotto il viadotto, a quota strada, raccordato con una rampa
    xa = X(1560, 0)
    S.box(xa + 0.2, YKERB - KERB_W, -0.4, XR, YF + 3.0, ZROAD, "ASPHALT", M_SLAB, "#2a2534")
    S.box(xa, YKERB - KERB_W, -0.3, xa + 0.25, YF + 0.3, 0.0, "KERB", M_KERB, COL["kerb"])
    # tombini e caditoie (geometria piatta), sul marciapiede e in strada
    for xs in (300, 1010, 1760):
        S.cyl((X(xs, -3.6), -3.6, ZROAD), 0.42, 0.025, "METAL", M_METAL, "#262c3c", n=16)
    for xs in (150, 560, 940, 1400):
        Xg = X(xs, YKERB - KERB_W - 0.3)
        S.box(Xg, YKERB - KERB_W - 0.42, ZROAD, Xg + 0.55, YKERB - KERB_W - 0.02, ZROAD + 0.015, "METAL",
              M_METAL, "#161a26")
        S.op("grate", X0=Xg, X1=Xg + 0.55, Y0=YKERB - KERB_W - 0.42, Y1=YKERB - KERB_W - 0.02, z=ZROAD + 0.015)
    # ---------------- 1. angolo di partenza (xs -60..60): muro con manifesti
    X0, X1 = building(S, -400, 60, "plaster_mauve", M_PLASTER_MAUVE, depth=2.2)
    wall_a = facade_band(S, X0, X1, "plaster_mauve", M_PLASTER_MAUVE, z0=0.0)
    plinth(S, X0, X1)
    downpipe(S, X1 - 0.18)
    S.op("posters", oid=wall_a, X0=X(-40), X1=X(48), z0=0.55, z1=2.05, seed=11, n=7)
    S.op("graffiti", oid=wall_a, X0=X(4), X1=X(48), z0=0.1, z1=0.9, seed=12, word="GIG")   # tutto dentro x >= 0
    wall_lamp(S, X(10), 2.3, NEON["sodium"])
    # niente targa "VIETATO AFFIGGERE" qui: a x 0 il bordo del mondo la tagliava ("...GGERE")
    # ---------------- 2. LOTTO A (xs 60..230): recinzione, terra, vista sulla città
    lot_a = (60, 230)
    lot(S, rng, lot_a[0], lot_a[1], depth=5.5, seed=21, sign="VIETATO L'ACCESSO")
    # ---------------- 3-5. edificio con BAR, portone, TABACCHI (xs 230..600)
    X0, X1 = building(S, 230, 600, "plaster_blue", M_PLASTER_BLUE, depth=2.0)
    band = facade_band(S, X0, X1, "plaster_blue", M_PLASTER_BLUE)
    # BAR 230..390
    pier(S, X(230), X(244), "plaster_blue", M_PLASTER_BLUE)
    pier(S, X(376), X(392), "plaster_blue", M_PLASTER_BLUE)
    g_bar = shop_window(S, X(244), X(334), mullions=1, lit="#ffa858")
    d_bar = door(S, X(338), X(372), lit="#ffb868")
    S.box(X(334), YF + 0.1, 0.0, X(338), YF + 0.2, LINTEL, "METAL", M_METAL, "#262c3c")
    sb = sign_box(S, X(240), X(380))
    S.op("neon_text", oid=sb, face="front", X0=X(240), X1=X(380), z0=SIGN_Z0, z1=SIGN_Z1, Yf=YF - 0.14,
         text="BAR", sub="CAFFÈ", ramp="neon_red", font="big", frame=True)
    awning(S, X(244), X(372), z_top=2.08, out=0.62, drop=0.26)
    S.op("awning_text", text="BAR SPORT", X0=X(244), X1=X(372))
    S.op("interior", oid=g_bar, style="bar", X0=X(244), X1=X(334), z0=0.4, z1=1.92)
    S.op("window_neon", oid=g_bar, X0=X(244), X1=X(334), z0=0.4, z1=1.92, text="APERTO", ramp="neon_red",
         fx=0.22, fy=0.62)
    S.op("interior", oid=d_bar, style="door", X0=X(338), X1=X(372), z0=0.05, z1=1.98)
    ac_unit(S, X(250), 2.7)
    # portone 392..450
    pier(S, X(392), X(400), "plaster_blue", M_PLASTER_BLUE)
    pier(S, X(442), X(452), "plaster_blue", M_PLASTER_BLUE)
    S.box(X(400), YF + 0.05, 0.0, X(442), YF + 0.2, 0.12, "CONCRETE", M_STONE, "#463b4c")   # gradino
    pt = door(S, X(403), X(439), z1=2.0, kind="wood", col="#2f1a20")
    S.op("door_panels", oid=pt, X0=X(403), X1=X(439), z0=0.12, z1=2.0)
    wall_lamp(S, X(421), 2.22, NEON["warm"])
    S.op("plate", oid=band, X0=X(404), X1=X(414), z0=1.45, z1=1.6, text="17", col="#d8d0e0", bg="#1c2a52",
         face_Y=YF)
    # TABACCHI 452..600
    pier(S, X(586), X(600), "plaster_blue", M_PLASTER_BLUE)
    g_tab = shop_window(S, X(452), X(540), mullions=1, lit="#ffc070")
    d_tab = door(S, X(546), X(582), lit="#ffc878")
    S.box(X(540), YF + 0.1, 0.0, X(546), YF + 0.2, LINTEL, "METAL", M_METAL, "#262c3c")
    sb = sign_box(S, X(470), X(584))
    S.op("neon_text", oid=sb, face="front", X0=X(470), X1=X(584), z0=SIGN_Z0, z1=SIGN_Z1, Yf=YF - 0.14,
         text="TABACCHI", ramp="neon_orange", font="med", frame=False)
    tb = S.box(X(452), YF - 0.16, SIGN_Z0 - 0.02, X(468), YF + 0.02, SIGN_Z1 + 0.04, "BILLBOARD", M_SIGNBOX,
               "#1c2a6a", emi="#1c2a6a")
    S.op("tabacchi_t", oid=tb, X0=X(452), X1=X(468), z0=SIGN_Z0 - 0.02, z1=SIGN_Z1 + 0.04, Yf=YF - 0.16)
    S.op("interior", oid=g_tab, style="tabacchi", X0=X(452), X1=X(540), z0=0.4, z1=1.92)
    S.op("window_neon", oid=g_tab, X0=X(452), X1=X(540), z0=0.4, z1=1.92, text="LOTTO", ramp="neon_red",
         fx=0.75, fy=0.62)
    S.op("interior", oid=d_tab, style="door", X0=X(546), X1=X(582), z0=0.05, z1=1.98)
    S.op("posters", oid=band, X0=X(392), X1=X(398), z0=0.4, z1=1.9, seed=31, n=1)
    downpipe(S, X(598))
    trash_bags(S, X(396), rng, n=2)
    # ---------------- 6. cantiere con palizzata (xs 600..740)
    hoarding(S, rng, 600, 742)
    # ---------------- 7. KEBAB (xs 742..900), edificio in mattoni
    X0, X1 = building(S, 742, 900, "brick", M_BRICK, depth=2.0)
    band = facade_band(S, X0, X1, "brick", M_BRICK)
    pier(S, X(742), X(756), "brick", M_BRICK)
    pier(S, X(886), X(900), "brick", M_BRICK)
    g_keb = shop_window(S, X(756), X(842), mullions=0, lit="#ff9a50")
    d_keb = door(S, X(848), X(882), lit="#ffaa60")
    S.box(X(842), YF + 0.1, 0.0, X(848), YF + 0.2, LINTEL, "METAL", M_METAL, "#262c3c")
    sb = sign_box(S, X(752), X(890), lit=None)
    S.op("neon_text", oid=sb, face="front", X0=X(752), X1=X(890), z0=SIGN_Z0, z1=SIGN_Z1, Yf=YF - 0.14,
         text="KEBAB", sub="PIZZA", ramp="neon_orange", font="big", frame=True)
    S.op("interior", oid=g_keb, style="kebab", X0=X(756), X1=X(842), z0=0.4, z1=1.92)
    S.op("window_neon", oid=g_keb, X0=X(756), X1=X(842), z0=0.4, z1=1.92, text="24H", ramp="neon_red",
         fx=0.15, fy=0.5)
    S.op("interior", oid=d_keb, style="door", X0=X(848), X1=X(882), z0=0.05, z1=1.98)
    ac_unit(S, X(820), 2.9, small=True)
    S.op("posters", oid=band, X0=X(744), X1=X(755), z0=0.5, z1=1.7, seed=71, n=1)
    # ---------------- 8. vicolo con cancello (xs 900..990)
    alley(S, rng, 900, 990)
    # ---------------- 9. FARMACIA (xs 990..1140)
    X0, X1 = building(S, 990, 1140, "plaster_grey", M_PLASTER_GREY)
    band = facade_band(S, X0, X1, "plaster_grey", M_PLASTER_GREY)
    plinth(S, X(990), X(1004))
    pier(S, X(990), X(1004), "plaster_grey", M_PLASTER_GREY)
    pier(S, X(1126), X(1140), "plaster_grey", M_PLASTER_GREY)
    g_far = shop_window(S, X(1004), X(1078), mullions=1, lit="#ffd090")
    d_far = door(S, X(1084), X(1122), lit="#ffd8a0")
    S.box(X(1078), YF + 0.1, 0.0, X(1084), YF + 0.2, LINTEL, "METAL", M_METAL, "#262c3c")
    sb = sign_box(S, X(1000), X(1130))
    S.op("neon_text", oid=sb, face="front", X0=X(1000), X1=X(1130), z0=SIGN_Z0, z1=SIGN_Z1, Yf=YF - 0.14,
         text="FARMACIA", ramp="neon_red", font="med", frame=False, cross=True)
    S.op("interior", oid=g_far, style="farmacia", X0=X(1004), X1=X(1078), z0=0.4, z1=1.92)
    S.op("interior", oid=d_far, style="door", X0=X(1084), X1=X(1122), z0=0.05, z1=1.98)
    cr, cy0 = blade_sign(S, X(1136), 2.05, 2.62, depth=0.55, thick=0.12, col="#1a1424")
    S.op("cross_blade", oid=cr, Xf=X(1136) + 0.12, Y0=cy0, Y1=YF - 0.08, z0=2.05, z1=2.62)
    # ---------------- 10. palazzo con portone, serranda e palo della linea elettrica (xs 1140..1340)
    X0, X1 = building(S, 1140, 1340, "plaster_mauve", M_PLASTER_MAUVE)
    band = facade_band(S, X0, X1, "plaster_mauve", M_PLASTER_MAUVE)
    plinth(S, X(1140), X(1340))
    pier(S, X(1140), X(1150), "plaster_mauve", M_PLASTER_MAUVE)
    pier(S, X(1190), X(1206), "plaster_mauve", M_PLASTER_MAUVE)
    pt = door(S, X(1153), X(1188), z1=2.0, kind="wood", col="#2a1a24")
    S.op("door_panels", oid=pt, X0=X(1153), X1=X(1188), z0=0.0, z1=2.0)
    wall_lamp(S, X(1170), 2.22, NEON["warm"])
    sh = shutter(S, X(1206), X(1326))
    pier(S, X(1326), X(1340), "plaster_mauve", M_PLASTER_MAUVE)
    # il graffito finisce prima del palo della luce (x 1292), che altrimenti copre l'ultima lettera
    S.op("graffiti", oid=sh, X0=X(1210), X1=X(1276), z0=0.15, z1=1.9, seed=101, word="SOTTO")
    S.op("posters", oid=sh, X0=X(1214), X1=X(1240), z0=1.1, z1=1.75, seed=102, n=2)
    S.op("plate", oid=sh, X0=X(1268), X1=X(1316), z0=1.85, z1=2.05, text="AFFITTASI", col="#20182a",
         bg="#d8c860")
    ac_unit(S, X(1218), 2.6)
    utility_pole(S, 1292)
    # ---------------- 11. OSTERIA (xs 1340..1462), mattoni e legno
    X0, X1 = building(S, 1340, 1462, "brick", M_BRICK)
    band = facade_band(S, X0, X1, "brick", M_BRICK)
    pier(S, X(1340), X(1352), "brick", M_BRICK)
    pier(S, X(1450), X(1462), "brick", M_BRICK)
    g_ost = shop_window(S, X(1352), X(1404), mullions=0, lit="#ff9850", frame="#2f1a20")
    d_ost = door(S, X(1410), X(1446), z1=1.98, kind="wood", col="#3b2228")
    S.box(X(1404), YF + 0.1, 0.0, X(1410), YF + 0.2, LINTEL, "WOOD", M_WOOD, "#2f1a20")
    sb = sign_box(S, X(1350), X(1452), col="#24141c")
    S.op("neon_text", oid=sb, face="front", X0=X(1350), X1=X(1452), z0=SIGN_Z0, z1=SIGN_Z1, Yf=YF - 0.14,
         text="OSTERIA", ramp="neon_orange", font="med", frame=True)
    S.op("interior", oid=g_ost, style="osteria", X0=X(1352), X1=X(1404), z0=0.4, z1=1.92)
    S.op("window_neon", oid=g_ost, X0=X(1352), X1=X(1404), z0=0.4, z1=1.92, text="VINO", ramp="neon_orange",
         fx=0.5, fy=0.62)
    S.op("door_panels", oid=d_ost, X0=X(1410), X1=X(1446), z0=0.0, z1=1.98)
    wall_lamp(S, X(1406), 2.15, NEON["warm"])
    S.op("menu_board", X0=X(1354), Y=YF - 0.3, z0=0.0)
    S.box(X(1354), YF - 0.42, 0.0, X(1354) + 0.5, YF - 0.3, 0.95, "WOOD", M_WOOD, "#2f1a20")
    # ---------------- 12. HOTEL (xs 1462..1572), ultimo palazzo prima dell'arena
    X0, X1 = building(S, 1462, 1572, "plaster_blue", M_PLASTER_BLUE, depth=2.0)
    band = facade_band(S, X0, X1, "plaster_blue", M_PLASTER_BLUE)
    pier(S, X(1462), X(1478), "plaster_blue", M_PLASTER_BLUE)
    pier(S, X(1522), X(1572), "plaster_blue", M_PLASTER_BLUE)
    S.box(X(1478), YF + 0.05, 0.0, X(1522), YF + 0.2, 0.12, "CONCRETE", M_STONE, "#463b4c")
    d_hot = door(S, X(1482), X(1518), z1=2.0, lit="#ffc078")
    S.op("interior", oid=d_hot, style="door", X0=X(1482), X1=X(1518), z0=0.05, z1=2.0)
    S.box(X(1474), YF - 0.7, 2.06, X(1526), YF + 0.02, 2.13, "METAL", M_METAL, "#262c3c")    # pensilina
    S.op("plate", oid=band, X0=X(1484), X1=X(1516), z0=2.2, z1=2.42, text="★★", col="#ffd27a", bg="#1c2030",
         face_Y=YF)
    hb, hy0 = blade_sign(S, X(1536), 0.95, 2.55, depth=0.8, thick=0.16)
    S.op("neon_vertical", oid=hb, Xf=X(1536) + 0.16, Y0=hy0, Y1=YF - 0.08, z0=0.95, z1=2.55, text="HOTEL",
         ramp="neon_red")
    S.op("posters", oid=band, X0=X(1530), X1=X(1566), z0=0.5, z1=1.9, seed=121, n=3)
    S.op("graffiti", oid=band, X0=X(1528), X1=X(1570), z0=0.1, z1=0.8, seed=122, word="LINEA")
    downpipe(S, X(1568))
    # ---------------- 13. ARENA sotto i piloni (xs 1572..1920)
    arena(S, rng)
    # ---------------- suolo: pozzanghere, crepe, rattoppi, rifiuti, sporco
    floor_dressing(S, rng)
    return S


def lot(S, rng, xs0, xs1, depth=5.5, seed=0, sign=None):
    """Lotto vuoto dietro una rete: terra, macerie, gomme, erbacce. Il fondo resta aperto (parallasse)."""
    r = random.Random(seed)
    yfence = YF - 0.15
    X0, X1 = X(xs0, yfence), X(xs1, yfence)
    # terra del lotto (fino in fondo) e cordolo basso sul retro
    S.box(X0 - 0.3, yfence, -0.3, X1 + 8.0, YF + depth, 0.02, "SIDEWALK", M_DIRT, COL["dirt"])
    S.box(X0 - 0.3, YF + depth - 0.25, 0.0, X1 + 8.0, YF + depth, 0.35, "CONCRETE", M_CONCRETE, "#2c2836")
    # paletti, traverse e rete (rete disegnata in 2D con test di profondità)
    n = max(2, int(round((X1 - X0) / 1.6)))
    for i in range(n + 1):
        xp = X0 + (X1 - X0) * i / n
        S.cyl((xp, yfence, 0.0), 0.035, 1.62, "POLE", M_METAL, "#3a4256", n=8)
    S.tube([(X0, yfence, 1.58), (X1, yfence, 1.58)], 0.022, "POLE", M_METAL, "#3a4256")
    S.tube([(X0, yfence, 0.08), (X1, yfence, 0.08)], 0.018, "POLE", M_METAL, "#3a4256")
    S.op("fence", along="x", X0=X0, X1=X1, Y=yfence, z0=0.08, z1=1.58, style="chain", seed=seed, sag=True)
    # filo spinato in cima
    S.op("barbed", along="x", X0=X0, X1=X1, Y=yfence, z=1.68)
    if sign:
        # il cartello sta fra due paletti (quelli sono davanti alla rete e coprirebbero le lettere)
        gap = (X1 - X0) / n
        sx0 = X0 + gap + 0.12
        sx1 = min(X0 + 2 * gap - 0.12, sx0 + 1.2)
        pl = S.box(sx0, yfence - 0.03, 0.95, sx1, yfence - 0.01, 1.35, "SIGN", M_SIGNBOX, "#d8d0e0")
        S.op("plate", oid=pl, X0=sx0, X1=sx1, z0=0.95, z1=1.35, text=sign, col="#b8303f",
             bg="#d8d0e0", face_Y=yfence - 0.03, lines=2)
    # macerie, gomme, erbacce, un carrello
    for i in range(6):
        cx = r.uniform(X0 + 0.5, X1 + 2.0)
        cy = r.uniform(YF + 0.6, YF + depth - 0.6)
        h = r.uniform(0.15, 0.45)
        S.cyl((cx, cy, 0.0), r.uniform(0.35, 0.8), h, "CONCRETE", M_CONCRETE, "#302b3a", n=7, r2=0.12)
    for i in range(3):
        cx = r.uniform(X0 + 0.6, X1)
        cy = r.uniform(YF + 0.4, YF + 2.5)
        S.cyl((cx, cy, 0.0), 0.32, 0.22, "DARK", M_RUBBER, COL["rubber"], n=12)
        S.cyl((cx, cy, 0.22), 0.32, 0.22, "DARK", M_RUBBER, COL["rubber"], n=12)
    for i in range(14):
        cx = r.uniform(X0 - 0.2, X1 + 3.0)
        cy = r.uniform(YF - 0.1, YF + depth - 0.3)
        S.cyl((cx, cy, 0.0), r.uniform(0.12, 0.3), r.uniform(0.25, 0.7), "PLANT", M_PLANT, COL["plant"], n=6,
              r2=0.02)
    # erbacce anche davanti alla rete
    for i in range(5):
        cx = r.uniform(X0, X1)
        S.cyl((cx, YF - 0.25, 0.0), r.uniform(0.08, 0.16), r.uniform(0.2, 0.45), "PLANT", M_PLANT, COL["plant"],
              n=5, r2=0.02)


def hoarding(S, rng, xs0, xs1):
    """Palizzata di cantiere alta 1,8 m coperta di manifesti; dietro, il palazzo demolito (aperto)."""
    Y0 = YF - 0.05
    X0, X1 = X(xs0, Y0), X(xs1, Y0)
    S.box(X0 - 0.3, Y0, -0.3, X1 + 6.0, YF + 6.0, 0.02, "SIDEWALK", M_DIRT, COL["dirt"])
    h = S.box(X0, Y0, 0.0, X1, Y0 + 0.06, 1.8, "WOOD", M_HOARDING, "#3a2a30")
    n = int((X1 - X0) / 1.2)
    for i in range(n + 1):
        xp = X0 + (X1 - X0) * i / n
        S.box(xp - 0.04, Y0 - 0.05, 0.0, xp + 0.04, Y0, 1.86, "METAL", M_METAL, "#2e3649")
    S.op("posters", oid=h, X0=X0 + 0.1, X1=X1 - 0.1, z0=0.35, z1=1.7, seed=61, n=12, dense=True)
    S.op("graffiti", oid=h, X0=X0 + 0.1, X1=X1 - 0.1, z0=0.05, z1=0.8, seed=62, word="REVENGE")
    S.op("plate", oid=h, X0=X0 + 0.3, X1=X0 + 1.55, z0=1.12, z1=1.5, text="LAVORI IN CORSO", col="#20182a",
         bg="#e0b040", face_Y=Y0, lines=2)
    # dietro: un mucchio di sabbia, una betoniera abbandonata (cilindri), lampada di cantiere
    S.cyl((X0 + 1.6, YF + 2.5, 0.0), 1.1, 0.7, "CONCRETE", M_DIRT, "#3d2a33", n=10, r2=0.15)
    S.cyl((X1 - 0.8, YF + 1.8, 0.4), 0.45, 0.9, "METAL", M_RUST, COL["rust"], n=10, axis="x", r2=0.25)
    S.box(X1 - 1.4, YF + 1.5, 0.0, X1 - 0.2, YF + 2.1, 0.45, "METAL", M_METAL, "#2e3649")
    lamp = S.cyl((X0 + 0.5, Y0 - 0.06, 1.8), 0.08, 0.1, "LAMP", M_LAMP, "#ffa448", emi="#ffa448", n=8)
    # facciata cieca del palazzo a destra (si vede di fianco): niente, il palazzo del kebab ha il lato nascosto


def alley(S, rng, xs0, xs1):
    """Vicolo: cancello a sbarre, pavimento che sale, muro di fondo con una porta illuminata."""
    Yg = YF + 0.05
    X0, X1 = X(xs0, Yg), X(xs1, Yg)
    S.box(X0 - 0.4, Yg, -0.3, X1 + 6.0, YF + 4.5, 0.0, "SIDEWALK", M_ASPHALT, "#1a1426")
    # muro di fondo (Y = YF + 4)
    Yb = YF + 4.0
    wb = S.box(X0 - 3.0, Yb, 0.0, X1 + 8.0, Yb + 0.3, 14.0, "WALL", M_PLASTER_GREY, "#2a2636")
    dX = 4.0 * E.KYX / E.KX
    S.box(X0 + dX + 0.2, Yb - 0.02, 0.0, X0 + dX + 1.1, Yb + 0.02, 2.0, "WINDOW_LIT", M_WINDOW_LIT, "#ffb060",
          emi="#ffb060")
    S.cyl((X0 + dX + 0.65, Yb - 0.12, 2.15), 0.09, 0.12, "LAMP", M_LAMP, "#ffb060", emi="#ffb060", n=8)
    S.op("graffiti", oid=wb, X0=X0 + dX - 1.2, X1=X0 + dX + 0.1, z0=0.2, z1=1.3, seed=81, word="NO", face_Y=Yb)
    # bidoni del vicolo (cassonetti) e sacchi
    S.kit("kr:dumpster", (X0 + dX * 0.4 + 0.2, YF + 1.4, 0.0), "METAL", M_METAL, "#2a4038", s=4.6, rz=90)
    trash_bags(S, X0 + 0.5, rng, n=2)
    # cancello: telaio + sbarre verticali (in 2D)
    for xe in (X0, X1 - 0.08):
        S.box(xe, Yg - 0.04, 0.0, xe + 0.08, Yg + 0.04, 2.3, "METAL", M_METAL, "#2e3649")
    S.box(X0, Yg - 0.03, 2.2, X1, Yg + 0.03, 2.28, "POLE", M_METAL, "#2e3649")
    S.box(X0, Yg - 0.03, 0.05, X1, Yg + 0.03, 0.12, "POLE", M_METAL, "#2e3649")
    S.op("fence", along="x", X0=X0, X1=X1, Y=Yg, z0=0.12, z1=2.2, style="bars", seed=82)
    # fianco del palazzo del kebab: tubo e cavi
    S.tube([(X0 - 0.05, YF + 0.3, 3.0), (X0 - 0.05, YF + 3.0, 2.8)], 0.02, "CABLE", M_CABLE, "#14121c")


def utility_pole(S, xs):
    """Palo della linea elettrica sul marciapiede, con il cavo strappato che pende fino a terra.
    Il cavo arriva a terra in (x 1250, y 150): lì prosegue l'oggetto di scena 'cable'."""
    Yp = 0.32
    Xp = X(xs, Yp)
    pole = S.cyl((Xp, Yp, 0.0), 0.12, 9.0, "POLE", M_POLE, COL["pole"], n=10, r2=0.09)
    S.box(Xp - 0.75, Yp - 0.05, 4.35, Xp + 0.75, Yp + 0.05, 4.45, "METAL", M_METAL, "#2e3649")
    for dx in (-0.6, 0.0, 0.6):
        S.cyl((Xp + dx, Yp, 4.45), 0.04, 0.14, "METAL", M_METAL, "#55647c", n=6)
    # cassetta del trasformatore sul palo
    cab = S.box(Xp - 0.28, Yp - 0.34, 2.5, Xp + 0.28, Yp - 0.08, 3.2, "METAL", M_CABINET, COL["cabinet"])
    S.op("plate", oid=cab, X0=Xp - 0.22, X1=Xp + 0.22, z0=2.62, z1=2.98, text="⚡", col="#20182a", bg="#e0b040",
         face_Y=Yp - 0.34)
    # cavo strappato: dall'isolatore di sinistra giù fino a terra (punto di raccordo con l'oggetto 'cable')
    Xg, Yg = E.x_to_X(1250, 0.06), 0.06
    p0 = (Xp - 0.6, Yp, 4.5)
    pts = []
    for i in range(17):
        t = i / 16
        x = p0[0] + (Xg - p0[0]) * t
        y = p0[1] + (Yg - p0[1]) * t
        z = p0[2] * (1 - t) ** 1.6 + 0.02
        x += 0.25 * math.sin(t * math.pi) * (1 - t)
        pts.append((x, y, z))
    S.tube(pts, 0.025, "CABLE", M_CABLE, "#14121c")
    # cavi integri verso l'alto (spariscono sotto l'impalcato)
    for dx in (0.0, 0.6):
        S.tube([(Xp + dx, Yp, 4.55), (Xp + dx - 2.0, Yp + 0.3, 6.5)], 0.015, "CABLE", M_CABLE, "#14121c")
    S.op("plate", oid=pole, X0=Xp - 0.15, X1=Xp + 0.15, z0=1.3, z1=1.6, text="☠", col="#e0e0e0", bg="#b8303f",
         face_Y=Yp - 0.13)


def arena(S, rng):
    """Spiazzo sotto il viadotto (x 1536-1920, telecamera ferma): due piloni di cemento ai lati, una trave
    d'acciaio chiodata che li collega con le luci al sodio, una rete bassa con filo spinato. Al centro, sopra
    e attraverso la rete, si vede la città (piani di parallasse). Fusti, bancali e gomme dietro la fascia."""
    Yfence = YF + 2.6
    # muretto e rete (1,45 m) con filo spinato
    S.box(X(1560, 0) - 1.0, Yfence + 0.05, ZROAD, 60.0, Yfence + 0.3, 0.25, "CONCRETE", M_CONCRETE, "#2c2836")
    X0, X1 = X(1575, Yfence), X(1980, Yfence)
    n = int((X1 - X0) / 1.6)
    for i in range(n + 1):
        xp = X0 + (X1 - X0) * i / n
        S.cyl((xp, Yfence, ZROAD), 0.04, 1.2, "POLE", M_METAL, "#3a4256", n=8)
    S.tube([(X0, Yfence, 1.12), (X1, Yfence, 1.12)], 0.024, "POLE", M_METAL, "#3a4256")
    S.op("fence", along="x", X0=X0, X1=X1, Y=Yfence, z0=0.25, z1=1.12, style="chain", seed=141, sag=True)
    S.op("barbed", along="x", X0=X0, X1=X1, Y=Yfence, z=1.22)
    # due piloni 1,1 x 1,1 m con zoccolo
    pillars = []
    for k, xs in enumerate((1584, 1868)):
        Yp0 = YF + 0.7
        Xp = X(xs, Yp0)
        p = S.box(Xp, Yp0, ZROAD, Xp + 1.1, Yp0 + 1.1, 12.0, "CONCRETE", M_CONCRETE_PILLAR, COL["pillar"])
        S.box(Xp - 0.08, Yp0 - 0.08, ZROAD, Xp + 1.18, Yp0 + 1.18, 0.42, "CONCRETE", M_CONCRETE, "#2c2836")
        pillars.append((p, Xp, Yp0))
        S.op("graffiti", oid=p, X0=Xp + 0.05, X1=Xp + 1.05, z0=0.5, z1=1.5, seed=150 + k, word=("ZONA", "LIBERA")[k],
             face_Y=Yp0)
        S.op("posters", oid=p, X0=Xp + 0.1, X1=Xp + 1.0, z0=1.45, z1=2.0, seed=160 + k, n=2, face_Y=Yp0)
        # lampada al sodio sul pilone, rivolta verso l'arena
        S.box(Xp + 0.35, Yp0 - 0.4, 2.0, Xp + 0.75, Yp0, 2.07, "METAL", M_METAL, "#262c3c")
        S.box(Xp + 0.38, Yp0 - 0.38, 1.9, Xp + 0.72, Yp0 - 0.06, 2.0, "LAMP", M_LAMP, NEON["sodium"], emi=NEON["sodium"])
        S.tube([(Xp + 0.55, Yp0 - 0.02, 2.05), (Xp + 0.55, Yp0 - 0.02, 3.4)], 0.02, "CABLE", M_CABLE, "#14121c")
        S.box(Xp + 0.2, Yp0 - 0.03, 0.9, Xp + 0.5, Yp0, 1.25, "METAL", M_CABINET, COL["cabinet"])
    # trave d'acciaio a doppia T fra i piloni, chiodata, con due lampade appese
    (_, XA, Yp0), (_, XB, _) = pillars
    Yb = Yp0 + 0.3
    zb0, zb1 = 2.42, 2.6
    S.box(XA + 1.1, Yb, zb0, XB, Yb + 0.45, zb0 + 0.05, "METAL", M_STEEL, "#232a3a")
    S.box(XA + 1.1, Yb, zb1 - 0.05, XB, Yb + 0.45, zb1, "METAL", M_STEEL, "#232a3a")
    web = S.box(XA + 1.1, Yb + 0.2, zb0, XB, Yb + 0.25, zb1, "METAL", M_STEEL, COL["steel"])
    S.op("rivets", oid=web, X0=XA + 1.1, X1=XB, z0=zb0, z1=zb1, face_Y=Yb + 0.2)
    for xe in (XA + 1.1, XB - 0.22):
        S.box(xe, Yb - 0.03, zb0 - 0.14, xe + 0.22, Yb + 0.5, zb1 + 0.14, "METAL", M_STEEL, "#1c2232")
    for t in (0.33, 0.67):
        xl = XA + 1.1 + (XB - XA - 1.1) * t
        S.tube([(xl, Yb + 0.1, zb0), (xl, Yb + 0.1, zb0 - 0.12)], 0.012, "CABLE", M_CABLE, "#14121c")
        S.box(xl - 0.2, Yb - 0.06, zb0 - 0.2, xl + 0.2, Yb + 0.26, zb0 - 0.12, "METAL", M_METAL, "#262c3c")
        S.box(xl - 0.17, Yb - 0.03, zb0 - 0.24, xl + 0.17, Yb + 0.23, zb0 - 0.2, "LAMP", M_LAMP, NEON["sodium"],
              emi=NEON["sodium"])
    # a terra, dietro la fascia: fusti (uno rovesciato), bancali, gomme, sacchi, una cassa
    for (xs, dy, col) in ((1652, 0.5, "#5c3023"), (1672, 0.7, "#2e3649"), (1660, 1.3, "#5c3023")):
        Xc = X(xs, YF + dy)
        S.cyl((Xc, YF + dy, ZROAD), 0.29, 0.86, "METAL", M_RUST, col, n=12)
        S.cyl((Xc, YF + dy, ZROAD + 0.84), 0.3, 0.04, "METAL", M_METAL, "#262c3c", n=12)
    S.cyl((X(1700, YF + 1.6), YF + 1.6, ZROAD + 0.29), 0.29, 0.86, "METAL", M_RUST, "#43221c", n=12, axis="x")
    for k in range(3):
        S.box(X(1782, YF + 0.6), YF + 0.5, ZROAD + k * 0.15, X(1782, YF + 0.6) + 1.2, YF + 1.3,
              ZROAD + k * 0.15 + 0.12, "WOOD", M_WOOD, "#4a2f28")
    for k in range(2):
        S.cyl((X(1840, YF + 1.5), YF + 1.5, ZROAD + k * 0.22), 0.32, 0.22, "DARK", M_RUBBER, COL["rubber"], n=12)
    S.box(X(1745, YF + 1.8), YF + 1.8, ZROAD, X(1745, YF + 1.8) + 0.7, YF + 2.4, ZROAD + 0.6, "WOOD", M_WOOD, "#3b2228")
    trash_bags(S, X(1615, YF), rng, n=2)


def floor_dressing(S, rng):
    """Pozzanghere, crepe, rattoppi, sporco e rifiuti sul suolo (tutto in 2D, con le coordinate del mondo)."""
    r = random.Random(4242)
    # pozzanghere (x schermo, Y, raggi in metri)
    for (xs, Yc, rx, ry) in ((130, -1.2, 1.1, 0.35), (420, -3.4, 1.6, 0.5), (690, -0.6, 0.8, 0.25),
                             (980, -4.2, 1.9, 0.45), (1410, -2.9, 1.3, 0.4), (1600, -3.8, 2.2, 0.6),
                             (1700, -1.0, 1.4, 0.4), (1850, -4.4, 1.5, 0.5), (1440, -0.8, 0.7, 0.22)):
        S.op("puddle", X=X(xs, Yc), Y=Yc, rx=rx, ry=ry, seed=int(xs), z=ZROAD if Yc < YKERB - KERB_W else 0.0)
    # rattoppi d'asfalto e crepe
    for i in range(16):
        xs = r.uniform(0, 1920)
        Yc = r.uniform(-5.4, -2.6)
        S.op("patch", X=X(xs, Yc), Y=Yc, rx=r.uniform(0.5, 1.4), ry=r.uniform(0.2, 0.45), seed=1000 + i,
             z=ZROAD)
    for i in range(22):
        xs = r.uniform(0, 1920)
        Yc = r.uniform(-5.4, 0.4)
        S.op("crack", X=X(xs, Yc), Y=Yc, length=r.uniform(0.6, 1.8), seed=2000 + i)
    for i in range(30):
        xs = r.uniform(0, 1920)
        Yc = r.uniform(-5.2, 0.5)
        S.op("litter", X=X(xs, Yc), Y=Yc, seed=3000 + i)
    # strisce: bordo della carreggiata (bianco sbiadito, tratteggiato) e striscia gialla di sosta nell'arena
    S.op("lane", Y=-4.75, X0=-10.0, X1=X(1560, -4.75), dash=2.0, gap=1.6, col="#8a8494", z=ZROAD)


# ------------------------------------------------------------------ SECONDO ISOLATO (near, parallasse 0,5)
NEAR_PPM = 14.0


def build_near():
    """Palazzi di 5-6 piani del secondo isolato, visti dalla strada (pitch 0: facciate e sagome contro il
    cielo, niente superfici dei tetti): finestre accese o con persiane, balconi, insegne verticali al neon,
    serbatoi, antenne con la luce rossa, qualche cartellone. Densità ridotta (14 px/m): stanno lontano."""
    S = Scene("near")
    r = random.Random(77)
    width_px = 1152 + 60
    kx = NEAR_PPM * math.cos(math.radians(E.YAW))
    x = -4.0
    Xmax = width_px / kx + 6
    cols = ["#2d3a62", "#3a2f5e", "#283456", "#3d3462", "#2a3a5c", "#352c50"]
    words = ["HOTEL", "BAR", "BINGO", "MOTEL", "DISCO", "PUB"]
    blades = ["BAR", "HOTEL", "SEXY", "PUB", "ROOM"]
    wi = bi = 0
    hero_done = False
    while x < Xmax:
        w = r.uniform(8.0, 15.0)
        h = r.choice([15.0, 15.5, 16.0, 16.5, 17.0, 18.0])
        y0 = r.uniform(0.0, 3.0)
        # nel tratto visto dal lotto della partenza (x 70-240) palazzi bassi: si vede lo skyline dietro
        low = kx * x < 240 and kx * (x + w) > 70
        if low:
            h = 15.0
        hero = kx * x <= 994 < kx * (x + w) and not hero_done
        if hero:
            h = 17.0
            hero_done = True
        col = r.choice(cols)
        S.box(x, y0, 0.0, x + w, y0 + 10.0, h, "WALL", r.choice([M_PLASTER_BLUE, M_PLASTER_MAUVE]), col)
        fl = 3.0
        bay = r.choice([2.0, 2.4, 2.8])
        nb = max(1, int(w / bay))
        off = (w - nb * bay) / 2
        ww = bay * r.uniform(0.42, 0.55)
        for j in range(1, int(h / fl)):
            for i in range(nb):
                wx = x + off + i * bay + (bay - ww) / 2
                wz = j * fl + 0.75
                if r.random() < (0.62 if hero else 0.38):
                    c = r.choice(["#ffb060", "#ffa050", "#ffc878", "#ff7a50", "#ffb060", "#ff5a5a"])
                    S.box(wx, y0 - 0.05, wz, wx + ww, y0 + 0.05, wz + 1.45, "WINDOW_LIT", M_WINDOW_LIT, c, emi=c)
                else:
                    S.box(wx, y0 - 0.05, wz, wx + ww, y0 + 0.05, wz + 1.45, "GLASS", M_GLASS, "#0c1122")
        if r.random() < 0.55:
            for j in range(1, int(h / fl)):
                if j % 2 == 1:
                    S.box(x + 0.3, y0 - 0.8, j * fl + 0.05, x + w - 0.3, y0, j * fl + 0.2, "CONCRETE", M_CONCRETE,
                          "#3a3654")
                    S.box(x + 0.3, y0 - 0.85, j * fl + 0.2, x + w - 0.3, y0 - 0.75, j * fl + 0.95, "CONCRETE",
                          M_CONCRETE, "#2e2a46")
        # cornicione
        S.box(x - 0.15, y0 - 0.25, h, x + w + 0.15, y0 + 10.2, h + 0.45, "CONCRETE", M_CONCRETE, "#3a3654")
        # insegna verticale al neon sulla facciata (a bandiera)
        if r.random() < 0.45:
            bz0 = r.uniform(4.0, 7.0)
            word = blades[bi % len(blades)]
            bi += 1
            bxs = x + r.uniform(0.5, w - 1.0)
            sb = S.box(bxs, y0 - 1.5, bz0, bxs + 0.18, y0 - 0.05, bz0 + 1.0 + 0.62 * len(word), "SIGN", M_SIGNBOX,
                       "#1c2030")
            S.op("neon_vertical", oid=sb, Xf=bxs + 0.18, Y0=y0 - 1.5, Y1=y0 - 0.05, z0=bz0,
                 z1=bz0 + 1.0 + 0.62 * len(word), text=word, ramp=r.choice(["neon_red", "neon_orange"]), small=True)
        # tetto: serbatoio, antenne con luce rossa, casotto scale
        if r.random() < 0.5:
            tx = x + r.uniform(0.8, w - 3.5)
            S.cyl((tx + 1.2, y0 + 3.0, h + 0.45), 1.15, 2.4, "METAL", M_RUST, "#3a2430", n=12)
            for ax in (tx + 0.2, tx + 2.1):
                S.box(ax, y0 + 2.2, h + 0.45, ax + 0.18, y0 + 2.4, h + 1.4, "METAL", M_METAL, "#2e3649")
        if r.random() < 0.5:
            cx_ = x + r.uniform(0.5, w - 3.0)
            S.box(cx_, y0 + 1.0, h + 0.45, cx_ + 2.6, y0 + 3.5, h + 2.6, "WALL", M_PLASTER_GREY, "#2c2848")
        for _ in range(r.randint(1, 2)):
            ax = x + r.uniform(0.8, w - 0.8)
            ah = r.uniform(2.0, 5.5)
            S.box(ax, y0 + 1.0, h + 0.45, ax + 0.16, y0 + 1.16, h + 0.45 + ah, "POLE", M_METAL, "#3a4256")
            if r.random() < 0.7:
                S.box(ax - 0.1, y0 + 0.98, h + 0.45 + ah, ax + 0.26, y0 + 1.2, h + 0.8 + ah, "LAMP", M_LAMP,
                      "#ff3a3a", emi="#ff3a3a")
        if (r.random() < 0.3 and not low) or hero:
            bw = min(w - 1.0, r.uniform(5.0, 7.5)) if not hero else min(w - 0.6, 8.5)
            bx = x + (w - bw) / 2
            word = words[wi % len(words)] if not hero else "CINEMA"
            wi += 1
            bz0, bz1 = (h + 0.75, h + 2.15) if hero else (h + 1.6, h + 3.4)
            for px_ in (bx + 0.5, bx + bw - 0.8):
                S.box(px_, y0 + 0.6, h + 0.45, px_ + 0.25, y0 + 0.85, bz0, "METAL", M_METAL, "#2e3649")
            sb = S.box(bx, y0 + 0.4, bz0, bx + bw, y0 + 0.6, bz1, "SIGN", M_SIGNBOX, "#1c2030")
            S.op("neon_text", oid=sb, face="front", X0=bx, X1=bx + bw, z0=bz0, z1=bz1, Yf=y0 + 0.4, text=word,
                 ramp=r.choice(["neon_red", "neon_orange"]), font="near", frame=True)
        x += w + r.choice([0.0, 0.0, 0.0, 1.2, 2.5])
    return S


# ------------------------------------------------------------------ IMPALCATO (fg, parallasse 1,25)
def build_fg():
    """Impalcato del viadotto visto dal basso (telecamera con pitch -12): della travata vediamo il bordo
    lontano, una trave reticolare d'acciaio (correnti, montanti, diagonali chiodati) attraverso cui si vede
    la città; sotto pendono lampade al sodio e cavi. Nell'arena (x 1920-2304 del piano) un portale più pesante."""
    S = Scene("fg")
    r = random.Random(1250)
    Xa, Xb = -8.0, 75.0
    Yg = FG_YFAR                     # piano della trave reticolare
    zb0, zb1 = FG_ZB - 0.5, FG_ZB   # corrente inferiore (sotto) e superiore (sopra)
    ch = 0.13                        # altezza dei correnti
    # correnti
    lo = S.box(Xa, Yg, zb0, Xb, Yg + 0.3, zb0 + ch, "METAL", M_STEEL, COL["steel"])
    S.box(Xa, Yg - 0.06, zb0 - 0.03, Xb, Yg + 0.36, zb0, "METAL", M_STEEL, "#232a3a")       # piattabanda
    hi = S.box(Xa, Yg, zb1 - ch, Xb, Yg + 0.3, zb1 + 0.4, "METAL", M_STEEL, COL["steel"])
    # soletta sopra (si vede appena)
    S.box(Xa, Yg - 9.0, zb1 + 0.4, Xb, Yg + 0.5, zb1 + 1.0, "CONCRETE", M_CONCRETE, "#1c1a26")
    panel = 1.4
    x = Xa
    k = 0
    arena_X0 = (1920 - E.KYX * Yg) / E.KX
    while x < Xb:
        heavy = arena_X0 - 0.5 < x < arena_X0 + 9.5 and k % 2 == 0
        wv = 0.22 if heavy else 0.1
        S.box(x - wv / 2, Yg + 0.05, zb0 + ch, x + wv / 2, Yg + 0.25, zb1 - ch, "METAL", M_STEEL,
              "#232a3a" if heavy else COL["steel"])
        # diagonale (alternata)
        if k % 2 == 0:
            p0, p1 = (x, Yg + 0.15, zb0 + ch), (x + panel, Yg + 0.15, zb1 - ch)
        else:
            p0, p1 = (x, Yg + 0.15, zb1 - ch), (x + panel, Yg + 0.15, zb0 + ch)
        S.tube([p0, p1], 0.032, "METAL", M_STEEL, COL["steel"], n=4)
        # lampada al sodio ogni 4 campate, piatta e attaccata sotto il corrente: non deve scendere sotto
        # y 25 dello schermo, dove cominciano le insegne del fondale (y 27-45)
        if k % 4 == 1:
            S.box(x + 0.36, Yg - 0.08, zb0 - 0.07, x + 0.7, Yg + 0.16, zb0 - 0.02, "METAL", M_METAL, "#262c3c")
            S.box(x + 0.40, Yg - 0.05, zb0 - 0.09, x + 0.66, Yg + 0.13, zb0 - 0.07, "LAMP", M_LAMP, NEON["sodium"],
                  emi=NEON["sodium"])
        k += 1
        x += panel
    S.op("rivets", oid=lo, X0=Xa, X1=Xb, z0=zb0, z1=zb0 + ch, face_Y=Yg)
    # cavi tesi lungo la travata: pendono di poco, sempre sopra y 25 dello schermo (le insegne sono sotto)
    for i in range(10):
        xa = r.uniform(Xa, Xb - 6)
        xb = xa + r.uniform(2.5, 6.0)
        sag = r.uniform(0.02, 0.05)
        pts = [(xa + (xb - xa) * t / 12, Yg - 0.2, zb0 - 0.02 - sag * 4 * (t / 12) * (1 - t / 12)) for t in range(13)]
        S.tube(pts, 0.02, "CABLE", M_CABLE, "#14121c")
    # tubo dell'acqua lungo la travata
    S.cyl((Xa, Yg - 0.12, zb0 + 0.05), 0.07, Xb - Xa, "PIPE", M_METAL, "#2e3649", n=8, axis="x")
    return S


def jobs_for(scene_name):
    """Ritorna (scena, vista) per ciascuna scena."""
    if scene_name == "street":
        S = build_street()
        view = dict(yaw=E.YAW, pitch=E.PITCH, ppm=E.PPM, ss=E.SS, x0=0, x1=E.LEVEL_W, y0=0, y1=E.SCREEN_H, oy=E.OY)
        return S, view
    if scene_name == "near":
        S = build_near()
        # i tetti più bassi (13 m) cadono intorno a y 80 dello schermo; il fondo dell'immagine è nascosto
        kz = NEAR_PPM
        view = dict(yaw=E.YAW, pitch=0.0, ppm=NEAR_PPM, ss=E.SS, x0=0, x1=1152, y0=0, y1=168,
                    oy=round(38 + kz * 18.0))
        return S, view
    if scene_name == "fg":
        S = build_fg()
        # telecamera che guarda in su: y = oy + KYY*Y - KZ*Z; il fondo della trave lontana va a y 22
        oy = round(21 - E.KYY * FG_YFAR + E.KZ * (FG_ZB - 0.5 - 0.03))
        view = dict(yaw=E.YAW, pitch=-E.PITCH, ppm=E.PPM, ss=E.SS, x0=0, x1=2304, y0=0, y1=64, oy=oy)
        return S, view
    raise KeyError(scene_name)


FG_YFAR = 3.0
FG_ZB = 5.0
